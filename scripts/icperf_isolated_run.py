"""ICPERF SPEC §G ①（v5.48）：於固定提交之 git worktree 副本執行凍結腳本之重型子命令。

步驟：
1. `--commit` 解析為完整 sha；副本＝`runs/<batch>/wt-<sha12>/`（不存在 ⇒ `git worktree add --detach`；已存在 ⇒ 其 HEAD
   須等於該 sha）。
2. 唯讀輸入（清單取副本之凍結腳本 `isolated-inputs`，單一來源 `ISOLATED_INPUTS`）以 symlink 自主 repo 引入副本之同
   相對路徑（已存在者須為指向同一目錄之 symlink）。
3. 跑前對唯讀輸入逐檔內容 sha256（symlink 目錄不被凍結快照走訪，故以此驗證未被寫入；不宣稱快照可偵測）。
4. 以本行程之直譯器、cwd＝副本、環境變數 `ICPERF_ISOLATED_COMMIT`＝sha 執行（本執行器由外層 `scripts/run_watched.py`
   包裝監看）副本之 `scripts/icperf_freeze_baseline.py <子命令與參數>`——程式碼自副本載入、§G (b) 之 `<repo>` 根＝副本；凍結腳本
   本身另以 `isolation_problems` 拒絕非副本執行。
5. 跑後再算一次；寫收據（宣告提交、副本跑前跑後 HEAD、命令、rc、唯讀輸入逐目錄摘要與差異）。
   合格＝rc 0、唯讀輸入未變、HEAD 前後皆等於宣告提交；否則 rc≠0。

用法（重型：列 `scripts/heavy_commands.json` wrapped 類，須背景、經 run_watched 並先寫估時收據；`-- isolation-check`
為秒級例外）：
  venv/bin/python scripts/run_watched.py --log <log> -- venv/bin/python scripts/icperf_isolated_run.py --commit HEAD --batch icperf/<批次> --receipt <收據 JSON> -- \\
      freeze --out $PWD/tests/_golden/icperf/pre_change.json.gz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

MAIN = Path(__file__).resolve().parents[1]
FREEZE_SCRIPT = "scripts/icperf_freeze_baseline.py"
COMMIT_ENV = "ICPERF_ISOLATED_COMMIT"
_CHUNK = 1 << 20


class IsolationError(RuntimeError):
    """副本建立、唯讀輸入引入或宣告提交不符。"""


def _git(*args: str, cwd: Path = MAIN) -> str:
    res = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise IsolationError(f"git {' '.join(args)} 失敗：{res.stderr.strip()}")
    return res.stdout.strip()


def worktree_path(sha: str, batch: str) -> Path:
    """`runs/<batch>/wt-<sha12>`；batch 須為不含 `..` 之相對路徑。"""
    b = Path(batch)
    if b.is_absolute() or ".." in b.parts or not b.parts:
        raise IsolationError(f"--batch 須為 runs/ 下之相對路徑：{batch}")
    return MAIN / "runs" / b / f"wt-{sha[:12]}"


def ensure_worktree(sha: str, wt: Path) -> None:
    if wt.exists():
        head = _git("rev-parse", "HEAD", cwd=wt)
        if head != sha:
            raise IsolationError(f"既有副本 {wt} 之 HEAD {head} ≠ 宣告提交 {sha}")
        return
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", "--detach", str(wt), sha)


def isolated_inputs(wt: Path) -> List[str]:
    res = subprocess.run([sys.executable, str(wt / FREEZE_SCRIPT), "isolated-inputs"], cwd=str(wt),
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise IsolationError(f"副本凍結腳本 isolated-inputs 失敗：{res.stderr.strip()[-500:]}")
    return list(json.loads(res.stdout))


def link_inputs(wt: Path, rels: Sequence[str]) -> None:
    for rel in rels:
        src, dst = MAIN / rel, wt / rel
        if not src.is_dir() or src.is_symlink():
            raise IsolationError(f"主 repo 唯讀輸入 {rel} 不存在或非實體目錄")
        if dst.is_symlink():
            if dst.resolve() != src.resolve():
                raise IsolationError(f"副本 {rel} 已指向 {dst.resolve()}，非 {src.resolve()}")
            continue
        if dst.exists():
            raise IsolationError(f"副本 {rel} 已存在且非 symlink")
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(src.resolve()), str(dst))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_inputs(rels: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """{輸入相對路徑: {檔相對路徑: 內容 sha256}}；走訪主 repo 實體目錄（不跟隨其下 symlink 目錄；symlink 檔取目標內容）。"""
    out: Dict[str, Dict[str, str]] = {}
    for rel in rels:
        root = MAIN / rel
        files: Dict[str, str] = {}
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                full = Path(dirpath) / fn
                files[str(full.relative_to(root))] = _sha256(full) if full.is_file() else "<非檔>"
        out[rel] = dict(sorted(files.items()))
    return out


def diff_digests(pre: Mapping[str, Mapping[str, str]], post: Mapping[str, Mapping[str, str]]) -> List[str]:
    changes: List[str] = []
    for rel in sorted(set(pre) | set(post)):
        a, b = pre.get(rel, {}), post.get(rel, {})
        for f in sorted(set(a) | set(b)):
            if f not in b:
                changes.append(f"刪除 {rel}/{f}")
            elif f not in a:
                changes.append(f"新增 {rel}/{f}")
            elif a[f] != b[f]:
                changes.append(f"改變 {rel}/{f}")
    return changes


def _summary(d: Mapping[str, Mapping[str, str]]) -> Dict[str, Any]:
    return {rel: {"n_files": len(files),
                  "sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}
            for rel, files in d.items()}


def run_child(cmd: List[str], *, wt: Path, sha: str) -> int:
    """執行副本凍結腳本（cwd＝副本、`COMMIT_ENV`＝sha；輸出直通）；回 rc。共用監看由外層 `scripts/run_watched.py`
    包裝（`heavy_commands.json` wrapped 類，監看整個子行程樹）；凍結腳本之重型子行程另經其自身 `run_watched`。"""
    return subprocess.run(cmd, cwd=str(wt), env={**os.environ, COMMIT_ENV: sha}).returncode


def run(commit: str, batch: str, receipt: Path, freeze_args: Sequence[str]) -> int:
    if not freeze_args:
        raise IsolationError("-- 之後須給凍結腳本子命令")
    sha = _git("rev-parse", "--verify", f"{commit}^{{commit}}")
    wt = worktree_path(sha, batch)
    ensure_worktree(sha, wt)
    head_before = _git("rev-parse", "HEAD", cwd=wt)
    rels = isolated_inputs(wt)
    link_inputs(wt, rels)
    started = time.time()
    pre = digest_inputs(rels)
    cmd = [sys.executable, str(wt / FREEZE_SCRIPT), *freeze_args]
    receipt = Path(receipt).resolve()
    rc = run_child(cmd, wt=wt, sha=sha)
    post = digest_inputs(rels)
    head_after = _git("rev-parse", "HEAD", cwd=wt)
    changes = diff_digests(pre, post)
    ok = rc == 0 and not changes and head_before == sha and head_after == sha
    rec = {"schema": "icperf-isolated-run/1", "spec": "docs/ICPERF_SPEC.md §G ①", "commit": sha,
           "worktree": str(wt), "head_before": head_before, "head_after": head_after,
           "argv": [os.path.relpath(c, wt) if c.startswith(str(wt)) else c for c in cmd], "rc": rc,
           "inputs": _summary(pre), "inputs_unchanged": not changes, "input_changes": changes[:200],
           "n_input_changes": len(changes), "seconds": round(time.time() - started, 1),
           "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pass": ok}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("commit", "worktree", "rc", "inputs_unchanged", "n_input_changes", "pass")},
                     ensure_ascii=False))
    return 0 if ok else (rc or 1)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("用法：icperf_isolated_run.py --commit <rev> --batch <runs 下相對路徑> --receipt <JSON> -- <子命令…>",
              file=sys.stderr)
        return 2
    i = argv.index("--")
    p = argparse.ArgumentParser(prog="icperf_isolated_run.py", description=__doc__.split("\n")[0])
    p.add_argument("--commit", required=True)
    p.add_argument("--batch", required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args(argv[:i])
    try:
        return run(args.commit, args.batch, args.receipt, argv[i + 1:])
    except IsolationError as exc:
        print(f"IsolationError：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
