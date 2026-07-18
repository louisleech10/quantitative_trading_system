"""LA-2 M-lookahead 測試（B0 骨架 12 nodeid；B1–B4 mutation 全套）。

SPEC: docs/IC_LA2_SPEC.md
TODO: docs/IC_LA2_TODO.md Task 0.3 / 1–3.* / 4.1

collect == 12（0 skip / 0 xfail）:
  - test_winsorized_disabled          ← B1 C-1 raise（非 flip）
  - test_model_oot_contract           ← B2 軌2 provenance（OOT 嚴格 < / OOF digest）
  - test_model_service_oot            ← B2/B4 全矩陣 scope + cross_symbol deny
  - test_config_theater               ← B2
  - test_calibrator_receipt           ← B2
  - test_pattern_train_mask           ← B3/B4 C-2 early flip 改前>0 改後=0
  - test_pattern_promotion_guard      ← B3 C-2 晉升 provenance
  - test_plan_identity_mismatch       ← B3
  - test_regime_no_global_fit         ← B3 C-1 regime 移除不可達
  - test_factor_loud                  ← B3/B4 C-3 loud + control deep-equal + proxy
  - test_adversarial_validator_diagnostic_only  ← B3
  - test_analysis_status_diagnostic   ← B3

B4 final gate 禁殘留 skip/xfail。collect 不觸 data_cache 副作用。
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

    # --- B4 T14/U17：真走 xgboost_batch_service 產線 cross_symbol 路徑 ---
    # 必呼 service._build_cross_symbol_validation（內含 eligibility + LOSO）；
    # 移除/改壞 service 內 run_leave_one_symbol_out 呼叫 → 本段必 FAIL。
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from api.services.xgboost_batch_service import XGBoostBatchService
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator

    batch_src = (
        _REPO_ROOT / "api" / "services" / "xgboost_batch_service.py"
    ).read_text(encoding="utf-8")
    assert "run_leave_one_symbol_out" in batch_src
    assert "if len(indices) < 10:" in batch_src  # eligibility 閘門
    assert "_build_cross_symbol_validation" in batch_src
    # _run_batch_analysis 必須接線呼叫產線方法（只留 helper 不接線 → 紅）
    assert "self._build_cross_symbol_validation(" in batch_src

    rng_cs = np.random.default_rng(42)
    # 插入序非字母序；ADA < min_rows → ineligible；eligible = ETH+BTC（≥2）
    symbol_order = ["ETHUSDT", "BTCUSDT", "ADAUSDT"]
    row_counts = {"ETHUSDT": 36, "BTCUSDT": 40, "ADAUSDT": 5}
    X_chunks: list[np.ndarray] = []
    y_chunks: list[np.ndarray] = []
    case_symbols: list[str] = []
    for sym in symbol_order:
        n = row_counts[sym]
        Xs = rng_cs.normal(size=(n, 3))
        ys = (rng_cs.random(n) > 0.45).astype(int)
        ys[0], ys[1] = 0, 1  # 雙類別，AUC 可算
        X_chunks.append(Xs)
        y_chunks.append(ys)
        case_symbols.extend([sym] * n)
    X_cs = np.vstack(X_chunks)
    y_cs = np.concatenate(y_chunks)
    valid_cases_cs = [SimpleNamespace(symbol=s) for s in case_symbols]

    # 真 service 實例：走產線方法（非鏡像 CrossSymbolValidator 直呼）
    service = XGBoostBatchService.__new__(XGBoostBatchService)
    service.logger = MagicMock()
    service.cross_symbol_validator = CrossSymbolValidator(
        params={"n_estimators": 8, "n_jobs": 1, "verbosity": 0, "max_depth": 2}
    )
    cross_list = service._build_cross_symbol_validation(
        symbols=symbol_order,
        valid_cases=valid_cases_cs,
        X=X_cs,
        y=y_cs,
    )
    assert cross_list is not None, (
        "batch service cross_symbol 產線必須回傳 LOSO list（None=LOSO 未跑/失敗）"
    )
    assert isinstance(cross_list, list)
    assert len(cross_list) >= 2
    targets = sorted(r["target_symbol"] for r in cross_list)
    # ADAUSDT <10 必須被 eligibility 剔除；eligible top-2 = BTC+ETH
    assert "ADAUSDT" not in targets
    eligible = ["BTCUSDT", "ETHUSDT"]
    assert targets == eligible

    # 同 batch Step9 尾：list payload → apply_service_matrix_scopes
    cross_raw = {
        "model_performance": {
            "in_sample_train_auc": 0.8,
            "cv_auc_mean": 0.7,
            "brier_score": 0.2,
            "pr_auc": 0.4,
        },
        "cross_symbol_validation": cross_list,
        "feature_importance": [{"feature": "f0", "importance": 0.5}],
        "shap_sample": {"sample_size": 5},
        "precision_at_k": {"recommended_k": 5, "precision_at_k": {5: 0.9}},
        "expectancy": {"expectancy": 0.01},
        "bootstrap_ci": {},
        "predictions": {},
        "permutation_importance": {},
        "fold_importance_stability": {},
        "regime_analysis": None,
        "oot_receipt": None,
    }
    scoped_cs = apply_service_matrix_scopes(cross_raw, has_oot_held_out=False)
    assert "cross_symbol_validation" in scoped_cs["matrix_consumer_deny"]
    assert scoped_cs["matrix_eval_scope"].get("cross_symbol_validation") == (
        "in_sample_research_only"
    )
    # 不得被標成 oot（本票無 LOSO receipt / 非 oot 分支）
    assert scoped_cs["matrix_eval_scope"].get("cross_symbol_validation") != "oot"
    cs_payload = scoped_cs.get("cross_symbol_validation") or {}
    assert isinstance(cs_payload, dict)
    assert cs_payload.get("eval_scope") == "in_sample_research_only"
    assert cs_payload.get("consumer") == "deny"
    items = cs_payload.get("items") or []
    assert len(items) >= 2
    assert sorted(r["target_symbol"] for r in items) == eligible


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


def test_pattern_train_mask() -> None:
    """B3：pattern train-mask + train-y 統計；缺 split / 非 train fail-closed。"""
    import xgboost as xgb

    from momentum.Analysis.pattern_extractor import (
        PatternExtractor,
        PatternSplitRequiredError,
    )
    from momentum.core.contracts import SplitPlan, canonical_split_plan_hash
    from momentum.factories import create_xgboost_analyzer

    rng = np.random.default_rng(42)
    n = 400
    X = pd.DataFrame(
        {
            "f0": rng.normal(size=n),
            "f1": rng.normal(size=n),
            "f2": rng.normal(size=n),
        }
    )
    y = ((X["f0"] > 0) & (X["f1"] > 0)).astype(int).to_numpy()
    analyzer = create_xgboost_analyzer()
    analyzer.train_model(X, y)
    extractor = PatternExtractor()

    # 缺 split → fail-closed
    with pytest.raises(PatternSplitRequiredError):
        extractor.extract_decision_rules(
            analyzer.model, X, y, list(X.columns), top_n=5, min_support=5
        )

    # 非 train split → fail-closed
    test_plan = _make_split_plan(np.arange(300, 400), label="test", universe="pat-u")
    with pytest.raises(PatternSplitRequiredError):
        extractor.extract_decision_rules(
            analyzer.model,
            X,
            y,
            list(X.columns),
            top_n=5,
            min_support=5,
            split=test_plan,
        )

    train_plan = _make_split_plan(np.arange(0, 300), label="train", universe="pat-u")
    rules = extractor.extract_decision_rules(
        analyzer.model,
        X,
        y,
        list(X.columns),
        top_n=10,
        min_support=5,
        split=train_plan,
        expected_plan_hash=canonical_split_plan_hash(train_plan),
    )
    assert len(rules) >= 1
    # threshold 為 train 分位值（finite），非 confidence
    for r in rules:
        assert 0.0 <= r.confidence <= 1.0
        for _f, _op, thr in r.feature_conditions:
            assert np.isfinite(thr)
            # threshold ≠ confidence（可證偽：誤用 confidence 當 threshold）
            assert thr != r.confidence or abs(thr) > 1.0 or thr == 0.0

    # --- B4 C-2：legacy full-sample early-flip 改前>0；train-mask 改後=0 ---
    from tests.golden.la2.gen_baseline import _pattern_early_flip_manifest

    legacy_flip = _pattern_early_flip_manifest(X, y)
    n_th_legacy = int(legacy_flip["pattern"]["n_threshold_flip"])
    n_cf_legacy = int(legacy_flip["pattern"]["n_confidence_flip"])
    assert n_th_legacy > 0 and n_cf_legacy > 0, (
        f"C-2 mutation oracle requires pre-fix full-sample flip>0; "
        f"got th={n_th_legacy} cf={n_cf_legacy}"
    )

    # trunc 未來：train-y-only → early 門檻/confidence 不因未來翻轉
    n_keep = 320
    X_trunc = X.iloc[:n_keep]
    y_trunc = y[:n_keep]
    # train plan 仍為 [0,300) 且在 trunc 內
    rules_trunc = extractor.extract_decision_rules(
        analyzer.model,
        X_trunc,
        y_trunc,
        list(X.columns),
        top_n=10,
        min_support=5,
        split=train_plan,
    )
    # 同 train mask → 門檻一致（early equal）
    assert len(rules) > 0 and len(rules_trunc) > 0
    thr_full = {
        (r.feature_conditions[0][0], r.feature_conditions[0][2])
        for r in rules
        if len(r.feature_conditions) == 1
    }
    thr_trunc = {
        (r.feature_conditions[0][0], r.feature_conditions[0][2])
        for r in rules_trunc
        if len(r.feature_conditions) == 1
    }
    # train 段相同 → 單特徵門檻集合應一致 → post-fix flip count = 0
    assert thr_full == thr_trunc, (thr_full, thr_trunc)
    conf_full = {r.rule_id: r.confidence for r in rules}
    conf_trunc = {r.rule_id: r.confidence for r in rules_trunc}
    shared_ids = set(conf_full) & set(conf_trunc)
    assert shared_ids, "need shared rule_ids for confidence flip=0"
    n_conf_flip_post = sum(
        1
        for rid in shared_ids
        if not np.isclose(conf_full[rid], conf_trunc[rid], atol=_ATOL, rtol=0.0)
    )
    assert n_conf_flip_post == 0, (
        f"C-2 train-mask post-fix confidence flip must be 0, got {n_conf_flip_post}"
    )
    n_thr_flip_post = 0 if thr_full == thr_trunc else 1
    assert n_thr_flip_post == 0
    # 可證偽對照：legacy full-sample flip 仍 >0（改前），post train-mask =0（改後）
    assert n_th_legacy > 0 and n_thr_flip_post == 0
    assert n_cf_legacy > 0 and n_conf_flip_post == 0


def test_pattern_promotion_guard() -> None:
    """B3：晉升 server 權威（create+PUT）；偽造 client 欄位拒；OOT lift 來源。"""
    from momentum.Analysis.eval_scope_utils import build_service_oot_bundle
    from api.services.pattern_management_service import PatternManagementService

    artifact = b"promo-artifact-v1"
    bundle = build_service_oot_bundle(
        n_samples=200,
        model_artifact=artifact,
        trusted_issuer="xgboost_task_service",
        oot_ratio=0.2,
        horizon=1,
        embargo=0,
        symbol="BTCUSDT",
        base_universe_hash="promo-u",
    )
    assert bundle["oot_receipt"] is not None

    task_result = {
        "case_id": "BTCUSDT_1h",
        "oot_receipt": bundle["oot_receipt"],
        # B3-F1：三份 provenance 必填，缺→非 active
        "train_plan": bundle["train_plan"],
        "eval_plan": bundle["eval_plan"],
        "model_artifact": artifact,
        "decision_rules": [
            {
                "rule_id": 1,
                "condition": "f0 > 0.1",
                "support": 50,
                "confidence": 0.7,
                "lift": 1.2,  # train lift
                "oot_lift": 1.5,  # OOT lift（晉升必須用此）
                "feature_conditions": [
                    {"feature": "f0", "operator": ">", "threshold": 0.1}
                ],
            }
        ],
        "feature_importance": [{"feature": "f0", "importance": 0.9}],
        "model_performance": {
            "value": {"in_sample_train_auc": 0.99, "oot_auc": 0.6},
            "eval_scope": {
                "in_sample_train_auc": "in_sample_research_only",
                "oot_auc": "oot",
            },
        },
    }
    store: dict = {"task-ok": task_result}
    svc = PatternManagementService(task_result_lookup=lambda tid: store.get(tid))

    # 偽造 client rules/metadata/status → 拒
    bad = svc.create_pattern(
        name="bad",
        description="d",
        task_id="task-ok",
        rules=[{"feature": "hack", "operator": ">", "threshold": 99, "description": "x"}],
    )
    assert bad["success"] is False
    assert "rules" in bad["error"]

    bad_meta = svc.create_pattern(
        name="bad2",
        description="d",
        task_id="task-ok",
        metadata={"forged": True},
    )
    assert bad_meta["success"] is False

    # 合法 create → active（有 oot_receipt + 三 provenance + finite oot_lift）
    ok = svc.create_pattern(
        name="good",
        description="from task",
        task_id="task-ok",
        tags=["t1"],
    )
    assert ok["success"] is True, ok
    assert ok["pattern"]["status"] == "active"
    # OOT lift 來源
    assert ok["pattern"]["performance_metrics"].get("oot_lift_source") == "oot"
    assert ok["pattern"]["performance_metrics"].get("oot_lift_mean") == pytest.approx(1.5)
    # threshold = 分位值 0.1 非 confidence 0.7
    assert ok["pattern"]["rules"][0]["threshold"] == pytest.approx(0.1)

    # B3-F1 反例：缺三 provenance → 非 active（可證偽）
    store["task-no-prov"] = {
        k: v
        for k, v in task_result.items()
        if k not in ("train_plan", "eval_plan", "model_artifact")
    }
    no_prov = svc.create_pattern(name="np", description="d", task_id="task-no-prov")
    assert no_prov["success"] is True, no_prov
    assert no_prov["pattern"]["status"] != "active"
    assert "provenance" in str(
        no_prov["pattern"].get("metadata", {}).get("promotion_blocked_reason", "")
    ) or no_prov["pattern"]["status"] == "testing"

    # B3-F6：缺 oot_lift → 非 active
    store["task-no-lift"] = {
        **task_result,
        "decision_rules": [
            {
                **task_result["decision_rules"][0],
                "oot_lift": None,
            }
        ],
    }
    no_lift = svc.create_pattern(name="nl", description="d", task_id="task-no-lift")
    assert no_lift["success"] is True, no_lift
    assert no_lift["pattern"]["status"] != "active"

    # 缺 oot_receipt → 非 active（仍可建立 testing）
    store["task-no-oot"] = {
        "case_id": "x",
        "decision_rules": task_result["decision_rules"],
        "feature_importance": [{"feature": "f0", "importance": 0.1}],
        "model_performance": {
            "value": {"in_sample_train_auc": 0.5, "cv_auc_mean": 0.5},
            "eval_scope": {
                "in_sample_train_auc": "in_sample_research_only",
                "cv_auc_mean": "cv_oof",
            },
        },
    }
    no_oot = svc.create_pattern(name="n", description="d", task_id="task-no-oot")
    assert no_oot["success"] is True, no_oot
    assert no_oot["pattern"]["status"] != "active"

    # 假 oot_receipt digest → 非 active
    forged_env = dict(bundle["oot_receipt"])
    forged_env["envelope_digest"] = "0" * 64
    store["task-forged"] = {**task_result, "oot_receipt": forged_env}
    forged = svc.create_pattern(name="f", description="d", task_id="task-forged")
    assert forged["success"] is True
    assert forged["pattern"]["status"] != "active"

    # PUT status 拒
    pid = ok["pattern_id"]
    put_bad = svc.update_pattern(pid, status="active")
    assert put_bad["success"] is False
    assert "status" in put_bad["error"]
    put_meta = svc.update_pattern(pid, metadata={"x": 1})
    assert put_meta["success"] is False


def test_plan_identity_mismatch() -> None:
    """B3：pattern/model plan_hash mismatch → fail-closed。"""
    from momentum.Analysis.pattern_extractor import (
        PatternExtractor,
        PatternPlanIdentityError,
        PatternSplitRequiredError,
    )
    from momentum.core.contracts import canonical_split_plan_hash
    from momentum.factories import create_xgboost_analyzer

    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    y = (X["a"] > 0).astype(int).to_numpy()
    analyzer = create_xgboost_analyzer()
    analyzer.train_model(X, y)

    plan_a = _make_split_plan(np.arange(0, 150), label="train", universe="u-a")
    plan_b = _make_split_plan(np.arange(0, 150), label="train", universe="u-b")
    # 同 cutoff 長度但 universe/symbol 不同 → hash 不同
    assert canonical_split_plan_hash(plan_a) != canonical_split_plan_hash(plan_b)

    extractor = PatternExtractor()
    with pytest.raises(PatternPlanIdentityError):
        extractor.extract_decision_rules(
            analyzer.model,
            X,
            y,
            list(X.columns),
            top_n=3,
            min_support=5,
            split=plan_a,
            expected_plan_hash=canonical_split_plan_hash(plan_b),
        )

    # 同 plan 三 cutoff 同 row 但不同 identity（symbol）
    plan_c = _make_split_plan(
        np.arange(0, 150), label="train", symbol="ETHUSDT", universe="u-a"
    )
    plan_d = _make_split_plan(
        np.arange(0, 150), label="train", symbol="BTCUSDT", universe="u-a"
    )
    assert canonical_split_plan_hash(plan_c) != canonical_split_plan_hash(plan_d)
    with pytest.raises(PatternPlanIdentityError):
        extractor.extract_decision_rules(
            analyzer.model,
            X,
            y,
            list(X.columns),
            top_n=3,
            min_support=5,
            split=plan_c,
            expected_plan_hash=canonical_split_plan_hash(plan_d),
        )


def test_regime_no_global_fit() -> None:
    """B3/B4：_fit_global / expanding 參數移除不可達；golden face == control PIT。"""
    import inspect
    import json

    from momentum.Analysis.regime_detector import RegimeDetector
    from momentum.factories import create_regime_detector

    det = create_regime_detector(n_clusters=3, lookback=20, min_samples_for_fit=50)
    sig = inspect.signature(RegimeDetector.detect)
    assert "expanding" not in sig.parameters
    assert not hasattr(det, "_fit_global")
    with pytest.raises(TypeError):
        det.detect(pd.Series([1.0, 2.0, 3.0]), expanding=False)  # type: ignore[call-arg]
    with pytest.raises(AttributeError):
        det._fit_global(pd.DataFrame({"volatility": [0.1]}))  # type: ignore[attr-defined]

    # 產線 PIT 仍可用
    rng = np.random.default_rng(1)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 0.5, 400)))
    r1 = det.detect(close)
    r2 = det.detect(close)
    assert len(r1.labels) == len(close)
    np.testing.assert_array_equal(r1.labels, r2.labels)

    # B4：重基準後 regime_fit_global.labels == control.regime_pit（PIT-only）
    for name in ("BTCUSDT_1h_baseline.json", "ETHUSDT_12h_baseline.json"):
        bl = json.loads(
            (_REPO_ROOT / "tests" / "golden" / "la2" / name).read_text(encoding="utf-8")
        )
        rg = (bl.get("regime_fit_global") or {}).get("labels_sha256")
        cp = ((bl.get("control") or {}).get("regime_pit") or {}).get("labels_sha256")
        assert rg and cp and rg == cp, f"{name}: regime face must equal control PIT"
        assert (bl.get("regime_fit_global") or {}).get("pit_only") is True


def test_factor_loud() -> None:
    """B3：factor typed loud + market_proxy 因果化 + deny gate。"""
    from dataclasses import asdict
    from types import SimpleNamespace

    from momentum.core.contracts import (
        ExposurePayload,
        FactorModuleResult,
        OrthogonalizationPayload,
        deny_factor_in_ok_oos,
    )
    from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    # typed contract hard asserts
    orth = FactorModuleResult(
        module="orthogonalization",
        oos_guarantees=False,
        fit_scope="full_sample",
        payload=OrthogonalizationPayload(
            method="gram_schmidt",
            orthogonalized_hash="abc",
            summary={"method": "gram_schmidt"},
        ),
    )
    assert orth.oos_guarantees is False
    assert orth.fit_scope == "full_sample"

    with pytest.raises(ValueError):
        FactorModuleResult(
            module="orthogonalization",
            oos_guarantees=True,  # type: ignore[arg-type]
            fit_scope="full_sample",
            payload=OrthogonalizationPayload(
                method="gs", orthogonalized_hash="x", summary={}
            ),
        )

    # GS 算法不改：兩次 deep-equal
    rng = np.random.default_rng(7)
    factors = pd.DataFrame(
        rng.normal(size=(200, 3)), columns=["f0", "f1", "f2"]
    )
    fo = FactorOrthogonalizer({})
    t1, s1 = fo.gram_schmidt(factors)
    t2, s2 = fo.gram_schmidt(factors)
    np.testing.assert_allclose(t1.to_numpy(), t2.to_numpy(), atol=_ATOL)
    assert s1["method"] == s2["method"] == "gram_schmidt"

    # root ok_oos + nested factor loud → deny
    report = {
        "analysis_status": "ok_oos",
        "deep_analysis": {
            "factor_orthogonalization": asdict(orth),
        },
    }
    with pytest.raises(ValueError, match="deny_factor_in_ok_oos"):
        deny_factor_in_ok_oos(report)

    # degraded root 可帶 factor loud
    report2 = {
        "analysis_status": "degraded_full_sample",
        "deep_analysis": {"factor_orthogonalization": asdict(orth)},
    }
    deny_factor_in_ok_oos(report2)  # no raise

    # proxy lag≥1：pct_change().shift(1) 不見當根 close / forward label
    close = pd.Series([100.0, 110.0, 121.0, 133.1], index=pd.RangeIndex(4))
    proxy = close.pct_change().shift(1)
    # bar 0,1 NaN；bar 2 = (110-100)/100 = 0.1（只用到 close[1], close[0]）
    assert np.isnan(proxy.iloc[0]) and np.isnan(proxy.iloc[1])
    assert proxy.iloc[2] == pytest.approx(0.1)
    # 與 forward label 不同：forward = close.pct_change().shift(-1) 用未來
    forward = close.pct_change().shift(-1)
    assert not np.allclose(
        proxy.fillna(0).to_numpy(), forward.fillna(0).to_numpy(), equal_nan=False
    )

    exp = FactorModuleResult(
        module="exposure",
        oos_guarantees=False,
        fit_scope="full_sample",
        payload=ExposurePayload(
            proxy_kind="trailing_close_ret",
            exposure_hash="e1",
            summary={"proxy_lag": 1},
        ),
    )
    assert exp.payload.proxy_kind == "trailing_close_ret"

    # B3-F9：orchestrator production 結果保留 typed_result（非純 asdict）
    orch = ICFilterOrchestrator.__new__(ICFilterOrchestrator)
    close_series = pd.Series(
        100 + np.cumsum(rng.normal(0, 1, len(factors))),
        index=factors.index,
    )
    orch._ic_cache = {
        "features_df": factors,
        "icir": {"f0": 0.1, "f1": 0.05, "f2": 0.02},
        "close_series": close_series,
    }
    orth_cfg = SimpleNamespace(
        method="gram_schmidt",
        enabled=True,
        model_dump=lambda: {"method": "gram_schmidt"},
    )
    cfg = SimpleNamespace(factor_orthogonalization=orth_cfg)
    prod = ICFilterOrchestrator._run_factor_orthogonalization(
        orch, list(factors.columns), cfg  # type: ignore[arg-type]
    )
    assert isinstance(prod.get("typed_result"), FactorModuleResult)
    assert prod["oos_guarantees"] is False
    assert prod["fit_scope"] == "full_sample"
    assert prod["module"] == "orthogonalization"
    # production envelope under ok_oos → deny
    with pytest.raises(ValueError, match="deny_factor_in_ok_oos"):
        deny_factor_in_ok_oos(
            {
                "analysis_status": "ok_oos",
                "deep_analysis": {"factor_orthogonalization": prod},
            }
        )

    # B4-F1：產線 _run_factor_exposure 必須用 trailing close-ret（lag≥1）
    # 產線 ic_filter_orchestrator:2155-2156 改 shift(-1) 時本段必 FAIL
    from unittest.mock import patch

    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer
    from momentum.Analysis.ic_config_schema import ICConfig

    captured_proxy: dict[str, pd.Series] = {}
    real_neutralize = FactorExposureAnalyzer.neutralize_factor_matrix

    def _spy_neutralize(
        self: object,
        factor_values: pd.DataFrame,
        market_proxy: pd.Series,
        mode: str,
        lookback: int,
    ):
        captured_proxy["market_proxy"] = market_proxy.copy()
        return real_neutralize(self, factor_values, market_proxy, mode, lookback)

    ic_cfg = ICConfig()
    with patch.object(
        FactorExposureAnalyzer, "neutralize_factor_matrix", _spy_neutralize
    ):
        exp_prod = ICFilterOrchestrator._run_factor_exposure(
            orch, list(factors.columns), ic_cfg
        )
    assert exp_prod.get("proxy_kind") == "trailing_close_ret"
    assert int(exp_prod.get("proxy_lag") or 0) == 1
    assert isinstance(exp_prod.get("typed_result"), FactorModuleResult)
    assert exp_prod["oos_guarantees"] is False
    assert "market_proxy" in captured_proxy
    lag1 = close_series.pct_change().shift(1)
    forward = close_series.pct_change().shift(-1)
    mp = captured_proxy["market_proxy"]
    # 真值：proxy == lag1；≠ forward（產線改 shift(-1) → 此 assert 紅）
    np.testing.assert_allclose(
        mp.fillna(0).to_numpy(),
        lag1.reindex(mp.index).fillna(0).to_numpy(),
        atol=_ATOL,
        equal_nan=True,
    )
    assert not np.allclose(
        mp.fillna(0).to_numpy(),
        forward.reindex(mp.index).fillna(0).to_numpy(),
        equal_nan=False,
    ), "production market_proxy must not equal forward pct_change().shift(-1)"

    # B4 C-3：factor OFF control deep-equal + proxy-causal face 歸因存在
    import json

    from tests.golden.la2.attribution_validator import (
        load_allowlist,
        validate_diffs,
    )

    al = load_allowlist(_REPO_ROOT / "tests/golden/la2/attribution_allowlist.json")
    # control factor_disabled 在 BTC/ETH baseline 均 skipped
    for name in ("BTCUSDT_1h_baseline.json", "ETHUSDT_12h_baseline.json"):
        bl = json.loads(
            (_REPO_ROOT / "tests/golden/la2" / name).read_text(encoding="utf-8")
        )
        ctrl = (bl.get("control") or {}).get("factor_disabled") or {}
        assert ctrl.get("enabled") is False
        assert ctrl.get("skipped") is True
        # GS/PCA 算法面 control 路徑：enabled face 的 gs/pca 與 B0 byte-stable
        # （EXPECTED_FACE 已鎖；此處斷言 proxy_kind 因果）
        exp = ((bl.get("factor") or {}).get("exposure") or {})
        assert exp.get("proxy_kind") == "trailing_close_ret"
        assert int(exp.get("proxy_lag") or 0) == 1
    # face rebaseline diffs 全列 allowlist → 0 unexpected
    face_diffs = [
        r
        for r in (al.get("rows") or [])
        if r.get("behavior") == "face_rebaseline"
        and r.get("class") == "P2-3a-proxy-causal"
    ]
    assert len(face_diffs) >= 2  # BTC+ETH exposure
    result = validate_diffs(face_diffs, al)
    assert result.ok is True and result.unexpected_count == 0


def test_adversarial_validator_diagnostic_only() -> None:
    """B3：adversarial_validator diagnostic_only 標記存在（含 F11 direct methods）。"""
    from momentum.Analysis.adversarial_validator import AdversarialValidator

    assert AdversarialValidator.DIAGNOSTIC_ONLY is True
    assert AdversarialValidator.ANALYSIS_STATUS == "diagnostic_only"

    rng = np.random.default_rng(3)
    X_train = pd.DataFrame(rng.normal(size=(80, 3)), columns=list("abc"))
    X_test = pd.DataFrame(rng.normal(size=(40, 3)) + 0.5, columns=list("abc"))
    av = AdversarialValidator({"n_estimators": 20, "cv": 2})
    out = av.validate_distribution(X_train, X_test)
    assert out.get("diagnostic_only") is True
    assert out.get("analysis_status") == "diagnostic_only"
    assert out.get("signal_use_denied") is True
    assert out.get("oos_guarantees") is False

    # F11：feature_level_tests / detect_leakage 直出亦須 envelope（漏標→FAIL）
    feat = av.feature_level_tests(X_train, X_test)
    assert feat.get("diagnostic_only") is True
    assert feat.get("analysis_status") == "diagnostic_only"
    assert feat.get("signal_use_denied") is True
    assert feat.get("oos_guarantees") is False
    # per-feature 結果仍在（算法不變）
    assert any(isinstance(v, dict) and "ks_statistic" in v for v in feat.values())

    y = rng.integers(0, 2, size=len(X_train)).astype(float)
    ts = np.arange(len(X_train), dtype=np.int64)
    leak = av.detect_leakage(X_train, y, ts, future_window=5)
    assert leak.get("diagnostic_only") is True
    assert leak.get("analysis_status") == "diagnostic_only"
    assert leak.get("signal_use_denied") is True
    assert leak.get("oos_guarantees") is False
    assert "suspicious_features" in leak
    assert leak.get("status") in {"ok", "skipped"}

    full = av.full_validation(X_train, X_test)
    assert full.get("diagnostic_only") is True
    assert full.get("analysis_status") == "diagnostic_only"


def test_analysis_status_diagnostic() -> None:
    """B3：adversarial diagnostic_only + root ok_oos 時仍 deny 進 signal。"""
    from momentum.Analysis.adversarial_validator import AdversarialValidator
    from momentum.Analysis.ic_reporter import ICReporter
    from momentum.core.contracts import deny_factor_in_ok_oos
    from api.services.ic_analysis_service import ICAnalysisService

    av = AdversarialValidator({"n_estimators": 10, "cv": 2})
    rng = np.random.default_rng(5)
    X_train = pd.DataFrame(rng.normal(size=(60, 2)), columns=["x", "y"])
    X_test = pd.DataFrame(rng.normal(size=(30, 2)), columns=["x", "y"])
    out = av.validate_distribution(X_train, X_test)

    # marker 存在
    assert out["analysis_status"] == "diagnostic_only"
    assert out["signal_use_denied"] is True

    # root ok_oos + diagnostic nested → 真 production deny（contracts + export + get_result）
    report = {
        "analysis_status": "ok_oos",
        "adversarial_validation": out,
    }
    with pytest.raises(ValueError, match="diagnostic_only|signal"):
        deny_factor_in_ok_oos(report)

    # production export 出口（ic_reporter.export_all）
    reporter = ICReporter(config={})
    with pytest.raises(ValueError, match="diagnostic_only|signal|deny_factor"):
        reporter.export_all(report, output_dir="/tmp/la2_b3_diag_export", case_id="diag")

    # production API 出口 get_result
    svc = ICAnalysisService()
    tid = "la2-b3-diag-task"
    with svc._lock:
        svc._tasks[tid] = {
            "task_id": tid,
            "status": "completed",
            "progress": 1.0,
            "result": report,
        }
    with pytest.raises(ValueError, match="diagnostic_only|signal|deny_factor"):
        svc.get_result(tid)

    # factor deny 仍獨立可證
    report_f = {
        "analysis_status": "ok_oos",
        "factor": {
            "module": "exposure",
            "oos_guarantees": False,
            "fit_scope": "full_sample",
        },
    }
    with pytest.raises(ValueError, match="deny_factor_in_ok_oos"):
        deny_factor_in_ok_oos(report_f)
