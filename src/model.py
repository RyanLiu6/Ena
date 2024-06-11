import re
import logging

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, TypeVar


class Category(Enum):
    RECURRING = "Recurring"
    GROCERIES = "Groceries"
    DINING = "Dining"
    ENTERTAINMENT = "Entertainment"
    MISC = "Misc"
    NONE = "N/A"


@dataclass
class Transaction:
    date: str
    amount: float
    note: str
    category: Category = Category.NONE

    def row_repr(self):
        return {
            "Date": self.date,
            "Amount": self.amount,
            "Note": self.note,
            "Category": self.category,
        }


class BaseFI:
    """
    Code for Regex, along with Regex Expressions are all directly from Bizzaro:Teller
    """
    def __init__(self, name: str, regex: Dict):
        self.name = name
        self.regex = regex

    def get_transaction_regex(self):
        return self.regex["transaction"]

    def get_start_year(self, pdf_text: str) -> int:
        logging.info("Getting Starting Year")
        match = re.search(self.regex["start_year"], pdf_text, re.IGNORECASE)
        year = int(match.groupdict()["year"].replace(', ', ''))
        logging.info(f"Starting Year: {year}")

        return year

    def get_opening_balance(self, pdf_text: str) -> int:
        logging.info("Getting Opening Balance")
        match = re.search(self.regex["open_balance"], pdf_text)
        if (match.groupdict()["cr"] and "-" not in match.groupdict()["balance"]):
            balance = float("-" + match.groupdict()["balance"].replace("$", ""))
            logging.info("Patched credit balance found for opening balance: %f" % balance)
            return balance

        balance = float(match.groupdict()["balance"].replace(",", "").replace("$", ""))
        logging.info(f"Opening Balance: {balance}")
        return balance

    def get_closing_balance(self, pdf_text: str) -> int:
        logging.info("Getting Closing Balance")
        match = re.search(self.regex["closing_balance"], pdf_text)
        if (match.groupdict()["cr"] and "-" not in match.groupdict()["balance"]):
            balance = float("-" + match.groupdict()["balance"].replace("$", ""))
            logging.info("Patched credit balance found for closing balance: %f" % balance)
            return balance

        balance = float(match.groupdict()["balance"].replace(",", "").replace("$", "").replace(" ", ""))
        logging.info(f"Closing Balance: {balance}")
        return balance

    def validate(self, opening_balance: int, closing_balance: int, transactions: List[Transaction]):
        # spend transactions are negative numbers.
        # net will most likely be a neg number unless your payments + cash back are bigger than spend
        # outflow is less than zero, so purchases
        # inflow is greater than zero, so payments/cashback

        # closing balance is a positive number
        # opening balance is only negative if you have a CR, otherwise also positive
        net = round(sum([r.amount for r in transactions]), 2)
        outflow = round(sum([r.amount for r in transactions if r.amount < 0]), 2)
        inflow = round(sum([r.amount for r in transactions if r.amount > 0]), 2)
        if round(opening_balance - closing_balance, 2) != net:
            logging.info(f"Difference is {opening_balance - closing_balance} vs {net}")
            logging.info(f"Opening Balance: {opening_balance}")
            logging.info(f"Closing Balance: {closing_balance}")
            logging.info(f"Transactions (net/infow/outflow): {net} / {inflow} / {outflow}")
            logging.info("Parsed transactions:")
            for item in sorted(transactions, key=lambda item: item.date):
                logging.info(item)
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


class TD(BaseFI):
    def __init__(self):
        regex = {
            "transaction": (r"(?P<dates>(?:\w{3} \d{1,2} ){2})"
                r"(?P<description>.+)\s"
                r"(?P<amount>-?\$[\d,]+\.\d{2}-?)(?P<cr>(\-|\s?CR))?"),
            "start_year": r"Statement Period: .+(?P<year>-?\,.[0-9][0-9][0-9][0-9])",
            "open_balance": r"(PREVIOUS|Previous) (STATEMENT|ACCOUNT|Account) (BALANCE|Balance) (?P<balance>-?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?",
            "closing_balance": r"(?:NEW|CREDIT) BALANCE (?P<balance>\-?\s?\$[\d,]+\.\d{2})(?P<cr>(\-|\s?CR))?"
        }

        super().__init__(name="TD", regex=regex)


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


FI_TO_CLASS = {
    "RBC": RBC,
    "TD": TD,
    "BNS": BNS,
}


FI = TypeVar("FI", RBC, TD, BNS)
