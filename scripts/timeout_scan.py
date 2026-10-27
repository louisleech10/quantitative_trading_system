"""NOCAP Task 0.2／0.2b③（docs/NOCAP_SPEC.md）：全庫逾時／期限樣式掃描——測試期（tests/registry/test_timeout_registry.py）
與 pre-commit（`--staged`，讀暫存區完整內容）共用之單一實作；樣式唯一來源 `scripts/timeout_patterns.json`、白名單
`scripts/timeout_registry.json`。

用法：`python3 scripts/timeout_scan.py [--repo R] [--staged]`（rc 0＝全部命中皆已登記且非 A 類；1＝有未登記或過期登記）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
#: 掃描範圍（SPEC Task 0.2）：Python／shell 走 AST＋文字樣式，`config/` 走 YAML／JSON 鍵，`frontend/` 走 TS／JS 文字樣式。
SCAN_ROOTS = ("scripts", "momentum", "api", "tests", "handoffs/run_receipts", "config", "frontend")
EXCLUDED_DIRS = ("node_modules", ".next", "__pycache__")


@dataclass(frozen=True)
class Hit:
    """一處逾時／期限樣式命中：`function` 為所在函式全名（模組層 `<module>`；非 Python 為空字串）、
    `callee` 為被呼叫者（非呼叫之字串型命中為空字串）、`literal` 為逾時參數之字面值。"""
    path: str
    line: int
    pattern_id: str
    function: str
    callee: str
    literal: str
    text: str


def scan_text(path: str, text: str) -> List[Hit]:
    """依副檔名與所在根目錄掃描單一檔內容（repo 相對路徑 `path`）。"""
    raise NotImplementedError("NOCAP Task 0.2")


def scan_repo(repo: Path = REPO, roots: Sequence[str] = SCAN_ROOTS) -> List[Hit]:
    """掃描 `roots` 下全部檔（排除 `EXCLUDED_DIRS`）。"""
    raise NotImplementedError("NOCAP Task 0.2")


def scan_staged(repo: Path = REPO) -> List[Hit]:
    """pre-commit：對每個暫存之受掃描檔讀暫存區內容（`git show :<path>`）跑 `scan_text`。"""
    raise NotImplementedError("NOCAP Task 0.2b")


def registered(hit: Hit, registry: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """白名單比對：Python 命中須 path＋function＋callee＋literal 全等；shell／其他須 path＋去頭尾空白整行相等。"""
    raise NotImplementedError("NOCAP Task 0.2b")


def unregistered(hits: Sequence[Hit], registry: Sequence[Mapping[str, Any]]) -> List[Hit]:
    """未登記或登記為 A 類之命中。"""
    raise NotImplementedError("NOCAP Task 0.2")


def stale_entries(registry: Sequence[Mapping[str, Any]], hits: Sequence[Hit]) -> List[Dict[str, Any]]:
    """登記檔中已無對應命中之列（防漂移）。"""
    raise NotImplementedError("NOCAP Task 0.2")


def main(argv: Optional[Sequence[str]] = None) -> int:
    raise NotImplementedError("NOCAP Task 0.2")


if __name__ == "__main__":
    raise SystemExit(main())
