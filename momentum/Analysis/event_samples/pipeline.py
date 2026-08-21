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
