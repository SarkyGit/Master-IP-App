from pydantic import BaseModel


class ColumnSelection(BaseModel):
    """List of selected column names for table preferences."""

    selected: list[str] = []
