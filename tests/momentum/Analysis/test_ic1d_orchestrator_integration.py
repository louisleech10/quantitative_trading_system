"""IC 1d B3/B4 orchestrator 整合驗收（幽靈契約隔離 + mutation 探針）。

B3 交付:
- module_summary["factor_exposure"] == "completed_partial"
- completed_count 與 p1 baseline 相同（sanitize 後；completed_partial 計入）
- results.factor_exposure 三鏡像 factor_attribution 各 exact 恰三鍵 unavailable
- exposure_hash 不變（哨兵）

B4 交付:
- test_mutation_stub_restored_must_fail / test_mutation_module_summary_completed_must_fail
- test_cache_hit_factor_exposure_completed_partial / test_force_only_factor_exposure_unavailable
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ic1d_baseline_freeze import (  # noqa: E402
    OUT_DIR,
    run_production_deep_analysis,
)

KLINE_CACHE = REPO_ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
P1_BASELINE = OUT_DIR / "p1_after_rename.json"

# 與 orchestrator stub reason 一字對齊（D-4 / Task 3.1）
ATTR_NOT_WIRED_REASON = (
    "attribution_not_wired_to_canonical_contract"
    "（單標的 canonical FR 下迴歸 ill-posed；"
    "接真需另定 portfolio_returns 與 RHS 契約，見 ROADMAP 票A/票B）"
)
EXPECTED_ATTR_UNAVAILABLE = {
    "status": "unavailable",
    "value": None,
    "reason": ATTR_NOT_WIRED_REASON,
}

# 三鏡像路徑（B3 幽靈契約隔離；comparator --allow-change 子樹後門需各鏡像 exact-assert）
MIRROR_PATHS = (
    "results.factor_exposure.factor_attribution",
    "results.factor_exposure.payload.summary.factor_attribution",
    "results.factor_exposure.typed_result.payload.summary.factor_attribution",
)


def _require_kline() -> None:
    if not KLINE_CACHE.is_file():
        pytest.fail(f"requires_kline: missing {KLINE_CACHE}")


def _require_p1() -> dict[str, Any]:
    if not P1_BASELINE.is_file():
        pytest.fail(f"requires p1 baseline: missing {P1_BASELINE}")
    return json.loads(P1_BASELINE.read_text(encoding="utf-8"))


def _exposure_hash_from_fe(fe: Any) -> str | None:
    if not isinstance(fe, dict):
        return None
    payload = fe.get("payload")
    if isinstance(payload, dict):
        h = payload.get("exposure_hash")
        if isinstance(h, str) and h:
            return h
    if payload is not None and hasattr(payload, "exposure_hash"):
        h = getattr(payload, "exposure_hash", None)
        if isinstance(h, str) and h:
            return h
    return None


def _summary_from_payload(payload: Any) -> dict[str, Any] | None:
    """自 payload（dict 或 dataclass）取 summary dict。"""
    if payload is None:
        return None
    if isinstance(payload, dict):
        summary = payload.get("summary")
    else:
        summary = getattr(payload, "summary", None)
    return summary if isinstance(summary, dict) else None


def _payload_from_typed(typed: Any) -> Any:
    if typed is None:
        return None
    if isinstance(typed, dict):
        return typed.get("payload")
    return getattr(typed, "payload", None)


def _factor_attribution_mirrors(fe: Any) -> dict[str, Any]:
    """收集 fe 上「存在」的 factor_attribution 鏡像。

    路徑（與 handoff ⑤ / p3 golden 對齊）:
      1. results.factor_exposure.factor_attribution
      2. results.factor_exposure.payload.summary.factor_attribution
      3. results.factor_exposure.typed_result.payload.summary.factor_attribution

    存在幾個以真實 report 為準；呼叫端對**每個存在的**鏡像 exact-assert。
    反例：若某鏡像被塞 alpha=123，該鏡像 ``== EXPECTED_ATTR_UNAVAILABLE`` 應紅
    （comparator --allow-change ...factor_attribution 子樹無法再遮蔽第二/三鏡像）。
    """
    mirrors: dict[str, Any] = {}
    if not isinstance(fe, dict):
        return mirrors

    # 1) 頂層（out.update(summary)）
    if "factor_attribution" in fe:
        mirrors[MIRROR_PATHS[0]] = fe.get("factor_attribution")

    # 2) payload.summary
    summary = _summary_from_payload(fe.get("payload"))
    if summary is not None and "factor_attribution" in summary:
        mirrors[MIRROR_PATHS[1]] = summary.get("factor_attribution")

    # 3) typed_result.payload.summary
    tp_summary = _summary_from_payload(_payload_from_typed(fe.get("typed_result")))
    if tp_summary is not None and "factor_attribution" in tp_summary:
        mirrors[MIRROR_PATHS[2]] = tp_summary.get("factor_attribution")

    return mirrors


def _assert_exact_unavailable(path: str, fa: Any) -> None:
    """恰三鍵 unavailable exact-assert（無殘留數值欄如 alpha）。

    反例：fa = {**EXPECTED, "alpha": 123} 或 fa["alpha"]=123 → 本 assert 必須紅。
    """
    assert fa == EXPECTED_ATTR_UNAVAILABLE, (
        f"{path}: factor_attribution must be exact three-key unavailable, got {fa!r}"
    )
    assert isinstance(fa, dict), f"{path}: expected dict, got {type(fa)}"
    assert set(fa.keys()) == {"status", "value", "reason"}, (
        f"{path}: keys must be exactly {{status,value,reason}}, got {set(fa.keys())!r}"
    )


def test_b3_factor_exposure_completed_partial_and_unavailable_attr():
    """B3 核心：completed_partial + 三鏡像 unavailable 三鍵 + completed_count 不變 + hash 哨兵。"""
    _require_kline()
    p1 = _require_p1()
    p1_completed = int(p1["completed_count"])
    p1_fe = (p1.get("results") or {}).get("factor_exposure") or {}
    p1_hash = _exposure_hash_from_fe(p1_fe)
    assert p1_hash, "p1 baseline must have exposure_hash sentinel"

    _orch, report, _src = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )

    # D-4 牙齒：sanitize 之後 module_summary
    assert report.module_summary.get("factor_exposure") == "completed_partial"

    # D-12：completed_partial 計入 completed → 與 p1 相同
    assert report.completed_count == p1_completed, (
        f"completed_count drifted: got {report.completed_count}, "
        f"p1 baseline={p1_completed}"
    )

    fe = (report.results or {}).get("factor_exposure")
    assert isinstance(fe, dict), f"factor_exposure must be dict, got {type(fe)}"

    # ⑤：三鏡像各 exact-assert 恰三鍵 unavailable
    # （禁只查第一鏡像；comparator 子樹 allow 無法再遮蔽 2nd/3rd）
    # 反例：任一鏡像塞 alpha=123 → 該 path 的 assert 必須紅
    mirrors = _factor_attribution_mirrors(fe)
    assert set(mirrors.keys()) == set(MIRROR_PATHS), (
        f"expected exactly three factor_attribution mirrors {list(MIRROR_PATHS)}, "
        f"got {sorted(mirrors.keys())}"
    )
    for path, fa in mirrors.items():
        _assert_exact_unavailable(path, fa)

    # 頂層鏡像 5 鍵已移除
    for ghost in ("alpha", "r_squared", "attribution", "unexplained", "factor_betas"):
        assert ghost not in fe, f"top-level ghost key still present: {ghost}"

    # exposure_hash 哨兵不變
    got_hash = _exposure_hash_from_fe(fe)
    assert got_hash == p1_hash, (
        f"exposure_hash changed: p1={p1_hash!r} got={got_hash!r}"
    )


def test_force_only_factor_exposure_unavailable():
    """ADV-C6/CM4：force_modules=['factor_exposure'] → completed_partial + 三鍵 exact。"""
    _require_kline()
    _orch, report, _src = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )
    assert report.module_summary.get("factor_exposure") == "completed_partial"
    fe = (report.results or {}).get("factor_exposure")
    assert isinstance(fe, dict)
    fa = fe.get("factor_attribution")
    assert fa == EXPECTED_ATTR_UNAVAILABLE
    assert set(fa.keys()) == {"status", "value", "reason"}
    assert fa["status"] == "unavailable"
    assert fa["value"] is None
    assert fa["reason"] == ATTR_NOT_WIRED_REASON


def test_cache_hit_factor_exposure_completed_partial():
    """ADV-C6/CM4：_deep_analysis_cache 命中 → completed_partial + 三鍵 exact。"""
    _require_kline()
    orch, report1, _src = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )
    # 第一次 force 跑完後 cache 應已寫入
    assert len(orch._deep_analysis_cache) >= 1
    cache_keys = list(orch._deep_analysis_cache.keys())
    assert cache_keys, "expected non-empty _deep_analysis_cache after first deep run"

    # 無 force → cache_hit_only 路徑
    report2 = orch.run_deep_analysis(force_modules=None)
    assert report2.module_summary.get("factor_exposure") == "completed_partial"
    fe = (report2.results or {}).get("factor_exposure")
    assert isinstance(fe, dict)
    fa = fe.get("factor_attribution")
    assert fa == EXPECTED_ATTR_UNAVAILABLE
    assert set(fa.keys()) == {"status", "value", "reason"}
    assert fa["status"] == "unavailable"
    assert fa["value"] is None
    assert fa["reason"] == ATTR_NOT_WIRED_REASON

    # 哨兵：第一次與 cache-hit 結果一致（三鍵 exact）
    fa1 = ((report1.results or {}).get("factor_exposure") or {}).get(
        "factor_attribution"
    )
    assert fa1 == fa == EXPECTED_ATTR_UNAVAILABLE


def test_mutation_stub_restored_must_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """B4：patch ExposurePayload 建構 seam 寫入舊數值形 → 三鍵 exact 斷言必紅。

    最窄 production seam：orchestrator 在 ExposurePayload(...) 封裝 summary 時
    就地改 factor_attribution（同 dict 隨 out.update 上三鏡像），非 runner 事後改 payload。
    """
    import momentum.Analysis.ic_filter_orchestrator as orch_mod

    _require_kline()
    orch, report, _src = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )
    fe = (report.results or {}).get("factor_exposure")
    assert isinstance(fe, dict)
    # 基線綠
    _assert_exact_unavailable(
        "results.factor_exposure.factor_attribution",
        fe.get("factor_attribution"),
    )

    # mutation：最窄 seam — ExposurePayload 建構時把 stub 改成舊數值形
    old_numeric = {
        "alpha": 0.01,
        "r_squared": 0.5,
        "factor_betas": {"f1": 0.1},
        "attribution": {"f1": 0.001},
        "unexplained": 0.01,
    }
    real_ep = orch_mod.ExposurePayload

    def _mut_exposure_payload(  # type: ignore[no-untyped-def]
        *,
        proxy_kind: str,
        exposure_hash: str,
        summary: dict[str, Any],
    ):
        summary["factor_attribution"] = dict(old_numeric)
        return real_ep(
            proxy_kind=proxy_kind,
            exposure_hash=exposure_hash,
            summary=summary,
        )

    monkeypatch.setattr(orch_mod, "ExposurePayload", _mut_exposure_payload)
    orch._clear_deep_analysis_cache()
    mut_report = orch.run_deep_analysis(force_modules=["factor_exposure"])
    mut_fe = (mut_report.results or {}).get("factor_exposure")
    mut_fa = mut_fe.get("factor_attribution") if isinstance(mut_fe, dict) else None
    with pytest.raises(AssertionError):
        _assert_exact_unavailable(
            "results.factor_exposure.factor_attribution", mut_fa
        )
    assert isinstance(mut_fa, dict)
    assert "alpha" in mut_fa
    assert mut_fa.get("status") != "unavailable"


def test_mutation_module_summary_completed_must_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-4：patch runner 回傳的 attribution.status（completed_partial 判定 seam）→ 斷言必紅。

    最窄 seam：D-4 讀 result['factor_attribution'].status=='unavailable' 才寫
    completed_partial；把 status 改掉讓判定走 else→completed。非事後改 module_summary。
    """
    _require_kline()
    orch, report, _src = run_production_deep_analysis(
        force_modules=["factor_exposure"]
    )
    # 基線綠
    assert report.module_summary.get("factor_exposure") == "completed_partial"

    real_runner = orch._run_factor_exposure

    def _bypass_partial_status(selected, config):  # type: ignore[no-untyped-def]
        result = real_runner(selected, config)
        if not isinstance(result, dict):
            return result
        fa = result.get("factor_attribution")
        if isinstance(fa, dict) and fa.get("status") == "unavailable":
            # 只動 D-4 判定欄；production 仍跑完整 runner
            fa = dict(fa)
            fa["status"] = "ok"
            result = dict(result)
            result["factor_attribution"] = fa
        return result

    monkeypatch.setattr(orch, "_run_factor_exposure", _bypass_partial_status)
    orch._clear_deep_analysis_cache()
    mut_report = orch.run_deep_analysis(force_modules=["factor_exposure"])
    with pytest.raises(AssertionError):
        assert mut_report.module_summary.get("factor_exposure") == "completed_partial"
    assert mut_report.module_summary.get("factor_exposure") == "completed"
