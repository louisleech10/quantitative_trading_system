#!/usr/bin/env python3
"""fact-key 生成器之 Python 核心（FKPERF，docs/FKPERF_SPEC.md）——**空殼，尚未實作**。

目標：取代 `scripts/gen_fact_key_blocks.sh` 之 bash 判定邏輯，使外部程序數與登記規模無關；
六種呼叫形態之 stdout、stderr、rc 與寫檔結果須與 oracle（切換前之 bash 實作）逐位元組相同（SPEC C-1）。
只用標準庫、以系統 python3（3.9）執行（C-5）。Phase 4 前不接入入口，只由差分測試直呼（SPEC §R）。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

Row = List[str]


@dataclass(frozen=True)
class Registry:
    """已載入並物化之註冊表（rows_source／rows_filter 已展開為靜態 rows）。"""

    path: Path          # 訊息顯示用之註冊表路徑（使用者要改的檔，非暫存物化檔）
    data: Dict[str, object]
    keys: Tuple[str, ...]  # jq `keys[]` 碼點序，已排除 `_schema`（SPEC C-3）


@dataclass(frozen=True)
class Outcome:
    """一次呼叫之結果：rc 與逐位元組之 stdout／stderr。"""

    rc: int
    stdout: bytes
    stderr: bytes


def preflight(reg_path: Path) -> Optional[Outcome]:
    """註冊表存在且為合法 JSON 物件；失敗回傳 rc=1 之 Outcome（SPEC Task 1.1，C-5）。
    `NaN`／`Infinity` 字面於解析階段接受（與 jq 1.7.1 相同），交由 rows 型別檢查以 oracle 同訊息拒絕（SPEC v6 C-5）。"""
    raise NotImplementedError("FKPERF Task 1.1")


def load_registry(reg_path: Path, repo_root: Path) -> Registry:
    """載入、驗證 keys／shape／rows／schema sets，並物化 rows_source／rows_filter（SPEC Task 1.1）。"""
    raise NotImplementedError("FKPERF Task 1.1")


def rows_tsv(reg: Registry, key: str) -> List[bytes]:
    """唯一排序點：整列 jq @tsv 跳脫後以位元組序排序（SPEC Task 1.2，C-3）。"""
    raise NotImplementedError("FKPERF Task 1.2")


def gen_block(reg: Registry, key: str) -> bytes:
    """產出單一 key 之生成區塊內容（tsv／table render；SPEC Task 1.2）。

    🔴 可測性契約（r5 三家 P1）：`emit_all`／`write_all`／`check_hosts` 之每 key 渲染一律在**呼叫當下**以模組全域名
    `gen_block(reg, key)` 呼叫——不得以模組層別名（`_x = gen_block`）、預設參數或閉包綁定，亦不得改走另一私有渲染函式。
    規模邊界 23／24 之 mutant 以覆寫此全域名注入每 key 迴圈；
    `tests/governance/test_fkperf_scale.py::test_gen_block_injection_reaches_every_key` 以行為驗證此契約。"""
    raise NotImplementedError("FKPERF Task 1.2")


def emit_all(reg: Registry) -> Outcome:
    """無參數模式：印出全部 fact-key 之生成區塊（SPEC Task 1.2）。"""
    raise NotImplementedError("FKPERF Task 1.2")


def write_all(reg: Registry, root: Path) -> Outcome:
    """`--write`：同目錄暫存檔 `<宿主>.factkey.<pid>` 寫完後 rename 覆蓋（SPEC Task 1.2）。"""
    raise NotImplementedError("FKPERF Task 1.2")


def scope_files(root: Path, reg: Registry) -> List[str]:
    """`git ls-files --cached --others --exclude-standard -z` 單次列舉範圍檔（SPEC Task 2.1）。"""
    raise NotImplementedError("FKPERF Task 2.1")


def status_hits(reg: Registry, lines: Sequence[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
    """唯一手寫狀態判定碼（`_FK_HIT_AWK` 語意，UTF-8 位元組；SPEC Task 2.1，C-3、C-11）。"""
    raise NotImplementedError("FKPERF Task 2.1")


def check_hosts(reg: Registry, root: Path) -> List[str]:
    """宿主檢查：標記、未登記區塊、漂移、區塊外 rc 宣稱、手寫狀態（SPEC Task 2.1）。"""
    raise NotImplementedError("FKPERF Task 2.1")


def validate_criteria_and_mechanism(reg: Registry, root: Path) -> List[str]:
    """判準與機制（含 receipt 存在性，相對 ROOT；SPEC Task 3.1）。"""
    raise NotImplementedError("FKPERF Task 3.1")


def validate_enforcement(reg: Registry, repo_root: Path) -> List[str]:
    """產出端覆蓋：settings.json 掛載對證、ticket allowlist、收案綁定、ticket universe（SPEC Task 3.2）。"""
    raise NotImplementedError("FKPERF Task 3.2")


def validate_docrot2_and_handoff(reg: Registry) -> List[str]:
    """DOCROT2 狀態與交接投影（SPEC Task 3.3）。"""
    raise NotImplementedError("FKPERF Task 3.3")


def print_help(entry_path: Path) -> Outcome:
    """印入口檔第 2–20 行；於 preflight 之後呼叫（SPEC Task 4.1）。"""
    raise NotImplementedError("FKPERF Task 4.1")


def main(argv: Sequence[str]) -> int:
    """六種呼叫形態之分派（emit／--check／--write／--status-hits／--help／錯誤參數；SPEC C-1）。"""
    raise NotImplementedError("FKPERF Task 1.1–4.1")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
