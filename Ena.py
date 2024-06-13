#!/usr/bin/env python3

import os
import click
import logging

from src.api import Ena
from Preferences import ROOT_PATH, CONFIG_FILE, write_preferences

STATEMENTS_PATH = os.path.join(ROOT_PATH, "statements")


@click.command()
@click.option("-d", "--directory", "statements_dir", type=click.Path(exists=True),
              default=STATEMENTS_PATH, help="Directory where statements are. Defaults to Ena/statements")
@click.option("-v", "--verbose", is_flag=True, default=False,
              help="If set, logs at INFO level. Else, defaults to WARNING level.")
@click.option("-m", "--manual-review", is_flag=True, default=False,
              help="""
                If set and using LLM to infer categories, any transactions that are categorized as
                Expense (catch-all) will be presented for manual review. Defaults to False.
            """)
def cli(statements_dir: str, verbose: bool, manual_review: bool):
    """
    Parses FI Statements into CSVs to be used for book-keeping purposes. Officially
    supported use-cases are Dime (iOS) and Google Sheets.
    """
    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    try:
        os.path.isfile(CONFIG_FILE)
    except FileNotFoundError:
        write_preferences()

    ena = Ena(statements_dir, manual_review)
    ena.parse_statements()


if __name__ == "__main__":
    cli()
