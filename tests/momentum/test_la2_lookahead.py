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
