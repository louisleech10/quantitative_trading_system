"""前端「走錯區」偵測之判準必須與後端 `looks_new_schema()` 一致（`-k contract_csv_guard`）。

出生事故（2026-09-02 使用者 UAT B10）：使用者把 `/search` 匯出的契約 CSV 丟進
「用自己的欄名匯入事件 CSV」那一區、把下拉**全部選滿**後送出，得到
`99 筆契約違規／列 0／label_definition／missing_required_field`。
成因：對映路徑只保留下拉指定的欄，而下拉只提供契約**頂層**欄，
`label_definition.window.horizon_bars` 這種巢狀欄沒得選 ⇒ 被丟掉。

修法是在前端**選檔當下**就擋。那需要前端有一份「這是不是契約 CSV」的判準——
🔴 於是就有兩份實作。本檔存在的唯一理由是**讓它們不能各走各的**：
逐字比對 `frontend/src/lib/contractCsvDetect.ts` 的 marker 與正規化規則
vs 後端 `EventImportService.looks_new_schema()` / `_canon_cols()`。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from api.services.case_import_service import EventImportService

FRONTEND = Path(__file__).resolve().parents[2] / "frontend/src/lib/contractCsvDetect.ts"


@pytest.fixture(scope="module")
def ts_source() -> str:
    assert FRONTEND.is_file(), f"前端判準檔不存在：{FRONTEND}"
    return FRONTEND.read_text(encoding="utf-8")


def test_contract_csv_guard_marker_columns_match_backend(ts_source: str):
    """marker 欄集合前後端**逐字相同**（少一欄 ⇒ 走錯區擋不住；多一欄 ⇒ 誤擋正常檔）。"""
    m = re.search(r"CONTRACT_MARKER_COLUMNS\s*=\s*\[([^\]]+)\]", ts_source)
    assert m, "前端找不到 CONTRACT_MARKER_COLUMNS"
    front = {s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()}
    assert front == {"event_id", "t0", "label"}, front

    svc = EventImportService()
    # 後端側：marker 齊 ⇒ True；缺任一 ⇒ False（這就是「集合相等」的行為證明）
    assert svc.looks_new_schema(sorted(front)) is True
    for drop in sorted(front):
        assert svc.looks_new_schema([c for c in sorted(front) if c != drop]) is False, drop


@pytest.mark.parametrize(
    "columns",
    [
        ["event_id", "t0", "label"],
        ["Event_ID", "T0", "Label"],                  # casefold
        ["  event_id  ", '"t0"', "'label'"],          # 去空白／引號
        ["﻿event_id", "t0", "label"],            # 去 BOM
        ["event_id", "t0", "label", "meta.price_change"],   # 帶 meta 欄仍算契約 CSV
    ],
)
def test_contract_csv_guard_backend_accepts_same_normalizations(columns):
    """前端 `canonColumnName()` 宣稱與後端同規則 ⇒ 這些寫法後端都要判為契約 CSV。

    🔴 前端那支是 TypeScript、跑不到這裡，本條驗的是**後端這一側的規則本身**；
    前端同規則之驗證在 `frontend/src/lib/contractCsvDetect.test.ts`（同一組 case）。
    兩檔用同一組輸入，任一端規則改了就會有一邊紅。
    """
    assert EventImportService().looks_new_schema(columns) is True


def test_contract_csv_guard_plain_csv_not_flagged():
    """over 向：一般自有欄名之 CSV **不得**被誤判為契約 CSV（否則對映區整個不能用）。"""
    svc = EventImportService()
    assert svc.looks_new_schema(["幣種", "週期", "進場時間_毫秒", "我的標記"]) is False
    # 只有 label 一欄同名也不算（marker 是三欄同時）
    assert svc.looks_new_schema(["symbol", "timestamp", "label"]) is False


def test_contract_csv_guard_frontend_normalization_rules_documented(ts_source: str):
    """前端的正規化必須真的做了四件事（BOM／空白／引號／小寫）——只寫註解不算。"""
    m = re.search(r"export function canonColumnName[\s\S]*?\n}", ts_source)
    assert m, "前端找不到 canonColumnName"
    body = m.group(0)
    assert "\\ufeff" in body or "﻿" in body, "缺去 BOM"
    assert ".trim()" in body, "缺去空白"
    assert '["\']' in body or "'\"'" in body, "缺去引號"
    assert ".toLowerCase()" in body, "缺 casefold"
