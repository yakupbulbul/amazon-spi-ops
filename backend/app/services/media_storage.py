from __future__ import annotations

from pathlib import Path
import uuid

from app.core.config import settings


class MediaStorageService:
    def __init__(self, root: Path | None = None, url_prefix: str | None = None) -> None:
        self.root = root or settings.media_root
        self.url_prefix = (url_prefix or settings.media_url_prefix).rstrip("/")

    def ensure_directories(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "aplus-assets").mkdir(parents=True, exist_ok=True)

    def store_bytes(self, *, subdirectory: str, suffix: str, content: bytes) -> tuple[Path, str]:
        target_dir = self.root / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid.uuid4().hex}{suffix}"
        file_path = target_dir / file_name
        file_path.write_bytes(content)
        public_url = f"{self.url_prefix}/{subdirectory}/{file_name}"
        return file_path, public_url

    def resolve_public_url(self, public_url: str) -> Path:
        relative_path = public_url.removeprefix(f"{self.url_prefix}/")
        resolved_path = (self.root / relative_path).resolve()
        root_path = self.root.resolve()
        if root_path not in resolved_path.parents and resolved_path != root_path:
            raise ValueError("Resolved media path is outside the configured storage root.")
        return resolved_path
