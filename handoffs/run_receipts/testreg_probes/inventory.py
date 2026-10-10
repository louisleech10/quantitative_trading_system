"""TESTREG 前期盤點（輕量、唯讀）：tests/ 下每個 test_*.py 之靜態事實，供委員諮詢 r1 使用。

每檔：測試函式數（含類別方法；參數化不展開）、標記（requires_kline／slow／timeout 等）、是否引用真實 kline、
匯入之生產模組、最後修改日、提交次數、首次加入日、所屬目錄；另彙整目錄層統計。不執行任何測試。
用法：venv/bin/python handoffs/run_receipts/testreg_probes/inventory.py <out.json>
"""
import ast
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def git(*args):
    return subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(REPO), *args], capture_output=True,
                          text=True).stdout


def scan(path: Path):
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return {"syntax_error": str(exc)}
    tests, markers, prod = 0, Counter(), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            tests += 1
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) \
                and getattr(node.value, "attr", "") == "mark":
            markers[node.attr] += 1
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in ("momentum", "api"):
            prod.add(".".join(node.module.split(".")[:3]))
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in ("momentum", "api"):
                    prod.add(".".join(a.name.split(".")[:3]))
    return {"tests": tests, "markers": dict(markers), "prod_modules": sorted(prod),
            "real_kline": "kline_cache" in src or "requires_kline" in src, "lines": src.count("\n") + 1}


def main(out: str) -> int:
    files = sorted(p for p in (REPO / "tests").rglob("test_*.py") if "__pycache__" not in p.parts)
    rows = []
    for p in files:
        rel = str(p.relative_to(REPO))
        log = git("log", "--follow", "--format=%cs", "--", rel).split()
        row = {"path": rel, "dir": str(Path(rel).parent), **scan(p),
               "last_commit": log[0] if log else None, "first_commit": log[-1] if log else None,
               "commits": len(log)}
        rows.append(row)
    by_dir = defaultdict(lambda: {"files": 0, "tests": 0, "real_kline": 0})
    for r in rows:
        d = by_dir[r["dir"]]
        d["files"] += 1
        d["tests"] += r.get("tests", 0)
        d["real_kline"] += int(bool(r.get("real_kline")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps({"files": rows, "by_dir": by_dir, "total_files": len(rows),
                                     "total_tests": sum(r.get("tests", 0) for r in rows)},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"files={len(rows)} tests={sum(r.get('tests', 0) for r in rows)} → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
