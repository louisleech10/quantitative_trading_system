"""FRAMEPATH Task 1.1：CGSA 輸出改前／改後逐位元不變（docs/FRAMEPATH_SPEC.md §G、Task 1.1）。

基準＝`tests/_golden/framepath/cgsa_fingerprint.json`（`scripts/freeze_framepath_baseline.py freeze` 於 HEAD
6e07e0ad 凍結）。每格以同一 `run_cell` 重跑，`compare_cell` 逐項無容差比對；記憶體以 `memory_guard._Readings`
取樣、每格峰值 < 2 GB。真實 kline、單組串行（本檔各格依序執行，不得與其他重型生成並行）。

M1–M4 mutation（`feature_naming.tag_timeframe` 少標一週期、`_combine_layers` 對 `layer4_input` 回傳空表、L7 落盤前
改 float64、manifest 新增未登記鍵）於暫存工作樹實跑，收據 `handoffs/run_receipts/<date>-framepath-b1-mutation.txt`；
本檔之 `test_mutation_*` 驗比對器本身對該四類差異之鑑別力（不需生成）。
"""

from __future__ import annotations

import copy
import inspect
import json
import re
from pathlib import Path

import pytest

from momentum.FeatureEngineering.feature_storage import COMPLETENESS_FIELD_NAMES
from scripts import freeze_framepath_baseline as fb

REPO = Path(__file__).resolve().parents[2]
BASELINE = REPO / fb.BASELINE_REL


@pytest.fixture(scope="module")
def baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_baseline_frozen_at_head_with_all_cells(baseline):
    assert baseline["code_anchor"].startswith(fb.HEAD_COMMIT_PREFIX) and len(baseline["code_anchor"]) == 40
    assert baseline["code_state_errors"] == []
    assert tuple(baseline["cells"]) == fb.CELLS


def test_boundary_09_freeze_refuses_off_anchor_code(monkeypatch, tmp_path):
    """凍結碼態以 git 實核（審查 r17 CODEX-R17-P1-01）：momentum／api／config 與 6e07e0ad 不同 ⇒ 錯誤；相同 ⇒ 無錯；
    freeze 遇錯不產任何輸出。"""
    anchor = "6e07e0ad952d3cccbe3fd2bef39b5ff49dd13581"

    def runner(diff_out="", untracked_out=""):
        def _run(args):
            if args[:1] == ["rev-parse"]:
                return 0, anchor + "\n"
            if args[:1] == ["diff"]:
                # 只有以錨點為比較端之 diff 才回傳受控結果；以 HEAD 或其他端比較 ⇒ 視為有差（防比錯基準，r18 CODEX-R18-P1-01）
                return 0, diff_out if any(a.startswith(fb.HEAD_COMMIT_PREFIX) for a in args) else "momentum/x.py\n"
            if args[:1] == ["ls-files"]:
                return 0, untracked_out
            return 1, ""
        return _run

    assert fb.code_state_errors(runner()) == []
    # 實作期 r41：真函式之錯誤判定須於下方以替身置換 code_state_errors 之前驗（原置於置換後，恆呼叫替身）
    assert fb.code_state_errors(runner(diff_out="momentum/FeatureEngineering/feature_factory.py\n")) != []
    assert fb.code_state_errors(runner(untracked_out="api/services/new_untracked.py\n")) != []
    # 錨點與執行時 HEAD 分開解析（審查 r19 CODEX-R19-P1-02）：rev-parse HEAD 回不同 sha ⇒ head_commit 取該值
    later = "74fdd4d1" + "0" * 32

    def two_commits(args):
        if args[:1] == ["rev-parse"]:
            return 0, (later if args[-1] == "HEAD" else anchor) + "\n"
        return runner()(args)

    assert fb.resolve_commits(two_commits) == {"code_anchor": anchor, "head_commit": later}
    # freeze 之接線（審查 r20 CODEX-R20-P1-05、GROK-R20-P1-01）：寫入基準之 head_commit 取執行時 HEAD、
    # code_anchor 取錨點（格生成以替身代之，只驗組裝）
    wired = tmp_path / "wired.json"
    monkeypatch.setattr(fb, "code_state_errors", lambda git_runner=None: [])
    monkeypatch.setattr(fb, "resolve_commits", lambda git_runner=None: {"code_anchor": anchor, "head_commit": later})
    stub_fp = {k: None for k in fb.FINGERPRINT_KEYS}
    stub_fp.update(run_status="complete")
    monkeypatch.setattr(fb, "run_cell", lambda cell, work_root: {
        "fingerprint": dict(stub_fp, run_status="refused" if cell in fb.REFUSED_CELLS else "complete"),
        "memory": {"peak_bytes": 1, "readings": 1, "seconds": 1.0, "failed": [], "injected": False,
                   "non_root_member_seen": True},
        "receipt": {"resume_entered": cell == "C5"}})
    monkeypatch.setattr(fb, "_freeze_refusals", lambda cells: [])
    fb.freeze(wired)
    written = json.loads(wired.read_text(encoding="utf-8"))
    assert written["head_commit"] == later and written["code_anchor"] == anchor
    out = tmp_path / "cgsa_fingerprint.json"
    monkeypatch.setattr(fb, "code_state_errors", lambda git_runner=None: ["momentum 與 6e07e0ad 不同"])
    with pytest.raises(fb.FramepathBaselineError):
        fb.freeze(out)
    assert not out.exists()


def _install_sampler_spy(monkeypatch) -> dict:
    """以 spy 置換 `memory_guard._Readings`，記錄每個取樣器之 root 與每筆 sample()（審查 r26／r27）。"""
    from momentum.FeatureEngineering import memory_guard

    seen: dict = {"roots": [], "samples": []}
    real = memory_guard._Readings

    class _Spy(real):  # type: ignore[misc, valid-type]
        def __init__(self, system, root):
            super().__init__(system, root)
            seen["roots"].append(root)

        def sample(self):
            row = super().sample()
            seen["samples"].append(copy.deepcopy(row))
            return row

    monkeypatch.setattr(memory_guard, "_Readings", _Spy)
    return seen


def _assert_memory_from_sampler(mem: dict, seen: dict) -> None:
    """記憶體摘要之來源核對：唯一 root 為子行程（非本行程）、至少一筆讀數、memory（除 seconds）等於
    summarize_readings(實際讀數, root)，且每筆讀數之 members 皆含 root（root_missing == 0）。"""
    import os

    assert len(set(seen["roots"])) == 1 and seen["roots"][0] != os.getpid()
    root = seen["roots"][0]
    assert len(seen["samples"]) >= 1
    assert {k: v for k, v in mem.items() if k != "seconds"} == fb.summarize_readings(seen["samples"], root)
    assert mem["root_missing"] == 0 and mem["readings"] == len(seen["samples"])


@pytest.mark.parametrize("cell", fb.CELLS)
def test_cell_matches_frozen_baseline(baseline, tmp_path, cell, monkeypatch):
    seen = _install_sampler_spy(monkeypatch)
    fresh = fb.run_cell(cell, tmp_path)
    assert fresh["receipt"]["resume_entered"] is (cell == "C5")
    if cell == "C9":
        # 前置條件以檔案系統實核，不只讀收據字串（審查 r20 CODEX-R20-P1-04）
        import h5py

        receipt = fresh["receipt"]
        copy_path = Path(receipt["kline_copy"])
        assert copy_path.is_file() and str(copy_path).startswith(str(tmp_path))
        primary = f"{receipt['symbol']}/{receipt['primary_timeframe']}/data"
        with h5py.File(receipt["source_kline"], "r") as src, h5py.File(copy_path, "r") as h5:
            # 刪前證據（審查 r21 CODEX-R21-P1-03）：原始 kline 確有該 dataset；複本為原始之真複本（主週期等長）且只缺該 dataset
            assert f"{receipt['deleted_dataset']}/data" in src
            assert f"{receipt['deleted_dataset']}/data" not in h5
            assert primary in h5 and h5[primary].shape == src[primary].shape
        legacy = Path(receipt["legacy_kline_dir"])
        assert legacy.is_dir() and str(legacy).startswith(str(tmp_path)) and not any(legacy.iterdir())
    _assert_memory_from_sampler(fresh["memory"], seen)  # 逐格取樣來源核對（審查 r27 CODEX-R27-P1-01）
    assert fb.memory_gate_errors(cell, fresh["memory"]) == []
    assert fb.compare_cell(baseline["cells"][cell]["fingerprint"], fresh["fingerprint"]) == []


def test_boundary_01_resume_cell_equals_single_tf_cell(baseline):
    # C5 須有實際 resume 之觀測證據（審查 r17 CODEX-R17-P1-02：只比輸出相等無法分辨「每次重算」）
    assert baseline["cells"]["C5"]["receipt"]["resume_entered"] is True
    assert all(baseline["cells"][c]["receipt"]["resume_entered"] is False for c in fb.CELLS if c != "C5")
    c1 = baseline["cells"]["C1"]["fingerprint"]
    c5 = baseline["cells"]["C5"]["fingerprint"]
    assert fb.compare_cell({k: v for k, v in c1.items() if k != "path_receipt"},
                           {k: v for k, v in c5.items() if k != "path_receipt"}) == []


def test_boundary_02_run_status_per_cell(baseline):
    """實作期 r41（SPEC v18）：HEAD 實測 allow_partial 下缺次週期 K 線 ⇒ 生成前具名拒絕（非 partial）；C9 凍結
    拒絕之例外型別與訊息（須指名缺載之 `<symbol>/<次週期>`）且拒絕前不留 parquet／manifest。"""
    for cell in fb.CELLS:
        fp = baseline["cells"][cell]["fingerprint"]
        if cell in fb.REFUSED_CELLS:
            assert fp["run_status"] == "refused", cell
            receipt = baseline["cells"][cell]["receipt"]
            assert any(receipt["deleted_dataset"] in r for r in fp["failure_reasons"]), cell
            assert fp["completeness"]["leftover_artifacts"] == [], cell
        elif cell in fb.CALIBRATION_PARTIAL_CELLS:
            # 實作期 r41（SPEC v18 C4）：多週期平穩化開之短窗，部分欄前史不足校準長度 ⇒ 逐欄不平穩化之 partial；
            # 原因只准 calibration_insufficient_history、週期與層皆 present、無失敗
            comp = fp["completeness"]
            assert fp["run_status"] == "partial" and fp["failure_reasons"], cell
            assert all(r.startswith(fb.CALIBRATION_PARTIAL_REASON) for r in fp["failure_reasons"]), cell
            assert comp["failed_timeframes"] == [] and comp["failed_layers"] == [], cell
            assert comp["present_timeframes"] == comp["expected_timeframes"], cell
        else:
            assert fp["run_status"] == "complete", cell


def test_boundary_03_memory_gates_in_frozen_baseline(baseline):
    for cell in fb.CELLS:
        mem = baseline["cells"][cell]["memory"]
        assert fb.memory_gate_errors(cell, mem) == [], cell
        assert 0 < mem["peak_bytes"] < fb.PEAK_LIMIT_BYTES and mem["readings"] > 0 and mem["seconds"] > 0
    assert baseline["cells"]["C6"]["memory"]["non_root_member_seen"] is True


_HEALTHY_MEMORY = {"peak_bytes": 512 * 1024 ** 2, "readings": 30, "seconds": 3.0, "failed": [], "injected": False,
                   "non_root_member_seen": True, "root_missing": 0}


@pytest.mark.parametrize("cell,override", [
    ("C1", {"failed": [12345]}),
    ("C1", {"injected": True}),
    ("C1", {"readings": 0}),
    ("C1", {"peak_bytes": fb.PEAK_LIMIT_BYTES}),
    ("C6", {"non_root_member_seen": False}),
    ("C1", {"root_missing": 1}),
])
def test_boundary_08_memory_gate_rejects_each_fail_condition(cell, override):
    """§G 記憶體閘五種 FAIL 條件逐一（審查 r16 CODEX-R16-P1-02）：讀數 failed 非空、injected、無讀數、峰值 ≥ 2 GB、
    C6 無根以外成員；健康讀數兩格皆無錯。"""
    assert fb.memory_gate_errors("C1", _HEALTHY_MEMORY) == []
    assert fb.memory_gate_errors("C6", _HEALTHY_MEMORY) == []
    assert fb.memory_gate_errors(cell, {**_HEALTHY_MEMORY, **override}) != []


def test_boundary_04_c9_preconditions_recorded(baseline):
    """C9 前置條件之收據須可核（審查 r19 CODEX-R19-P1-06）：受控 kline 複本路徑、被刪之 `<symbol>/<次週期>` dataset、
    刪前存在／刪後讀回缺失、子行程環境之 LEGACY_KLINE_CACHE_DIR 指向空受控目錄；且拒絕原因指名該
    `<symbol>/<次週期>`（實作期 r41：HEAD 為具名拒絕，非 partial）。"""
    cell = baseline["cells"]["C9"]
    receipt = cell["receipt"]
    tf = receipt["dropped_timeframe"]
    assert receipt["kline_copy"] and receipt["kline_copy"] != receipt["source_kline"]
    assert receipt["deleted_dataset"] == f"{receipt['symbol']}/{tf}"
    assert receipt["readback_before"] == "present" and receipt["deleted_readback"] == "missing"
    assert receipt["legacy_kline_dir"] and receipt["legacy_kline_dir_entries_at_start"] == []
    assert receipt["child_env"]["LEGACY_KLINE_CACHE_DIR"] == receipt["legacy_kline_dir"]
    fp = cell["fingerprint"]
    assert fp["run_status"] == "refused" and any(receipt["deleted_dataset"] in r for r in fp["failure_reasons"])


def test_boundary_05_compare_domain_rejects_forbidden_and_non_scalar(tmp_path):
    domain = json.loads((REPO / fb.COMPARE_DOMAIN_REL).read_text(encoding="utf-8"))
    # 契約明列之禁排除鍵全部（審查 r16 CODEX-R16-P1-01：原只餵子集）＋ COMPLETENESS_FIELD_NAMES
    forbidden = tuple(domain["forbidden_exclusions"]["keys"])
    assert {"run_status", "quality_status", "failure_reasons", "feature_names", "columns", "config_hash",
            "skipped_timeframes"} <= set(forbidden)
    for key in (*forbidden, *COMPLETENESS_FIELD_NAMES):
        bad = copy.deepcopy(domain)
        bad["exclude"].append({"path": key, "category": "timestamp", "source": "t"})
        p = tmp_path / f"bad_{key}.json"
        p.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(fb.FramepathBaselineError):
            fb.load_compare_domain(p)
    bad = copy.deepcopy(domain)
    bad["exclude"].append({"path": "created_at", "category": "semantic", "source": "t"})
    p = tmp_path / "bad_cat.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(fb.FramepathBaselineError):
        fb.load_compare_domain(p)
    ok = fb.load_compare_domain()
    with pytest.raises(fb.FramepathBaselineError):
        fb.filter_manifest({"created_at": {"nested": 1}}, ok)


@pytest.mark.parametrize("path", ["", ".created_at", "created_at.", "a..b", "a.**.b", "a.*.*.b", "a.0.b",
                                  "a[0].b", "a.[].b", "a.*", "*"])
def test_boundary_13_compare_domain_path_grammar_rejects_malformed(tmp_path, path):
    """path 語法封閉（審查 r19 CODEX-R19-P1-03）：只准以 . 分隔之物件鍵與中間層單一 `*`；空、首尾點、連續點、`**`、
    兩個 `*`、數字或陣列記號、末段萬用 ⇒ 拒跑。"""
    domain = json.loads((REPO / fb.COMPARE_DOMAIN_REL).read_text(encoding="utf-8"))
    domain["exclude"].append({"path": path, "category": "timestamp", "source": "t"})
    p = tmp_path / "grammar.json"
    p.write_text(json.dumps(domain), encoding="utf-8")
    with pytest.raises(fb.FramepathBaselineError):
        fb.load_compare_domain(p)


def test_boundary_11_c5_resume_entered_is_observed_not_declared(tmp_path):
    """C5（SPEC v16 A10）：同 work dir 第二次生成進入 CGSA resume 分支（`resume_from_manifest` 對本格 work dir 被呼叫），
    強制重算則不進入；兩者輸出逐位元相等。HEAD 實測（收據 handoffs/run_receipts/20261008-framepath-c5-probe.json）：
    已完成 run 之中間群組已清，resume 回傳空 registry、L1–L6 照常重算，故本格驗「resume 分支之輸出不變」而非「跳過
    計算」（r19／r20 所加之「非空 registry」「L1 不重算」斷言於現行碼不成立，r21 撤回）。真實 kline 單週期輕量設定。"""
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    calls = []
    original = ColumnGroupRegistry.resume_from_manifest.__func__

    def spy(cls, work_dir):
        registry = original(cls, work_dir)
        calls.append(str(work_dir))
        return registry

    import pytest as _pytest

    mp = _pytest.MonkeyPatch()
    mp.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(spy))
    try:
        normal = fb.generate_cell("C5", tmp_path / "normal")
        normal_calls = list(calls)
        calls.clear()
        forced = fb.generate_cell("C5", tmp_path / "forced", force_regenerate_second=True)
        forced_calls = list(calls)
    finally:
        mp.undo()
    # 測試端獨立觀測：正常 C5 之第二次生成對本格 work dir 呼叫 resume；強制重算不呼叫。receipt 須與觀測一致
    assert any(str(tmp_path / "normal") in w for w in normal_calls), normal_calls
    assert not any(str(tmp_path / "forced") in w for w in forced_calls), forced_calls
    assert normal["receipt"]["resume_entered"] is True
    assert forced["receipt"]["resume_entered"] is False
    strip = lambda fp: {k: v for k, v in fp.items() if k != "path_receipt"}  # noqa: E731
    assert fb.compare_cell(strip(normal["fingerprint"]), strip(forced["fingerprint"])) == []


def test_boundary_14_c9_legacy_dir_observed_in_process(tmp_path):
    """C9 之 legacy 目錄以測試端獨立觀測（審查 r21–r24 CODEX P1-03 系列）：行程內 generate_cell("C9") 期間，每個
    KlineStorageManager 建構後之 legacy_cache_dir 皆為收據所報之受控空目錄（不靠子行程自報）。真實 kline 多週期短窗。"""
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    seen = []
    original_init = KlineStorageManager.__init__

    def init_spy(self, *a, **k):
        original_init(self, *a, **k)
        seen.append(Path(self.legacy_cache_dir).resolve())

    mp = pytest.MonkeyPatch()
    mp.setattr(KlineStorageManager, "__init__", init_spy)
    try:
        out = fb.generate_cell("C9", tmp_path)
    finally:
        mp.undo()
    legacy = Path(out["receipt"]["legacy_kline_dir"]).resolve()
    assert seen and all(p == legacy for p in seen), (seen, legacy)
    assert str(legacy).startswith(str(tmp_path.resolve())) and legacy.is_dir() and not any(legacy.iterdir())


def test_boundary_12_generation_metadata_exclusion_scalar_only():
    """非萬用之多段排除鍵 `generation_metadata.source_registry_manifest`（審查 r18 GROK-R18-P1-01）：純量排除、
    同層其他鍵保留；物件／陣列 ⇒ 拒跑。"""
    domain = fb.load_compare_domain()
    out = fb.filter_manifest({"generation_metadata": {"source_registry_manifest": "/abs/x", "other": 1}}, domain)
    assert out["generation_metadata"] == {"other": 1}
    for bad in ({"nested": 1}, ["/abs/x"]):
        with pytest.raises(fb.FramepathBaselineError):
            fb.filter_manifest({"generation_metadata": {"source_registry_manifest": bad, "other": 1}}, domain)


def test_boundary_10_wildcard_exclusion_scalar_only_and_not_across_arrays():
    """萬用鍵 `artifacts.*.metadata.source_registry_manifest`（審查 r17 CODEX-R17-P1-03）：多個 artifact 之純量值皆
    排除；任一指向物件／陣列 ⇒ 拒跑；`*` 不匹配陣列元素（陣列內同名鍵保留於比對域）。"""
    domain = fb.load_compare_domain()
    manifest = {"run_status": "complete",
                "artifacts": {"raw": {"metadata": {"source_registry_manifest": "/abs/a", "k": 1}},
                              "processed": {"metadata": {"source_registry_manifest": "/abs/b", "k": 2}}},
                "groups": [{"metadata": {"source_registry_manifest": "/abs/c"}}]}
    out = fb.filter_manifest(manifest, domain)
    assert "source_registry_manifest" not in out["artifacts"]["raw"]["metadata"]
    assert "source_registry_manifest" not in out["artifacts"]["processed"]["metadata"]
    assert out["artifacts"]["raw"]["metadata"]["k"] == 1
    assert out["groups"][0]["metadata"]["source_registry_manifest"] == "/abs/c"
    for bad in ({"nested": 1}, ["/abs/x"]):
        m = copy.deepcopy(manifest)
        m["artifacts"]["processed"]["metadata"]["source_registry_manifest"] = bad
        with pytest.raises(fb.FramepathBaselineError):
            fb.filter_manifest(m, domain)


def test_boundary_06_injected_readings_refused(monkeypatch, tmp_path):
    from momentum.FeatureEngineering import memory_guard

    monkeypatch.setenv(memory_guard.READINGS_ENV, str(tmp_path / "readings.jsonl"))
    with pytest.raises(fb.FramepathBaselineError):
        fb.run_cell("C1", tmp_path)


def test_boundary_15_memory_summary_comes_from_readings_sampler(monkeypatch, tmp_path):
    """審查 r26 CODEX-R26-P1-02：記憶體摘要須來自 `memory_guard._Readings` 對子行程之實際取樣——以 spy 置換該
    模組屬性跑 C1（真實 kline、單週期秒級）；全部格之同一核對另於 test_cell_matches_frozen_baseline 逐格執行
    （審查 r27 CODEX-R27-P1-01）。回傳固定健康常數之實作 ⇒ 紅。"""
    seen = _install_sampler_spy(monkeypatch)
    _assert_memory_from_sampler(fb.run_cell("C1", tmp_path)["memory"], seen)


def test_mutation_summarize_readings_derives_every_field():
    """summarize_readings 逐欄可證偽：峰值取最大 footprint、failed 聯集、injected 任一、非根成員、缺根計數。"""
    root = 100
    rows = [{"footprint": 5, "failed": [], "members": [{"pid": root}]},
            {"footprint": 9, "failed": [7], "members": [{"pid": root}, {"pid": 101}]},
            {"footprint": 3, "failed": [7, 2], "members": [{"pid": 101}], "injected": True}]
    got = fb.summarize_readings(rows, root)
    assert got == {"readings": 3, "peak_bytes": 9, "failed": [2, 7], "injected": True,
                   "non_root_member_seen": True, "root_missing": 1}
    only_root = fb.summarize_readings(rows[:1], root)
    assert only_root["non_root_member_seen"] is False and only_root["injected"] is False
    assert only_root["failed"] == [] and only_root["root_missing"] == 0
    assert fb.summarize_readings([], root)["readings"] == 0 and fb.summarize_readings([], root)["peak_bytes"] == 0
    # 審查 r27 CODEX-R27-P1-01：members 為空之讀數亦屬缺根
    assert fb.summarize_readings([{"footprint": 1, "failed": [], "members": []}], root)["root_missing"] == 1


def test_boundary_07_comparator_has_no_timeframe_or_symbol_literals():
    src = inspect.getsource(fb.compare_cell) + inspect.getsource(fb.filter_manifest)
    assert not re.search(r"""["']\d+[mhdwM]["']""", src)
    assert not re.search(r"USDT|BTC|ETH", src)


def _synthetic_pair():
    fp = {k: None for k in fb.FINGERPRINT_KEYS}
    fp.update({"column_names_sha256": "a", "column_count": 2, "row_count": 3, "time_index_sha256": "t",
               "columns": {"x": {"nan": "n1", "inf": "i1", "values": "v1"}, "y": {"nan": "n2", "inf": "i2", "values": "v2"}},
               "stationarity_decisions_sha256": "d", "manifest_sha256": "m", "run_status": "complete",
               "completeness": {}, "failure_reasons": [], "path_receipt": {"l3": "streaming"}})
    return fp, copy.deepcopy(fp)


def test_mutation_compare_detects_value_mask_and_manifest_changes():
    base, fresh = _synthetic_pair()
    assert fb.compare_cell(base, fresh) == []
    for mutate in (
        lambda f: f["columns"]["x"].__setitem__("values", "v1-float64"),        # M3 類：值位元
        lambda f: f["columns"].pop("y"),                                         # M2 類：欄消失
        lambda f: f.__setitem__("column_names_sha256", "a-untagged"),            # M1 類：欄名
        lambda f: f.__setitem__("manifest_sha256", "m-extra-key"),               # M4 類：manifest
        lambda f: f["columns"]["y"].__setitem__("nan", "n2x"),
    ):
        changed = copy.deepcopy(fresh)
        mutate(changed)
        assert fb.compare_cell(base, changed) != []


def test_mutation_result_frame_values_detected(tmp_path):
    """審查 r41 CODEX-R41-P1-01：回傳 features_df 之欄值（每格皆記）改變 ⇒ 差異；同值 ⇒ 相等。
    同一 index／feature_names／metadata，只改一欄之值、dtype 或 NaN 位置。"""
    from types import SimpleNamespace

    import numpy as np
    import pandas as pd

    settings = {"persist": True, "repeat": 1, "training_tfs": ["x"]}
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    meta = {"feature_names": ["x"], "feature_count": 1, "stationarity_decisions": {}}

    def fp(values, dtype="float32"):
        res = SimpleNamespace(features_df=pd.DataFrame({"x": np.asarray(values, dtype=dtype)}, index=idx), metadata=meta)
        return fb._fingerprint(settings, tmp_path / "absent", res)

    base = fp([1.0, 2.0, 3.0])
    assert fb.compare_cell(base, fp([1.0, 2.0, 3.0])) == []
    for changed in (fp([9.0, 8.0, 7.0]), fp([1.0, 2.0, 3.0], dtype="float64"), fp([1.0, np.nan, 3.0])):
        assert fb.compare_cell(base, changed) != []


def test_mutation_persist_false_registry_values_detected(tmp_path):
    """審查 r41 CODEX-R41-P1-01：CGSA persist=False 回傳空 features_df（實測 0 欄），產出在 registry 工作目錄之群組
    .npy ⇒ C7 指紋須逐欄涵蓋 registry 群組：改一格值、NaN 位置或 dtype ⇒ 差異；manifest 缺 ⇒ 具名拒跑。"""
    from types import SimpleNamespace

    import numpy as np
    import pandas as pd

    settings = {"persist": False, "repeat": 1, "training_tfs": ["x"]}
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")

    def fp(values, dtype="float32", name="g"):
        work = tmp_path / name
        work.mkdir()
        np.save(work / "g1.npy", np.asarray(values, dtype=dtype))
        (work / "manifest.json").write_text(json.dumps({"created_at": name, "groups": [
            {"group_id": "g1", "columns": ["a", "b"], "npy_path": "g1.npy", "shards": []}]}), encoding="utf-8")
        meta = {"feature_names": [], "feature_count": 2, "stationarity_decisions": {},
                "manifest_path": str(work / "manifest.json")}
        res = SimpleNamespace(features_df=pd.DataFrame(index=idx), metadata=meta)
        return fb._fingerprint(settings, tmp_path / "absent", res)

    rows = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
    base = fp(rows, name="base")
    assert set(base["columns"]) == {"g1/a", "g1/b"} and base["column_count"] == 2
    assert fb.compare_cell(base, fp(rows, name="same")) == []
    assert fb.compare_cell(base, fp([[1.0, 2.0], [3.0, 9.0], [5.0, 6.0]], name="value")) != []
    assert fb.compare_cell(base, fp([[1.0, 2.0], [np.nan, 4.0], [5.0, 6.0]], name="nan")) != []
    assert fb.compare_cell(base, fp(rows, dtype="float64", name="dtype")) != []
    with pytest.raises(fb.FramepathBaselineError):
        fb._fingerprint(settings, tmp_path / "absent", SimpleNamespace(
            features_df=pd.DataFrame(index=idx), metadata={"feature_count": 0, "manifest_path": str(tmp_path / "no")}))


@pytest.mark.parametrize("key", fb.FINGERPRINT_KEYS)
def test_mutation_compare_detects_missing_required_key(key):
    """任一必要比對項缺席（單側）⇒ 差異（審查 r19 CODEX-R19-P1-04：比較器不得只比共同鍵或以 .get 預設）。"""
    base, fresh = _synthetic_pair()
    fresh.pop(key)
    assert fb.compare_cell(base, fresh) != []
    base2, fresh2 = _synthetic_pair()
    base2.pop(key)
    assert fb.compare_cell(base2, fresh2) != []


def test_mutation_unregistered_manifest_key_changes_digest():
    domain = fb.load_compare_domain()
    manifest = {"run_status": "complete", "created_at": "2026-10-08T00:00:00", "updated_at": "x"}
    extra = dict(manifest, framepath_unregistered_key=1)
    assert fb.manifest_sha256(manifest, domain) != fb.manifest_sha256(extra, domain)
    later = dict(manifest, created_at="2027-01-01T00:00:00", updated_at="y")
    assert fb.manifest_sha256(manifest, domain) == fb.manifest_sha256(later, domain)
