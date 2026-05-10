from core.ui import UI
from tasks._common import PATHFIND
from tasks.base import Task

COLLECT_TAP = (238, 508)   # 招揽按钮固定坐标，无需模板匹配
ENTER_SLEEP = 2.0
CLICK_TIMES = 15
CLICK_INTERVAL = 0.4


class PorridgeTask(Task):
    def run(self, ui: UI) -> None:
        if not ui.click(PATHFIND):
            return
        ui.device.sleep(0.8)

        if not ui.click_text("粥棚", search_area=(454, 198, 660, 524)):
            return
        ui.device.sleep(ENTER_SLEEP)

        for _ in range(CLICK_TIMES):
            ui.device.click(*COLLECT_TAP)
            ui.device.sleep(CLICK_INTERVAL)
