"""TFWINDOW Task 3.1：rolling 視窗依 run 週期換算——生產路徑接線（`ICEngine.set_timeframe` ← `metadata.timeframe`）。

SPEC：`docs/TFWINDOW_SPEC.md`　TODO：`docs/EVTWARMUP_TODO.md` Task 3.1

- 引擎層：[21,63,126] 於 1h ⇒ [252,756,1512]；12h ⇒ 不變；缺／非法 ⇒ 不變＋揭露值
- 接線主 gate（經 `analyze`）：12h fixture rolling 鍵不變＋`timeframe_adjustment=="applied"`；1h fixture 鍵集 ×12；
  meta 拿掉／非法 timeframe ⇒ analyze 於切分先 fail-closed（ValueError）；`not_applied:*` 揭露值只在引擎層可觀測
- 1h golden：`tests/golden/tfwindow/rolling_keys_1h.json`（鍵集＋每視窗序列長度＋值 sha256）
- 誠實邊界（TW-RESID-1）：1h fixture 2000 根 ⇒ warmup 1517 > 測試段 ⇒ 全域 fallback（預期，非本票缺陷）
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_engine import ICEngine
from tests.momentum.helpers.ichc_run import run_analyze

REPO = Path(__file__).resolve().parents[2]
GOLDEN_1H = REPO / "tests/golden/tfwindow/rolling_keys_1h.json"
H5_1H = "BTCUSDT_1h_*_a0_tail2000.h5"


def _engine() -> ICEngine:
    return ICEngine(ICConfig().ic_calculation.model_dump())


def test_engine_set_timeframe_adjusts_windows_and_discloses():
    e = _engine()
    base = [21, 63, 126]
    assert e._adjust_rolling_windows(base) == base                        # 未注入 ⇒ 不變（改前行為）
    assert e.set_timeframe("1h") == "applied" and e._adjust_rolling_windows(base) == [252, 756, 1512]
    assert e.set_timeframe("12h") == "applied" and e._adjust_rolling_windows(base) == base
    assert e.set_timeframe("4h") == "applied" and e._adjust_rolling_windows(base) == [63, 189, 378]
    assert e.set_timeframe(None) == "not_applied:missing_timeframe" and e._adjust_rolling_windows(base) == base
    assert e.set_timeframe("") == "not_applied:missing_timeframe"
    assert e.set_timeframe("bad") == "not_applied:invalid_timeframe" and e._adjust_rolling_windows(base) == base


def _rolling_keys(report: dict) -> set:
    rolling = report.get("rolling_ic_series") or {}
    keys: set = set()
    for feat, windows in rolling.items():
        if isinstance(windows, dict):
            keys |= set(windows.keys())
    return keys


def test_12h_fixture_windows_unchanged_and_applied():
    rep = run_analyze(None)
    d = rep["metadata"]["ic_window_disclosure"]
    assert d["timeframe_adjustment"] == "applied" and d["timeframe"] == "12h"
    assert d["adjusted_windows"] == [21, 63, 126] and d["icir_role"] == "threshold"
    assert _rolling_keys(rep) == {"window_21", "window_63", "window_126"}


@pytest.fixture(scope="module")
def report_1h():
    return run_analyze(None, h5_glob=H5_1H)


def test_1h_fixture_window_keys_scaled_by_12(report_1h):
    d = report_1h["metadata"]["ic_window_disclosure"]
    assert d["timeframe_adjustment"] == "applied" and d["timeframe"] == "1h"
    assert d["adjusted_windows"] == [252, 756, 1512]
    assert _rolling_keys(report_1h) == {"window_252", "window_756", "window_1512"}
    # TW-RESID-1：1h 2000 根 fixture 之 warmup 1517 > 測試段 ⇒ 全域 fallback 為預期，且必須 loud
    if report_1h["analysis_status"] != "ok_oos":
        assert report_1h["metadata"]["oos_downgrade"]["reason"] in {"rolling_warmup_insufficient", "insufficient_data"}


def test_1h_golden_rolling_keys_values(report_1h):
    payload = _golden_payload(report_1h)
    assert GOLDEN_1H.is_file(), "1h golden 缺席：先跑 handoffs/20260909-probe-tfwindow-1h-golden.py --write"
    golden = json.loads(GOLDEN_1H.read_text(encoding="utf-8"))
    assert payload["window_keys"] == golden["window_keys"]
    assert payload["lengths"] == golden["lengths"]
    assert payload["values_sha256"] == golden["values_sha256"]


def _golden_payload(report: dict) -> dict:
    rolling = report.get("rolling_ic_series") or {}
    keys = sorted(_rolling_keys(report))
    lengths = {}
    h = hashlib.sha256()
    for feat in sorted(rolling):
        windows = rolling[feat] or {}
        for k in keys:
            seq = windows.get(k) or []
            lengths.setdefault(k, len(seq))
            h.update(json.dumps(seq, sort_keys=True, default=str).encode("utf-8"))
    return {"window_keys": keys, "lengths": lengths, "values_sha256": h.hexdigest(), "n_features": len(rolling)}


def test_missing_timeframe_fails_closed_before_stage4():
    """邊界③（analyze 層）：meta 缺 timeframe ⇒ 切分先 fail-closed（ValueError），永遠到不了視窗換算——
    `not_applied:missing_timeframe` 只在引擎層可觀測（見 test_engine_set_timeframe_adjusts_windows_and_discloses）。"""
    with pytest.raises(ValueError, match="Unsupported or missing timeframe"):
        run_analyze(None, h5_glob=H5_1H, meta_override={"timeframe": None})


def test_invalid_timeframe_fails_closed_before_stage4():
    """邊界④（analyze 層）：非法字串同上 fail-closed；`not_applied:invalid_timeframe` 只在引擎層可觀測。"""
    with pytest.raises(ValueError, match="Unsupported or missing timeframe"):
        run_analyze(None, h5_glob=H5_1H, meta_override={"timeframe": "bad"})
