from core.template import Button
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

COLLECT_TAP = (238, 508)   # 招揽按钮固定坐标，无需模板匹配
ENTER_SLEEP = 2.0
CLICK_TIMES = 15
CLICK_INTERVAL = 0.4


class PorridgeTask(Task):
    def run(self, ui: UI) -> None:
        if not ui.click(PATHFIND):
            return
        ui.device.sleep(0.8)

        if not ui.click(PORRIDGE_IN_MENU):
            return
        ui.device.sleep(ENTER_SLEEP)

        for _ in range(CLICK_TIMES):
            ui.device.click(*COLLECT_TAP)
            ui.device.sleep(CLICK_INTERVAL)
