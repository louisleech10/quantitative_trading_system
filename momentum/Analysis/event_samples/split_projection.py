"""SPLITUNIFY B2b：由 canonical K 線 holdout **投影**出 `EventSplitPlan`（純函式）。

規格：`docs/SPLITUNIFY_SPEC.md`（v5）C-0／C-1／C-2／C-3／C-4／C-5；
凍結鏈：`docs/GAP3_EVENT_UX_SPEC.D-002.md`、`docs/GAP3_EVENT_SPEC_AMENDMENTS.md`。

出生理由：平台原本有**兩個入口各自產切分**（事件掃描端 `split_events` 與 IC 端
`_build_holdout_split_plan`），同一批事件會得到兩個互相矛盾的驗證段數字。
本模組把事件側降為**投影容器**——邊界只有一個來源（`momentum.core.split_preview.holdout_boundary`）。

🔴 **純函式**：無 log、無 I/O、不讀 config、不改輸入（解耦 R1：不 import `api`）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples.event_split import (
    _degraded_flags,
    build_time_clusters,
    time_cluster_bucket_ms,
)
from momentum.Analysis.event_samples.types import AlignmentReceipts, EventManifest, EventSplitPlan
from momentum.core.split_preview import assert_epoch_ms_array, assert_positional_rows

_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "split_unify.json"
_EVENT_IMPORT_CONTRACT = (
    Path(__file__).resolve().parents[1] / "contracts" / "event_import_contract.json"
)


def _load_closed_set(path: Path, key: str) -> tuple:
    """自契約 JSON 讀封閉值集；缺鍵或空集合 ⇒ **import 期** raise（SPEC C-8）。

    禁在本模組手打第二份值集——那正是本票要消滅的「兩份真相源」形態。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data.get(key)
    if not values:
        raise ValueError(f"{path.name}: 缺鍵或空值集 {key!r}（fail-closed，不補預設）")
    return tuple(values)


#: fail-closed reason 之封閉集合（字面唯一住 `split_unify.json`）。
FAIL_CLOSED_REASONS = _load_closed_set(_CONTRACT_PATH, "fail_closed_reasons")
#: canonical 切分權威值集。
SPLIT_AUTHORITY_VALUES = _load_closed_set(_CONTRACT_PATH, "split_authority_values")
#: purge reason **沿用既有契約**，不在 `split_unify.json` 另造（SPEC C-3）。
PURGE_REASONS = _load_closed_set(_EVENT_IMPORT_CONTRACT, "split_purge_reasons")

_REASON_MULTI_SYMBOL = "multi_symbol_projection_unsupported"
_REASON_MISSING_TRAIN = "missing_train_plan"
_REASON_MISSING_TEST = "missing_test_plan"
_PURGE_REASON = "interval_crosses_split_boundary"

for _r in (_REASON_MULTI_SYMBOL, _REASON_MISSING_TRAIN, _REASON_MISSING_TEST):
    if _r not in FAIL_CLOSED_REASONS:  # pragma: no cover - import 期契約自證
        raise ValueError(f"split_unify.json 缺 fail-closed reason {_r!r}")
if _PURGE_REASON not in PURGE_REASONS:  # pragma: no cover - import 期契約自證
    raise ValueError(f"event_import_contract.json 缺 purge reason {_PURGE_REASON!r}")

#: `event_keys` 之必填欄（SPEC C-4；R3 之 E2）。
EVENT_KEY_COLUMNS = (
    "event_id",
    "feature_cutoff_ms",
    "label_start_ms",
    "label_end_ms",
    "symbol",
    "timeframe",
)


def _index_as_ms(index: Any) -> np.ndarray:
    """把 `pd.Index` 正規化為 **epoch 毫秒 int64** 陣列。

    🔴 SPLITUNIFY 之時鐘一律毫秒；**不呼叫** `_normalize_ic_time_index`——那支是
    「秒」語意，餵毫秒會 raise（`ic_filter_orchestrator.py:269-271`；SPEC C-4／R2 之 D7）。
    🔴 單位政策**共用** `split_preview.assert_epoch_ms_array`（B2b review：codex／grok／主委
    三方獨立命中我原本在此手寫 `1e11` ＝ 第二份 policy），且該支是**逐元素**檢查——
    原本的 `np.all(...)` 對**混合**單位會直接放行。
    """
    idx = pd.Index(index)
    if isinstance(idx, pd.DatetimeIndex):
        if idx.hasnans:
            raise ValueError("split_projection: feature_index 含 NaT（fail-closed）")
        return (idx.asi8 // 10 ** 6).astype("int64")
    return assert_epoch_ms_array(np.asarray(idx), role="split_projection: feature_index")


def build_event_keys(
    receipts: AlignmentReceipts,
    *,
    selected_timeframe: str,
) -> pd.DataFrame:
    """由對齊收據組出投影所需的 **keyed** 事件表（SPEC C-4；R4 之 F2）。

    🔴 **producer 具名在此，B3 只傳遞、不臨時組裝**。理由（`CODEX-R3-P1-01`／`R4-P1-02`）：
    `dedupe.py` 會依 `(label_start_ms, event_id)` **重排** manifest，
    `receipts.per_tf` 每個 `(event_id, timeframe)` 可有多列 ⇒ 用 positional zip 對位會
    **靜默錯分**，連 golden 的 oracle 都可能對錯 event。

    🔴 `manifest.table` 只 merge trigger `timeframe`、**沒有** `feature_cutoff_ms`
    ⇒ 不能用它代替 per-TF cutoff。

    每個事件在 `selected_timeframe` 下必須**恰有一列** `per_tf`；否則 raise
    （多 TF 之 `(event_id, timeframe)` 複合鍵為殘留 `SU-RESID-2`，本票不解）。
    """
    per_tf = receipts.per_tf
    event_level = receipts.event_level
    if per_tf is None or event_level is None:
        raise ValueError("build_event_keys: receipts 缺 per_tf 或 event_level（fail-closed）")

    selected = per_tf.loc[per_tf["timeframe"] == str(selected_timeframe)]
    if selected.empty:
        raise ValueError(
            f"build_event_keys: per_tf 無 timeframe={selected_timeframe!r} 之列（fail-closed）"
        )
    dupes = selected["event_id"][selected["event_id"].duplicated()].unique().tolist()
    if dupes:
        raise ValueError(
            f"build_event_keys: timeframe={selected_timeframe!r} 下事件有多列 per_tf："
            f"{sorted(dupes)[:5]}——本票要求每事件恰一列（殘留 SU-RESID-2）"
        )

    merged = event_level.merge(
        selected[["event_id", "feature_cutoff_ms"]], on="event_id", how="inner", validate="1:1"
    )
    missing = set(event_level["event_id"]) - set(merged["event_id"])
    if missing:
        raise ValueError(
            f"build_event_keys: {len(missing)} 個事件在 timeframe={selected_timeframe!r} 下缺 cutoff"
            f"（例：{sorted(missing)[:3]}）——缺就是缺，不補預設"
        )
    out = merged[
        ["event_id", "feature_cutoff_ms", "label_start_ms", "label_end_ms", "symbol", "timeframe"]
    ].copy()
    return out.reset_index(drop=True)


def derive_event_split_from_plans(
    train_plan: Any,
    test_plan: Any,
    event_keys: pd.DataFrame,
    feature_index: Any,
    *,
    manifest: EventManifest,
    bucket_ms: Optional[int] = None,
) -> EventSplitPlan:
    """由 canonical 邊界投影出**完整**的 `EventSplitPlan`（SPEC C-3／C-4／C-5）。

    🔴 **兩段式判定，先後不可調**（R3 之 E1；式子逐字採 `CODEX-R4-P1-01`）：

    1. **答案窗 purge**（保留 `event_split.py:114` 之既有 guard）——
       `train_cutoff and label_end_ms >= test_start_ms` ⇒ purged。
       `purge_gap`／`embargo` 是 **row 單位且已含在 `test_plan.row_index[0]` 這個起點裡**，
       **不得**再以毫秒相減（舊式的 `test_start` 在緩衝**之前**，canonical 的在**之後**）。
    2. **集合成員判定**——`feature_cutoff_ms ∈ feature_index[plan.row_index]` 決定 train／test；
       皆不在 ⇒ purged。**禁**以 `time_bounds` 閉區間取代集合、**禁** nearest／asof／ffill。

    少了第一段就是把事件側唯一擋標籤窗跨界洩漏的閘刪掉——`SPLITUNIFY` v3 犯過一次，
    由 `CODEX-R3-P1-02` 抓出。`M-SU-13` 之 mutation 即針對此。

    三態＝**兩個容器**（SPEC C-3）：train/test 進 `assignments`（`split_label` 仍只有兩值），
    被隔離者進**獨立**的 `purged`；多出第三值時只認兩值的下游會**靜默少算**。
    """
    missing_cols = [c for c in EVENT_KEY_COLUMNS if c not in event_keys.columns]
    if missing_cols:
        raise ValueError(f"derive_event_split_from_plans: event_keys 缺欄 {missing_cols}")

    if train_plan is None or getattr(train_plan, "row_index", None) is None:
        raise ValueError(f"{_REASON_MISSING_TRAIN}: 缺 train plan（fail-closed）")
    if test_plan is None or getattr(test_plan, "row_index", None) is None:
        raise ValueError(f"{_REASON_MISSING_TEST}: 缺 test plan（fail-closed）")
    for plan, label in ((train_plan, "train"), (test_plan, "test")):
        if getattr(plan, "index_kind", None) != "positional":
            raise ValueError(
                f"derive_event_split_from_plans: {label}_plan.index_kind="
                f"{getattr(plan, 'index_kind', None)!r}，本投影只接受 'positional'（fail-closed）"
            )

    # 🔴 多 symbol fail-closed（SPEC C-2）：實測全域 12 列 vs per-symbol 8 列，兩者不等價。
    symbols = {str(s) for s in event_keys["symbol"].unique() if s is not None}
    plan_symbols = {
        str(getattr(p, "symbol")) for p in (train_plan, test_plan)
        if getattr(p, "symbol", None) is not None
    }
    # 🔴 三道，順序有意義（SPEC C-2；B2b review `CODEX-R1-P1-02`）：
    #    ① plan 必須帶 symbol——沒有身份就無法證明邊界屬於本批；
    #    ② train/test 兩 plan 之 symbol 必須一致（否則邊界本身就跨批）；
    #    ③ 事件之 symbol 集合必須與 plan **相等**。
    #    🔴 ③ 同時涵蓋了「事件批含多個 symbol」——原本另寫的
    #    `len(symbols) > 1` 在 ③ 存在後是**冗餘**（任何多 symbol 事件批都不可能等於
    #    單一 plan symbol），留著只會變成殺不掉的 mutant／死碼，故刪除。
    if not plan_symbols:
        raise ValueError(
            f"{_REASON_MULTI_SYMBOL}: plan 未帶 symbol——無法證明邊界屬於本批（fail-closed）"
        )
    if len(plan_symbols) > 1:
        raise ValueError(
            f"{_REASON_MULTI_SYMBOL}: train/test plan 之 symbol 不同 {sorted(plan_symbols)}"
            "——邊界本身就跨批（fail-closed）"
        )
    if symbols and symbols != plan_symbols:
        raise ValueError(
            f"{_REASON_MULTI_SYMBOL}: 事件 symbol {sorted(symbols)} 與 plan symbol "
            f"{sorted(plan_symbols)} 不一致——per-symbol 投影未支援前一律擋下"
            "（禁以第一個 symbol 冒充整批，亦禁沿用不屬於本批的邊界）"
        )

    # 🔴 兩個輸入必須是**同一批**（B2b review `CODEX-R1-P1-01`）：原本只有 clusters 用到
    #    manifest，餵另一批 manifest 也會產出看起來成功的 assignment。
    #    **不接受 subset**——要子集就由呼叫端先裁好 manifest，別讓本函式猜。
    key_ids = set(event_keys["event_id"])
    man_ids = set(manifest.table["event_id"])
    if key_ids != man_ids:
        only_keys, only_man = sorted(key_ids - man_ids)[:3], sorted(man_ids - key_ids)[:3]
        raise ValueError(
            "derive_event_split_from_plans: event_keys 與 manifest 之 event_id 集合不相等"
            f"（只在 event_keys：{only_keys}；只在 manifest：{only_man}）"
            "——兩者必須是同一批，不接受 subset（fail-closed）"
        )

    index_ms = _index_as_ms(feature_index)
    train_rows = assert_positional_rows(
        train_plan.row_index, n=index_ms.size, role="derive: train_plan"
    )
    test_rows = assert_positional_rows(
        test_plan.row_index, n=index_ms.size, role="derive: test_plan"
    )
    if test_rows.size == 0:
        # 🔴 先 fail-closed，禁與 None 比較（R4 之 F1）。
        raise ValueError(f"{_REASON_MISSING_TEST}: test_plan.row_index 為空（fail-closed）")

    train_ms = set(index_ms[train_rows].tolist())
    test_ms = set(index_ms[test_rows].tolist())
    test_start_ms = int(index_ms[test_rows[0]])

    assign_rows: List[dict] = []
    purge_rows: List[dict] = []
    for rec in event_keys.to_dict("records"):
        cutoff = int(rec["feature_cutoff_ms"])
        in_train = cutoff in train_ms
        in_test = cutoff in test_ms
        if in_train and in_test:
            raise ValueError(
                f"derive_event_split_from_plans: 事件 {rec['event_id']!r} 同時落在 train 與 test"
                "——不應發生，fail-closed 不靜默取一"
            )
        # ── 第一段：答案窗 purge（優先於一切）──
        if in_train and int(rec["label_end_ms"]) >= test_start_ms:
            purge_rows.append({"event_id": rec["event_id"], "reason": _PURGE_REASON})
            continue
        # ── 第二段：集合成員判定 ──
        if in_test:
            assign_rows.append(
                {"event_id": rec["event_id"], "symbol": rec["symbol"], "split_label": "test"}
            )
        elif in_train:
            assign_rows.append(
                {"event_id": rec["event_id"], "symbol": rec["symbol"], "split_label": "train"}
            )
        else:
            purge_rows.append({"event_id": rec["event_id"], "reason": _PURGE_REASON})

    assignments = pd.DataFrame(assign_rows, columns=["event_id", "symbol", "split_label"])
    purged = pd.DataFrame(purge_rows, columns=["event_id", "reason"])
    clusters = build_time_clusters(manifest, bucket_ms)

    per_symbol_n: Dict[str, int] = {
        str(sym): int(n) for sym, n in event_keys["symbol"].value_counts().items()
    }
    n_test = int((assignments["split_label"] == "test").sum()) if not assignments.empty else 0
    summary = _build_summary(
        manifest=manifest,
        clusters=clusters,
        per_symbol_n=per_symbol_n,
        n_purged=int(len(purged)),
        n_test=n_test,
        bucket=int(time_cluster_bucket_ms(manifest, bucket_ms)),
    )
    return EventSplitPlan(
        assignments=assignments, purged=purged, clusters=clusters, summary=summary
    )


def _build_summary(
    *,
    manifest: EventManifest,
    clusters: pd.DataFrame,
    per_symbol_n: Dict[str, int],
    n_purged: int,
    n_test: int,
    bucket: int,
    tier_min_test_events: int = 1,
) -> Dict[str, Any]:
    """`EventSplitPlan.summary` 之 **12 個必填鍵**（SPEC C-5）。

    少一鍵，`pipeline.py:696` 會靜默丟欄、報告整段消失——與 EVTLABEL B5 那條
    「light 視圖漏 `metadata_keep_keys`」同形態。

    🔴 `insufficient_events_in_test` 改看**投影後**的 test 數；
    `single_symbol` 恆亮是**預期的**（多 symbol 已 fail-closed ⇒ 存活路徑恆 `n_symbols == 1`），
    連帶使 `tables.py:138` 之 `formal_pooled_inference_allowed` 恆 `False`——方向保守，
    **不得**為了讓它變 `True` 而清空 `degraded`（SPEC Task 2.2 要點 6／R2 之 D11）。
    """
    n_symbols = len(per_symbol_n)
    insufficient = [s for s in per_symbol_n if n_test < int(tier_min_test_events)]
    n_clusters = int(clusters["time_cluster_id"].nunique()) if not clusters.empty else 0
    return {
        "n_symbols": n_symbols,
        "per_symbol_n": per_symbol_n,
        "n_time_clusters": n_clusters,
        "avg_cluster_size": float(len(clusters) / max(1, n_clusters)),
        "degraded": _degraded_flags(n_symbols, cluster_adjusted=True),
        "loso_status": "not_evaluated",
        "insufficient_events_in_test": insufficient,
        "stats_modes": {"primary": "macro", "sensitivity": "micro"},
        "n_events_raw": int(manifest.summary["n_events_raw"]),
        "n_events_effective": manifest.summary["n_events_effective"],
        "n_purged": int(n_purged),
        "bucket_ms": int(bucket),
    }


__all__ = [
    "EVENT_KEY_COLUMNS",
    "FAIL_CLOSED_REASONS",
    "PURGE_REASONS",
    "SPLIT_AUTHORITY_VALUES",
    "build_event_keys",
    "build_time_clusters",
    "derive_event_split_from_plans",
]
