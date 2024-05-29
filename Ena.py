#!/usr/bin/env python

import os
import click

from src.api import Ena
from config import STATEMENTS_PATH


@click.command()
@click.option("-d", "--directory", "statements_dir", type=click.Path(exists=True),
              default=STATEMENTS_PATH, help="Directory where statements are.")
def cli(statements_dir: str):
    """
    Parses FI Statements into CSVs to be used for book-keeping purposes. Officially
    supported use-cases are Dime (iOS) and Google Sheets.
    """
    ena = Ena(statements_dir)
    ena.parse_statements()


if __name__ == "__main__":
    cli()
