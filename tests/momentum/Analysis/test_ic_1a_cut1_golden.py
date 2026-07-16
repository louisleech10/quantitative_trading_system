from __future__ import annotations

import asyncio
import copy
import json
import time
from pathlib import Path
from typing import Any

import pytest

from api.models.ic_models import FeatureFilterConfig, ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
]


# ---------------------------------------------------------------------------
# Legacy G-OLD/G-NEW paths（檔案保留；B6 不再對 20k×50 全量 API report deep-equal）
# ---------------------------------------------------------------------------
BASE_DIR = Path("tests/golden/ic_phase1_1a_cut1")
BASELINE_PATH = BASE_DIR / "baseline_old_btc_1h_a384e6d2.json"
BASELINE_NEW_PATH = BASE_DIR / "baseline_new_btc_1h_a384e6d2.json"
FEATURES_PATH = (
    BASE_DIR
    / "inputs"
    / "BTCUSDT_1h_a384e6d22ca15fc639757cb3162e7cb3_top50.h5"
)
META_PATH = (
    BASE_DIR
    / "inputs"
    / "BTCUSDT_1h_a384e6d22ca15fc639757cb3162e7cb3_top50_meta.json"
)
CONFIG_HASH = "a384e6d22ca15fc639757cb3162e7cb3"
GENERATED_AT_EXEMPTION = {"generated_at"}

# B6 after golden（強 gate）
LA0_DIR = Path("tests/golden/la0")
BEFORE_BTC = LA0_DIR / "BTCUSDT_1h_baseline.json"
AFTER_BTC = LA0_DIR / "BTCUSDT_1h_baseline_after.json"
AFTER_BTC_SPLIT_OFF = LA0_DIR / "BTCUSDT_1h_baseline_after_split_off.json"
BEFORE_ETH = LA0_DIR / "ETHUSDT_12h_baseline.json"
AFTER_ETH = LA0_DIR / "ETHUSDT_12h_baseline_after.json"
AFTER_ETH_SPLIT_OFF = LA0_DIR / "ETHUSDT_12h_baseline_after_split_off.json"
ATTR = LA0_DIR / "attribution.json"


def _without_generated_at(payload: dict[str, Any]) -> dict[str, Any]:
    """供外部 caller 正規化 payload（保留 API）。"""
    normalized = copy.deepcopy(payload)
    for key in GENERATED_AT_EXEMPTION:
        normalized.pop(key, None)
    return normalized


async def _run_baseline(
    *, split_on: bool, timeout_seconds: int = 120
) -> dict[str, Any]:
    """供 redirect A/B 等 caller 重用（非 B6 主 gate）。"""
    service = ICAnalysisService()
    request = ICAnalyzeRequest(
        features_path=str(FEATURES_PATH.resolve()),
        meta_path=str(META_PATH.resolve()),
        symbol="BTCUSDT",
        timeframe="1h",
        config_hash=CONFIG_HASH,
        mode="longitudinal",
        config_override={"ic_train_test_split": split_on},
        feature_filter=FeatureFilterConfig(max_features=50),
    )
    started = await service.start_analysis(request)
    task_id = started["task_id"]
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        status = service.get_task_status(task_id)
        if status and status.get("status") == "completed":
            result = service.get_result(task_id)
            if result is None:
                raise AssertionError("completed IC task returned no result")
            return result
        if status and status.get("status") == "failed":
            raise AssertionError(f"IC task failed: {status.get('error')}")
        await asyncio.sleep(0.25)

    raise TimeoutError(f"IC golden run timed out: task_id={task_id}")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_la0_after_gate() -> None:
    """B6 強 gate：after golden + attribution control-stable（雙 symbol）。"""
    assert BEFORE_BTC.is_file() and AFTER_BTC.is_file()
    assert BEFORE_ETH.is_file() and AFTER_ETH.is_file()
    assert ATTR.is_file()

    before_btc = _load(BEFORE_BTC)
    after_btc = _load(AFTER_BTC)
    before_eth = _load(BEFORE_ETH)
    after_eth = _load(AFTER_ETH)
    attr = _load(ATTR)

    assert before_btc.get("pit_stats_version") == "pre_la0_baseline"
    assert after_btc.get("baseline_role") == "after_pit"
    assert after_eth.get("baseline_role") == "after_pit"
    assert after_btc.get("pit_stats_version") not in (None, "pre_la0_baseline")

    assert (
        after_btc["input_contract"]["features_h5_sha256"]
        == before_btc["input_contract"]["features_h5_sha256"]
    )
    assert (
        after_eth["input_contract"]["features_h5_sha256"]
        == before_eth["input_contract"]["features_h5_sha256"]
    )

    def _ric_sha(bl: dict, feature: str, window: str) -> str:
        return bl["rolling_ic"]["per_feature_window"][feature][window]["sha256"]

    def _pearson_sha(bl: dict, feature: str, window: str) -> str:
        return bl["control"]["pearson_rolling_ic"]["per_feature_window"][feature][
            window
        ]["sha256"]

    f0 = next(iter(before_btc["rolling_ic"]["per_feature_window"]))
    w0 = next(iter(before_btc["rolling_ic"]["per_feature_window"][f0]))
    # spearman 必變；pearson control 必不變
    assert _ric_sha(before_btc, f0, w0) != _ric_sha(after_btc, f0, w0)
    assert _pearson_sha(before_btc, f0, w0) == _pearson_sha(after_btc, f0, w0)

    f1 = next(iter(before_eth["rolling_ic"]["per_feature_window"]))
    w1 = next(iter(before_eth["rolling_ic"]["per_feature_window"][f1]))
    assert _ric_sha(before_eth, f1, w1) != _ric_sha(after_eth, f1, w1)
    assert _pearson_sha(before_eth, f1, w1) == _pearson_sha(after_eth, f1, w1)

    assert attr["summary"]["n_unexpected"] == 0
    assert attr["summary"]["control_stable"] is True
    for row in attr["rows"]:
        if row.get("component") == "control" or str(row["name"]).startswith(
            "control_"
        ):
            assert abs(float(row["delta"])) <= 1e-12


def test_flag_off_deep_equal_baseline() -> None:
    """G-OLD / flag-off 強 gate：split-OFF after-golden + **live** deep-equal。

    Codex DATA-CORRECT ⑤：禁只驗靜態 artifact；須實跑 analyze(split OFF)
    → element 級 deep-equal vs ``*_baseline_after_split_off.json``。
    """
    from tests.golden.la0.build_after_and_attribution import (  # noqa: WPS433
        SPLIT_OFF_OVERRIDE,
        collect_after_from_frozen,
        metric_value,
    )

    assert AFTER_BTC_SPLIT_OFF.is_file() and AFTER_ETH_SPLIT_OFF.is_file()
    assert ATTR.is_file()
    attr = _load(ATTR)
    assert attr["summary"]["n_unexpected"] == 0
    assert attr["summary"]["control_stable"] is True

    for after_path, before_path, key in (
        (AFTER_BTC_SPLIT_OFF, BEFORE_BTC, "BTCUSDT_1h"),
        (AFTER_ETH_SPLIT_OFF, BEFORE_ETH, "ETHUSDT_12h"),
    ):
        before = _load(before_path)
        golden = _load(after_path)
        assert golden.get("baseline_role") == "after_pit_split_off"
        assert golden.get("config_snapshot", {}).get("ic_train_test_split") is False
        fit_mode = (golden.get("stage1") or {}).get("preproc_log", {}).get("fit_mode")
        assert fit_mode == "pit_expanding", f"{key}: golden fit_mode={fit_mode}"

        live, _ = collect_after_from_frozen(
            before,
            config_override=SPLIT_OFF_OVERRIDE,
            baseline_role="after_pit_split_off",
        )
        assert live["config_snapshot"]["ic_train_test_split"] is False
        live_fit = (live.get("stage1") or {}).get("preproc_log", {}).get("fit_mode")
        assert live_fit == "pit_expanding"

        for metric in (
            "control_pearson_rolling_ic",
            "rolling_ic_spearman",
            "mono_bin_t",
            "monotonicity_score",
            "turnover_time_series",
            "turnover_scalar",
            "stage1_winsorize_full_sample_fallback",
        ):
            assert metric_value(golden, metric) == metric_value(live, metric), (
                f"flag-off live deep-equal fail: {key}/{metric}"
            )

    if BASELINE_PATH.exists():
        legacy = _load(BASELINE_PATH)
        assert isinstance(legacy, dict)
        assert legacy.get("baseline_role") != "after_pit_split_off"


def test_flag_on_matches_new_golden() -> None:
    """G-NEW / flag-on 強 gate：split-ON after golden + live deep-equal。"""
    from tests.golden.la0.build_after_and_attribution import (  # noqa: WPS433
        collect_after_from_frozen,
        metric_value,
    )

    _assert_la0_after_gate()
    after = _load(AFTER_BTC)
    assert after.get("config_snapshot", {}).get("ic_train_test_split") is True
    assert int(after.get("counts", {}).get("test_rows") or 0) > 0

    # live re-analyze（split ON 預設）vs after golden
    before = _load(BEFORE_BTC)
    live, _ = collect_after_from_frozen(before)
    assert live["config_snapshot"]["ic_train_test_split"] is True
    for metric in (
        "control_pearson_rolling_ic",
        "rolling_ic_spearman",
        "mono_bin_t",
        "turnover_time_series",
        "stage1_winsorize_full_sample_fallback",
    ):
        assert metric_value(after, metric) == metric_value(live, metric), (
            f"flag-on live deep-equal fail: {metric}"
        )

    if BASELINE_NEW_PATH.exists():
        legacy = _load(BASELINE_NEW_PATH)
        assert isinstance(legacy, dict)
