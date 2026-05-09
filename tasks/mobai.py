import time

from core.logger import logger
from core.ocr import scan_texts
from core.template import Button
from core.ui import UI
from tasks.base import Task

# 头像图每个账号不同，用固定坐标点击（区域中心）
AVATAR_TAP = (67, 149)

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

# OCR 识别 tab 文字，不依赖模板颜色
KUAFU_TAB_TEXTS  = ["县邑评分", "戎车评分", "税收"]
PAIHANG_TAB_TEXTS = ["县邑评分", "税收", "演武场"]
TAB_AREA   = (280, 1120, 680, 1215)  # 覆盖所有 tab 的搜索区
MOBAI_AREA = (257, 1021, 447, 1108)  # 膜拜/已膜拜 按钮区

SLEEP = 1.5


class MobaiTask(Task):
    def run(self, ui: UI) -> None:
        ui.device.click(*AVATAR_TAP)
        ui.device.sleep(SLEEP)

        if not ui.click_text("跨服榜", search_area=(459, 1189, 545, 1285)):
            return
        ui.device.sleep(SLEEP)
        self._do_ranking(ui, KUAFU_TAB_TEXTS)

        if not ui.click_text("排行榜", search_area=(545, 1192, 630, 1282)):
            return
        ui.device.sleep(SLEEP)
        self._do_ranking(ui, PAIHANG_TAB_TEXTS)

        if ui.click(BTN_FENGLU):
            ui.device.sleep(2.0)
            ui.click(BTN_CLICKOFF)
            ui.device.sleep(SLEEP)

        ui.click(BTN_PROFILE_CLOSE)

    def _do_ranking(self, ui: UI, tab_texts: list[str]) -> None:
        popup = False
        for i, text in enumerate(tab_texts):
            # 第一个 tab 打开时已默认选中，不需要点击
            popup = self._mobai_tab(ui, text, dismiss_first=popup, click_tab=(i > 0))
        if popup:
            ui.click(BTN_BACK)
            ui.device.sleep(SLEEP)
        ui.click(BTN_BACK)
        ui.device.sleep(SLEEP)

    def _mobai_tab(self, ui: UI, tab_text: str, dismiss_first: bool, click_tab: bool = True) -> bool:
        if dismiss_first:
            ui.click_text(tab_text, search_area=TAB_AREA)
            ui.device.sleep(SLEEP)
        if click_tab:
            ui.click_text(tab_text, search_area=TAB_AREA)
            ui.device.sleep(SLEEP)

        end = time.time() + 15
        while time.time() < end:
            hits = scan_texts(ui.device.screenshot(), search_area=MOBAI_AREA)
            # 先判断"已膜拜"（包含"膜拜"子串，需优先检查）
            done_pt = next((pt for t, pt in hits if "已膜拜" in t), None)
            if done_pt is not None:
                logger.info(f"  {tab_text}: 已膜拜过，跳过")
                return False
            mobai_pt = next((pt for t, pt in hits if "膜拜" in t), None)
            if mobai_pt is not None:
                ui.device.click(*mobai_pt)
                ui.device.sleep(SLEEP)
                return True
            logger.info(f"  {tab_text}: 膜拜按钮未出现，等待重试…")
            ui.device.sleep(1)

        logger.warning(f"  {tab_text}: 等待超时，膜拜按钮始终未找到")
        return False
