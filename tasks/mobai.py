from core.logger import logger
from core.template import Button, match
from core.ui import UI
from tasks.base import Task

# 头像图每个账号不同，用固定坐标点击（区域中心）
AVATAR_TAP = (67, 149)

BTN_KUAFU = Button(
    "profile.BTN_KUAFU", "profile/BTN_KUAFU.png",
    search_area=(459, 1189, 545, 1285),
)
BTN_PAIHANG = Button(
    "profile.BTN_PAIHANG", "profile/BTN_PAIHANG.png",
    search_area=(545, 1192, 630, 1282),
)
BTN_MOBAI = Button(
    "rank.BTN_MOBAI", "rank/BTN_MOBAI.png",
    search_area=(257, 1021, 447, 1108),
)
BTN_MOBAI_DONE = Button(
    "rank.BTN_MOBAI_DONE", "rank/BTN_MOBAI_DONE.png",
    search_area=(279, 1026, 438, 1112),
)
BTN_BACK = Button(
    "common.BTN_BACK", "common/BTN_BACK.png",
    search_area=(613, 126, 705, 206),
)
BTN_FENGLU = Button(
    "profile.BTN_FENGLU", "profile/BTN_FENGLU.png",
    search_area=(72, 795, 253, 907),
)
BTN_CLICKOFF = Button(
    "profile.BTN_CLICKOFF", "profile/BTN_CLICKOFF.png",
    search_area=(77, 97, 354, 283),
)
BTN_PROFILE_CLOSE = Button(
    "profile.BTN_CLOSE", "profile/BTN_CLOSE.png",
    search_area=(5, 1180, 105, 1279),
)

KUAFU_TABS = [
    Button("rank.TAB_KUAFU_XIANYI", "rank/TAB_1.png", search_area=(294, 1125, 420, 1210)),
    Button("rank.TAB_KUAFU_RONGCHE", "rank/TAB_2.png", search_area=(422, 1123, 548, 1203)),
    Button("rank.TAB_KUAFU_SHUISHOU", "rank/TAB_3.png", search_area=(556, 1126, 674, 1200)),
]
PAIHANG_TABS = [
    Button("rank.TAB_PAIHANG_XIANYI", "rank/TAB_PAIHANG_1.png", search_area=(298, 1125, 423, 1209)),
    Button("rank.TAB_PAIHANG_SHUISHOU", "rank/TAB_PAIHANG_2.png", search_area=(420, 1120, 548, 1203)),
    Button("rank.TAB_PAIHANG_YANWU", "rank/TAB_PAIHANG_3.png", search_area=(551, 1123, 676, 1199)),
]

SLEEP = 1.5


class MobaiTask(Task):
    def run(self, ui: UI) -> None:
        ui.device.click(*AVATAR_TAP)
        ui.device.sleep(SLEEP)

        if not ui.click(BTN_KUAFU):
            return
        ui.device.sleep(SLEEP)
        self._do_ranking(ui, KUAFU_TABS)

        if not ui.click(BTN_PAIHANG):
            return
        ui.device.sleep(SLEEP)
        self._do_ranking(ui, PAIHANG_TABS)

        if ui.click(BTN_FENGLU):
            ui.device.sleep(2.0)
            ui.click(BTN_CLICKOFF)
            ui.device.sleep(SLEEP)

        ui.click(BTN_PROFILE_CLOSE)

    def _do_ranking(self, ui: UI, tabs: list[Button]) -> None:
        popup = False
        for tab in tabs:
            popup = self._mobai_tab(ui, tab, dismiss_first=popup)
        if popup:
            ui.click(BTN_BACK)
            ui.device.sleep(SLEEP)
        ui.click(BTN_BACK)
        ui.device.sleep(SLEEP)

    def _mobai_tab(self, ui: UI, tab: Button, dismiss_first: bool) -> bool:
        if dismiss_first:
            ui.click(tab)
            ui.device.sleep(SLEEP)
        ui.click(tab)
        ui.device.sleep(SLEEP)

        timeout = 15
        elapsed = 0
        while elapsed < timeout:
            screen = ui.device.screenshot()
            if match(screen, BTN_MOBAI_DONE):
                logger.info(f"  {tab.name}: 已膜拜过，跳过")
                return False
            point = match(screen, BTN_MOBAI)
            if point is not None:
                ui.device.click(*point)
                ui.device.sleep(SLEEP)
                return True
            logger.info(f"  {tab.name}: 膜拜按钮未出现，等待重试…")
            ui.device.sleep(1)
            elapsed += 1

        logger.warning(f"  {tab.name}: 等待超时，膜拜按钮始终未找到")
        return False
