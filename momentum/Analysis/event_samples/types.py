"""GAP-3 事件樣本層共用 dataclass（docs/GAP3_EVENT_TODO.md Task B1.0）。

欄位名/枚舉/reason 字面唯一住 `momentum/Analysis/contracts/event_import_contract.json`；
本檔只定義容器形狀（R7 DTO 不跨界：事件契約 dataclass 住 momentum/）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd


@dataclass(frozen=True)
class AlignmentConfig:
    """PIT 對齊設定（Task B1.1）。

    timeframes: 需產 per-TF 收據之 TF 清單（含錨定 TF）。
    """

    timeframes: tuple = ()


@dataclass(frozen=True)
class AlignmentReceipts:
    """兩層對齊收據（SPEC D2-4／R3 Z1；欄名字面＝契約檔 receipt_schema）。

    🔴 **GAP-3 UX Task 7.0b 增 `analysis_alignment_receipt_hash`**（SPEC ③(d)）：
    分析時 receipt 之識別碼，字面已登記於契約 `receipt_schema.batch`。
    預設 `None` ＝**匯入／平台產生器路徑**（那些路徑不產生分析時 receipt）；
    只有 `prepare_analysis_windows` 會填它。
    🔴 **不得**在下游看到 `None` 就自己算一個補上——那就是「各自重算出巧合相同之值」，
    正是 SPEC ⑩ 第二條斷言要擋的形態。拿不到就是拿不到，往上報。
    """

    event_level: pd.DataFrame
    per_tf: pd.DataFrame
    analysis_alignment_receipt_hash: Optional[str] = None


@dataclass(frozen=True)
class DedupePolicyConfig:
    """去重/簇政策（Task B1.2）。

    cluster_gap_ms: 簇間隔（UTC duration ms；None ⇒ 預設＝答案窗 duration）。
    primary policy 事前固定依情境：C ⇒ cluster_first、A/B ⇒ all_with_uniqueness。
    """

    cluster_gap_ms: Optional[int] = None
    scenario: str = "C"


@dataclass(frozen=True)
class EventManifest:
    """事件 manifest（Task B1.2 產出）。"""

    table: pd.DataFrame
    summary: Dict[str, Any]
    policy: Dict[str, Any]


@dataclass(frozen=True)
class EventSplitConfig:
    """事件切分設定（Task B1.3）。

    test_fraction: 每 symbol 時間尾段比例；embargo_ms: train/test 緩衝（≥答案窗）。
    bucket_ms: time_cluster 桶寬（None ⇒ 觸發 TF 一根）。
    tier_min_test_events: test 段事件數下限（不足 ⇒ loud，不回退全樣本）。
    """

    test_fraction: float = 0.3
    embargo_ms: Optional[int] = None
    bucket_ms: Optional[int] = None
    tier_min_test_events: int = 1


@dataclass(frozen=True)
class EventSplitPlan:
    """事件切分計畫（Task B1.3 產出；不動 momentum/core/contracts.py::SplitPlan）。"""

    assignments: pd.DataFrame
    purged: pd.DataFrame
    clusters: pd.DataFrame
    summary: Dict[str, Any]


@dataclass(frozen=True)
class OracleConfig:
    """置亂 oracle 設定（Task B1.4；SPEC R2 Y5/R3 Z4 定式）。"""

    seed: int = 20260820
    n_perm: int = 1000
    q_low: float = 0.025
    q_high: float = 0.975
