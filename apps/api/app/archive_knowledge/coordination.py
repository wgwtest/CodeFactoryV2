from __future__ import annotations

from threading import Lock


class ArchiveExtractionCoordinator:
    def __init__(self) -> None:
        self._lock = Lock()
        self.current_archive_id: str | None = None

    def try_start(self, archive_id: str) -> bool:
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            return False
        self.current_archive_id = archive_id
        return True

    def finish(self, archive_id: str) -> None:
        if self.current_archive_id != archive_id:
            return
        self.current_archive_id = None
        self._lock.release()


coordinator = ArchiveExtractionCoordinator()
