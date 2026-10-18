"""FF-NAME v19 §N：版控之 IC 測試固定輸入 h5（la0／la1 等 10 檔）欄名為舊命名世代，IC 路徑不得解讀之。

把 `parse_feature_name` 於全部已載入之 momentum／api 模組換成「一被呼叫即拋」之替身（`patch_everywhere`），重放固定輸入：
- 標註：各 h5 根屬性 `naming_note`（不放 *_meta.json：其鍵會被 IC 複製進報告 metadata 而改 golden）。
- la0（ETHUSDT 12h，ichc runner）：結果之 canonical sha 與正常重放相等，且等於 GAP-2 §G-1 凍結之 golden
  （`handoffs/run_receipts/gap2_golden_pre.json`，同 `tests/momentum/Analysis/test_gap2_golden.py`）。
- la1（BTCUSDT 1h strat 輸入）：替身下之結果 canonical sha 與正常重放相等。
替身被呼叫次數須為 0（被呼叫即拋 ⇒ 重放失敗；另以計數器明證）。真實 kline、版控輸入，不造資料。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

import momentum.FeatureEngineering.feature_naming as fn
from tests.feature_engineering.ffname_helpers import patch_everywhere
from tests.momentum.helpers.ichc_run import fixture_paths, run_analyze

REPO = Path(__file__).resolve().parents[2]
LA1_INPUTS = REPO / "tests" / "golden" / "la1" / "inputs"


def _raising_parse(calls: List[str]):
    def stub(name, *a, **k):
        calls.append(str(name))
        raise AssertionError(f"IC 路徑解讀了固定輸入之欄名：{name!r}（FF-NAME v19 §N：欄名不被解讀）")

    return stub


def _naming_noted(h5: Path) -> bool:
    """固定輸入 h5 根屬性帶 v18 命名世代與「欄名不被解讀、世代為舊」之標註（標註不放 *_meta.json：其鍵會被 IC 複製進
    報告 metadata，改之即改 golden）。"""
    import h5py

    with h5py.File(h5, "r") as handle:
        return (int(handle.attrs.get(fn.FEATURE_NAMING_VERSION_KEY, -1)) == fn.CURRENT_FEATURE_NAMING_VERSION
                and "欄名不被解讀" in str(handle.attrs.get("naming_note", "")))


def _gap2_sha(report: Dict[str, Any]) -> str:
    from scripts.gap2_freeze_golden import gap2_canonical_sha

    return gap2_canonical_sha(report)


def _run_la1(h5: Path) -> Dict[str, Any]:
    """la1 固定輸入之重放（同 ichc runner：持久化導 tmp、真實 kline reader）。"""
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    meta = h5.with_name(h5.stem + "_meta.json")
    orchestrator = create_ic_analyzer()
    tmp = Path(tempfile.mkdtemp(prefix="ffname_opaque_la1_"))
    reporter = orchestrator._reporter
    save_report, save_log, save_filtered = reporter.save_report, reporter.save_filter_log, reporter.save_filtered_features
    reporter.save_report = lambda report, output_dir=None, case_id=None, **kw: save_report(
        report, output_dir=str(tmp / "reports"), case_id=case_id, **kw)
    reporter.save_filter_log = lambda log, output_dir=None, case_id=None, **kw: save_log(
        log, output_dir=str(tmp / "reports"), case_id=case_id, **kw)
    reporter.save_filtered_features = lambda df, columns, output_path, **kw: save_filtered(
        df, columns, str(tmp / "features" / Path(str(output_path)).name), **kw)
    return orchestrator.analyze(features_path=str(h5.resolve()), labels_path="", meta_path=str(meta.resolve()),
                                kline_reader=create_kline_storage_manager(cache_dir="data_cache/feature_klines"))


def test_la0_replay_does_not_parse_names_and_equals_golden(monkeypatch):
    pre_path = REPO / "handoffs" / "run_receipts" / "gap2_golden_pre.json"
    assert pre_path.is_file(), f"GAP-2 §G-1 凍結 golden 缺：{pre_path}"
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    h5, meta = fixture_paths()
    assert _naming_noted(h5)
    normal = run_analyze()
    calls: List[str] = []
    assert patch_everywhere(monkeypatch, fn.parse_feature_name, _raising_parse(calls)) >= 1
    opaque = run_analyze()
    assert calls == []
    assert _gap2_sha(opaque) == _gap2_sha(normal) == pre["canonical_sha"]


def test_la1_replay_does_not_parse_names(monkeypatch):
    h5 = next(iter(sorted(LA1_INPUTS.glob("BTCUSDT_1h_*_strat_*_tail2000.h5"))))
    assert _naming_noted(h5)
    normal = _run_la1(h5)
    calls: List[str] = []
    assert patch_everywhere(monkeypatch, fn.parse_feature_name, _raising_parse(calls)) >= 1
    opaque = _run_la1(h5)
    assert calls == []
    assert _gap2_sha(opaque) == _gap2_sha(normal)
    assert opaque["summary_table"], "la1 重放無結果（比對空集合不足以證明）"


def test_every_committed_ic_input_h5_carries_version_and_note():
    """審查 r2 CODEX-R2-P2-02：全部版控 IC 測試固定輸入 h5 皆帶命名世代與標註（漏一檔即紅）。"""
    import subprocess

    files = subprocess.run(["git", "ls-files", "tests/golden/*/inputs/*.h5"], cwd=str(REPO), capture_output=True,
                           text=True, check=True).stdout.split()
    assert len(files) == 10
    assert [rel for rel in files if not _naming_noted(REPO / rel)] == []


def test_mutation_parse_call_in_ic_path_is_caught(monkeypatch):
    """反例：若 IC 路徑解讀欄名（以於 stage0 讀檔後呼叫 parser 模擬），替身必拋 ⇒ 重放失敗。"""
    import momentum.Analysis.ic_filter_orchestrator as orch_mod

    real_load = orch_mod.ICFilterOrchestrator._load_features_hdf5

    def parsing_load(self, path):
        frame, meta = real_load(self, path)
        for column in frame.columns:
            fn.parse_feature_name(column)
        return frame, meta

    monkeypatch.setattr(orch_mod.ICFilterOrchestrator, "_load_features_hdf5", parsing_load)
    calls: List[str] = []
    patch_everywhere(monkeypatch, fn.parse_feature_name, _raising_parse(calls))
    with pytest.raises(Exception):
        run_analyze()
    assert calls
