import re
from enum import Enum
from typing import Dict
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod


class Category(Enum):
    RECURRING = "Recurring"
    GROCERIES = "Groceries"
    DINING = "Dining"
    ENTERTAINMENT = "Entertainment"
    MISC = "Misc"
    NONE = "N/A"


@dataclass
class Transaction:
    date: datetime
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


class BaseFI(ABC):
    def __init__(self, name: str, regex: Dict):
        self.name = name

    @abstractmethod
    def get_year(self):
        raise NotImplementedError
