# Ena
Converts and categorizes transactions into CSVs for Canadian Financial Institutions. Uses Llama3 to infer categories via Ollama.

## Credits
Credits to [Bizzaro](https://github.com/Bizzaro), whose fork of [Teller](https://github.com/Bizzaro/Teller) was my goto tool for a period of time. I found myself wanting to make something similar with some changes to benefit my personal use-case. So, full credits to them, as their Regex code for processing statements was extremely helpful for creating a base to work off of.

## Table of Contents
* [Features](#features)
* [Usage](#usage)
    * [Preferences](#preferences)
        * [Options for Preferences](#options-for-preferences)
    * [Ena](#ena-1)
        * [Options for Ena](#options-for-ena)
* [Goals and WIP](#goals-and-wIP)
* [Contributing](#contributing)

## Features
Ena was built as a tool to better house-keep finances, rather than simply paying Credit Card bills monthly without checking what was paid for. As mentioned above, Ena itself was built because I found myself wanting specific features that weren't available in existing tools without a fee.

The core feature of Ena is to take Credit Card bill statements from major Financial Institutes in Canada and turning them into CSV files to be used with Google Sheets or Dime (iOS) to better visualize your monthly spendings.

The second core feature is Ena's ability to query a local custom LLM to categorize transactions into pre-set categories (defined in `src/model:Category`) so users have a better idea of what they're spending on. Currently, the local LLM model is based off Meta's Llama3, and its model is defined at `src/llm/Modelfile`. It has been instructed to only categorize a transaction if its at least 90% confident (0.9). While not perfect, it serves as a nice starting point for most users.

> [!NOTE]
> Due to how local LLMs work via Ollama, the first time this script is ran, it will take significantly longer (60+ seconds on my 7800XT).
> This is primarily because Ollama has to load the model into memory before any requests can be made towards the model. By default, the model
> stays in memory for 5 minutes. If possible, load the model beforehand, although that just kicks the problem to a different stage. Wait times
> can vary depending on your machine.

An option is also included, if preferred, to manually categorize transactions that have been categorized into the catch-all category of Expense. If this option is enabled, every time a transaction is categorized into the generic category, the console will prompt the user to type in a valid category before moving onto the next transaction. This gives some control back to the user. At this point, no training is done to the LLM as that is a bit out of my scope.

## Usage
Two scripts are provided, the first of which, `Ena.py`, is the one to use to process statement PDFs into CSVs. The second one, `Preferences.py`, is used to configure `preferences.ini` for individual users to determine Ena's overall behaviour.

Before continuing, make sure you're on Python3 and installed all required dependencies with
```bash
pip install -r requirements.txt
```

### Preferences
`preferences.ini` is an untracked file, which has the following:

```ini
[Preferences]
csv_order = DEFAULT
use_llm = no
positive_expenses = no
```

You do not need to create this file manually, and can run `Preferences.py` to generate it. If `preferences.ini` is not found upon running Ena, the default version will be generated for you.

To generate `preferences.ini` for a user that would like the `DEFAULT` order without using LLM for categorization and keeping expenses as negative would be:
```bash
./Preferences.py --csv-order DEFAULT
```

To generate one that would use LLM and representing expenses as positive numbers would be :
```bash
./Preferences.py --csv-order DEFAULT --use-llm --positive-expenses
```

#### Options for Preferences
Below you'll find more details about the options and flags `Preferences.py` can be ran with.

##### CSV Order
In the output CSV, the order of columns is an important distinction so that users can know exactly what data they're dealing with. Ena can order the columns to best fit your needs.

This feature is represented by the `csv_order` flag, and there are three options to choose from currently, defaulting to `SIMPLE`.

```
1. DEFAULT - [date, amount, note, category]
2. SIMPLE - [date, amount, note, category]
3. DIME - [category, note, date, amount]
```

`DEFAULT` and `SIMPLE` are quite self-explanatory; `DIME` is the order in which the iOS app expects and prompts the user for the column names, and it's easier to simply click next 4 times in a row withing moving anything around, a real lazy approach to it if you will.

##### Categories
By default, Ena will only categorize transactions into two categories - expenses and income. This behaviour can be configured to instead use a local custom LLM via Ollama to categorize transactions. This will allow Ena to automatically categorize transactions without manual user input.

This feature is represented by the `use_llm` flag, and by default, is set to False (no).

##### Expenses as Positive or Negative numbers
Depending on what method of madness you approach finances, you may want to represent expenses as negative or positive numbers. This can be helpful if you're expecting the numbers output by Ena to be negative or positive.

Part of the motivation behind this flag was because I often think of expenses as a negative number, well, since it's an expense. But, statements often represent it as a positive number, while payments or refunds are represented as negative numbers.

This feature is represented by the `positive_expenses` flag, and by default, is set to False (no). This means that expenses by default are represented by negative numbers.

### Ena
Once you've ran `Preferences.py` (or don't and let Ena create it from default), you can now use Ena. Ena itself only has two options, being the directory where to find statements and logging level.

To run Ena:
1. Download statements and place them in corresponding folders, creating subdirectories for individual Financial Institutes if needed.
    ```
    └── statements
        └── BNS
            ├── .gitkeep
            ├── statement_1.pdf
            ├── statement_2.pdf
            └── ...statement_x.pdf
        └── RBC
            ├── .gitkeep
            ├── statement_1.pdf
            ├── statement_2.pdf
            └── ...statement_x.pdf
    ```
2. Run Ena
    ```bash
    ./Ena.py
    ```

    Feel free to run it with the `verbose` flag to see more of what's happening.
3. If everything went well, then you'll find CSVs under the `output` folder with the following structure
    ```
    └── output
        └── BNS
            ├── .gitkeep
            └── 1718254777.csv
        └── RBC
            ├── .gitkeep
            └── 1718254777.csv
    ```

#### Options for Ena
Below you'll find more details about the flags and options Ena can be ran with.

##### Directory
In this repo, you'll find two pre-set directories for which Ena defaults to act upon - `statements` and `output`, which both have first level subdirectories corresponding to individual Financial Institutes. By default, Ena will look at `statements` to glob statements and process, before creating CSV files in `output`.

If there are statements under `statements/RBC` then a single CSV will be created in `output/RBC`, containing transactions found in all statements. Thus, it is recommended to run Ena as frequently as possible (with the highest being monthly) to reduce the chance of bugs.

If you wish to change the directory that Ena looks for statements in, you can do so.

##### Logging
Ena uses Python's `logging` module to handle outputs to the console, and by default, will set logging level to `WARNING`. However, if verbose mode is enabled via `-v, --verbose`, Ena will log at the `INFO` level for this particular run.

Verbose logging at the `INFO` level is useful during debugging or attempting to add new Financial Institutes. It is not advised to use verbose mode for general usage as it spits out a lot of information that is not needed.

##### Manual Review
As mentioned above in features, categorization via local LLM inference isn't perfect. Thus, in the case that a user wishes to manually review transactions that the LLM could not categorize due to low confidence, this flag is provided.

If specified via the `-m, --manual-review` flag when running Ena, then for every transaction that has been categorized as the catch-all category of Expense (Category.EXPENSE), the terminal will prompt the user to manually categorize the transaction. For this, the user must type exactly the category they want to categorize this transaction as.

## Goals and WIP
The following Financial Insitutes are a WIP as I do not have access to them atm.
* BNS
* TD

Another feature I have in mind has to do with recurring expenses, such as Rent, Mortgage, Utilities, etc. In Canada, some of those things are not payable via Credit Card, and thus cannot be tracked by Ena. However, they should be around the same every month, and so, can be included via another option for `Ena.py`. Current approach is to include another file to be looked at by Ena, which include utilities.

As the basis of this fork comes from Teller (noted above), some of the code isn't exactly what I need to for my purposes. Thus, a refactor of the processor code is planned for the future.

While a long shot, it would be interested for me to personally learn how to properly generate and train the LLM to properly categorize transactions based on the data generated via the manual review processing. At this point, this is not within the scope of this project and not something I'm actively working towards.

At this moment, supporting online models like OpenAI, Google, xAI (Grok), etc, is not within the pipelines. It is not within the scope of this project as I do not have access to the APIs of these models, and I do not wish to pay to access those APIs. If you wish to use an online API you have access to, feel free to extract the prompt from `src/llm/Modelfile` and modify `src/llm/api.py` to communicate with the online model of your choice!

## Contributing
If you wish to add support for a Financial Insitute of your own choice, feel free to do so! Whether that's by creating a PR or forking is up to you!

The general process of adding support would:
1. Download statements
2. Create corresponding directory under `statements` and `output`, with their own `.gitkeep` files.
3. Copy the regex statements and create a new class that inherits from `src/model.py:BaseFI`

    Ex. If you're adding BMO, you'll create something like the following:

    ```python
    @dataclass
    class Transaction()
        ...

    class BaseFI(ABC)
        ...

    class BMO(BaseFI):
        def __init__(self):
            # Call super's init with regex dictionary'
            ...

        def is_transaction_income(self, transaction: Transaction, positive_expenses: bool) -> bool:
            # This function will change per FI to determine if a transaction is considered Income
            # rather than Expense.
            ...
    ```

4. Run it with verbose mode
5. You'll most likely see a warning to the degree of

    ```
    Discrepancy found, bad parse :(. Not all transcations are accounted for, validate your transaction regex
    ```

    That's OK! Grab what was logged to the console and play around with the regex until you get what you need. That includes:
    1. Transaction date, amount, and description
    2. Account starting balance (Most likely how much payment last statement needed)
    3. Account closing balance (Most likely how much payment this statement needs)
6. Update the regex under
7. Run it again
8. If no errors and correct CSV is generated, that's it! Otherwise, repeat steps 4 - 7 until it's done.
