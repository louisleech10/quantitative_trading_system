"""FF-TFMETA §G golden／baseline（docs/FFTFMETA_SPEC.md §G）。

真實 kline 小窗 run：改前（動工前 HEAD）凍結於 tests/_golden/fftfmeta/baseline.json，改後同參數重跑比對：
群組檔名集合、每群組逐欄四 hash 摘要、去除允許路徑後之 manifest 與 task record canonical JSON 全等；
允許路徑之改後值恰為 SPEC 所定。基準產生器：handoffs/run_receipts/fftfmeta_probes/freeze_baseline.py。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.feature_engineering import fftfmeta_golden_helpers as g

pytestmark = pytest.mark.requires_kline

_MULTI = ["1h", "12h"]


def _compare(base: Dict[str, Any], fp: Dict[str, Any]) -> List[str]:
    """回傳與基準不等之項（空＝全等）：群組檔名集合、每群組摘要、去除允許路徑後之兩份 JSON。"""
    diffs: List[str] = []
    for key in ("group_files_sha256", "manifest_stripped_sha256", "task_stripped_sha256"):
        if base[key] != fp[key]:
            diffs.append(key)
    for name in sorted(set(base["groups"]) | set(fp["groups"])):
        if base["groups"].get(name) != fp["groups"].get(name):
            diffs.append(f"group {name}")
    return diffs


def _rerun(tmp_path: Path, name: str) -> Dict[str, Any]:
    base = g.load_baseline()["references"][name]
    art = g.run(tmp_path / "features", base["payload"], *g.WINDOW)
    return g.fingerprint(art)


def test_golden_multi_tf_features_unchanged_and_timeframes_canonical(tmp_path: Path) -> None:
    """健康多週期 run：特徵與去除允許路徑之 JSON 全等；manifest 與 task record 之週期三欄＝[1h,12h]／[1h,12h]／[]、complete。"""
    base = g.load_baseline()["references"]["multi"]
    fp = _rerun(tmp_path, "multi")
    assert _compare(base, fp) == []
    layers = base["allowed"]["manifest"]["root"]["expected_layers"]  # 改前已正確之層欄（本票不改層之判定）
    for where in ("root", "raw"):
        m = fp["allowed"]["manifest"][where]
        assert (m["expected_timeframes"], m["present_timeframes"], m["failed_timeframes"]) == (_MULTI, _MULTI, []), where
        assert m["quality_status"] == "complete", where
        # 其餘允許路徑亦逐鍵定值（r5 codex P1-03：digest 去除之欄不得無斷言）
        assert (m["expected_layers"], m["present_layers"], m["failed_layers"], m["failure_reasons"]) == (
            layers, layers, [], []), where
    assert fp["allowed"]["manifest"]["root"]["run_status"] == "complete"
    assert fp["allowed"]["manifest"]["raw"]["run_status"] is None  # raw 無此鍵（§C 不新增；r6 codex P1-02）
    t = fp["allowed"]["task"]
    assert (t["expected_timeframes"], t["present_timeframes"], t["failed_timeframes"]) == (_MULTI, _MULTI, [])
    assert (t["quality_status"], t["run_status"]) == ("complete", "complete")
    assert (t["expected_layers"], t["present_layers"], t["failed_layers"], t["failure_reasons"]) == (layers, layers, [], [])


def test_golden_degraded_single_tf_manifest_matches_task_record(tmp_path: Path) -> None:
    """降級單週期 reference（max_nan_ratio=0.0）：特徵與 JSON 全等；manifest 根與 artifacts.raw 由 complete 變 partial，
    failure_reasons 等於 task record；task record 之 quality_status／failure_reasons／quality_thresholds 改前改後相等。"""
    base = g.load_baseline()["references"]["degraded"]
    fp = _rerun(tmp_path, "degraded")
    assert _compare(base, fp) == []
    root, raw, task = fp["allowed"]["manifest"]["root"], fp["allowed"]["manifest"]["raw"], fp["allowed"]["task"]
    assert base["allowed"]["manifest"]["root"]["quality_status"] == "complete"  # 改前（缺陷）：manifest 未降級
    assert root["quality_status"] == root["run_status"] == "partial"
    assert raw["quality_status"] == "partial"
    assert raw["run_status"] is None  # raw 無此鍵（§C 不新增；r6 codex P1-02）
    assert root["failure_reasons"] == task["failure_reasons"]
    assert any(r.startswith("nan_ratio=") and ">max_nan_ratio=0" in r for r in task["failure_reasons"])
    for key in ("quality_status", "failure_reasons", "quality_thresholds"):
        assert task[key] == base["allowed"]["task"][key], key
    before = base["allowed"]["manifest"]["root"]
    for where, m in (("root", root), ("raw", raw), ("task", task)):  # 層與週期欄：降級不動層判定（r5 codex P1-03）
        for key in ("expected_layers", "present_layers", "failed_layers"):
            assert m[key] == before[key], (where, key)
        assert (m["expected_timeframes"], m["present_timeframes"], m["failed_timeframes"]) == (["1h"], ["1h"], []), where


def test_golden_baseline_frozen_before_change() -> None:
    """基準之改前允許路徑值即缺陷現況（manifest 週期欄只有 primary）——證基準確於動工前凍結。"""
    multi = g.load_baseline()["references"]["multi"]["allowed"]
    assert multi["manifest"]["root"]["present_timeframes"] == ["1h"]
    assert multi["task"]["present_timeframes"] == _MULTI


def test_mutation_registry_reference_wrong_target_changes_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    """r5 codex P2-01：位置正規化只換工作目錄前綴；指向錯檔名或錯 run 之 reference 必改 digest。"""
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", "/tmp/work_a")
    right = {"generation_metadata": {"source_registry_manifest": "/tmp/work_a/manifest.json"}}
    moved = {"generation_metadata": {"source_registry_manifest": "/tmp/work_a/manifest.json"}}
    wrong_name = {"generation_metadata": {"source_registry_manifest": "/tmp/work_a/other.json"}}
    wrong_run = {"generation_metadata": {"source_registry_manifest": "/wrong-run/manifest.json"}}
    digest = lambda m: g.canonical_json(g.strip_manifest(m))  # noqa: E731
    assert digest(right) == digest(moved)
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", "/tmp/work_b")
    assert digest({"generation_metadata": {"source_registry_manifest": "/tmp/work_b/manifest.json"}}) == g.canonical_json(
        {"generation_metadata": {"source_registry_manifest": "<cgsa_work>/manifest.json"}})
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", "/tmp/work_a")
    assert digest(wrong_name) != digest(right)
    assert digest(wrong_run) != digest(right)


def test_mutation_registry_reference_missing_file_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """r6 codex P2-01：同字面 reference 但指向之檔已消失 ⇒ 指紋前置檢查必報。"""
    work = tmp_path / "work"
    work.mkdir()
    (work / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work))
    manifest = {"generation_metadata": {"source_registry_manifest": str(work / "manifest.json")}}
    assert g.registry_refs_problems(manifest) == []
    (work / "manifest.json").unlink()
    assert g.registry_refs_problems(manifest) != []
    assert g.registry_refs_problems({"x": {"source_registry_manifest": "/elsewhere/manifest.json"}}) != []


def test_mutation_golden_compare_detects_single_group_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """鑑別力：改後指紋只有一個群組摘要不同 ⇒ `_compare` 必報該群組；JSON 摘要不同亦報。"""
    base = g.load_baseline()["references"]["multi"]
    altered = {**base, "groups": dict(base["groups"])}
    victim = sorted(altered["groups"])[0]
    altered["groups"][victim] = "0" * 64
    monkeypatch.setattr(g, "fingerprint", lambda _art: altered)
    assert _compare(base, g.fingerprint(None)) == [f"group {victim}"]
    assert _compare(base, {**base, "task_stripped_sha256": "x"}) == ["task_stripped_sha256"]
