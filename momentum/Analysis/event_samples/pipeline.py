"""GAP-3 事件樣本組合殼（docs/GAP3_EVENT_TODO.md Task B5.1）：validate → align → dedupe → split → materialize。

服務端**唯一**消費入口（`momentum/factories.create_event_sample_pipeline()` 出口）。本檔只組合 B1 純函式、不重複實作
任何檢查（R7：契約驗證唯一實作＝`import_contract.validate_event_import`）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from momentum.core.logging import get_logger
from momentum.Analysis.event_samples.alignment import align_events, n_dropped_by_reason
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.feature_materialization import materialize_features_at_decision
from momentum.Analysis.event_samples.import_contract import ContractValidationError, validate_event_import
from momentum.Analysis.event_samples.types import (
    AlignmentConfig, AlignmentReceipts, DedupePolicyConfig, EventManifest, EventSplitConfig, EventSplitPlan,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class EventPipelineConfig:
    """組合殼設定（全部轉交 B1 各 dataclass；無新字面）。

    timeframes：需 per-TF 收據之 TF 清單（空 ⇒ 只錨定 TF）。
    cluster_gap_ms：B1.2 簇間隔（None ⇒ 答案窗）。
    split：B1.3 切分設定。
    feature_config：B1.6 設定（None ⇒ 不物化特徵）。
    """

    timeframes: Tuple[str, ...] = ()
    cluster_gap_ms: Optional[int] = None
    split: EventSplitConfig = field(default_factory=EventSplitConfig)
    feature_config: Optional[dict] = None


@dataclass
class EventPipelineResult:
    """一次 run 的全部產出（各層記帳守恆：n_events == n_receipts + n_align_failures）。"""

    events: pd.DataFrame
    receipts: AlignmentReceipts
    align_failures: pd.DataFrame
    manifest: EventManifest
    split_plan: EventSplitPlan
    features: Optional[pd.DataFrame]
    feature_manifest_hash: Optional[str]
    feature_failures: Optional[pd.DataFrame]
    summary: Dict[str, Any]


class EventSamplePipeline:
    """validate→align→dedupe→split→materialize 組合殼（純組合；不 log hot loop）。"""

    # ---- 契約唯讀出口（R3：api 層只經 factories 一個出口取得 pipeline，再由此讀契約；不直 import momentum 內部）----
    @staticmethod
    def import_contract() -> dict:
        """事件匯入契約 JSON（SoT；唯讀拷貝）。"""
        from momentum.Analysis.event_samples.import_contract import load_event_import_contract

        return load_event_import_contract()

    @staticmethod
    def condition_engine_contract() -> dict:
        """條件引擎契約 JSON（含 `allowed_filtering_params`；深拷貝）。"""
        from momentum.Analysis.event_samples.condition_engine import load_condition_engine_contract

        return load_condition_engine_contract()

    @staticmethod
    def bars_from_kline_cache(symbols, timeframes, *, cache_path=None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """真實 kline bars（`bars_source.load_bars_from_kline_cache`）；服務端取 bars 的唯一入口。"""
        from momentum.Analysis.event_samples.bars_source import load_bars_from_kline_cache

        return load_bars_from_kline_cache(symbols, timeframes, cache_path=cache_path)

    def run_with_params(
        self, records, bars_by_tf, *, test_fraction: float = 0.3, embargo_ms: Optional[int] = None,
        tier_min_test_events: int = 1, timeframes: Tuple[str, ...] = (), cluster_gap_ms: Optional[int] = None,
    ) -> "EventPipelineResult":
        """純量參數版 `run`（服務端經 factories 出口呼叫、不 import momentum dataclass——R3/R7）。"""
        cfg = EventPipelineConfig(
            timeframes=tuple(timeframes), cluster_gap_ms=cluster_gap_ms,
            split=EventSplitConfig(test_fraction=float(test_fraction), embargo_ms=embargo_ms,
                                   tier_min_test_events=int(tier_min_test_events)),
        )
        return self.run(records, bars_by_tf, cfg)

    def analyze_tables(
        self, result: "EventPipelineResult", bars_by_tf: Dict[str, Dict[str, pd.DataFrame]], *,
        horizons: Tuple[int, ...] = (1, 2, 4), seed: int = 20260820, n_boot: int = 300,
    ) -> Dict[str, Any]:
        """B2 表：事件後報酬表（B2.1）＋全 K 線驗證（B2.5 `evaluate_all_bars`，rule＝事件成員：事件 t₀ 根 score=1、其餘 0）；
        辨別表需模型分數——無分數 ⇒ `not_computed`＋reason（前端顯示原因，不重算）。"""
        from momentum.Analysis.event_samples.all_bars_eval import evaluate_all_bars
        from momentum.Analysis.event_samples.tables import event_forward_return_table

        fwd = event_forward_return_table(result.manifest, result.receipts, bars_by_tf, result.split_plan,
                                         {"horizons": [int(h) for h in horizons], "seed": int(seed), "n_boot": int(n_boot)})
        disc = {"statistic_kind": "binary_discrimination", "capability_status": "not_computed",
                "reason": "no_model_scores_in_event_pipeline",
                "doc": "辨別表需 test 段模型分數（B4.1 pattern 橋或外部模型）；匯入管線本身不產分數，不在此重算統計"}
        all_bars = self._all_bars_for_events(result, bars_by_tf, seed=seed, n_boot=n_boot, evaluate_all_bars=evaluate_all_bars)
        return {"event_forward_return_table": fwd, "binary_discrimination_table": disc, "all_bars_evaluation": all_bars}

    @staticmethod
    def _all_bars_for_events(result, bars_by_tf, *, seed: int, n_boot: int, evaluate_all_bars) -> Dict[str, Any]:
        """全 K 線驗證（U11 靈魂路徑）：把匯入事件集當訊號（事件 t₀ 根 score=1、其餘 0），固定分母跑 B2.5；
        manifest_config 全自事件欄導出（label_definition.window／direction／entry_price_semantic／timeframe 批內須單值）；
        prevalence_learn＝匯入事件正例率（case-control 揭露）。"""
        ev = result.events
        tfs = sorted(set(ev["timeframe"]))
        dirs = sorted(set(ev["direction"]))
        ents = sorted(set(ev["entry_price_semantic"]))
        lds = {(d["window"]["horizon_bars"], d.get("label_return_mode", "close_to_close")) for d in ev["label_definition"]}
        if len(tfs) != 1 or len(dirs) != 1 or len(ents) != 1 or len(lds) != 1:
            return {"statistic_kind": "all_bars_evaluation", "capability_status": "not_computed",
                    "reason": "batch_not_single_valued",
                    "doc": f"全 K 線驗證需批內單一 timeframe/direction/entry_price_semantic/label_definition（得 {len(tfs)}/{len(dirs)}/{len(ents)}/{len(lds)}）"}
        (horizon, mode), = lds
        if mode != "close_to_close":
            return {"statistic_kind": "all_bars_evaluation", "capability_status": "not_computed",
                    "reason": "label_return_mode_not_supported", "doc": f"evaluate_all_bars 標籤公式為 close_to_close；批為 {mode}"}
        tf = tfs[0]
        bars = {s: bars_by_tf[s][tf] for s in sorted(set(ev["symbol"]))}
        idx = pd.MultiIndex.from_arrays([ev["symbol"].to_numpy(), ev["t0"].astype("int64").to_numpy()])
        members = pd.Series(1.0, index=idx)
        rows = []
        for s, b in bars.items():
            ot = b["open_time_ms"].astype("int64").to_numpy()
            sc = pd.Series(0.0, index=pd.MultiIndex.from_arrays([[s] * len(ot), ot]))
            hit = members.index[members.index.get_level_values(0) == s]
            sc.loc[hit] = 1.0
            rows.append(sc)
        scores = pd.concat(rows)
        cfg = {"horizon_bars": int(horizon), "label_threshold": 0.0, "direction": dirs[0],
               "decision_offset_bars": int(ev["decision_offset_bars"].iloc[0]), "score_threshold": 0.5, "top_q": 0.1,
               "prevalence_learn": float(ev["label"].mean()), "sample_design": "case_control",
               "seed": int(seed), "n_boot": int(n_boot), "label_id": "event_membership",
               "entry_price_semantic": ents[0], "timeframe": tf}
        rep = evaluate_all_bars(scores, bars, cfg, event_split_plan=result.split_plan, manifest=result.manifest)
        rep["rule"] = "event_membership (score=1 at imported event t0 bars, else 0)"
        rep["label_threshold_note"] = "threshold=0.0（signed 報酬 ≥0 ⇒ 1）；使用者標籤門檻不在事件欄，此為 all-bars 基準語意"
        return rep

    def validate(
        self, records: Union[List[dict], pd.DataFrame], *, source_bytes: Optional[bytes] = None
    ) -> Tuple[Optional[pd.DataFrame], List[Dict[str, Any]]]:
        """不 raise 之驗證：回 (正規化 df | None, failures)。failures 字面＝契約檔（唯一實作在 import_contract）。"""
        try:
            return validate_event_import(records, source_bytes=source_bytes), []
        except ContractValidationError as exc:
            return None, list(exc.failures)

    def run(
        self,
        records: Union[List[dict], pd.DataFrame],
        bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
        config: EventPipelineConfig,
        *,
        source_bytes: Optional[bytes] = None,
    ) -> EventPipelineResult:
        """全鏈；匯入不合規 ⇒ raise ContractValidationError（fail-closed，不半套）。"""
        events = validate_event_import(records, source_bytes=source_bytes)
        tfs = tuple(config.timeframes) or tuple(sorted(set(events["timeframe"])))
        receipts, failures = align_events(events, bars_by_tf, AlignmentConfig(timeframes=tfs))
        if receipts.event_level.empty:
            raise ValueError(f"EventSamplePipeline.run: 全部事件對齊失敗 {n_dropped_by_reason(failures)}（loud）")

        scenarios = sorted(set(events["scenario"]))
        if len(scenarios) != 1:
            raise ValueError(f"EventSamplePipeline.run: 批內 scenario 混值 {scenarios}（去重 policy 須單一）")
        aligned = events[events["event_id"].isin(set(receipts.event_level["event_id"]))].reset_index(drop=True)
        manifest = build_event_manifest(
            receipts, DedupePolicyConfig(cluster_gap_ms=config.cluster_gap_ms, scenario=scenarios[0]), events=aligned,
        )
        plan = split_events(manifest, config.split)

        features = fhash = ffail = None
        if config.feature_config is not None:
            features, fhash, ffail = materialize_features_at_decision(receipts, bars_by_tf, dict(config.feature_config), events=aligned)

        summary = {
            "n_input": int(len(events)),
            "n_aligned": int(len(receipts.event_level)),
            "n_align_failures": int(len(failures)),
            "align_failures_by_reason": n_dropped_by_reason(failures),
            "accounting_ok": int(len(events)) == int(len(receipts.event_level)) + int(len(failures)),
            "dedupe": {**manifest.summary, "policy": manifest.policy},
            "split": {k: v for k, v in plan.summary.items() if k != "per_symbol_n"},
            "n_train": int((plan.assignments["split_label"] == "train").sum()) if not plan.assignments.empty else 0,
            "n_test": int((plan.assignments["split_label"] == "test").sum()) if not plan.assignments.empty else 0,
            "n_purged": int(len(plan.purged)),
            "features": None if features is None else {
                "n_rows": int(len(features)), "n_cols": int(features.shape[1]),
                "n_failures": int(len(ffail)) if ffail is not None else 0, "feature_manifest_hash": fhash,
            },
        }
        if not summary["accounting_ok"]:
            raise RuntimeError("EventSamplePipeline.run: 對齊記帳守恆失敗")
        return EventPipelineResult(
            events=aligned, receipts=receipts, align_failures=failures, manifest=manifest, split_plan=plan,
            features=features, feature_manifest_hash=fhash, feature_failures=ffail, summary=summary,
        )


__all__ = ["EventPipelineConfig", "EventPipelineResult", "EventSamplePipeline"]
