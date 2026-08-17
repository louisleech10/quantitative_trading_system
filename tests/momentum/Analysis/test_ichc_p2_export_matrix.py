"""ICHC Task 2.1 — 出口矩陣測試（CODEX-R1-P1-07 RECHECK 形態）。

同一 analysis_results（巢狀舊形）經 generate_json_report（flatten＋validator 單點邊界）
後，逐出口驗證契約形狀與數值：raw JSON／summary CSV（long_short_spread 有值）／
save_report 落地重讀。GET /quantile 與 get_result 由既有 tests/api/test_ic_response_v2.py
（7 passed）覆蓋，不重複。
"""

import csv
import json
from io import StringIO

import pytest

from momentum.Analysis.ic_config_schema import load_report_contract
from momentum.Analysis.ic_reporter import ICReporter

NESTED_ANALYSIS_RESULTS = {
    "filter_log": {},
    "summary_table": [
        {
            "feature_name": "featA",
            "ic_mean": 0.02,
            "icir": 0.5,
            "p_value": 0.01,
            "pass_class": "research_only",
        }
    ],
    "ic_decay": {},
    "quantile_returns": {
        "featA": {
            "quantile_returns": {
                "quantile_mean_returns": {"Q1": -0.01, "Q2": 0.0, "Q3": 0.015},
                "cumulative_returns": {"Q1": [-0.01], "Q2": [0.0], "Q3": [0.015]},
                "long_short_spread": 0.025,
                "long_short_tstat": 1.9,
            },
            "monotonicity_score": 0.75,
            "long_short": {"spread": 0.025, "tstat": 1.9},
        }
    },
    "grouped_ic": {},
    "correlation_matrix": {},
    "diversification_metrics": {},
    "turnover_analysis": {},
    "coverage_analysis": {},
}


@pytest.fixture()
def report():
    reporter = ICReporter(config={})
    return reporter.generate_json_report(
        dict(NESTED_ANALYSIS_RESULTS), metadata={"case_id": "ichc_matrix"}
    )


def _required_keys():
    contract = load_report_contract()
    return contract["report_sections"]["quantile_returns"]["per_feature_required_keys"]


class TestExportMatrix:
    def test_report_quantile_is_flat_contract_shape(self, report):
        payload = report["quantile_returns"]["featA"]
        for key in _required_keys():
            assert key in payload, f"缺契約鍵 {key}"
        assert payload["quantile_mean_returns"]["Q3"] == 0.015
        assert payload["long_short_spread"] == 0.025
        assert payload["monotonicity_score"] == 0.75

    def test_raw_json_export_preserves_flat_shape(self, report, tmp_path):
        reporter = ICReporter(config={})
        paths = reporter.export_all(report, str(tmp_path), "ichc_matrix")
        raw_candidates = [p for p in paths.values() if str(p).endswith(".json")]
        assert raw_candidates, f"export_all 無 JSON 出口：{paths}"
        found_flat = False
        for path in raw_candidates:
            data = json.loads(open(path, encoding="utf-8").read())
            quantile_section = data.get("quantile_returns")
            if isinstance(quantile_section, dict) and "featA" in quantile_section:
                payload = quantile_section["featA"]
                for key in _required_keys():
                    assert key in payload, f"{path} 缺 {key}"
                found_flat = True
        assert found_flat, "沒有任何 JSON 出口帶 quantile_returns.featA"

    def test_summary_csv_long_short_spread_has_value(self, report):
        reporter = ICReporter(config={})
        csv_text = reporter.generate_summary_csv(report)
        rows = list(csv.DictReader(StringIO(csv_text)))
        assert rows, "CSV 空"
        spread_cols = [c for c in rows[0].keys() if "long_short_spread" in c]
        assert spread_cols, f"CSV 無 long_short_spread 欄：{list(rows[0].keys())}"
        value = rows[0][spread_cols[0]]
        assert value not in ("", "None", None), "long_short_spread 欄無值"
        assert abs(float(value) - 0.025) < 1e-12

    def test_save_report_roundtrip_flat(self, report, tmp_path):
        reporter = ICReporter(config={})
        paths = reporter.save_report(report, str(tmp_path), "ichc_matrix")
        json_paths = [p for p in paths.values() if str(p).endswith(".json")]
        assert json_paths, f"save_report 無 JSON：{paths}"
        reloaded = json.loads(open(json_paths[0], encoding="utf-8").read())
        payload = reloaded["quantile_returns"]["featA"]
        for key in _required_keys():
            assert key in payload
        assert payload["long_short_tstat"] == 1.9
