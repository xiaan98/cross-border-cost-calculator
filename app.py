"""跨境小生意 · 成本模拟计算器（Streamlit 版）

一个帮助大学生理解跨境电商成本的模拟计算器，不是专业报价工具。

本地运行：
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from calculator import CASES, CASE_NOTES, calculate, money, pct, risk_hint, usd

st.set_page_config(
    page_title="跨境小生意 · 成本模拟计算器",
    page_icon="📦",
    layout="wide",
)

# ---------------------------------------------------------------- 样式
st.markdown(
    """
<style>
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }
.kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 2px; }
.kpi-card { flex: 1 1 200px; min-width: 172px; padding: 16px 18px 14px;
            border-radius: 14px; border: 1px solid rgba(125,135,155,.22);
            background: rgba(125,135,155,.07); }
.kpi-label { font-size: .80rem; letter-spacing: .05em; opacity: .70; margin-bottom: 6px; }
.kpi-value { font-size: 1.45rem; font-weight: 700; line-height: 1.25;
             font-variant-numeric: tabular-nums; }
.kpi-value.small { font-size: 1.05rem; }
.kpi-sub { font-size: .78rem; opacity: .60; margin-top: 7px; line-height: 1.5; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- 标题
st.markdown("## 跨境小生意 · 成本模拟计算器")
st.markdown(
    "**帮助大学生理解跨境电商成本的模拟计算器，不是专业报价工具。**"
)
st.caption("填 7 个参数 → 点「计算」→ 看这笔单子到底赚不赚钱、卖到多少钱才不亏。")

# ---------------------------------------------------------------- 示例案例
sel_col, tip_col = st.columns([1.0, 2.4], gap="large")
with sel_col:
    choice = st.selectbox("载入示例商品", list(CASES.keys()), key="case_select")

if st.session_state.get("_loaded_case") != choice:
    # 换案例时，把 7 个参数整组换成该案例的假设值，并清掉旧结果
    st.session_state.update(CASES[choice])
    st.session_state["_loaded_case"] = choice
    for key in ("result", "error"):
        st.session_state.pop(key, None)

for key, value in CASES["手机壳"].items():
    st.session_state.setdefault(key, value)

with tip_col:
    st.caption(
        f"{CASE_NOTES[choice]}（三个案例都是自编的教学假设值，不是抓取的真实数据。）"
    )

# ---------------------------------------------------------------- 输入区
with st.container(border=True):
    with st.form("calculator_form", clear_on_submit=False):
        cols = st.columns([1, 1, 1, 1, 0.95, 0.95, 0.95], gap="small")
        with cols[0]:
            purchase_price = st.number_input(
                "采购价（¥）", min_value=0.0, max_value=5000.0, step=0.5,
                format="%.2f", key="purchase_price",
                help="国内拿货价，不含国内快递到集运仓的费用。",
            )
        with cols[1]:
            weight_kg = st.number_input(
                "重量（kg）", min_value=0.0, max_value=30.0, step=0.01,
                format="%.2f", key="weight_kg",
                help="含包装的出海重量，运费按它算。",
            )
        with cols[2]:
            freight_rate = st.number_input(
                "运费单价（¥/kg）", min_value=0.0, max_value=500.0, step=1.0,
                format="%.0f", key="freight_rate",
                help="跨境小包/专线的公斤价，可向物流商索要报价单。",
            )
        with cols[3]:
            price_usd = st.number_input(
                "售价（$）", min_value=0.0, max_value=500.0, step=0.1,
                format="%.2f", key="price_usd",
                help="海外买家实际支付的商品价，不含买家侧运费。",
            )
        with cols[4]:
            fx_rate = st.number_input(
                "汇率", min_value=1.0, max_value=20.0, step=0.01,
                format="%.2f", key="fx_rate",
                help="1 美元换多少人民币，示例按 7.15。",
            )
        with cols[5]:
            commission_pct = st.number_input(
                "佣金（%）", min_value=0.0, max_value=50.0, step=0.5,
                format="%.1f", key="commission_pct",
                help="平台按售价抽取的比例，示例按 12%。",
            )
        with cols[6]:
            tariff_pct = st.number_input(
                "关税（%）", min_value=0.0, max_value=50.0, step=1.0,
                format="%.1f", key="tariff_pct",
                help="简化处理：按售价比例计征的关税。",
            )

        submitted = st.form_submit_button("计算", type="primary")

if submitted:
    try:
        result = calculate(
            purchase_price, weight_kg, freight_rate, price_usd,
            fx_rate, commission_pct, tariff_pct,
        )
    except ValueError as exc:
        st.session_state["error"] = str(exc)
        st.session_state.pop("result", None)
    else:
        st.session_state["result"] = result
        st.session_state["auto_computed"] = False
        st.session_state.pop("error", None)

if (
    not submitted
    and st.session_state.get("result") is None
    and st.session_state.get("error") is None
):
    # 首次进入或刚换案例：先按当前参数算一次，页面不会是空的
    try:
        st.session_state["result"] = calculate(
            st.session_state["purchase_price"], st.session_state["weight_kg"],
            st.session_state["freight_rate"], st.session_state["price_usd"],
            st.session_state["fx_rate"], st.session_state["commission_pct"],
            st.session_state["tariff_pct"],
        )
        st.session_state["auto_computed"] = True
    except ValueError as exc:
        st.session_state["error"] = str(exc)

# ---------------------------------------------------------------- 结果区
st.markdown("### 测算结果")

error = st.session_state.get("error")
result = st.session_state.get("result")


def kpi_card(label: str, value: str, sub: str, color: str, small: bool = False) -> str:
    cls = "kpi-value small" if small else "kpi-value"
    return (
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="{cls}" style="color:{color}">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>'
    )


if error:
    st.error(error)
elif result is None:
    st.info("参数调好后，点一下上面的「计算」，四个结果卡片会出现在这里。")
else:
    gross_color = "#16a34a" if result.gross_cny >= 0 else "#dc2626"
    if result.breakeven_usd is None:
        breakeven_value, breakeven_sub = "无法持平", "佣金 + 关税已达 100%，卖多少都是亏"
    else:
        breakeven_value, breakeven_sub = (
            usd(result.breakeven_usd),
            "毛利正好为 0 时对应的售价",
        )

    cards = [
        kpi_card("总成本", money(result.total_cost_cny), "采购 + 运费 + 佣金 + 关税", "#2563eb"),
        kpi_card(
            "毛利", money(result.gross_cny),
            f"售价折人民币 {money(result.revenue_cny)} − 成本 {money(result.total_cost_cny)}",
            gross_color,
        ),
        kpi_card("毛利率", pct(result.margin), "毛利 ÷ 售价折人民币", gross_color),
        kpi_card(
            "盈亏平衡售价", breakeven_value, breakeven_sub, "#d97706",
            small=result.breakeven_usd is None,
        ),
    ]
    st.markdown('<div class="kpi-row">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.caption(
        f"成本明细：采购 {money(result.purchase_price)} + 运费 {money(result.shipping_cny)}"
        f" + 佣金 {money(result.commission_cny)} + 关税 {money(result.tariff_cny)}"
        f" = {money(result.total_cost_cny)}；售价 {usd(result.price_usd)} × 汇率 "
        f"{result.fx_rate:.2f} = {money(result.revenue_cny)}。"
    )
    if st.session_state.get("auto_computed"):
        st.caption("已按当前示例参数算好一次；改动参数后点「计算」重新算。")

    level, hint = risk_hint(result)
    message = f"**风险提示 · {hint}**"
    if level == "bad":
        st.error(message)
    elif level == "warn":
        st.warning(message)
    else:
        st.success(message)

# ---------------------------------------------------------------- 三个案例对比
st.markdown("### 三个示例案例摆在一起看")
st.caption("同一套费率（佣金 12% / 关税 10% / 汇率 7.15），只有采购价、重量、售价不同。")

rows = []
for name, params in CASES.items():
    case_result = calculate(**params)
    rows.append(
        {
            "商品": name,
            "采购价": money(case_result.purchase_price),
            "重量（kg）": f"{params['weight_kg']:.2f}",
            "运费": money(case_result.shipping_cny),
            "售价（$）": usd(case_result.price_usd),
            "总成本": money(case_result.total_cost_cny),
            "毛利": money(case_result.gross_cny),
            "毛利率": pct(case_result.margin),
            "盈亏平衡售价": usd(case_result.breakeven_usd)
            if case_result.breakeven_usd is not None
            else "无法持平",
        }
    )

st.dataframe(pd.DataFrame(rows), hide_index=True)

# ---------------------------------------------------------------- 说明
with st.container(border=True):
    st.markdown("#### 这个计算器怎么算的")
    st.markdown(
        """
- **售价折人民币** = 售价 × 汇率
- **国际运费** = 重量 × 运费单价
- **平台佣金** = 售价折人民币 × 佣金率
- **关税** = 售价折人民币 × 关税税率（简化：按售价比例计征）
- **总成本** = 采购价 + 国际运费 + 平台佣金 + 关税
- **毛利** = 售价折人民币 − 总成本
- **毛利率** = 毛利 ÷ 售价折人民币
- **盈亏平衡售价**：让毛利 = 0 的售价，即（采购价 + 国际运费）÷〔汇率 ×（1 − 佣金率 − 关税税率）〕
"""
    )
    st.markdown("#### 为什么值得算一遍")
    st.markdown(
        """
跨境电商的利润不是「售价减采购价」，而是被三笔额外成本挤出来的：
**运费按公斤走**（轻的东西才有救）、**佣金按售价抽**（卖得越贵抽得越多）、
**关税按售价打**（定价越高税越高）。把这几笔摆到台面上，才看得清「卖得动」和「卖得赚」之间的差距。
"""
    )
    st.markdown("#### 假设与局限（务必看一眼）")
    st.markdown(
        """
- 只算**单笔订单**，不含广告费、仓储费、退货退款、支付手续费、汇损等；
- 关税按售价比例简化处理，真实税率取决于品类、目的国与申报价；
- 汇率固定为输入值，不随实时行情变动；
- 结论只用来建立成本直觉，**不能直接拿去报价或决策**。
"""
    )
    st.caption(
        "这是一个教学用的简化模型，不是专业报价工具。真实报价请以物流商报价单、平台费率后台、"
        "以及目的国海关规定为准。页面数据全部为自编示例，未联网抓取。"
    )
