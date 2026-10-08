"""FRAMEPATH Task 1.4 前置：於 HEAD 6e07e0ad 計算三檔之既有死碼集合（`HEAD_DEAD` 凍結值之產生方式）。

以 `git ls-tree`／`git cat-file` 讀 HEAD 版全部 momentum／api／scripts／tests 之 .py（不讀工作樹，避免 TODO 階段
新增之測試檔字串常數影響引用數），呼叫 `tests/feature_engineering/test_framepath_cgsa_only.dead_defs`
（與驗收同一函式）；結果寫 `--out` JSON 收據並印出排序後之 qualname。

用法：PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/dead_scan_head.py --out <收據>
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

HEAD = "6e07e0ad"
SCAN = (
    "momentum/FeatureEngineering/feature_factory.py",
    "momentum/FeatureEngineering/timeframe/multi_tf_generator.py",
    "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py",
)
REF_ROOTS = ("momentum", "api", "scripts", "tests")


def _dead_defs():
    # 只取函式本體（不 import 測試模組本身之 pytest 依賴鏈以外之東西）：以 AST 抽出同名函式定義執行
    src = (REPO / "tests/feature_engineering/test_framepath_cgsa_only.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = {"_defs", "_referenced_names", "dead_defs"}
    mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in keep], type_ignores=[])
    ns = {"ast": ast}
    from typing import Dict, Iterable, List, Set, Tuple  # noqa: F401
    ns.update({"Dict": Dict, "Iterable": Iterable, "List": List, "Set": Set, "Tuple": Tuple})
    exec(compile(mod, "test_framepath_cgsa_only.py", "exec"), ns)
    return ns["dead_defs"]


def head_sources(roots):
    names = subprocess.run(["git", "ls-tree", "-r", "--name-only", HEAD, "--", *roots], cwd=REPO,
                           capture_output=True, text=True, check=True).stdout.split()
    out = []
    for n in names:
        if n.endswith(".py"):
            blob = subprocess.run(["git", "cat-file", "blob", f"{HEAD}:{n}"], cwd=REPO, capture_output=True, check=True).stdout
            out.append((n, blob.decode("utf-8", "replace")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    dead_defs = _dead_defs()
    scan = [(p, subprocess.run(["git", "cat-file", "blob", f"{HEAD}:{p}"], cwd=REPO, capture_output=True,
                                check=True).stdout.decode("utf-8")) for p in SCAN]
    refs = head_sources(REF_ROOTS)
    dead = sorted(dead_defs(scan, refs))
    receipt = {"schema_version": 1, "command": " ".join(sys.argv), "exit_code": 0, "head": HEAD,
               "scan_files": list(SCAN), "ref_roots": list(REF_ROOTS), "ref_file_count": len(refs),
               "head_dead": dead}
    Path(args.out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(dead))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
