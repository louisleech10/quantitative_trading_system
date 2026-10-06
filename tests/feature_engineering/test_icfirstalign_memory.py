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
from typing import Any, Callable, Dict, List, Optional, Tuple

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


_MAX_METRIC_PROBE = """
import sys
from pathlib import Path

import numpy as np

from momentum.FeatureEngineering import memory_budget as mb

MiB, GiB = 1 << 20, 1 << 30
mb.sample_memory_bytes = lambda: max(mb._read_rusage()["resident"], mb._read_rusage()["phys_footprint"])
snapshot = mb.VMSnapshot(free_bytes=8 * GiB, file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                         swap_volume_free_bytes=75 * GiB, swap_volume_capacity_bytes=228 * GiB)
now = mb.sample_memory_bytes()
with mb.budget_override(now + 64 * MiB), mb.vm_snapshot_override(snapshot):
    arr = np.memmap(Path(sys.argv[1]) / "touched.bin", dtype=np.uint8, mode="w+", shape=(256 * MiB,))
    arr[::4096] = 1
    try:
        mb.check("IC.selected_read", [mb.Component(name="read", kind="anon", nbytes=MiB)])
        print("RESULT passed")
    except mb.GenerationMemoryBudgetExceeded:
        print("RESULT raised")
"""


def test_mutation_metric_max_resident_footprint(tmp_path: Path) -> None:
    """mutant：預算量改取 max(resident, footprint) ⇒ 上案例誤拋。

    b3 實作期（測試調整 25）：於新子行程執行——長 session 後段本行程 footprint 遠大於 resident（壓縮／換出頁），
    觸頁 256 MiB 映射使 resident 上升仍不超過 footprint，mutant 之讀數不變而不拋（全套後段實測兩次）；新行程之
    resident≈footprint，mutant 判定與環境無關。案例本體（mutant、上限、觸頁量、斷言）不變。"""
    proc = subprocess.run([sys.executable, "-c", _MAX_METRIC_PROBE, str(tmp_path)], cwd=str(h.REPO),
                          env={**os.environ, "PYTHONPATH": str(h.REPO)}, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "RESULT raised" in proc.stdout, proc.stdout[-2000:]


# ---------------------------------------------------------------- 系統條件

def _swapfiles(limit: int = 100, count: int = 5, size: int = GiB) -> Dict[str, int]:
    return {"swapfile_limit": limit, "swapfile_count": count, "swapfile_size_max": size}


def test_machine_insufficient_raises_named() -> None:
    """SPEC v35：新增量 G > 剩餘可用量 A（free＋file-backed＋換頁剩餘＋可證擴充 X；換頁卷僅剩保留量 ⇒ X＝0）⇒
    具名停止「機器可用量不足」。"""
    snap = _snapshot(free_bytes=GiB // 2, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=4 * GiB,
                     **_swapfiles())
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            mb.check("IC.selected_read", _anon(int(1.5 * GiB)))
    assert info.value.reason == MSG["machine_insufficient"]


def test_swap_expansion_counts_toward_available() -> None:
    """SPEC v35：G 介於「free＋file-backed＋換頁剩餘」與 A 之間（換頁可擴充）⇒ 放行——以前靠換頁跑完者不卡死。"""
    snap = _snapshot(free_bytes=GiB // 2, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=75 * GiB,
                     **_swapfiles())
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap)
        mb.check("IC.selected_read", _anon(int(1.5 * GiB)))


def test_mutation_swap_expansion_counted_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「擴充計 0」（v35 前之舊定義）⇒ 上案例誤拒而紅。"""
    monkeypatch.setattr(mb, "swap_expansion_bytes", lambda snapshot: 0)
    snap = _snapshot(free_bytes=GiB // 2, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=75 * GiB,
                     **_swapfiles())
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            mb.check("IC.selected_read", _anon(int(1.5 * GiB)))


def test_available_definition() -> None:
    """A＝free＋file-backed＋換頁剩餘＋min（剩餘檔數 × 單檔上限，換頁卷可用 − 保留量）；擴充上限讀不到 ⇒ X＝0。"""
    snap = _snapshot(free_bytes=3, file_backed_bytes=5, swap_free_bytes=7, swap_volume_free_bytes=10 * GiB,
                     **_swapfiles(limit=10, count=8, size=GiB))
    assert mb.swap_expansion_bytes(snap) == 2 * GiB  # min(2 個檔, 10 − 4 GiB)
    assert mb.available_bytes(snap) == 15 + 2 * GiB
    roomy = _snapshot(free_bytes=3, file_backed_bytes=5, swap_free_bytes=7, swap_volume_free_bytes=5 * GiB,
                      **_swapfiles(limit=100, count=8, size=GiB))
    assert mb.swap_expansion_bytes(roomy) == GiB  # min(92 個檔, 5 − 4 GiB)
    unreadable = _snapshot(free_bytes=3, file_backed_bytes=5, swap_free_bytes=7, swap_volume_free_bytes=10 * GiB)
    assert mb.available_bytes(unreadable) == 15


def test_expansion_bounded_by_swapfile_slots() -> None:
    """X 取 min：換頁卷剩 150 GiB 而換頁檔僅剩 1 個 ⇒ G＝10 GiB 具名停止。"""
    snap = _snapshot(free_bytes=0, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=150 * GiB,
                     **_swapfiles(limit=6, count=5, size=GiB))
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap, budget=10 ** 15)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            mb.check("IC.selected_read", _anon(10 * GiB))


def test_mutation_expansion_not_bounded_by_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「X 只用換頁卷剩餘（不取檔數 min）」⇒ 上案例誤放行而紅。"""
    monkeypatch.setattr(mb, "swap_expansion_bytes", lambda s: max(
        s.swap_volume_free_bytes - mb.disk_reserve_bytes(s.swapfile_size_max), 0))
    snap = _snapshot(free_bytes=0, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=150 * GiB,
                     **_swapfiles(limit=6, count=5, size=GiB))
    with ExitStack() as stack:
        _ctx(stack, snapshot=snap, budget=10 ** 15)
        mb.check("IC.selected_read", _anon(10 * GiB))


@pytest.mark.parametrize("level", [B["pressure_critical_level"], B["pressure_warn_level"]])
def test_pressure_level_only_recorded(level: int) -> None:
    """SPEC v35／v36：壓力等級只記錄、不拒絕（HEAD 框架臂壓力 4 一次取樣仍跑完）。"""
    with ExitStack() as stack:
        _ctx(stack, snapshot=_snapshot(pressure_level=level))
        mb.check("IC.selected_read", _anon(MiB))


def test_mutation_pressure_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「壓力 ≥ 4 拒絕」⇒ 上案例（等級 4）誤拒而紅。"""
    real = mb.check

    def mutant(branch_id: str, components: Any, **kw: Any) -> None:
        if mb.sample_vm_snapshot().pressure_level >= B["pressure_critical_level"]:
            raise mb.GenerationMemoryBudgetExceeded(branch_id, 0, 0, 0, "pressure")
        real(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", mutant)
    with ExitStack() as stack:
        _ctx(stack, snapshot=_snapshot(pressure_level=B["pressure_critical_level"]))
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            mb.check("IC.selected_read", _anon(MiB))


def test_footprint_far_above_ratio_but_fits_available_passes() -> None:
    """SPEC v35：F ≫ R（實體 75%）而 G ≤ A ⇒ 放行——R 不作拒絕理由。"""
    snap = _snapshot(free_bytes=GiB, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=75 * GiB,
                     **_swapfiles())
    with mb.sampler_override(lambda: {"resident": 4 * GiB, "phys_footprint": 50 * GiB}), \
            mb.vm_snapshot_override(snap):
        mb.check("IC.selected_read", _anon(2 * GiB))


def test_mutation_ratio_cap_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「F＋planned > R 即拒」⇒ 上案例誤拒而紅；硬判定不得隨比例縮放。"""
    real = mb.check

    def mutant(branch_id: str, components: Any, **kw: Any) -> None:
        current = mb.sample_memory_bytes()
        if current + mb.planned_bytes(components) > mb.configured_budget_bytes():
            raise mb.GenerationMemoryBudgetExceeded(branch_id, current, 0, 0, "ratio")
        real(branch_id, components, **kw)

    monkeypatch.setattr(mb, "check", mutant)
    snap = _snapshot(free_bytes=GiB, file_backed_bytes=0, swap_free_bytes=0, swap_volume_free_bytes=75 * GiB,
                     **_swapfiles())
    with mb.sampler_override(lambda: {"resident": 4 * GiB, "phys_footprint": 50 * GiB}), \
            mb.vm_snapshot_override(snap), pytest.raises(mb.GenerationMemoryBudgetExceeded):
        mb.check("IC.selected_read", _anon(2 * GiB))


@pytest.mark.parametrize("size_max,expected", [(None, 4 * GiB), (GiB, 4 * GiB), (2 * GiB, 6 * GiB)])
def test_disk_reserve_bytes(size_max: Any, expected: int) -> None:
    """SPEC v36：磁碟保留量＝max(4 GiB, 3 × 換頁檔單檔上限)；與卷容量無關。"""
    assert mb.disk_reserve_bytes(size_max) == expected == max(B["disk_reserve_min_bytes"],
                                                              B["disk_reserve_swapfiles"] * int(size_max or 0))


def test_mutation_reserve_capacity_fraction() -> None:
    """mutant「保留量取卷容量 × 5%」⇒ 大容量卷（2000 GiB、剩 90 GiB）誤停；正確保留量 4 GiB 不停。"""
    assert mb.guard_should_stop(90 * GiB, mb.disk_reserve_bytes(GiB)) is None
    assert mb.guard_should_stop(90 * GiB, int(2000 * GiB * 0.05)) == "swap_volume_low"


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
    # b3 實作期：chunked 臂須輸入欄數 > chunk（真實兩欄、預設 chunk 256 走 unchunked）⇒ 該案例顯式 chunk＝1
    chunk = {"column_chunk_size": 1} if branch == "L3.vectorized_chunked" else {}
    with ExitStack() as stack:
        _ctx(stack, budget=64 * GiB, snapshot=_snapshot(free_bytes=64 * GiB))
        RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean"], "keep_all_columns": True,
                           **chunk}).compute_all(_l3_base(), persist_callback=lambda label, frame: None)
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
    # b3 實作期：選擇子須於 `_producer` 之隔離環境（prepare_env 重設 FFACT_ 固定值）之後設定，否則被覆寫回預設臂
    for k, v in env.items():
        monkeypatch.setenv(k, v)
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
    # b3 實作期：S2 規模下 spill／concat／對齊之 memmap 皆在 500 MB 門檻下不觸發；pandas L3 臂無條件建 memmap，
    # 故本案例關 numba 使正式生成確有 create_temp_memmap 呼叫可驗（斷言不變）
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "0")
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


def test_mutation_run_mapping_released_after_run_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(p) mutant「L2 spill 映射延後至 run 結束界線之後才釋放」（測試端持有 spill 映射至案例結束）⇒ 生命期斷言紅。"""
    held: List[Any] = []
    real_memmap_new = np.memmap.__new__

    def hold(cls: Any, *a: Any, **k: Any) -> Any:
        out = real_memmap_new(cls, *a, **k)
        held.append(out)
        return out

    monkeypatch.setattr(np.memmap, "__new__", staticmethod(hold))
    _observe_mappings("l2_spill", tmp_path, monkeypatch)
    assert _lifetime_violations()
    held.clear()


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
        # b3 實作期：分片大小不必相等（真實 64 欄 × 256 KiB 目標 ⇒ 38＋26 欄兩片，估算式依片大小分列、各 count 1），
        # 故 mutant 改為「第一個 mapped 成分之一片」誤標 anon（count−1，同量計入匿名）——語意同原「一片誤標」
        out, done = [], False
        for c in full_estimator(params):
            if not done and c.kind == "mapped" and c.count >= 1:
                out.append(mb.Component(c.name, "mapped", c.nbytes, c.entry, c.count - 1, c.lifetime))
                out.append(mb.Component(c.name + "_as_anon", "anon", c.nbytes, None, 1))
                done = True
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
    # b3 實作期：SPEC (ii) 之「段」＝自一次 check 至下一次 check 或該臂結束；臂結束（`layer_end`）後至下一次 check 之間、
    # 及首次 check 之前不屬任何 check 段（例：L6.5／L7 之 registry 讀回，SPEC 檢查點清單不含），不入逐項對應
    recorded_list = list(recorded)
    return [rec for rec in seen
            if rec[0] >= 0 and not str(recorded_list[rec[0]][0]).startswith("LAYER_END:")]


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
        if life == "run":
            # r25：`run` 須於 producer 之 run 結束界線（`mb.layer_end("run")` 記為 "LAYER_END:run"）之前釋放
            recorded = getattr(_observe_mappings, "recorded", [])
            ends = [i for i, (branch, _) in enumerate(recorded) if branch == "LAYER_END:run" and i > rec[0]]
            if not ends or release_seg is None or release_seg >= ends[0]:
                bad.append((rec, release_seg))
    return bad


def _run_mapping_case(case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator

    if case == "l3_pandas_fallback":
        monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "0")
        out = RollingAggregator({"enabled": True, "windows": [5, 13], "aggregators": ["mean"],
                                 "keep_all_columns": True}).compute_all(_l3_base(),
                                                                         persist_callback=lambda label, frame: None)
        # b3 實作期：單獨呼叫 producer 無 run 界線——由本 harness 於消費端放手回傳表後補記 run 結束界線
        del out
        mb.layer_end("run")
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

                def shutdown(self, wait: bool = True) -> None:
                    # 排程器於 shutdown 成功後才標 joined（SPEC v30）；同步執行者提交時已完成
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
            # b3 實作期：行程內執行器之 worker 讀數即整個測試行程之 footprint（非獨立子行程）⇒ 任務峰值 E 加上當下
            # footprint（正式估算之資料與 runtime 項不變），否則全套後段行程已膨脹時 worker 被判「估算低估」
            real_envelope = MultiTFGenerator._estimate_worker_envelope

            def envelope(self: Any, *a: Any, **k: Any) -> Any:
                base = real_envelope(self, *a, **k)
                return None if base is None else base + mb.sample_memory_bytes()

            monkeypatch.setattr(MultiTFGenerator, "_estimate_worker_envelope", envelope)
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
    assert mods <= _stdlib_module_names() | {"__future__"}


def _stdlib_module_names() -> set:
    """標準函式庫模組名（`sys.stdlib_module_names` 自 3.10 起才有；3.9 以 stdlib 目錄與內建模組列出）。"""
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return set(names)
    import sysconfig

    stdlib = Path(sysconfig.get_paths()["stdlib"])
    found = set(sys.builtin_module_names)
    for p in stdlib.iterdir():
        if p.name == "site-packages":
            continue
        if p.suffix == ".py":
            found.add(p.stem)
        elif p.is_dir() and (p / "__init__.py").exists():
            found.add(p.name)
    dynload = stdlib / "lib-dynload"
    if dynload.is_dir():
        found.update(p.name.split(".")[0] for p in dynload.iterdir())
    return found


def test_guard_start_failure_refuses_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    # b3 實作期：磁碟後援查詢（diskutil）亦經 subprocess；只令守護腳本之啟動失敗，使拒絕確由守護啟動造成
    real_popen = subprocess.Popen
    spawned = {"guard": 0}

    def popen(args: Any, *a: Any, **k: Any) -> Any:
        if any(str(x).endswith("memory_guard.py") for x in (args if isinstance(args, (list, tuple)) else [args])):
            spawned["guard"] += 1
            raise OSError("cannot spawn")
        return real_popen(args, *a, **k)

    monkeypatch.setattr(subprocess, "Popen", popen)
    with pytest.raises(mb.MemoryMeasurementUnavailable, match="守護"):
        h.generate_s2(root)
    assert spawned["guard"] == 1


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


_SWAP_LOW_ROW = {"pressure_level": 1, "swap_volume_free_bytes": 1 << 30, "footprint": 1 << 20}  # 1 GiB < 保留量
_NORMAL_ROW = {"pressure_level": 1, "swap_volume_free_bytes": 75 << 30, "footprint": 1 << 20}


def test_guard_lifecycle_two_runs_old_guard_has_no_power(tmp_path: Path) -> None:
    """同一父行程先後 run A、B（SPEC v35：以換頁卷剩餘之注入讀數驅動——A 之守護讀到換頁卷不足、B 之守護讀到
    正常）：A 結束後 A 之守護已回收 ⇒ B 完成、無 A 收據。"""
    a_rows = _readings_file(tmp_path, [_SWAP_LOW_ROW] * 200)
    b_rows = tmp_path / "readings_b.jsonl"
    b_rows.write_text("\n".join(json.dumps(_NORMAL_ROW) for _ in range(200)) + "\n", encoding="utf-8")
    body = """
from momentum.FeatureEngineering import memory_budget as mb
from pathlib import Path
base = Path(sys.argv[1])
a, b = base / "A", base / "B"
a.mkdir(); b.mkdir()
os.environ[%r] = %r
ga = mb.start_guard(a, "A", budget=64 << 30)
ga.stop()
os.environ[%r] = %r
gb = mb.start_guard(b, "B", budget=64 << 30)
time.sleep(2.0)
gb.stop()
print(json.dumps({"a_abort": (a / "memory_guard_abort.json").exists(), "alive": os.getpid()}))
""" % (C["guard_test_readings_env"], str(a_rows), C["guard_test_readings_env"], str(b_rows))
    child = _child_script(tmp_path, body)
    proc = subprocess.run([sys.executable, str(child), str(tmp_path)], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["a_abort"] is False


def test_mutation_guard_not_stopped_at_run_exit_kills_next_run(tmp_path: Path) -> None:
    """mutant：A 出口不停止守護（子行程內不呼叫 `GuardHandle.stop`）⇒ A 之守護（讀到換頁卷不足）終止父行程。"""
    assert callable(mb.GuardHandle.stop) and callable(mb.start_guard)  # 被測符號：mutant 即略過其 stop
    a_rows = _readings_file(tmp_path, [_SWAP_LOW_ROW] * 200)
    body = """
os.environ[%r] = %r
from momentum.FeatureEngineering import memory_budget as mb
from pathlib import Path
base = Path(sys.argv[1])
a = base / "A"; a.mkdir()
ga = mb.start_guard(a, "A", budget=64 << 30)
time.sleep(5.0)
print("survived")
""" % (C["guard_test_readings_env"], str(a_rows))
    child = _child_script(tmp_path, body)
    proc = subprocess.run([sys.executable, str(child), str(tmp_path)], capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0 and "survived" not in proc.stdout


def test_guard_stops_main_during_compiled_numba_kernel(tmp_path: Path) -> None:
    """主行程於真實 compiled numba 核心執行中、守護讀數持續越界 ⇒ abort 收據齊全、主行程以 SIGKILL 結束。"""
    readings = _readings_file(tmp_path, [_SWAP_LOW_ROW] * 200)  # SPEC v35：以換頁卷不足驅動（壓力不再為條件）
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
    (tmp_path / C["guard_files"]["stop_flag"]).write_text("swap_volume_low", encoding="utf-8")
    with ExitStack() as stack:
        _ctx(stack)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded):
            mb.check("IC.selected_read", _anon(MiB), run_dir=tmp_path)


def test_guard_single_reading_does_not_kill(tmp_path: Path) -> None:
    """第二段需連續 2 次越界：單次越界後恢復 ⇒ 不終止（mutant「只 1 次即終止」下此案例紅）。"""
    readings = _readings_file(tmp_path, [_SWAP_LOW_ROW] + [_NORMAL_ROW] * 50)
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


# ---------------------------------------------------------------- 守護第二段逐條件計數（SPEC v30；審碼 b3 r1 codex P2-04）

def _guard_run(readings: List[Dict[str, Any]], budget: int = 100) -> Dict[str, Any]:
    """以注入讀數序列跑守護主迴圈（旗標寫入與終止皆攔截，不送任何訊號）；回傳終止原因與耗用之取樣數。"""
    from unittest.mock import patch

    from momentum.FeatureEngineering import memory_guard as mg

    consumed: List[int] = []
    killed: List[str] = []

    class Readings:
        def __init__(self, *a: Any) -> None:
            self.pos = 0

        def sample(self) -> Dict[str, Any]:
            value = readings[min(self.pos, len(readings) - 1)]
            self.pos += 1
            consumed.append(self.pos)
            return dict(value)

    def abort(args: Any, system: Any, reason: str, history: Any) -> None:
        killed.append(reason)

    alive = iter(range(len(readings) + 1))

    def is_alive(pid: int) -> bool:  # 讀數用盡後令本行程「已死」以結束迴圈（無終止時）
        return next(alive, None) is not None and len(consumed) < len(readings)

    import signal

    # 守護主程式會安裝 SIGTERM／SIGINT 處理器（獨立行程中正確）；行程內呼叫時須還原，否則遺留至同 session 之後續測試
    saved = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        with patch.object(mg, "_System", lambda: object()), patch.object(mg, "_Readings", Readings), \
                patch.object(mg, "_alive", is_alive), patch.object(mg, "_write_atomic", lambda *a: None), \
                patch.object(mg, "_abort", abort):
            mg._STOP = False
            mg.main(["--pid", "123456", "--run-dir", "/nonexistent", "--run-id", "probe", "--budget", str(budget),
                     "--interval", "0.01"])
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)
    return {"killed": killed, "samples": len(consumed)}


def _r(pressure: int = 1, swap_free: int = 10 ** 20, available: Optional[int] = 10 ** 12,
       failed: bool = False, footprint: int = 0, swapfiles_full: bool = True) -> Dict[str, Any]:
    """守護讀數（SPEC v35–v39 之條件：換頁卷剩餘、剩餘可用量 A、量測失敗）；`available` 置於 free（其餘 A 成分 0）。"""
    row: Dict[str, Any] = {"pressure_level": pressure, "swap_volume_free_bytes": swap_free,
                           "swap_volume_capacity_bytes": 0, "footprint": footprint, "failed": [1] if failed else []}
    if available is not None:
        row.update({"free_bytes": available, "file_backed_bytes": 0, "swap_avail_bytes": 0, "page_size": 16384,
                    "swapfile_limit": 100, "swapfile_count": 100 if swapfiles_full else 5,
                    "swapfile_size_max": 1 << 30})
    return row


def test_guard_alternating_conditions_do_not_accumulate() -> None:
    """旗標後三種不同條件輪替各成立 1 次 ⇒ 不終止（改前：任一非空即累加 ⇒ 第 3 次取樣即終止而紅）。"""
    out = _guard_run([_r(swap_free=10 ** 9), _r(available=0), _r(failed=True), _r()])
    assert out["killed"] == []


def test_guard_same_condition_twice_after_flag_kills() -> None:
    """同一條件於旗標後連續 2 次成立 ⇒ 終止（第 3 次取樣），原因＝該條件。"""
    out = _guard_run([_r(available=0), _r(available=0), _r(available=0), _r()])
    assert out["killed"] == ["paging_exhausted"] and out["samples"] == 3


def test_guard_persistent_condition_counted_despite_priority_flicker() -> None:
    """換頁耗盡持續、換頁卷不足時有時無（優先序較高）⇒ 換頁耗盡仍連續計數而終止；只依「最優先原因」計數之實作
    會因原因切換歸零而漏殺。"""
    out = _guard_run([_r(swap_free=10 ** 9, available=0), _r(available=0), _r(swap_free=10 ** 9, available=0), _r()])
    assert out["killed"] == ["paging_exhausted"] and out["samples"] == 3


def test_guard_pressure_critical_never_stops() -> None:
    """SPEC v35：壓力等級 4 連續成立而其餘正常 ⇒ 不立旗、不終止（mutant「壓力 ≥ 4 立旗」⇒ 誤殺而紅）。"""
    out = _guard_run([_r(pressure=4)] * 4 + [_r()])
    assert out["killed"] == []


def test_guard_footprint_over_ratio_never_stops() -> None:
    """SPEC v35：全樹 footprint 遠大於 R（上限參數）而 A 與換頁卷充裕 ⇒ 不終止（mutant「守護以 F 對 R 判停」⇒ 紅）。"""
    out = _guard_run([_r(footprint=1 << 40)] * 4 + [_r()], budget=100)
    assert out["killed"] == []


def test_guard_positive_available_with_full_swapfiles_does_not_stop() -> None:
    """SPEC v38：換頁檔數達上限、free 與換頁剩餘各 512 MiB（各小於一個換頁檔）⇒ A ≥ 一頁、不立旗（mutant
    「各項小於一個換頁檔即立旗」⇒ 誤殺而紅）；段內動態：A 自 8 GiB 降至 3 GiB（段內已實現配置）⇒ 不終止，
    同段 A 降至 0 ⇒ 立旗並經連續 2 次終止。"""
    assert _guard_run([_r(available=1 << 30)] * 4 + [_r()])["killed"] == []
    assert _guard_run([_r(available=8 << 30), _r(available=3 << 30), _r(available=3 << 30),
                       _r(available=3 << 30), _r()])["killed"] == []
    out = _guard_run([_r(available=8 << 30), _r(available=0), _r(available=0), _r(available=0), _r()])
    assert out["killed"] == ["paging_exhausted"] and out["samples"] == 4


def test_guard_available_counts_swap_expansion() -> None:
    """換頁檔數未達上限、換頁卷充裕 ⇒ 即使 free 與換頁剩餘為 0，A 含可證擴充 ⇒ 不立旗。"""
    assert _guard_run([_r(available=0, swapfiles_full=False, swap_free=50 << 30)] * 4 + [_r()])["killed"] == []


def test_guard_first_observation_after_exhaustion_timing() -> None:
    """SPEC v39 時序：首筆觀測前即耗盡 ⇒ 首筆立旗、第三筆終止；零值後一筆回復 ⇒ 不終止。驗收只斷言觀測後之反應
    順序，不斷言早於系統終止。"""
    assert _guard_run([_r(available=0)] * 4 + [_r()])["samples"] == 3
    assert _guard_run([_r(available=0), _r(), _r(available=0), _r()])["killed"] == []


# ---------------------------------------------------------------- 選路（SPEC v35–v39：白名單等價臂、預設保留原臂）

def _route_table(monkeypatch: pytest.MonkeyPatch, original_bytes: int, alt_bytes: int) -> None:
    """注入兩個分支之估算：原臂（L2.polars）與白名單候選（L2.pandas_serial）各一 anon 成分。"""
    monkeypatch.setitem(mb.BRANCH_TABLE, "L2.polars", lambda p: [mb.Component("orig", "anon", original_bytes)])
    monkeypatch.setitem(mb.BRANCH_TABLE, "L2.pandas_serial", lambda p: [mb.Component("alt", "anon", alt_bytes)])


def _route_ctx(stack: ExitStack, available: int) -> None:
    stack.enter_context(mb.vm_snapshot_override(_snapshot(free_bytes=available, file_backed_bytes=0, swap_free_bytes=0,
                                                          swap_volume_free_bytes=75 * GiB)))


_CANDS = [("L2.polars", {}), ("L2.pandas_serial", {})]


def test_route_keeps_original_when_fits_without_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    """原臂 G ≤ A 且無收據 ⇒ 保留原臂（即使候選 planned 較小）。"""
    _route_table(monkeypatch, original_bytes=2 * GiB, alt_bytes=GiB)
    with ExitStack() as stack:
        _route_ctx(stack, available=4 * GiB)
        assert mb.route("Layer 2", _CANDS, scale_key="s") == "L2.polars"


def test_mutation_route_by_smallest_planned(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant「依 planned 最小選」⇒ 上案例選到候選（較小者未證較快）而紅。"""
    _route_table(monkeypatch, original_bytes=2 * GiB, alt_bytes=GiB)
    chosen = min(_CANDS, key=lambda c: mb.planned_bytes(mb.estimate(c[0], c[1])))[0]
    assert chosen == "L2.pandas_serial"  # mutant 之選擇 ≠ 正確之「保留原臂」


def test_route_switches_when_original_exceeds_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """原臂 G > A 而白名單候選可容 ⇒ 改走候選。"""
    _route_table(monkeypatch, original_bytes=6 * GiB, alt_bytes=GiB)
    with ExitStack() as stack:
        _route_ctx(stack, available=4 * GiB)
        assert mb.route("Layer 2", _CANDS, scale_key="s") == "L2.pandas_serial"


def test_route_raises_when_no_candidate_fits(monkeypatch: pytest.MonkeyPatch) -> None:
    """全部候選皆 G > A ⇒ 具名停止（原臂之錯誤）。"""
    _route_table(monkeypatch, original_bytes=6 * GiB, alt_bytes=5 * GiB)
    with ExitStack() as stack:
        _route_ctx(stack, available=4 * GiB)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            mb.route("Layer 2", _CANDS, scale_key="s")
    assert info.value.reason == MSG["machine_insufficient"] and info.value.planned == 6 * GiB


@pytest.mark.parametrize("receipt_scale,expected", [("s", "L2.pandas_serial"), ("other", "L2.polars")])
def test_route_speed_receipt_switch_only_on_matching_scale(monkeypatch: pytest.MonkeyPatch, receipt_scale: str,
                                                           expected: str) -> None:
    """原臂 G ≤ A：有相符規模之收據證明候選較快 ⇒ 切換；收據規模不符 ⇒ 保留原臂（SPEC v36，審碼 r32 codex P2-01）。"""
    _route_table(monkeypatch, original_bytes=GiB, alt_bytes=2 * GiB)
    monkeypatch.setitem(mb.ROUTE_SPEED_RECEIPTS, ("Layer 2", "L2.polars", "L2.pandas_serial"), (receipt_scale,))
    with ExitStack() as stack:
        _route_ctx(stack, available=8 * GiB)
        assert mb.route("Layer 2", _CANDS, scale_key="s") == expected


def test_route_does_not_switch_on_stop_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """停止旗標已立 ⇒ 具名停止、不試候選（非容量原因不換路）。"""
    _route_table(monkeypatch, original_bytes=GiB, alt_bytes=GiB)
    (tmp_path / C["guard_files"]["stop_flag"]).write_text("swap_volume_low", encoding="utf-8")
    real = mb.check_estimate
    tried: List[str] = []

    def spy(branch: str, params: Any, **kw: Any) -> Any:
        tried.append(branch)
        return real(branch, params, run_dir=tmp_path, **kw)

    monkeypatch.setattr(mb, "check_estimate", spy)
    with ExitStack() as stack:
        _route_ctx(stack, available=8 * GiB)
        with pytest.raises(mb.GenerationMemoryBudgetExceeded) as info:
            mb.route("Layer 2", _CANDS)
    assert tried == ["L2.polars"] and info.value.reason == MSG["swap_volume_low"]


# ── 速度驗收判定（SPEC v40）──────────────────────────────────────────────────

_SPEED_VERDICT = Path(__file__).resolve().parents[2] / "handoffs/run_receipts/icfirstalign_probes/speed_verdict.py"


def _speed_module(mutation: Optional[Tuple[str, str]] = None) -> Any:
    """載入判定程式；mutation＝(原字串, 置換字串)，須恰命中一次。"""
    import types

    src = _SPEED_VERDICT.read_text(encoding="utf-8")
    if mutation is not None:
        assert src.count(mutation[0]) == 1, mutation[0]
        src = src.replace(mutation[0], mutation[1])
    mod = types.ModuleType("speed_verdict_under_test")
    exec(compile(src, str(_SPEED_VERDICT), "exec"), mod.__dict__)
    return mod


def _pair(order: str, head: float, new: float) -> Dict[str, Any]:
    return {"order": order, "head_s": head, "new_s": new}


def _case(name: str, pairs: List[Dict[str, Any]], **kw: Any) -> Dict[str, Any]:
    return {"name": name, "timing_source": "wall_clock_full_entry", "pairs": pairs, **kw}


# (案例, 正確判定)；每個 mutant 至少使其中一案例判定改變。
_SPEED_BATTERY: List[Tuple[Dict[str, Any], str]] = [
    (_case("single_faster", [_pair("new_first", 100.0, 99.5)]), "pass"),
    (_case("single_within_3pct", [_pair("new_first", 100.0, 102.5)]), "pass"),
    # r＝1.04 > 1.03 ⇒ 不過（容許改 5% 會誤過）
    (_case("single_over_3pct", [_pair("head_first", 100.0, 104.0)]), "fail"),
    (_case("no_pairs", []), "insufficient"),
    (_case("censored_done", [], censored=True, new_outcome="completed", new_s=4000.0), "censored"),
    (_case("censored_unknown", [], censored=True, new_outcome=None), "fail"),
    # 新碼一快兩慢：中位 104 ⇒ 不過（取最快一次會誤過）
    (_case("median_not_min", [_pair("new_first", 100.0, 101.0), _pair("head_first", 100.0, 104.0),
                              _pair("new_first", 100.0, 104.5)]), "fail"),
    # 四對中兩對新碼大幅較慢：中位 106 ⇒ 不過（剔除差距最大之對會改判過）
    (_case("all_pairs_kept", [_pair("new_first", 100.0, 102.0), _pair("head_first", 100.0, 102.0),
                              _pair("new_first", 100.0, 110.0), _pair("head_first", 100.0, 110.0)]), "fail"),
]


def _speed_battery_failures(sv: Any) -> List[str]:
    failures = []
    for case, expected in _SPEED_BATTERY:
        got = sv.judge(case)["verdict"]
        if got != expected:
            failures.append(f"{case['name']}: {got} != {expected}")
    try:
        sv.judge({**_SPEED_BATTERY[0][0], "timing_source": "generation_only"})
        failures.append("timing_source 未拒")
    except ValueError:
        pass
    return failures


def test_speed_verdict_contract() -> None:
    """SPEC v40 速度驗收判定：已跑之對中位比 ≤ 1.03 視為相同、censored 永不判過、計時來源須為完整入口牆鐘。"""
    sv = _speed_module()
    assert _speed_battery_failures(sv) == []
    receipt = sv.build_receipt([c for c, _ in _SPEED_BATTERY if c["name"] in ("single_faster", "censored_done")])
    assert receipt["all_pass"] is True
    receipt = sv.build_receipt([c for c, _ in _SPEED_BATTERY if c["name"] in ("single_faster", "median_not_min")])
    assert receipt["all_pass"] is False and receipt["cases"][1]["input"]["pairs"][2]["new_s"] == 104.5


_SPEED_MUTANTS = {
    "censored_counted_as_pass": ('"verdict": "censored", "reason"', '"verdict": "pass", "reason"'),
    "timing_excludes_calibration": ('if case.get("timing_source") != TIMING_SOURCE:', "if False:"),
    "tolerance_5pct": ("SAME_RATIO = 1.03", "SAME_RATIO = 1.05"),
    "fastest_new_run": ("statistics.median(t_n)", "min(t_n)"),
    "drop_largest_gap_pair": (
        '    t_h = [float(p["head_s"]) for p in pairs]',
        '    pairs = sorted(pairs, key=lambda p: abs(float(p["new_s"]) - float(p["head_s"])))[:-1] if len(pairs) >= 3 else pairs\n'
        '    t_h = [float(p["head_s"]) for p in pairs]'),
}


@pytest.mark.parametrize("mutant", sorted(_SPEED_MUTANTS))
def test_mutation_speed_verdict(mutant: str) -> None:
    """每個判定規則 mutant 至少使一個契約案例判定改變（SPEC v40）。"""
    assert _speed_battery_failures(_speed_module(_SPEED_MUTANTS[mutant])) != []


def test_speed_stage_parser_segments_and_midnight() -> None:
    """逐段切分：首段自第一筆時間戳、重複標記帶序號、跨午夜續算。"""
    sv = _speed_module()
    lines = [
        "23:59:58.000 x start\n",
        "23:59:59.000 f Layer 1 starting, rss=1MB\n",
        "no timestamp line\n",
        "00:00:01.500 f Layer 1 done: 3 cols\n",
        "00:00:02.000 f Layer 1 starting, rss=1MB\n",
        "00:00:05.000 f Layer 1 done: 3 cols\n",
        "00:00:06.000 x tail\n",
    ]
    assert sv.parse_stage_log(lines) == {
        "start→layer_start1#1": 1.0,
        "layer_start1#1→layer_done1#1": 2.5,
        "layer_done1#1→layer_start1#2": 0.5,
        "layer_start1#2→layer_done1#2": 3.0,
        "layer_done1#2→end": 1.0,
    }
