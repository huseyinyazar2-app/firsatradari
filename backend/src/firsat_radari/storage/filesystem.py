import os
import tempfile
from pathlib import Path, PurePosixPath

from firsat_radari.storage.base import ObjectStore


class FileObjectStore(ObjectStore):
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put_if_absent(self, key: str, content: bytes) -> bool:
        target = self._resolve_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return False

        descriptor, temporary_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=".write-",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(content)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            if target.exists():
                return False
            os.replace(temporary_path, target)
            return True
        finally:
            temporary_path.unlink(missing_ok=True)

    def read(self, key: str) -> bytes:
        return self._resolve_key(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve_key(key).is_file()

    def delete(self, key: str) -> bool:
        target = self._resolve_key(key)
        if not target.is_file():
            return False
        target.unlink()
        return True

    def _resolve_key(self, key: str) -> Path:
        relative = PurePosixPath(key)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError("Object key must be a safe relative path")

        target = self._root.joinpath(*relative.parts).resolve()
        if target == self._root or self._root not in target.parents:
            raise ValueError("Object key escapes storage root")
        return target
