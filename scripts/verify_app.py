"""自检：① 算式是否自洽 ② 页面能否真实跑起来并点得动「计算」。

运行：python scripts/verify_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calculator import CASES, calculate, risk_hint  # noqa: E402


def check_formula() -> None:
    print("== 算式自检 ==")
    for name, params in CASES.items():
        res = calculate(**params)
        # 恒等式 1：售价折人民币 − 总成本 = 毛利
        assert abs((res.revenue_cny - res.total_cost_cny) - res.gross_cny) < 1e-9
        # 恒等式 2：成本四项相加 = 总成本
        parts = res.purchase_price + res.shipping_cny + res.commission_cny + res.tariff_cny
        assert abs(parts - res.total_cost_cny) < 1e-9
        # 恒等式 3：按盈亏平衡售价重算，毛利应约等于 0
        reb = calculate(
            params["purchase_price"], params["weight_kg"], params["freight_rate"],
            res.breakeven_usd, params["fx_rate"], params["commission_pct"], params["tariff_pct"],
        )
        assert abs(reb.gross_cny) < 1e-6, (name, reb.gross_cny)
        # 恒等式 4：佣金率取临界值，毛利应约等于 0
        crit = calculate(
            params["purchase_price"], params["weight_kg"], params["freight_rate"],
            params["price_usd"], params["fx_rate"], res.commission_threshold_pct, params["tariff_pct"],
        )
        assert abs(crit.gross_cny) < 1e-6, (name, crit.gross_cny)
        level, hint = risk_hint(res)
        print(
            f"{name}: 总成本 {res.total_cost_cny:8.2f} | 毛利 {res.gross_cny:8.2f} | "
            f"毛利率 {res.margin * 100:5.1f}% | 盈亏平衡 ${res.breakeven_usd:5.2f} | "
            f"临界佣金率 {res.commission_threshold_pct:5.1f}% | [{level}] {hint}"
        )

    # 边界：佣金 + 关税 ≥ 100% 时无解
    edge = calculate(3.5, 0.05, 85.0, 6.99, 7.15, 60.0, 45.0)
    assert edge.breakeven_usd is None
    print("边界（佣金60%+关税45%）: 盈亏平衡售价 ->", edge.breakeven_usd, "|", risk_hint(edge)[1])

    # 边界：亏本单应给出 bad 级提示
    loss = calculate(50.0, 0.05, 85.0, 6.99, 7.15, 12.0, 10.0)
    assert loss.gross_cny < 0, loss.gross_cny
    assert risk_hint(loss)[0] == "bad"
    print("边界（采购 ¥50 卖 $6.99）:", risk_hint(loss)[1])

    # 边界：售价 0 / 汇率 0 应报错而不是除零
    for bad in ({"price_usd": 0.0}, {"fx_rate": 0.0}):
        params = {**CASES["手机壳"], **bad}
        try:
            calculate(**params)
        except ValueError as exc:
            print("边界参数报错 OK:", exc)
        else:
            raise AssertionError(f"{bad} 应当抛 ValueError")


def check_app() -> None:
    print("\n== 页面自检（AppTest）==")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    print("初始渲染 OK：标题 =", at.markdown[0].value if at.markdown else None)
    print("输入框数量：number_input =", len(at.number_input))
    assert len(at.number_input) == 7, len(at.number_input)

    # 默认案例（手机壳）点一次「计算」
    buttons = at.button  # 含表单提交按钮
    print("按钮：", [(b.label, b.type) for b in buttons])
    submit = [b for b in buttons if b.label == "计算"]
    assert submit, "找不到「计算」按钮"
    submit[0].click().run()
    assert not at.exception, at.exception

    assert at.session_state["result"] is not None
    res = at.session_state["result"]
    expect = calculate(**CASES["手机壳"])
    assert abs(res.total_cost_cny - expect.total_cost_cny) < 1e-9
    print(f"点击后结果 OK：总成本 {res.total_cost_cny:.2f} 毛利 {res.gross_cny:.2f} 毛利率 {res.margin * 100:.1f}%")

    # 换案例 -> 参数应跟着变，并自动按新案例算一次
    at.selectbox[0].set_value("小夜灯").run()
    assert not at.exception, at.exception
    assert at.session_state.get("auto_computed") is True
    res_auto = at.session_state["result"]
    assert abs(res_auto.total_cost_cny - calculate(**CASES["小夜灯"]).total_cost_cny) < 1e-9
    print("切换案例后采购价 =", at.number_input[0].value, "售价 =", at.number_input[3].value,
          "| 自动算得总成本 =", round(res_auto.total_cost_cny, 2))

    # 手动点「计算」-> 自动标记应清除，结果仍一致
    [b for b in at.button if b.label == "计算"][0].click().run()
    assert not at.exception, at.exception
    assert at.session_state.get("auto_computed") is False
    res = at.session_state["result"]
    assert abs(res.total_cost_cny - calculate(**CASES["小夜灯"]).total_cost_cny) < 1e-9
    print(f"手动重算 OK：总成本 {res.total_cost_cny:.2f} 毛利率 {res.margin * 100:.1f}%")

    # 结果区文案是否齐全（四张卡片 + 风险提示 + 成本明细）
    page_text = (
        " ".join(m.value for m in at.markdown)
        + " ".join(c.value for c in at.caption)
        + " ".join(a.value for a in list(at.error) + list(at.warning) + list(at.success) + list(at.info))
    )
    for keyword in ("总成本", "毛利", "毛利率", "盈亏平衡售价", "成本明细", "风险提示"):
        assert keyword in page_text, f"页面缺少：{keyword}"
    print("结果区关键词齐全：总成本 / 毛利 / 毛利率 / 盈亏平衡售价 / 成本明细 / 风险提示")
    print("风险提示行：", [a.value for a in list(at.success) + list(at.warning) + list(at.error)])

    # 案例对比表应有三行
    assert len(at.dataframe) == 1
    assert len(at.dataframe[0].value) == 3, at.dataframe[0].value
    print("案例对比表 OK：三行 =", list(at.dataframe[0].value["商品"]))
    print("\n全部自检通过。")


if __name__ == "__main__":
    check_formula()
    check_app()
