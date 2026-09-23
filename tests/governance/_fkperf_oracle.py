"""FKPERF 差分 harness（docs/FKPERF_SPEC.md Task 0.1）——**空殼，尚未實作**。

oracle＝`git show ORACLE_COMMIT:scripts/gen_fact_key_blocks.sh`（切換前之 bash 實作）。每筆語料建兩個同形完整沙箱：
同一輸入樹＋註冊表引用之未追蹤 receipt，oracle 沙箱放 oracle 入口、新實作沙箱放新入口與核心；
兩邊於相同 env／參數／stdin／相對 cwd 下各跑一次，比對 stdout、stderr、rc 與宿主檔寫後位元組、權限位。
唯一正規化：兩沙箱根目錄路徑互換（寫死於 `normalize`）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
# 實作起點 commit：bash 實作最後一次修改所在之 commit（SPEC Task 0.1「寫死於 helper」）
ORACLE_COMMIT = "4bdc2d562543"


@dataclass(frozen=True)
class RunOut:
    """單次呼叫之觀測：rc、stdout、stderr，與指定宿主檔寫後之（位元組, 權限位）。"""

    rc: int
    stdout: bytes
    stderr: bytes
    files: Dict[str, Tuple[bytes, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class Case:
    """一筆差分語料：模式、參數、沙箱建法，與 oracle 應命中之預期分支標籤。"""

    case_id: str
    args: Tuple[str, ...]
    build: Callable[[Path], None]           # 於沙箱根目錄建樹（兩沙箱各呼叫一次）
    expect_rc: int                          # oracle 應得之 rc
    expect_first_line: str                  # rc≠0：stderr 首行；rc=0：stdout 首行
    stdin: Optional[bytes] = None
    env: Dict[str, str] = field(default_factory=dict)
    watch_files: Tuple[str, ...] = ()       # 比對寫後位元組與權限位之宿主檔（相對沙箱根）
    entry: str = "core"                     # 新實作之呼叫方式：core＝直呼核心、entry＝經入口檔


def make_pair(tmp_path: Path, case: Case) -> Tuple[Path, Path]:
    """建 oracle 沙箱與新實作沙箱（同一輸入樹、各自完整相依檔）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def run_oracle(root: Path, case: Case) -> RunOut:
    """於 oracle 沙箱跑 oracle 入口。"""
    raise NotImplementedError("FKPERF Task 0.1")


def run_new(root: Path, case: Case) -> RunOut:
    """於新實作沙箱跑新實作（`case.entry`：直呼核心或經入口檔）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def normalize(out: RunOut, root: Path, other_root: Path) -> RunOut:
    """唯一正規化：把 `root` 路徑字面換成 `other_root`；其他一律不動。"""
    raise NotImplementedError("FKPERF Task 0.1")


def diff(a: RunOut, b: RunOut) -> List[str]:
    """逐位元組比對兩次觀測，回傳差異描述（空＝全等）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def exit_catalog() -> Dict[str, str]:
    """由 oracle 原始碼逐一列舉拒絕出口（每個 `return 1`／`_fk_die`／`exit`）→ 標籤：stderr 首行。"""
    raise NotImplementedError("FKPERF Task 0.1")


def exit_sites() -> Dict[int, str]:
    """oracle 原始碼中每一條寫 stderr 之行（`>&2` 或 `_fk_die `）之行號 → 歸類：`exit_catalog()` 之出口標籤、
    "continuation"（多行訊息之後續行）、"warning"（不退出之預警首行）、"tool_failure"（oracle 內部 jq／awk／mktemp
    子程序自身失敗之出口，字面合測試之封閉集；新實作無對應分支，不入 catalog）或 "helper"（`_fk_die` 定義行）。逐行手寫歸類，
    須合 `test_fkperf_differential._site_rules` 之機械規則（出口首行不得為續行；r6 codex／grok P1-01），
    供出口清單之獨立完整性錨（`test_exit_sites_cover_every_stderr_line_of_oracle`）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def corpus(kind: str) -> List[Case]:
    """語料五類：real／sandbox／exit／key_order／bytes（SPEC Task 0.1 改法①～⑤）。
    每筆之 `expect_first_line` 為字面：rc≠0 為 stderr 首行、rc=0 為 stdout 首行（空輸出為 ""）。
    `exit` 類每筆以手寫建法構成，不得迴圈轉手 `exit_catalog()` 產生（否則與出口清單之集合比對恆等；r5 grok P1-01）。
    `bytes` 類至少一筆為 `--write` 且以 `watch_files` 列出其寫入之宿主檔（供寫檔結果之差分與鑑別力；r6 grok P1-03）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def check_case(tmp_path: Path, case: Case) -> List[str]:
    """跑一筆語料：先斷言 oracle 命中預期分支，再回傳新舊差異（空＝全等）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def build_sandbox_tree(root: Path, *, omit: Sequence[str] = (), git_init: bool = True, minimal: bool = False) -> None:
    """以 `git archive ORACLE_COMMIT` 之受管檔＋註冊表引用之 receipt 建完整樹；`omit` 指定要刪之相依檔。
    `minimal=True`：只放入口（與核心）及註冊表，比照既有 `test_empty_registry_is_rc_zero_not_failure` 之沙箱
    （完整樹下空註冊表會先撞交接投影檢查，2026-09-23 主委實測）。"""
    raise NotImplementedError("FKPERF Task 0.1")


def build_current_tree(root: Path) -> None:
    """以目前工作樹之受管檔（含新入口與核心）＋註冊表引用之 receipt 建完整樹並 `git init`（切換後驗收用）。"""
    raise NotImplementedError("FKPERF Task 4.1")
