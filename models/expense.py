"""Pydantic model for Expense data"""
from pydantic import BaseModel
from datetime import date
from typing import Literal, Optional

class Expense(BaseModel):
    """
    Represents a single expense or income transaction.
    """
    id: Optional[str] = None # MongoDB ID
    date: date # Restored type
    description: str
    value: float # Restored type
    in_out: Literal['in', 'out'] # Restored type

    class Config:
        populate_by_name = True # Allows using '_id' in Python and 'id' in MongoDB
        from_attributes = True # Replaced orm_mode for Pydantic V2
        # Removed json_schema_extra for simplification 