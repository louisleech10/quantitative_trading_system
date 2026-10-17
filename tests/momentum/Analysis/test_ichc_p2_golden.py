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


# TESTREG b5：receipt 凍結（a943e500，2026-08-17）後 ICConfig **只新增**下列預設欄、既有欄預設值零變更
# （以 a943e500 版 ic_config_schema.py 重算 model_dump 之雜湊＝凍結值 c1616bdf…，逐鍵比對僅 ADDED）。
# config 雜湊比對改為：現行預設 config 剔除此具名清單後須與凍結雜湊 byte 相同——既有欄任一預設改動、
# 或未登記之新欄，仍會紅。新增欄對 golden 數值無影響由 test_per_feature_canonical_exact 逐 path exact 把關。
_ICCONFIG_FIELDS_ADDED_SINCE_FREEZE = (
    ("marginal_ic",),  # ab53c24e 2026-08-19
    ("event_filter", "min_test_events"),  # 39b48531 2026-09-08
    ("event_filter", "min_events_per_class"),  # a69287f3 2026-09-10
    ("event_filter", "negative_control_n"),  # a69287f3
    ("event_filter", "oracle_seed"),  # a69287f3
    ("event_filter", "perm_budget_total"),  # a69287f3
    ("event_filter", "negative_control_budget_seconds"),  # 77aa5817 2026-09-10
    ("thresholds", "rank_biserial_min"),  # a69287f3
)


def _config_hash_without_post_freeze_fields(helpers) -> str:
    import hashlib

    from momentum.Analysis.ic_config_schema import ICConfig

    dump = ICConfig().model_dump(mode="json")
    for path in _ICCONFIG_FIELDS_ADDED_SINCE_FREEZE:
        node = dump
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]  # 欄若被移除／改名 ⇒ KeyError，須回頭檢視
    return hashlib.sha256(helpers.canonical_json_bytes(dump)).hexdigest()


class TestTG1Golden:
    def test_feature_set_and_config_exact(self, helpers, frozen_receipt, live_receipt):
        import hashlib

        from momentum.Analysis.ic_config_schema import ICConfig

        # live 主流程所用 config 即現行預設 ICConfig（全量雜湊）
        assert live_receipt["config_hash"] == hashlib.sha256(
            helpers.canonical_json_bytes(ICConfig().model_dump(mode="json"))
        ).hexdigest()
        # 剔除凍結後新增之具名欄 ⇒ 與凍結雜湊 byte 相同
        assert _config_hash_without_post_freeze_fields(helpers) == frozen_receipt["config_hash"]
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

    def test_m1_mutation_probe_key_rename_breaks_golden_shape(self, helpers, monkeypatch):
        """M1 等價探針：映射鍵改名（模擬）→ canonical 抽取結果必變。

        TESTREG b5：原寫法只改「測試輸入字典」之鍵名，未變異生產 `_flatten_quantile_returns`，
        只證「不同輸入得不同雜湊」。改為對生產 flatten 注入變異（輸入不變），斷言 golden 抽取可分辨。
        """
        from momentum.Analysis.ic_reporter import ICReporter

        base = {
            "featD": {
                "quantile_returns": {
                    "quantile_mean_returns": {"Q1": 0.1},
                    "cumulative_returns": {"Q1": [0.1]},
                    "long_short_tstat": 1.0,
                },
                "monotonicity_score": 0.7,
                "long_short": {"spread": 0.2, "tstat": 1.0},
            }
        }
        good = helpers.extract_quantile_canonical(
            self._reporter()._flatten_quantile_returns(base)
        )
        assert good["featD"] == helpers.extract_quantile_canonical(
            {
                "featD": {
                    "quantile_mean_returns": {"Q1": 0.1},
                    "cumulative_returns": {"Q1": [0.1]},
                    "long_short_spread": 0.2,
                    "long_short_tstat": 1.0,
                    "monotonicity_score": 0.7,
                }
            }
        )["featD"]

        original = ICReporter._flatten_quantile_returns

        def _rename_qmr(qr_tree):
            # 變異①：攤平映射把 quantile_mean_returns 改名
            return {
                feature: (
                    {("quantile_mean_returns_RENAMED" if k == "quantile_mean_returns" else k): v
                     for k, v in payload.items()}
                    if isinstance(payload, dict) else payload
                )
                for feature, payload in original(qr_tree).items()
            }

        def _drop_long_short_lift(qr_tree):
            # 變異②：漏做 long_short.spread → long_short_spread 上提
            return {
                feature: (
                    {k: v for k, v in payload.items() if k != "long_short_spread"}
                    if isinstance(payload, dict) else payload
                )
                for feature, payload in original(qr_tree).items()
            }

        for mutant in (_rename_qmr, _drop_long_short_lift):
            monkeypatch.setattr(ICReporter, "_flatten_quantile_returns", staticmethod(mutant))
            bad = helpers.extract_quantile_canonical(
                self._reporter()._flatten_quantile_returns(base)
            )
            assert good != bad
            assert (
                good["featD"]["canonical_sha256"] != bad["featD"]["canonical_sha256"]
            )
