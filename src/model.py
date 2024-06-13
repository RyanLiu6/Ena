import re
import logging

from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, List, TypeVar


# Two orders are specified here, whichever is used can be configured via CLI.
class Orders(Enum):
    DEFAULT = "DEFAULT"
    DIME = "DIME"
    SIMPLE = "SIMPLE"


CSV_ORDERS = {
    Orders.DEFAULT: ["date", "amount", "note", "category"],
    Orders.DIME: ["category", "note", "date", "amount"],
    Orders.SIMPLE: ["date", "amount", "note"],
}


# User config
@dataclass
class Preferences:
    csv_order: Orders
    use_llm: bool
    positive_expenses: bool


class Category(Enum):
    RECURRING = "Recurring"
    GROCERIES = "Groceries"
    HOUSEHOLD = "Household"
    FOOD = "Food"
    FUN = "Fun"
    FASHION = "Fashion"
    GAMES = "Games"
    TRAVEL = "Travel"
    GIFTS = "Gifts"
    # Used to differentiate payments / refunds
    # / cashback rewards from expenses
    INCOME = "Income"
    # Serves as generic expense
    EXPENSE = "Expense"


@dataclass
class Transaction:
    date: str
    amount: float
    note: str
    category: Category = Category.EXPENSE

    def __eq__(self, other):
        return isinstance(other, Transaction) and self.date == other.date and self.amount == other.amount \
            and self.note == other.note and self.category == other.category

    def row_repr(self) -> Dict:
        """
        Returns the Row Representation of a Transaction.

        Returns:
            Dict: Dictionary representation of this Transaction
        """
        return {
            "date": self.date,
            "amount": self.amount,
            "note": self.note,
            "category": self.category.value,
        }

    def simple_repr(self) -> Dict:
        """
        Returns the Row Representation of a Transaction, simplified (without category).

        Returns:
            Dict: Dictionary representation of this Transaction
        """
        return {
            "date": self.date,
            "amount": self.amount,
            "note": self.note,
        }


class BaseFI(ABC):
    """
    Code for Regex Expressions and validate are directly from Bizzaro:Teller
    """
    def __init__(self, name: str, regex: Dict):
        self.name = name
        self.regex = regex

    def get_transaction_regex(self) -> str:
        """
        Get Transaction regex.

        Returns:
            str: Transaction regex.
        """
        return self.regex["transaction"]

    @abstractmethod
    def is_transaction_income(self, transaction: Transaction) -> bool:
        """
        Must be implemented by individual FI Classes due to statements being different
        between different FIs.
        """
        pass

    def get_start_year(self, statement: str) -> int:
        """
        Get starting year for a given statement.

        Args:
            statement (str): Text extracted from a given statement.

        Returns:
            int: Starting year of statement.
        """
        logging.info("Getting Starting Year")
        match = re.search(self.regex["start_year"], statement, re.IGNORECASE)
        year = int(match.groupdict()["year"].replace(', ', ''))
        logging.info(f"Starting Year: {year}")
        return year

    def get_opening_balance(self, statement: str) -> float:
        """
        Get opening balance for a given statement.

        Args:
            statement (str): Text extracted from a given statement.

        Returns:
            float: Opening balance, represented as float since transactions
                are not clean integer numbers.
        """
        logging.info("Getting Opening Balance")
        match = re.search(self.regex["open_balance"], statement)
        if (match.groupdict()["cr"] and "-" not in match.groupdict()["balance"]):
            balance = float("-" + match.groupdict()["balance"].replace("$", ""))
            logging.info("Patched credit balance found for opening balance: %f" % balance)
            return balance

        balance = float(match.groupdict()["balance"].replace(",", "").replace("$", ""))
        logging.info(f"Opening Balance: {balance}")
        return balance

    def get_closing_balance(self, statement: str) -> float:
        """
        Get closing balance for a given statement.

        Args:
            statement (str): Text extracted from a given statement.

        Returns:
            float: Closing balance, represented as float since transactions
                are not clean integer numbers.
        """
        logging.info("Getting Closing Balance")
        match = re.search(self.regex["closing_balance"], statement)
        if (match.groupdict()["cr"] and "-" not in match.groupdict()["balance"]):
            balance = float("-" + match.groupdict()["balance"].replace("$", ""))
            logging.info("Patched credit balance found for closing balance: %f" % balance)
            return balance

        balance = float(match.groupdict()["balance"].replace(",", "").replace("$", "").replace(" ", ""))
        logging.info(f"Closing Balance: {balance}")
        return balance

    def validate(self, opening_balance: int, closing_balance: int, transactions: List[Transaction], positive_expenses: bool):
        """
        Validates list of processed transactions against opening and closing balances.

        Args:
            opening_balance (int): Opening balance for a given statement
            closing_balance (int): Closing balance for a given statement
            transactions (List[Transaction]): List of transactions for a given statement
            positive_expenses (bool): True if expenses are represented as positive floats,
                False if they are represented as negative floats instead.

        Raises:
            AssertionError: An exception is raised when not all transactions are accounted for due to
                mismatched sum.
        """
        # spend transactions are negative numbers.
        # net will most likely be a neg number unless your payments + cash back are bigger than spend
        # outflow is less than zero, so purchases
        # inflow is greater than zero, so payments/cashback

        # closing balance is a positive number
        # opening balance is only negative if you have a CR, otherwise also positive
        net = round(sum([r.amount for r in transactions]), 2)
        outflow = round(sum([r.amount for r in transactions if r.amount < 0]), 2)
        inflow = round(sum([r.amount for r in transactions if r.amount > 0]), 2)
        difference = round(opening_balance - closing_balance, 2)
        if positive_expenses:
            difference *= -1

        if difference != net:
            logging.warn(f"Difference is {difference} vs {net}")
            logging.warn(f"Opening Balance: {opening_balance}")
            logging.warn(f"Closing Balance: {closing_balance}")
            logging.warn(f"Transactions (net/infow/outflow): {net} / {inflow} / {outflow}")
            logging.warn("Parsed transactions:")
            for item in sorted(transactions, key=lambda item: item.date):
                logging.warn(item)
            raise AssertionError("Discrepancy found, bad parse :(. Not all transcations are accounted for, validate your transaction regex.")


class RBC(BaseFI):
    def __init__(self):
        regex = {
            "transaction": (r"^(?P<dates>(?:\w{3} \d{2} ){2})"
                r"(?P<description>.+)\s"
                r"(?P<amount>-?\$[\d,]+\.\d{2}-?)(?P<cr>(\-|\s?CR))?"),
            "start_year": r"STATEMENT FROM .+(?P<year>-?\,.[0-9][0-9][0-9][0-9])",
            "open_balance": r"(PREVIOUS|Previous) (STATEMENT|ACCOUNT|Account) (BALANCE|Balance) (?P<balance>-?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?",
            "closing_balance": r"(?:NEW|CREDIT) BALANCE (?P<balance>-?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?"
        }

        super().__init__(name="RBC", regex=regex)

    def is_transaction_income(self, transaction: Transaction, positive_expenses: bool) -> bool:
        """
        Checks if a given transaction is considered an income transaction. This
        is explicitly any transactions that show up on the CC bill that are:
        1. Cash Back Rewards
        2. Payment towards the bill
        3. Refunds / Chargebacks

        Args:
            transaction (Transaction): Transaction to be checked
            positive_expenses (bool): True if expenses are represented as positive floats,
                False if they are represented as negative floats instead.

        Returns:
            bool: True if given transaction is considered income, False if its
                considered expense
        """
        # If positive_expenses is True, then expenses are > 0 and income < 0
        amount = transaction.amount if positive_expenses else transaction.amount * -1
        return amount < 0


class TD(BaseFI):
    def __init__(self):
        """
        NOTE: Currently unimplemented as I do not have access to a TD CC Statement.
        """
        regex = {
            "transaction": (r"(?P<dates>(?:\w{3} \d{1,2} ){2})"
                r"(?P<description>.+)\s"
                r"(?P<amount>-?\$[\d,]+\.\d{2}-?)(?P<cr>(\-|\s?CR))?"),
            "start_year": r"Statement Period: .+(?P<year>-?\,.[0-9][0-9][0-9][0-9])",
            "open_balance": r"(PREVIOUS|Previous) (STATEMENT|ACCOUNT|Account) (BALANCE|Balance) (?P<balance>-?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?",
            "closing_balance": r"(?:NEW|CREDIT) BALANCE (?P<balance>\-?\s?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?"
        }

        super().__init__(name="TD", regex=regex)

    def is_transaction_income(self, transaction: Transaction) -> bool:
        """
        Checks if a given transaction is considered an income transaction. This
        is explicitly any transactions that show up on the CC bill that are:
        1. Cash Back Rewards
        2. Payment towards the bill
        3. Refunds / Chargebacks

        NOTE: Currently unimplemented as I do not have access to a TD CC Statement.

        Args:
            transaction (Transaction): Transaction to be checked

        Returns:
            bool: True if given transaction is considered income, False if its
                considered expense
        """
        ...


class BNS(BaseFI):
    def __init__(self):
        regex = {
            "transaction": (r"^(?P<dates>(?:\w{3} \d{2} ){2})"
                r"(?P<description>.+)\s"
                r"(?P<amount>-?\$[\d,]+\.\d{2}-?)(?P<cr>(\-|\s?CR))?"),
            "start_year": r"STATEMENT FROM .+(?P<year>-?\,.[0-9][0-9][0-9][0-9])",
            "open_balance": r"(PREVIOUS|Previous) (STATEMENT|ACCOUNT|Account) (BALANCE|Balance) (?P<balance>-?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?",
            "closing_balance": r"(?:NEW|CREDIT) BALANCE (?P<balance>-?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?"
        }

        super().__init__(name="BNS", regex=regex)

    def is_transaction_income(self, transaction: Transaction) -> bool:
        """
        Checks if a given transaction is considered an income transaction. This
        is explicitly any transactions that show up on the CC bill that are:
        1. Cash Back Rewards
        2. Payment towards the bill
        3. Refunds / Chargebacks

        Args:
            transaction (Transaction): Transaction to be checked

        Returns:
            bool: True if given transaction is considered income, False if its
                considered expense
        """
        ...


class FIFactory:
    type_FI = TypeVar("type_FI", RBC, TD, BNS)

    @staticmethod
    def get_processor(fi_name: str) -> type_FI:
        """
        Gets FI specific class given FI name.

        Args:
            fi_name (str): Name of Financial Institute to get processor class for.

        Raises:
            KeyError: An exception is raised when fi_name is not supported.

        Returns:
            FI: An instance of a FI class from above, which must be a subclass of BaseFI.
        """
        match fi_name:
            case "RBC":
                return RBC()
            case "TD":
                return TD()
            case "BNS":
                return BNS()
            case _:
                raise KeyError(f"Financial Institute {fi_name} is currently not supported. Please open an issue or follow instructions to add it yourself!")
