import time
from datetime import datetime

from core.logger import logger
from core.ui import UI
from tasks.base import Task


class Scheduler:
    def __init__(self, ui: UI, tasks: list[Task], name: str = "default"):
        self.ui = ui
        self.tasks = tasks
        self.name = name
        self.status: str = "starting"
        self.current_task: str | None = None
        self.next_task: str | None = None
        self.next_run_at: datetime | None = None
        self.last_error: str | None = None

    def _refresh_next(self) -> None:
        if not self.tasks:
            self.next_task = None
            self.next_run_at = None
            return
        nxt = min(self.tasks, key=lambda t: t.next_run)
        self.next_task = nxt.name
        self.next_run_at = nxt.next_run

    def loop(self) -> None:
        logger.info(f"Scheduler started: {[t.name for t in self.tasks]}")
        self.status = "idle"
        while True:
            due = [t for t in self.tasks if t.due()]
            if due:
                task = due[0]
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
                self.status = "idle"
                self._refresh_next()
                continue

            self._refresh_next()
            wait = max((self.next_run_at - datetime.now()).total_seconds(), 1) if self.next_run_at else 60
            logger.info(f"Idle, next: {self.next_task} in {int(wait)}s")
            time.sleep(min(wait, 60))
