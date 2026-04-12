from pathlib import Path
from uuid import uuid4


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, file_name: str) -> str:
        key = f"{uuid4()}-{file_name}"
        target = self.root / key
        target.write_bytes(content)
        return key

    def resolve(self, storage_key: str) -> Path:
        return self.root / storage_key
