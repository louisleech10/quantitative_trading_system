"""FKPERF 規模探針（docs/FKPERF_SPEC.md Task 0.2）——**空殼，尚未實作**。

外部程序計數：PATH shim（工具集合同 handoffs/run_receipts/fkperf_probes/prof_spawn.sh 另加 bash），
shim 以真實路徑 exec，不得對 builtin 名稱建 shim（r1 grok 實測 printf shim 會使 emit 早退）。
合成規模註冊表：規模以總 fact-key 數定義（tests/governance/fixtures/fkperf_scale_contract.json）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "tests" / "governance" / "fixtures" / "fkperf_scale_contract.json"


def load_contract() -> dict:
    """讀規模驗收規則（量測點、門檻、次數之單一落點）。"""
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def content_keys() -> List[str]:
    """`docs/GOV_B25_SCOPE_AMENDMENT.md` 之 FACTKEY-CONTENT 宣告集合（jq keys[] 序）。"""
    raise NotImplementedError("FKPERF Task 0.2")


def build_scaled_tree(tmp_path: Path, total_keys: int) -> Path:
    """建總 fact-key 數恰為 `total_keys` 之合成沙箱樹（只複製純內容 key 並改名；宿主區塊以 --write 物化）。"""
    raise NotImplementedError("FKPERF Task 0.2")


def total_key_count(root: Path) -> int:
    """沙箱註冊表之總 fact-key 數（排除 `_schema`）。"""
    raise NotImplementedError("FKPERF Task 0.2")


def verify_scaled_tree(root: Path, target_total: int) -> List[str]:
    """合成樹之合規問題清單（空＝合規）：總數≠目標、複製了非內容 key、改名後 key 不合 `_schema.key_pattern`、
    與既有 key 或狀態識別碼撞名。"""
    raise NotImplementedError("FKPERF Task 0.2")


def count_spawns_cmd(argv: Sequence[str], cwd: Path) -> Tuple[int, Dict[str, int]]:
    """對任意指令以同一 PATH shim 計外部程序數（helper 自測用）。"""
    raise NotImplementedError("FKPERF Task 0.2")


def count_spawns(root: Path, mode: str) -> Tuple[int, Dict[str, int]]:
    """以 PATH shim 計 `mode`（emit／--check／--write／--status-hits／guard）之外部程序數。
    被量之呼叫 rc≠0 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗之路徑不得充當「與規模無關」；r5 三家 P1）。"""
    raise NotImplementedError("FKPERF Task 0.2")


def time_mode(root: Path, mode: str, trials: int, timeout: float = 0.0) -> List[float]:
    """量 `mode` 之牆鐘耗時 `trials` 次；`timeout`>0 時單次逾時即回傳 inf（逾時之那次不看 rc）。
    未逾時而 rc≠0 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗不得充當「耗時有限」；r5 三家 P1）。"""
    raise NotImplementedError("FKPERF Task 4.4")


def write_receipt(rows: Sequence[dict], name: str) -> Path:
    """耗時與程序數收據寫入 `handoffs/run_receipts/<日期>-<name>.json`。"""
    raise NotImplementedError("FKPERF Task 4.4")
