"""真实浏览器验收：打开页面 → 截图 → 改售价 → 点「计算」→ 结果应随之变化。

依赖 playwright（使用系统已装的 Chrome，不下载额外浏览器）。
运行：python scripts/ui_check.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculator import CASES, calculate, money, pct  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("APP_URL", "http://localhost:8501")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=2)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("text=测算结果", timeout=30000)
        page.wait_for_timeout(2000)

        default_cards = page.locator(".kpi-row").inner_text()
        print("默认（手机壳）卡片内容：\n", default_cards)
        page.screenshot(path=str(ROOT / "preview.png"), full_page=True)

        # 改售价 -> 点计算 -> 结果应更新
        price_input = page.locator("input[type=number]").nth(3)
        price_input.fill("12.5")
        page.get_by_role("button", name="计算").click()
        page.wait_for_timeout(1500)

        new_cards = page.locator(".kpi-row").inner_text()
        print("改售价 $12.5 后卡片内容：\n", new_cards)

        expect = calculate(**{**CASES["手机壳"], "price_usd": 12.5})
        assert money(expect.gross_cny) in new_cards, f"毛利 {money(expect.gross_cny)} 未出现在卡片里"
        assert pct(expect.margin) in new_cards, f"毛利率 {pct(expect.margin)} 未出现在卡片里"
        print(f"真实浏览器验收通过：$12.5 时毛利 {money(expect.gross_cny)} / 毛利率 {pct(expect.margin)} 与算式一致")

        page.screenshot(path=str(ROOT / "preview_after.png"), full_page=True)

        # 底部说明区：先滚到底再截一张，并检查关键段落是否都在
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(ROOT / "preview_bottom.png"))
        body = page.inner_text("body")
        for keyword in (
            "帮助大学生理解跨境电商成本的模拟计算器，不是专业报价工具",
            "这个计算器怎么算的",
            "盈亏平衡售价",
            "为什么值得算一遍",
            "假设与局限",
            "不是专业报价工具",
        ):
            assert keyword in body, f"页面缺少：{keyword}"
        print("说明区关键词齐全（口径 / 为什么 / 假设与局限 / 免责）")
        browser.close()


if __name__ == "__main__":
    main()
