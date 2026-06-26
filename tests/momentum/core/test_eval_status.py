from __future__ import annotations

from momentum.core.contracts import EvaluationStatus, ICResult, filter_evaluated


def _ic_result(
    feature_name: str,
    eval_status: EvaluationStatus = EvaluationStatus.UNKNOWN_LEGACY,
) -> ICResult:
    return ICResult(
        feature_name=feature_name,
        ic_mean=0.1,
        ic_std=0.2,
        icir=0.5,
        p_value=0.03,
        ic_hit_rate=0.6,
        eval_status=eval_status,
    )


def test_only_explicit_evaluated_ranked() -> None:
    results = [
        _ic_result("evaluated_a", EvaluationStatus.EVALUATED),
        _ic_result("not_evaluated", EvaluationStatus.NOT_EVALUATED),
        _ic_result("skipped", EvaluationStatus.SKIPPED),
        _ic_result("legacy"),
        _ic_result("evaluated_b", EvaluationStatus.EVALUATED),
    ]

    evaluated = filter_evaluated(results)

    assert [result.feature_name for result in evaluated] == [
        "evaluated_a",
        "evaluated_b",
    ]


def test_legacy_not_counted() -> None:
    legacy_result = _ic_result("legacy")
    skipped_result = _ic_result("skipped", EvaluationStatus.SKIPPED)

    assert legacy_result.eval_status == EvaluationStatus.UNKNOWN_LEGACY
    assert filter_evaluated([legacy_result, skipped_result]) == []
