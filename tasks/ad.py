import time

from core.logger import logger
from core.ocr import find_text, scan_texts
from core.ui import UI
from tasks.base import Task

# ── 商城入口 ─────────────────────────────────────────────
MALL_ENTRY_AREA  = (0, 260, 200, 310)    # 主界面「商城」@ (51, 283)

# ── 底部 nav ─────────────────────────────────────────────
BOTTOM_NAV_AREA  = (0, 1230, 720, 1280)
NAV_SWIPE_LEFT   = (600, 1250, 120, 1250)  # 手指左划 → 显示右侧 tab（找「爵位」用）
NAV_SWIPE_RIGHT  = (120, 1250, 600, 1250)
SWIPE_MS         = 400

# ── 爵位内顶部 sub-tab ────────────────────────────────────
TOP_NAV_AREA     = (0, 395, 720, 435)    # 招贤直购 @ (264,412)  元宝直购 @ (399,412)

# ── 商品卡片区 ────────────────────────────────────────────
CARD_AREA        = (50, 480, 680, 1200)  # 扫「免费」「售罄」

# ── 弹窗 ─────────────────────────────────────────────────
DIALOG_AD_AREA   = (300, 790, 680, 870)  # 「观看广告」按钮 @ (490, 822)
POPUP_DISMISS_PT = (650, 200)            # 弹窗外空白，点击关闭奖励弹窗

# ── 退出 ─────────────────────────────────────────────────
PRIVILEGE_ENTRY_AREA = (260, 260, 380, 310)

EXIT_PT          = (55, 1210)

# ── 时序 ─────────────────────────────────────────────────
SLEEP_NAV      = 1.5
SLEEP_CLAIM    = 1.5
SLEEP_AD       = 2.0
SAFETY_TIMEOUT = 60


class AdTask(Task):
    def run(self, ui: UI) -> None:
        if not ui.click_text("商城", search_area=MALL_ENTRY_AREA):
            logger.warning("商城入口未找到"); return
        ui.device.sleep(SLEEP_NAV)

        totals: dict[str, int] = {}

        for tab in ("赛季物资", "每日物资"):
            if self._goto_bottom_tab(ui, tab):
                totals[tab] = self._claim_free_loop(ui, area=CARD_AREA, with_ad=False)

        if self._goto_bottom_tab(ui, "爵位", exact=True):
            for top_tab in ("招贤直购", "元宝直购"):
                if ui.click_text(top_tab, search_area=TOP_NAV_AREA):
                    ui.device.sleep(SLEEP_NAV)
                    totals[top_tab] = self._claim_free_loop(ui, area=CARD_AREA, with_ad=True)

        ui.device.click(*EXIT_PT)
        ui.device.sleep(SLEEP_NAV)

        if ui.click_text("特权", search_area=PRIVILEGE_ENTRY_AREA):
            ui.device.sleep(SLEEP_NAV)
            if self._goto_bottom_tab(ui, "观影金扇"):
                totals["观影金扇"] = self._claim_free_loop(ui, area=CARD_AREA, with_ad=True)
            ui.device.click(*EXIT_PT)

        summary = "  ".join(f"{tab}:{n}" for tab, n in totals.items())
        logger.info(f"看广告完成 — {summary}  合计:{sum(totals.values())}")

    def _goto_bottom_tab(self, ui: UI, tab_text: str, max_swipes: int = 3, exact: bool = False) -> bool:
        def _find(screen):
            if exact:
                hits = scan_texts(screen, search_area=BOTTOM_NAV_AREA)
                matches = [pt for t, pt in hits if t == tab_text]
                return matches[0] if matches else None
            return find_text(screen, tab_text, search_area=BOTTOM_NAV_AREA)

        pt = _find(ui.device.screenshot())
        if pt:
            ui.device.click(*pt); ui.device.sleep(SLEEP_NAV); return True

        for _ in range(max_swipes):
            ui.device.swipe(*NAV_SWIPE_LEFT, SWIPE_MS); ui.device.sleep(0.6)
            pt = _find(ui.device.screenshot())
            if pt:
                ui.device.click(*pt); ui.device.sleep(SLEEP_NAV); return True

        for _ in range(max_swipes * 2):
            ui.device.swipe(*NAV_SWIPE_RIGHT, SWIPE_MS); ui.device.sleep(0.6)
            pt = _find(ui.device.screenshot())
            if pt:
                ui.device.click(*pt); ui.device.sleep(SLEEP_NAV); return True

        logger.warning(f"底部 tab『{tab_text}』未找到")
        return False

    def _claim_free_loop(self, ui: UI, area: tuple, with_ad: bool) -> int:
        end = time.time() + SAFETY_TIMEOUT
        claimed = 0
        skipped: set[tuple[int, int]] = set()  # 已确认售罄的坐标

        while time.time() < end:
            hits = scan_texts(ui.device.screenshot(), search_area=area)
            free_pts = [pt for t, pt in hits if "免费" in t]
            free_pts = [fp for fp in free_pts
                        if not any(abs(fp[0] - sx) <= 15 and abs(fp[1] - sy) <= 15
                                   for sx, sy in skipped)]
            if not free_pts:
                return claimed

            pt = free_pts[0]
            ui.device.click(*pt)
            ui.device.sleep(SLEEP_CLAIM)

            # 扫全屏检查「已售罄」
            post = scan_texts(ui.device.screenshot())
            if any("已售罄" in t for t, _ in post):
                logger.debug(f"  已售罄，跳过 {pt}")
                skipped.add(pt)
                ui.device.click(*POPUP_DISMISS_PT)
                ui.device.sleep(0.5)
                continue

            if with_ad:
                if not ui.click_text("观看广告", search_area=DIALOG_AD_AREA, timeout=5.0):
                    # 弹窗里没有「观看广告」，视为已领取/售罄，跳过
                    logger.debug(f"  观看广告未出现，跳过 {pt}")
                    skipped.add(pt)
                    ui.device.click(*POPUP_DISMISS_PT)
                    ui.device.sleep(0.5)
                    continue
                ui.device.sleep(SLEEP_AD)
            ui.device.click(*POPUP_DISMISS_PT)
            ui.device.sleep(SLEEP_CLAIM)
            claimed += 1

        logger.warning(f"  超时退出，已领 {claimed} 个")
        return claimed
