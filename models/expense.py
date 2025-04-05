"""Pydantic model for Expense data"""
from pydantic import BaseModel
from datetime import date
from typing import Literal, Optional

class Expense(BaseModel):
    """
    Represents a single expense or income transaction.
    """
    id: Optional[str] = None
    date: date
    description: str
    value: float
    in_out: Literal['in', 'out']

    class Config:
        populate_by_name = True
        from_attributes = True 