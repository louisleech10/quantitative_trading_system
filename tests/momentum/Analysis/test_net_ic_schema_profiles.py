"""§U 三 profile 鍵集合常數 — 唯一來源(T-F6)。

T1 / T2 / freeze 腳本一律 import 此檔,禁複製字面常數。
capacity 子鍵集合一併釘死(SPEC v1.1)。
"""

from __future__ import annotations

# SCHEMA_SKIPPED: turnover 缺/非有限/負值 或 gross_ic 非有限
SCHEMA_SKIPPED: frozenset[str] = frozenset({"skipped", "reason"})

# SCHEMA_GROSS_ONLY: cost_enabled=False
SCHEMA_GROSS_ONLY: frozenset[str] = frozenset(
    {
        "gross_ic",
        "turnover",
        "turnover_semantics",
        "capacity",
        "net_factor_return",
    }
)

# SCHEMA_COST_ENABLED = GROSS_ONLY ∪ cost 子樹
SCHEMA_COST_ENABLED: frozenset[str] = SCHEMA_GROSS_ONLY | frozenset(
    {
        "cost_bps",
        "cost_semantics",
        "cost_drag_return",
        "cost_sensitivity",
        "breakeven_cost_bps",
        "profitable_after_cost",
    }
)

# capacity 允許子鍵(鍵集合+型別斷言,r5)
CAPACITY_KEYS: frozenset[str] = frozenset(
    {
        "estimated_capacity_usd",
        "capacity_tier",
        "calibration",
    }
)

TURNOVER_SEMANTICS = "membership_change_both_legs_per_bar"
COST_SEMANTICS = "per_rebalance_not_annualized"
UNAVAILABLE_REASON = "canonical_factor_return_series_not_built (1c-FR)"


def test_schema_profile_constants_frozen() -> None:
    """常數自身一致性(多/少鍵於 union 關係)。"""
    assert SCHEMA_SKIPPED == frozenset({"skipped", "reason"})
    assert SCHEMA_GROSS_ONLY.isdisjoint({"cost_bps", "cost_drag_return", "net_ic"})
    assert "net_ic" not in SCHEMA_COST_ENABLED
    assert SCHEMA_GROSS_ONLY.issubset(SCHEMA_COST_ENABLED)
    assert CAPACITY_KEYS == frozenset(
        {"estimated_capacity_usd", "capacity_tier", "calibration"}
    )
