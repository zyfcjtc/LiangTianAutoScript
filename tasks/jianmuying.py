from core.logger import logger
from core.template import Button, match_all
from core.ui import UI
from tasks.base import Task

PATHFIND = Button(
    "main.BTN_PATHFIND",
    "main/BTN_PATHFIND.png",
    search_area=(635, 643, 717, 735),
)
# 建木营内图标（4 类，每类最多 3 个）
# 模板截的是静态建筑背景，点击时加偏移量指向左上角的收集图标
ICON_AREA = (0, 150, 720, 1200)
ICON_LIANGCAO = Button("jianmuying.ICON_LIANGCAO", "jianmuying/ICON_LIANGCAO.png", search_area=ICON_AREA, threshold=0.8)
ICON_MUCAI    = Button("jianmuying.ICON_MUCAI",    "jianmuying/ICON_MUCAI.png",    search_area=ICON_AREA, threshold=0.8)
ICON_JINKUANG = Button("jianmuying.ICON_JINKUANG", "jianmuying/ICON_JINKUANG.png", search_area=ICON_AREA, threshold=0.8)
ICON_JINGTIE  = Button("jianmuying.ICON_JINGTIE",  "jianmuying/ICON_JINGTIE.png",  search_area=ICON_AREA, threshold=0.8)
ICONS = [ICON_LIANGCAO, ICON_MUCAI, ICON_JINKUANG, ICON_JINGTIE]

# 建筑中心 → 收集图标中心的偏移量（需对每种建筑单独标定）
CLICK_OFFSET = (-56, -96)  # 建筑中心 → 左上角收集图标的偏移，四种建筑一致

ENTER_SLEEP = 1.5
PRE_SWIPE_SLEEP = 2.0   # 每次滑动前等待
SWIPE_SLEEP = 0.8       # 滑动后等视角稳定
PRE_CLICK_SLEEP = 2.0   # 每次点击前等待
SCAN_FRAMES = 1
SCAN_FRAME_INTERVAL = 0.4
DEDUP_DIST = 80

# 复位：进入后先往左划两次，回到地图起点
RESET_SWIPES = 2
RESET_SWIPE = (120, 640, 600, 640)   # 手指右划 → 视角左移

# 扫描：从起点出发，每次右移一个视角
SWIPE_PASSES: list[tuple | None] = [
    None,
    (600, 640, 120, 640),   # 右移 ~480px
    (600, 640, 240, 640),   # 再右移 ~360px
]
SWIPE_DURATION_MS = 400


class JianmuyingTask(Task):
    def run(self, ui: UI) -> None:
        if not ui.click(PATHFIND):
            return
        ui.device.sleep(0.8)

        if not ui.click_text("建木营", search_area=(200, 450, 570, 850)):
            return
        ui.device.sleep(ENTER_SLEEP)

        # 复位到地图起点
        for _ in range(RESET_SWIPES):
            ui.device.swipe(*RESET_SWIPE, SWIPE_DURATION_MS)
            ui.device.sleep(SWIPE_SLEEP)

        total = 0
        clicked: list[tuple[int, int]] = []   # 跨 pass 保留，防止重复点击
        for swipe in SWIPE_PASSES:
            if swipe is not None:
                ui.device.sleep(PRE_SWIPE_SLEEP)
                ui.device.swipe(*swipe, SWIPE_DURATION_MS)
                ui.device.sleep(SWIPE_SLEEP)
                # 滑动后图标在屏幕上的坐标平移，同步更新已点击列表
                dx = swipe[0] - swipe[2]
                clicked = [(x - dx, y) for x, y in clicked]

            for _ in range(SCAN_FRAMES):
                screen = ui.device.screenshot()
                for icon in ICONS:
                    try:
                        pts = match_all(screen, icon)
                    except FileNotFoundError as e:
                        logger.warning(f"建木营: 图标模板缺失 — {e}")
                        continue
                    ox, oy = CLICK_OFFSET
                    for pt in pts:
                        if not any(
                            abs(pt[0] - p[0]) < DEDUP_DIST and abs(pt[1] - p[1]) < DEDUP_DIST
                            for p in clicked
                        ):
                            clicked.append(pt)
                            click_pt = (pt[0] + ox, pt[1] + oy)
                            logger.info(f"建木营: 点击 {icon.name} @ {click_pt} (建筑={pt})")
                            ui.device.sleep(PRE_CLICK_SLEEP)
                            ui.device.click(*click_pt)
                            total += 1
                ui.device.sleep(SCAN_FRAME_INTERVAL)

        logger.info(f"建木营: 共点击 {total} 个图标")
