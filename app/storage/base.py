"""Abstract base storage interface."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TypeVar, Generic

T = TypeVar("T")


class BaseStorage(ABC, Generic[T]):
    """Abstract storage interface for data persistence."""

    @abstractmethod
    def save(self, key: str, data: T) -> None:
        """Save data with the given key."""
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[T]:
        """Load data by key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data by key."""
        pass

    @abstractmethod
    def list_all(self) -> Dict[str, T]:
        """List all stored data."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all data."""
        pass
