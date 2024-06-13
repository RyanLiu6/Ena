import os
import re
import csv
import logging
import pdfplumber

from Preferences import ROOT_PATH, get_preferences

from typing import List
from datetime import datetime
from collections import defaultdict
from src.model import Category, Orders, Transaction, FIFactory, CSV_ORDERS


class Ena:
    def __init__(self, statements_dir: str):
        """
        Does two things:
        1. Globs available statements and maps FI Name to corresponding statements'
            absolute path

        2. Reads stored preferences

        Args:
            statements_dir (str): Directory where statements are stored.
        """
        self.preferences = get_preferences()
        self.statements = defaultdict(list)
        for item in os.listdir(statements_dir):
            local_path = os.path.join(statements_dir, item)

            if os.path.isdir(local_path):
                for file_name in os.listdir(local_path):
                    if file_name.endswith(".pdf"):
                        file_path = os.path.join(local_path, file_name)
                        self.statements[item].append(file_path)

    def parse_statements(self):
        """
        Parses all statements found, ordered by individual Financial Institutes.
        """
        for fi_name, statements in self.statements.items():
            csv_data = []
            processor = FIFactory.get_processor(fi_name=fi_name)
            for statement in statements:
                csv_data.extend(self._parse_statement(processor, statement))

            csv_data.sort(key=lambda x: x.date)
            file_path = os.path.join(ROOT_PATH, "output", fi_name, f"{int(datetime.today().timestamp())}.csv")
            with open(file_path, "w+", newline="") as csv_file:
                csv_order = CSV_ORDERS[self.preferences.csv_order]
                writer = csv.DictWriter(csv_file, csv_order)
                writer.writeheader()
                for txn in csv_data:
                    if csv_order == Orders.SIMPLE:
                        writer.writerow(txn.simple_repr())
                    else:
                        writer.writerow(txn.row_repr())

    def _parse_statement(self, processor: FIFactory.type_FI, statement_path: str) -> List[Transaction]:
        """
        Code is directly from Bizzaro:Teller/teller/pdf_processor.py, but modified to fit
        Ena's models and needs.

        Specifically:
        1. Category is added via Ollama based on available categories and confidence %.
            a. This behaviour can be disabled.

        2. Transactions will all have "positive" value, ie, > 0, as Ena is designed to be an
            expense tracker for Credit Cards. In the rare case that a transaction is "negative",
            for income of some sort (Cashback rewards, refunds, etc), it'll be categorized under
            Category.INCOME with a negative value.
            a. This behaviour can be inverted so that Expenses are negative and Incomes are positive.

        All the above configuration and more are outlined in README.md and configured via config.py.

        Args:
            processor (FIFactory.type_FI): Financial Insitute's class (from src/model.py). Must be an
                instance of Base_FI.
            statement_path (str): Absolute path to statement being processed.

        Returns:
            List[Transaction]: List of transactions
        """
        transactions = []
        with pdfplumber.open(statement_path) as pdf:
            logging.info("=================================================")

            text = ""
            for page in pdf.pages:
                text += page.extract_text(x_tolerance=1)

            year = processor.get_start_year(text)
            opening_balance = processor.get_opening_balance(text)
            closing_balance = processor.get_closing_balance(text)

            print(text)

            # debugging transaction mapping - all 3 regex in transaction have to find a result in order for it to be considered a "match"
            year_end = False
            transaction_regex = processor.get_transaction_regex()
            for match in re.finditer(transaction_regex, text, re.MULTILINE):
                match_dict = match.groupdict()
                print(match_dict)

                date = match_dict["dates"].replace("/", " ") # change format to standard: 03/13 -> 03 13
                date = date.split(" ")[0:2]  # Aug. 10 Aug. 13 -> ["Aug.", "10"]
                date[0] = date[0].strip(".") # Aug. -> Aug
                date.append(str(year))
                date = " ".join(date) # ["Aug", "10", "2021"] -> Aug 10 2021

                try:
                    date = datetime.strptime(date, "%b %d %Y") # try Aug 10 2021 first
                except: # yes I know this is horrible, but this script runs once if you download your .csvs monthly, what do you want from me
                    date = datetime.strptime(date, "%m %d %Y") # if it fails, 08 10 2021

                # need to account for current year (Jan) and previous year (Dec) in statements
                month = date.strftime("%m")
                if month == "12" and not year_end:
                    year_end = True
                if month == "01" and year_end:
                    date = date.replace(year=date.year + 1)

                if (match_dict["cr"]):
                    logging.info(f"Credit balance found in transaction: {match_dict['amount']}")
                    amount = -float("-" + match_dict["amount"].replace("$", "").replace(",", ""))
                else:
                    amount = -float(match_dict["amount"].replace("$", "").replace(",", ""))

                # checks description regex
                if ("$" in match_dict["description"]):
                    logging.info(f"$ found in description: {match_dict['description']}")
                    newAmount = re.search(r"(?P<amount>-?\$[\d,]+\.\d{2}-?)(?P<cr>(\-|\s?CR))?", match_dict["description"])
                    amount = -float(newAmount["amount"].replace("$", "").replace(",", ""))
                    match_dict["description"] = match_dict["description"].split("$", 1)[0]

                # Set amount based on preferences
                if self.preferences.positive_expenses:
                    amount *= -1

                transaction = Transaction(date=str(date.date().isoformat()),
                                          amount=amount,
                                          note=match_dict["description"].strip())

                # Check if transaction should be directly categorized as income transaction
                if processor.is_transaction_income(transaction, self.preferences.positive_expenses):
                    transaction.category = Category.INCOME
                else:
                    if self.preferences.use_llm:
                        # Get category via inference
                        ...
                    else:
                        transaction.category = Category.EXPENSE

                """
                Transactions is represented as a List instead of Set because duplicate transactions
                where properties are the same (Transaction.__eq__) are valid.

                It's entirely possible that you make the same purchase at the same spot regularly.
                """
                transactions.append(transaction)

        processor.validate(opening_balance, closing_balance, transactions, self.preferences.positive_expenses)
        return transactions
