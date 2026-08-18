"""Task 3.4 — `StrategyValidationReporter`：唯一消費冠軍 trial 之 API 路徑上的「降級展示＋警語」（不拒絕）。

SPEC ref：Task 3.4 ＋ A1-8（介面／三鍵投影）／A1-16（例外收窄＋入口語意二分）。

入口語意二分（🔴 不得混同）：
- `dataset_key`／`t_years`／`target_sharpe` 任一為 `None` ＝「**未提供**」⇒ **不**呼叫 `read_trial_ledger`／
  `assess_eligibility`，直接組誠實 `EligibilityResult(eligible=None, status="unavailable", reason="n_unknown",
  n_source="assumed_not_ledgered")` → `build_validation_section(dsr=None, pbo=None)`；正常路徑不製造例外。
- 「**提供了但非法**」（`t_years<=0`／`target_sharpe<=0`）＝呼叫方 bug ⇒ 交由 `assess_eligibility` raise
  `InvalidValidationArgument` 並**上拋**（route → 5xx），**不得**正規化為 unavailable。
例外分類：只捕 `(OSError, json.JSONDecodeError, ContractViolation)` ⇒ 各節 `status="computation_failed"`、
`reason="reporter_failed"`；例外文字只進 log、不進回應。其他例外（含 `ValueError`／`InvalidValidationArgument`）一律上拋。
🔴 **禁** `dataset_key=f"trial:{trial_number}"` 之自創公式（per-trial 鍵使 N≡1）；dataset 級鍵由 G1-R1 生產者契約提供。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from momentum.Analysis.strategy_validation.contract import ContractViolation
from momentum.Analysis.strategy_validation.ledger import read_trial_ledger
from momentum.Analysis.strategy_validation.min_btl import EligibilityResult, assess_eligibility
from momentum.Analysis.strategy_validation.report import WARNING_TEXT_KEY, build_validation_section
from momentum.core.logging import get_logger

logger = get_logger(__name__)

_STATUS_UNAVAILABLE = "unavailable"
_STATUS_COMPUTATION_FAILED = "computation_failed"
_REASON_N_UNKNOWN = "n_unknown"
_REASON_REPORTER_FAILED = "reporter_failed"
_N_SOURCE_ASSUMED = "assumed_not_ledgered"


def _failed_section() -> Dict[str, Any]:
    """捕獲之資料型例外 ⇒ 契約合法之五節降級結構（各節 computation_failed／reporter_failed；靜態字面，無動態字串）。"""
    return {
        "eligibility": {
            "eligible": None,
            "required_years_upper_bound": None,
            "available_years": None,
            "trials_budget": None,
            "trials_used": None,
            "target_sharpe": None,
            "n_source": _N_SOURCE_ASSUMED,
            "display_downgrade": True,
            "warning_text_key": WARNING_TEXT_KEY,
            "status": _STATUS_COMPUTATION_FAILED,
            "reason": _REASON_REPORTER_FAILED,
        },
        "min_btl": {
            "status": _STATUS_COMPUTATION_FAILED,
            "reason": _REASON_REPORTER_FAILED,
            "required_years_upper_bound": None,
            "available_years": None,
            "trials_budget": None,
            "trials_used": None,
            "target_sharpe": None,
        },
        "dsr": {
            "status": _STATUS_COMPUTATION_FAILED,
            "reason": _REASON_REPORTER_FAILED,
            "value": None,
            "sr0": None,
            "sr_obs_per_period": None,
            "n_trials_used": None,
            "variance_source": None,
            "n_independence": None,
        },
        "pbo": {
            "status": _STATUS_COMPUTATION_FAILED,
            "reason": _REASON_REPORTER_FAILED,
            "value": None,
            "n_paths_used": None,
            "n_paths_skipped": None,
            "n_candidates_invalid": None,
            "universe_scope": None,
        },
        "provenance": {
            "status": _STATUS_COMPUTATION_FAILED,
            "reason": _REASON_REPORTER_FAILED,
            "n_semantics": None,
            "t_semantics": None,
            "annualization_source": None,
            "n_independence": None,
        },
        "display_downgrade": True,
        "warning_text_key": WARNING_TEXT_KEY,
    }


class StrategyValidationReporter:
    """三關結果之 API 投影來源（今日只有 MinBTL 資格路徑；DSR／PBO 為 `None` ⇒ 誠實 not_computed）。"""

    def for_study_trial(
        self,
        study_name: str,
        trial_number: int,
        *,
        dataset_key: Optional[str] = None,
        t_years: Optional[float] = None,
        target_sharpe: Optional[float] = None,
    ) -> Dict[str, Any]:
        """回傳 `build_validation_section` 之完整五節 dict（route 只投影三鍵）。

        Raises:
            InvalidValidationArgument／ValueError／其他非資料型例外：一律上拋（呼叫方 bug 須可觀測）。
        """
        try:
            if dataset_key is None or t_years is None or target_sharpe is None:
                eligibility = EligibilityResult(
                    eligible=None,
                    required_years_upper_bound=None,
                    available_years=None,
                    trials_budget=None,
                    trials_used=None,
                    target_sharpe=None,
                    n_source=_N_SOURCE_ASSUMED,
                    status=_STATUS_UNAVAILABLE,
                    reason=_REASON_N_UNKNOWN,
                )
                provenance = {"status": _STATUS_UNAVAILABLE, "reason": _REASON_N_UNKNOWN}
                return build_validation_section(eligibility=eligibility, dsr=None, pbo=None, provenance=provenance)

            ledger = read_trial_ledger(research_session_id=study_name, dataset_key=dataset_key)
            eligibility = assess_eligibility(t_years=t_years, ledger_result=ledger, target_sharpe=target_sharpe)
            provenance = {
                "status": ledger.status,
                "reason": ledger.reason,
                "n_semantics": ledger.n_semantics,
            }
            return build_validation_section(eligibility=eligibility, dsr=None, pbo=None, provenance=provenance)
        except (OSError, json.JSONDecodeError, ContractViolation):
            logger.error("strategy_validation reporter failed", exc_info=True)
            return _failed_section()
