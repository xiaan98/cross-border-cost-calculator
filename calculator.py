"""跨境电商成本模型：纯计算逻辑，不依赖 Streamlit，便于单独测试。

只有一件事：把 7 个输入变成总成本、毛利、毛利率、盈亏平衡售价和一句风险提示。

口径（简化版，教学用）：
    售价折人民币 = 售价(USD) × 汇率
    国际运费     = 重量(kg) × 运费单价(元/kg)
    平台佣金     = 售价折人民币 × 佣金率
    关税         = 售价折人民币 × 关税税率        （简化：按售价计征）
    总成本       = 采购价 + 国际运费 + 平台佣金 + 关税
    毛利         = 售价折人民币 − 总成本
    毛利率       = 毛利 ÷ 售价折人民币
    盈亏平衡售价 = (采购价 + 国际运费) ÷ [汇率 × (1 − 佣金率 − 关税税率)]
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------- 示例案例
# 三个自编的教学案例（不抓数据）：小商品 + 跨境小包 + 平台佣金 12% + 简化关税 10%。
# 汇率按 7.15 计。
CASES: dict[str, dict[str, float]] = {
    "手机壳": {
        "purchase_price": 3.50,
        "weight_kg": 0.05,
        "freight_rate": 85.0,
        "price_usd": 6.99,
        "fx_rate": 7.15,
        "commission_pct": 12.0,
        "tariff_pct": 10.0,
    },
    "帆布袋": {
        "purchase_price": 12.00,
        "weight_kg": 0.18,
        "freight_rate": 85.0,
        "price_usd": 12.99,
        "fx_rate": 7.15,
        "commission_pct": 12.0,
        "tariff_pct": 10.0,
    },
    "小夜灯": {
        "purchase_price": 18.50,
        "weight_kg": 0.32,
        "freight_rate": 85.0,
        "price_usd": 15.99,
        "fx_rate": 7.15,
        "commission_pct": 12.0,
        "tariff_pct": 10.0,
    },
}

CASE_NOTES: dict[str, str] = {
    "手机壳": "轻、便宜、卖得起价：运费占比低，是典型的“高毛利小件”。",
    "帆布袋": "中等重量、单价不高：运费开始吃掉利润。",
    "小夜灯": "又重又要过认证类成本：运费占比最高，最接近“越卖越薄”。",
}


@dataclass
class Result:
    """一次测算的全部中间量和结论。"""

    purchase_price: float
    revenue_cny: float
    shipping_cny: float
    commission_cny: float
    tariff_cny: float
    total_cost_cny: float
    gross_cny: float
    margin: float
    breakeven_usd: float | None
    commission_threshold_pct: float
    price_usd: float
    commission_pct: float
    tariff_pct: float
    fx_rate: float
    weight_kg: float
    freight_rate: float


def calculate(
    purchase_price: float,
    weight_kg: float,
    freight_rate: float,
    price_usd: float,
    fx_rate: float,
    commission_pct: float,
    tariff_pct: float,
) -> Result:
    """按上面的口径算一遍；参数不合法时抛 ValueError（由页面负责显示）。"""
    if price_usd <= 0:
        raise ValueError("售价必须大于 0，否则毛利率没有意义。")
    if fx_rate <= 0:
        raise ValueError("汇率必须大于 0。")
    if purchase_price < 0 or weight_kg < 0 or freight_rate < 0:
        raise ValueError("采购价、重量、运费单价不能为负数。")
    if commission_pct < 0 or tariff_pct < 0:
        raise ValueError("佣金率和关税税率不能为负数。")

    commission_rate = commission_pct / 100.0
    tariff_rate = tariff_pct / 100.0

    revenue_cny = price_usd * fx_rate
    shipping_cny = weight_kg * freight_rate
    commission_cny = revenue_cny * commission_rate
    tariff_cny = revenue_cny * tariff_rate

    total_cost_cny = purchase_price + shipping_cny + commission_cny + tariff_cny
    gross_cny = revenue_cny - total_cost_cny
    margin = gross_cny / revenue_cny

    # 盈亏平衡：毛利 = 0 时，
    #   售价×汇率×(1−佣金率−关税率) = 采购价 + 运费
    denom = 1 - commission_rate - tariff_rate
    breakeven_usd = (purchase_price + shipping_cny) / (fx_rate * denom) if denom > 1e-9 else None

    # 佣金率临界值：毛利 = 0 时解出的佣金率（其余参数不变）
    commission_threshold_pct = (1 - tariff_rate - (purchase_price + shipping_cny) / revenue_cny) * 100.0

    return Result(
        purchase_price=purchase_price,
        revenue_cny=revenue_cny,
        shipping_cny=shipping_cny,
        commission_cny=commission_cny,
        tariff_cny=tariff_cny,
        total_cost_cny=total_cost_cny,
        gross_cny=gross_cny,
        margin=margin,
        breakeven_usd=breakeven_usd,
        commission_threshold_pct=commission_threshold_pct,
        price_usd=price_usd,
        commission_pct=commission_pct,
        tariff_pct=tariff_pct,
        fx_rate=fx_rate,
        weight_kg=weight_kg,
        freight_rate=freight_rate,
    )


def risk_hint(res: Result) -> tuple[str, str]:
    """返回 (level, 一句话风险提示)，level 取 ok / warn / bad，决定页面上用什么颜色。"""
    if res.breakeven_usd is None:
        return (
            "bad",
            "佣金率与关税税率合计已不低于 100%，卖多少钱都亏，得先把费率降下来。",
        )

    if res.gross_cny < 0:
        if res.commission_threshold_pct <= 0:
            return (
                "bad",
                "当前这笔单子已经是亏损，即使平台佣金为 0 也补不回来，要先提价或压降采购价、运费。",
            )
        return (
            "bad",
            f"当前毛利为负（毛利率 {res.margin * 100:.1f}%），"
            f"佣金率要降到 {res.commission_threshold_pct:.1f}% 以下才能转正，"
            f"当前是 {res.commission_pct:.1f}%。",
        )

    gap = res.commission_threshold_pct - res.commission_pct
    if gap < 3:
        return (
            "warn",
            f"佣金率超过 {res.commission_threshold_pct:.1f}% 时毛利转负，"
            f"当前 {res.commission_pct:.1f}%，只剩 {gap:.1f} 个百分点空间。",
        )
    return (
        "ok",
        f"佣金率超过 {res.commission_threshold_pct:.1f}% 时毛利转负"
        f"（当前 {res.commission_pct:.1f}%，还有 {gap:.1f} 个百分点空间）。",
    )


# ---------------------------------------------------------------- 显示格式
def money(value: float) -> str:
    """人民币显示：负数写成 -¥ 3.20，而不是 ¥ -3.20。"""
    sign = "-" if value < 0 else ""
    return f"{sign}¥ {abs(value):,.2f}"


def usd(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}$ {abs(value):,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"
