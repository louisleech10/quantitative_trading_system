"""SPLITUNIFY Task 1.2（B1）：`split_unify.json` 之契約測試。

🔴 **B1 刻意不動生產碼**，所以本批**還沒有** `split_projection.py` 可以對證 Python 常數
（那是 B2b）。為了讓本批仍有「兩端對證」而非只驗自己，本檔改以
**SPEC 文件字面**當第二來源：`docs/SPLITUNIFY_SPEC.md` 內必須逐字出現每一個 reason，
JSON 與 SPEC 任一邊漂了就紅。B2b 建 `split_projection.py` 後**再加**
「JSON ↔ Python 常數集合相等」那條（見本檔尾之 TODO 註記），不刪本檔既有斷言。

對應 SPEC：C-8（JSON 單一真相源）、C-3（三態＝兩容器，故禁 `assignment_states`）、
C-0 決議③(b)（`estimand_scope`）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CONTRACT = REPO / "momentum" / "Analysis" / "contracts" / "split_unify.json"
SPEC = REPO / "docs" / "SPLITUNIFY_SPEC.md"
EVENT_IMPORT_CONTRACT = (
    REPO / "momentum" / "Analysis" / "contracts" / "event_import_contract.json"
)

REQUIRED_KEYS = {
    "schema_version",
    "split_authority_values",
    "fail_closed_reasons",
    "estimand_scope_values",
}


@pytest.fixture(scope="module")
def contract() -> dict:
    assert CONTRACT.exists(), f"契約檔不存在: {CONTRACT}"
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_required_keys_present(contract: dict) -> None:
    """缺任一必填鍵 ⇒ 紅（可證偽：刪掉 fail_closed_reasons 本測試必紅）。"""
    missing = REQUIRED_KEYS - set(contract)
    assert not missing, f"split_unify.json 缺鍵: {sorted(missing)}"


def test_value_sets_are_non_empty_closed_sets(contract: dict) -> None:
    """三個值集皆須非空、無重複、全為 str（空集合＝沒有封閉集合可對證）。"""
    for key in ("split_authority_values", "fail_closed_reasons", "estimand_scope_values"):
        values = contract[key]
        assert isinstance(values, list) and values, f"{key} 須為非空 list"
        assert all(isinstance(v, str) and v for v in values), f"{key} 須全為非空字串"
        assert len(set(values)) == len(values), f"{key} 有重複值: {values}"


def test_split_authority_is_kline_holdout(contract: dict) -> None:
    """SPEC C-1：canonical 權威＝K 線 holdout。"""
    assert set(contract["split_authority_values"]) == {"kline_holdout"}


def test_fail_closed_reasons_exact_set(contract: dict) -> None:
    """SPEC C-0／C-2 之四個 fail-closed 原因，逐值相等（不是 issubset）。"""
    assert set(contract["fail_closed_reasons"]) == {
        "multi_symbol_projection_unsupported",
        "missing_train_plan",
        "missing_test_plan",
        "canonical_feature_universe_unavailable",
    }


def test_estimand_scope_exact_set(contract: dict) -> None:
    """SPEC C-0 決議③(b)：event-study-only 之表身須標非 OOS。"""
    assert set(contract["estimand_scope_values"]) == {"full_sample_not_oos"}


def test_assignment_states_must_not_exist(contract: dict) -> None:
    """🔴 SPEC C-3：三態＝兩容器（`assignments` ＋ 獨立 `purged`），**不是**三值枚舉。

    v1 曾把 `assignment_states=["train","purged","test"]` 寫進本檔；若照字面實作成
    `assignments.split_label` 三值，只認兩值的消費者（`pipeline.py:697-698`、
    `baseline.py:106`、`tables.py:305`、`pattern_bridge.py:115,125-127`）**不會報錯，
    只會靜默少算**。本斷言就是擋這個回潮。
    """
    assert "assignment_states" not in contract, (
        "split_unify.json 不得含 assignment_states——三態是兩個容器不是三值枚舉（SPEC C-3）"
    )


def test_purge_reason_stays_in_event_import_contract() -> None:
    """🔴 SPEC C-3：purge reason 沿用既有契約，**不得**在 split_unify.json 另造第二份。"""
    existing = json.loads(EVENT_IMPORT_CONTRACT.read_text(encoding="utf-8"))
    assert existing["split_purge_reasons"] == ["interval_crosses_split_boundary"], (
        "既有 purge reason 字面已漂——SPLITUNIFY 之投影沿用它，漂了要一起改"
    )


def test_every_reason_appears_verbatim_in_spec(contract: dict) -> None:
    """兩端對證（B1 版）：SPEC 內須逐字出現每一個 reason 與權威值。

    B2b 之後會再加「JSON ↔ `split_projection.py` 常數集合相等」，本條不刪。
    """
    spec_text = SPEC.read_text(encoding="utf-8")
    literals = (
        list(contract["fail_closed_reasons"])
        + list(contract["split_authority_values"])
        + list(contract["estimand_scope_values"])
    )
    missing = [lit for lit in literals if lit not in spec_text]
    assert not missing, f"SPEC 未逐字出現這些字面（JSON 與 SPEC 漂了）: {missing}"


# TODO(B2b)：`split_projection.py` 建立後，於本檔新增
#   test_python_constants_equal_json —— `set(split_projection.FAIL_CLOSED_REASONS) ==
#   set(contract["fail_closed_reasons"])`，並驗「刪 JSON 一鍵 ⇒ import 期 raise」。
#   B1 之所以還沒加，是因為本批不動生產碼（SPEC §P 之 B1 定義）。


# ---------------------------------------------------------------------------
# D-002 `D-002-C5` register 碼證錨點（v26；R32 `CODEX-R32-P1-01`）
#
# 🔴 為什麼放在這個檔：六路回歸逐檔明列路徑，本檔已在其中 ⇒ 錨點每次回歸都會被驗，
#    而不是「`Task 9.3` 驗收當下跑一次」。codex 在 R32 明指前一版的問題正是
#    「沒有獨立可重跑的 persisted checker」。
# ---------------------------------------------------------------------------

import importlib.util as _importlib_util  # noqa: E402

_ANCHOR_CHECKER = REPO / "scripts" / "register_anchor_check.py"


def _load_anchor_checker():
    spec = _importlib_util.spec_from_file_location(
        "register_anchor_check", _ANCHOR_CHECKER
    )
    mod = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_d002_register_anchors_all_valid():
    """register 每個 ANCHOR 子句都必須指到它所述之碼（單一精確行＋token 序列恰一次）。"""
    mod = _load_anchor_checker()
    anchors = mod.parse_anchors(mod.SPEC_PATH.read_text(encoding="utf-8"))
    assert len(anchors) >= 16, f"register ANCHOR 子句數異常：{len(anchors)}"
    bad = []
    for a in anchors:
        ok, why = mod.check_anchor(a)
        if not ok:
            bad.append(f"{a.row_id} {a.path}:{a.line} — {why}")
    assert not bad, "register 錨點失準：\n" + "\n".join(bad)


def test_d002_register_anchor_gate_rejects_known_false_greens():
    """must-fail 回歸：歷來三道閘各自放行過的落點，現行閘必須全部拒絕。

    - `:341` 是 `raise ValueError` 的**訊息字串**，v26 前的「行範圍＋子字串」會綠
      （R32 codex 實跑打穿）。
    - `:566` 是另一道重複閘，同樣含 `feature_timeframe` 字面。
    - `:556`／`pipeline.py:760` 是**純註解行**，v15 的「行號 ≤ 總行數」會綠。
    """
    mod = _load_anchor_checker()
    sp = "momentum/Analysis/event_samples/split_projection.py"
    must_fail = [
        (sp, 341, ("columns", '"timeframe"', '"feature_timeframe"')),
        (sp, 341, ("feature_timeframe",)),
        (sp, 566, ("columns", '"timeframe"', '"feature_timeframe"')),
        (sp, 566, ("feature_timeframe",)),
        (sp, 556, ("purged",)),
        ("momentum/Analysis/event_samples/pipeline.py", 760, ('"n_purged"',)),
    ]
    leaked = []
    for path, line, toks in must_fail:
        ok, why = mod.check_anchor(mod.Anchor("(must-fail)", path, line, toks))
        if ok:
            leaked.append(f"{path}:{line} {list(toks)} — 竟然通過：{why}")
    assert not leaked, "錨點閘又變成弱閘了：\n" + "\n".join(leaked)
