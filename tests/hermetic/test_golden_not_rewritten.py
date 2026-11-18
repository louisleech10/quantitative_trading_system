"""TESTSEL I1a｜SPEC Task 1.5：golden 輸入檔不被測試改寫。

1.5a 閘門結果（runs/testsel_route/i1a/i1a_facts.md ①，45 候選檔逐檔＋nodeid 級沙盒實跑）：寫入者 3 條／被改檔 3 個——
- `test_b4_golden_rebaseline.py::test_b4_modified_path_attribution_unexpected_zero` → la1 `BTCUSDT_1h_…_fallback_tail100.h5`
- `test_b4_golden_rebaseline.py::test_b4_cross_symbol_eth_independent` → la1 `ETHUSDT_12h_…_fallback_tail100.h5`
  （機制：`gen_baseline._materialize_short_features` 無條件寫 `INPUTS_DIR`，b4 `_build_live_five_path_artifact` 呼叫之）
- `test_l65_golden.py::test_l65_golden_inventory_exists` → `tests/golden/l65/test_inventory.txt`
  （機制：`tests/conftest.py` `pytest_collection_modifyitems` 於任何 collect-only 改寫入庫清單）
1.5b 改法：`_materialize_short_features` 加輸出目錄參數（預設仍 `INPUTS_DIR`＝正式重生命令行為不變），b4 傳 tmp；
conftest 之 inventory 改寫只在明示時（正式產生者 `scripts/build_l65_golden.collect_existing_l65_tests` 自行寫檔，不依賴該 hook）。
"""
from __future__ import annotations

import hashlib
import inspect
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest

from tests.hermetic._harness import REPO, run_repo_nodeids_in_scratch_cwd

GOLDEN = REPO / "tests" / "golden"
WRITERS = [
    "tests/golden/la1/test_b4_golden_rebaseline.py::test_b4_modified_path_attribution_unexpected_zero",
    "tests/golden/la1/test_b4_golden_rebaseline.py::test_b4_cross_symbol_eth_independent",
    "tests/golden/l65/test_l65_golden.py::test_l65_golden_inventory_exists",
]
INVENTORY = GOLDEN / "l65" / "test_inventory.txt"


def _sha_tree(root: Path) -> Dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


class _GoldenRestore:
    """紅狀態下跑寫入者會改寫入庫 golden：記錄原位元組，結束時還原被改者（只還原、不掩蓋——斷言先於還原比對）。"""

    def __init__(self) -> None:
        self.before_bytes = {p: p.read_bytes() for p in GOLDEN.rglob("*") if p.is_file()}

    def restore(self) -> None:
        for p, b in self.before_bytes.items():
            if not p.exists() or p.read_bytes() != b:
                p.write_bytes(b)


@pytest.mark.slow
def test_accept_01_golden_writers_leave_golden_unchanged() -> None:
    """1.5a 清單每條測試跑後 `tests/golden/**` sha256 與跑前相同（b4 兩條實測 640 s／25 s，屬重型）。"""
    guard = _GoldenRestore()
    before = _sha_tree(GOLDEN)
    try:
        res = run_repo_nodeids_in_scratch_cwd(WRITERS, REPO)
        after = _sha_tree(GOLDEN)
    finally:
        guard.restore()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    assert changed == [], changed
    assert res.rc == 0, res.out


def test_accept_02_plain_collect_only_leaves_inventory() -> None:
    """一般 `--collect-only`（不經正式產生命令）不得改寫入庫 `l65/test_inventory.txt`（實測：現況必改寫）。"""
    guard = _GoldenRestore()
    before = hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "tests/golden/l65/test_l65_golden.py"], cwd=str(REPO), capture_output=True, text=True)
        after = hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
    finally:
        guard.restore()
    assert after == before


def test_accept_03_materialize_short_features_explicit_dir_writes_only_there(tmp_path: Path) -> None:
    """b4 用法：明給輸出目錄 ⇒ 只寫該目錄，入庫 la1/inputs 不變（真實 la0 輸入 BTCUSDT/1h）。"""
    from tests.golden.la1 import gen_baseline as gb

    run = gb.RUNS[0]
    src = sorted(gb.LA0_INPUTS_DIR.glob(run["la0_h5_glob"]))[0]
    before = _sha_tree(gb.INPUTS_DIR)
    h5, meta = gb._materialize_short_features(
        src, run["symbol"], run["timeframe"], run["config_hash"], gb.FALLBACK_TAIL_BARS, inputs_dir=tmp_path
    )
    assert Path(h5).parent == tmp_path and Path(meta).parent == tmp_path
    assert _sha_tree(gb.INPUTS_DIR) == before


def test_boundary_01_official_regen_default_still_writes_inputs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界①：正式重生命令（人工執行 gen_baseline，不給目錄）仍寫 `INPUTS_DIR`（此處以 monkeypatch 指 tmp 代表入庫目錄觀測）。"""
    from tests.golden.la1 import gen_baseline as gb

    fake_inputs = tmp_path / "inputs"
    fake_inputs.mkdir()
    monkeypatch.setattr(gb, "INPUTS_DIR", fake_inputs)
    run = gb.RUNS[0]
    src = sorted(gb.LA0_INPUTS_DIR.glob(run["la0_h5_glob"]))[0]
    h5, _meta = gb._materialize_short_features(src, run["symbol"], run["timeframe"], run["config_hash"], gb.FALLBACK_TAIL_BARS)
    assert Path(h5).parent == fake_inputs and Path(h5).is_file()
    assert "inputs_dir" in inspect.signature(gb._materialize_short_features).parameters


def test_boundary_02_tests_read_golden_from_repo() -> None:
    """邊界②：測試讀 golden 仍讀 repo——b4 之凍結物目錄與 gen_baseline 輸入／輸出目錄皆為入庫路徑。"""
    from tests.golden.la1 import gen_baseline as gb
    import tests.golden.la1.test_b4_golden_rebaseline as b4

    la1 = (REPO / "tests" / "golden" / "la1").resolve()
    assert Path(b4.LA1_DIR).resolve() == la1
    assert Path(gb.OUTPUT_DIR).resolve() == la1
    assert Path(gb.INPUTS_DIR).resolve() == la1 / "inputs"


def test_mutation_default_dir_rewrites_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞對照：寫入者改回不給目錄（寫 INPUTS_DIR）⇒ 被改檔 sha256 不同（以入庫 inputs 之 tmp 複本觀測，不碰入庫檔）。"""
    from tests.golden.la1 import gen_baseline as gb

    copy = tmp_path / "inputs_copy"
    shutil.copytree(gb.INPUTS_DIR, copy)
    monkeypatch.setattr(gb, "INPUTS_DIR", copy)
    before = _sha_tree(copy)
    run = gb.RUNS[0]
    src = sorted(gb.LA0_INPUTS_DIR.glob(run["la0_h5_glob"]))[0]
    gb._materialize_short_features(src, run["symbol"], run["timeframe"], run["config_hash"], gb.FALLBACK_TAIL_BARS)
    after = _sha_tree(copy)
    assert after != before
