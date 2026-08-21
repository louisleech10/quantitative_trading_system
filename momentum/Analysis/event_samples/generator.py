"""GAP-3 完整版事件產生器（docs/GAP3_EVENT_TODO.md Task B3.2；SPEC U6／G1–G6／R1 X13）。

輸入＝`ConditionSpec`（B3.1）＋bars（含任意 FF 特徵欄）＋多組 label 規則＋產生器設定；
輸出＝合規事件 DataFrame（**過 B1.0 `validate_event_import`，無 profile 分裂——G5**）＋provenance。

- G1：條件可引用任意 pit 特徵欄＋t₀ 結果欄（`trigger_return`）＋未來結果欄（`future_return_<h>`）；
  結果欄由 `build_evaluation_frame` 注入、角色由 `outcome_column_registry` 給定（D3）。
- G2：多組 label 一次設定——每條 `LabelRule` 一個 `label_id`，事件逐 label_id 產列（manifest，非布林覆寫）。
- G3：方向／情境／答案窗／規則摘要自動寫入每列（`direction/scenario/label_definition.window/search_rule_summary`）。
- G4：去重在產生期——復用 B1.1 `align_events`＋B1.2 `build_event_manifest`，回報原始／去重後數。
- G6：全 K 線標籤重算＝**呼叫 B2.5 `evaluate_all_bars`，禁平行實作**；eligibility／label 規則亦直接
  復用 `all_bars_eval._is_eligible`／`_label_from_rule`（同一分母、同一標籤公式）。
- `control_kind=platform_same_trigger_rule` 自本 Task 啟用：同一觸發規則下 label=0 者即平台產之控制組。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.core.logging import get_logger
from momentum.Analysis.event_samples import all_bars_eval as _ab
from momentum.Analysis.event_samples.alignment import align_events, n_dropped_by_reason
from momentum.Analysis.event_samples.condition_engine import ConditionSpec, evaluate_condition
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig

logger = get_logger(__name__)

TRIGGER_RETURN_COL = "trigger_return"
FUTURE_RETURN_PREFIX = "future_return_"
_BAR_COLS = ("open_time_ms", "close_time_ms", "open", "close")


@dataclass(frozen=True)
class LabelRule:
    """一組 label 規則（close_to_close：dir·(close[t0+h]/close[t0]−1) ≥ threshold ⇒ 1）。

    label_return_mode 目前只實作 `close_to_close`（B2.5 `_label_from_rule` 同公式）；其他值 ⇒ ValueError loud。
    """

    label_id: str
    horizon_bars: int
    threshold: float
    label_return_mode: str = "close_to_close"


@dataclass(frozen=True)
class GeneratorConfig:
    """產生器設定（事件頂層欄之來源；枚舉合法性由 B1.0 validator 判）。"""

    symbol: str
    timeframe: str
    data_snapshot_digest: str
    direction: str = "long"
    scenario: str = "C"
    decision_offset_bars: int = 0
    entry_price_semantic: str = "trigger_open"
    control_kind: str = "platform_same_trigger_rule"
    cluster_gap_ms: Optional[int] = None
    run_all_bars_eval: bool = True
    classifier_config: Optional[dict] = None
    seed: int = 20260820
    n_boot: int = 100


def outcome_column_registry(label_config: Sequence[LabelRule]) -> Dict[str, str]:
    """產生器注入之結果欄角色（D3）：`trigger_return`＝trigger_outcome、`future_return_<h>`＝future_outcome。"""
    reg = {TRIGGER_RETURN_COL: "trigger_outcome"}
    for r in label_config:
        reg[f"{FUTURE_RETURN_PREFIX}{int(r.horizon_bars)}"] = "future_outcome"
    return reg


def build_evaluation_frame(bars: pd.DataFrame, label_config: Sequence[LabelRule]) -> pd.DataFrame:
    """bars（含特徵欄）＋結果欄。結果欄為**原始**（未乘方向）報酬：
    `trigger_return`＝close/open−1（t₀ 根內）、`future_return_h`＝close[t+h]/close[t]−1（未來；只准 selection_predicate/label 角色引用）。"""
    for c in _BAR_COLS:
        if c not in bars.columns:
            raise ValueError(f"build_evaluation_frame: bars 缺欄 {c}")
    df = bars.sort_values("open_time_ms").reset_index(drop=True).copy()
    close = df["close"].astype(float)
    df[TRIGGER_RETURN_COL] = close / df["open"].astype(float) - 1.0
    for r in label_config:
        h = int(r.horizon_bars)
        df[f"{FUTURE_RETURN_PREFIX}{h}"] = close.shift(-h) / close - 1.0
    return df


def _rule_digest(rule: LabelRule, direction: str) -> str:
    payload = {"label_id": rule.label_id, "horizon_bars": int(rule.horizon_bars), "threshold": float(rule.threshold),
               "label_return_mode": rule.label_return_mode, "direction": direction}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _check_inputs(spec: ConditionSpec, bars_by_tf: Mapping[str, pd.DataFrame], label_config: Sequence[LabelRule],
                  gen_config: GeneratorConfig) -> None:
    if spec.expression_role not in ("feature", "selection_predicate"):
        raise ValueError("generate_events: spec.expression_role 須為 feature 或 selection_predicate（label 角色非選樣式）")
    if gen_config.timeframe not in bars_by_tf:
        raise ValueError(f"generate_events: bars_by_tf 缺錨定 TF {gen_config.timeframe!r}")
    if gen_config.timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"generate_events: timeframe {gen_config.timeframe!r} 不在 TIMEFRAME_SECONDS")
    if not label_config:
        raise ValueError("generate_events: label_config 不得為空（至少一組 label_id）")
    ids = [r.label_id for r in label_config]
    if len(set(ids)) != len(ids) or any(not str(i).strip() for i in ids):
        raise ValueError(f"generate_events: label_id 須唯一且非空：{ids}")
    for r in label_config:
        if int(r.horizon_bars) < 1:
            raise ValueError(f"generate_events: {r.label_id} horizon_bars 須 ≥ 1")
        if r.label_return_mode != "close_to_close":
            raise ValueError(f"generate_events: {r.label_id} label_return_mode {r.label_return_mode!r} 未實作（v1 只 close_to_close）")
    if not str(gen_config.data_snapshot_digest).strip():
        raise ValueError("generate_events: data_snapshot_digest 必填非空")
    if int(gen_config.decision_offset_bars) < 0:
        raise ValueError("generate_events: decision_offset_bars 須 ≥ 0")


def generate_events(
    spec: ConditionSpec,
    bars_by_tf: Mapping[str, pd.DataFrame],
    label_config: Sequence[LabelRule],
    gen_config: GeneratorConfig,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """依條件式產合規事件。回 (events, provenance)。

    events：過 B1.0 validator 之契約形狀 DataFrame（去重後 primary 保留集；去重前全表見 provenance['manifest']）。
    0 命中 ⇒ 空 DataFrame＋provenance.status='empty'（loud 空結果非錯）。
    只有單一類別（全正或全反）⇒ validator `missing_control_group` raise（fail-closed，不靜默）。
    """
    _check_inputs(spec, bars_by_tf, label_config, gen_config)
    tf = gen_config.timeframe
    k = int(gen_config.decision_offset_bars)
    sign = 1.0 if gen_config.direction == "long" else -1.0
    step_ms = TIMEFRAME_SECONDS[tf] * 1000

    frame = build_evaluation_frame(bars_by_tf[tf], label_config)
    mask = evaluate_condition(spec, frame).to_numpy()
    n_rows = int(len(frame))
    hits = np.flatnonzero(mask)
    open_ = frame["open"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    ot = frame["open_time_ms"].to_numpy().astype("int64")

    rule_summary = json.dumps({
        "expression": spec.expression, "canonical_digest": spec.canonical_digest,
        "expression_role": spec.expression_role, "column_roles": dict(spec.column_roles),
        "max_lookback": int(spec.max_lookback),
    }, sort_keys=True, ensure_ascii=False)
    gen_payload = {"generator_config": asdict(gen_config), "rules": [asdict(r) for r in label_config],
                   "condition_digest": spec.canonical_digest}
    source_digest = hashlib.sha256(json.dumps(gen_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    label_manifest = [{"label_id": r.label_id, "horizon_bars": int(r.horizon_bars), "threshold": float(r.threshold),
                       "label_return_mode": r.label_return_mode, "canonical_digest": _rule_digest(r, gen_config.direction)}
                      for r in label_config]

    prov: Dict[str, Any] = {
        "status": "ok",
        "expression": spec.expression,
        "canonical_digest": spec.canonical_digest,
        "expression_role": spec.expression_role,
        "column_roles": dict(spec.column_roles),
        "selection_uses_outcome_columns": any(v != "pit_feature" for v in spec.column_roles.values()),
        "max_lookback": int(spec.max_lookback),
        "label_manifest": label_manifest,
        "n_rows": n_rows,
        "n_hits": int(len(hits)),
        "always_true": bool(n_rows > 0 and len(hits) == n_rows),
        "generator_config": asdict(gen_config),
        "source_file_digest": source_digest,
    }
    if prov["always_true"]:
        logger.warning("generate_events: 條件恆真（%s 列全命中）", n_rows)

    rows: List[dict] = []
    dropped: Dict[str, int] = {}
    n_candidates = 0
    for i in hits:
        i = int(i)
        for r, lm in zip(label_config, label_manifest):
            n_candidates += 1
            h = int(r.horizon_bars)
            reason = _ab._is_eligible(i, n_rows, h, k, open_, close, ot, step_ms)   # 同一分母（B2.5）
            if reason is not None:
                dropped[reason] = dropped.get(reason, 0) + 1
                continue
            y = _ab._label_from_rule(sign, close, i, h, float(r.threshold))           # 同一標籤公式（B2.5）
            rows.append({
                "event_id": f"{gen_config.symbol}:{tf}:{int(ot[i])}:{r.label_id}",
                "symbol": gen_config.symbol,
                "timeframe": tf,
                "t0": int(ot[i]),
                "decision_offset_bars": k,
                "entry_price_semantic": gen_config.entry_price_semantic,
                "direction": gen_config.direction,
                "scenario": gen_config.scenario,
                "label": int(y),
                "label_value": float(sign * (close[i + h] / close[i] - 1.0)),
                "label_definition": {"rule_id": r.label_id, "canonical_digest": lm["canonical_digest"],
                                     "window": {"horizon_bars": h}, "label_return_mode": r.label_return_mode},
                "control_kind": gen_config.control_kind,
                "source_file_digest": source_digest,
                "data_snapshot_digest": gen_config.data_snapshot_digest,
                "search_rule_summary": rule_summary,
                "kind_source": "platform_auto",
                "event_source": "platform_generator",
                "meta": {"generator": "condition_engine", "condition_digest": spec.canonical_digest},
            })
    prov["n_candidates"] = n_candidates
    prov["n_events_raw"] = len(rows)
    prov["n_dropped_by_reason"] = dropped
    prov["accounting_ok"] = (n_candidates == len(rows) + sum(dropped.values()))
    if not prov["accounting_ok"]:
        raise RuntimeError("generate_events: 記帳守恆失敗（候選 ≠ 事件＋丟棄）")

    if not rows:
        prov["status"] = "empty"
        prov["n_events_after_dedupe"] = 0
        return pd.DataFrame(), prov

    # G5：同一 B1.0 validator（無 profile 分裂）；單類別 ⇒ missing_control_group raise
    events = validate_event_import(rows)

    # G4：去重在產生期——復用 B1.1 對齊＋B1.2 manifest
    bars_core = frame[list(_BAR_COLS)].copy()
    receipts, failures = align_events(events, {gen_config.symbol: {tf: bars_core}}, AlignmentConfig(timeframes=(tf,)))
    if len(failures):
        # 對齊層比 B2.5 eligibility 多一道「決策前須有已收盤 bar」（warmup_insufficient_<tf>）等檢查；
        # 失敗者逐事件記帳丟棄（不靜默），守恆：候選＝事件＋eligibility 丟棄＋對齊丟棄
        for reason, n_ in n_dropped_by_reason(failures).items():
            dropped[reason] = dropped.get(reason, 0) + int(n_)
        events = events[~events["event_id"].isin(set(failures["event_id"]))].reset_index(drop=True)
        prov["n_events_raw"] = int(len(events))
        prov["n_dropped_by_reason"] = dropped
        prov["accounting_ok"] = (n_candidates == len(events) + sum(dropped.values()))
        if not prov["accounting_ok"]:
            raise RuntimeError("generate_events: 記帳守恆失敗（對齊層丟棄後）")
        if events.empty:
            prov["status"] = "empty"
            prov["n_events_after_dedupe"] = 0
            return pd.DataFrame(), prov
        events = validate_event_import(events.to_dict("records"))   # 丟棄後仍須過同一 validator（單類別 ⇒ raise）
        receipts, failures = align_events(events, {gen_config.symbol: {tf: bars_core}}, AlignmentConfig(timeframes=(tf,)))
        assert len(failures) == 0
    manifest = build_event_manifest(receipts, DedupePolicyConfig(cluster_gap_ms=gen_config.cluster_gap_ms,
                                                                 scenario=gen_config.scenario), events=events)
    keep_ids = set(manifest.table.loc[manifest.table["in_primary"], "event_id"])
    deduped = events[events["event_id"].isin(keep_ids)].reset_index(drop=True)
    prov["n_events_after_dedupe"] = int(len(deduped))
    prov["dedupe"] = {**manifest.summary, "policy": manifest.policy}
    prov["manifest"] = manifest

    # G6：全 K 線標籤重算＝呼叫 B2.5（禁平行實作）。rule callable 在決策根 i−k 之分數＝「觸發於 i」
    # 之遮罩（與 evaluate_all_bars 自身 decision=ot[i−k]、label 取 close[i]→close[i+h] 之映射一致）。
    if gen_config.run_all_bars_eval:
        abe: Dict[str, Any] = {}
        for r in label_config:
            sub = events[events["label_definition"].apply(lambda d: d["rule_id"]) == r.label_id]
            prevalence_learn = float(sub["label"].mean()) if len(sub) else float("nan")

            def _rule(df_bars: pd.DataFrame, _spec=spec, _k=k) -> pd.Series:
                fr = build_evaluation_frame(df_bars, label_config)
                m = evaluate_condition(_spec, fr).astype(float)
                return m.shift(-_k) if _k else m

            cfg = {"horizon_bars": int(r.horizon_bars), "label_threshold": float(r.threshold),
                   "direction": gen_config.direction, "decision_offset_bars": k, "score_threshold": 0.5,
                   "top_q": 0.1, "prevalence_learn": prevalence_learn, "sample_design": "case_control",
                   "classifier_config": gen_config.classifier_config, "seed": gen_config.seed,
                   "n_boot": gen_config.n_boot, "label_id": r.label_id,
                   "entry_price_semantic": gen_config.entry_price_semantic, "timeframe": tf}
            rep = _ab.evaluate_all_bars(_rule, {gen_config.symbol: bars_by_tf[tf]}, cfg, manifest=manifest)
            rep["estimand_note"] = (
                "selection_predicate 引用結果欄 ⇒ 此為標籤重算而非預測力評估（D3-3）"
                if prov["selection_uses_outcome_columns"] else "rule 僅引用 pit 特徵；可作規則命中之全 K 線評估"
            )
            abe[r.label_id] = rep
        prov["all_bars_evaluation"] = abe
    return deduped, prov


__all__ = [
    "FUTURE_RETURN_PREFIX",
    "GeneratorConfig",
    "LabelRule",
    "TRIGGER_RETURN_COL",
    "build_evaluation_frame",
    "generate_events",
    "outcome_column_registry",
]
