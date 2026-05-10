import time
from collections import deque
from dataclasses import dataclass, field

from core.device import Device
from core.logger import logger
from core.ocr import find_text
from core.template import Button, appear, match


@dataclass
class Page:
    name: str
    check: Button
    links: dict[str, Button] = field(default_factory=dict)


class UI:
    def __init__(self, device: Device, pages: list[Page]):
        self.device = device
        self.pages = {p.name: p for p in pages}

    def current_page(self) -> Page | None:
        screen = self.device.screenshot()
        for page in self.pages.values():
            if appear(screen, page.check):
                return page
        return None

    def wait_until(self, button: Button, timeout: float = 10.0, interval: float = 0.5) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if appear(self.device.screenshot(), button):
                return True
            time.sleep(interval)
        return False

    def click(self, button: Button, timeout: float = 5.0, interval: float = 0.5) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            point = match(self.device.screenshot(), button)
            if point:
                self.device.click(*point)
                logger.info(f"Click {button.name} @ {point}")
                return True
            time.sleep(interval)
        logger.warning(f"Not found: {button.name}")
        return False

    def click_text(
        self,
        text: str,
        search_area: tuple | None = None,
        timeout: float = 5.0,
        interval: float = 0.5,
        threshold: float = 0.5,
    ) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            point = find_text(self.device.screenshot(), text,
                              search_area=search_area, threshold=threshold)
            if point:
                self.device.click(*point)
                logger.info(f"Click text={text!r} @ {point}")
                return True
            time.sleep(interval)
        logger.warning(f"Not found text: {text!r}")
        return False

    def goto(self, target: str, max_steps: int = 6) -> bool:
        for _ in range(max_steps):
            current = self.current_page()
            if current is None:
                logger.warning("Unknown page")
                return False
            if current.name == target:
                return True
            path = self._bfs(current.name, target)
            if not path or len(path) < 2:
                logger.warning(f"No path: {current.name} -> {target}")
                return False
            nxt = path[1]
            self.click(current.links[nxt])
            self.wait_until(self.pages[nxt].check)
        return False

    def _bfs(self, start: str, target: str) -> list[str] | None:
        q = deque([[start]])
        seen = {start}
        while q:
            path = q.popleft()
            node = path[-1]
            if node == target:
                return path
            for nb in self.pages[node].links:
                if nb not in seen:
                    seen.add(nb)
                    q.append(path + [nb])
        return None
