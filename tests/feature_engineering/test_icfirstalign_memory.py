"""ICFIRSTALIGN 乙 Task 4.2／4.3：生成記憶體預算（docs/ICFIRSTALIGN_SPEC.md v19）。

預算量＝致 OOM 之量（macOS `ri_phys_footprint`）；`check` 三條件：本程式 footprint＋planned ≤ 上限、核心壓力非危急、
planned ≤ 系統可吸收量（free＋file-backed＋現有換頁剩餘）；分支 ID 於實際分派點宣告；選擇子正規化唯一入口；
獨立守護行程；強制停止後之恢復。真實 kline（精簡 L1）、注入接縫（`sampler_override`、`budget_override`、
`vm_snapshot_override`、`check_recorder`）。實作前應為紅：`memory_budget` 為空殼、producer 未接 `check`。
"""

from __future__ import annotations

import ast
import itertools
import json
import os
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering import memory_budget as mb
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(1800)

C = h.CONTRACT
B = C["budget"]
MSG = C["budget_messages"]
GiB = 1 << 30
MiB = 1 << 20
PRODUCER_MODULES = [
    "momentum/FeatureEngineering/feature_factory.py",
    "momentum/FeatureEngineering/operators/rolling_aggregator.py",
    "momentum/FeatureEngineering/operators/derived_operators.py",
    "momentum/FeatureEngineering/utils/hardware_utils.py",
    "momentum/FeatureEngineering/polars_adapter.py",
    "momentum/FeatureEngineering/timeframe/multi_tf_generator.py",  # v23：多週期子行程之分派
]
GUARD = h.REPO / C["guard_script"]


def _snapshot(**over: int) -> mb.VMSnapshot:
    base = dict(free_bytes=8 * GiB, file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                swap_volume_free_bytes=75 * GiB, swap_volume_capacity_bytes=228 * GiB)
    base.update(over)
    return mb.VMSnapshot(**base)


def _anon(nbytes: int, name: str = "read") -> List[mb.Component]:
    return [mb.Component(name=name, kind="anon", nbytes=int(nbytes))]


def _ctx(stack: ExitStack, *, resident: int = 100 * MiB, footprint: int = 100 * MiB, budget: int = 6 * GiB,
         snapshot: mb.VMSnapshot = None) -> None:
    stack.enter_context(mb.sampler_override(lambda: {"resident": resident, "phys_footprint": footprint}))
    stack.enter_context(mb.budget_override(budget))
    stack.enter_context(mb.vm_snapshot_override(snapshot or _snapshot()))


# ---------------------------------------------------------------- 預算量

def test_real_sample_is_positive_integer() -> None:
    value = mb.sample_memory_bytes()
    assert isinstance(value, int) and value > 0


def test_footprint_is_the_budget_metric() -> None:
    """（resident, footprint）＝（低, 高）使 resident＋planned ≤ 上限 < footprint＋planned ⇒ 拋具名錯誤。"""
    with ExitStack() as stack:
        _ctx(stack, resident=100 * MiB, footprint=5 * GiB, budget=6 * GiB)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            mb.check("IC.selected_read", _anon(int(1.5 * GiB)))
    assert info.value.reason == MSG["own_cap"]


def test_mutation_metric_resident(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：預算量改取 resident ⇒ 上案例不拋。"""
    monkeypatch.setattr(mb, "sample_memory_bytes", lambda: mb._read_rusage()["resident"])
    with ExitStack() as stack:
        _ctx(stack, resident=100 * MiB, footprint=5 * GiB, budget=6 * GiB)
        mb.check("IC.selected_read", _anon(int(1.5 * GiB)))


def _touched_memmap(tmp_path: Path, nbytes: int) -> np.memmap:
    arr = np.memmap(tmp_path / "touched.bin", dtype=np.uint8, mode="w+", shape=(nbytes,))
    arr[::4096] = 1
    return arr


def test_real_file_mapping_not_counted(tmp_path: Path) -> None:
    """真實檔案映射：觸頁一個大於（上限 − 當下 footprint）之 np.memmap、匿名配置不變 ⇒ 不拋。"""
    now = mb.sample_memory_bytes()
    with mb.budget_override(now + 64 * MiB), mb.vm_snapshot_override(_snapshot()):
        arr = _touched_memmap(tmp_path, 256 * MiB)
        try:
            mb.check("IC.selected_read", _anon(MiB))
        finally:
            del arr


def test_mutation_metric_max_resident_footprint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：預算量改取 max(resident, footprint) ⇒ 上案例誤拋。"""
    monkeypatch.setattr(mb, "sample_memory_bytes",
                        lambda: max(mb._read_rusage()["resident"], mb._read_rusage()["phys_footprint"]))
    now = mb.sample_memory_bytes()
    with mb.budget_override(now + 64 * MiB), mb.vm_snapshot_override(_snapshot()):
        arr = _touched_memmap(tmp_path, 256 * MiB)
        try:
            with pytest.raises(mb.GenerationMemoryBudgetExceeded):
                mb.check("IC.selected_read", _anon(MiB))
        finally:
            del arr


# ---------------------------------------------------------------- 系統條件

def test_system_insufficient_raises_named() -> None:
    snap = _snapshot(free_bytes=GiB // 2, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=75 * GiB)
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            mb.check("IC.selected_read", _anon(int(1.5 * GiB)))
    assert info.value.reason == MSG["system_insufficient"]


def test_system_sufficient_passes() -> None:
    snap = _snapshot(free_bytes=GiB // 2, file_backed_bytes=0, swap_free_bytes=0)
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap)
        mb.check("IC.selected_read", _anon(GiB // 4))


def test_absorbable_is_free_file_backed_swap_free() -> None:
    snap = _snapshot(free_bytes=3, file_backed_bytes=5, swap_free_bytes=7, swap_volume_free_bytes=1000)
    assert mb.system_absorbable_bytes(snap) == 15


@pytest.mark.parametrize("mutant", ["anon_included", "swap_volume_included"])
def test_mutation_absorbable_definition(monkeypatch: pytest.MonkeyPatch, mutant: str) -> None:
    """mutant：可吸收量改含匿名頁、或加入換頁卷剩餘空間 ⇒ 系統不足案例放行。"""
    extra = {"anon_included": lambda s: 10 * GiB, "swap_volume_included": lambda s: s.swap_volume_free_bytes}[mutant]
    monkeypatch.setattr(mb, "system_absorbable_bytes",
                        lambda s: s.free_bytes + s.file_backed_bytes + s.swap_free_bytes + extra(s))
    snap = _snapshot(free_bytes=GiB // 2, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=75 * GiB)
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap)
        mb.check("IC.selected_read", _anon(int(1.5 * GiB)))


@pytest.mark.parametrize("level,raises", [(B["pressure_critical_level"], True), (B["pressure_warn_level"], False)])
def test_pressure_level_condition(level: int, raises: bool) -> None:
    with ExitStack() as stack:
        _ctx(stack, snapshot=_snapshot(pressure_level=level))
        if raises:
            with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
                mb.check("IC.selected_read", _anon(MiB))
            assert info.value.reason == MSG["pressure_critical"]
        else:
            mb.check("IC.selected_read", _anon(MiB))


def test_mutation_pressure_condition_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mb, "_pressure_ok", lambda snapshot: True)
    with ExitStack() as stack:
        _ctx(stack, snapshot=_snapshot(pressure_level=B["pressure_critical_level"]))
        mb.check("IC.selected_read", _anon(MiB))


@pytest.mark.parametrize("capacity_gb,expected_gb", [(50, 4.0), (100, 5.0), (228, 11.4), (2000, 100.0)])
def test_disk_reserve_bytes(capacity_gb: int, expected_gb: float) -> None:
    assert mb.disk_reserve_bytes(int(capacity_gb * 1e9)) == max(B["disk_reserve_min_bytes"], int(capacity_gb * 1e9 * B["disk_reserve_fraction"]))
    assert abs(mb.disk_reserve_bytes(int(capacity_gb * 1e9)) / 1e9 - max(4 * GiB / 1e9, expected_gb)) < 0.01


@pytest.mark.parametrize("physical_gb", [8, 32, 64])
def test_budget_ratio_default_and_absolute_override(physical_gb: int) -> None:
    physical = physical_gb * GiB
    assert mb.budget_bytes(physical) == int(physical * B["ratio_default"])
    assert mb.budget_bytes(physical, absolute_bytes=123 * MiB) == 123 * MiB


def test_boundary_01_planned_zero_still_checks_current() -> None:
    """Task 4.2 邊界①：planned_bytes 為 0 ⇒ 仍判現值。"""
    with ExitStack() as stack:
        _ctx(stack, footprint=7 * GiB, budget=6 * GiB)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            mb.check("IC.selected_read", _anon(0))


def test_boundary_02_budget_from_config_not_hardcoded() -> None:
    """Task 4.2 邊界②：上限由實體記憶體比例／設定讀，不寫死機器大小。"""
    assert mb.budget_bytes(8 * GiB) != mb.budget_bytes(32 * GiB)


def test_boundary_03_temp_registry_removed_when_budget_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.2 邊界③：校準域超預算拋出時，已落盤之暫存 registry 於例外路徑刪除。"""
    from momentum.FeatureEngineering.preprocessing.calibration import CALIBRATION_TMP_PREFIX

    root = h.isolated(monkeypatch, tmp_path)
    calls = {"n": 0}
    real_check = mb.check

    def fail_late(branch_id: str, components: Any, **kw: Any) -> None:
        calls["n"] += 1
        if calls["n"] > 3:  # 讓暫存 registry 先落盤若干群組，再超預算
            raise mb.GenerationMemoryBudgetExceeded(branch_id, 0, 0, 0, MSG["own_cap"])
        return real_check(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", fail_late)
    with pytest.raises(mb.GenerationMemoryBudgetExceeded):
        h.generate_s2(root)
    leftovers = [p for p in tmp_path.rglob(f"{CALIBRATION_TMP_PREFIX}*")]
    assert leftovers == []


# ---------------------------------------------------------------- 平台

@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_unsupported_platform_raises_named(monkeypatch: pytest.MonkeyPatch, platform: str) -> None:
    monkeypatch.setattr(sys, "platform", platform)
    with pytest.raises(mb.MemoryMeasurementUnavailable):
        mb.sample_memory_bytes()


def test_linux_generation_refused_before_first_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "platform", "linux")
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    layer_calls = {"n": 0}
    real = FeatureFactory._layer1_atomic_indicators
    monkeypatch.setattr(FeatureFactory, "_layer1_atomic_indicators",
                        lambda self, *a, **k: (layer_calls.__setitem__("n", layer_calls["n"] + 1), real(self, *a, **k))[1])
    with pytest.raises(mb.MemoryMeasurementUnavailable):
        h.generate_s2(root)
    assert layer_calls["n"] == 0


def test_mutation_linux_reads_smaps(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：linux 改讀 smaps_rollup 之 Anonymous＋Swap 放行 ⇒ 不再拋 MemoryMeasurementUnavailable。"""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(mb, "sample_memory_bytes", lambda: 123 * MiB)
    assert mb.sample_memory_bytes() == 123 * MiB


# ---------------------------------------------------------------- 選擇子正規化

def test_selectors_closed_name_set_matches_contract() -> None:
    assert set(mb.SELECTORS) == set(C["selectors"])


@pytest.mark.parametrize("env", [{"FFACT_MEMORY_TIER": "12gb"}, {"FFACT_L2_CATEGORY_WORKERS": "four"},
                                 {"FFACT_L3_PERSIST_MODE": "disk"}, {"FFACT_USE_NUMBA_ROLLING": "yes"}])
def test_normalize_selectors_rejects_illegal_values(env: Dict[str, str]) -> None:
    with pytest.raises(ValueError):
        mb.normalize_selectors(env)


def test_mutation_unknown_tier_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（r23 改）：正規化表（`mb.SELECTORS`，同檔唯一一份）之 tier 值域放入未知值 ⇒ 正規化放行，
    `test_normalize_selectors_rejects_illegal_values[tier]` 之拒絕斷言翻轉（正規化須由該表驅動）。"""
    monkeypatch.setitem(mb.SELECTORS, "FFACT_MEMORY_TIER", tuple(mb.SELECTORS["FFACT_MEMORY_TIER"]) + ("12gb",))
    with pytest.raises(pytest.fail.Exception):
        test_normalize_selectors_rejects_illegal_values({"FFACT_MEMORY_TIER": "12gb"})


def _ffact_env_reads(source: str) -> List[str]:
    keys: List[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", "") or getattr(func, "id", "")
            if name in {"getenv", "get"} and node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str) and value.startswith("FFACT_"):
                    keys.append(value)
        if isinstance(node, ast.Subscript) and isinstance(getattr(node, "slice", None), ast.Constant):
            value = node.slice.value
            if isinstance(value, str) and value.startswith("FFACT_") and "environ" in ast.unparse(node.value):
                keys.append(value)
    return keys


def _scan_violations(selectors: Any, non_arm: Any, sources: Dict[str, str]) -> List[str]:
    """(A)：producer 模組之 FFACT_ 環境讀取 ⇒ 臂選擇鍵不得直接讀（須經 mb.selector）；其餘鍵須列於排除清單。"""
    out = []
    for path, src in sources.items():
        for key in _ffact_env_reads(src):
            if key in selectors:
                out.append(f"{path}: 臂選擇鍵 {key} 旁路直讀")
            elif key not in non_arm:
                out.append(f"{path}: 未登記之 FFACT_ 鍵 {key}")
    return out


def _producer_sources() -> Dict[str, str]:
    return {p: (h.REPO / p).read_text(encoding="utf-8") for p in PRODUCER_MODULES}


def test_static_scan_selector_single_entry_and_registered_keys() -> None:
    assert _scan_violations(mb.SELECTORS, mb.NON_ARM_FFACT_KEYS, _producer_sources()) == []


def test_mutation_selector_list_drops_numba_key_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（r23 改）：自正規化清單（`mb.SELECTORS` 本身）刪 `FFACT_USE_NUMBA_ROLLING` ⇒ 封閉名集合斷言與
    靜態掃描（producer 讀該鍵而清單無之）皆翻轉。"""
    monkeypatch.setattr(mb, "SELECTORS", {k: v for k, v in mb.SELECTORS.items() if k != "FFACT_USE_NUMBA_ROLLING"})
    with pytest.raises(AssertionError):
        test_selectors_closed_name_set_matches_contract()


def test_mutation_producer_getenv_bypass_detected() -> None:
    src = 'import os\nx = os.getenv("FFACT_USE_NUMBA_ROLLING", "1")\n'
    assert _scan_violations(mb.SELECTORS, mb.NON_ARM_FFACT_KEYS, {"inject.py": src})


# ---------------------------------------------------------------- 分支表

def test_branch_table_keys_equal_contract() -> None:
    assert set(mb.BRANCH_TABLE) == set(C["branch_ids"])


def _shape_params() -> Dict[str, Any]:
    return {"rows": 1000, "input_cols": 2, "output_cols": 40, "windows": 2, "steps": 7, "buffer_cols": 64,
            "chunk_cols": 256, "workers": 4, "categories": 6, "max_category_cols": 20, "category_cols_sum": 52,
            "group_cols": 10, "selected_cols": 5, "n_calibration": 500, "accumulated_cols": 5,
            "primary_rows": 1200, "source_rows": 400, "source_shards": 3, "align_block_rows": 1024}


@pytest.mark.parametrize("branch", C["branch_ids"])
def test_branch_components_names_and_kinds_match_contract(branch: str) -> None:
    comps = mb.BRANCH_TABLE[branch](_shape_params())
    got = sorted(f"{c.name}:mapped" if c.kind == "mapped" else c.name for c in comps)
    assert got == sorted(C["branch_components"][branch])


@pytest.mark.parametrize("branch", C["branch_ids"])
def test_planned_sums_only_anon_components(branch: str) -> None:
    comps = mb.BRANCH_TABLE[branch](_shape_params())
    assert mb.planned_bytes(comps) == sum(c.nbytes * c.count for c in comps if c.kind == "anon")


def test_mutation_mapped_counted_in_planned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mb, "planned_bytes", lambda comps: sum(c.nbytes * c.count for c in comps))
    comps = mb.BRANCH_TABLE["L3.numba_single"](_shape_params())
    assert mb.planned_bytes(comps) != sum(c.nbytes * c.count for c in comps if c.kind == "anon")


def test_unknown_branch_rejected() -> None:
    with ExitStack() as stack:
        _ctx(stack)
        with pytest.raises(mb.UnknownBudgetBranchError):
            mb.check("L9.nonexistent", _anon(MiB))


# ---------------------------------------------------------------- (i) 宣告完整性（實際可達組合，真實資料微型設定）

def _resolve(dotted: str) -> Tuple[Any, str]:
    module_name, attr = dotted.split(":")
    owner_name, func_name = attr.split(".")
    module = __import__(module_name, fromlist=[owner_name])
    return getattr(module, owner_name), func_name


def _l3_base() -> pd.DataFrame:
    close = h.kline_close().iloc[-800:]
    return pd.DataFrame({"close_trend_EMA_8": close.ewm(span=8, adjust=False).mean(),
                         "close_trend_SMA_13": close.rolling(13).mean()}).reset_index(drop=True)


def _record_events(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, str]]:
    events: List[Tuple[str, str]] = []
    real_check = mb.check

    def check(branch_id: str, components: Any, **kw: Any) -> None:
        events.append(("check", branch_id))
        return real_check(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", check)
    seen = set()
    for branch, dotted in C["arm_functions"].items():
        owner, name = _resolve(dotted)
        key = (owner, name)
        if key in seen:
            continue
        seen.add(key)
        real = getattr(owner, name)

        def wrap(*a: Any, __real: Callable = real, __fn: str = dotted, **k: Any) -> Any:
            events.append(("arm", __fn))
            return __real(*a, **k)

        monkeypatch.setattr(owner, name, wrap)
    return events


def _assert_arms_preceded_by_check(events: List[Tuple[str, str]]) -> None:
    by_fn: Dict[str, set] = {}
    for branch, dotted in C["arm_functions"].items():
        by_fn.setdefault(dotted, set()).add(branch)
    declared: set = set()
    for kind, value in events:
        if kind == "check":
            assert value in mb.BRANCH_TABLE
            declared.add(value)
        elif kind == "arm":
            assert declared & by_fn[value], f"臂 {value} 之前無對應分支 ID 之 check"


L3_COMBOS = list(itertools.product(["0", "1"], ["0", "1"], ["0", "1"], [True, False]))


@pytest.mark.parametrize("numba,streaming,multi,callback", L3_COMBOS)
def test_declared_completeness_l3_combinations(monkeypatch: pytest.MonkeyPatch, numba: str, streaming: str,
                                               multi: str, callback: bool) -> None:
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", numba)
    monkeypatch.setenv("FFACT_L3_STREAMING", streaming)
    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", multi)
    events = _record_events(monkeypatch)
    sink: List[Any] = []
    with ExitStack() as stack:
        _ctx(stack, budget=64 * GiB, snapshot=_snapshot(free_bytes=64 * GiB))
        RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean", "std"],
                           "keep_all_columns": True}).compute_all(
            _l3_base(), persist_callback=(lambda label, frame: sink.append(frame.shape)) if callback else None)
    assert any(kind == "arm" for kind, _ in events)
    _assert_arms_preceded_by_check(events)


def test_fallback_rechecked_before_pandas_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.FeatureEngineering.operators import numba_rolling
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    monkeypatch.setattr(numba_rolling, "fused_rolling_stats_multi_window",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    events = _record_events(monkeypatch)
    with ExitStack() as stack:
        _ctx(stack, budget=64 * GiB, snapshot=_snapshot(free_bytes=64 * GiB))
        RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean"], "keep_all_columns": True}) \
            .compute_all(_l3_base(), persist_callback=lambda label, frame: None)
    checks = [v for k, v in events if k == "check"]
    assert "L3.pandas_fallback" in checks
    pandas_arm = C["arm_functions"]["L3.pandas_fallback"]
    first_pandas = next(i for i, e in enumerate(events) if e == ("arm", pandas_arm))
    assert ("check", "L3.pandas_fallback") in events[:first_pandas]


@pytest.mark.parametrize("polars_env,polars_available,workers",
                         list(itertools.product(["0", "1"], [True, False], ["1", "4"])))
def test_declared_completeness_l2_combinations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, polars_env: str,
                                               polars_available: bool, workers: str) -> None:
    import momentum.FeatureEngineering.polars_adapter as pa_mod

    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_USE_POLARS", polars_env)
    monkeypatch.setenv("FFACT_L2_CATEGORY_WORKERS", workers)
    if not polars_available:
        monkeypatch.setattr(pa_mod, "_check_polars_available", lambda: False)
    events = _record_events(monkeypatch)
    payload = h.s2_payload(rolling_aggregation={"enabled": False})
    h.generate_s2(root, payload)
    checks = {v for k, v in events if k == "check"}
    expected = "L2.polars" if (polars_env == "1" and polars_available) else (
        "L2.pandas_parallel" if workers == "4" else "L2.pandas_serial")
    assert expected in checks
    _assert_arms_preceded_by_check(events)


@pytest.mark.parametrize("parallel", ["0", "1"])
def test_declared_completeness_l1_combinations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, parallel: str) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", parallel)
    events = _record_events(monkeypatch)
    h.generate_s2(root, h.s2_payload(rolling_aggregation={"enabled": False}))
    assert ("L1.parallel" if parallel == "1" else "L1.serial") in {v for k, v in events if k == "check"}


def test_branch_table_coverage_over_population(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(B)：分支表每一 ID 於組合母體中被實際宣告至少一次（含後備、L4–L6、IC、post-IC、校準歸約）。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.operators import numba_rolling
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    declared: set = set()
    with mb.check_recorder() as recorded:
        for numba, streaming, multi, callback in L3_COMBOS:
            with pytest.MonkeyPatch.context() as mp:
                mp.setenv("FFACT_USE_NUMBA_ROLLING", numba)
                mp.setenv("FFACT_L3_STREAMING", streaming)
                mp.setenv("FFACT_L3_MULTI_WINDOW", multi)
                RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean"],
                                   "keep_all_columns": True, "column_chunk_size": 1 if callback else 0}).compute_all(
                    _l3_base(), persist_callback=(lambda label, frame: None) if callback else None)
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(numba_rolling, "fused_rolling_stats_multi_window",
                       lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
            RollingAggregator({"enabled": True, "windows": [5], "aggregators": ["mean"], "keep_all_columns": True}) \
                .compute_all(_l3_base(), persist_callback=lambda label, frame: None)
        for polars_env, workers, parallel in (("1", "1", "0"), ("0", "1", "1"), ("0", "4", "0")):
            with pytest.MonkeyPatch.context() as mp:
                root = h.isolated(mp, tmp_path / f"p{polars_env}w{workers}l{parallel}")
                mp.setenv("FFACT_USE_POLARS", polars_env)
                mp.setenv("FFACT_L2_CATEGORY_WORKERS", workers)
                mp.setenv("FFACT_LAYER1_PARALLEL", parallel)
                h.generate_s2(root, h.s2_payload(rolling_aggregation={"enabled": False}))
        for compact in ("0", "1"):  # r24：真實多週期 [12h, 4h] 之 dense／compact 兩臂（`MTF.align_*` 只在此命中）
            with pytest.MonkeyPatch.context() as mp:
                root = h.isolated(mp, tmp_path / f"mtf_compact{compact}")
                mp.setenv("FFACT_MULTI_TF_PARALLEL", "1")
                mp.setenv("FFACT_MULTI_TF_MAX_WORKERS", "1")
                mp.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", compact)
                h.generate_s2(root, h.s2_payload(["12h", "4h"], rolling_aggregation={"enabled": False}))
        with pytest.MonkeyPatch.context() as mp:
            root = h.isolated(mp, tmp_path / "icfirst")
            factory = h.make_factory(root)
            factory.run_ic_first(h.SYMBOL, h.PRIMARY, factory._resolve_config(h.s2_payload()),
                                 start_date=h.S2_WINDOW[0], end_date=h.S2_WINDOW[1],
                                 ic_engine=ICEngine({"methods": ["spearman"]}), ic_threshold=0.0, label_horizon="1",
                                 selection_window={"start": h.S2_WINDOW[0], "end": h.S2_WINDOW[1]})
        declared = {branch for branch, _ in recorded}
    missing = set(C["branch_ids"]) - declared
    assert missing == set(), f"未被組合母體命中之分支 ID：{sorted(missing)}"


@pytest.mark.parametrize("branch,env", [("L3.numba_multi_callback", {"FFACT_USE_NUMBA_ROLLING": "1"}),
                                        ("L3.vectorized_chunked", {"FFACT_L3_STREAMING": "0"}),
                                        ("L3.numba_single", {"FFACT_L3_MULTI_WINDOW": "0"})])
def test_mutation_dispatch_point_without_check(monkeypatch: pytest.MonkeyPatch, branch: str, env: Dict[str, str]) -> None:
    """mutant（r23 改）：producer 之某分派點不呼叫 check——於 producer 實跑期間，該分支 ID 之 `check` 呼叫
    不抵達 `memory_budget.check`（等同刪去該分派點之呼叫；外層 recorder 不變）⇒ 同一完整性斷言紅。
    （舊版事後刪 events 列表只測斷言輔助函式本身，不是 producer mutant。）"""
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    for k, v in env.items():
        monkeypatch.setenv(k, v)
    events = _record_events(monkeypatch)
    recorded_check = mb.check
    monkeypatch.setattr(mb, "check",
                        lambda branch_id, components, **kw: None if branch_id == branch
                        else recorded_check(branch_id, components, **kw))
    with ExitStack() as stack:
        _ctx(stack, budget=64 * GiB, snapshot=_snapshot(free_bytes=64 * GiB))
        RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean"], "keep_all_columns": True}) \
            .compute_all(_l3_base(), persist_callback=lambda label, frame: None)
    assert ("arm", C["arm_functions"][branch]) in events, "該分派點之臂須於本組合實際被呼叫"
    with pytest.raises(AssertionError):
        _assert_arms_preceded_by_check(events)


# ---------------------------------------------------------------- 工作區安全間隙（配置前拒絕；mutant＝刪去該成分）

SAFETY_GAP = [
    ("L3.numba_multi_callback", "fused_x2", {}, "l3_callback"),
    ("L3.numba_multi_callback", "step_buffers", {}, "l3_callback"),
    ("L3.numba_single", "six_stat", {"FFACT_L3_MULTI_WINDOW": "0"}, "l3_callback"),
    ("L3.numba_single", "chunk_cache", {"FFACT_L3_MULTI_WINDOW": "0"}, "l3_callback"),
    ("L3.numba_multi_nocallback", "accumulated_steps", {}, "l3_nocallback"),
    ("L3.vectorized_chunked", "chunk_cache", {"FFACT_L3_STREAMING": "0"}, "l3_chunked"),
    ("L2.pandas_parallel", "category_tables_sum", {"FFACT_USE_POLARS": "0", "FFACT_L2_CATEGORY_WORKERS": "4"}, "l2"),
    ("L2.pandas_parallel", "merge_return", {"FFACT_USE_POLARS": "0", "FFACT_L2_CATEGORY_WORKERS": "4"}, "l2"),
    ("L1.parallel", "engine_tables", {"FFACT_LAYER1_PARALLEL": "1"}, "l1"),
    ("PostIC.transform_selected", "accumulated_processed", {}, "postic"),
]


def _producer(kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], Any]:
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    cfg = {"enabled": True, "windows": [5, 13], "aggregators": ["mean", "std"], "keep_all_columns": True}
    if kind == "l3_callback":
        return lambda: RollingAggregator(cfg).compute_all(_l3_base(), persist_callback=lambda label, frame: None)
    if kind == "l3_nocallback":
        return lambda: RollingAggregator(cfg).compute_all(_l3_base())
    if kind == "l3_chunked":
        return lambda: RollingAggregator({**cfg, "column_chunk_size": 1}).compute_all(_l3_base())
    root = h.isolated(monkeypatch, tmp_path)
    if kind in {"l1", "l2"}:
        return lambda: h.generate_s2(root, h.s2_payload(rolling_aggregation={"enabled": False}))
    if kind == "postic":
        from momentum.Analysis.ic_engine import ICEngine

        factory = h.make_factory(root)
        return lambda: factory.run_ic_first(h.SYMBOL, h.PRIMARY, factory._resolve_config(h.s2_payload()),
                                            start_date=h.S2_WINDOW[0], end_date=h.S2_WINDOW[1],
                                            ic_engine=ICEngine({"methods": ["spearman"]}), ic_threshold=0.0,
                                            label_horizon="1",
                                            selection_window={"start": h.S2_WINDOW[0], "end": h.S2_WINDOW[1]})
    raise AssertionError(kind)


def _gap_run(branch: str, component: str, env: Dict[str, str], kind: str, tmp_path: Path,
             monkeypatch: pytest.MonkeyPatch) -> int:
    """預算置於「planned（不含該成分）」與「planned（含該成分）」之中點（目前用量注入為 100 MiB）；
    回傳該分支之臂被呼叫次數。完整估算式 ⇒ 超預算、臂 0 次；估算式漏該成分（mutant）⇒ 中點即其 planned、放行。"""
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    real_check = mb.check

    def check(branch_id: str, components: Any, **kw: Any) -> None:
        budget = 64 * GiB
        if branch_id == branch:
            full = mb.planned_bytes(list(components))
            part = mb.planned_bytes([c for c in components if c.name != component])
            budget = 100 * MiB + (full + part) // 2
        with mb.budget_override(budget):
            return real_check(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", check)
    owner, name = _resolve(C["arm_functions"].get(branch, "momentum.FeatureEngineering.preprocessing.feature_preprocessor:FeaturePreprocessor.transform"))
    calls = {"n": 0}
    real_arm = getattr(owner, name)
    monkeypatch.setattr(owner, name, lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1), real_arm(*a, **k))[1])
    run = _producer(kind, tmp_path, monkeypatch)
    with ExitStack() as stack:
        stack.enter_context(mb.sampler_override(lambda: {"resident": 100 * MiB, "phys_footprint": 100 * MiB}))
        stack.enter_context(mb.vm_snapshot_override(_snapshot(free_bytes=64 * GiB)))
        try:
            run()
        except mb.GenerationMemoryBudgetExceeded:
            pass
    return calls["n"]


@pytest.mark.parametrize("branch,component,env,kind", SAFETY_GAP)
def test_safety_gap_refused_before_arm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: str, component: str,
                                       env: Dict[str, str], kind: str) -> None:
    assert _gap_run(branch, component, env, kind, tmp_path, monkeypatch) == 0


@pytest.mark.parametrize("branch,component,env,kind", SAFETY_GAP)
def test_mutation_safety_gap_component_dropped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, branch: str,
                                               component: str, env: Dict[str, str], kind: str) -> None:
    """mutant：自分支估算式刪去該成分 ⇒ 預算放行而進入臂（配置前拒絕斷言翻轉）。"""
    full_estimator = mb.BRANCH_TABLE[branch]
    monkeypatch.setitem(mb.BRANCH_TABLE, branch,
                        lambda p: [c for c in full_estimator(p) if c.name != component])
    assert _gap_run(branch, component, env, kind, tmp_path, monkeypatch) > 0


def test_preallocation_refusal_before_first_layer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """配置前拒絕：上限低於第一層 planned ⇒ 具名錯誤於該層函式被呼叫之前。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    root = h.isolated(monkeypatch, tmp_path)
    calls = {"n": 0}
    real = FeatureFactory._layer1_atomic_indicators
    monkeypatch.setattr(FeatureFactory, "_layer1_atomic_indicators",
                        lambda self, *a, **k: (calls.__setitem__("n", calls["n"] + 1), real(self, *a, **k))[1])
    with mb.budget_override(mb.sample_memory_bytes() + 1):
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            h.generate_s2(root)
    assert calls["n"] == 0


def test_mutation_check_removed_layer_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(mb, "check", lambda *a, **k: None)
    calls = {"n": 0}
    real = FeatureFactory._layer1_atomic_indicators
    monkeypatch.setattr(FeatureFactory, "_layer1_atomic_indicators",
                        lambda self, *a, **k: (calls.__setitem__("n", calls["n"] + 1), real(self, *a, **k))[1])
    with mb.budget_override(mb.sample_memory_bytes() + 1):
        h.generate_s2(root)
    assert calls["n"] > 0


# ---------------------------------------------------------------- 磁碟後援前置

@pytest.mark.parametrize("bus", ["Disk Image", None])
def test_disk_backing_rejected_before_allocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bus: Any) -> None:
    from momentum.FeatureEngineering import memmap_utils

    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(mb, "backing_bus_protocol", lambda path: bus)
    calls = {"n": 0}
    real = memmap_utils.create_temp_memmap
    monkeypatch.setattr(memmap_utils, "create_temp_memmap",
                        lambda *a, **k: (calls.__setitem__("n", calls["n"] + 1), real(*a, **k))[1])
    with pytest.raises(mb.MemoryMeasurementUnavailable):
        h.generate_s2(root)
    assert calls["n"] == 0


def test_disk_backing_real_internal_disk_passes(tmp_path: Path) -> None:
    assert mb.backing_bus_protocol(tmp_path) not in C["disk_backing_rejected_bus_protocols"]
    mb.assert_disk_backed([tmp_path])


def test_mutation_disk_backing_platform_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：只判 sys.platform == "darwin" 即放行 ⇒ Disk Image 不再被拒。"""
    monkeypatch.setattr(mb, "backing_bus_protocol", lambda path: "Disk Image")
    monkeypatch.setattr(mb, "assert_disk_backed", lambda paths: None if sys.platform == "darwin" else None)
    mb.assert_disk_backed([tmp_path])


def test_temp_memmap_created_under_mapping_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """暫存 memmap 一律建於 run 之映射根（不沿用 TMPDIR）：TMPDIR 指向另一目錄 ⇒ 映射檔仍在映射根下。"""
    from momentum.FeatureEngineering import memmap_utils

    root = h.isolated(monkeypatch, tmp_path / "run")
    other = tmp_path / "other_tmp"
    other.mkdir()
    monkeypatch.setenv("TMPDIR", str(other))
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(other))
    dirs: List[str] = []
    real = memmap_utils.create_temp_memmap
    monkeypatch.setattr(memmap_utils, "create_temp_memmap",
                        lambda *a, **k: (dirs.append(str(k.get("dir"))), real(*a, **k))[1])
    h.generate_s2(root)
    assert dirs and all(d not in ("None", str(other)) for d in dirs)


# ---------------------------------------------------------------- 映射入口封閉（AST）與標記核對

_MAP_CALLS = {"memmap", "open_memmap", "memory_map", "mmap"}


def _mapping_call_sites(sources: Dict[str, str]) -> Dict[Tuple[str, str, str], int]:
    """（檔案, 所在函式〔類別.函式，模組層為 <module>〕, 建構子）→ 呼叫點數。r23：保留呼叫點身分與數量。"""
    sites: Dict[Tuple[str, str, str], int] = {}
    for path, src in sources.items():
        tree = ast.parse(src)
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", "") or getattr(node.func, "id", "")
            kw = {k.arg for k in node.keywords}
            if name in _MAP_CALLS:
                call = ast.unparse(node.func)
            elif name == "load" and "mmap_mode" in kw:
                call = "np.load(mmap_mode)"
            elif name in {"read_parquet", "read_table"} and "memory_map" in kw:
                call = f"{name}(memory_map)"
            else:
                continue
            chain, cur = [], node
            while cur in parents:
                cur = parents[cur]
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    chain.append(cur.name)
            key = (path, ".".join(reversed(chain)) or "<module>", call)
            sites[key] = sites.get(key, 0) + 1
    return sites


def _registered_sites() -> Dict[Tuple[str, str, str], int]:
    entries = C["mapping_entries"]["writable"] + C["mapping_entries"]["readonly"]
    return {(e["file"], e["function"], e["call"]): int(e["count"]) for e in entries}


def _unregistered(sites: Dict[Tuple[str, str, str], int]) -> List[Tuple[Tuple[str, str, str], int]]:
    """未登記之（檔案, 函式, 建構子），或同一處之呼叫點數超過登記數 ⇒ 列出。"""
    registered = _registered_sites()
    return [(k, n) for k, n in sites.items() if n > registered.get(k, 0)]


def _momentum_sources() -> Dict[str, str]:
    return {str(p.relative_to(h.REPO)): p.read_text(encoding="utf-8") for p in (h.REPO / "momentum").rglob("*.py")}


def test_mapping_entry_points_closed() -> None:
    sites = _mapping_call_sites(_momentum_sources())
    assert _unregistered(sites) == []
    assert set(sites) == set(_registered_sites()), "登記清單有已不存在之呼叫點（清單須與碼同步）"


def test_mutation_unregistered_open_memmap_detected() -> None:
    """mutant：producer（以真實 memmap_utils 原始碼為底）新增未登記之 open_memmap 呼叫 ⇒ 掃描抓到未登記入口。"""
    import inspect

    from momentum.FeatureEngineering import memmap_utils

    src = inspect.getsource(memmap_utils) + \
        "\n\ndef _injected():\n    return np.lib.format.open_memmap('f.npy', mode='w+', dtype='f4', shape=(1,))\n"
    assert _unregistered(_mapping_call_sites({"momentum/FeatureEngineering/memmap_utils.py": src}))


def test_mutation_same_constructor_new_call_site_detected() -> None:
    """mutant（r23）：同檔另一函式新增已登記建構子（`np.memmap`）之呼叫 ⇒ 依（函式, 數量）判未登記。"""
    import inspect

    from momentum.FeatureEngineering import memmap_utils

    src = inspect.getsource(memmap_utils) + \
        "\n\ndef _injected():\n    return np.memmap('f.dat', mode='w+', dtype='f4', shape=(1,))\n"
    assert _unregistered(_mapping_call_sites({"momentum/FeatureEngineering/memmap_utils.py": src}))
    real_fn = inspect.getsource(memmap_utils.create_temp_memmap)
    doubled = real_fn.rstrip() + "\n    _extra = np.memmap(path, mode='w+', dtype='f4', shape=(1,))\n"
    assert _unregistered(_mapping_call_sites({"momentum/FeatureEngineering/memmap_utils.py": doubled})), \
        "登記之函式內呼叫點數增加 ⇒ 須判未登記"


@pytest.mark.parametrize("case", ["l3_pandas_fallback", "l2_spill", "registry_multi_shard", "mtf_align_dense",
                                  "mtf_align_sharded", "mtf_align_compact"])
def test_mapped_tags_match_observed_allocations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """標記核對：逐 check 段，觀測之映射配置與該段 `mapped` 成分逐項一一對應（段、入口、容量）；
    入口屬登記之建構子名；釋放段合於宣告之生命期（r24）；案例結束時全部映射已釋放。"""
    observed = _observe_mappings(case, tmp_path, monkeypatch)
    declared = _declared_mapped(case)
    assert observed, "案例須實際觸及映射入口"
    assert {e for _, e, _ in declared} <= set(C["mapping_constructors"])
    assert sorted(observed) == sorted(declared)
    assert _lifetime_violations() == []
    assert _observe_mappings.leaks == []  # type: ignore[attr-defined]
    if case == "mtf_align_dense":
        assert any(e == "np.lib.format.open_memmap" for _, e, _ in observed)
    if case == "mtf_align_sharded":
        groups = getattr(_run_mapping_case, "source_groups", [])
        multi = [n for _, n in groups if n > 1]
        assert multi, "須有同一來源群組分片數 > 1"
        per_seg: Dict[int, int] = {}
        for seg, e, _ in observed:
            if e == "np.load(mmap_mode)":
                per_seg[seg] = per_seg.get(seg, 0) + 1
        assert any(n in per_seg.values() for n in multi), "某段之逐片映射次數須等於該群組分片數"


def test_mutation_mapping_released_next_segment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（r24）：分片映射延後至下一段才釋放（測試端持有每片映射至下一次 check）⇒ 生命期斷言紅。"""
    held: List[Any] = []
    real_check = mb.check

    def check_then_drop(branch_id: str, components: Any, **kw: Any) -> None:
        out = real_check(branch_id, components, **kw)
        held.clear()  # 於下一次 check 之後才放手
        return out

    real_load = np.load

    def load_and_hold(path: Any, *a: Any, mmap_mode: Any = None, **k: Any) -> Any:
        out = real_load(path, *a, mmap_mode=mmap_mode, **k)
        if mmap_mode:
            held.append(out)
        return out

    monkeypatch.setattr(mb, "check", check_then_drop)
    monkeypatch.setattr(np, "load", load_and_hold)
    _observe_mappings("registry_multi_shard", tmp_path, monkeypatch)
    assert _lifetime_violations()


def test_mutation_mtf_aligned_output_tagged_anon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（v23 (f)）：對齊輸出之 mapped 成分改標 anon 並自匿名扣同量 ⇒ 逐項對應紅。"""
    full_estimator = mb.BRANCH_TABLE["MTF.align_persist"]

    def mislabel(params: Any) -> List[mb.Component]:
        return [mb.Component(c.name, "anon", c.nbytes, None, c.count) if c.name == "aligned_output" else c
                for c in full_estimator(params)]

    monkeypatch.setitem(mb.BRANCH_TABLE, "MTF.align_persist", mislabel)
    observed = _observe_mappings("mtf_align_dense", tmp_path, monkeypatch)
    assert sorted(observed) != sorted(_declared_mapped("mtf_align_dense"))


def test_mutation_mapped_component_tagged_anon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：多片先後載入之一片誤標 anon（估算式該 mapped 成分次數減 1、改計入匿名）⇒ 逐項對應斷言紅。"""
    full_estimator = mb.BRANCH_TABLE["Calib.group_reduce"]

    def mislabel(params: Any) -> List[mb.Component]:
        out = []
        for c in full_estimator(params):
            if c.kind == "mapped" and c.count > 1:
                out.append(mb.Component(c.name, "mapped", c.nbytes, c.entry, c.count - 1))
                out.append(mb.Component(c.name + "_as_anon", "anon", c.nbytes, None, 1))
            else:
                out.append(c)
        return out

    monkeypatch.setitem(mb.BRANCH_TABLE, "Calib.group_reduce", mislabel)
    observed = _observe_mappings("registry_multi_shard", tmp_path, monkeypatch)
    declared = _declared_mapped("registry_multi_shard")
    assert sorted(observed) != sorted(declared)


def _observe_mappings(case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> List[Tuple[int, str, int]]:
    """包住登記清單之全部映射建構子（r23），逐次記（建立時之 check 段, 入口, 容量）與釋放段。

    check 段＝建立當下 `check_recorder` 已記錄之 check 數 − 1（第 k 次 check 之後、第 k+1 次之前為段 k）。
    釋放以 weakref.finalize 記；案例結束（gc 後）仍未釋放之映射記為洩漏。
    """
    import gc
    import weakref

    import pyarrow as pa

    seen: List[Tuple[int, str, int]] = []
    leaks: List[Tuple[int, str, int]] = []
    state: Dict[str, Any] = {"recorded": [], "depth": 0}

    def nested(fn: Callable[..., Any], entry: str, size: Callable[[Any], int]) -> Callable[..., Any]:
        """只記最外層入口（np.load(mmap_mode) 內部經 open_memmap → np.memmap，不重複記）。"""
        def wrapper(*a: Any, **k: Any) -> Any:
            state["depth"] += 1
            try:
                out = fn(*a, **k)
            finally:
                state["depth"] -= 1
            if state["depth"] == 0 and out is not None:
                note(entry, out, size(out))
            return out
        return wrapper

    def note(entry: str, obj: Any, nbytes: int) -> Any:
        rec = (len(state["recorded"]) - 1, entry, int(nbytes))
        seen.append(rec)
        alive: Dict[str, Any] = {"v": True, "release_seg": None}

        def released() -> None:  # r24：記釋放當下之 check 段
            alive["v"] = False
            alive["release_seg"] = len(state["recorded"]) - 1

        try:
            weakref.finalize(obj, released)
        except TypeError:  # 不支援 weakref 之物件（例 pyarrow 檔案）：以 close 記釋放
            real_close = obj.close
            obj.close = lambda *a, **k: (released(), real_close(*a, **k))[1]  # type: ignore[method-assign]
        state.setdefault("alive", []).append((rec, alive))
        return obj

    real_memmap_new = np.memmap.__new__
    real_load = np.load

    def load(path: Any, *a: Any, mmap_mode: Any = None, **k: Any) -> Any:
        if not mmap_mode:
            return real_load(path, *a, **k)
        return nested(lambda: real_load(path, *a, mmap_mode=mmap_mode, **k), "np.load(mmap_mode)",
                      lambda o: o.nbytes)()

    with mb.check_recorder() as recorded:
        state["recorded"] = recorded
        with monkeypatch.context() as mp:
            mp.setattr(np.memmap, "__new__", staticmethod(nested(real_memmap_new, "np.memmap", lambda o: o.nbytes)))
            mp.setattr(np.lib.format, "open_memmap",
                       nested(np.lib.format.open_memmap, "np.lib.format.open_memmap", lambda o: o.nbytes))
            mp.setattr(np, "load", load)
            mp.setattr(pa, "memory_map", nested(pa.memory_map, "pa.memory_map", lambda o: o.size()))
            _run_mapping_case(case, tmp_path, monkeypatch)
        gc.collect()
    leaks.extend(rec for rec, alive in state.get("alive", []) if alive["v"])
    _observe_mappings.recorded = list(recorded)  # type: ignore[attr-defined]
    _observe_mappings.leaks = leaks  # type: ignore[attr-defined]
    _observe_mappings.intervals = [(rec, alive["release_seg"]) for rec, alive in state.get("alive", [])]  # type: ignore[attr-defined]
    return seen


def _declared_mapped(case: str) -> List[Tuple[int, str, int]]:
    """分支表於各 check 段宣告之 mapped 成分：（段, 入口, 容量）× 次數。"""
    return [(seg, entry, nbytes) for seg, entry, nbytes, _ in _declared_mapped_with_lifetime()]


def _declared_mapped_with_lifetime() -> List[Tuple[int, str, int, str]]:
    recorded = getattr(_observe_mappings, "recorded", [])
    out: List[Tuple[int, str, int, str]] = []
    for seg, (_, comps) in enumerate(recorded):
        for c in comps:
            if c.kind == "mapped":
                assert c.lifetime == C["mapped_lifetimes"][c.name], f"{c.name} 生命期須依契約"
                out.extend([(seg, c.entry, c.nbytes, c.lifetime)] * c.count)
    return out


def _lifetime_violations() -> List[Any]:
    """`segment` 生命期之映射須於建立段內釋放（釋放段＝建立段）；`run` 者只須於案例結束前釋放（洩漏另核）。"""
    lifetimes: Dict[Tuple[int, str, int], List[str]] = {}
    for seg, entry, nbytes, life in _declared_mapped_with_lifetime():
        lifetimes.setdefault((seg, entry, nbytes), []).append(life)
    bad = []
    for rec, release_seg in sorted(getattr(_observe_mappings, "intervals", []), key=lambda x: x[0]):
        pool = lifetimes.get(rec, [])
        life = "segment" if "segment" in pool else (pool[0] if pool else None)
        if life in pool:
            pool.remove(life)
        if life == "segment" and release_seg != rec[0]:
            bad.append((rec, release_seg))
    return bad


def _run_mapping_case(case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    if case == "l3_pandas_fallback":
        monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "0")
        RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean"], "keep_all_columns": True}) \
            .compute_all(_l3_base(), persist_callback=lambda label, frame: None)
        return
    root = h.isolated(monkeypatch, tmp_path)
    if case == "l2_spill":
        h.generate_s2(root, h.s2_payload(rolling_aggregation={"enabled": False}))
        return
    if case in ("mtf_align_dense", "mtf_align_sharded", "mtf_align_compact"):
        # 真實 kline [12h, 4h]；根行程逐群組對齊（dense＝compact 關，compact＝compact 開）。
        monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1")
        monkeypatch.setenv("FFACT_MULTI_TF_MAX_WORKERS", "1")
        monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "1" if case == "mtf_align_compact" else "0")
        if case == "mtf_align_sharded":
            # r24：`FFACT_CGSA_SHARD_BYTES` 有 32 MiB 下限（hardware_utils），小環境值無法強制多片；
            # 改以行程內執行器代替 spawn、於同一行程覆寫分片目標 helper，worker 輸出多片，根行程逐片映射。
            import concurrent.futures as cf

            from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
            from momentum.FeatureEngineering.utils import hardware_utils

            class InProcessExecutor:
                def __init__(self, *a: Any, **k: Any) -> None:
                    pass

                def __enter__(self) -> "InProcessExecutor":
                    return self

                def __exit__(self, *exc: Any) -> None:
                    return None

                def submit(self, fn: Callable[..., Any], *a: Any, **k: Any) -> cf.Future:
                    fut: cf.Future = cf.Future()
                    try:
                        fut.set_result(fn(*a, **k))
                    except BaseException as exc:  # noqa: BLE001 — 與 pool 語意同：例外交由 result() 拋
                        fut.set_exception(exc)
                    return fut

            monkeypatch.setenv("NUMBA_NUM_THREADS", os.environ.get("NUMBA_NUM_THREADS", "1"))  # worker 會改寫，結束還原
            monkeypatch.setattr(cf, "ProcessPoolExecutor", InProcessExecutor)
            monkeypatch.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: 256 * 1024)
            groups: List[Tuple[str, int]] = []
            real_src = MultiTFGenerator._load_worker_group_source_array

            def src(group_data: Dict) -> Any:
                groups.append((str(group_data.get("group_id")), len(group_data.get("shards") or [])))
                return real_src(group_data)

            monkeypatch.setattr(MultiTFGenerator, "_load_worker_group_source_array", staticmethod(src))
            _run_mapping_case.source_groups = groups  # type: ignore[attr-defined]
        h.generate_s2(root, h.s2_payload(["12h", "4h"], rolling_aggregation={"enabled": False}))
        return
    if case == "registry_multi_shard":
        # 真實 kline 之 L3 型輸入落 registry、以小分片目標強制多片；於「校準歸約」段內逐片讀回
        # （`core/column_group_registry.py:320–324` 之逐 shard np.load(mmap_mode) 生命週期）。
        from momentum.FeatureEngineering.core.column_group_registry import ColumnGroup, ColumnGroupRegistry, LayerSource
        from momentum.FeatureEngineering.utils import hardware_utils

        shard_bytes = 256 * 1024
        monkeypatch.setattr(hardware_utils, "get_cgsa_shard_bytes", lambda: shard_bytes)
        close = h.kline_close()
        cols = {f"close_ret_lag{k}": close.pct_change().shift(k) for k in range(64)}
        arr = pd.DataFrame(cols).to_numpy(dtype=np.float32)
        reg = ColumnGroupRegistry(tmp_path / "reg")
        group = ColumnGroup(group_id="g", layer=LayerSource.L3, timeframe="12h", data_source="derived",
                            indicator="lag", columns=tuple(cols), shape=arr.shape, dtype="float32")
        reg.save_data(group, arr)
        params = {"rows": arr.shape[0], "group_cols": arr.shape[1], "shard_bytes": shard_bytes,
                  "n_calibration": 500, "accumulated_cols": 0}
        mb.check("Calib.group_reduce", mb.BRANCH_TABLE["Calib.group_reduce"](params))
        reg.load_data("g")
        return
    raise AssertionError(case)


# ---------------------------------------------------------------- 獨立守護行程

def test_guard_script_imports_only_stdlib() -> None:
    tree = ast.parse(GUARD.read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert not mods & {"momentum", "pandas", "numpy", "polars", "pyarrow"}
    assert mods <= set(sys.stdlib_module_names) | {"__future__"}


def test_guard_start_failure_refuses_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(OSError("cannot spawn")))
    with pytest.raises(mb.MemoryMeasurementUnavailable):
        h.generate_s2(root)


def test_guard_footprint_counted_in_current_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """守護之 footprint 計入目前用量（本行程＋守護）。"""
    handle = mb.start_guard(tmp_path, "run-x", budget=64 * GiB)
    try:
        own = mb.sample_memory_bytes()
        guard = mb.sample_footprint_of(handle.pid)
        assert guard > 0
        assert mb._current_usage_bytes(guard_pid=handle.pid) >= own + guard - 16 * MiB
    finally:
        handle.stop()


def _child_script(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "child.py"
    path.write_text("import os, sys, json, time\nsys.path.insert(0, %r)\n" % str(h.REPO) + body, encoding="utf-8")
    return path


def _readings_file(tmp_path: Path, rows: List[Dict[str, Any]]) -> Path:
    path = tmp_path / "readings.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_guard_lifecycle_two_runs_old_guard_has_no_power(tmp_path: Path) -> None:
    """同一父行程先後 run A（小上限）、B（大上限）：A 結束後 A 之守護已回收；B 之讀數超 A 上限而未超 B ⇒ B 完成、無 A 收據。"""
    body = """
from momentum.FeatureEngineering import memory_budget as mb
from pathlib import Path
base = Path(sys.argv[1])
a, b = base / "A", base / "B"
a.mkdir(); b.mkdir()
ga = mb.start_guard(a, "A", budget=1 << 20)
ga.stop()
gb = mb.start_guard(b, "B", budget=64 << 30)
x = bytearray(64 << 20)
time.sleep(2.0)
gb.stop()
print(json.dumps({"a_abort": (a / "memory_guard_abort.json").exists(), "alive": os.getpid()}))
"""
    child = _child_script(tmp_path, body)
    proc = subprocess.run([sys.executable, str(child), str(tmp_path)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["a_abort"] is False


def test_mutation_guard_not_stopped_at_run_exit_kills_next_run(tmp_path: Path) -> None:
    """mutant：A 出口不停止守護（子行程內不呼叫 `GuardHandle.stop`）⇒ A 之守護（小上限）終止父行程。"""
    assert callable(mb.GuardHandle.stop) and callable(mb.start_guard)  # 被測符號：mutant 即略過其 stop
    body = """
from momentum.FeatureEngineering import memory_budget as mb
from pathlib import Path
base = Path(sys.argv[1])
a = base / "A"; a.mkdir()
ga = mb.start_guard(a, "A", budget=1 << 20)
x = bytearray(64 << 20)
time.sleep(5.0)
print("survived")
"""
    child = _child_script(tmp_path, body)
    proc = subprocess.run([sys.executable, str(child), str(tmp_path)], capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0 and "survived" not in proc.stdout


def test_guard_stops_main_during_compiled_numba_kernel(tmp_path: Path) -> None:
    """主行程於真實 compiled numba 核心執行中、守護讀數持續越界 ⇒ abort 收據齊全、主行程以 SIGKILL 結束。"""
    readings = _readings_file(tmp_path, [{"pressure_level": 4, "swap_volume_free_bytes": 75 << 30,
                                          "footprint": 1 << 20}] * 200)
    body = """
os.environ[%r] = %r
from momentum.FeatureEngineering import memory_budget as mb
from momentum.FeatureEngineering.operators import numba_rolling
import numpy as np
from pathlib import Path
run = Path(sys.argv[1]) / "run"; run.mkdir()
g = mb.start_guard(run, "R", budget=64 << 30)
x = np.random.default_rng(0).standard_normal(4_000_000)
for _ in range(400):
    numba_rolling.fused_rolling_stats(x, 2000)
print("finished")
""" % (C["guard_test_readings_env"], str(readings))
    child = _child_script(tmp_path, body)
    proc = subprocess.run([sys.executable, str(child), str(tmp_path)], capture_output=True, text=True, timeout=300)
    assert proc.returncode == -9 and "finished" not in proc.stdout
    receipt = json.loads((tmp_path / "run" / C["guard_files"]["abort_receipt"]).read_text(encoding="utf-8"))
    assert set(C["guard_files"]["abort_receipt_keys"]) <= set(receipt)


def test_guard_stop_flag_then_check_stops_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """第一段：守護寫停止旗標 ⇒ 主行程下一個 check 具名停止。"""
    (tmp_path / C["guard_files"]["stop_flag"]).write_text("pressure_critical", encoding="utf-8")
    with ExitStack() as stack:
        _ctx(stack)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            mb.check("IC.selected_read", _anon(MiB), run_dir=tmp_path)


def test_guard_single_reading_does_not_kill(tmp_path: Path) -> None:
    """第二段需連續 2 次越界：單次越界後恢復 ⇒ 不終止（mutant「只 1 次即終止」下此案例紅）。"""
    readings = _readings_file(tmp_path, [{"pressure_level": 4, "swap_volume_free_bytes": 75 << 30, "footprint": 1 << 20}]
                              + [{"pressure_level": 1, "swap_volume_free_bytes": 75 << 30, "footprint": 1 << 20}] * 50)
    body = """
os.environ[%r] = %r
from momentum.FeatureEngineering import memory_budget as mb
from pathlib import Path
run = Path(sys.argv[1]) / "run"; run.mkdir()
g = mb.start_guard(run, "R", budget=64 << 30)
time.sleep(4.0)
g.stop()
print("survived")
""" % (C["guard_test_readings_env"], str(readings))
    child = _child_script(tmp_path, body)
    proc = subprocess.run([sys.executable, str(child), str(tmp_path)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0 and "survived" in proc.stdout


def test_recovery_after_hard_abort_cleans_owned_paths(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    owned = tmp_path / "owned_tmp"
    owned.mkdir()
    (owned / "x.bin").write_bytes(b"0" * 1024)
    other = tmp_path / "other_run_tmp"
    other.mkdir()
    mb.register_owned_path(run, owned)
    (run / C["guard_files"]["abort_receipt"]).write_text(json.dumps({
        "time": "t", "trigger": "pressure_critical", "readings": {}, "last_checkpoint": "L3", "run_id": "R",
        "owned_paths": [str(owned)]}), encoding="utf-8")
    (run / C["guard_files"]["stop_flag"]).write_text("x", encoding="utf-8")
    report = mb.recover_aborted_run(run)
    assert not owned.exists() and other.exists()
    assert not (run / C["guard_files"]["stop_flag"]).exists()
    assert (run / C["guard_files"]["abort_receipt"]).exists()
    assert report


def test_mutation_recovery_ignores_abort_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "run"
    run.mkdir()
    owned = tmp_path / "owned_tmp"
    owned.mkdir()
    monkeypatch.setattr(mb, "recover_aborted_run", lambda run_dir: {})
    mb.recover_aborted_run(run)
    assert owned.exists()


# ---------------------------------------------------------------- Task 4.3 量測停損

PROBE = h.REPO / "handoffs/run_receipts/icfirstalign_probes/memory_series_probe.py"


def _run_probe(tmp_path: Path, extra_env: Dict[str, str]) -> Tuple[subprocess.CompletedProcess, Path]:
    out = tmp_path / "series.jsonl"
    env = {**os.environ, "PYTHONPATH": str(h.REPO), "ICFA_SERIES_OUT": str(out), **extra_env}
    proc = subprocess.run([sys.executable, str(PROBE), "--max-steps", "3"], capture_output=True, text=True,
                          timeout=600, env=env, cwd=str(tmp_path))
    return proc, out


def test_probe_stop_loss_keeps_partial_series(tmp_path: Path) -> None:
    """越過 75% ⇒ 時序檔非空且含越界前至少一筆、abort 收據齊全、探針被終止。"""
    phys = 8 << 30
    readings = _readings_file(tmp_path, [{"pressure_level": 1, "swap_volume_free_bytes": 75 << 30, "footprint": 1 << 20}] * 4
                              + [{"pressure_level": 1, "swap_volume_free_bytes": 75 << 30, "footprint": int(phys * 0.8)}] * 50)
    proc, out = _run_probe(tmp_path, {C["guard_test_readings_env"]: str(readings)})
    assert proc.returncode == -9
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows and any(r.get("footprint", 0) < phys * 0.75 for r in rows)
    assert list(tmp_path.rglob(C["guard_files"]["abort_receipt"]))


def test_boundary_01_probe_first_step_over_half_stops(tmp_path: Path) -> None:
    """Task 4.3 邊界①：第一步即越過 50% ⇒ 停止並回報（rc 非 0、輸出含停止原因）。"""
    phys = 8 << 30
    readings = _readings_file(tmp_path, [{"pressure_level": 1, "swap_volume_free_bytes": 75 << 30,
                                          "footprint": int(phys * 0.55)}] * 50)
    proc, _ = _run_probe(tmp_path, {C["guard_test_readings_env"]: str(readings), "ICFA_PHYSICAL_BYTES": str(phys)})
    assert proc.returncode != 0 and "50%" in (proc.stdout + proc.stderr)


def test_boundary_02_probe_records_platform(tmp_path: Path) -> None:
    proc, out = _run_probe(tmp_path, {"ICFA_DRY_RUN": "1"})
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows and rows[0].get("platform")


def test_mutation_probe_series_written_at_end_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：時序改為結束時一次寫出 ⇒ 被終止時時序檔空（以 ICFA_SERIES_BUFFERED=1 驅動探針之緩衝模式模擬）。"""
    assert callable(mb.start_guard)  # 被測符號：探針之停損經同一守護
    phys = 8 << 30
    readings = _readings_file(tmp_path, [{"pressure_level": 1, "swap_volume_free_bytes": 75 << 30, "footprint": 1 << 20}] * 4
                              + [{"pressure_level": 1, "swap_volume_free_bytes": 75 << 30, "footprint": int(phys * 0.8)}] * 50)
    proc, out = _run_probe(tmp_path, {C["guard_test_readings_env"]: str(readings), "ICFA_SERIES_BUFFERED": "1"})
    assert not out.exists() or out.read_text(encoding="utf-8").strip() == ""
