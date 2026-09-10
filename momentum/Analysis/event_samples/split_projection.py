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
from momentum.core.split_preview import (
    assert_epoch_ms_array,
    assert_positional_rows,
    boundary_hash as _boundary_hash,
)

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
#: Task 3.3：呼叫端拿不到 post-trim feature universe ⇒ 明示 event-study-only（SPEC C-0 決議③）。
_REASON_NO_UNIVERSE = "canonical_feature_universe_unavailable"
#: B3 自查發現之第五種 fail-closed 情形：train/test 兩 plan 建在不同 universe 上
#: ⇒ 同一個 row_index 指到不同時刻。
#: 🔴 **刻意不進 `split_unify.json` 的封閉值集**：登記會動到已戳記之 SPEC 的值集與前端枚舉面，
#:    而守衛的保護力不依賴字面（下方以明文 ValueError 擋）。是否升格為具名 reason 交 B3 review 裁定。
_UNREGISTERED_UNIVERSE_MISMATCH = "train/test plan 之 base_universe_hash 不同"
_PURGE_REASON = "interval_crosses_split_boundary"
#: event-study-only 之估計量範圍標記（SPEC C-0 決議③(b)）；字面唯一住 `split_unify.json`。
ESTIMAND_SCOPE_VALUES = _load_closed_set(_CONTRACT_PATH, "estimand_scope_values")
_ESTIMAND_FULL_SAMPLE = "full_sample_not_oos"

if _ESTIMAND_FULL_SAMPLE not in ESTIMAND_SCOPE_VALUES:  # pragma: no cover - import 期契約自證
    raise ValueError(f"split_unify.json 缺 estimand_scope {_ESTIMAND_FULL_SAMPLE!r}")


def canonical_universe_unavailable_reason() -> str:
    """Task 3.3：capability reason 字面之**唯一** Python 出口（自契約讀，禁手打）。"""
    return _REASON_NO_UNIVERSE


def full_sample_estimand_scope() -> str:
    """Task 3.3 ③：`estimand_scope` 字面之**唯一** Python 出口（自契約讀，禁手打）。"""
    return _ESTIMAND_FULL_SAMPLE


def build_split_unify_disclosure(
    *,
    n_test: Optional[int],
    test_timestamps_ms: Any,
    per_symbol_counts: Optional[Dict[str, int]] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """`metadata.split_unify` 之**唯一**產生點（Task 4.1／SPEC C-6）。

    🔴 **fail-closed 時 `n_test` 為 `None` 而非 `0`**：0 讀起來是「算過，結果是零個」，
    None 才是「沒得算」。這兩件事在報告上長得一樣就是本票要消滅的假數字。
    `reason` 非空 ⇒ 視為 fail-closed，`n_test`／`boundary_hash`／`per_symbol_counts`
    一律清成 `None`／`{}`——留半套數字比不給更糟（讀的人不知道哪一半可信）。

    `reason` 必須在 `split_unify.json` 之封閉集合內；`split_authority` 亦自契約讀，禁手打。
    """
    if reason is not None and reason not in FAIL_CLOSED_REASONS:
        raise ValueError(
            f"build_split_unify_disclosure: reason={reason!r} 不在契約封閉集合內"
            f"（{sorted(FAIL_CLOSED_REASONS)}；fail-closed，不接受自造字面）"
        )
    authority = SPLIT_AUTHORITY_VALUES[0]
    if reason is not None:
        return {
            "n_test": None,
            "split_authority": authority,
            "boundary_hash": None,
            "per_symbol_counts": {},
            "reason": reason,
        }
    if n_test is None:
        raise ValueError(
            "build_split_unify_disclosure: 沒有 reason 卻也沒有 n_test"
            "——「算不出來」必須指名原因（fail-closed）"
        )
    counts = {str(k): int(v) for k, v in (per_symbol_counts or {}).items()}
    total = sum(counts.values())
    if counts and total != int(n_test):
        raise ValueError(
            f"build_split_unify_disclosure: per_symbol_counts 合計 {total} != n_test {int(n_test)}"
            "——兩個數字在同一份揭露裡互相矛盾（fail-closed）"
        )
    return {
        "n_test": int(n_test),
        "split_authority": authority,
        "boundary_hash": _boundary_hash(test_timestamps_ms),
        "per_symbol_counts": counts,
        "reason": None,
    }


for _r in (_REASON_MULTI_SYMBOL, _REASON_MISSING_TRAIN, _REASON_MISSING_TEST, _REASON_NO_UNIVERSE):
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
        # 🔴 DatetimeIndex **也要**過同一組不變式（B2b R3 之 J1）——R2 我只補了數值分支，
        #    這一支直接 return 就繞過了嚴格遞增檢查，等於只修了一半。
        return assert_epoch_ms_array(
            (idx.asi8 // 10 ** 6).astype("int64"),
            role="split_projection: feature_index",
            strictly_increasing=True,
        )
    return assert_epoch_ms_array(
        np.asarray(idx), role="split_projection: feature_index", strictly_increasing=True
    )  # 🔴 feature_index **必須**嚴格遞增：下游以 row_index[0] 取「最早時刻」


def _plan_bounds_as_ms(plan: Any, *, label: str) -> tuple:
    """把 `SplitPlan.time_bounds` 正規化為 **epoch 毫秒**（型別分派，**不猜單位**）。

    🔴 分派規則與 `_index_as_ms` 同一套（B3 review R1 收斂）：
      · datetime-like（`pd.Timestamp`／`np.datetime64`）⇒ 轉毫秒（IC orchestrator 之
        `_time_bounds_for_rows` 產出的就是 `pd.Timestamp`）；
      · 整數 ⇒ **必須**是毫秒，過 `assert_epoch_ms_array`；餵秒會被指名擋下。
    **不做**「看起來像秒就 ×1000」那種magnitude 猜測——那正是本票在別處禁掉的東西。
    """
    bounds = getattr(plan, "time_bounds", None)
    if bounds is None or len(tuple(bounds)) != 2 or any(b is None for b in tuple(bounds)):
        raise ValueError(
            f"derive_event_split_from_plans: {label}_plan.time_bounds 缺失或非兩元組"
            f"（實得 {bounds!r}）——沒有時間端點就無法對證同源（fail-closed）"
        )
    lo, hi = tuple(bounds)
    out = []
    for value, side in ((lo, "start"), (hi, "end")):
        if isinstance(value, (pd.Timestamp, np.datetime64)):
            ts = pd.Timestamp(value)
            if pd.isna(ts):
                raise ValueError(
                    f"derive_event_split_from_plans: {label}_plan.time_bounds.{side} 為 NaT（fail-closed）"
                )
            out.append(int(ts.value // 10 ** 6))
            continue
        out.append(
            int(
                assert_epoch_ms_array(
                    np.asarray([value]),
                    role=f"derive_event_split_from_plans: {label}_plan.time_bounds.{side}",
                )[0]
            )
        )
    return out[0], out[1]


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


def _assert_event_keys_wellformed(event_keys: pd.DataFrame) -> None:
    """驗 `event_keys` 之**不變式**（B2b R2 之 I5；codex／grok／主委）。

    🔴 上游 `alignment.py:192` 已有 `decision_at <= label_start < label_end` 之閘，
    但本函式是**公開純函式**——B3 以外的 caller（測試、未來的 per-symbol 版）不受那道閘保護。
    ⇒ 三個時間欄各自須為 finite 整數毫秒，且 `label_start_ms <= label_end_ms`。
    """
    if event_keys.empty:
        return
    for col in ("feature_cutoff_ms", "label_start_ms", "label_end_ms"):
        assert_epoch_ms_array(
            np.asarray(event_keys[col]),
            role=f"derive_event_split_from_plans: event_keys.{col}",
        )  # 🔴 不加 strictly_increasing：事件欄可以重複（兩事件同一根 bar 是正常的）
    starts = np.asarray(event_keys["label_start_ms"], dtype="int64")
    ends = np.asarray(event_keys["label_end_ms"], dtype="int64")
    inverted = starts > ends
    if inverted.any():
        bad = event_keys.loc[inverted, "event_id"].tolist()
        raise ValueError(
            f"derive_event_split_from_plans: 答案窗反轉（label_start > label_end）於 "
            f"{sorted(bad)[:5]}——反轉的窗不是『比較短』，是資料壞掉（fail-closed）"
        )


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
    _assert_event_keys_wellformed(event_keys)

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
    # 🔴 **不得先把 None 濾掉**（B2b R3 之 J3；codex／composer／grok 三家獨立命中）：
    #    原本寫 `if s is not None` ⇒ 全為 None 時 `symbols` 為空集合 ⇒ 後面的
    #    `if symbols and ...` 整條被跳過 ＝ **fail-open**，還會輸出 `symbol=None` 的 assignment。
    raw_symbols = list(event_keys["symbol"].unique())
    if any(s is None or (isinstance(s, str) and not s.strip()) for s in raw_symbols):
        raise ValueError(
            f"{_REASON_MULTI_SYMBOL}: event_keys.symbol 含 None／空字串"
            "——沒有身份就無法證明邊界屬於本批（fail-closed，不得跳過守衛）"
        )
    symbols = {str(s) for s in raw_symbols}
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
    # 🔴 第四道（B3 自查補上）：兩 plan 必須來自**同一個 universe**。
    #    symbol 相同**不代表** universe 相同——同一個 ETHUSDT 可以有裁切前／裁切後兩份特徵索引
    #    （實測：EVTALIGN 裁頭尾後邊界位移可達 67 小時）。兩 plan 各自建在不同 universe 上時，
    #    `row_index` 的同一個數字指的是不同的時刻，投影會**靜默錯分**。
    #    🔴 本檢查**不涵蓋**「plan 之 universe 與傳入的 `feature_index` 是否同源」——
    #    那需要兩側共用同一種 hash 表示法，而現行 `base_universe_hash` 是**秒**語意
    #    （`contracts._coerce_timestamp_array` 對數字一律 `unit="s"`），事件側時鐘是毫秒；
    #    改動 hash 輸入會移動既有 IC golden digest ⇒ 具名殘留 `SU-RESID-3`（needs-research）。
    plan_universes = {str(getattr(p, "base_universe_hash", "")) for p in (train_plan, test_plan)}
    if len(plan_universes) > 1:
        raise ValueError(
            f"derive_event_split_from_plans: {_UNREGISTERED_UNIVERSE_MISMATCH} "
            f"{sorted(plan_universes)}——同一個 symbol 也可能有兩份特徵索引，"
            "row_index 的同一個數字會指到不同時刻（fail-closed）"
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
    # 🔴 唯一性必須先驗（B2b R2 之 I3）：集合相等會**吃掉重複**——同一個 event_id 出現
    #    兩次仍與 manifest 集合相等，然後被重複計數／重複輸出 assignment。
    for frame, name in ((event_keys, "event_keys"), (manifest.table, "manifest.table")):
        dupes = frame["event_id"][frame["event_id"].duplicated()].unique().tolist()
        if len(dupes):
            raise ValueError(
                f"derive_event_split_from_plans: {name} 之 event_id 重複 {sorted(dupes)[:5]}"
                "——集合相等吃不掉重複，會重複計數（fail-closed）"
            )
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

    # 🔴 **同源對證**（B3 review R1：codex／composer／grok 三家獨立實跑證明的同一個洞）：
    #    到這裡為止，plan 只被驗過「row_index 在 universe 長度內」與「兩 plan hash 相同」——
    #    `base_universe_hash` 是**字面**，plan 可以帶著相同字面卻建在**另一份網格**上。
    #    三家各自的反例都成立：①plan 建在較短網格、傳入長 `feature_index` ⇒ 靜默成功、
    #    同一個 row number 指到不同時刻；②`feature_index` **同長度**整體平移 50 根 ⇒
    #    control 的 `ev3=test` 變成 `train`，`labels_equal=False`，全程 `NO_RAISE`。
    #    ⇒ 以 plan 自己帶的 `time_bounds` 與**傳入的** `feature_index` 在該 plan 之
    #    首尾列上逐值對證。三家提的修法都是這個形狀，且**不動** `base_universe_hash` 的輸入
    #    （改它會移動既有 IC golden digest）。
    for plan, rows, label in ((train_plan, train_rows, "train"), (test_plan, test_rows, "test")):
        if rows.size == 0:
            continue  # train 可為空（極端切分）；空段沒有首尾可對，交由上面的長度閘
        lo, hi = _plan_bounds_as_ms(plan, label=label)
        actual_lo, actual_hi = int(index_ms[rows[0]]), int(index_ms[rows[-1]])
        if (lo, hi) != (actual_lo, actual_hi):
            raise ValueError(
                f"derive_event_split_from_plans: {label}_plan 與傳入的 feature_index **不同源**"
                f"——plan.time_bounds=({lo}, {hi})，但 feature_index 在該 plan 首尾列上是"
                f"({actual_lo}, {actual_hi})。同一個 row number 指到不同時刻 ⇒ 會靜默錯分"
                "（fail-closed；`base_universe_hash` 只是字面，擋不住這件事）"
            )

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
