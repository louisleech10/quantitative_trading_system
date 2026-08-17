"""ICHC Task 6.2 — split_method 誠實標示測試。"""

import pytest

from momentum.Analysis.ic_config_schema import load_report_contract
from tests.momentum.helpers.ichc_run import run_analyze


@pytest.mark.slow
class TestSplitMethodMetadata:
    @pytest.fixture(scope="class")
    def report(self):
        return run_analyze()

    def test_split_method_is_holdout_on_default_path(self, report):
        assert report["metadata"]["split_method"] == "holdout"

    def test_value_in_contract_enum(self, report):
        contract = load_report_contract()
        assert report["metadata"]["split_method"] in contract["split_method"]

    def test_fallback_marks_full_sample(self):
        """fallback 路徑（事件小子集觸發 warmup fallback）→ split_method 顯式標示。"""
        from tests.momentum.helpers.ichc_run import feature_index

        fallback_report = run_analyze(
            config_override={"event_filter": {"enabled": True}},
            event_timestamps=list(feature_index(400)),
        )
        assert fallback_report["metadata"]["split_method"] == "full_sample_fallback"
