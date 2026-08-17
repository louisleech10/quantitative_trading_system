"""Task 2.2／2.3 — N 帳本（append-only JSONL）之唯一讀寫入口。

SPEC ref：Task 2.2／2.3 ＋ A1-7（計數語意與 `n_rows_rejected`）＋ A1-21（B2 code review 修補 L1–L10）。

🔴 今日**無生產者**（`momentum/Optimization` 屬不完整層，見 registry G1-R1）：
帳本不存在／無列 ⇒ `status="unavailable"`、`reason="n_unknown"`。
**禁**回 `n=1`、**禁**以 request `n_trials` 或完成數替代。

寫入口契約（A1-21 L5／L7）：
- 掃描重複 `evaluation_id` ＋ append 包在 **`fcntl.flock(LOCK_EX)`** 內（sidecar `<ledger>.lock`），
  跨執行緒／跨行程互斥 ⇒ 同 id 不可能雙寫、長列（>PIPE_BUF）不交錯。
- `record` 之 `research_session_id`／`dataset_key` **必須**等於參數（禁寫進別人的帳本）。
- 型別採**精確比對**（`type(x) is`）：只收純 Python 純量；`Enum`／numpy 純量／bool 冒充 int 一律拒；
  `float` 欄位須 `math.isfinite`（NaN／±inf 拒）。生產者請自行 `float(x)`／`int(x)`。
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

from momentum.Analysis.strategy_validation.contract import (
    ContractViolation,
    load_strategy_validation_contract,
)
from momentum.core.config import MomentumConfig

_REASON_N_UNKNOWN = "n_unknown"
_REASON_ROW_INVALID = "ledger_row_invalid"

# 契約型別名 → 允許之**精確** Python 型別（`type(value) in ...`；非 isinstance）。
# 精確比對一次擋掉：bool 冒充 int／float、`class S(str, Enum)` 冒充 str、numpy 純量冒充 int／float。
_PY_TYPES: Dict[str, Tuple[type, ...]] = {
    "str": (str,),
    "int": (int,),
    "float": (float, int),  # JSON 之 1 與 1.0 皆視為 float 相容
    "bool": (bool,),
}

_LEDGER_DIRNAME = "strategy_validation"
_LEDGER_ID_SEPARATOR = "__"
_LOCK_SUFFIX = ".lock"

# 測試注入點（預設 None）：在「重複掃描完成、寫入之前」被呼叫。
# 用途＝把 TOCTOU 視窗放大成可證偽測試（拿掉 flock ⇒ 兩執行緒同 id 皆通過掃描 ⇒ 雙寫 ⇒ 紅）。
_after_duplicate_scan_hook: Optional[Callable[[], None]] = None


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


def _ledger_filename(*, research_session_id: str, dataset_key: str) -> str:
    """帳本檔名（純函式；A1-21 L6 單測）。

    兩個識別字皆須為非空 str，且不得含路徑分隔符／`..`／NUL／`__`
    （`__` 為檔名內兩識別字之分隔符；放行會使 `("a__b","c")` 與 `("a","b__c")` 落同一檔）。

    Raises:
        ValueError: 識別字不合法（fail-loud，禁靜默改寫）。
    """
    for name, value in (
        ("research_session_id", research_session_id),
        ("dataset_key", dataset_key),
    ):
        if type(value) is not str or not value:
            raise ValueError(f"{name} 須為非空 str，得到 {value!r}")
        bad = [
            sep
            for sep in (os.sep, os.altsep, "\x00", _LEDGER_ID_SEPARATOR)
            if sep and sep in value
        ]
        if bad or value in (".", ".."):
            raise ValueError(f"{name} 含不合法片段 {bad or [value]!r}: {value!r}")
    return f"{research_session_id}{_LEDGER_ID_SEPARATOR}{dataset_key}.jsonl"


def ledger_path(*, research_session_id: str, dataset_key: str) -> Path:
    """帳本落地路徑（由既有輸出根目錄推導，**不**新增設定鍵）。"""
    root = MomentumConfig.from_project_root().results_path
    return Path(root) / _LEDGER_DIRNAME / _ledger_filename(
        research_session_id=research_session_id, dataset_key=dataset_key
    )


def _snapshot_hash(
    artifact_hashes: Sequence[str], dataset_key: str, research_session_id: str
) -> str:
    """帳本快照 hash（A1-21 L4）。

    payload 用 JSON 序列化三分量（每個字串各自定界）⇒ 任一分量含 `|`／`,`／引號皆無歧義；
    舊法 `",".join(...) + "|" + ... + "|" + ...` 可碰撞（三家各給反例）。
    """
    payload = json.dumps(
        [sorted(artifact_hashes), dataset_key, research_session_id],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _row_problems(
    row: Any, schema: Dict[str, Dict[str, Any]], contract: Dict[str, Any]
) -> List[str]:
    """schema 檢核；回傳問題清單（空＝合法）。reason 字面只有 `ledger_row_invalid`，
    清單只進錯誤**訊息**（A1-21 L9：缺鍵／額外鍵／型別在訊息上可分，reason 不分）。

    規則：必填齊備／無額外鍵／型別**精確**相符／`float` 有限／`<key>_values` 枚舉 membership
    （凡契約存在 `f"{key}_values"` 者一律機械檢查，涵蓋 `metric_unit`）。
    """
    if not isinstance(row, dict):
        return [f"row 非物件: {type(row).__name__}"]
    problems: List[str] = []
    missing = sorted(set(schema) - set(row))
    extra = sorted(set(row) - set(schema))
    if missing:
        problems.append(f"missing={missing}")
    if extra:
        problems.append(f"extra={extra}")
    for key, spec in schema.items():
        if key not in row:
            continue
        expected = _PY_TYPES.get(spec["type"])
        value = row[key]
        if expected is None:
            problems.append(f"unknown_type_name={spec['type']!r}")
            continue
        if type(value) not in expected:
            problems.append(f"bad_type[{key}]={type(value).__name__}")
            continue
        if spec["type"] == "float" and not math.isfinite(value):
            problems.append(f"non_finite[{key}]={value!r}")
            continue
        enum_key = f"{key}_values"
        if enum_key in contract and value not in contract[enum_key]:
            problems.append(f"not_in_enum[{key}]={value!r}")
    return problems


def _row_is_valid(row: Any, schema: Dict[str, Dict[str, Any]], contract: Dict[str, Any]) -> bool:
    return not _row_problems(row, schema, contract)


@contextmanager
def _ledger_lock(path: Path, *, exclusive: bool) -> Iterator[None]:
    """sidecar 檔鎖（`<ledger>.lock`）：寫者 LOCK_EX（掃描＋append 原子）、讀者 LOCK_SH（不讀到半列）。"""
    lock_path = path.with_name(path.name + _LOCK_SUFFIX)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


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
      schema-invalid 含：JSON 語法錯／缺鍵／額外鍵／型別錯／非有限數值／枚舉外／
      row 之 `research_session_id`／`dataset_key` 與本帳本不符（A1-21 L1／L5）。
      `metric_unit="annualized"` 為**合法**枚舉 ⇒ schema-valid、計入 `n_evaluated`，
      只是不入 `valid_sharpe_values`（A1-21 L3；取代 TODO ⑥b 之「計入 n_rows_rejected」字面）。
    reason（A1-21 L2）：檔缺／真·零列 ⇒ `n_unknown`；檔存在但**全列非法** ⇒ `ledger_row_invalid`
    （`status=unavailable`）；有合法列且有非法列 ⇒ `status=ok`、`reason=ledger_row_invalid`。
    """
    path = ledger_path(research_session_id=research_session_id, dataset_key=dataset_key)
    if not path.is_file():
        return _unavailable()

    contract = load_strategy_validation_contract()
    schema = contract["ledger_record_keys"]["keys"]

    n_evaluated = n_valid_metrics = n_failed = n_rejected = 0
    artifact_hashes: set = set()
    candidate_ids: set = set()
    sharpe_values: List[float] = []
    reasons_seen: List[str] = []

    def _reject() -> None:
        nonlocal n_rejected
        n_rejected += 1
        if _REASON_ROW_INVALID not in reasons_seen:
            reasons_seen.append(_REASON_ROW_INVALID)

    with _ledger_lock(path, exclusive=False):
        with path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            _reject()
            continue
        if not _row_is_valid(row, schema, contract):
            _reject()
            continue
        if row["research_session_id"] != research_session_id or row["dataset_key"] != dataset_key:
            _reject()  # 別人的列混進本帳本 ⇒ 對本帳本而言非法（fail-closed）
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
    snapshot_hash = _snapshot_hash(sorted(artifact_hashes), dataset_key, research_session_id)

    if n_evaluated == 0:
        status = "unavailable"
        reason = _REASON_ROW_INVALID  # 檔在、全列非法：是「帳本損壞」不是「無帳本」
    else:
        status = "ok"
        reason = reasons_seen[0] if reasons_seen else ""

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
        ContractViolation: record 不符 `ledger_record_keys`（訊息列出 missing／extra／bad_type／
            non_finite／not_in_enum）、record 之 `research_session_id`／`dataset_key` 與參數不符、
            或 `evaluation_id` 於同檔重複。
        ValueError: `research_session_id`／`dataset_key` 不可作檔名（見 `_ledger_filename`）。
        OSError: 目錄不可建立／檔案不可寫。
    """
    contract = load_strategy_validation_contract()
    schema = contract["ledger_record_keys"]["keys"]
    problems = _row_problems(record, schema, contract)
    if problems:
        raise ContractViolation("record 不符 ledger_record_keys: " + "; ".join(problems))
    if record["research_session_id"] != research_session_id or record["dataset_key"] != dataset_key:
        raise ContractViolation(
            "record 之 research_session_id/dataset_key 與目標帳本不符（禁寫進別人的帳本）: "
            f"record=({record['research_session_id']!r}, {record['dataset_key']!r}) "
            f"target=({research_session_id!r}, {dataset_key!r})"
        )

    path = ledger_path(research_session_id=research_session_id, dataset_key=dataset_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"

    with _ledger_lock(path, exclusive=True):
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                for raw in handle:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    try:
                        existing = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if (
                        isinstance(existing, dict)
                        and existing.get("evaluation_id") == record["evaluation_id"]
                    ):
                        raise ContractViolation(
                            f"evaluation_id 重複: {record['evaluation_id']!r}"
                            "（帳本為 append-only，禁重覆記）"
                        )
        if _after_duplicate_scan_hook is not None:
            _after_duplicate_scan_hook()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)  # 在 LOCK_EX 內 ⇒ 掃描＋寫入原子；不依賴 PIPE_BUF 原子性
            handle.flush()
