"""GAP-3 UX Task 1.10 — 欄位級 lookahead 契約之驗收（SPEC L1653–1679 之 ①–④）。

盤點來源＝`tests/momentum/event_samples/fixtures/case_data_future_columns.json`
（由 `python3 handoffs/gen_case_data_future_columns.py` 自 `CaseData.model_fields` 凍結）。
🔴 **不用文字掃描**——`grep -oE "future[_0-9]…"` 會把區域變數、f-string 片段與註解字樣
混進來，使「未登記集合 == set()」不可靠（CODEX-R2-P1-05）。
本目錄不 import `api`（R6 獨立性）；fixture 與 live 欄集之漂移由 `tests/api` 側之
`test_gap3_future_column_inventory_drift.py` 看住。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from momentum.Analysis.event_samples.lookahead_registry import (
    hours_to_bars,
    load_lookahead_registry,
    lookahead_columns,
    resolve_lookahead_bars,
    unregistered_future_columns,
)

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "case_data_future_columns.json"

_BAR_RE = re.compile(r"^future_(\d+)bar_(return|max_drawdown)$")

# ── producer-backed 分類 oracle（CODEX-R1-P1-01 之修法） ──────────────────────
# 🔴 **不得**用欄名 regex 導出分類——那正是本輪被打掉的錯誤：
#    `future1/2/4/6_close_return` 長得像「小時命名」，producer 卻用裸 shift(-N)＝N 根。
#    照名字推會在 12h 線上把 future6（實際 6 根）算成 1 根，purge 低估六倍。
# 下表逐欄抄自 `momentum/DataExtraction/case_search_engine.py` 之**實際算式**，
# 每一列都可回該檔以字面錨點對證（字面見 registry 之 classification_evidence）。
_PRODUCER_SEMANTICS = {
    # 裸整數 shift(-N)：N 就是根數，與 timeframe 無關
    "future1_close_return": ("bar", 1),
    "future2_close_return": ("bar", 2),
    "future4_close_return": ("bar", 4),
    "future6_close_return": ("bar", 6),
    # shift(-periods_{H}h)：H 是小時，根數與 timeframe 相依
    "future24_close_return": ("hour", 24),
    "future48_close_return": ("hour", 48),
    "future72_close_return": ("hour", 72),
    "future24_close": ("hour", 24),
    "future24_low": ("hour", 24),
    "future72_max_return": ("hour", 72),
    "future72_max_drawdown": ("hour", 72),
    # 寫死之 standard_lookahead = 6，但欄名看不出來 ⇒ 依 SPEC 標 unknown、不得給預設深度
    "future_max_return": ("unknown", None),
    "future_max_drawdown": ("unknown", None),
}


@pytest.fixture(scope="module")
def registry() -> dict:
    return load_lookahead_registry()


@pytest.fixture(scope="module")
def cols(registry: dict) -> dict:
    return lookahead_columns(registry)


@pytest.fixture(scope="module")
def actual_columns() -> list:
    with open(_FIXTURE, "r", encoding="utf-8") as f:
        return json.load(f)["columns"]


# ── ② 未登記集合 == set()（fail-closed 之判定依據） ─────────────────────────
def test_lookahead_registry_complete_01_no_unregistered_future_columns(actual_columns, registry) -> None:
    assert unregistered_future_columns(actual_columns, registry) == set()
    assert len(actual_columns) > 0  # 防「空清單當全綠」


# ── ① 兩套命名之單位與換算 ────────────────────────────────────────────────
def test_lookahead_registry_complete_02_units_and_conversion(cols, registry) -> None:
    assert cols["future_4bar_max_drawdown"]["lookahead_bars"] == 4
    assert cols["future72_max_return"]["lookahead_hours"] == 72
    assert "lookahead_bars" not in cols["future72_max_return"]  # 禁存固定 bar 數
    # 小時命名欄之根數與 timeframe 相依：同樣 72 小時，12h 線 6 根、1h 線 72 根
    assert resolve_lookahead_bars("future72_max_return", "12h", registry) == 6
    assert resolve_lookahead_bars("future72_max_return", "1h", registry) == 72


# ── ①／④ bar 命名欄：逐欄 lookahead_bars == N ───────────────────────────────
def test_lookahead_registry_complete_03_bar_named_depth_equals_n(actual_columns, registry) -> None:
    checked = 0
    for c in actual_columns:
        m = _BAR_RE.match(c)
        if not m:
            continue
        checked += 1
        assert resolve_lookahead_bars(c, "1h", registry) == int(m.group(1)), c
        # bar 命名欄之根數與 timeframe 無關
        assert resolve_lookahead_bars(c, "12h", registry) == int(m.group(1)), c
    assert checked >= 24  # 12 個 return ＋ 12 個 max_drawdown


# ── ③ 三形態辨識（契約蛇形／CSV 標題形／全大寫） ───────────────────────────
@pytest.mark.parametrize(
    "form",
    ["Future_4Bar_Return_%", "future_4bar_return", "FUTURE_4BAR_RETURN"],
)
def test_lookahead_registry_complete_04_three_header_forms(form, registry) -> None:
    assert resolve_lookahead_bars(form, "1h", registry) == 4


def test_lookahead_registry_complete_04b_csv_drawdown_alias(registry) -> None:
    # CSV 標題是 Future_4Bar_Drawdown_%，契約蛇形是 future_4bar_max_drawdown（少了 max）
    assert resolve_lookahead_bars("Future_4Bar_Drawdown_%", "1h", registry) == 4


# ── ④ registry 內容正確性：以 **producer 實際算式** 逐欄對證分類與深度 ───────
def test_lookahead_registry_complete_05_registry_content_correct(cols) -> None:
    """🔴 oracle 來源＝producer，不是欄名（CODEX-R1-P1-01）。

    `future_{N}bar_*` 之 N 可安全由欄名導出（producer 就是以 N 為 shift 量），
    其餘全部逐欄查 `_PRODUCER_SEMANTICS`——那張表抄自 `case_search_engine.py` 之實際算式。
    """
    for name, entry in cols.items():
        bar = _BAR_RE.match(name)
        if bar:
            assert entry["kind"] == "bar", name
            assert entry["lookahead_bars"] == int(bar.group(1)), name
            assert "lookahead_hours" not in entry, name
            continue

        assert name in _PRODUCER_SEMANTICS, f"{name} 未列入 producer-backed oracle（新增欄須先查 producer 算式）"
        kind, depth = _PRODUCER_SEMANTICS[name]
        assert entry["kind"] == kind, name
        if kind == "bar":
            assert entry["lookahead_bars"] == depth, name
            assert "lookahead_hours" not in entry, name
        elif kind == "hour":
            assert entry["lookahead_hours"] == depth, name
            assert "lookahead_bars" not in entry, name
        else:
            assert entry.get("lookahead_unknown") is True, name
            assert "lookahead_bars" not in entry and "lookahead_hours" not in entry, name


def test_lookahead_registry_complete_05b_producer_oracle_covers_every_non_bar_column(cols) -> None:
    """oracle 表本身不得漏欄——漏了就會讓 05 的迴圈靜默跳過那一欄。"""
    non_bar = {n for n in cols if not _BAR_RE.match(n)}
    assert non_bar == set(_PRODUCER_SEMANTICS)


def test_lookahead_registry_complete_05c_shift_named_columns_are_bar_kind(cols, registry) -> None:
    """定向探針：`future{N}_close_return`（N ∈ 1,2,4,6）**不是**小時欄。

    這是 CODEX-R1-P1-01 之回歸鎖。若被改回 hour，12h 線上之深度會塌成 1，本條即紅。
    """
    for name, n in (("future1_close_return", 1), ("future2_close_return", 2),
                    ("future4_close_return", 4), ("future6_close_return", 6)):
        assert cols[name]["kind"] == "bar", name
        assert cols[name]["lookahead_bars"] == n, name
        # 與 timeframe 無關：12h 與 1h 皆為同一根數
        assert resolve_lookahead_bars(name, "12h", registry) == n, name
        assert resolve_lookahead_bars(name, "1h", registry) == n, name


# ── ④ legacy 無數字欄：顯式 unknown，且**不得**給任何預設深度 ───────────────
@pytest.mark.parametrize("name", ["future_max_return", "future_max_drawdown"])
def test_lookahead_registry_complete_06_legacy_columns_marked_unknown(name, cols, registry) -> None:
    entry = cols[name]
    assert entry["kind"] == "unknown"
    assert entry.get("lookahead_unknown") is True
    assert "lookahead_bars" not in entry
    assert "lookahead_hours" not in entry
    assert resolve_lookahead_bars(name, "1h", registry) is None


# ── 換算方向（實作決策之釘死）：sub-bar 深度不得被讀成 0 ────────────────────
def test_lookahead_registry_complete_07_hours_to_bars_is_ceil(registry) -> None:
    assert hours_to_bars(72, "1h") == 72
    assert hours_to_bars(72, "12h") == 6
    # sub-bar 小時值：向下取整會得 0＝宣稱不必 purge，屬放水 ⇒ 一律向上取整。
    # ⚠️ CODEX-R1-P1-01 修法後，現行 hour 類欄只有 {24,48,72}，對現有全部 timeframe 皆整除
    #    ⇒ 本條目前**沒有活的欄位案例**，是對函式本身之防禦性釘死（日後新增 hour 欄即生效）。
    assert hours_to_bars(1, "12h") == 1
    assert hours_to_bars(30, "12h") == 3


# ── 未知 timeframe fail-closed（不猜預設值） ───────────────────────────────
def test_lookahead_registry_complete_08_unknown_timeframe_fail_closed(registry) -> None:
    with pytest.raises(ValueError):
        resolve_lookahead_bars("future72_max_return", "3h", registry)
