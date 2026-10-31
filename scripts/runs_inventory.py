#!/usr/bin/env python3
"""repo 內 `runs/`（驗證／量測之中間工作目錄，`.gitignore` 之 `runs/`）列表（SPEC docs/ICPERF_SPEC.md v5.45 §G (2) ②）。

只列、不刪（使用者 2026-10-31：刪除權在使用者，清理腳本自動刪不核准）。每個工作目錄應有說明卡 `README.txt`
（`scripts/icperf_freeze_baseline.py` `new_work_root` 建立時寫入：入口、用途、建立時間、git HEAD、何時可刪）；
無說明卡者列「無說明卡」。`--rm-cmd` 另印刪除命令供使用者自行執行——本地有未推送提交或 handoffs/run_receipts/ 有未提交
變更時不印（結果尚未存妥）。

用法：venv/bin/python scripts/runs_inventory.py [--rm-cmd]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "runs"
CARD = "README.txt"
#: 說明卡最深之位置（runs/<批次>/<工作目錄>/README.txt）
MAX_DEPTH = 3


def _size(path: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for fn in files:
            try:
                total += os.lstat(os.path.join(dirpath, fn)).st_size
            except OSError:
                pass
    return total


def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


def _card(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (path / CARD).read_text(encoding="utf-8").splitlines():
        key, sep, val = line.partition("：")
        if sep:
            out[key.strip()] = val.strip()
    return out


def entries(runs: Path = RUNS) -> List[Dict[str, object]]:
    """有說明卡之目錄（深度 ≤ MAX_DEPTH，找到即不再往下）與 runs/ 下無任何說明卡之第一層目錄。"""
    found: List[Dict[str, object]] = []
    if not runs.is_dir():
        return found

    def walk(d: Path, depth: int) -> bool:
        if (d / CARD).is_file() and d != runs:
            found.append({"path": d, "card": _card(d), "size": _size(d)})
            return True
        if depth >= MAX_DEPTH:
            return False
        hit = False
        for child in sorted(p for p in d.iterdir() if p.is_dir() and not p.is_symlink()):
            hit = walk(child, depth + 1) or hit
        return hit

    for top in sorted(p for p in runs.iterdir() if p.is_dir() and not p.is_symlink()):
        if not walk(top, 1):
            found.append({"path": top, "card": None, "size": _size(top)})
    return found


def unsaved_reason(repo: Path = REPO) -> Optional[str]:
    """結果尚未存妥之理由（未推送提交、收據未提交）；皆無 ⇒ None。"""
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()

    if git("rev-list", "--count", "@{u}..HEAD") not in ("", "0"):
        return "本地有未推送之提交"
    if git("status", "--porcelain", "--", "handoffs/run_receipts"):
        return "handoffs/run_receipts/ 有未提交之變更"
    return None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rm-cmd", action="store_true", help="另印刪除命令（結果已存妥時）")
    args = ap.parse_args(argv)
    rows = entries()
    if not rows:
        print("runs/ 無工作目錄")
        return 0
    for r in rows:
        rel = Path(r["path"]).relative_to(REPO)
        card = r["card"]
        print(f"{rel}  [{_human(int(r['size']))}]")
        if card is None:
            print("    無說明卡")
            continue
        for key in ("入口", "用途", "建立", "git HEAD", "何時可刪"):
            if key in card:
                print(f"    {key}：{card[key]}")
    print(f"合計 {_human(sum(int(r['size']) for r in rows))}")
    if args.rm_cmd:
        why = unsaved_reason()
        if why:
            print(f"不印刪除命令：{why}")
            return 1
        print("刪除命令（請自行確認上列用途後執行）：")
        print("rm -rf " + " ".join(str(Path(r["path"]).relative_to(REPO)) for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
