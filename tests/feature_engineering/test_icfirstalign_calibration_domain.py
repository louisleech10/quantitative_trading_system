"""ICFIRSTALIGN 乙 Task 4.1：校準域改走正式 CGSA 層產出、逐群組歸約（docs/ICFIRSTALIGN_SPEC.md v22）。

oracle：HEAD 凍結之 tests/_golden/icfirstalign/probe_baseline.json、calibration_baseline.json（甲＝HEAD 加兩處測試端替換；
乙＝HEAD 預設；所測設定甲＝乙，收據 handoffs/run_receipts/20261004-icfirstalign-freeze-baselines.json）。
新實作之介面（測試接縫）：`FeatureFactory._iter_calibration_domain_groups(symbol, tf, config, klines)` 逐群組產出
（群組 ID、欄名、float32 陣列＝registry 讀回陣列本身或其 view、索引），消費端以零複製建 frame 交
`FeaturePreprocessor._apply_winsorization`；`FeatureFactory._public_warmup_first_finite`（末輪各週期「標記欄名→首個有限值時間」）。
實作前應為紅：上述接縫不存在、校準域仍經 `_combine_layers(context="calibration_domain")`。
"""

from __future__ import annotations

import gc
import hashlib
import json
import weakref
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

import scripts.freeze_icfirstalign_baseline as frz
from momentum.FeatureEngineering import feature_factory as ff
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.preprocessing import calibration as cal
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(1200)

PROBE = json.loads((h.REPO / "tests/_golden/icfirstalign/probe_baseline.json").read_text(encoding="utf-8"))
CALIB = json.loads((h.REPO / "tests/_golden/icfirstalign/calibration_baseline.json").read_text(encoding="utf-8"))
SETTINGS = {"P1": (frz.p1_payload, frz.P1_WINDOW), "P2": (frz.p2_payload, h.S2_WINDOW)}


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _generate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: Dict[str, Any], window: Any) -> Any:
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    factory.generate_features(h.SYMBOL, h.PRIMARY, config_override=payload, force_regenerate=True,
                              start_date=window[0], end_date=window[1], persist=True)
    return factory


def _probe_record(factory: Any) -> Dict[str, Any]:
    late = getattr(factory, "_public_warmup_late", None)
    final = factory._public_warmup_first_finite
    return {
        "rounds": list(factory._public_warmup_probe),
        "window": {k: str(getattr(factory._current_output_window, k, None))
                   for k in ("output_start", "output_end", "ingest_start", "max_warmup_bars", "warmup_enabled")},
        "late_names_sha256": _sha(sorted(late[1])) if late else None,
        "final_first_finite": {tf: _sha(sorted(m.items())) for tf, m in final.items()},
    }


def _golden_final(mode: str, name: str) -> Dict[str, str]:
    """golden 之末輪各週期首個有限值 sha（domain_calls 依呼叫序；末輪＝每週期最後一次）。"""
    out: Dict[str, str] = {}
    for call in PROBE[mode][name]["domain_calls"]:
        out[call["timeframe"]] = call["first_finite_sha256"]
    return out


# ---------------------------------------------------------------- §G oracle

@pytest.mark.parametrize("name", sorted(SETTINGS))
def test_probe_bytes_equal_head_jia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    payload_fn, window = SETTINGS[name]
    factory = _generate(tmp_path, monkeypatch, payload_fn(), window)
    got = _probe_record(factory)
    gold = PROBE["jia"][name]
    assert got["rounds"] == gold["rounds"]
    assert got["window"] == gold["window"]
    assert got["late_names_sha256"] == gold["late_names_sha256"]
    assert got["final_first_finite"] == _golden_final("jia", name)


@pytest.mark.parametrize("name", sorted(SETTINGS))
def test_probe_first_finite_and_late_equal_head_yi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    """對乙之首個有限值時間或晚到集合有任何差異 ⇒ 停下回報（本斷言即停止條件）。"""
    payload_fn, window = SETTINGS[name]
    got = _probe_record(_generate(tmp_path, monkeypatch, payload_fn(), window))
    assert got["late_names_sha256"] == PROBE["yi"][name]["late_names_sha256"]
    assert got["final_first_finite"] == _golden_final("yi", name)


def _packets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winsor: bool) -> Dict[str, Any]:
    captured: Dict[str, Any] = {}
    real = ff.FeatureFactory.run_calibration_preflight

    def preflight(self: Any, *a: Any, **k: Any) -> Any:
        out = real(self, *a, **k)
        captured.update(out.get("packets", {}))
        return out

    monkeypatch.setattr(ff.FeatureFactory, "run_calibration_preflight", preflight)
    _generate(tmp_path, monkeypatch, frz.s3_payload(winsor), h.S2_WINDOW)
    return {tf: frz._packet_record(p) for tf, p in captured.items()}


@pytest.mark.parametrize("winsor", [True, False], ids=["winsor_on", "winsor_off"])
def test_calibration_packets_bytes_equal_head_jia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winsor: bool) -> None:
    got = _packets(tmp_path, monkeypatch, winsor)
    assert got == CALIB["jia"][f"S3_winsor_{'on' if winsor else 'off'}"]


# ---------------------------------------------------------------- 結構

def test_calibration_domain_never_merges_full_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """spy：`_combine_layers(context="calibration_domain")` 0 次、`concat_with_memmap` 於校準域 0 次。

    b3 實作期：校準域以正式單週期生成之同一組層函式產出，L3／L4 之層輸入合併（`layer3_input`／`layer4_input`，
    正式生成同用、只含 raw＋L1）經 `_combine_layers` 內之 `concat_with_memmap`——非全欄合併；故「於校準域」之計數
    限校準域期間（`_iter_calibration_domain_groups` 消費區間）**不經 `_combine_layers`** 之直接呼叫，且校準域期間之
    `_combine_layers` 情境只得為層輸入合併（全欄合併之情境或直接呼叫任一出現即紅）。"""
    from momentum.FeatureEngineering import memmap_utils

    st: Dict[str, Any] = {"active": 0, "combine_depth": 0, "contexts": [], "domain_contexts": [], "direct": 0,
                          "domain_calls": 0}
    real_combine = ff.FeatureFactory._combine_layers

    def combine(layers: Any, context: str = "unknown") -> Any:
        st["contexts"].append(context)
        if st["active"]:
            st["domain_contexts"].append(context)
        st["combine_depth"] += 1
        try:
            return real_combine(layers, context=context)
        finally:
            st["combine_depth"] -= 1

    monkeypatch.setattr(ff.FeatureFactory, "_combine_layers", staticmethod(combine))
    real_concat = memmap_utils.concat_with_memmap

    def concat(*a: Any, **k: Any) -> Any:
        if st["active"] and st["combine_depth"] == 0:
            st["direct"] += 1
        return real_concat(*a, **k)

    monkeypatch.setattr(memmap_utils, "concat_with_memmap", concat)
    monkeypatch.setattr(ff, "concat_with_memmap", concat, raising=False)
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def iter_groups(self: Any, *a: Any, **k: Any) -> Any:
        st["active"] += 1
        st["domain_calls"] += 1
        try:
            yield from real_iter(self, *a, **k)
        finally:
            st["active"] -= 1

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", iter_groups)
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert st["domain_calls"] > 0
    assert "calibration_domain" not in st["contexts"]
    assert st["direct"] == 0
    assert set(st["domain_contexts"]) <= {"layer3_input", "layer4_input"}


def _spy_calibration(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Task 4.1 驗證 (a)–(d) 之觀測接縫（不依值差；所測設定兩臂值相等）。

    (a) 存活：對 `load_data` 實際回傳之陣列直接建 weakref（不經中介物件），只計校準歸約期之讀回；
        計數點＝縮尾輸入端（消費端已把迴圈變數換成當前群組，前一群組應已無參照）。
    (b) dtype：縮尾輸入 frame 之 dtype（讀回 dtype 另記，作落盤格式檢查）。
    (c) L2 寫入來源：`_persist_layer2_category_group` 收到之 frame 須為當次 `compute_category` 回傳物件
        （同一物件或逐欄共用記憶體）。
    (d) L2 消費來源：縮尾輸入 frame 須與某個仍存活之校準期 registry 讀回陣列共用記憶體（零複製交接）。
    """
    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    st: Dict[str, Any] = {"active": 0, "reads": [], "ids": [], "read_dtypes": set(), "live_max": 0,
                          "winsor_calls": 0, "winsor_dtypes": set(), "unmatched": 0, "matched_ids": [],
                          "category_out": {}, "category_calls": 0, "category_during_domain": 0,
                          "l2_writes_active": 0, "l2_write_violations": 0}
    real_load = ColumnGroupRegistry.load_data

    def load(self: ColumnGroupRegistry, group_id: str) -> np.ndarray:
        arr = real_load(self, group_id)
        st["ids"].append(group_id)
        st["read_dtypes"].add(str(arr.dtype))
        if st["active"]:
            st["reads"].append((group_id, weakref.ref(arr)))
        return arr

    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def iter_groups(self: Any, *a: Any, **k: Any) -> Any:
        st["active"] += 1
        before = st["category_calls"]
        try:
            yield from real_iter(self, *a, **k)
        finally:
            st["active"] -= 1
            st["category_during_domain"] += st["category_calls"] - before

    real_winsor = FeaturePreprocessor._apply_winsorization

    def winsor(self: FeaturePreprocessor, df: Any) -> Any:
        if st["active"]:
            gc.collect()
            live = [(gid, r()) for gid, r in st["reads"]]
            live = [(gid, arr) for gid, arr in live if arr is not None]
            st["live_max"] = max(st["live_max"], len(live))
            st["winsor_calls"] += 1
            st["winsor_dtypes"].update(str(t) for t in df.dtypes.unique())
            values = df.to_numpy()
            hit = [gid for gid, arr in live if np.shares_memory(values, arr)]
            if hit:
                st["matched_ids"].extend(hit)
            else:
                st["unmatched"] += 1
            del live, values
        return real_winsor(self, df)

    real_category = DerivedOperatorEngine.compute_category

    def category(self: Any, layer1_df: Any, raw_data: Any, indicator_specs: Any, category: str) -> Any:
        out = real_category(self, layer1_df, raw_data, indicator_specs, category)
        st["category_calls"] += 1
        st["category_out"][category] = weakref.ref(out) if out is not None else None
        return out

    real_persist = ff.FeatureFactory._persist_layer2_category_group

    def persist(self: Any, category: str, frame: Any) -> None:
        ref = st["category_out"].get(category)
        src = ref() if ref is not None else None
        same = src is not None and (frame is src or all(
            np.shares_memory(frame[c].to_numpy(), src[c].to_numpy()) for c in frame.columns if c in src.columns
        ) and set(frame.columns) <= set(src.columns))
        if not same:
            st["l2_write_violations"] += 1
        if st["active"]:
            st["l2_writes_active"] += 1
        del src
        return real_persist(self, category, frame)

    monkeypatch.setattr(ColumnGroupRegistry, "load_data", load)
    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", iter_groups)
    monkeypatch.setattr(FeaturePreprocessor, "_apply_winsorization", winsor)
    monkeypatch.setattr(DerivedOperatorEngine, "compute_category", category)
    monkeypatch.setattr(ff.FeatureFactory, "_persist_layer2_category_group", persist)
    return st


def _capture_returned_l2(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """mutant 用：記錄最近一次 `compute_all_polars` 回傳表（L2 回傳表臂）。"""
    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    last: Dict[str, Any] = {}
    real_all = DerivedOperatorEngine.compute_all_polars

    def compute_all(self: Any, *a: Any, **k: Any) -> Any:
        last["ret"] = real_all(self, *a, **k)
        return last["ret"]

    monkeypatch.setattr(DerivedOperatorEngine, "compute_all_polars", compute_all)
    return last


def test_reduction_holds_at_most_one_group_and_float32(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(a)(b)：縮尾輸入端同時存活之校準期讀回陣列恰 1、縮尾輸入 dtype 恆 float32。"""
    st = _spy_calibration(monkeypatch)
    _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    assert st["ids"], "校準域須逐群組自暫存 registry 讀回"
    assert st["winsor_calls"] > 0
    assert st["live_max"] == 1
    assert st["read_dtypes"] == {"float32"}
    assert st["winsor_dtypes"] == {"float32"}


def test_calibration_l2_values_from_registry_category_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(c)(d)：L2 群組由 `compute_category` 回傳物件寫入；縮尾輸入零複製來自 registry 讀回（含 L2 群組）。"""
    st = _spy_calibration(monkeypatch)
    _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    assert st["category_during_domain"] > 0
    assert st["l2_writes_active"] > 0 and st["l2_write_violations"] == 0
    assert st["winsor_calls"] > 0 and st["unmatched"] == 0
    assert any("_L2_" in gid for gid in st["matched_ids"])


# ---------------------------------------------------------------- 邊界

def test_boundary_01_empty_layer_yields_no_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界①：某層為空（L3 關）⇒ 無該層群組、探測照常完成。"""
    state = _spy_calibration(monkeypatch)
    payload = frz.p1_payload()
    payload["rolling_aggregation"] = {"enabled": False}
    factory = _generate(tmp_path, monkeypatch, payload, frz.P1_WINDOW)
    assert not any("_L3_" in gid for gid in state["ids"])
    assert factory._public_warmup_probe


def test_boundary_02_no_finite_in_probe_counts_as_late(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界②：探測段無有限值之欄 ⇒ 計入晚到集合（P2 之晚到集合與 HEAD 相同即涵蓋）。"""
    got = _probe_record(_generate(tmp_path, monkeypatch, frz.p2_payload(), h.S2_WINDOW))
    final = _generate(tmp_path / "again", monkeypatch, frz.p2_payload(), h.S2_WINDOW)._public_warmup_first_finite
    no_finite = {c for m in final.values() for c, ts in m.items() if ts is None}
    assert no_finite and got["late_names_sha256"] == PROBE["jia"]["P2"]["late_names_sha256"]


def test_boundary_03_row_count_mismatch_raises_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界③：校準域列數與前史切片不符 ⇒ 既有具名錯誤（CalibrationError）。"""
    real = ColumnGroupRegistry.load_data
    monkeypatch.setattr(ColumnGroupRegistry, "load_data", lambda self, gid: real(self, gid)[1:])
    with pytest.raises(cal.CalibrationError):
        _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)


def test_boundary_04_disk_precheck_insufficient_raises_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界④：暫存 registry 落盤前之累計磁碟預檢不足 ⇒ 具名錯誤（沿用 registry 既有預檢）。

    r23：不替換預檢本身；只令校準暫存目錄（前綴 `CALIBRATION_TMP_PREFIX`）之可用空間為 0，
    由既有 `_precheck_cgsa_cumulative_disk` 拋 `ColumnGroupRegistryError(IO_ERROR)`；暫存目錄於例外後仍刪除。
    """
    import tempfile

    from momentum.FeatureEngineering.core import column_group_registry as cgr

    monkeypatch.setenv("FFACT_CGSA_DISK_PRECHECK", "1")
    tmp_root = tmp_path / "sys_tmp"
    tmp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_root))
    real_free = ColumnGroupRegistry._disk_free_bytes
    hits: Dict[str, Any] = {"calibration": 0, "paths": set()}

    def free(path: Path) -> Any:
        if cal.CALIBRATION_TMP_PREFIX in str(path):
            hits["calibration"] += 1
            hits["paths"].add(Path(path))
            return 0
        return real_free(path)

    monkeypatch.setattr(ColumnGroupRegistry, "_disk_free_bytes", staticmethod(free))
    with pytest.raises(cgr.ColumnGroupRegistryError) as info:
        _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert info.value.failure_type == cgr.FailureType.IO_ERROR
    assert "Insufficient disk space" in str(info.value)
    assert hits["calibration"] > 0
    assert not [p for p in tmp_root.iterdir() if p.name.startswith(cal.CALIBRATION_TMP_PREFIX)]
    # r24：暫存目錄可能落於映射根而非 TMPDIR——以預檢實際看到之路徑核其校準暫存根已刪
    roots = {next((a for a in [p, *p.parents] if a.name.startswith(cal.CALIBRATION_TMP_PREFIX)), p) for p in hits["paths"]}
    assert roots and not [r for r in roots if r.exists()]
    assert hasattr(ff.FeatureFactory, "_iter_calibration_domain_groups")


def test_boundary_05_history_shorter_than_n_keeps_empty_columns_semantics(tmp_path: Path,
                                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界⑤：前史不足 N ⇒ 既有 empty_columns 語意（不足之欄不帶校準值、列入 empty_columns）。"""
    payload = frz.s3_payload(True)
    payload["preprocessing"] = {**payload["preprocessing"], "calibration_bars": 5000,
                                "calibration_bars_by_timeframe": {"12h": 5000}}
    captured: Dict[str, Any] = {}
    real = ff.FeatureFactory.run_calibration_preflight
    monkeypatch.setattr(ff.FeatureFactory, "run_calibration_preflight",
                        lambda self, *a, **k: (lambda out: (captured.update(out.get("packets", {})), out)[1])(real(self, *a, **k)))
    _generate(tmp_path, monkeypatch, payload, h.S2_WINDOW)
    rec = frz._packet_record(captured["12h"])
    assert rec["empty_columns"] and not (set(rec["empty_columns"]) & set(rec["values"]))
    assert hasattr(ff.FeatureFactory, "_iter_calibration_domain_groups")


# ---------------------------------------------------------------- mutants

def test_mutation_winsor_skipped_changes_first_finite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：歸約時縮尾漏套 ⇒ 首個有限值對照與 HEAD 甲不等。"""
    monkeypatch.setattr(FeaturePreprocessor, "_apply_winsorization", lambda self, frame: frame)
    got = _probe_record(_generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW))
    assert got["final_first_finite"] != _golden_final("jia", "P1")


def test_mutation_reduction_accumulates_all_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant (a)：歸約前把全部群組累積成一表（讀回陣列全數持有）⇒ 縮尾輸入端存活數 > 1。

    安裝順序：mutant 先裝於原 iterator、spy 後裝於最外層，使 spy 之歸約期涵蓋累積後之整段消費
    （r21：反序時 `list()` 先耗盡 spy 包裝器、歸約期提前結束而觀測全停）。
    """
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def accumulate(self: Any, *a: Any, **k: Any) -> Any:
        groups = list(real_iter(self, *a, **k))
        yield from groups

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", accumulate)
    st = _spy_calibration(monkeypatch)
    _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    assert st["winsor_calls"] > 0
    assert st["live_max"] > 1


def test_mutation_group_cast_float64_before_winsor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant (b)：群組讀回、交出後先轉 float64 再縮尾（reader 本身不變）⇒ 縮尾輸入 dtype 斷言翻轉。"""
    st = _spy_calibration(monkeypatch)
    spied_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def cast(self: Any, *a: Any, **k: Any) -> Any:
        for gid, names, arr, idx in spied_iter(self, *a, **k):
            yield gid, names, arr.astype(np.float64), idx

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", cast)
    _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    assert st["read_dtypes"] == {"float32"}
    assert "float64" in st["winsor_dtypes"]


def test_mutation_l2_written_from_returned_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant (c)：仍呼叫 `compute_category`，但以 `compute_all_polars` 回傳表之該類別欄寫入 L2 群組 ⇒ 寫入來源斷言紅。"""
    st = _spy_calibration(monkeypatch)
    last = _capture_returned_l2(monkeypatch)
    spied_persist = ff.FeatureFactory._persist_layer2_category_group
    monkeypatch.setattr(ff.FeatureFactory, "_persist_layer2_category_group",
                        lambda self, category, frame: spied_persist(self, category,
                                                                    last["ret"].reindex(columns=frame.columns)))
    _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    assert st["category_during_domain"] > 0
    assert st["l2_write_violations"] > 0


def test_mutation_l2_handed_from_returned_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant (d)：保留 `compute_category` 與 registry L2 讀回，但交出回傳表值（值相等）⇒ 消費來源斷言紅。"""
    st = _spy_calibration(monkeypatch)
    last = _capture_returned_l2(monkeypatch)
    spied_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def swap(self: Any, *a: Any, **k: Any) -> Any:
        for gid, names, arr, idx in spied_iter(self, *a, **k):
            if "_L2_" in str(gid):
                arr = last["ret"].reindex(index=idx, columns=names).to_numpy(np.float32)
            yield gid, names, arr, idx

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", swap)
    _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    assert any("_L2_" in gid for gid in st["ids"])
    assert st["unmatched"] > 0


def test_mutation_missing_group_changes_column_set_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：漏一個群組 ⇒ S3 封包 column_set_digest 與 HEAD 甲不等。"""
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def drop_first(self: Any, *a: Any, **k: Any) -> Any:
        items = real_iter(self, *a, **k)
        next(items, None)
        yield from items

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", drop_first)
    # b3 實作期：漏群組之封包於 L6.5 取子封包時被既有 fail-closed（公開域之欄在校準域缺欄）擋下 ⇒ 生成具名失敗；
    # 封包本身（前置關卡已交出）之 column_set_digest 亦與 HEAD 甲不等——兩者皆斷言
    captured: Dict[str, Any] = {}
    real = ff.FeatureFactory.run_calibration_preflight

    def preflight(self: Any, *a: Any, **k: Any) -> Any:
        out = real(self, *a, **k)
        captured.update(out.get("packets", {}))
        return out

    monkeypatch.setattr(ff.FeatureFactory, "run_calibration_preflight", preflight)
    with pytest.raises(cal.CalibrationError, match="缺欄"):
        _generate(tmp_path, monkeypatch, frz.s3_payload(True), h.S2_WINDOW)
    got = frz._packet_record(captured["12h"])
    assert got["column_set_digest"] != CALIB["jia"]["S3_winsor_on"]["12h"]["column_set_digest"]
