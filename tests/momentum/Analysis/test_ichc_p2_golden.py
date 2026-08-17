"""ICHC Task 2.1 — T-G1 golden 對照＋M1 mutation＋flatten 單元（§G）。

Oracle：真實 kline 衍生 fixture（ETHUSDT/12h）跑主流程，與凍結 receipt
`handoffs/run_receipts/ichc_p2_golden_pre.json` 逐 feature 逐 path exact 比對。
序列化與抽取共用 scripts/ichc_freeze_p2_golden.py 的 helper（單一實作）。
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RECEIPT = REPO / "handoffs/run_receipts/ichc_p2_golden_pre.json"


def _load_helpers():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ichc_freeze_p2_golden", REPO / "scripts/ichc_freeze_p2_golden.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def helpers():
    return _load_helpers()


@pytest.fixture(scope="module")
def frozen_receipt():
    if not RECEIPT.exists():
        pytest.fail(f"golden receipt 缺席（先跑 scripts/ichc_freeze_p2_golden.py）：{RECEIPT}")
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live_receipt(helpers):
    report, config_hash = helpers.run_analyze()
    return helpers.build_receipt(report, config_hash)


class TestTG1Golden:
    def test_feature_set_and_config_exact(self, frozen_receipt, live_receipt):
        assert live_receipt["config_hash"] == frozen_receipt["config_hash"]
        assert (
            live_receipt["feature_set_sha256"] == frozen_receipt["feature_set_sha256"]
        )
        assert live_receipt["n_features"] == frozen_receipt["n_features"]

    def test_per_feature_canonical_exact(self, frozen_receipt, live_receipt):
        """逐 feature 逐 path exact（atol=0）；差異列出 feature+path。"""
        diffs = []
        frozen = frozen_receipt["per_feature"]
        live = live_receipt["per_feature"]
        for feature in sorted(set(frozen) | set(live)):
            if feature not in frozen or feature not in live:
                diffs.append(f"{feature}: 存在性不一致")
                continue
            if frozen[feature] != live[feature]:
                for key in sorted(set(frozen[feature]) | set(live[feature])):
                    if frozen[feature].get(key) != live[feature].get(key):
                        diffs.append(
                            f"{feature}.{key}: frozen={frozen[feature].get(key)!r} "
                            f"live={live[feature].get(key)!r}"
                        )
        assert not diffs, "golden 不一致：\n" + "\n".join(diffs[:20])


class TestFlattenUnit:
    """flatten 映射單元（不跑 pipeline）。"""

    def _reporter(self):
        from momentum.Analysis.ic_reporter import ICReporter

        return ICReporter(config={})

    def test_nested_payload_lifts_to_root(self):
        nested = {
            "featA": {
                "quantile_returns": {
                    "quantile_mean_returns": {"Q1": 0.1, "Q2": 0.2},
                    "cumulative_returns": {"Q1": [0.1], "Q2": [0.2]},
                    "long_short_spread": 0.1,
                    "long_short_tstat": 1.5,
                },
                "monotonicity_score": 0.8,
                "long_short": {"spread": 0.1, "tstat": 1.5},
            }
        }
        flat = self._reporter()._flatten_quantile_returns(nested)
        payload = flat["featA"]
        assert payload["quantile_mean_returns"] == {"Q1": 0.1, "Q2": 0.2}
        assert payload["long_short_spread"] == 0.1
        assert payload["long_short_tstat"] == 1.5
        assert payload["monotonicity_score"] == 0.8
        assert payload["cumulative_returns"] == {"Q1": [0.1], "Q2": [0.2]}

    def test_already_flat_passes_through(self):
        flat_in = {
            "featB": {
                "quantile_mean_returns": {"Q1": 0.3},
                "cumulative_returns": {},
                "long_short_spread": 0.0,
                "long_short_tstat": 0.0,
                "monotonicity_score": 0.5,
            }
        }
        assert self._reporter()._flatten_quantile_returns(flat_in) == flat_in

    def test_status_object_passes_through(self):
        status_in = {"featC": {"status": "not_applicable", "reason": "cross_sectional_mode"}}
        assert self._reporter()._flatten_quantile_returns(status_in) == status_in

    def test_m1_mutation_probe_key_rename_breaks_golden_shape(self, helpers):
        """M1 等價探針：映射鍵改名（模擬）→ canonical 抽取結果必變。"""
        base = {
            "featD": {
                "quantile_returns": {
                    "quantile_mean_returns": {"Q1": 0.1},
                    "cumulative_returns": {"Q1": [0.1]},
                    "long_short_spread": 0.2,
                    "long_short_tstat": 1.0,
                },
                "monotonicity_score": 0.7,
            }
        }
        good = helpers.extract_quantile_canonical(
            self._reporter()._flatten_quantile_returns(base)
        )
        mutated = {
            "featD": {
                "quantile_returns": {
                    "quantile_mean_returns_RENAMED": {"Q1": 0.1},
                    "cumulative_returns": {"Q1": [0.1]},
                    "long_short_spread": 0.2,
                    "long_short_tstat": 1.0,
                },
                "monotonicity_score": 0.7,
            }
        }
        bad = helpers.extract_quantile_canonical(
            self._reporter()._flatten_quantile_returns(mutated)
        )
        assert good != bad
        assert (
            good["featD"]["canonical_sha256"] != bad["featD"]["canonical_sha256"]
        )
