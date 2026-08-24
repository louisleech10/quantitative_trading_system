"""GAP-3 UX Task 1.10 — 凍結 fixture 與 live 欄集之漂移防線。

`tests/momentum/event_samples/` 依 R6 須可獨立跑、不 import `api`，故那側之
「未登記集合 == set()」是對**凍結 fixture** 斷言。凍結物會漂——本檔補上另一半：
fixture 必須逐字等於 `CaseData` 之 live future 欄集。

新增 future 欄而未重跑 `python3 handoffs/gen_case_data_future_columns.py`
並登記進 registry ⇒ 本檔紅。該紅為 fail-closed 之預期行為。
"""

from __future__ import annotations

import json
from pathlib import Path

from api.models.responses import CaseData
from momentum.Analysis.event_samples.lookahead_registry import unregistered_future_columns

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "momentum" / "event_samples" / "fixtures" / "case_data_future_columns.json"
)


def _live_columns() -> list:
    return sorted(n for n in CaseData.model_fields if n.lower().startswith("future"))


def test_gap3_future_column_inventory_drift_fixture_matches_casedata() -> None:
    with open(_FIXTURE, "r", encoding="utf-8") as f:
        frozen = json.load(f)["columns"]
    assert frozen == _live_columns()


def test_gap3_future_column_inventory_drift_live_columns_all_registered() -> None:
    assert unregistered_future_columns(_live_columns()) == set()
