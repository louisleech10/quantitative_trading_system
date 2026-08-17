"""ICHC Task 5.2 — 契約三方一致性（schema 檔 ↔ pydantic loader ↔ types.ts）＋M6。

解析規則：types.ts 取 ICHC 契約對應段（兩標記行之間），抽 CapabilityStatus union
字面值；註解行忽略（fixture 涵蓋）。
"""

import re
from pathlib import Path

import pytest

from momentum.Analysis.ic_config_schema import contract_enum, load_report_contract

REPO = Path(__file__).resolve().parents[3]
TYPES = REPO / "frontend/src/lib/types.ts"

BLOCK_START = "// ===== ICHC 契約對應段"
BLOCK_END = "// ===== ICHC 契約對應段結束 ====="


def _ts_capability_statuses(src: str) -> set:
    block_match = re.search(
        re.escape(BLOCK_START) + r"[\s\S]*?" + re.escape(BLOCK_END), src
    )
    assert block_match, "types.ts ICHC 契約段標記缺失"
    block = "\n".join(
        line for line in block_match.group(0).splitlines() if not line.strip().startswith("//")
    )
    union = re.search(r"export type CapabilityStatus =([\s\S]*?);", block)
    assert union, "CapabilityStatus union 缺失"
    return set(re.findall(r"'(\w+)'", union.group(1)))


class TestThreeWaySync:
    def test_capability_status_sets_equal(self):
        schema_set = set(load_report_contract()["capability_status"])
        pydantic_set = set(contract_enum("capability_status"))
        ts_set = _ts_capability_statuses(TYPES.read_text(encoding="utf-8"))
        assert schema_set == pydantic_set == ts_set, (
            f"schema={sorted(schema_set)} pydantic={sorted(pydantic_set)} ts={sorted(ts_set)}"
        )

    def test_r6_wider_contract_nodes_consistent(self):
        """R6 修補（CODEX-R6）：不只 capability_status——reasons/split_method/
        report_sections 鍵集也做跨源一致性（pydantic 消費點 vs 契約檔）。"""
        contract = load_report_contract()
        # split_method 枚舉：orchestrator 寫入值必在契約集合
        assert {"holdout", "full_sample_fallback"} == set(contract["split_method"])
        # reasons 消費點：程式碼中寫入的 reason 字面必在契約 reasons 值域
        all_reasons = {
            value for values in contract["reasons"].values() for value in values
        }
        orch_src = (REPO / "momentum/Analysis/ic_filter_orchestrator.py").read_text(
            encoding="utf-8"
        )
        for literal in ("insufficient_events", "turnover_disabled"):
            assert literal in all_reasons
            assert literal in orch_src  # 消費點存在
        # report_sections：五節鍵在 orchestrator 組裝面皆出現
        for section in contract["report_sections"]:
            assert f'"{section}"' in orch_src or section == "net_ic_analysis"

    def test_m6_tamper_one_side_breaks(self):
        """M6：任一側增/刪一鍵 → 集合不等（tamper fixture 自證可證偽）。"""
        schema_set = set(load_report_contract()["capability_status"])
        src = TYPES.read_text(encoding="utf-8")
        # 刪一鍵形態
        removed = src.replace("  | 'disabled'\n", "", 1)
        assert _ts_capability_statuses(removed) != schema_set
        # 增一鍵形態
        added = src.replace(
            "  | 'unavailable';", "  | 'unavailable'\n  | 'ichc_m6_extra';", 1
        )
        assert _ts_capability_statuses(added) != schema_set

    def test_comment_lines_ignored_by_parser(self):
        src = TYPES.read_text(encoding="utf-8")
        with_comment = src.replace(
            "export type CapabilityStatus =",
            "// 'commented_out_value' 干擾行\nexport type CapabilityStatus =",
            1,
        )
        assert _ts_capability_statuses(with_comment) == set(
            load_report_contract()["capability_status"]
        )

    def test_empty_schema_enum_would_fail(self):
        with pytest.raises(AssertionError):
            assert set() == set(load_report_contract()["capability_status"])
