"""SPLITUNIFY B2c：golden 五組之 pytest 入口（SPEC §G；nodeid 依 SPEC Task 2.3 命名）。

🔴 本檔**不重寫**比對邏輯——`scripts/freeze_splitunify_golden.py` 是唯一實作，
本檔只是把它接進 pytest，讓 golden 進回歸網。重寫一份就又是「兩份算術」。

nodeid 對照 SPEC §G：
  `-k row_fingerprint`   → G-5① 逐 row test fingerprint（sha256）
  `-k event_ids`         → G-5② 逐 event assignments／purged IDs（含 diff 輸出）
  `-k answer_window`     → G-5③ answer-window 完整性
  `-k leakage_negative`  → G-5④ 注入跨界事件必進 purged
  `-k independent_oracle`→ G-3b 新投影 vs 獨立 oracle
  `-k per_symbol`        → G-4 per-symbol counts
  `-k golden_compare`    → G-1 全組比對（失敗須**指名差在哪一筆**）
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "freeze_splitunify_golden.py"
GOLDEN = REPO / "tests" / "golden" / "splitunify" / "splitunify_golden.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    assert GOLDEN.exists(), f"golden 不存在：{GOLDEN}——首次請跑 `--write`"
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def compare_run() -> subprocess.CompletedProcess:
    """跑一次比對模式；三個「每次都驗」的檢查（G-3b／G-5④）也在裡面。"""
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=REPO, capture_output=True, text=True
    )


def test_golden_compare_is_clean(compare_run) -> None:
    """G-1 全組比對 rc=0；失敗時輸出**必須指名差在哪一筆**（不是只回布林）。"""
    assert compare_run.returncode == 0, (
        f"golden 比對失敗（rc={compare_run.returncode}）：\n{compare_run.stdout[-2000:]}"
    )
    assert "GOLDEN OK" in compare_run.stdout


def test_independent_oracle_agrees(compare_run) -> None:
    """G-3b：投影 vs **獨立** oracle 集合相等（oracle 逐行重寫規則，不呼叫被測函式）。"""
    assert "✓ G-3b" in compare_run.stdout, compare_run.stdout[-2000:]


def test_leakage_negative_case_blocks(compare_run) -> None:
    """G-5④：把 train 事件的 `label_end_ms` 推進 test 區 ⇒ **必進 purged**。

    正向全對但負例不擋，等於沒有 containment 保證——這條是 golden 的另一半。
    """
    assert "✓ G-5④" in compare_run.stdout, compare_run.stdout[-2000:]


def test_row_fingerprint_is_frozen(golden: dict) -> None:
    """G-5①：逐 row test fingerprint 之 sha256 已凍結且非空。"""
    assert len(golden["g5_row_fingerprint_sha256"]) == 64
    assert golden["g5_row_fingerprint_n"] > 0


def test_event_ids_three_states_are_disjoint_and_total(golden: dict) -> None:
    """G-5②：三態互斥且涵蓋全集（金檔自身之不變式——防「凍了一份壞的」）。"""
    m = golden["g1_membership"]
    tr, te, pu = set(m["train"]), set(m["test"]), set(m["purged"])
    assert tr & te == set() and tr & pu == set() and te & pu == set(), "三態必須互斥"
    assert len(tr) + len(te) + len(pu) == len(tr | te | pu), "不得有重複 event_id"
    assert pu, "fixture 必須含被 purge 的事件，否則 G-5④ 的負例無從對照"


def test_answer_window_completeness_recorded(golden: dict) -> None:
    """G-5③：test 段事件之 label 起點皆落在 universe 內（缺 endpoint 者不在此列）。"""
    assert isinstance(golden["g5_answer_window_complete"], list)
    assert set(golden["g5_answer_window_complete"]) <= set(golden["g1_membership"]["test"])


def test_per_symbol_counts_are_integers(golden: dict) -> None:
    """G-4：per-symbol counts 為**整數逐值**（非 atol 比較）。"""
    counts = golden["g4_per_symbol_n"]
    assert counts, "per_symbol_n 不得為空"
    assert all(isinstance(v, int) for v in counts.values())


def test_purge_reason_literal_is_contract_value(golden: dict) -> None:
    """purge reason 沿用既有契約字面，不得另造（SPEC C-3）。"""
    assert golden["purge_reasons"] == ["interval_crosses_split_boundary"]
