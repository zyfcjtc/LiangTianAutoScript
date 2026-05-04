from datetime import datetime, timedelta

from core.ui import UI


class Task:
    def __init__(self, name: str, interval_minutes: int = 60):
        self.name = name
        self.interval_minutes = interval_minutes
        self.next_run = datetime.now()

    def due(self) -> bool:
        return datetime.now() >= self.next_run

    def reschedule(self) -> None:
        self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)

    def run(self, ui: UI) -> None:
        raise NotImplementedError
