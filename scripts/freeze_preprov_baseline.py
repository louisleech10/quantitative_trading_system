"""PRE-PROV 改前基準凍結（docs/FFDSTAR_SPEC.md §G「改前基準」）。

於改前生產碼態，對 §V 全格（`preprov_helpers.CELLS` × 各格標的）以真實 kline 短窗完整生成，取公開值指紋
（`preprov_helpers.value_fingerprints`：逐欄 float32 值 sha256、NaN 遮罩 sha256、dtype、欄名集合 sha256），
寫入 `tests/_golden/preprov/pre_change_fingerprints.json`。

用法：
  venv/bin/python scripts/freeze_preprov_baseline.py [--out PATH] [--work DIR]
寫入前檢查：momentum／api 受版控檔對 HEAD 無改動（含未追蹤 .py），否則拒寫（rc 2）——基準必須出自改前碼。
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests.feature_engineering import preprov_helpers as ph  # noqa: E402


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def _production_clean() -> bool:
    """momentum／api 對 HEAD 無追蹤改動、且無未追蹤 .py。"""
    diff = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD", "--", "momentum", "api",
                           ":(exclude,glob)**/__pycache__/**"])
    if diff.returncode != 0:
        return False
    untracked = _git("ls-files", "--others", "--exclude-standard", "--", "momentum", "api")
    return not any(line.endswith(".py") for line in untracked.splitlines())


def _kinds_with_files(handle: ph.RunHandle) -> list:
    artifacts = ph.load_manifest(handle.run_dir).get("artifacts", {})
    return [k for k in ("raw", "processed") if k in artifacts and (handle.run_dir / k).exists()]


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ph.PRE_CHANGE_FINGERPRINTS_PATH))
    parser.add_argument("--work", default=None, help="生成暫存根（預設系統暫存）")
    args = parser.parse_args(argv)

    if not _production_clean():
        print("REFUSE: momentum／api 對 HEAD 有改動或有未追蹤 .py；改前基準須出自改前碼", file=sys.stderr)
        return 2

    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="preprov_freeze_"))
    cells: Dict[str, Dict[str, Any]] = {}
    for cell in ph.CELLS:
        for symbol in ph.cell_symbols(cell):
            handle = ph.generate_short_run(work / f"{cell}_{symbol}", cell, symbol=symbol)
            kinds = _kinds_with_files(handle)
            if not kinds:
                print(f"REFUSE: {cell}/{symbol} 無可取指紋之 artifact", file=sys.stderr)
                return 1
            cells.setdefault(cell, {})[symbol] = {k: ph.value_fingerprints(handle.run_dir, k) for k in kinds}
            print(f"[freeze] {cell}/{symbol}: {', '.join(kinds)}", flush=True)

    payload = {
        "schema_version": 1,
        "command": " ".join(["venv/bin/python", "scripts/freeze_preprov_baseline.py", *(argv or sys.argv[1:])]),
        "exit_code": 0,
        "head": _git("rev-parse", "HEAD").strip(),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "cells": cells,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[freeze] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
