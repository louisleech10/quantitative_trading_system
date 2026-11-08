"""上限盤點掃描器（ICPERF SPEC v5.85 Task 0.6 (b)，L0；施工前空殼）。

以語法解析掃 Python（AST）、JSON、TS／TSX、YAML 中可能構成上限之數字字面量與符號常數，供產生現行需修機讀表
`tests/_golden/icperf/limit_inventory.json`。parse 失敗入 errors，不得視為「無上限」。取代
`runs/limit_audit/scan_py_literals.py`（未入版控之一次性腳本）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable


def scan(paths: Iterable[Path]) -> Dict[str, Any]:
    """掃描路徑集合，回 `{"rows": [{"file", "line", "kind", "value", "code"}...], "errors": [{"file", "error"}...]}`。"""
    raise NotImplementedError("Task 0.6")


DEFAULT_ROOTS = ("momentum", "api", "frontend/src", "config")


def scan_default_roots(root: Path) -> Dict[str, Any]:
    """遞迴掃 `root` 下 DEFAULT_ROOTS 之全部 .py／.json／.ts／.tsx／.yaml／.yml 檔（同 `scan` 之輸出形狀；路徑為 root 相對）。"""
    raise NotImplementedError("Task 0.6")


def build_inventory(scan_out: Dict[str, Any], rulings: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """候選＋裁定（`tests/_golden/icperf/limit_rulings.json`，以 file＋code_sha256 為鍵）⇒ 機讀表
    `{"rows": [...], "unruled": [...]}`；無裁定之候選列入 unruled，不得靜默丟棄；裁定指向已不存在之候選列入 unruled。"""
    raise NotImplementedError("Task 0.6")


def main(argv: Any = None) -> int:
    """CLI：`limit_scan.py [路徑...]` 輸出候選 JSON；`limit_scan.py --inventory --rulings <檔> --out <檔>` 重產機讀表。"""
    raise NotImplementedError("Task 0.6")


if __name__ == "__main__":
    raise SystemExit(main())
