import os
import re
import csv
import logging
import pdfplumber

from config import ROOT_PATH

from typing import List
from datetime import datetime
from collections import defaultdict
from src.model import Category, Transaction, FIFactory, CSV_ORDERS


class Ena:
    def __init__(self, order: str, statements_dir: str):
        """
        Iterates statements_dir to create dictionary where:
        Key = Financial Institute Name
        Value = List of Statements (absolute path)

        Args:
            order (str): CSV Order
            statements_dir (str): Directory where statements are stored.
        """
        self.csv_order = CSV_ORDERS[order]
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
                writer = csv.DictWriter(csv_file, self.csv_order)
                writer.writeheader()
                for txn in csv_data:
                    writer.writerow(txn.row_repr())

    def _parse_statement(self, processor: FIFactory.type_FI, statement_path: str) -> List[Transaction]:
        """
        Code is directly from Bizzaro:Teller/teller/pdf_processor.py, but modified to fit
        Ena's models and needs.

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

            # debugging transaction mapping - all 3 regex in transaction have to find a result in order for it to be considered a "match"
            year_end = False
            transaction_regex = processor.get_transaction_regex()
            for match in re.finditer(transaction_regex, text, re.MULTILINE):
                match_dict = match.groupdict()
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

                transaction = Transaction(date=str(date.date().isoformat()),
                                          amount=amount,
                                          note=match_dict["description"].strip())

                if transaction in transactions:
                    # Assumes all duplicate transactions are valid
                    transaction.description = transaction.description + " 2"
                else:
                    transactions.append(transaction)

        processor.validate(opening_balance, closing_balance, transactions)
        return transactions
