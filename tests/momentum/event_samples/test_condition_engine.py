"""Task B3.1 驗證：safe-subset AST／角色隔離（W6 雙案例：同式只差 role）／digest 決定性／
邊界（未註冊欄、空式、恆真）／evaluate 與手算 exact。ASSERT：expression_role=feature 引用 future_return ⇒ 拒（M6 seam 在 test_mutation_guard）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples.condition_engine import (
    ConditionError,
    allowed_filtering_params,
    assert_no_outcome_columns,
    evaluate_condition,
    load_condition_engine_contract,
    parse_condition,
)

REG = {
    "rsi_14": "pit_feature",
    "ema_gap": "pit_feature",
    "volume_z": "pit_feature",
    "trigger_return": "trigger_outcome",
    "future_return_2": "future_outcome",
}


def _df() -> pd.DataFrame:
    return pd.DataFrame({
        "rsi_14": [20.0, 35.0, np.nan, 80.0, 50.0],
        "ema_gap": [-1.0, 0.5, 0.2, -0.3, 0.0],
        "volume_z": [0.1, 2.5, 1.0, 3.0, np.nan],
        "trigger_return": [0.01, -0.02, 0.03, 0.0, 0.05],
        "future_return_2": [0.02, 0.00, -0.01, 0.04, 0.06],
    })


# ---- 角色隔離（D3）：W6 雙案例，同一表達式只差 role ----
EXPR_WITH_FUTURE = "rsi_14 < 30 and future_return_2 >= 0.01"


def test_feature_role_rejects_future_column():
    with pytest.raises(ConditionError) as ei:
        parse_condition(EXPR_WITH_FUTURE, REG, "feature")
    assert ei.value.reason == "role_isolation_violation"


def test_selection_predicate_accepts_future_column_and_records_role():
    spec = parse_condition(EXPR_WITH_FUTURE, REG, "selection_predicate")
    assert spec.column_roles["future_return_2"] == "future_outcome"
    assert spec.column_roles["rsi_14"] == "pit_feature"
    assert spec.expression_role == "selection_predicate"


def test_feature_role_rejects_trigger_outcome_and_future_prefix_backstop():
    with pytest.raises(ConditionError) as ei:
        parse_condition("trigger_return > 0", REG, "feature")
    assert ei.value.reason == "role_isolation_violation"
    # registry 誤登 future_* 為 pit_feature ⇒ 命名 backstop 仍拒
    with pytest.raises(ConditionError) as ei2:
        parse_condition("future_x > 0", {"future_x": "pit_feature"}, "feature")
    assert ei2.value.reason == "role_isolation_violation"


def test_label_role_requires_outcome_column():
    with pytest.raises(ConditionError) as ei:
        parse_condition("rsi_14 < 30", REG, "label")
    assert ei.value.reason == "role_isolation_violation"            # CODEX-R1-P1-02：label 拒 pit_feature
    spec = parse_condition("future_return_2 >= 0.01", REG, "label")
    assert spec.column_roles == {"future_return_2": "future_outcome"}
    spec2 = parse_condition("trigger_return > 0 and future_return_2 >= 0.01", REG, "label")
    assert set(spec2.column_roles.values()) == {"trigger_outcome", "future_outcome"}


def test_label_role_rejects_mixed_feature_and_outcome():
    """CODEX-R1-P1-02 RECHECK：label 混入 pit_feature ⇒ 拒；同式 selection_predicate 通過、feature 拒。"""
    expr = "rsi_14 > 0 and future_return_2 > 0"
    with pytest.raises(ConditionError) as ei:
        parse_condition(expr, REG, "label")
    assert ei.value.reason == "role_isolation_violation"
    assert parse_condition(expr, REG, "selection_predicate").column_roles["rsi_14"] == "pit_feature"
    with pytest.raises(ConditionError):
        parse_condition(expr, REG, "feature")


def test_future_prefix_backstop_is_case_insensitive():
    """GROK-R1-P2-01 RECHECK：`Future_Return`／`FUTURE_X` 誤登 pit_feature 仍拒。"""
    for col in ("Future_Return", "FUTURE_X", "fUtUrE_y"):
        with pytest.raises(ConditionError) as ei:
            parse_condition(f"{col} > 0", {col: "pit_feature"}, "feature")
        assert ei.value.reason == "role_isolation_violation"
        assert parse_condition(f"{col} > 0", {col: "pit_feature"}, "selection_predicate").column_roles == {col: "pit_feature"}


@pytest.mark.parametrize("expr", [
    "True or rsi_14 > 0",
    "rsi_14 > 0 or True",
    "False and rsi_14 > 0",
    "rsi_14 > 0 or not rsi_14 > 0",
    "rsi_14 > 0 and not (rsi_14 > 0)",
    "not (rsi_14 > 0 or not rsi_14 > 0)",
    "(1 < 2 or rsi_14 > 0) and ema_gap > 0 or True",
    "rsi_14 <= rsi_14 and ema_gap > 0 or 3 > 2",
])
def test_logical_tautology_rejected(expr):
    """COMPOSER-R1-P1-01 RECHECK：引用欄位但邏輯恆真／恆假 ⇒ constant_expression（parse-time fail-closed）。"""
    with pytest.raises(ConditionError) as ei:
        parse_condition(expr, REG, "feature")
    assert ei.value.reason == "constant_expression"


def test_non_tautology_with_constant_subterm_accepted():
    spec = parse_condition("(rsi_14 > 0 or 1 > 2) and ema_gap > 0", REG, "feature")   # `1>2` 恆假但整體仍依資料
    assert spec.column_roles == {"ema_gap": "pit_feature", "rsi_14": "pit_feature"}
    assert evaluate_condition(spec, _df()).tolist() == [False, True, False, False, False]   # 列 2 rsi NaN ⇒ False


def test_contract_cache_immutable():
    """CODEX-R1-P2-04 RECHECK：caller 改寫回傳 dict 不污染 SoT。"""
    c = load_condition_engine_contract()
    c["future_column_prefix"] = "zzz_"
    c["allowed_functions"]["evil"] = {"arity": 1}
    assert load_condition_engine_contract()["future_column_prefix"] == "future_"
    assert "evil" not in load_condition_engine_contract()["allowed_functions"]
    with pytest.raises(ConditionError):
        parse_condition("future_q > 0", {"future_q": "pit_feature"}, "feature")


# ---- safe-subset ----
@pytest.mark.parametrize("expr,reason", [
    ("", "empty_expression"),
    ("   ", "empty_expression"),
    ("rsi_14 <", "syntax_error"),
    ("rsi_14 + 1 > 0", "disallowed_node"),
    ("__import__('os')", "disallowed_function"),
    ("rsi_14.mean() > 0", "disallowed_function"),
    ("foo > 1", "unregistered_column"),
    ("1 < 2", "constant_expression"),
    ("True", "constant_expression"),
    ("rsi_14 == rsi_14", "constant_expression"),
    ("lag(rsi_14, -1) > 0", "invalid_lag"),
    ("lag(rsi_14, 0) > 0", "invalid_lag"),
    ("lag(1, 2) > 0", "invalid_lag"),
    ("sqrt(rsi_14) > 0", "disallowed_function"),
    ("rsi_14 in [1, 2]", "disallowed_node"),
    ("rsi_14 if True else 0", "disallowed_node"),
])
def test_rejects_outside_safe_subset(expr, reason):
    with pytest.raises(ConditionError) as ei:
        parse_condition(expr, REG, "selection_predicate")
    assert ei.value.reason == reason


def test_unknown_column_role_and_unknown_expression_role():
    with pytest.raises(ConditionError) as ei:
        parse_condition("x > 0", {"x": "weird"}, "feature")
    assert ei.value.reason == "unknown_column_role"
    with pytest.raises(ConditionError) as ei2:
        parse_condition("rsi_14 > 0", REG, "nope")  # type: ignore[arg-type]
    assert ei2.value.reason == "unknown_expression_role"


def test_failure_reasons_all_in_contract():
    reasons = set(load_condition_engine_contract()["failure_reasons"])
    for expr, role in [("", "feature"), ("rsi_14 <", "feature"), ("foo > 1", "feature"), ("1 < 2", "feature"),
                       (EXPR_WITH_FUTURE, "feature"), ("rsi_14 < 30", "label")]:
        with pytest.raises(ConditionError) as ei:
            parse_condition(expr, REG, role)  # type: ignore[arg-type]
        assert ei.value.reason in reasons


# ---- digest 決定性 ----
def test_digest_invariant_to_whitespace_and_operand_order():
    a = parse_condition("rsi_14<30 and ema_gap>0", REG, "feature")
    b = parse_condition("  ema_gap > 0   and rsi_14 < 30 ", REG, "feature")
    c = parse_condition("30 > rsi_14 and 0 < ema_gap", REG, "feature")
    assert a.canonical_digest == b.canonical_digest == c.canonical_digest
    assert len(a.canonical_digest) == 64
    d = parse_condition("rsi_14 < 31 and ema_gap > 0", REG, "feature")
    assert d.canonical_digest != a.canonical_digest


def test_digest_chained_interval_equals_explicit_and():
    a = parse_condition("20 < rsi_14 < 40", REG, "feature")
    b = parse_condition("rsi_14 > 20 and rsi_14 < 40", REG, "feature")
    assert a.canonical_digest == b.canonical_digest


def test_digest_independent_of_role_and_and_or_distinct():
    a = parse_condition("rsi_14 < 30", REG, "feature")
    b = parse_condition("rsi_14 < 30", REG, "selection_predicate")
    assert a.canonical_digest == b.canonical_digest
    assert parse_condition("rsi_14 < 30 and ema_gap > 0", REG, "feature").canonical_digest != \
        parse_condition("rsi_14 < 30 or ema_gap > 0", REG, "feature").canonical_digest


# ---- max_lookback ----
def test_max_lookback_from_lag():
    spec = parse_condition("lag(rsi_14, 3) < 30 and lag(ema_gap, 1) > 0", REG, "feature")
    assert spec.max_lookback == 3
    assert parse_condition("rsi_14 < 30", REG, "feature").max_lookback == 0


# ---- evaluate：手算 exact ----
def test_evaluate_hand_exact_with_nan_and_interval():
    df = _df()
    m = evaluate_condition(parse_condition("rsi_14 < 40 and ema_gap >= 0", REG, "feature"), df)
    assert m.tolist() == [False, True, False, False, False]   # NaN rsi ⇒ False
    m2 = evaluate_condition(parse_condition("20 < rsi_14 < 60 or isnull(volume_z)", REG, "feature"), df)
    assert m2.tolist() == [False, True, False, False, True]
    m3 = evaluate_condition(parse_condition("not (ema_gap > 0)", REG, "feature"), df)
    assert m3.tolist() == [True, False, False, True, True]
    m4 = evaluate_condition(parse_condition("abs(ema_gap) >= 0.5", REG, "feature"), df)
    assert m4.tolist() == [True, True, False, False, False]
    assert m.dtype == bool and m2.dtype == bool


def test_evaluate_lag_only_looks_back():
    df = _df()
    m = evaluate_condition(parse_condition("lag(ema_gap, 1) > 0", REG, "feature"), df)
    assert m.tolist() == [False, False, True, True, False]    # shift(1)：列 i 看列 i-1
    # 因果：截斷未來列不改變前段結果
    m_cut = evaluate_condition(parse_condition("lag(ema_gap, 1) > 0", REG, "feature"), df.iloc[:3])
    assert m_cut.tolist() == m.tolist()[:3]


def test_evaluate_missing_column_loud():
    spec = parse_condition("rsi_14 < 30", REG, "feature")
    with pytest.raises(KeyError):
        evaluate_condition(spec, _df().drop(columns=["rsi_14"]))


# ---- D3-4／D3-3 出口 ----
def test_assert_no_outcome_columns():
    assert_no_outcome_columns(["rsi_14", "ema_gap"], REG)
    with pytest.raises(ConditionError) as ei:
        assert_no_outcome_columns(["rsi_14", "future_return_2"], REG)
    assert ei.value.reason == "role_isolation_violation"
    with pytest.raises(ConditionError):
        assert_no_outcome_columns(["trigger_return"], REG)
    with pytest.raises(ConditionError):
        assert_no_outcome_columns(["Future_Return_2"], {"Future_Return_2": "pit_feature"})   # casefold backstop（GROK R2 殘差）


def test_allowed_filtering_params_from_contract():
    assert allowed_filtering_params() == frozenset({"price_change"})
