"""NOCAP Task 0.3b／0.3c／0.4（docs/NOCAP_SPEC.md）：成長曲線、估時、四項平衡三種收據之共用身分 `identity`——
比對欄 `match`（下指令當下重算、逐欄相等才可沿用）與紀錄欄 `meta`（producer、created_at，不參與比對）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
MATCH_KEYS = ("entrypoint", "target_argv", "code_sha256", "data", "config_sha256", "hardware")
META_KEYS = ("producer", "created_at")


def normalize_argv(argv: Sequence[str], repo: Path = REPO) -> str:
    """以 `shlex.join` 正規化；repo 內絕對路徑轉相對路徑。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def code_sha256(paths: Sequence[str], repo: Path = REPO) -> str:
    """各檔**工作樹實際內容**之 `git hash-object` 依路徑排序串接後之 sha256（含未提交改動）。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def data_identity(paths: Sequence[str], repo: Path = REPO) -> list:
    """每個輸入檔 {path, size, sha256}；sha256 以 (path, size, mtime_ns) 快取。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def compute_match(entrypoint: str, target_argv: Sequence[str], code_paths: Sequence[str], data_paths: Sequence[str],
                  config_paths: Sequence[str], repo: Path = REPO) -> Dict[str, Any]:
    """下指令當下之 `match`（鍵恰為 `MATCH_KEYS`）。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def receipt_matches(receipt: Mapping[str, Any], current_match: Mapping[str, Any]) -> bool:
    """收據 `identity.match` 與當下 `match` 逐欄相等；`identity.meta` 不比對。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def coverage_ids_valid(estimate_receipt: Mapping[str, Any], spec_text: str) -> bool:
    """估時收據之 `coverage_path_ids` 皆為該 SPEC `## §B` 預算表某列之 id（Task 0.3c）。"""
    raise NotImplementedError("NOCAP Task 0.3c")
