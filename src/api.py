import os
import re
import csv
import pdfplumber

from pprint import pprint
from config import ROOT_PATH
from datetime import datetime
from collections import defaultdict
from src.model import Category, Transaction


class Ena:
    def __init__(self, statements_dir: str):
        self.statements = defaultdict(list)
        for item in os.listdir(statements_dir):
            local_path = os.path.join(statements_dir, item)

            if os.path.isdir(local_path):
                for file_name in os.listdir(local_path):
                    if file_name.endswith(".pdf"):
                        file_path = os.path.join(local_path, file_name)
                        self.statements[item].append(file_path)

    def parse_statements(self):
        for FI, statements in self.statements.items():
            csv_data = []
            for statement in statements:
                csv_data.extend(self._parse_statement(statement))

            csv_data.sort(key=lambda x: x.date)
            file_path = os.path.join(ROOT_PATH, "output", FI, f"{int(datetime.today().timestamp())}.csv")
            with open(file_path, "w+", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, ["Date", "Amount", "Note", "Category"])
                writer.writeheader()
                for txn in csv_data:
                    writer.writerow(txn.row_repr())

    def _parse_statement(self, pdf_path: str):
        transactions = []
        # with pdfplumber.open(pdf_path) as pdf:
        #     pprint("=================================================")
        #     pprint(pdf_path)

        #     text = ""
        #     for page in pdf.pages:
        #         text += page.extract_text()

        #     pprint(text)

        for i in range(10):
            transactions.append(Transaction(datetime(2024, 1, i + 1), (i + 5)*(i + 5), ""))

        return transactions
