"""ICFIRSTALIGN 乙 Task 4.1：校準域改走正式 CGSA 層產出、逐群組歸約（docs/ICFIRSTALIGN_SPEC.md v20）。

oracle：HEAD 凍結之 tests/_golden/icfirstalign/probe_baseline.json、calibration_baseline.json（甲＝HEAD 加兩處測試端替換；
乙＝HEAD 預設；所測設定甲＝乙，收據 handoffs/run_receipts/20261004-icfirstalign-freeze-baselines.json）。
新實作之介面（測試接縫）：`FeatureFactory._iter_calibration_domain_groups(symbol, tf, config, klines)` 逐群組產出
（欄名、float32 陣列、索引），`FeatureFactory._public_warmup_first_finite`（末輪各週期「標記欄名→首個有限值時間」）。
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
    from momentum.FeatureEngineering import memmap_utils

    contexts: List[str] = []
    real_combine = ff.FeatureFactory._combine_layers
    monkeypatch.setattr(ff.FeatureFactory, "_combine_layers",
                        staticmethod(lambda layers, context="unknown": (contexts.append(context), real_combine(layers, context=context))[1]))
    concat_calls = {"n": 0}
    real_concat = memmap_utils.concat_with_memmap

    def concat(*a: Any, **k: Any) -> Any:
        concat_calls["n"] += 1
        return real_concat(*a, **k)

    monkeypatch.setattr(memmap_utils, "concat_with_memmap", concat)
    monkeypatch.setattr(ff, "concat_with_memmap", concat, raising=False)
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert "calibration_domain" not in contexts
    assert concat_calls["n"] == 0


def _spy_group_reads(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    state: Dict[str, Any] = {"live_max": 0, "refs": [], "dtypes": set(), "ids": []}
    real = ColumnGroupRegistry.load_data

    def load(self: ColumnGroupRegistry, group_id: str) -> np.ndarray:
        arr = real(self, group_id)
        state["ids"].append(group_id)
        state["dtypes"].add(str(arr.dtype))
        state["refs"] = [r for r in state["refs"] if r() is not None]
        gc.collect()
        state["refs"] = [r for r in state["refs"] if r() is not None]
        holder = _Holder(arr)
        state["refs"].append(weakref.ref(holder))
        state["live_max"] = max(state["live_max"], len(state["refs"]))
        return holder.array

    monkeypatch.setattr(ColumnGroupRegistry, "load_data", load)
    return state


class _Holder:
    __slots__ = ("array", "__weakref__")

    def __init__(self, array: np.ndarray) -> None:
        self.array = array


def test_reduction_holds_at_most_one_group_and_float32(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _spy_group_reads(monkeypatch)
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert state["ids"], "校準域須逐群組自暫存 registry 讀回"
    assert state["live_max"] <= 1
    assert state["dtypes"] == {"float32"}


def test_calibration_l2_values_from_registry_category_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = _spy_group_reads(monkeypatch)
    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    calls = {"category": 0}
    real = DerivedOperatorEngine.compute_category
    monkeypatch.setattr(DerivedOperatorEngine, "compute_category",
                        lambda self, *a, **k: (calls.__setitem__("category", calls["category"] + 1), real(self, *a, **k))[1])
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups
    in_domain = {"category_during_domain": 0}

    def iter_groups(self: Any, *a: Any, **k: Any) -> Any:
        before = calls["category"]
        yield from real_iter(self, *a, **k)
        in_domain["category_during_domain"] += calls["category"] - before

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", iter_groups)
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert any("_L2_" in gid for gid in state["ids"])
    assert in_domain["category_during_domain"] > 0


# ---------------------------------------------------------------- 邊界

def test_boundary_01_empty_layer_yields_no_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.1 邊界①：某層為空（L3 關）⇒ 無該層群組、探測照常完成。"""
    state = _spy_group_reads(monkeypatch)
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
    """Task 4.1 邊界④：暫存 registry 落盤前之累計磁碟預檢不足 ⇒ 具名錯誤（沿用 registry 既有預檢）。"""
    from momentum.FeatureEngineering.core import column_group_registry as cgr

    def insufficient(self: Any, *a: Any, **k: Any) -> None:
        raise cgr.CGSAPersistenceError("disk insufficient", cgr.FailureType.DISK_FULL) \
            if hasattr(cgr, "FailureType") else RuntimeError("disk insufficient")

    monkeypatch.setattr(ColumnGroupRegistry, "_precheck_cgsa_cumulative_disk", insufficient)
    with pytest.raises(Exception) as info:
        _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert "disk" in str(info.value).lower()


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
    """mutant：歸約前把全部群組累積成一表 ⇒ 同時存活群組數 > 1。"""
    state = _spy_group_reads(monkeypatch)
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def accumulate(self: Any, *a: Any, **k: Any) -> Any:
        groups = list(real_iter(self, *a, **k))
        yield from groups

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", accumulate)
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert state["live_max"] > 1


def test_mutation_group_cast_float64_before_winsor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：群組讀回後先轉 float64 ⇒ dtype 斷言翻轉。"""
    real = ColumnGroupRegistry.load_data
    monkeypatch.setattr(ColumnGroupRegistry, "load_data", lambda self, gid: real(self, gid).astype(np.float64))
    state = _spy_group_reads(monkeypatch)
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert "float64" in state["dtypes"]


def test_mutation_l2_from_returned_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：校準域 L2 改取回傳表（不讀 registry L2 群組）⇒ 讀回之群組 ID 不含 L2。"""
    state = _spy_group_reads(monkeypatch)
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def without_l2(self: Any, *a: Any, **k: Any) -> Any:
        for item in real_iter(self, *a, **k):
            if "_L2_" not in str(item[0]):
                yield item

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", without_l2)
    monkeypatch.setattr(ColumnGroupRegistry, "load_data",
                        lambda self, gid, _real=ColumnGroupRegistry.load_data: _real(self, gid))
    _generate(tmp_path, monkeypatch, frz.p1_payload(), frz.P1_WINDOW)
    assert not any("_L2_" in gid for gid in state["ids"] if state["ids"])


def test_mutation_missing_group_changes_column_set_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：漏一個群組 ⇒ S3 封包 column_set_digest 與 HEAD 甲不等。"""
    real_iter = ff.FeatureFactory._iter_calibration_domain_groups

    def drop_first(self: Any, *a: Any, **k: Any) -> Any:
        items = real_iter(self, *a, **k)
        next(items, None)
        yield from items

    monkeypatch.setattr(ff.FeatureFactory, "_iter_calibration_domain_groups", drop_first)
    got = _packets(tmp_path, monkeypatch, True)
    assert got["12h"]["column_set_digest"] != CALIB["jia"]["S3_winsor_on"]["12h"]["column_set_digest"]
