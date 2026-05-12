from core.logger import logger
from core.ui import UI
from tasks.base import Task

PATHFIND_SLEEP = 0.8
ENTER_SLEEP = 1.5
PRE_SWIPE_SLEEP = 2.0
SWIPE_SLEEP = 0.8
PRE_CLICK_SLEEP = 1.0

RESET_SWIPES = 2
RESET_SWIPE = (120, 640, 600, 640)

SWIPE_PASSES: list[tuple | None] = [
    None,
    (600, 640, 360, 640),   # right ~240px
    (600, 640, 420, 640),   # right ~180px
]
SWIPE_DURATION_MS = 400

# 每个 pass 下收集按钮的固定屏幕坐标（标定自 calibrate_jianmuying.py）
FIXED_CLICKS: list[list[tuple[int, int]]] = [
    [(278, 721), (401, 780), (522, 843), (465, 630), (589, 690)],  # pass 0
    [(481, 752), (415, 539), (543, 599)],  # pass 1
    [(485, 657), (424, 443), (548, 507), (674, 573)],  # pass 2
]


class JianmuyingTask(Task):
    def run(self, ui: UI) -> None:
        if not ui.click_text("寻路", search_area=(600, 700, 720, 830), timeout=15.0):
            return
        ui.device.sleep(PATHFIND_SLEEP)

        if not ui.click_text("建木营", search_area=(200, 450, 570, 850)):
            return
        ui.device.sleep(ENTER_SLEEP)

        for _ in range(RESET_SWIPES):
            ui.device.swipe(*RESET_SWIPE, SWIPE_DURATION_MS)
            ui.device.sleep(SWIPE_SLEEP)

        total = 0
        for i, (swipe, pts) in enumerate(zip(SWIPE_PASSES, FIXED_CLICKS)):
            if swipe is not None:
                ui.device.sleep(PRE_SWIPE_SLEEP)
                ui.device.swipe(*swipe, SWIPE_DURATION_MS)
                ui.device.sleep(SWIPE_SLEEP)

            for pt in pts:
                logger.debug(f"建木营 pass{i}: 点击 @ {pt}")
                ui.device.sleep(PRE_CLICK_SLEEP)
                ui.device.click(*pt)
                total += 1

        logger.info(f"建木营: 共点击 {total} 个")
