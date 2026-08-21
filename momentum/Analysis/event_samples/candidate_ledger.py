"""GAP-3 規則 → return series → candidate ledger → DSR/PBO/MinBTL（docs/GAP3_EVENT_TODO.md Task B4.2；SPEC K6/C7；W8）。

GAP-1 對接（**唯讀消費、不改簽名**）：
- 帳本＝`strategy_validation/ledger.py`（`append_trial_attempt` 唯一合法寫入口；`read_trial_ledger` 讀 N）；
  `n_trials` **只**從 ledger 讀（`LedgerReadResult`），禁 request 任意填。
- 檢定＝`deflated_sharpe`／`probability_of_backtest_overfitting`／`assess_eligibility`（MinBTL）。
- 型別閘：AUC／PR-AUC／rank-biserial **不得**餵 return-based DSR/PBO——`CandidateReturns.metric_kind` 必為
  `return_series`，其他一律 `MetricTypeError`（機械拒，非文件約定）。

W8 entry×exit 一致性：`to_return_series` 之 entry 取對齊收據 `entry_price_source_bar_open_ms`＋`entry_price_source_field`
（D1-6 映射），exit＝`label_end_ms` 對應 bar 之 close（D1-4 持有鏈）；horizon 由 `label_definition.window` 唯一決定——
**禁**自行推導時點、禁把事件標籤報酬／實際進場報酬混用。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Union

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.Analysis.event_samples.types import AlignmentReceipts
from momentum.Analysis.strategy_validation import ledger as _ledger
from momentum.Analysis.strategy_validation.deflated_sharpe import deflated_sharpe
from momentum.Analysis.strategy_validation.min_btl import assess_eligibility
from momentum.Analysis.strategy_validation.pbo import UniverseProvenance, candidate_set_hash, probability_of_backtest_overfitting
from momentum.Analysis.strategy_validation.returns_contract import PeriodReturns
from momentum.Analysis.strategy_validation.sharpe import compute_sharpe

logger = get_logger(__name__)

METRIC_KIND_RETURN_SERIES = "return_series"
_FORBIDDEN_METRIC_KINDS = ("auc", "pr_auc", "rank_biserial", "roc_auc", "precision", "recall", "f1", "lift")
_MS_PER_YEAR = 365.25 * 86400 * 1000.0
_T_SEMANTICS = "trade_level"


class MetricTypeError(TypeError):
    """非 return-based 指標（AUC／PR-AUC／rank-biserial…）餵入 DSR/PBO/ledger（機械拒）。"""


@dataclass(frozen=True)
class LedgerKey:
    """GAP-1 帳本身分（檔名由 `ledger.ledger_path` 推導；本模組不自行開檔）。"""

    research_session_id: str
    dataset_key: str


@dataclass(frozen=True)
class CandidateReturns:
    """一個候選之 per-trade return series（typed 容器；DSR/PBO 唯一合法輸入形）。

    returns：index=event_id（依 entry_at 排序）、值＝signed 持有報酬；attrs 帶 `source_artifact_hash`／`span_years`。
    metric_kind：必為 `return_series`；其他（auc／pr_auc／rank_biserial…）⇒ MetricTypeError。
    """

    candidate_id: str
    returns: pd.Series
    metric_kind: str = METRIC_KIND_RETURN_SERIES


_RECEIPT_ATTRS = ("t_semantics", "entry_semantic", "label_definition", "source_artifact_hash", "span_years", "entry_at_ms_by_event")


def _assert_return_series(cr: Any, where: str) -> None:
    """K6/C7 型別閘（機械）：typed 容器＋`to_return_series` 收據 attrs 全齊（COMPOSER-R1-P1-01／GROK-R1-P2-01：
    只擋 metric_kind／name 可被「預設 return_series＋分數數列」繞過 ⇒ 改驗收據鍵：t_semantics=trade_level、
    entry_semantic、label_definition、source_artifact_hash(64hex)、span_years>0、entry_at_ms_by_event 覆蓋全 index、n≥2）。"""
    if not isinstance(cr, CandidateReturns):
        raise MetricTypeError(f"{where}: 須為 CandidateReturns，得 {type(cr).__name__}")
    if str(cr.metric_kind).lower() != METRIC_KIND_RETURN_SERIES:
        raise MetricTypeError(f"{where}: metric_kind={cr.metric_kind!r} 非 return_series（AUC/PR-AUC/rank-biserial 禁餵 DSR/PBO）")
    if not isinstance(cr.returns, pd.Series) or len(cr.returns) < 2:
        raise MetricTypeError(f"{where}: returns 須為 ≥2 筆之 pd.Series（per-trade return series；單一分數非序列）")
    if str(cr.returns.name or "").lower() in _FORBIDDEN_METRIC_KINDS:
        raise MetricTypeError(f"{where}: returns.name={cr.returns.name!r} 指向分類指標，非 return series")
    a = cr.returns.attrs
    missing = [k for k in _RECEIPT_ATTRS if k not in a]
    if missing:
        raise MetricTypeError(f"{where}: returns 缺 to_return_series 收據 attrs {missing}（分數／AUC 數列不得冒充 return series）")
    if a["t_semantics"] != _T_SEMANTICS:
        raise MetricTypeError(f"{where}: t_semantics={a['t_semantics']!r} ≠ {_T_SEMANTICS}")
    h = str(a["source_artifact_hash"])
    if len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h):
        raise MetricTypeError(f"{where}: source_artifact_hash 非 64 hex")
    if not (isinstance(a["span_years"], (int, float)) and np.isfinite(a["span_years"]) and a["span_years"] > 0):
        raise MetricTypeError(f"{where}: span_years 須 >0（收據）")
    ent = a["entry_at_ms_by_event"]
    if not isinstance(ent, dict) or not set(cr.returns.index) <= set(ent):
        raise MetricTypeError(f"{where}: entry_at_ms_by_event 須覆蓋全部事件（觀測軸時序收據）")
    if not np.isfinite(cr.returns.to_numpy(dtype=float)).all():
        raise ValueError(f"{where}: returns 含 NaN/inf（loud）")
    if receipt_digest(cr.returns) != h:
        raise MetricTypeError(f"{where}: source_artifact_hash 與目前 index/values 不符（stale receipt：序列被改動或非 to_return_series 產出）")


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def receipt_digest(returns: pd.Series) -> str:
    """return series 收據 digest＝f(index, values, entry_semantic, label_definition)——`to_return_series` 產生、
    `_assert_return_series` 重算比對（CODEX-R2-P1-02：copy 後原地改值之 stale receipt 必拒）。"""
    a = returns.attrs
    return _digest({"events": [str(e) for e in returns.index], "entry": a.get("entry_semantic"), "ld": a.get("label_definition"),
                    "values": [float(v) for v in returns.to_numpy(dtype=float)]})


# --------------------------------------------------------------------------- return series（W8）
def to_return_series(
    rule_or_scores: Union[pd.Series, Mapping[str, Any]],
    bars: Mapping[str, pd.DataFrame],
    entry_semantic: str,
    label_definition: dict,
    receipts: AlignmentReceipts,
    *,
    events: Optional[pd.DataFrame] = None,
    score_threshold: float = 0.5,
) -> pd.Series:
    """訊號事件 → signed 持有報酬序列（index=event_id，依 entry_at_ms 排序）。

    rule_or_scores：index=event_id 之 bool 遮罩或分數（≥ score_threshold 為訊號）。
    bars：{symbol: DataFrame(open_time_ms/close_time_ms/open/close)}（錨定 TF）。
    entry_semantic／label_definition：須與 events 之 `entry_price_semantic`／`label_definition` 全列一致（W8：禁混用）。
    receipts：B1.1 對齊收據——entry 時點／價源欄、label_end **只**從此取。
    events：驗證後匯入表（symbol／direction／entry_price_semantic／label_definition context；必填）。
    """
    if events is None or events.empty:
        raise ValueError("to_return_series: 需 events= context（symbol/direction/label_definition）")
    for col in ("event_id", "symbol", "direction", "entry_price_semantic", "label_definition"):
        if col not in events.columns:
            raise ValueError(f"to_return_series: events 缺欄 {col}")
    ev = events.set_index("event_id")
    if not (ev["entry_price_semantic"] == entry_semantic).all():
        raise ValueError("to_return_series: entry_semantic 與 events.entry_price_semantic 不一致（W8 禁混用）")
    ld_key = {"rule_id": label_definition.get("rule_id"), "canonical_digest": label_definition.get("canonical_digest"),
              "window": label_definition.get("window"), "label_return_mode": label_definition.get("label_return_mode", "close_to_close")}
    bad = [e for e, d in ev["label_definition"].items()
           if {k: d.get(k) for k in ld_key} != {**ld_key, "label_return_mode": d.get("label_return_mode", "close_to_close")}]
    if bad:
        raise ValueError(f"to_return_series: label_definition 與 events 不一致（W8：horizon 由 label_definition 唯一決定）：{bad[:3]}")

    sig = pd.Series(rule_or_scores) if not isinstance(rule_or_scores, pd.Series) else rule_or_scores
    if sig.dtype == bool:
        signaled = set(sig.index[sig])
    else:
        signaled = set(sig.index[sig.astype(float) >= float(score_threshold)])

    rec = receipts.event_level.set_index("event_id")
    rows = []
    for eid in sorted(signaled):
        if eid not in rec.index:
            raise ValueError(f"to_return_series: 訊號事件 {eid} 無對齊收據（禁自行推導時點）")
        r = rec.loc[eid]
        symbol = ev.loc[eid, "symbol"]
        if symbol not in bars:
            raise ValueError(f"to_return_series: bars 缺 symbol {symbol}")
        b = bars[symbol]
        ot = b["open_time_ms"].to_numpy().astype("int64")
        ct = b["close_time_ms"].to_numpy().astype("int64")
        i_entry = int(np.searchsorted(ot, int(r["entry_price_source_bar_open_ms"])))
        if i_entry >= len(ot) or ot[i_entry] != int(r["entry_price_source_bar_open_ms"]):
            raise ValueError(f"to_return_series: {eid} entry 價源 bar 不在 bars")
        field = str(r["entry_price_source_field"])
        if field not in ("open", "close"):
            raise ValueError(f"to_return_series: {eid} entry_price_source_field {field!r} 非 open/close")
        entry = float(b[field].to_numpy()[i_entry])
        i_exit = int(np.searchsorted(ct, int(r["label_end_ms"])))
        if i_exit >= len(ct) or ct[i_exit] != int(r["label_end_ms"]):
            raise ValueError(f"to_return_series: {eid} label_end bar 不在 bars")
        exit_ = float(b["close"].to_numpy()[i_exit])
        if not (np.isfinite(entry) and np.isfinite(exit_) and entry > 0 and exit_ > 0):
            raise ValueError(f"to_return_series: {eid} 價格非有限正值")
        sign = 1.0 if ev.loc[eid, "direction"] == "long" else -1.0
        rows.append((int(r["entry_at_ms"]), int(r["label_end_ms"]), eid, sign * (exit_ / entry - 1.0)))
    rows.sort()
    out = pd.Series([x[3] for x in rows], index=[x[2] for x in rows], dtype=float, name="hold_return")
    span_ms = (max(x[1] for x in rows) - min(x[0] for x in rows)) if rows else 0
    out.attrs["span_years"] = float(span_ms / _MS_PER_YEAR)
    out.attrs["entry_semantic"] = entry_semantic
    out.attrs["label_definition"] = dict(ld_key)
    out.attrs["t_semantics"] = _T_SEMANTICS
    out.attrs["entry_at_ms_by_event"] = {x[2]: int(x[0]) for x in rows}   # 觀測軸時序收據（PBO 聯集軸依此排序）
    out.attrs["source_artifact_hash"] = receipt_digest(out)               # 綁 index＋values＋entry＋ld（消費端重算比對）
    return out


# --------------------------------------------------------------------------- ledger
def record_candidate(ledger_path: LedgerKey, candidate_meta: Dict[str, Any]) -> None:
    """寫一筆 candidate 至 GAP-1 帳本（唯一合法寫入口 `append_trial_attempt`）＋provenance sidecar。

    candidate_meta 必含：`candidate_id`、`evaluation_id`、`returns`（CandidateReturns）、`rule_digest`、`seed`、
    `input_digest`、`command`（可重播命令）、`expected`（oracle 預期 'pass'|'fail'）；選填 `attempt_index`（預設 0）、`ts`。
    寫入順序：全部驗證 → **sidecar**（自帶 flock）→ `append_trial_attempt`（GAP-1 自帶 flock）；
    誠實邊界：兩檔非同一交易——帳本 append 失敗只留 provenance 孤兒（不影響 N，`provenance_reconcile` 可列出）；
    反向「帳本有、sidecar 無」由 `run_dsr_pbo` 逐 evaluation 對帳 ⇒ unavailable。
    metric 固定 `sharpe`／`per_period`（由 return series 算；退化 ⇒ metric_valid=False、state=failed）。
    """
    if not isinstance(ledger_path, LedgerKey):
        raise TypeError("record_candidate: ledger_path 須為 LedgerKey（檔名由 GAP-1 ledger_path 推導）")
    # CODEX-R1-P1-04：每 oracle 必記可重播命令＋預期 fail/pass——command／expected 必填非空，寫任何檔前先驗
    for k in ("candidate_id", "evaluation_id", "returns", "rule_digest", "seed", "input_digest", "command", "expected"):
        if k not in candidate_meta or candidate_meta[k] is None or (isinstance(candidate_meta[k], str) and not candidate_meta[k].strip()):
            raise ValueError(f"record_candidate: candidate_meta 缺 {k}（provenance 必填；未寫入任何檔）")
    if str(candidate_meta["expected"]) not in ("pass", "fail"):
        raise ValueError("record_candidate: expected 須為 'pass'|'fail'")
    if str(candidate_meta.get("metric_kind", METRIC_KIND_RETURN_SERIES)).lower() != METRIC_KIND_RETURN_SERIES:
        raise MetricTypeError(f"record_candidate: metric_kind={candidate_meta.get('metric_kind')!r} 非 return_series")
    cr: CandidateReturns = candidate_meta["returns"]
    _assert_return_series(cr, "record_candidate")
    if cr.candidate_id != candidate_meta["candidate_id"]:
        raise ValueError("record_candidate: candidate_id 與 returns.candidate_id 不符")

    vals = cr.returns.to_numpy(dtype=float)
    ppy = _periods_per_year(cr.returns)
    sr = compute_sharpe(vals, periods_per_year=int(round(ppy)) if ppy >= 1 else 1)
    valid = sr.status == "ok" and np.isfinite(sr.value_per_period)
    ts = str(candidate_meta.get("ts") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    record = {
        "research_session_id": ledger_path.research_session_id,
        "dataset_key": ledger_path.dataset_key,
        "candidate_id": str(candidate_meta["candidate_id"]),
        "evaluation_id": str(candidate_meta["evaluation_id"]),
        "attempt_index": int(candidate_meta.get("attempt_index", 0)),
        "state": "complete" if valid else "failed",
        "metric_name": "sharpe",
        "metric_value": float(sr.value_per_period) if valid else 0.0,
        "metric_unit": "per_period",
        "metric_valid": bool(valid),
        "input_artifact_hash": str(cr.returns.attrs.get("source_artifact_hash") or candidate_meta["input_digest"]),
        "ts": ts,
    }
    # 寫入順序（CODEX-R2-P1-01）：**sidecar 先、帳本後**——帳本 append 失敗只留 provenance 孤兒（不影響 N）；
    # 反向「帳本有、sidecar 無」由 run_dsr_pbo 消費端 `_provenance_complete` 檢查 ⇒ unavailable（fail-closed）。
    prov_path = _provenance_path(ledger_path)
    prov = {
        "candidate_id": record["candidate_id"], "evaluation_id": record["evaluation_id"],
        "rule_digest": str(candidate_meta["rule_digest"]), "seed": int(candidate_meta["seed"]),
        "input_digest": str(candidate_meta["input_digest"]), "input_artifact_hash": record["input_artifact_hash"],
        "n_trades": int(len(vals)), "span_years": float(cr.returns.attrs.get("span_years", float("nan"))),
        "entry_semantic": cr.returns.attrs.get("entry_semantic"), "label_definition": cr.returns.attrs.get("label_definition"),
        "command": str(candidate_meta["command"]), "expected": str(candidate_meta["expected"]), "ts": ts,
    }
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    with _ledger._ledger_lock(prov_path, exclusive=True):
        with prov_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(prov, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    _ledger.append_trial_attempt(research_session_id=ledger_path.research_session_id,
                                 dataset_key=ledger_path.dataset_key, record=record)


def _provenance_path(key: LedgerKey):
    return _ledger.ledger_path(research_session_id=key.research_session_id,
                               dataset_key=key.dataset_key).with_suffix(".provenance.jsonl")


def _jsonl_rows(path) -> list:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _read_provenance_pairs(key: LedgerKey) -> set:
    """sidecar 之 {(candidate_id, evaluation_id)}；檔缺 ⇒ 空。"""
    return {(str(r["candidate_id"]), str(r["evaluation_id"])) for r in _jsonl_rows(_provenance_path(key))
            if "candidate_id" in r and "evaluation_id" in r}


def _read_ledger_pairs(key: LedgerKey) -> set:
    """帳本 schema-valid 列之 {(candidate_id, evaluation_id)}（與 `read_trial_ledger` 同一合法性判準；只讀不寫）。"""
    contract = _ledger.load_strategy_validation_contract()
    schema = contract["ledger_record_keys"]["keys"]
    p = _ledger.ledger_path(research_session_id=key.research_session_id, dataset_key=key.dataset_key)
    pairs = set()
    for r in _jsonl_rows(p):
        if _ledger._row_is_valid(r, schema, contract) and r["research_session_id"] == key.research_session_id \
                and r["dataset_key"] == key.dataset_key:
            pairs.add((str(r["candidate_id"]), str(r["evaluation_id"])))
    return pairs


def provenance_reconcile(ledger_path: LedgerKey) -> Dict[str, Any]:
    """帳本 vs sidecar **逐 evaluation** 對帳（CODEX-R3-P1-01：同 candidate 多 evaluation_id，按 candidate 聚合會吞孤兒）。
    `ledger_without_provenance`：帳本 evaluation 缺 sidecar（⇒ DSR/PBO 不可用）；
    `provenance_without_ledger`：sidecar 孤兒（帳本 append 失敗留下；不影響 N，列出供對帳）。值為 "candidate_id:evaluation_id"。"""
    lr = _ledger.read_trial_ledger(research_session_id=ledger_path.research_session_id, dataset_key=ledger_path.dataset_key)
    ledger_pairs = _read_ledger_pairs(ledger_path)
    prov_pairs = _read_provenance_pairs(ledger_path)
    fmt = lambda s: sorted(f"{c}:{e}" for c, e in s)  # noqa: E731
    return {
        "ledger_status": lr.status,
        "n_ledger_evaluations": len(ledger_pairs),
        "n_provenance_rows": len(prov_pairs),
        "ledger_without_provenance": fmt(ledger_pairs - prov_pairs),
        "provenance_without_ledger": fmt(prov_pairs - ledger_pairs),
        "complete": bool(lr.status == "ok" and ledger_pairs and ledger_pairs <= prov_pairs),
    }


def _periods_per_year(s: pd.Series) -> float:
    years = float(s.attrs.get("span_years", 0.0) or 0.0)
    return float(len(s) / years) if years > 0 else 0.0


def _period_returns(cr: CandidateReturns) -> PeriodReturns:
    vals = cr.returns.to_numpy(dtype=float)
    ppy = _periods_per_year(cr.returns)
    ok = ppy > 0 and len(vals) >= 2
    return PeriodReturns(
        values=vals, t_semantics=_T_SEMANTICS, n_obs=int(len(vals)), periods_per_year=float(ppy),
        annualization_source="resolved" if ok else "",
        source_artifact_hash=str(cr.returns.attrs.get("source_artifact_hash", "")),
        status="ok" if ok else "unavailable",
        reason="" if ok else "annualization_unresolved",
    )


# --------------------------------------------------------------------------- DSR/PBO/MinBTL
def run_dsr_pbo(
    ledger_path: LedgerKey,
    returns_by_candidate: Mapping[str, CandidateReturns],
    *,
    target_sharpe: float = 1.0,
    s_blocks: int = 8,
    selection_metric: str = "sharpe",
) -> Dict[str, Any]:
    """N 從 ledger 讀 → champion DSR（ledger_cross_trial）＋PBO（CSCV）＋MinBTL 資格。

    ledger 空／不可讀 ⇒ 三者 `unavailable`（reason 傳遞）；return series 長度不足 MinBTL 前提 ⇒ `eligible=False` loud。
    PBO 之觀測軸＝各候選訊號事件聯集（依 entry 時間排序），未出手者 0 報酬（無部位）。
    """
    if not isinstance(ledger_path, LedgerKey):
        raise TypeError("run_dsr_pbo: ledger_path 須為 LedgerKey")
    for cid, cr in returns_by_candidate.items():
        _assert_return_series(cr, f"run_dsr_pbo[{cid}]")
        if cr.candidate_id != cid:
            raise ValueError(f"run_dsr_pbo: key {cid!r} ≠ returns.candidate_id {cr.candidate_id!r}")

    lr = _ledger.read_trial_ledger(research_session_id=ledger_path.research_session_id, dataset_key=ledger_path.dataset_key)
    out: Dict[str, Any] = {
        "statistic_kind": "dsr_pbo_bridge",
        "ledger": {"status": lr.status, "reason": lr.reason, "n_for_dsr": int(lr.n_for_dsr), "n_evaluated": int(lr.n_evaluated),
                   "n_candidates_considered": int(lr.n_candidates_considered), "n_rows_rejected": int(lr.n_rows_rejected),
                   "n_semantics": lr.n_semantics, "snapshot_hash": lr.snapshot_hash},
        "n_trials_source": "ledger",
    }
    if lr.status != "ok" or not returns_by_candidate:
        reason = lr.reason if lr.status != "ok" else "no_candidates"
        out.update({"capability_status": "unavailable", "reason": reason,
                    "dsr": {"status": "unavailable", "reason": reason},
                    "pbo": {"status": "unavailable", "reason": reason},
                    "eligibility": {"status": "unavailable", "reason": reason}})
        return out

    # CODEX-R2-P1-01：每個帳本候選須有 provenance sidecar 列，否則 unavailable（sidecar 缺＝規則 digest／seed／命令不可追）
    recon = provenance_reconcile(ledger_path)
    out["provenance_reconcile"] = recon
    if recon["ledger_without_provenance"]:
        reason = "provenance_incomplete"
        out.update({"capability_status": "unavailable", "reason": reason,
                    "dsr": {"status": "unavailable", "reason": reason},
                    "pbo": {"status": "unavailable", "reason": reason},
                    "eligibility": {"status": "unavailable", "reason": reason}})
        return out
    # CODEX-R1-P1-02：DSR／MinBTL 前先要求輸入候選集 == ledger 候選集（未記帳候選不得成 champion；禁跳過 ledger 直餵）
    if frozenset(returns_by_candidate) != frozenset(lr.candidate_ids):
        reason = "universe_provenance_unverifiable"
        out.update({"capability_status": "unavailable", "reason": reason,
                    "candidate_set_mismatch": {"input": sorted(returns_by_candidate), "ledger": sorted(lr.candidate_ids)},
                    "dsr": {"status": "unavailable", "reason": reason},
                    "pbo": {"status": "unavailable", "reason": reason},
                    "eligibility": {"status": "unavailable", "reason": reason}})
        return out

    # champion＝per-period Sharpe 最大（平手取 candidate_id 最小）
    sharpes = {}
    for cid, cr in returns_by_candidate.items():
        pr = _period_returns(cr)
        sr = compute_sharpe(pr.values, periods_per_year=int(round(pr.periods_per_year)) if pr.periods_per_year >= 1 else 1)
        sharpes[cid] = float(sr.value_per_period) if sr.status == "ok" else float("nan")
    finite = {c: v for c, v in sharpes.items() if np.isfinite(v)}
    champion = sorted(finite, key=lambda c: (-finite[c], c))[0] if finite else sorted(returns_by_candidate)[0]
    pr_champ = _period_returns(returns_by_candidate[champion])
    dsr = deflated_sharpe(period_returns=pr_champ, ledger_result=lr, variance_source="ledger_cross_trial",
                          n_semantics=lr.n_semantics)
    out["champion"] = champion
    out["sharpe_per_period_by_candidate"] = sharpes
    out["dsr"] = asdict(dsr)

    # MinBTL：t_years＝champion 序列跨度；N 從 ledger
    span = float(pr_champ.values.size and returns_by_candidate[champion].returns.attrs.get("span_years", 0.0) or 0.0)
    if span > 0:
        el = assess_eligibility(t_years=span, ledger_result=lr, target_sharpe=float(target_sharpe))
        out["eligibility"] = asdict(el)
        if el.eligible is False:
            logger.warning("run_dsr_pbo: return series 跨度 %.3f 年不足 MinBTL 上界 %.3f 年（N=%s）", span, el.required_years_upper_bound, el.trials_used)
            out["eligibility"]["loud"] = "return_series_shorter_than_min_btl"
    else:
        out["eligibility"] = {"status": "unavailable", "reason": "span_unknown"}

    # PBO：聯集觀測軸；ledger 候選集須與輸入一致（universe guard）
    ids = sorted(returns_by_candidate)
    if len(ids) < 2:
        out["pbo"] = {"status": "unavailable", "reason": "single_candidate"}
    else:
        # 觀測軸＝entry 時間序（CODEX-R1-P1-03／COMPOSER-R1-P2-02／GROK-R1-P1-01：字串序 ≠ 時序 ⇒ CSCV 塊切壞）；
        # 時間戳只取 to_return_series 收據 attrs.entry_at_ms_by_event；同事件跨候選時間戳不一致 ⇒ fail-closed
        entry_at: Dict[str, int] = {}
        for cid in ids:
            for e, t in returns_by_candidate[cid].returns.attrs["entry_at_ms_by_event"].items():
                if e in entry_at and entry_at[e] != int(t):
                    raise ValueError(f"run_dsr_pbo: 事件 {e} 於候選間 entry_at_ms 不一致（收據衝突）")
                entry_at[e] = int(t)
        union = sorted({e for cid in ids for e in returns_by_candidate[cid].returns.index}, key=lambda e: (entry_at[e], e))
        M = np.zeros((len(union), len(ids)), dtype=float)
        for j, cid in enumerate(ids):
            M[:, j] = returns_by_candidate[cid].returns.reindex(union).fillna(0.0).to_numpy(dtype=float)
        if len(union) < int(s_blocks):
            out["pbo"] = {"status": "unavailable", "reason": "n_obs_below_s_blocks", "n_obs": len(union), "s_blocks": int(s_blocks)}
        else:
            prov = UniverseProvenance(selection_free=True, source="ledger_all_candidates",
                                      candidate_set_hash=candidate_set_hash(ids), candidate_count=len(ids),
                                      declared_by="candidate_ledger")
            pbo = probability_of_backtest_overfitting(
                returns_matrix=M, n_obs=len(union), n_candidates=len(ids), candidate_ids=ids, s_blocks=int(s_blocks),
                selection_metric=selection_metric, universe_provenance=prov, ledger_result=lr,
            )
            out["pbo"] = {**asdict(pbo), "n_obs": len(union), "observation_axis": "union_of_signaled_events_sorted_by_entry_at_ms_zero_when_flat",
                          "observation_axis_first_last_entry_ms": [entry_at[union[0]], entry_at[union[-1]]]}
    out["capability_status"] = "ok"
    out["reason"] = None
    return out


__all__ = ["CandidateReturns", "LedgerKey", "MetricTypeError", "METRIC_KIND_RETURN_SERIES",
           "provenance_reconcile", "receipt_digest", "record_candidate", "run_dsr_pbo", "to_return_series"]
