"""FF-STAT Task 2.4（SPEC v32–v43）：倍數表補齊、封閉 period_keys、缺項擋下、量測 finite guard、五週期取最大。

真實 K 線（`kline_cache.h5` 1h／4h 與長歷史快取 5m／12h／1d），禁合成 fixture。實作前本檔應為紅。
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest

from tests.feature_engineering import ffstat_helpers as h

CONTRACT = h.CONTRACT
REPO = Path(__file__).resolve().parents[2]
TABLE_PATH = REPO / CONTRACT["warmup_table"]["path"]
COVERAGE_SCRIPT = REPO / "handoffs/run_receipts/ffstat_probes/warmup_table_coverage.py"
VERIFIER = REPO / "scripts/verify_l1_warmup_requirements.py"


def _load_module(path: Path, name: str):
    """載入腳本為模組並登記於 sys.modules（dataclass 需要）；同名已載入者直接回傳（mutant 可 monkeypatch 其屬性）。"""
    import sys

    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _entries() -> Dict[str, Dict[str, Any]]:
    import yaml

    return dict(yaml.safe_load(TABLE_PATH.read_text(encoding="utf-8"))["indicators"])


def test_every_enabled_output_point_covered_by_table() -> None:
    """Task 2.4 驗證：預設全設定之每個 L1 輸出點皆在表內、參數字典 ⊇ period_keys；類別全集＝十個模型欄位。"""
    from momentum.FeatureEngineering.feature_config import AtomicIndicatorConfig

    report = _load_module(COVERAGE_SCRIPT, "ffstat_warmup_cov").coverage_report("1h")
    assert report["categories"] == sorted(AtomicIndicatorConfig.model_fields)
    assert report["output_points"] > 0
    assert report["missing"] == [], report["missing"]
    assert report["missing_keys"] == [], report["missing_keys"][:10]


def test_every_entry_has_closed_class_and_period_keys() -> None:
    """Task 2.4（v37／v38）：每條目具 warmup_class（封閉值）與 period_keys 欄位；無參數者 period_keys 為空且有登記 K。"""
    classes = set(CONTRACT["warmup_table"]["warmup_classes"])
    for name, entry in _entries().items():
        assert entry.get("warmup_class") in classes, name
        assert isinstance(entry.get("period_keys"), list), name
        if not entry["period_keys"] and entry["warmup_class"] != "cumulative":
            assert isinstance(entry.get("k"), int) and entry["k"] > 0, name


def test_recursive_adopted_factor_ge_each_timeframe() -> None:
    """Task 2.4 驗證（v40）：recursive 條目之採用係數 ≥ 其 5m、1h、4h、12h、1d 各量得值，且五週期皆有量測。"""
    timeframes = CONTRACT["warmup_measure_timeframes"]
    for name, entry in _entries().items():
        if entry.get("warmup_class") != "recursive" or not entry.get("period_keys"):
            continue
        measured = entry["factors_by_timeframe"]
        assert set(timeframes) <= set(measured), name
        assert entry["recommended_factor"] >= max(float(measured[tf]) for tf in timeframes), name


def test_keltner_adopted_k_ge_atr_derived() -> None:
    """Task 2.4 驗證：KELTNER（EMA＋ATR）參數 233 之採用 K ≥ ATR 係數推得之根數（現行後備 1,049 低估）。"""
    entries = _entries()
    assert math.ceil(233 * entries["KELTNER"]["recommended_factor"]) >= math.ceil(233 * entries["ATR"]["recommended_factor"])


def test_boundary_26_parameterless_recursive_k_not_five() -> None:
    """Task 2.4 邊界①：無參數之遞迴指標（MAMA、SAREXT、HT_PHASOR、HT_SINE、KLINGER_VOLUME_OSC）K 以實測登記、不得為 5。"""
    entries = _entries()
    for name in ("MAMA", "SAREXT", "HT_PHASOR", "HT_SINE", "KLINGER_VOLUME_OSC"):
        entry = entries[name]
        k = entry.get("k") if not entry.get("period_keys") else None
        assert k is not None and k != 5 and k > 5, name


def test_boundary_27_finite_guard_rejects_unfinished_test() -> None:
    """Task 2.4 邊界①′（v33）：評估窗內 ground truth 有限而 test 非有限 ⇒ 誤差為 inf（r13 codex 真實 12h TEMA 反例）。"""
    verifier = _load_module(VERIFIER, "ffstat_verifier")
    import talib

    close = h.kline_frame(timeframe="12h")["close"].to_numpy(dtype=np.float64)
    gt = talib.TEMA(close, timeperiod=13)[-500:]
    test = talib.TEMA(close[-520:], timeperiod=13)[-500:]  # 較短前史 ⇒ test 開頭有 NaN
    assert np.isnan(test).any() and np.isfinite(gt).all()
    assert verifier.scale_normalized_error(test, gt, False) == float("inf")


def test_boundary_28_cumulative_registered_without_factor() -> None:
    """Task 2.4 邊界②：OBV、AD 登記 warmup_class=cumulative 而無係數。"""
    entries = _entries()
    for name in ("OBV", "AD"):
        assert entries[name]["warmup_class"] == "cumulative", name
        assert "recommended_factor" not in entries[name], name


def test_boundary_29_measure_receipt_per_indicator() -> None:
    """Task 2.4 邊界③：量測收據逐指標記標的、週期、量得 K 與 finite count。"""
    receipts = sorted((REPO / "handoffs" / "run_receipts").glob("*-ffstat-warmup-measure.json"))
    assert receipts, "缺倍數量測收據"
    doc = json.loads(receipts[-1].read_text(encoding="utf-8"))
    symbols = set(CONTRACT["warmup_measure_symbols"])
    timeframes = set(CONTRACT["warmup_measure_timeframes"])
    for row in doc["rows"]:
        assert {"indicator", "symbol", "timeframe", "k", "test_finite", "gt_finite"} <= set(row)
        assert row["test_finite"] == row["gt_finite"], row
    assert {r["symbol"] for r in doc["rows"]} == symbols
    assert {r["timeframe"] for r in doc["rows"]} == timeframes


def test_table_k_ge_every_converged_measurement() -> None:
    """v47（r31 codex P1-01）：採用值不得低於收據中任一已收斂量測（含前史 < 2K 之不可信者）——逐筆比對
    倍數表經 `stable_mask.instance_k` 規則所得之 K ≥ 該筆量得 K（DX／ADA／1d／144 實測 1,138 之反例）。"""
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    receipts = sorted((REPO / "handoffs" / "run_receipts").glob("*-ffstat-warmup-measure.json"))
    doc = json.loads(receipts[-1].read_text(encoding="utf-8"))
    table = _entries()
    low = []
    for row in doc["rows"]:
        if not row["converged"] or row["indicator"] not in table:
            continue
        entry = table[row["indicator"]]
        if entry.get("warmup_class") == "cumulative":
            continue
        spec = sm.OutputPointSpec(engine="receipt", indicator=row["indicator"], column="x", params=row["params"],
                                  period_keys=tuple(entry["period_keys"]))
        k = sm.instance_k(spec, table)
        if k < int(row["k"]):
            low.append((row["indicator"], row["timeframe"], row["symbol"], row["params"], k, row["k"]))
    assert not low, low[:10]


def test_mutation_adopted_k_below_measurement_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """r31 codex P1-01 之可證偽版：把 DX timeperiod=144 之採用值改為 1 ⇒ 不變量測試必紅。"""
    import yaml

    original = yaml.safe_load

    def lowered(text):
        doc = original(text)
        if isinstance(doc, dict) and "DX" in (doc.get("indicators") or {}):
            table = doc["indicators"]["DX"]["k_by_params"]
            table[next(k for k in table if "timeperiod=144" in k)] = 1
        return doc

    monkeypatch.setattr(yaml, "safe_load", lowered)
    with pytest.raises(AssertionError):
        test_table_k_ge_every_converged_measurement()


def test_cdl_pattern_entry_named() -> None:
    """Task 2.4 CDL pattern 映射（v39）：raw CDL＊ 之 K 取表內具名條目（取代全域 pattern_default_warmup_bars）。"""
    import yaml

    doc = yaml.safe_load(TABLE_PATH.read_text(encoding="utf-8"))
    entry = doc["indicators"][CONTRACT["warmup_table"]["pattern_entry"]]
    assert entry["warmup_class"] == "pattern" and entry["period_keys"] == [] and entry["k"] >= 1
    assert "pattern_default_warmup_bars" not in doc


def test_fallback_factor_removed() -> None:
    """Task 2.4／R5：刪 `_FALLBACK_FACTOR`；查不到之指標拋錯（不再 4.5 後備）。"""
    from momentum.FeatureEngineering.atomic import warmup_lookup

    assert not hasattr(warmup_lookup, "_FALLBACK_FACTOR")
    with pytest.raises(Exception):
        warmup_lookup.get_warmup_factor("NOT_IN_TABLE_XYZ")


def test_unregistered_indicator_blocked_before_hash_and_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.4 驗證：表外指標 ⇒ 設定 hash 與快取查詢之前拋錯（spy）、run 目錄零寫入、訊息含指標名與 max_period。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    called = {"hash": 0, "cache": 0}
    monkeypatch.setattr(FeatureFactory, "_compute_config_hash",
                        lambda self, *a, **k: called.__setitem__("hash", called["hash"] + 1) or "x")
    monkeypatch.setattr(FeatureFactory, "_try_load_cache",
                        lambda self, *a, **k: called.__setitem__("cache", called["cache"] + 1))
    from momentum.FeatureEngineering.config_manager import ConfigManager

    payload = h.stat_payload(fracdiff=False, adf=False)
    default_trend = [ind.model_dump() for ind in ConfigManager().get_merged_config().atomic_indicators.trend.indicators]
    payload["atomic_indicators"]["trend"] = {"enabled": True, "indicators": default_trend + [
        {"name": "NOT_IN_TABLE_XYZ", "enabled": True, "periods": [17]}]}
    h.prepare_stat_env(monkeypatch, tmp_path)
    before = h.snapshot_tree(tmp_path / "features")
    with pytest.raises(Exception) as exc:
        h.run_stat(tmp_path, payload)
    assert "NOT_IN_TABLE_XYZ" in str(exc.value) and "17" in str(exc.value)
    assert called == {"hash": 0, "cache": 0}
    assert h.snapshot_tree(tmp_path / "features") == before


# ─────────────────────────────── §V mutants

def test_mutation_fallback_restored_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦¹⁶：恢復 4.5 後備 ⇒ 必紅。"""
    from momentum.FeatureEngineering.atomic import warmup_lookup

    monkeypatch.setattr(warmup_lookup, "_FALLBACK_FACTOR", 4.5, raising=False)
    monkeypatch.setattr(warmup_lookup, "get_warmup_factor", lambda name: 4.5)
    with pytest.raises(AssertionError):
        test_fallback_factor_removed()


def test_mutation_finite_guard_removed_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V ⑦²¹：量測誤差改回遮除 NaN 後計算 ⇒ 邊界①′ 必紅。"""
    verifier = _load_module(VERIFIER, "ffstat_verifier")

    def legacy(test, gt, integer):
        mask = ~(np.isnan(gt) | np.isnan(test))
        diff = np.abs(test[mask] - gt[mask])
        return float(diff.max() / max(np.percentile(np.abs(gt[mask]), 75), np.std(gt[mask]), 1e-8))

    monkeypatch.setattr(verifier, "scale_normalized_error", legacy)
    with pytest.raises(AssertionError):
        test_boundary_27_finite_guard_rejects_unfinished_test()


def test_mutation_table_entry_removed_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """刪表中一項（EMA）⇒ 覆蓋測試必紅。"""
    import yaml

    original = yaml.safe_load

    def without_ema(text):
        doc = original(text)
        if isinstance(doc, dict) and "indicators" in doc:
            doc["indicators"].pop("EMA", None)
        return doc

    monkeypatch.setattr(yaml, "safe_load", without_ema)
    with pytest.raises(AssertionError):
        test_every_enabled_output_point_covered_by_table()
