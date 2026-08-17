"""Task 2.2／2.3 — N 帳本（append-only JSONL）之唯一讀寫入口。

SPEC ref：Task 2.2／2.3 ＋ A1-7（計數語意與 `n_rows_rejected`）。

🔴 今日**無生產者**（`momentum/Optimization` 屬不完整層，見 registry G1-R1）：
帳本不存在／無列 ⇒ `status="unavailable"`、`reason="n_unknown"`。
**禁**回 `n=1`、**禁**以 request `n_trials` 或完成數替代。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from momentum.Analysis.strategy_validation.contract import (
    ContractViolation,
    load_strategy_validation_contract,
)
from momentum.core.config import MomentumConfig

_REASON_N_UNKNOWN = "n_unknown"
_REASON_ROW_INVALID = "ledger_row_invalid"

_PY_TYPES = {
    "str": (str,),
    "int": (int,),
    "float": (float, int),
    "bool": (bool,),
}


@dataclass(frozen=True)
class LedgerReadResult:
    """帳本讀取結果（typed；三關取 N 與 trial Sharpe 之唯一來源）。"""

    n_candidates_considered: int
    n_evaluated: int
    n_valid_metrics: int
    n_failed_or_pruned: int
    n_rows_rejected: int
    n_is_lower_bound: bool
    n_for_dsr: int
    snapshot_hash: str
    artifact_hashes: frozenset
    candidate_ids: frozenset
    n_semantics: str
    valid_sharpe_values: Tuple[float, ...]
    status: str
    reason: str
    reasons_seen: Tuple[str, ...] = field(default=())


def ledger_path(*, research_session_id: str, dataset_key: str) -> Path:
    """帳本落地路徑（由既有輸出根目錄推導，**不**新增設定鍵）。"""
    root = MomentumConfig.from_project_root().results_path
    return Path(root) / "strategy_validation" / f"{research_session_id}__{dataset_key}.jsonl"


def _row_schema() -> Dict[str, Dict[str, Any]]:
    return load_strategy_validation_contract()["ledger_record_keys"]["keys"]


def _row_is_valid(row: Any, schema: Dict[str, Dict[str, Any]]) -> bool:
    """schema 檢核：必填齊備／型別相符／無額外鍵／`metric_unit` 屬枚舉。"""
    if not isinstance(row, dict):
        return False
    if set(row) != set(schema):  # additional_properties: false ＋ 必填全備
        return False
    for key, spec in schema.items():
        expected = _PY_TYPES.get(spec["type"])
        value = row[key]
        if expected is None:
            return False
        if isinstance(value, bool) and spec["type"] != "bool":
            return False
        if not isinstance(value, expected):
            return False
    contract = load_strategy_validation_contract()
    if row["metric_unit"] not in contract["metric_unit_values"]:
        return False
    return True


def _unavailable(reason: str = _REASON_N_UNKNOWN) -> LedgerReadResult:
    return LedgerReadResult(
        n_candidates_considered=0,
        n_evaluated=0,
        n_valid_metrics=0,
        n_failed_or_pruned=0,
        n_rows_rejected=0,
        n_is_lower_bound=True,
        n_for_dsr=0,
        snapshot_hash="",
        artifact_hashes=frozenset(),
        candidate_ids=frozenset(),
        n_semantics="unknown",
        valid_sharpe_values=(),
        status="unavailable",
        reason=reason,
    )


def read_trial_ledger(*, research_session_id: str, dataset_key: str) -> LedgerReadResult:
    """讀 append-only JSONL 帳本；缺檔／零列 ⇒ fail-closed `n_unknown`。

    計數語意（A1-7；不變式由構造成立）：
      `n_evaluated` ＝ schema-valid 列數；
      `n_valid_metrics` ＝ schema-valid ∧ `metric_valid is True`；
      `n_failed_or_pruned` ＝ schema-valid ∧ `metric_valid is False`；
      ⇒ `n_evaluated == n_valid_metrics + n_failed_or_pruned`；
      `n_rows_rejected` ＝ schema-invalid 列數（**不**進 `n_evaluated`），reason 記 `ledger_row_invalid`。
    """
    path = ledger_path(research_session_id=research_session_id, dataset_key=dataset_key)
    if not path.is_file():
        return _unavailable()

    schema = _row_schema()
    contract = load_strategy_validation_contract()

    n_evaluated = n_valid_metrics = n_failed = n_rejected = 0
    artifact_hashes: set = set()
    candidate_ids: set = set()
    sharpe_values: List[float] = []
    reasons_seen: List[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                n_rejected += 1
                if _REASON_ROW_INVALID not in reasons_seen:
                    reasons_seen.append(_REASON_ROW_INVALID)
                continue
            if not _row_is_valid(row, schema):
                n_rejected += 1
                if _REASON_ROW_INVALID not in reasons_seen:
                    reasons_seen.append(_REASON_ROW_INVALID)
                continue

            n_evaluated += 1
            candidate_ids.add(row["candidate_id"])
            artifact_hashes.add(row["input_artifact_hash"])
            if row["metric_valid"]:
                n_valid_metrics += 1
                if row["metric_name"] == "sharpe" and row["metric_unit"] == "per_period":
                    sharpe_values.append(float(row["metric_value"]))
            else:
                n_failed += 1

    if n_evaluated == 0 and n_rejected == 0:
        return _unavailable()

    n_candidates = len(candidate_ids)
    snapshot_hash = hashlib.sha256(
        (",".join(sorted(artifact_hashes)) + "|" + dataset_key + "|" + research_session_id).encode(
            "utf-8"
        )
    ).hexdigest()

    status = "ok" if n_evaluated > 0 else "unavailable"
    reason = "" if n_evaluated > 0 else _REASON_N_UNKNOWN
    if n_rejected > 0 and _REASON_ROW_INVALID not in reasons_seen:
        reasons_seen.append(_REASON_ROW_INVALID)
    if n_evaluated == 0:
        reason = _REASON_N_UNKNOWN
    elif reasons_seen:
        reason = reasons_seen[0]

    if reason and reason not in contract["reasons"]:  # 防自創 reason 字面
        raise ContractViolation(f"reason 不在契約 reasons: {reason!r}")

    return LedgerReadResult(
        n_candidates_considered=n_candidates,
        n_evaluated=n_evaluated,
        n_valid_metrics=n_valid_metrics,
        n_failed_or_pruned=n_failed,
        n_rows_rejected=n_rejected,
        n_is_lower_bound=True,
        n_for_dsr=n_candidates,
        snapshot_hash=snapshot_hash,
        artifact_hashes=frozenset(artifact_hashes),
        candidate_ids=frozenset(candidate_ids),
        n_semantics="unknown",
        valid_sharpe_values=tuple(sharpe_values),
        status=status,
        reason=reason,
        reasons_seen=tuple(reasons_seen),
    )


def append_trial_attempt(
    *,
    research_session_id: str,
    dataset_key: str,
    record: Dict[str, Any],
) -> None:
    """Task 2.3 — **唯一**合法寫入口：先驗 schema，通過才 append 一行（失敗 raise，不寫半列）。

    Raises:
        ContractViolation: record 不符 `ledger_record_keys`，或 `evaluation_id` 於同檔重複。
        OSError: 目錄不可建立／檔案不可寫。
    """
    schema = _row_schema()
    if not _row_is_valid(record, schema):
        raise ContractViolation(
            "record 不符 ledger_record_keys（缺鍵／型別錯／額外鍵／metric_unit 非法）"
        )

    path = ledger_path(research_session_id=research_session_id, dataset_key=dataset_key)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(existing, dict) and existing.get("evaluation_id") == record["evaluation_id"]:
                    raise ContractViolation(
                        f"evaluation_id 重複: {record['evaluation_id']!r}（帳本為 append-only，禁重覆記）"
                    )

    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)  # 單次 write ⇒ 併發追加不交錯（POSIX O_APPEND）
        handle.flush()
