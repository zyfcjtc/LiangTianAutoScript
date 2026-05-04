from core.template import Button, match
from core.ui import UI
from tasks.base import Task

PATHFIND = Button(
    "main.BTN_PATHFIND",
    "main/BTN_PATHFIND.png",
    search_area=(635, 643, 717, 735),
)
PORRIDGE_IN_MENU = Button(
    "pathfind.BTN_ZHOUPENG",
    "pathfind/BTN_ZHOUPENG.png",
    search_area=(454, 198, 660, 524),
)
COLLECT = Button(
    "porridge.BTN_COLLECT",
    "main/BTN_PORRIDGE.png",
    search_area=(193, 469, 284, 547),
)

CLICK_TIMES = 15
CLICK_INTERVAL = 0.4


class PorridgeTask(Task):
    def run(self, ui: UI) -> None:
        if not ui.click(PATHFIND):
            return
        ui.device.sleep(0.8)

        if not ui.click(PORRIDGE_IN_MENU):
            return

        if not ui.wait_until(COLLECT, timeout=8.0):
            return

        point = match(ui.device.screenshot(), COLLECT)
        if point is None:
            return
        for i in range(1, CLICK_TIMES + 1):
            ui.device.click(*point)
            ui.device.sleep(CLICK_INTERVAL)
