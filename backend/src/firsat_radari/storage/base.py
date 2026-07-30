from abc import ABC, abstractmethod


class ObjectStore(ABC):
    @abstractmethod
    def put_if_absent(self, key: str, content: bytes) -> bool:
        """Store immutable content and return True only when a new object is written."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Read an object by its relative key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether an object exists."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete an object and return True only when it existed."""
