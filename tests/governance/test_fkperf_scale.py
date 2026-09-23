"""FKPERF 規模驗收（docs/FKPERF_SPEC.md C-6、Task 0.2、Task 4.4）。

規模一律以總 fact-key 數定義；量測點、門檻、次數之單一落點＝tests/governance/fixtures/fkperf_scale_contract.json。
比例型耗時：`min(40× 三次) <= 20 * min(4× 三次)`（使用者 2026-09-23 裁定；端點經白話審閱確認）。
實作前本檔應為紅（helper 與核心皆為空殼）。
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import List

import pytest

from tests.governance import _fkperf_opens as op
from tests.governance import _fkperf_spawn as sp

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "scripts" / "_gen_fact_key_blocks.py"
C = sp.load_contract()
MUTATION_ANCHOR = 'if __name__ == "__main__":'


def _targets() -> dict:
    t = dict(C["scale_total_keys"])
    t["1x"] = sp.total_key_count(REPO)
    return t


def _ratio_verdict(root4: Path, root40: Path, mode: str) -> bool:
    """比例型耗時判定：40× 端以 20 × min(4×) 為逾時上限，逾時即判否。"""
    t4 = min(sp.time_mode(root4, mode, C["trials"]))
    t40 = sp.time_mode(root40, mode, C["trials"], timeout=C["ratio_max"] * t4)
    return math.isfinite(min(t40)) and min(t40) <= C["ratio_max"] * t4


def _mutated_core(tmp_path: Path, injected: str) -> Path:
    """於核心 `if __name__` 前注入一段覆寫 `gen_block` 之碼，產生 mutant 核心檔。"""
    src = CORE.read_text(encoding="utf-8")
    assert src.count(MUTATION_ANCHOR) == 1, "核心 __main__ 錨點須恰一處"
    mutant = tmp_path / "_gen_fact_key_blocks_mutant.py"
    mutant.write_text(src.replace(MUTATION_ANCHOR, injected + "\n\n" + MUTATION_ANCHOR, 1), encoding="utf-8")
    return mutant


# ---------------------------------------------------------------- 規則檔與 helper 自測（Task 0.2 驗證①）

def test_contract_ratio_pair_is_exactly_tenfold() -> None:
    """C-6 ②：比例兩端之總 fact-key 數恰相差 10 倍（使用者裁定之規模差）。"""
    a, b = C["ratio_pair"]
    assert C["scale_total_keys"][b] == C["ratio_required_scale_factor"] * C["scale_total_keys"][a]


def test_spawn_counter_counts_known_calls(tmp_path: Path) -> None:
    """Task 0.2 驗證①：shim 計數等於已知呼叫次數（小腳本呼叫 jq 三次、awk 兩次）。"""
    script = tmp_path / "probe.sh"
    script.write_text("jq -n 1 >/dev/null; jq -n 2 >/dev/null; jq -n 3 >/dev/null; awk 'BEGIN{}'; awk 'BEGIN{}'\n", encoding="utf-8")
    total, by = sp.count_spawns_cmd(["bash", str(script)], tmp_path)
    assert by.get("jq") == 3 and by.get("awk") == 2 and total == 5


def test_open_counter_counts_known_opens(tmp_path: Path) -> None:
    """Task 0.2 驗證①：開檔計數等於已知開檔數（小腳本在 ROOT 下開兩個檔）。"""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    script = tmp_path / "probe.py"
    script.write_text("open('a.txt').read(); open('b.txt').read()\n", encoding="utf-8")
    n, paths = op.count_opens(tmp_path, [], script)
    assert n == 2, paths


# ---------------------------------------------------------------- 邊界（Task 0.2）

def test_boundary_19_scaled_key_names_match_key_pattern(tmp_path: Path) -> None:
    """Task 0.2 邊界①：10× 規模之合成 key 名稱皆合 `_schema.key_pattern`。"""
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["10x"])
    assert sp.verify_scaled_tree(root, C["scale_total_keys"]["10x"]) == []


def test_boundary_20_scaled_keys_do_not_collide(tmp_path: Path) -> None:
    """Task 0.2 邊界②：合成 key 不與既有 key 或狀態識別碼撞名（總數恰等於目標，集合無重複）。"""
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["4x"])
    import json
    data = json.loads((root / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))
    keys = [k for k in data if k != "_schema"]
    assert len(keys) == len(set(keys)) == C["scale_total_keys"]["4x"]


# ---------------------------------------------------------------- 邊界（Task 4.4）

def test_boundary_21_check_rc0_at_10x_and_40x(tmp_path: Path) -> None:
    """Task 4.4 邊界①：10× 與 40× 規模下 `--check` rc=0（經入口）。"""
    for label in ("10x", "40x"):
        root = sp.build_scaled_tree(tmp_path / label, C["scale_total_keys"][label])
        t = sp.time_mode(root, "--check", 1)
        assert math.isfinite(t[0]), label


def test_boundary_22_synthetic_registry_stays_in_tmp(tmp_path: Path) -> None:
    """Task 4.4 邊界②：合成註冊表只在 tmp 沙箱內；真實註冊表位元組不變，合成 key 不在宣告檔。"""
    real = REPO / "scripts" / "fact_keys.json"
    before = hashlib.sha256(real.read_bytes()).hexdigest()
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["4x"])
    assert hashlib.sha256(real.read_bytes()).hexdigest() == before
    assert root.resolve() != REPO.resolve()
    declared = (REPO / "docs" / "GOV_B25_SCOPE_AMENDMENT.md").read_text(encoding="utf-8")
    import json
    synth = set(json.loads((root / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))) - set(
        json.loads(real.read_text(encoding="utf-8")))
    assert synth and not any(re.search(rf"^FACTKEY-[A-Z0-9-]+: {re.escape(k)}$", declared, re.M) for k in synth)


def test_boundary_23_per_key_extra_read_breaks_open_invariance(tmp_path: Path) -> None:
    """Task 4.4 邊界③：每 key 多讀一次檔之 mutant ⇒ 開檔次數隨規模改變（不變性斷言會紅）。"""
    mutant = _mutated_core(tmp_path, (
        "_fkperf_orig_gen_block = gen_block\n"
        "def gen_block(reg, key):  # FKPERF mutation：每 key 多讀一次檔\n"
        "    open(str(reg.path)).read()\n"
        "    return _fkperf_orig_gen_block(reg, key)"))
    r4 = sp.build_scaled_tree(tmp_path / "4x", C["scale_total_keys"]["4x"])
    r10 = sp.build_scaled_tree(tmp_path / "10x", C["scale_total_keys"]["10x"])
    assert op.count_opens(r4, [], mutant)[0] != op.count_opens(r10, [], mutant)[0]


def test_boundary_24_per_key_json_roundtrip_breaks_ratio(tmp_path: Path) -> None:
    """Task 4.4 邊界④：每 key 對整份註冊表做 JSON 往返之 mutant ⇒ 比例型耗時判否，且在逾時上限內判出。"""
    mutant = _mutated_core(tmp_path, (
        "import json as _fkperf_json\n"
        "_fkperf_orig_gen_block = gen_block\n"
        "def gen_block(reg, key):  # FKPERF mutation：每 key 對整份註冊表做 JSON 往返\n"
        "    _fkperf_json.loads(_fkperf_json.dumps(reg.data, ensure_ascii=False))\n"
        "    return _fkperf_orig_gen_block(reg, key)"))
    r4 = sp.build_scaled_tree(tmp_path / "4x", C["scale_total_keys"]["4x"])
    r40 = sp.build_scaled_tree(tmp_path / "40x", C["scale_total_keys"]["40x"])
    for root in (r4, r40):
        (root / "scripts" / "_gen_fact_key_blocks.py").write_bytes(mutant.read_bytes())
    assert _ratio_verdict(r4, r40, "--check") is False


def test_boundary_25_bad_synthesis_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.4 邊界⑤：合成規則誤把非內容 key 一併複製 ⇒ 合規檢查先報錯。"""
    real = sp.content_keys()
    monkeypatch.setattr(sp, "content_keys", lambda: real + ["roadmap-status"])
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["4x"])
    assert sp.verify_scaled_tree(root, C["scale_total_keys"]["4x"]) != []


# ---------------------------------------------------------------- Task 4.4 驗證

@pytest.mark.parametrize("mode", C["invariance_modes"])
def test_spawn_and_open_counts_scale_invariant(tmp_path: Path, mode: str) -> None:
    """Task 4.4 驗證：四模式之外部程序數與核心開檔次數，在 1×／4×／10×／40× 皆相等。"""
    targets = _targets()
    spawns, opens = set(), set()
    args = {"emit": [], "--status-hits": ["--status-hits", "lines.txt"]}.get(mode, [mode])
    for label in C["post_cutover_scales"]:
        root = sp.build_scaled_tree(tmp_path / label, targets[label])
        (root / "lines.txt").write_text("L1\tHP-FKPERF 已完成\n", encoding="utf-8")
        spawns.add(sp.count_spawns(root, mode)[0])
        opens.add(op.count_opens(root, args, root / "scripts" / "_gen_fact_key_blocks.py")[0])
    assert len(spawns) == 1, spawns
    assert len(opens) == 1, opens


@pytest.mark.parametrize("mode", C["ratio_modes"])
def test_ratio_40x_within_20x_of_4x(tmp_path: Path, mode: str) -> None:
    """Task 4.4 驗證／C-6 ②：`min(40× 三次) <= 20 * min(4× 三次)`。"""
    r4 = sp.build_scaled_tree(tmp_path / "4x", C["scale_total_keys"]["4x"])
    r40 = sp.build_scaled_tree(tmp_path / "40x", C["scale_total_keys"]["40x"])
    assert _ratio_verdict(r4, r40, mode)


def test_guard_spawns_scale_invariant(tmp_path: Path) -> None:
    """Task 4.4 驗證：`factkey_write_guard.sh HANDOFF.md` 之外部程序數與規模無關。"""
    counts = set()
    for label in ("4x", "10x"):
        root = sp.build_scaled_tree(tmp_path / label, C["scale_total_keys"][label])
        counts.add(sp.count_spawns(root, "guard")[0])
    assert len(counts) == 1, counts


def test_mutation_ratio_verdict_flags_superlinear(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """鑑別力：把耗時量測換成超線性假資料（40× 為 4× 之 50 倍）⇒ 比例判定必為否。"""
    def fake(root: Path, mode: str, trials: int, timeout: float = 0.0) -> List[float]:
        t = 50.0 if root.name == "40x" else 1.0
        return [t if not timeout or t <= timeout else math.inf] * trials
    monkeypatch.setattr(sp, "time_mode", fake)
    (tmp_path / "4x").mkdir()
    (tmp_path / "40x").mkdir()
    assert _ratio_verdict(tmp_path / "4x", tmp_path / "40x", "--check") is False
