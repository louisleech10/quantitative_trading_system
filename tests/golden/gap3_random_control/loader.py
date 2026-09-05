"""GAP-3 `G3-D2` D5.4 — 隨機對照抽樣 golden 之 **typed loader**。

## 為什麼要外部凍結檔

抽樣的正確性有兩種壞法：①**不決定性**（同 seed 兩次抽不一樣）②**抽錯母體**
（排除區間算錯、分層粒度變了、eligibility 換了一支）。②的特徵是「抽出來的仍是
合法的 bar、label 仍是合法的 0/1」——assert 式測試很容易在錯的前提下全綠。
外部凍結檔把「這份 bar 表、這個 spec、這批觸發事件 ⇒ 這些 id 與這些 label」
釘成位元組，任何一項變動都要**顯式重凍並在 commit message 具名**。

## 內容（逐項 exact，`atol=0`）

`data_snapshot_digest`、`sample_ids_digest`、`n_drawn`、`candidate_count`、
`per_stratum`（逐層 key／候選數／抽出數）、逐列 `label`、`trigger_ids_digest`。

## 手算法（唯一）

`check` **不另寫抽樣或標籤公式**：它重跑 `sample_random_bars` 並逐項與凍結值比對。
「值對不對」由 `tests/momentum/event_samples/test_random_control.py` 之
(i)–(vii) 以獨立不變式釘住（排除區間、配額比例、標籤路徑）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from momentum.Analysis.event_samples.random_control import sample_random_bars

#: golden JSON 之**必要鍵**（缺一即 raise；型別不符亦 raise）。
_REQUIRED: Tuple[str, ...] = (
    "case_id", "symbol", "timeframe", "scenario", "seed", "spec", "trigger_receipts",
    "data_snapshot_digest", "sample_ids_digest", "n_drawn", "candidate_count",
    "per_stratum", "labels", "trigger_ids_digest",
)


class GoldenError(AssertionError):
    """golden 之 fail-closed 例外（載入層與比對層共用）。"""


@dataclass(frozen=True)
class GoldenRandomControlCase:
    path: Path
    case_id: str
    symbol: str
    timeframe: str
    scenario: str
    seed: int
    spec: Mapping[str, Any]
    trigger_receipts: Tuple[Mapping[str, Any], ...]
    data_snapshot_digest: str
    sample_ids_digest: str
    n_drawn: int
    candidate_count: int
    per_stratum: Tuple[Mapping[str, Any], ...]
    labels: Mapping[str, int]
    trigger_ids_digest: str


@dataclass(frozen=True)
class Report:
    """比對結果。`ok` 為真 ⇔ `diffs` 為空（無「大致相符」）。"""

    case_id: str
    ok: bool
    diffs: Tuple[str, ...]


def load_golden(path) -> GoldenRandomControlCase:
    """讀 golden JSON → typed case。**缺鍵／型別不符 ⇒ raise**（不補預設、不靜默跳過）。"""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GoldenError(f"{p}: golden 頂層須為 object")
    missing = [k for k in _REQUIRED if k not in raw]
    if missing:
        raise GoldenError(f"{p}: golden 缺必要鍵 {missing}")
    if not isinstance(raw["spec"], dict) or not isinstance(raw["trigger_receipts"], list):
        raise GoldenError(f"{p}: spec 須為 object、trigger_receipts 須為 list")
    if not isinstance(raw["labels"], dict) or not raw["labels"]:
        raise GoldenError(f"{p}: labels 須為非空 object（空 labels 會讓逐列比對變成空迴圈）")
    return GoldenRandomControlCase(
        path=p,
        case_id=str(raw["case_id"]),
        symbol=str(raw["symbol"]),
        timeframe=str(raw["timeframe"]),
        scenario=str(raw["scenario"]),
        seed=int(raw["seed"]),
        spec=dict(raw["spec"]),
        trigger_receipts=tuple(dict(r) for r in raw["trigger_receipts"]),
        data_snapshot_digest=str(raw["data_snapshot_digest"]),
        sample_ids_digest=str(raw["sample_ids_digest"]),
        n_drawn=int(raw["n_drawn"]),
        candidate_count=int(raw["candidate_count"]),
        per_stratum=tuple(dict(s) for s in raw["per_stratum"]),
        labels={str(k): int(v) for k, v in raw["labels"].items()},
        trigger_ids_digest=str(raw["trigger_ids_digest"]),
    )


def run_case(case: GoldenRandomControlCase, bars) -> Dict[str, Any]:
    """重跑抽樣 → observed（**唯一**產生路徑，不另寫公式）。"""
    records, receipt = sample_random_bars(
        bars, dict(case.spec), [dict(r) for r in case.trigger_receipts],
        scenario=case.scenario,
    )
    return {
        "data_snapshot_digest": str(receipt["data_snapshot_digest"]),
        "sample_ids_digest": str(receipt["sample_ids_digest"]),
        "n_drawn": int(receipt["n_drawn"]),
        "candidate_count": int(receipt["candidate_count"]),
        "per_stratum": [dict(s) for s in receipt["per_stratum"]],
        "labels": {str(r["event_id"]): int(r["label"]) for r in records},
        "trigger_ids_digest": str(receipt["exclusion"]["trigger_ids_digest"]),
    }


def check_golden(case: GoldenRandomControlCase, bars) -> Report:
    actual = run_case(case, bars)
    diffs: List[str] = []
    # 🔴 bar 表換了就沒有「同一批」可言 ⇒ 直接 FAIL，**不得靜默跳過**。
    if actual["data_snapshot_digest"] != case.data_snapshot_digest:
        return Report(case_id=case.case_id, ok=False, diffs=(
            f"data_snapshot_digest: golden={case.data_snapshot_digest[:16]} "
            f"actual={actual['data_snapshot_digest'][:16]}（bar 表已變，值比對無意義）",
        ))
    for key in ("sample_ids_digest", "n_drawn", "candidate_count", "trigger_ids_digest"):
        if actual[key] != getattr(case, key):
            diffs.append(f"{key}: golden={getattr(case, key)!r} actual={actual[key]!r}")
    exp_ps = [dict(s) for s in case.per_stratum]
    if exp_ps != actual["per_stratum"]:
        diffs.append(f"per_stratum: golden={exp_ps} actual={actual['per_stratum']}")
    exp_ids, act_ids = set(case.labels), set(actual["labels"])
    if exp_ids != act_ids:
        diffs.append(f"抽中 id 集合不等：golden−actual={sorted(exp_ids - act_ids)[:5]} "
                     f"actual−golden={sorted(act_ids - exp_ids)[:5]}")
    for eid in sorted(exp_ids & act_ids):
        if case.labels[eid] != actual["labels"][eid]:
            diffs.append(f"{eid}.label: golden={case.labels[eid]} actual={actual['labels'][eid]}")
    return Report(case_id=case.case_id, ok=not diffs, diffs=tuple(diffs))


def freeze_payload(case_meta: Mapping[str, Any], bars) -> Dict[str, Any]:
    """以 `case_meta`（不含期望值之骨架）跑一次抽樣 → 完整 golden payload。"""
    case = GoldenRandomControlCase(
        path=Path("/dev/null"),
        case_id=str(case_meta["case_id"]),
        symbol=str(case_meta["symbol"]),
        timeframe=str(case_meta["timeframe"]),
        scenario=str(case_meta["scenario"]),
        seed=int(case_meta["seed"]),
        spec=dict(case_meta["spec"]),
        trigger_receipts=tuple(dict(r) for r in case_meta["trigger_receipts"]),
        data_snapshot_digest="", sample_ids_digest="", n_drawn=0, candidate_count=0,
        per_stratum=(), labels={"_": 0}, trigger_ids_digest="",
    )
    actual = run_case(case, bars)
    return {
        "case_id": case.case_id,
        "symbol": case.symbol,
        "timeframe": case.timeframe,
        "scenario": case.scenario,
        "seed": case.seed,
        "spec": dict(case.spec),
        "trigger_receipts": [dict(r) for r in case.trigger_receipts],
        "data_snapshot_digest": actual["data_snapshot_digest"],
        "sample_ids_digest": actual["sample_ids_digest"],
        "n_drawn": actual["n_drawn"],
        "candidate_count": actual["candidate_count"],
        "per_stratum": actual["per_stratum"],
        "labels": actual["labels"],
        "trigger_ids_digest": actual["trigger_ids_digest"],
    }
