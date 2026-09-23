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


def _install_mutant(root: Path, injected: str) -> Path:
    """於沙箱核心 `if __name__` 前注入一段覆寫 `gen_block` 之碼，**寫回該沙箱之 scripts/**（核心以腳本同目錄解析
    註冊表；寫在沙箱外則讀不到縮放後之註冊表——r5 grok 實測 `REG_EXISTS False`）。回傳沙箱核心路徑。"""
    core = root / "scripts" / "_gen_fact_key_blocks.py"
    src = core.read_text(encoding="utf-8")
    assert src.count(MUTATION_ANCHOR) == 1, "核心 __main__ 錨點須恰一處"
    core.write_text(src.replace(MUTATION_ANCHOR, injected + "\n\n" + MUTATION_ANCHOR, 1), encoding="utf-8")
    return core


def _registry_keys(root: Path) -> List[str]:
    import json
    return [k for k in json.loads((root / "scripts" / "fact_keys.json").read_text(encoding="utf-8")) if k != "_schema"]


def _status_ids(root: Path) -> set:
    """狀態識別碼集合：`_schema.status_keys` 與 `docrot2_status_keys` 所指各表之第二欄。"""
    import json
    data = json.loads((root / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))
    sch = data["_schema"]
    return {row[1] for k in list(sch.get("status_keys", [])) + list(sch.get("docrot2_status_keys", []))
            for row in data.get(k, {}).get("rows", []) if len(row) > 1}


_PROBE_INJECTION = (
    "import os as _fkperf_os\n"
    "_fkperf_orig_gen_block = gen_block\n"
    "def gen_block(reg, key):  # FKPERF 探針：記錄每次呼叫之 key\n"
    "    with open(_fkperf_os.environ['FKPERF_PROBE'], 'a', encoding='utf-8') as _f:\n"
    "        _f.write(key + '\\n')\n"
    "    return _fkperf_orig_gen_block(reg, key)")


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


def test_measurement_helpers_raise_on_nonzero_rc(tmp_path: Path) -> None:
    """helper 自測（r5 三家 P1）：被量之呼叫 rc≠0 ⇒ 三支量測 helper 皆拋例外，不回傳可當「有限／不變」之數值。"""
    import subprocess
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "gen_fact_key_blocks.sh").write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    core = tmp_path / "scripts" / "_gen_fact_key_blocks.py"
    core.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    with pytest.raises(subprocess.CalledProcessError):
        sp.time_mode(tmp_path, "--check", 1)
    with pytest.raises(subprocess.CalledProcessError):
        sp.count_spawns(tmp_path, "--check")
    with pytest.raises(subprocess.CalledProcessError):
        op.count_opens(tmp_path, ["--check"], core)


# ---------------------------------------------------------------- 邊界（Task 0.2）

def test_boundary_19_scaled_key_names_match_key_pattern(tmp_path: Path) -> None:
    """Task 0.2 邊界①：10× 規模之合成 key 名稱皆合 `_schema.key_pattern`。"""
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["10x"])
    assert sp.verify_scaled_tree(root, C["scale_total_keys"]["10x"]) == []


def test_boundary_20_scaled_keys_do_not_collide(tmp_path: Path) -> None:
    """Task 0.2 邊界②：合成 key 不與既有 key 或狀態識別碼撞名（r5 codex P2：dict 之 key 恆不重複，須顯式比交集）。"""
    target = C["scale_total_keys"]["4x"]
    root = sp.build_scaled_tree(tmp_path, target)
    assert sp.verify_scaled_tree(root, target) == []
    keys = _registry_keys(root)
    assert len(keys) == target
    synth = set(keys) - set(_registry_keys(REPO))
    assert synth, "合成 key 集合為空"
    assert len(synth) == target - sp.total_key_count(REPO)
    assert not synth & _status_ids(root), sorted(synth & _status_ids(root))
    assert not synth & _status_ids(REPO), sorted(synth & _status_ids(REPO))


# ---------------------------------------------------------------- 邊界（Task 4.4）

def test_boundary_21_check_rc0_at_10x_and_40x(tmp_path: Path) -> None:
    """Task 4.4 邊界①：10× 與 40× 規模下 `--check` rc=0（經入口）。
    rc≠0 由 `time_mode` 拋例外即紅（r5 三家 P1）；10×／40× 以既有比例上限 `ratio_max × min(4×)` 為逾時，
    超線性實作停在此處即判紅而非掛住（不另訂秒數）。"""
    r4 = sp.build_scaled_tree(tmp_path / "4x", C["scale_total_keys"]["4x"])
    t4 = min(sp.time_mode(r4, "--check", 1))
    for label in ("10x", "40x"):
        root = sp.build_scaled_tree(tmp_path / label, C["scale_total_keys"][label])
        t = sp.time_mode(root, "--check", 1, timeout=C["ratio_max"] * t4)
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
    """Task 4.4 邊界③：每 key 多讀一次檔之 mutant ⇒ 開檔次數隨規模改變（不變性斷言會紅）。
    先證 mutant 確實打進每 key 迴圈：同一 4× 樹上 mutant 之開檔數須多於原核心（r5 codex P1-01）。"""
    injected = (
        "_fkperf_orig_gen_block = gen_block\n"
        "def gen_block(reg, key):  # FKPERF mutation：每 key 多讀一次檔\n"
        "    open(str(reg.path)).read()\n"
        "    return _fkperf_orig_gen_block(reg, key)")
    r4 = sp.build_scaled_tree(tmp_path / "4x", C["scale_total_keys"]["4x"])
    r10 = sp.build_scaled_tree(tmp_path / "10x", C["scale_total_keys"]["10x"])
    n4_orig = op.count_opens(r4, [], r4 / "scripts" / "_gen_fact_key_blocks.py")[0]
    m4, m10 = _install_mutant(r4, injected), _install_mutant(r10, injected)
    n4 = op.count_opens(r4, [], m4)[0]
    assert n4 > n4_orig, (n4, n4_orig)
    assert n4 != op.count_opens(r10, [], m10)[0]


def test_boundary_24_per_key_json_roundtrip_breaks_ratio(tmp_path: Path) -> None:
    """Task 4.4 邊界④：每 key 對整份註冊表做 JSON 往返之 mutant ⇒ 比例型耗時判否，且在逾時上限內判出。
    注入點打得到每 key 迴圈由 `test_gen_block_injection_reaches_every_key`（`--check` 在內）以行為證明。"""
    injected = (
        "import json as _fkperf_json\n"
        "_fkperf_orig_gen_block = gen_block\n"
        "def gen_block(reg, key):  # FKPERF mutation：每 key 對整份註冊表做 JSON 往返\n"
        "    _fkperf_json.loads(_fkperf_json.dumps(reg.data, ensure_ascii=False))\n"
        "    return _fkperf_orig_gen_block(reg, key)")
    r4 = sp.build_scaled_tree(tmp_path / "4x", C["scale_total_keys"]["4x"])
    r40 = sp.build_scaled_tree(tmp_path / "40x", C["scale_total_keys"]["40x"])
    for root in (r4, r40):
        _install_mutant(root, injected)
    assert _ratio_verdict(r4, r40, "--check") is False


def test_boundary_25_bad_synthesis_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4.4 邊界⑤：合成規則誤把非內容 key 一併複製 ⇒ 合規檢查先報錯。"""
    real = sp.content_keys()
    monkeypatch.setattr(sp, "content_keys", lambda: real + ["roadmap-status"])
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["4x"])
    assert sp.verify_scaled_tree(root, C["scale_total_keys"]["4x"]) != []


# ---------------------------------------------------------------- Task 4.4 驗證

@pytest.mark.parametrize("mode", ["emit", "--check", "--write"])
def test_gen_block_injection_reaches_every_key(tmp_path: Path, mode: str) -> None:
    """可測性契約（r5 三家 P1）：覆寫模組全域 `gen_block` 之探針，於三種渲染模式皆記錄到每個合成 key
    ⇒ 邊界 23／24 之 mutant 真的打進每 key 迴圈（核心若以別名／私有函式渲染，此處即紅）。
    直呼核心與經入口（`bash scripts/gen_fact_key_blocks.sh`）兩條路徑各跑一次、各自須記錄到每個合成 key，
    且兩次 stdout 相同（r7 codex P1-02：入口可設環境變數使核心改走私有渲染，只直呼時量不到）。"""
    import os
    import subprocess
    root = sp.build_scaled_tree(tmp_path, C["scale_total_keys"]["4x"])
    core = _install_mutant(root, _PROBE_INJECTION)
    args = [] if mode == "emit" else [mode]
    synth = set(_registry_keys(root)) - set(_registry_keys(REPO))
    assert synth
    outs = {}
    for path, argv in (("direct", ["python3", str(core), *args]),
                       ("entry", ["bash", "scripts/gen_fact_key_blocks.sh", *args])):
        probe = tmp_path / f"probe_{path}.txt"
        r = subprocess.run(argv, cwd=str(root), capture_output=True, env=dict(os.environ, FKPERF_PROBE=str(probe)))
        assert r.returncode == 0, (path, r.stderr.decode("utf-8", "replace"))
        called = set(probe.read_text(encoding="utf-8").splitlines()) if probe.exists() else set()
        assert synth <= called, (path, sorted(synth - called)[:5])
        outs[path] = r.stdout
    assert outs["direct"] == outs["entry"]


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
