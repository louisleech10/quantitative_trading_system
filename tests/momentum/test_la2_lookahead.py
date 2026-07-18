"""LA-2 M-lookahead 測試骨架（B0 predeclare 12 nodeid；B1-B3 填實）。

SPEC: docs/IC_LA2_SPEC.md
TODO: docs/IC_LA2_TODO.md Task 0.3（T16/U20；TODO 12 nodeid 為權威）

collect == 12:
  - test_winsorized_disabled
  - test_model_oot_contract
  - test_model_service_oot
  - test_config_theater
  - test_calibrator_receipt
  - test_pattern_train_mask
  - test_pattern_promotion_guard
  - test_plan_identity_mismatch
  - test_regime_no_global_fit
  - test_factor_loud
  - test_adversarial_validator_diagnostic_only
  - test_analysis_status_diagnostic

骨架 xfail（B4 final gate 禁殘留 skip/xfail；B1-B3 去 xfail 填實）。
collect 不觸 data_cache 副作用。
"""

from __future__ import annotations

import pytest

# 契約：恰 12 nodeid（--collect-only 驗收）
EXPECTED_NODEID_COUNT = 12
EXPECTED_NODEIDS = (
    "test_winsorized_disabled",
    "test_model_oot_contract",
    "test_model_service_oot",
    "test_config_theater",
    "test_calibrator_receipt",
    "test_pattern_train_mask",
    "test_pattern_promotion_guard",
    "test_plan_identity_mismatch",
    "test_regime_no_global_fit",
    "test_factor_loud",
    "test_adversarial_validator_diagnostic_only",
    "test_analysis_status_diagnostic",
)

_XFAIL_REASON = "LA-2 B0 skeleton: filled in B1/B2/B3 (TODO Task 0.3)"


# strict=True：意外 XPASS 必紅（B0-F7；B1-B3 去 xfail 填實時改 mark）
@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_winsorized_disabled() -> None:
    """B1：winsorized 三層 raise（LOOKAHEAD_LABEL_UNSUPPORTED）。"""
    raise NotImplementedError("B1 Task 1.1")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_model_oot_contract() -> None:
    """B2：analyzer 診斷 eval_scope + OOT horizon 嚴格 <。"""
    raise NotImplementedError("B2 Task 2.1")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_model_service_oot() -> None:
    """B2：service 全矩陣 scope + recommend_k OOT。"""
    raise NotImplementedError("B2 Task 2.2")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_config_theater() -> None:
    """B2：calibrator/sample_weight enabled≠wired 可見。"""
    raise NotImplementedError("B2 Task 2.3")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_calibrator_receipt() -> None:
    """B2：CalibratorReceipt 兩分支缺 receipt → raise。"""
    raise NotImplementedError("B2 Task 2.2")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_pattern_train_mask() -> None:
    """B3：pattern train-mask + train-y 統計。"""
    raise NotImplementedError("B3 Task 3.2")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_pattern_promotion_guard() -> None:
    """B3：晉升 server 權威（create+PUT）。"""
    raise NotImplementedError("B3 Task 3.2")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_plan_identity_mismatch() -> None:
    """B3：pattern/model plan_hash mismatch → fail-closed。"""
    raise NotImplementedError("B3 Task 3.2")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_regime_no_global_fit() -> None:
    """B3：_fit_global / expanding 參數移除不可達。"""
    raise NotImplementedError("B3 Task 3.1")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_factor_loud() -> None:
    """B3：factor typed loud + market_proxy 因果化。"""
    raise NotImplementedError("B3 Task 3.3")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_adversarial_validator_diagnostic_only() -> None:
    """B3：adversarial_validator diagnostic_only 標記。"""
    raise NotImplementedError("B3 Task 3.4")


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_analysis_status_diagnostic() -> None:
    """B3/B4：analysis_status=diagnostic_only + consumer deny。"""
    raise NotImplementedError("B3 Task 3.4 / B4")
