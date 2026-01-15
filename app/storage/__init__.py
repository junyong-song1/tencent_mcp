"""Data storage module."""
from .base import BaseStorage
from .json_storage import JSONStorage

__all__ = ["BaseStorage", "JSONStorage"]
