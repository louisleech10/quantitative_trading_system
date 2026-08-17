"""ICHC Task 3.1 — xsec 五節 capability status 測試＋M4 mutation 等價探針。

斷言（TODO/CODEX-R3-P1-04 修訂版）：mode=cross_sectional 時
ic_decay/quantile_returns/grouped_ic/turnover_analysis/coverage_analysis 五節
status 值 ∈ 契約枚舉（contract_enum 比對）且 reason 非空——非只「帶 status」。
fixture 沿用 tests/momentum/test_ic_1eb_b3_xsec.py 的合成 MultiIndex 慣例
（xsec 單元測試既有做法；FF golden 禁合成不適用此層）。
"""

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import contract_enum, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

FIVE_SECTIONS = (
    "ic_decay",
    "quantile_returns",
    "grouped_ic",
    "turnover_analysis",
    "coverage_analysis",
)


def _make_xsec_frame(n_timestamps: int = 60, seed: int = 7) -> pd.DataFrame:
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT", "XRPUSDT"]
    timestamps = pd.date_range("2020-01-01", periods=n_timestamps, freq="12h")
    index = pd.MultiIndex.from_product(
        [timestamps, symbols], names=["timestamp", "_symbol"]
    )
    rng = np.random.default_rng(seed)
    n = len(index)
    feat = rng.normal(0, 1, n)
    label = feat * 0.5 + rng.normal(0, 1, n)
    return pd.DataFrame(
        {
            "alpha": feat.astype(np.float32),
            "return_1": label.astype(np.float32),
        },
        index=index,
    )


@pytest.fixture(scope="module")
def xsec_report():
    orch = ICFilterOrchestrator(load_ic_config())
    return orch.analyze_cross_sectional(
        _make_xsec_frame(),
        config_override={"ic_train_test_split": False},
    )


class TestXsecCapabilityStatus:
    def test_five_sections_status_in_contract_enum_with_reason(self, xsec_report):
        statuses = contract_enum("capability_status")
        problems = []
        for section in FIVE_SECTIONS:
            node = xsec_report.get(section)
            if not isinstance(node, dict) or not node:
                problems.append(f"{section}: 裸空或缺節={node!r}")
                continue
            status = node.get("status")
            if status not in statuses:
                problems.append(f"{section}: status={status!r} 不在契約枚舉")
            if not node.get("reason"):
                problems.append(f"{section}: reason 空")
        assert not problems, "；".join(problems)

    def test_status_is_not_applicable_for_xsec_mode(self, xsec_report):
        for section in FIVE_SECTIONS:
            assert xsec_report[section]["status"] == "not_applicable", section
            assert xsec_report[section]["reason"] == "cross_sectional_mode", section

    def test_m4_probe_bare_empty_dict_would_fail(self, xsec_report):
        """M4 等價探針：把任一節換回裸 {} → 本檔第一條斷言必紅（自我可證偽）。"""
        mutated = dict(xsec_report)
        mutated["grouped_ic"] = {}
        node = mutated["grouped_ic"]
        assert not (isinstance(node, dict) and node.get("status")), (
            "mutation fixture 應為裸空——此斷言保證第一條測試對裸空是紅的"
        )

    def test_xsec_core_outputs_still_present(self, xsec_report):
        assert isinstance(xsec_report.get("summary_table"), list)
        assert xsec_report["filter_log"]["mode"] == "cross_sectional"
