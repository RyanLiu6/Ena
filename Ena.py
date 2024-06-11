#!/usr/bin/env python

import os
import click
import logging

from src.api import Ena
from config import STATEMENTS_PATH


@click.command()
@click.option("-d", "--directory", "statements_dir", type=click.Path(exists=True),
              default=STATEMENTS_PATH, help="Directory where statements are. Defaults to Ena/statements")
@click.option("-v", "--verbose", is_flag=True, default=False,
              help="If true, logs at INFO level. Else, defaults to WARNING level.")
def cli(statements_dir: str, verbose: bool):
    """
    Parses FI Statements into CSVs to be used for book-keeping purposes. Officially
    supported use-cases are Dime (iOS) and Google Sheets.
    """
    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    ena = Ena(statements_dir)
    ena.parse_statements()


if __name__ == "__main__":
    cli()
