from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, path: str, content: bytes) -> str:
        """Save content to storage. Returns the storage path."""
        pass

    @abstractmethod
    async def load(self, path: str) -> bytes:
        """Load content from storage."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete content from storage."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if path exists in storage."""
        pass

    @abstractmethod
    async def list_files(self, prefix: str = "") -> list[str]:
        """List files in storage with optional prefix filter."""
        pass
