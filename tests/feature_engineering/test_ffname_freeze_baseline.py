"""FF-NAME Task 0.1 — 改前凍結（docs/FFNAME_SPEC.md §G、Task 0.1）。

邊界（SPEC v15）：①同名欄出自兩個組名點 ⇒ 凍結失敗並列出；②零件 source 依輸入元組規則取自組名點之實際輸入，
不得為 None（baseline 內有 None ⇒ `--check` 失敗）；③raw lag 輸入以 `(tf, "raw", 資料鍵)` 記錄。
golden 值 oracle（§G v15）：逐欄 golden 非空且雜湊長＝契約 `refreeze.golden_value_hash_len`；無逐欄紀錄者須登記於
`refreeze.no_column_records` 並記 `golden_file_sha256`，未登記之空紀錄 ⇒ `--check` 失敗。
驗證：`freeze_baseline.py --check` rc 0（manifest 全部欄有零件紀錄；L2 配對簽名、lag 輸入集合、欄序、group_id、
平穩化決策鍵均已記）。baseline.json 由 Task 0.1 於改前 HEAD 碼態產出；產出前本檔之 baseline 測試為紅（不 skip）。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from tests._nocap_subprocess import run_watched_subprocess

import pytest

from tests.feature_engineering.ffname_helpers import (
    BASELINE_PATH,
    CONTRACT,
    FREEZE_SCRIPT,
    REPO,
    baseline_immutability_problems,
    load_freeze_module,
)

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
    """收集器層：假零件之 None 可序列化為 JSON null（收集器不擋 None；baseline 層之禁止見下兩條測試與 `--check`）。"""
    rec = freeze.PartRecorder()
    rec.record(_part("tr_mdd_21", point="A3:tail_risk._compute_max_drawdown", source=None, raw_lookup_key=None))
    parts = rec.parts()
    assert parts["tr_mdd_21"].source is None and parts["tr_mdd_21"].raw_lookup_key is None
    rows = rec.to_json()
    row = next(r for r in rows if r["old_name"] == "tr_mdd_21")
    assert row["source"] is None and row["raw_lookup_key"] is None
    assert json.loads(json.dumps(rows))  # 可序列化
    assert '"source": null' in json.dumps(row, sort_keys=True)


def test_boundary_02_source_never_none_in_baseline_parts():
    """SPEC v15 Task 0.1 ②：baseline 零件之 source 一律非 None；microstructure／entropy／tail-risk 取輸入元組。"""
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert data["parts"]
    assert [row["old_name"] for row in data["parts"] if row["source"] is None] == []
    advanced = [row for row in data["parts"] if row["category"] in ("microstructure", "entropy", "tail_risk")]
    assert advanced and all(row["source"] for row in advanced)
    rows = freeze.PartRecorder().to_json()
    assert json.loads(json.dumps(rows)) == []  # 空收集器可序列化


def test_mutation_part_with_source_none_fails_check(tmp_path):
    """mutant：baseline 任一零件 source 改 None ⇒ `--check` rc 1。"""
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    data["parts"][0]["source"] = None
    mutated = tmp_path / "baseline.json"
    mutated.write_text(json.dumps(data), encoding="utf-8")
    assert freeze.check(mutated) == 1


def test_boundary_03_raw_lag_inputs_recorded_as_tf_raw_key():
    """SPEC v15 Task 0.1 ③：lag 輸入集合每筆＝[tf, "raw"|"feature", 名]；raw 以資料鍵記（無週期段），且至少一筆。"""
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    triples = data["l4_lag_inputs"]
    assert all(isinstance(t, list) and len(t) == 3 and t[1] in ("raw", "feature") for t in triples)
    raw = [t for t in triples if t[1] == "raw"]
    assert raw and all(t[0] in CONTRACT["refreeze"]["full_reference"]["timeframes"] for t in raw)


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
    proc = run_watched_subprocess([sys.executable, str(FREEZE_SCRIPT), "--check"], cwd=str(REPO))
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


def test_baseline_golden_values_nonempty_and_complete():
    """審查 r13 P1-05：每個重凍對象 golden 之 `golden_values` 非空，且 fingerprint 數 == 該 golden 欄數（凍結當下）。"""
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    # SPEC v21：不可變 baseline 之範圍＝refreeze.baseline_goldens（refreeze.goldens 只列實際重凍者，為其子集）
    goldens = CONTRACT["refreeze"]["baseline_goldens"]
    outside = {rel for rel, d in CONTRACT["refreeze"]["dispositions"].items() if d.get("outside_baseline")}
    assert set(CONTRACT["refreeze"]["goldens"]) - outside <= set(goldens)  # baseline 範圍外者只准契約明示（v22 漏列補登）
    assert sorted(data["golden_values"]) == sorted(goldens)
    # SPEC v15 §G：逐欄 golden（未登記 no_column_records）須非空、數＝欄數
    empty = [rel for rel in goldens
             if rel not in CONTRACT["refreeze"]["no_column_records"] and not data["golden_values"][rel]]
    count_mismatch = [rel for rel in goldens if len(data["golden_values"][rel]) != data["golden_column_counts"][rel]]
    assert empty == [] and count_mismatch == []
    # 逐欄 golden 之值雜湊長＝契約 hash_len
    registered = CONTRACT["refreeze"]["no_column_records"]
    hash_len = int(CONTRACT["refreeze"]["golden_value_hash_len"])
    bad_len = [name for name in goldens if name not in registered
               and any(len(h) != hash_len for h in data["golden_values"][name].values())]
    assert bad_len == []
    # 登記之無逐欄紀錄 golden：空紀錄、欄數 0、類別屬 oracle_classes、理由非空、檔案 sha256＝baseline frozen_at_head 之該檔
    # （SPEC v21：重凍後磁碟上之 K2 golden 依處置改變；基準之錨為凍結點之 git 物件）
    import subprocess

    assert set(registered) <= set(goldens)
    assert sorted(data["golden_file_sha256"]) == sorted(registered)
    for name, entry in registered.items():
        assert data["golden_values"][name] == {} and data["golden_column_counts"][name] == 0, name
        assert entry["class"] in CONTRACT["refreeze"]["oracle_classes"] and str(entry["reason"]).strip(), name
        blob = subprocess.run(["git", "show", f"{data['frozen_at_head']}:{name}"], cwd=str(REPO), capture_output=True)
        assert blob.returncode == 0, name
        assert data["golden_file_sha256"][name] == hashlib.sha256(blob.stdout).hexdigest(), name


def test_mutation_unregistered_empty_golden_fails_check(monkeypatch):
    """SPEC v15 §G mutant：空紀錄之 golden 自 no_column_records 移除 ⇒ `--check` rc 1（不得只 WARN）。"""
    registered = dict(CONTRACT["refreeze"]["no_column_records"])
    victim = sorted(registered)[0]
    registered.pop(victim)
    monkeypatch.setattr(freeze, "no_column_records", lambda: dict(registered))
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert any(victim in p for p in freeze._golden_problems(data))
    assert freeze.check(BASELINE_PATH) == 1


def test_baseline_sha_anchor_immutable():
    """審查 r13 P1-05：baseline.sha256 等於 baseline.json 之 sha256，且該 sha 檔只有 1 筆提交（Phase 2 起不得改）。"""
    assert baseline_immutability_problems() == []


def test_mutation_baseline_edited_after_anchor_is_caught(tmp_path, monkeypatch):
    """mutant：baseline.json 於錨定後被改（sha 檔未同步）⇒ sha_mismatch。"""
    edited = tmp_path / "baseline.json"
    edited.write_bytes(BASELINE_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(freeze, "BASELINE_PATH", edited)
    assert "sha_mismatch" in baseline_immutability_problems(baseline_path=freeze.BASELINE_PATH)


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
