"""FKPERF 規模探針（docs/FKPERF_SPEC.md Task 0.2、4.4）。

外部程序計數：PATH shim（工具集合同 handoffs/run_receipts/fkperf_probes/prof_spawn.sh 另加 bash），
shim 以真實路徑 exec，不得對 builtin 名稱建 shim（r1 grok 實測 printf shim 會使 emit 早退）。
合成規模註冊表：規模以總 fact-key 數定義（tests/governance/fixtures/fkperf_scale_contract.json）。
"""
from __future__ import annotations

import copy
import datetime as _dt
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from tests.governance import _fkperf_oracle as fo

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "tests" / "governance" / "fixtures" / "fkperf_scale_contract.json"
_DECL = REPO / "docs" / "GOV_B25_SCOPE_AMENDMENT.md"
_DECL_RE = re.compile(r"^FACTKEY-CONTENT: (\S+)$", re.M)
_SYNTH_RE = re.compile(r"^(?P<base>.+)-x(?P<n>[0-9]+)$")
# 外部工具（prof_spawn.sh 之集合去掉 builtin 名 printf，另加 bash）
_SHIM_TOOLS = ("bash", "jq", "awk", "sort", "grep", "sed", "git", "tr", "cut", "wc", "head", "tail", "shasum",
               "python3", "cat", "mktemp", "comm", "uniq", "basename", "dirname", "realpath", "stat", "find")


def load_contract() -> dict:
    """讀規模驗收規則（量測點、門檻、次數之單一落點）。"""
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _declared_content() -> List[str]:
    return sorted(_DECL_RE.findall(_DECL.read_text(encoding="utf-8")))


def content_keys() -> List[str]:
    """`docs/GOV_B25_SCOPE_AMENDMENT.md` 之 FACTKEY-CONTENT 宣告集合（jq keys[] 序＝碼點序）。"""
    return _declared_content()


def _registry(root: Path) -> dict:
    return json.loads((root / fo.REG_REL).read_text(encoding="utf-8"))


def total_key_count(root: Path) -> int:
    """沙箱註冊表之總 fact-key 數（排除 `_schema`）。"""
    return sum(1 for k in _registry(root) if k != "_schema")


def build_scaled_tree(tmp_path: Path, total_keys: int) -> Path:
    """建總 fact-key 數恰為 `total_keys` 之合成沙箱樹：以目前工作樹為底，只複製純內容 key 並改名為
    `<key>-x<n>`（整份複製不足之餘數依 keys[] 序取前 k 個補足），宿主補空生成區塊後以入口 `--write` 物化。"""
    root = tmp_path / "tree"
    fo.build_current_tree(root)
    reg = _registry(root)
    base = [k for k in reg if k != "_schema"]
    need = total_keys - len(base)
    assert need >= 0, (total_keys, len(base))
    src = content_keys()
    blocks: Dict[str, List[str]] = {}
    n = 0
    while need > 0:
        n += 1
        for k in src[:need]:
            new = f"{k}-x{n}"
            reg[new] = copy.deepcopy(reg[k])
            for t in (reg[k]["target"] if isinstance(reg[k]["target"], list) else [reg[k]["target"]]):
                blocks.setdefault(t, []).append(new)
        need -= len(src[:need])
    (root / fo.REG_REL).write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for rel, keys in blocks.items():
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8") + "".join(
            f"\n<!-- BEGIN GENERATED: {k} -->\n<!-- END GENERATED: {k} -->\n" for k in keys), encoding="utf-8")
    r = subprocess.run(["bash", fo.ENTRY_REL, "--write"], cwd=str(root), capture_output=True)
    if r.returncode != 0:
        raise subprocess.CalledProcessError(r.returncode, r.args, r.stdout, r.stderr)
    return root


def _status_ids(reg: dict) -> set:
    sch = reg.get("_schema", {})
    return {row[1] for k in list(sch.get("status_keys", [])) + list(sch.get("docrot2_status_keys", []))
            for row in reg.get(k, {}).get("rows", []) if len(row) > 1}


def verify_scaled_tree(root: Path, target_total: int) -> List[str]:
    """合成樹之合規問題清單（空＝合規）：總數≠目標、複製了非內容 key、改名後 key 不合 `_schema.key_pattern`、
    與既有 key 或狀態識別碼撞名。宣告集合直接讀宣告檔（不經 `content_keys()`，使其被改壞時仍抓得到）。"""
    reg = _registry(root)
    real = json.loads((REPO / fo.REG_REL).read_text(encoding="utf-8"))
    keys = [k for k in reg if k != "_schema"]
    problems: List[str] = []
    if len(keys) != target_total:
        problems.append(f"總數 {len(keys)} ≠ 目標 {target_total}")
    declared = set(_declared_content())
    pattern = re.compile(reg["_schema"].get("key_pattern", "^[a-z0-9][a-z0-9-]*$"))
    synth = [k for k in keys if k not in real]
    ids = _status_ids(reg) | _status_ids(real)
    for k in synth:
        m = _SYNTH_RE.match(k)
        if not m or m.group("base") not in declared:
            problems.append(f"{k}：非純內容 key 之複本")
        if not pattern.match(k):
            problems.append(f"{k}：不合 key_pattern")
        if k in ids:
            problems.append(f"{k}：與狀態識別碼撞名")
    return problems


def _shim_dir(log: Path) -> Path:
    d = Path(tempfile.mkdtemp(prefix="fkperf_shim_"))
    for tool in _SHIM_TOOLS:
        real = shutil.which(tool)
        if not real:
            continue
        (d / tool).write_text(f'#!/bin/sh\necho {tool} >> "{log}"\nexec "{real}" "$@"\n', encoding="utf-8")
        (d / tool).chmod(0o755)
    return d


def count_spawns_cmd(argv: Sequence[str], cwd: Path) -> Tuple[int, Dict[str, int]]:
    """對任意指令以同一 PATH shim 計外部程序數（helper 自測用）；頂層指令以真實路徑啟動、不計入。
    量測範圍＝經 PATH 解析之命令；以絕對路徑啟動者不計（r1 codex P2-05）——oracle 無絕對路徑呼叫（見
    `test_oracle_has_no_absolute_path_command`），核心側之全部子程序另以 `_fkperf_opens.count_core_spawns` 計。
    被量之呼叫 rc≠0 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗之路徑不得充當「與規模無關」；r5 三家 P1）。"""
    with tempfile.TemporaryDirectory() as t:
        log = Path(t) / "spawn.log"
        log.write_text("", encoding="utf-8")
        shim = _shim_dir(log)
        try:
            top = shutil.which(argv[0]) or argv[0]
            env = dict(os.environ, PATH=f"{shim}{os.pathsep}{os.environ.get('PATH', '')}")
            r = subprocess.run([top, *argv[1:]], cwd=str(cwd), capture_output=True, env=env)
        finally:
            shutil.rmtree(shim, ignore_errors=True)
        if r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, list(argv), r.stdout, r.stderr)
        by: Dict[str, int] = {}
        for line in log.read_text(encoding="utf-8").split():
            by[line] = by.get(line, 0) + 1
        return sum(by.values()), by


def _mode_argv(mode: str) -> List[str]:
    if mode == "emit":
        return ["bash", fo.ENTRY_REL]
    if mode == "guard":
        return ["bash", "scripts/factkey_write_guard.sh", "HANDOFF.md"]
    if mode == "--status-hits":
        return ["bash", fo.ENTRY_REL, "--status-hits", "lines.txt"]
    return ["bash", fo.ENTRY_REL, mode]


def count_spawns(root: Path, mode: str) -> Tuple[int, Dict[str, int]]:
    """以 PATH shim 計 `mode`（emit／--check／--write／--status-hits／guard）之外部程序數。
    被量之呼叫 rc≠0 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗之路徑不得充當「與規模無關」；r5 三家 P1）。"""
    return count_spawns_cmd(_mode_argv(mode), root)


def time_mode(root: Path, mode: str, trials: int, timeout: float = 0.0) -> List[float]:
    """量 `mode` 之牆鐘耗時 `trials` 次；`timeout`>0 時單次逾時即回傳 inf（逾時之那次不看 rc）。
    逾時須先殺死該次子程序再回傳（`subprocess.run(timeout=…)`；入口以 `exec python3` 使核心即為該子程序，
    否則未 exec 之孫程序於逾時後續跑、與下一次計時疊加；r6 grok P2-04 實測）。
    未逾時而 rc≠0 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗不得充當「耗時有限」；r5 三家 P1）。"""
    argv = _mode_argv(mode)
    out: List[float] = []
    for _ in range(trials):
        t0 = time.perf_counter()
        try:
            r = subprocess.run(argv, cwd=str(root), capture_output=True, timeout=timeout if timeout > 0 else None)
        except subprocess.TimeoutExpired:
            out.append(math.inf)
            continue
        dt = time.perf_counter() - t0
        if r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, argv, r.stdout, r.stderr)
        out.append(dt)
    return out


def write_receipt(rows: Sequence[dict], name: str) -> Path:
    """耗時與程序數收據寫入 `handoffs/run_receipts/<日期>-<name>.json`。"""
    p = REPO / "handoffs" / "run_receipts" / f"{_dt.date.today():%Y%m%d}-{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema_version": 1, "command": " ".join(sys.argv), "exit_code": 0,
                             "rows": list(rows)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p
