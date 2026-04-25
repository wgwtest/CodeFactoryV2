from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event, Thread

from app.archive_knowledge.service import ArchiveKnowledgeService
from app.tool_hub.runtime_models import RuntimeCycleRunResult


class ToolHubRuntimeWorker:
    def __init__(
        self,
        *,
        root: str | Path,
        archive_service: ArchiveKnowledgeService,
        seed_demo_data: bool = True,
        worker_id: str = "p4-runtime-worker",
        executor_tick_seconds: float = 0.1,
        simulation_profile_durations: dict[str, int | tuple[int, int]] | None = None,
    ) -> None:
        self.root = Path(root)
        self.archive_service = archive_service
        self.seed_demo_data = seed_demo_data
        self.worker_id = worker_id
        self.executor_tick_seconds = executor_tick_seconds
        self.simulation_profile_durations = simulation_profile_durations

    def run_once(self) -> RuntimeCycleRunResult:
        from app.tool_hub.service import ToolHubService

        service = ToolHubService(
            root=self.root,
            archive_service=self.archive_service,
            seed_demo_data=self.seed_demo_data,
            enable_background_executor=False,
            executor_tick_seconds=self.executor_tick_seconds,
            simulation_profile_durations=self.simulation_profile_durations,
            runtime_worker_id=self.worker_id,
        )
        return service.run_runtime_cycle()


class ToolHubRuntimeCoordinator:
    def __init__(
        self,
        worker_factory: Callable[[], ToolHubRuntimeWorker],
        interval_seconds: float,
    ) -> None:
        self.worker_factory = worker_factory
        self.interval_seconds = interval_seconds
        self._stop_event = Event()
        self._thread = Thread(target=self._run, name="tool-hub-runtime-coordinator", daemon=True)

    def start(self) -> None:
        if self._thread.is_alive():
            return
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        worker = self.worker_factory()
        while not self._stop_event.is_set():
            try:
                worker.run_once()
            except Exception:
                pass
            self._stop_event.wait(self.interval_seconds)
