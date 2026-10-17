"""FF-NAME Task 0.1 — 改前凍結（docs/FFNAME_SPEC.md §G、Task 0.1）。

邊界：①同名欄出自兩個組名點 ⇒ 凍結失敗並列出；②零件中 source 為 None 照實記錄。
驗證：`freeze_baseline.py --check` rc 0（manifest 全部欄有零件紀錄；L2 配對簽名、lag 輸入集合、欄序、group_id、
平穩化決策鍵均已記）。baseline.json 由 Task 0.1 於改前 HEAD 碼態產出；產出前本檔之 baseline 測試為紅（不 skip）。
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tests.feature_engineering.ffname_helpers import BASELINE_PATH, FREEZE_SCRIPT, REPO, load_freeze_module

freeze = load_freeze_module()


def _part(old_name: str, point: str, source=None, raw_lookup_key=None):
    return freeze.NamingPart(
        old_name=old_name, kind="atomic", source=source, raw_lookup_key=raw_lookup_key,
        category="microstructure", indicator="amihud", params=(("21",),), ops=(), tf=None, point=point,
    )


def _duplicate_detected(recorder_cls) -> bool:
    """同一舊名由兩個不同組名點記錄 ⇒ FreezeError 且訊息同時列出兩個組名點（鑑別函式，供 mutation 共用）。"""
    rec = recorder_cls()
    rec.record(_part("ms_amihud_illiq_21", point="A3:microstructure._compute_amihud"))
    try:
        rec.record(_part("ms_amihud_illiq_21", point="A4:derived._apply_pair_operator"))
    except freeze.FreezeError as exc:
        text = str(exc)
        return "ms_amihud_illiq_21" in text and "A3:microstructure._compute_amihud" in text and "A4:derived._apply_pair_operator" in text
    return False


def test_boundary_01_same_name_from_two_points_fails_and_lists():
    assert _duplicate_detected(freeze.PartRecorder)


def test_boundary_02_source_none_recorded_as_is():
    rec = freeze.PartRecorder()
    rec.record(_part("tr_mdd_21", point="A3:tail_risk._compute_max_drawdown", source=None, raw_lookup_key=None))
    parts = rec.parts()
    assert parts["tr_mdd_21"].source is None and parts["tr_mdd_21"].raw_lookup_key is None
    rows = rec.to_json()
    row = next(r for r in rows if r["old_name"] == "tr_mdd_21")
    assert row["source"] is None and row["raw_lookup_key"] is None
    assert json.loads(json.dumps(rows))  # 可序列化
    assert '"source": null' in json.dumps(row, sort_keys=True)


def test_same_point_rerecord_is_not_duplicate():
    """同一組名點重複記錄同一欄（如多週期迴圈）不得誤判為兩個組名點。"""
    rec = freeze.PartRecorder()
    rec.record(_part("ms_amihud_illiq_21", point="A3:microstructure._compute_amihud"))
    rec.record(_part("ms_amihud_illiq_21", point="A3:microstructure._compute_amihud"))
    assert list(rec.parts()) == ["ms_amihud_illiq_21"]


def test_missing_parts_detects_unrecorded_manifest_column():
    parts = {"ms_amihud_illiq_21": _part("ms_amihud_illiq_21", point="A3")}
    assert freeze.missing_parts(["ms_amihud_illiq_21", "ent_perm_21"], parts) == ["ent_perm_21"]
    assert freeze.missing_parts(["ms_amihud_illiq_21"], parts) == []


def test_baseline_check_rc0():
    proc = subprocess.run([sys.executable, str(FREEZE_SCRIPT), "--check"], cwd=str(REPO),
                          capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_baseline_records_all_sections():
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    for key in ("columns", "parts", "l2_pairs", "l4_lag_inputs", "column_order", "group_ids", "groups",
                "stationarity_keys", "stationarity_decisions"):
        assert key in data and data[key], key
    recorded = {row["old_name"] for row in data["parts"]}
    assert set(data["columns"]) <= recorded
    for col, fp in data["columns"].items():
        assert {"dtype", "shape", "nan_sha256", "value_sha256"} <= set(fp), col


def test_mutation_recorder_without_duplicate_check_is_caught(monkeypatch):
    """mutant：record 不檢查組名點（後寫覆蓋）⇒ 邊界①之鑑別函式翻為 False。"""
    class LenientRecorder:
        def __init__(self):
            self._parts = {}

        def record(self, part):
            self._parts[part.old_name] = part

        def parts(self):
            return dict(self._parts)

    monkeypatch.setattr(freeze, "PartRecorder", LenientRecorder)
    assert _duplicate_detected(freeze.PartRecorder) is False
