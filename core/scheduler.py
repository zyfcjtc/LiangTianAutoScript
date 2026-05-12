import threading
import time
from datetime import datetime

from core.logger import logger
from core.ui import UI
from tasks.base import Task


class Scheduler:
    def __init__(
        self,
        ui: UI,
        tasks: list[Task],
        name: str = "default",
        serial: str = "",
        mumu_instance: int | None = None,
        package: str | None = None,
        auto_login: bool = False,
        run_once: bool = False,
    ):
        self.ui = ui
        self.tasks = tasks
        self.name = name
        self.serial = serial
        self.mumu_instance = mumu_instance
        self.package = package
        self.auto_login = auto_login
        self.run_once = run_once
        self.status: str = "starting"
        self.current_task: str | None = None
        self.next_task: str | None = None
        self.next_run_at: datetime | None = None
        self.last_error: str | None = None
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.thread: threading.Thread | None = None

    def stop(self) -> None:
        self.stop_event.set()
        self.wake_event.set()
        self.status = "stopping"

    def _refresh_next(self) -> None:
        if not self.tasks:
            self.next_task = None
            self.next_run_at = None
            return
        nxt = min(self.tasks, key=lambda t: t.next_run)
        self.next_task = nxt.name
        self.next_run_at = nxt.next_run

    def _run_task(self, task: Task) -> None:
        self.status = "running"
        self.current_task = task.name
        logger.info(f"Run: {task.name}")
        try:
            task.run(self.ui)
            self.last_error = None
        except Exception as e:
            logger.exception(f"Task failed: {task.name}")
            self.last_error = f"{task.name}: {e}"
        task.reschedule()
        self.current_task = None

    def loop(self) -> None:
        logger.info(f"Scheduler started: {[t.name for t in self.tasks]}")
        self.status = "idle"

        if self.run_once:
            for task in self.tasks:
                if self.stop_event.is_set():
                    break
                self._run_task(task)
                self._refresh_next()
                self.stop_event.wait(timeout=5)
            logger.info(f"Run-once complete: {self.name}")
        else:
            while not self.stop_event.is_set():
                due = [t for t in self.tasks if t.due()]
                if due:
                    self._run_task(due[0])
                    self.status = "idle"
                    self._refresh_next()
                    self.stop_event.wait(timeout=5)
                    continue

                self._refresh_next()
                wait = max((self.next_run_at - datetime.now()).total_seconds(), 1) if self.next_run_at else 60
                logger.info(f"Idle, next: {self.next_task} in {int(wait)}s")
                self.wake_event.wait(timeout=min(wait, 60))
                self.wake_event.clear()

        self.status = "stopped"
        logger.info(f"Scheduler stopped")
