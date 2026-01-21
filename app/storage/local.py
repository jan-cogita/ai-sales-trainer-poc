"""Local filesystem storage backend."""

from pathlib import Path

from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Store files on local filesystem."""

    def __init__(self, base_path: str = "./data/documents"):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to base path, preventing directory traversal."""
        # Resolve to absolute path and ensure it's within base_path
        resolved = (self.base_path / path).resolve()
        if not str(resolved).startswith(str(self.base_path)):
            raise ValueError(f"Path traversal attempt detected: {path}")
        return resolved

    async def save(self, path: str, content: bytes) -> str:
        """Save content to local filesystem."""
        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return str(full_path)

    async def load(self, path: str) -> bytes:
        """Load content from local filesystem."""
        full_path = self._resolve_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return full_path.read_bytes()

    async def delete(self, path: str) -> None:
        """Delete file from local filesystem."""
        full_path = self._resolve_path(path)
        if full_path.exists():
            full_path.unlink()

    async def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        return self._resolve_path(path).exists()

    async def list_files(self, prefix: str = "") -> list[str]:
        """List files in local filesystem."""
        search_path = self._resolve_path(prefix) if prefix else self.base_path
        if not search_path.exists():
            return []

        if search_path.is_file():
            return [prefix]

        files = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(self.base_path)
                files.append(str(relative))
        return files
