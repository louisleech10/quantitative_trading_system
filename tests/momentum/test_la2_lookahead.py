"""LA-2 M-lookahead 測試（B0 骨架 12 nodeid；B1 填實 test_winsorized_disabled）。

SPEC: docs/IC_LA2_SPEC.md
TODO: docs/IC_LA2_TODO.md Task 0.3 / 1.1 / 1.2

collect == 12:
  - test_winsorized_disabled          ← B1 實作
  - test_model_oot_contract           ← B2 xfail
  - test_model_service_oot            ← B2 xfail
  - test_config_theater               ← B2 xfail
  - test_calibrator_receipt           ← B2 xfail
  - test_pattern_train_mask           ← B3 xfail
  - test_pattern_promotion_guard      ← B3 xfail
  - test_plan_identity_mismatch       ← B3 xfail
  - test_regime_no_global_fit         ← B3 xfail
  - test_factor_loud                  ← B3 xfail
  - test_adversarial_validator_diagnostic_only  ← B3 xfail
  - test_analysis_status_diagnostic   ← B3/B4 xfail

B1 以外骨架 xfail（B4 final gate 禁殘留 skip/xfail；B2-B3 去 xfail 填實）。
collect 不觸 data_cache 副作用。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from momentum.Analysis.ic_config_schema import ICConfig, LabelConfig, load_ic_config
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.FeatureEngineering.labels.label_generator import (
    LOOKAHEAD_LABEL_UNSUPPORTED,
    WINSORIZED_DISABLED_MSG,
    LabelGenerator,
)
from momentum.factories import create_label_generator

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

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ATOL = 1e-12

# engine / orch(LabelGenerator) 兩路徑一致行為表（TODO Task 1.1③）
# return_type     | engine (_compute_returns)     | orch (LG dispatch)
# simple          | numeric ==                    | numeric ==
# log             | numeric ==                    | numeric ==
# excess          | ValueError w/o bench; == w/   | same
# risk_adjusted   | numeric ==                    | numeric ==
# winsorized      | NotImplementedError reason    | NotImplementedError reason
# unknown         | ValueError (no silent simple) | ValueError


def _assert_reason_code(exc: BaseException) -> None:
    """任一層 raise 必須帶固定 reason-code（字串一致）。"""
    msg = str(exc)
    assert LOOKAHEAD_LABEL_UNSUPPORTED in msg, (
        f"missing reason-code {LOOKAHEAD_LABEL_UNSUPPORTED!r} in {msg!r}"
    )


def _layer_generator_raises() -> None:
    lg = LabelGenerator({})
    close = pd.Series([1.0, 2.0, 3.0, 4.0])
    with pytest.raises(NotImplementedError) as ei:
        lg.generate_returns_by_type(close, horizon=1, return_type="winsorized")
    _assert_reason_code(ei.value)
    assert WINSORIZED_DISABLED_MSG in str(ei.value)


def _layer_schema_raises() -> None:
    with pytest.raises(ValidationError) as ei:
        LabelConfig(return_type="winsorized")  # type: ignore[arg-type]
    _assert_reason_code(ei.value)

    with pytest.raises(ValidationError) as ei2:
        ICConfig.model_validate({"labels": {"return_type": "winsorized"}})
    _assert_reason_code(ei2.value)


def _layer_orch_raises() -> None:
    """orch fail-closed：model_construct 繞過 schema 後 stage2 仍 raise 同 reason。"""
    base = load_ic_config()
    labels = LabelConfig.model_construct(
        return_type="winsorized",
        horizons=[1],
        horizons_time=None,
    )
    config = base.model_copy(update={"labels": labels})
    orch = ICFilterOrchestrator(config)

    n = 32
    idx = pd.date_range("2020-01-01", periods=n, freq="h", tz="UTC")
    close_df = pd.DataFrame(
        {"close": np.linspace(100.0, 110.0, n)},
        index=idx,
    )

    class _FakeKlineReader:
        def read_klines(self, symbol: str, timeframe: str) -> pd.DataFrame:
            return close_df

    with pytest.raises(NotImplementedError) as ei:
        orch._stage2_label_generation(
            labels_df=None,
            metadata={"symbol": "BTCUSDT", "timeframe": "1h"},
            config=config,
            kline_reader=_FakeKlineReader(),
            features_df=None,
        )
    _assert_reason_code(ei.value)


def _layer_engine_raises() -> None:
    engine = ICEngine({})
    close = pd.Series(np.linspace(100.0, 110.0, 40))
    with pytest.raises(NotImplementedError) as ei:
        engine._compute_returns(close, horizon=1, return_type="winsorized")
    _assert_reason_code(ei.value)


def _assert_engine_orch_equal(
    return_type: str,
    close: pd.Series,
    *,
    horizon: int = 1,
    benchmark_close: pd.Series | None = None,
) -> None:
    """engine._compute_returns == LabelGenerator (orch 同源) atol=1e-12。"""
    engine = ICEngine({})
    lg = create_label_generator()
    eng = engine._compute_returns(
        close, horizon, return_type, benchmark_close=benchmark_close
    )
    orch = lg.generate_returns_by_type(
        close, horizon, return_type, benchmark_close=benchmark_close
    )
    # 禁止 silent 回退 simple：非 simple 路徑不得整段等於 simple
    if return_type != "simple":
        simple = lg.generate_returns_by_type(close, horizon, "simple")
        # 允許部分 NaN 重合，但 finite 區不得全等（risk_adjusted/log 必與 simple 不同）
        both_finite = eng.notna() & simple.notna()
        if both_finite.any() and return_type in {"log", "risk_adjusted"}:
            assert not np.allclose(
                eng[both_finite].to_numpy(dtype=float),
                simple[both_finite].to_numpy(dtype=float),
                atol=_ATOL,
                equal_nan=True,
            ), f"{return_type} must not silently equal simple"
    pd.testing.assert_series_equal(
        eng,
        orch,
        check_names=False,
        atol=_ATOL,
        rtol=0.0,
    )


def _assert_engine_orch_both_raise(
    return_type: str,
    close: pd.Series,
    *,
    horizon: int = 1,
    benchmark_close: pd.Series | None = None,
    exc_type: type[BaseException] = ValueError,
) -> None:
    engine = ICEngine({})
    lg = create_label_generator()
    with pytest.raises(exc_type) as e_eng:
        engine._compute_returns(
            close, horizon, return_type, benchmark_close=benchmark_close
        )
    with pytest.raises(exc_type) as e_orch:
        lg.generate_returns_by_type(
            close, horizon, return_type, benchmark_close=benchmark_close
        )
    # 訊息語意對齊（同一錯誤族）
    assert type(e_eng.value) is type(e_orch.value)


def _assert_winsorize_returns_reader_zero() -> None:
    """winsorize_returns reader=0 + yaml 宣告移除（production 路徑）。"""
    # 1) yaml 不得宣告
    yaml_text = (_REPO_ROOT / "config" / "ic_config.yaml").read_text(encoding="utf-8")
    assert "winsorize_returns" not in yaml_text
    # 2) schema 不得再有該欄
    assert "winsorize_returns" not in LabelConfig.model_fields
    # 3) production py/yaml reader=0（排除 tests/docs/handoffs/Archived）
    # rg returncode: 0=有命中→FAIL；1=無命中→PASS；≥2=rg 錯→FAIL（禁靜默 pass）
    proc = subprocess.run(
        [
            "rg",
            "-n",
            "winsorize_returns",
            "--glob",
            "*.py",
            "--glob",
            "*.yaml",
            "--glob",
            "*.yml",
            "--glob",
            "!tests/**",
            "--glob",
            "!docs/**",
            "--glob",
            "!handoffs/**",
            "--glob",
            "!**/Archived/**",
            str(_REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    if proc.returncode >= 2:
        raise AssertionError(
            f"rg failed (returncode={proc.returncode}): "
            f"{(proc.stderr or '').strip() or '(no stderr)'}"
        )
    hits = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    assert proc.returncode == 1 and hits == [], (
        f"winsorize_returns reader must be 0 (rg rc=1 no hits); "
        f"got rc={proc.returncode} hits:\n" + "\n".join(hits)
    )


def _assert_allowlist_b1_four_rows() -> None:
    """Task 1.2：恰 4 個 P2-1-disable raise-only rows，無 old value/幽靈 path。"""
    import json

    al_path = _REPO_ROOT / "tests" / "golden" / "la2" / "attribution_allowlist.json"
    data = json.loads(al_path.read_text(encoding="utf-8"))
    rows = [r for r in data["rows"] if r.get("class") == "P2-1-disable"]
    assert len(rows) == 4, f"expected 4 P2-1-disable rows, got {len(rows)}"
    expected_paths = {
        "momentum/FeatureEngineering/labels/label_generator.py::generate_returns_by_type",
        "momentum/Analysis/ic_config_schema.py::return_type Literal",
        "momentum/Analysis/ic_filter_orchestrator.py:2380",
        "momentum/Analysis/ic_engine.py::_compute_returns",
    }
    got_paths = {r["path"] for r in rows}
    assert got_paths == expected_paths
    for r in rows:
        assert r.get("behavior") == "raises"
        assert r.get("reason_code") == LOOKAHEAD_LABEL_UNSUPPORTED
        assert r.get("old") is None
        assert r.get("new") is None
        assert r.get("index") == "winsorized"


def test_winsorized_disabled() -> None:
    """B1：winsorized 三層(+engine) raise 同 reason；engine==orch；reader=0。"""
    # --- 三層 fail-closed（任一層漏 → FAIL）---
    _layer_generator_raises()
    _layer_schema_raises()
    _layer_orch_raises()
    # engine 亦 raise（Task 1.1③ / allowlist 第四入口）
    _layer_engine_raises()

    # --- simple/log/excess/risk_adjusted engine == orch ---
    rng = np.random.default_rng(42)
    n = 80
    close = pd.Series(100.0 + np.cumsum(rng.normal(0, 0.5, n)), name="close")
    bench = pd.Series(100.0 + np.cumsum(rng.normal(0, 0.3, n)), name="bench")

    _assert_engine_orch_equal("simple", close)
    _assert_engine_orch_equal("log", close)
    _assert_engine_orch_equal("risk_adjusted", close)
    # excess：有 benchmark → 數值一致；無 benchmark → 兩路徑皆 raise
    _assert_engine_orch_equal("excess", close, benchmark_close=bench)
    _assert_engine_orch_both_raise("excess", close, benchmark_close=None)
    # unknown：禁 silent simple
    _assert_engine_orch_both_raise("unknown", close, exc_type=ValueError)

    # --- 死欄位 / config ---
    _assert_winsorize_returns_reader_zero()
    _assert_allowlist_b1_four_rows()


def _make_split_plan(
    rows: np.ndarray,
    *,
    label: str = "train",
    symbol: str = "BTCUSDT",
    universe: str = "u1",
    embargo: int = 0,
    index_kind: str = "positional",
    expected_freq: str | None = None,
) -> "SplitPlan":
    from momentum.core.contracts import SplitPlan

    return SplitPlan(
        split_label=label,  # type: ignore[arg-type]
        index_kind=index_kind,  # type: ignore[arg-type]
        row_index=np.asarray(rows, dtype=int),
        time_bounds=(None, None),
        purge_gap=0,
        embargo=embargo,
        purge_semantic="rows",
        expected_freq=expected_freq,
        base_universe_hash=universe,
        symbol=symbol,
    )


def test_model_oot_contract() -> None:
    """B2：analyzer 診斷 eval_scope + OOT horizon 嚴格 < + receipt 重算。"""
    from dataclasses import replace

    from momentum.core.contracts import (
        MODEL_PERFORMANCE_EVAL_SCOPE,
        ReceiptVerificationError,
        SplitPairLeakageError,
        TimestampDiscontinuityError,
        build_receipt_envelope,
        build_train_oot_split_plans,
        canonical_idx_hash,
        make_oof_receipt,
        make_oot_receipt,
        validate_oot_label_horizon,
        verify_oof_receipt,
        verify_oot_receipt,
    )
    from momentum.factories import create_xgboost_analyzer

    # --- 1) OOT 嚴格 <：row96 + h5 + emb0 = 101 vs eval_start=101 → FAIL ---
    train = _make_split_plan(np.arange(0, 97), label="train", embargo=0)  # max=96
    # fit_label_end = 96 + 5 = 101；eval_start=101 → 101<101 False
    eval_eq = _make_split_plan(np.arange(101, 120), label="test", embargo=0)
    with pytest.raises(SplitPairLeakageError):
        validate_oot_label_horizon(train, eval_eq, horizon=5, embargo=0)

    # 嚴格通過：eval_start=102 → 101<102
    eval_ok = _make_split_plan(np.arange(102, 120), label="test", embargo=0)
    validate_oot_label_horizon(train, eval_ok, horizon=5, embargo=0)

    # F10：timestamp 分支缺 bar_duration / ts → raise
    train_ts = _make_split_plan(
        np.arange(0, 50), label="train", embargo=0, expected_freq="1h"
    )
    # force timestamp kind
    from momentum.core.contracts import SplitPlan

    train_ts = SplitPlan(
        split_label="train",
        index_kind="timestamp",
        row_index=np.arange(0, 50, dtype=int),
        time_bounds=(0, 49),
        purge_gap=0,
        embargo=0,
        purge_semantic="rows",
        expected_freq="1h",
        base_universe_hash="ts-uni",
        symbol="BTC",
    )
    eval_ts = SplitPlan(
        split_label="test",
        index_kind="timestamp",
        row_index=np.arange(60, 80, dtype=int),
        time_bounds=(60, 79),
        purge_gap=0,
        embargo=0,
        purge_semantic="rows",
        expected_freq="1h",
        base_universe_hash="ts-uni",
        symbol="BTC",
    )
    with pytest.raises(SplitPairLeakageError, match="bar_duration"):
        validate_oot_label_horizon(train_ts, eval_ts, horizon=1, embargo=0)
    ts_arr = pd.date_range("2020-01-01", periods=80, freq="1h").to_numpy()
    with pytest.raises(SplitPairLeakageError, match="ts array"):
        validate_oot_label_horizon(
            train_ts, eval_ts, horizon=1, bar_duration="1h", embargo=0
        )
    validate_oot_label_horizon(
        train_ts, eval_ts, horizon=1, bar_duration="1h", ts=ts_arr, embargo=0
    )

    # --- 2) OofReceipt digest 重算（假 hash → raise）---
    plan = _make_split_plan(np.arange(0, 50), label="train")
    fit_idx = np.arange(0, 30)
    eval_idx = np.arange(30, 50)
    artifact = b"model-bytes-v1"
    oof = make_oof_receipt(
        plan, fold_id=0, fit_idx=fit_idx, eval_idx=eval_idx,
        model_artifact=artifact, trusted_issuer="xgboost_analyzer",
    )
    env = build_receipt_envelope("oof", oof)
    verify_oof_receipt(oof, plan, fit_idx, eval_idx, artifact, envelope=env)

    # F1：envelope=None → raise
    with pytest.raises(ReceiptVerificationError, match="envelope is required"):
        verify_oof_receipt(oof, plan, fit_idx, eval_idx, artifact, envelope=None)
    # F1：假 fields / version → raise
    fake_fields = dict(env)
    fake_fields["fields"] = {**env["fields"], "split_plan_hash": "fake"}
    with pytest.raises(ReceiptVerificationError):
        verify_oof_receipt(oof, plan, fit_idx, eval_idx, artifact, envelope=fake_fields)
    fake_ver = dict(env)
    fake_ver["version"] = 99
    with pytest.raises(ReceiptVerificationError, match="version"):
        verify_oof_receipt(oof, plan, fit_idx, eval_idx, artifact, envelope=fake_ver)

    # 假 fit_idx_hash → raise（仍須帶合法 envelope 結構；hash 步先於 envelope 時
    # 用合法 env 但 receipt 被改 → ①–③ 或 fields mismatch）
    bad = replace(oof, fit_idx_hash="0" * 64)
    with pytest.raises(ReceiptVerificationError):
        verify_oof_receipt(bad, plan, fit_idx, eval_idx, artifact, envelope=env)

    # 重疊 fit/eval → 不可建
    with pytest.raises(ReceiptVerificationError):
        make_oof_receipt(
            plan, 0, np.arange(0, 35), np.arange(30, 50),
            artifact, trusted_issuer="xgboost_analyzer",
        )

    # F2：hash 非 | 可撞；factory 2-D → raise
    h1 = canonical_idx_hash(
        np.arange(3), split_label="a|b", symbol="c", base_universe_hash="u"
    )
    h2 = canonical_idx_hash(
        np.arange(3), split_label="a", symbol="b|c", base_universe_hash="u"
    )
    assert h1 != h2, "delimiter collision must not hold under field-wise sha256"
    with pytest.raises(ValueError, match="1-D"):
        make_oof_receipt(
            plan, 0, np.array([[0, 1]]), np.array([2, 3]),
            artifact, trusted_issuer="xgboost_analyzer",
        )
    with pytest.raises(ValueError, match="1-D"):
        from momentum.core.contracts import make_calibrator_receipt

        make_calibrator_receipt(
            plan, np.array([[5, 6]]), artifact, trusted_issuer="probability_calibrator"
        )

    # --- 3) OotReceipt 合法/非法 ---
    oot = make_oot_receipt(
        train, eval_ok, horizon=5, model_artifact=artifact,
        trusted_issuer="xgboost_task_service",
    )
    env_oot = build_receipt_envelope("oot", oot)
    verify_oot_receipt(
        oot, train, eval_ok, horizon=5, model_artifact=artifact, envelope=env_oot
    )
    bad_oot = replace(oot, model_artifact_digest="deadbeef")
    with pytest.raises(ReceiptVerificationError):
        verify_oot_receipt(
            bad_oot, train, eval_ok, horizon=5, model_artifact=artifact, envelope=env_oot
        )

    # F3 helper：有足夠樣本 → has_oot plans
    plans = build_train_oot_split_plans(200, oot_ratio=0.2, horizon=1, embargo=0)
    assert plans is not None
    t_plan, e_plan = plans
    assert int(t_plan.row_index.max()) + 1 + 0 < int(e_plan.row_index.min())

    # --- 4) analyzer 欄位 rename + eval_scope + cal/PR=cv_oof + OMITTED oot ---
    rng = np.random.default_rng(7)
    n, f = 120, 4
    X = pd.DataFrame(rng.normal(size=(n, f)), columns=[f"f{i}" for i in range(f)])
    y = (rng.random(n) > 0.45).astype(int)
    # 確保兩類
    y[0], y[1] = 0, 1
    analyzer = create_xgboost_analyzer()
    perf = analyzer.train_model(
        X, y, feature_names=list(X.columns),
        early_stopping_rounds=5, eval_size=0.2,
        xgboost_params={"n_estimators": 20, "max_depth": 2, "n_jobs": 1},
        cv_folds=3,
    )
    assert hasattr(perf, "in_sample_train_auc")
    assert not hasattr(perf, "train_auc") or "train_auc" not in getattr(perf, "__dataclass_fields__", {})
    assert perf.eval_scope is not None
    assert perf.eval_scope.get("brier_score") == "cv_oof"
    assert perf.eval_scope.get("pr_auc") == "cv_oof"
    assert perf.eval_scope.get("in_sample_train_auc") == "in_sample_research_only"
    assert perf.oot_status == "OMITTED"
    assert perf.oot_auc is None
    # fit_pool_auc 應有值（ES 池）
    assert perf.fit_pool_auc is not None
    # §0.6-C enum 三值
    for scope in perf.eval_scope.values():
        assert scope in {"oot", "cv_oof", "in_sample_research_only"}

    # LGBM 對稱
    from momentum.factories import create_model_trainer

    lgbm = create_model_trainer("lightgbm", config={"n_estimators": 20, "n_jobs": 1, "verbose": -1})
    lperf = lgbm.train_model(
        X, y, feature_names=list(X.columns),
        early_stopping_rounds=5, eval_size=0.2, cv_folds=3,
    )
    assert hasattr(lperf, "in_sample_train_auc")
    assert lperf.eval_scope is not None
    assert lperf.eval_scope.get("brier_score") == "cv_oof"
    assert lperf.oot_status == "OMITTED"


def test_model_service_oot() -> None:
    """B2：service 全矩陣 scope + recommend_k OOT + migration。"""
    from momentum.Analysis.eval_scope_utils import apply_service_matrix_scopes
    from momentum.core.contracts import MODEL_PERFORMANCE_EVAL_SCOPE, OMITTED_METRIC

    # 模擬 service 全矩陣（無 held-out）
    raw = {
        "model_performance": {
            "in_sample_train_auc": 0.9,
            "cv_auc_mean": 0.7,
            "cv_auc_std": 0.01,
            "precision": 0.6,
            "recall": 0.5,
            "f1_score": 0.55,
            "overfitting_score": 0.2,
            "brier_score": 0.2,
            "ece": 0.05,
            "pr_auc": 0.4,
        },
        "feature_importance": [{"feature": "f0", "importance": 0.5}],
        "feature_importance_all": {"gain": []},
        "permutation_importance": {"items": []},
        "fold_importance_stability": {"items": []},
        "shap_sample": {"sample_size": 10},
        "regime_analysis": None,
        "cross_symbol_validation": {"symbols": []},
        "precision_at_k": {
            "recommended_k": 10,
            "precision_at_k": {10: 0.8},
        },
        "expectancy": {"expectancy": 0.1, "sharpe_proxy": 0.5},
        "bootstrap_ci": {"auc": {}},
        "predictions": {"predictions": []},
        "calibration_curve": {"bin_midpoints": []},
        "pr_curve": {"pr_auc": 0.4},
        "oot_receipt": None,
    }
    scoped = apply_service_matrix_scopes(raw, has_oot_held_out=False)
    mp = scoped["model_performance"]
    assert "train_auc" not in mp
    assert mp.get("oot_status") == OMITTED_METRIC
    assert mp["eval_scope"]["in_sample_train_auc"] == "in_sample_research_only"
    assert mp["eval_scope"]["brier_score"] == "cv_oof" or scoped["matrix_eval_scope"].get("calibration_curve") == "cv_oof"
    # recommend_k / precision@K OOT 且無 held-out → OMITTED
    assert scoped["precision_at_k"]["status"] == OMITTED_METRIC
    assert scoped["matrix_eval_scope"].get("recommend_k") == "oot"
    # importance/shap research_only + deny
    assert "feature_importance" in scoped["matrix_consumer_deny"]
    assert "shap_sample" in scoped["matrix_consumer_deny"]
    assert "cross_symbol_validation" in scoped["matrix_consumer_deny"]
    # migration map
    assert scoped["field_migration"]["/model_performance/train_auc"] == (
        "/model_performance/in_sample_train_auc"
    )
    # F8：無 held-out 源頭不得保留全樣本 recommended_k 值（必須 OMITTED+deny）
    assert scoped["precision_at_k"].get("status") == OMITTED_METRIC
    assert scoped["precision_at_k"].get("recommended_k") is None
    assert scoped["precision_at_k"].get("consumer") == "deny"

    # F3：service helper 真產 oot_receipt（有 held-out 時）
    from momentum.Analysis.eval_scope_utils import build_service_oot_bundle

    bundle = build_service_oot_bundle(
        n_samples=200,
        model_artifact=b"svc-artifact",
        trusted_issuer="xgboost_task_service",
        oot_ratio=0.2,
        horizon=1,
    )
    assert bundle["has_oot_held_out"] is True
    assert bundle["oot_receipt"] is not None
    assert bundle["oot_receipt"]["receipt_kind"] == "oot"
    tiny = build_service_oot_bundle(
        n_samples=5,
        model_artifact=b"svc-artifact",
        trusted_issuer="xgboost_task_service",
    )
    assert tiny["has_oot_held_out"] is False
    assert tiny["oot_receipt"] is None

    # has_oot 時 oot 欄保留
    scoped_oot = apply_service_matrix_scopes(
        {
            **raw,
            "precision_at_k": {"recommended_k": 5, "precision_at_k": {5: 0.9}},
        },
        has_oot_held_out=True,
    )
    assert scoped_oot["precision_at_k"].get("eval_scope") == "oot"
    assert scoped_oot["precision_at_k"].get("status") != OMITTED_METRIC

    # §0.6-C 28 path 閉集存在於 contracts
    assert len(MODEL_PERFORMANCE_EVAL_SCOPE) == 28

    # allowlist 含 B2 rows
    import json

    al = json.loads(
        (_REPO_ROOT / "tests/golden/la2/attribution_allowlist.json").read_text()
    )
    classes = {r["class"] for r in al["rows"]}
    assert "P2-2-oot" in classes
    assert "P2-2-scope-tag" in classes


def test_config_theater() -> None:
    """B2：calibrator/sample_weight enabled=true,wired=false 可見。"""
    from momentum.Analysis.model_config import ModelConfigManager

    mgr = ModelConfigManager(str(_REPO_ROOT / "config" / "model_config.yaml"))
    theater = mgr.list_config_theater_modules()
    names = {t["module"] for t in theater}
    assert "probability_calibration" in names
    assert "sample_weight" in names
    for t in theater:
        assert t["enabled"] is True
        assert t["wired"] is False
        assert t["theater"] is True

    pc = mgr.get_module_wiring("probability_calibration")
    assert pc["wired"] is False
    # yaml 自身亦標 wired:false
    yaml_text = (_REPO_ROOT / "config" / "model_config.yaml").read_text(encoding="utf-8")
    assert "wired: false" in yaml_text

    # UI 標記存在
    ui = (
        _REPO_ROOT / "frontend/src/components/pattern/EngineConfigPanel.tsx"
    ).read_text(encoding="utf-8")
    assert "config-theater-panel" in ui
    assert "已宣告未接線" in ui
    assert "probability_calibration" in ui
    assert "sample_weight" in ui

    # runtime 行為不受 yaml enabled 控：train_model 無 sample_weight/calibrator wiring
    # （grep production train path 不讀這兩個 enabled 開關）
    import subprocess

    proc = subprocess.run(
        [
            "rg",
            "-n",
            r"probability_calibration|sample_weight",
            "momentum/Analysis/xgboost_analyzer.py",
            "momentum/Analysis/lightgbm_analyzer.py",
            "api/services/xgboost_task_service.py",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    # train path 不應因 yaml enabled 呼叫 calibrator/sample_weight
    hits = [
        ln
        for ln in (proc.stdout or "").splitlines()
        if "enabled" in ln.lower() or "sample_weight" in ln or "probability_calibration" in ln
    ]
    # 允許 0 命中；若有命中不得是 train wiring
    for ln in hits:
        assert "train_model" not in ln or "wired" in ln.lower()


def test_calibrator_receipt() -> None:
    """B2：CalibratorReceipt 兩分支缺 receipt → raise；合法可 verify。"""
    from momentum.Analysis.probability_calibrator import ProbabilityCalibrator
    from momentum.core.contracts import (
        ReceiptVerificationError,
        build_receipt_envelope,
        make_calibrator_receipt,
        verify_calibrator_receipt,
    )

    train = _make_split_plan(np.arange(0, 80), label="train")
    calib_idx = np.arange(80, 120)  # disjoint
    artifact = b"calib-model-artifact"

    # 合法 receipt
    receipt = make_calibrator_receipt(
        train, calib_idx, artifact, trusted_issuer="probability_calibrator"
    )
    env = build_receipt_envelope("calibrator", receipt)
    verify_calibrator_receipt(receipt, train, calib_idx, artifact, envelope=env)

    # 假 hash → raise
    from dataclasses import replace

    bad = replace(receipt, calib_idx_hash="ff" * 32)
    with pytest.raises(ReceiptVerificationError):
        verify_calibrator_receipt(bad, train, calib_idx, artifact, envelope=env)
    # F1：calibrator envelope=None → raise
    with pytest.raises(ReceiptVerificationError, match="envelope is required"):
        verify_calibrator_receipt(receipt, train, calib_idx, artifact, envelope=None)

    # 重疊 calib∩train → 不可建
    with pytest.raises(ReceiptVerificationError):
        make_calibrator_receipt(
            train, np.arange(0, 10), artifact, trusted_issuer="probability_calibrator"
        )

    cal = ProbabilityCalibrator()
    # fit_from_predictions 缺 receipt → fail-closed
    y_true = np.array([0, 1] * 60)
    y_pred = np.clip(np.linspace(0.1, 0.9, 120) + np.random.default_rng(0).normal(0, 0.05, 120), 0.01, 0.99)
    with pytest.raises(ReceiptVerificationError):
        cal.fit_from_predictions(y_true=y_true, y_pred_proba=y_pred, require_receipt=True)

    # F4：有 plan/idx/artifact 但 receipt=None → 仍 raise（不自簽）
    with pytest.raises(ReceiptVerificationError, match="must be supplied"):
        cal.fit_from_predictions(
            y_true=y_true,
            y_pred_proba=y_pred,
            train_plan=train,
            calib_idx=calib_idx,
            model_artifact=artifact,
            receipt=None,
            require_receipt=True,
        )

    # 合法兩分支：receipt 外部傳入
    ok = cal.fit_from_predictions(
        y_true=y_true,
        y_pred_proba=y_pred,
        train_plan=train,
        calib_idx=calib_idx,
        model_artifact=artifact,
        receipt=receipt,
        require_receipt=True,
    )
    assert "calibrator_receipt" in ok
    assert ok["calibrator_receipt"]["receipt_kind"] == "calibrator"

    # fit(model, ...) 分支同樣缺 → raise
    from sklearn.linear_model import LogisticRegression

    X = np.random.default_rng(1).normal(size=(120, 3))
    y = (X[:, 0] > 0).astype(int)
    model = LogisticRegression(max_iter=200).fit(X, y)
    with pytest.raises(ReceiptVerificationError):
        cal.fit(model=model, X_cal=X, y_cal=y, require_receipt=True)

    ok2 = cal.fit(
        model=model,
        X_cal=X,
        y_cal=y,
        train_plan=train,
        calib_idx=calib_idx,
        model_artifact=artifact,
        receipt=receipt,
        require_receipt=True,
    )
    assert "calibrator_receipt" in ok2


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
