#!/usr/bin/env python3

import os
import click
import logging

from typing import Dict
from configparser import ConfigParser

from src.model import Orders, Config


ROOT_PATH = os.path.dirname(os.path.abspath(__name__))
CONFIG_FILE = os.path.join(ROOT_PATH, "preferences.ini")
CONFIG_SECTION = "Preferences"


def bool_to_str(item: bool) -> str:
    if item:
        return "yes"
    else:
        return "no"


def get_preferences() -> Dict:
    parser = ConfigParser()
    parser.read(CONFIG_FILE)

    csv_order = Orders[parser.get(CONFIG_SECTION, "csv_order")]
    use_ollama = parser.getboolean(CONFIG_SECTION, "use_ollama")
    keep_payments = parser.getboolean(CONFIG_SECTION, "keep_payments")
    negative_expenses = parser.getboolean(CONFIG_SECTION, "negative_expenses")
    preferences = Config(csv_order, use_ollama, keep_payments, negative_expenses)

    return preferences


@click.command()
@click.option("-o", "--order", type=click.Choice([order.value for order in Orders]), default=Orders.SIMPLE.value,
              help="CSV Order. Defaults to the simple order, which is Date, Amount, and Note (Description)")
@click.option("-u", "--use-ollama", is_flag=True, default=False,
              help="Use Ollama and local LLM to categorize expenses. NOTE: Experimental Feature. Defaults to False.")
@click.option("-k", "--keep-payments", is_flag=True, default=False,
              help="Keep payments to Credit Card Bill in transactions. Defaults to False.")
@click.option("-n", "--negative_expenses", is_flag=True, default=False,
              help="Have expenses represented as negative values and incomes represented as positive values. Defaults to False.")
def cli(order: Orders, use_ollama: bool, keep_payments: bool, negative_expenses: bool):
    """
    Writes an .ini file dictating Ena's behavioural preferences.
    """
    logging.basicConfig(level=logging.INFO)

    config = ConfigParser()
    config[CONFIG_SECTION] = {
        "csv_order": order,
        "use_ollama": bool_to_str(use_ollama),
        "keep_payments": bool_to_str(keep_payments),
        "negative_expenses": bool_to_str(negative_expenses),
    }

    with open(CONFIG_FILE, "w+") as config_file:
        config.write(config_file)


if __name__ == "__main__":
    cli()
