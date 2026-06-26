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


def _without_generated_at(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    for key in GENERATED_AT_EXEMPTION:
        normalized.pop(key, None)
    return normalized


async def _run_baseline(
    *, split_on: bool, timeout_seconds: int = 120
) -> dict[str, Any]:
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


def test_flag_off_deep_equal_baseline() -> None:
    """G-OLD：flag off 與 baseline 逐位元組一致（僅豁免 generated_at）。"""
    if not BASELINE_PATH.exists():
        pytest.skip("G-OLD baseline file is absent")
    if not FEATURES_PATH.exists() or not META_PATH.exists():
        pytest.skip("G-OLD materialized inputs are absent")

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    actual = asyncio.run(_run_baseline(split_on=False))

    assert GENERATED_AT_EXEMPTION == {"generated_at"}
    assert _without_generated_at(actual) == _without_generated_at(baseline)


def test_flag_on_matches_new_golden() -> None:
    """G-NEW：flag on（OOS applied:true）與 baseline_new 一致（豁免 generated_at）。"""
    if not BASELINE_NEW_PATH.exists():
        pytest.skip("G-NEW baseline file is absent")
    if not FEATURES_PATH.exists() or not META_PATH.exists():
        pytest.skip("G-NEW materialized inputs are absent")

    baseline = json.loads(BASELINE_NEW_PATH.read_text(encoding="utf-8"))
    actual = asyncio.run(_run_baseline(split_on=True))

    # 確認 G-NEW 是真 OOS：輸出層 surfaced discriminator = metadata.scope=="test"
    assert actual.get("metadata", {}).get("scope") == "test"
    assert _without_generated_at(actual) == _without_generated_at(baseline)
