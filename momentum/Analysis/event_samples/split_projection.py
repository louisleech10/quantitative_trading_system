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
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples.event_split import (
    _degraded_flags,
    build_time_clusters,
    time_cluster_bucket_ms,
)
from momentum.Analysis.event_samples.types import AlignmentReceipts, EventManifest, EventSplitPlan
# 🔴 D-002 `Task 9.2b` (3.2)：異側／混態之 fail-closed 一律用 `AlignmentViolationError`
#    （`ValueError` 子類）——不得沿用裸 `ValueError`，否則呼叫端分不出「資料壞掉」與
#    「實作退回了各 feature TF 自行判側」這兩件事（R21 `CODEX-R21-P1-01` 把錨點測試釘死在此型別）。
from momentum.core.contracts import AlignmentViolationError
from momentum.core.split_preview import (
    assert_epoch_ms_array,
    assert_positional_rows,
    boundary_hash as _boundary_hash,
    build_row_time_fingerprint,
    epoch_ms_from_index,
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
#: D-001-C1 第 3 點（symbol 三角相等）：`plans` 之鍵、`plan.symbol`、事件 symbol 三者須相等。
#: 🔴 **不得**復用 `_REASON_MULTI_SYMBOL`——那個字面專指「未提供 Mapping 結構」；
#:    多標的既已支援，再用它會把「你漏給了一個標的」誤導成「本功能不支援多標的」。
#: 🔴 同 `_UNREGISTERED_UNIVERSE_MISMATCH`：刻意不進 `split_unify.json` 之封閉值集
#:    （登記會動到已戳記 SPEC 的值集與前端枚舉面），守衛以明文 ValueError 承擔。
_SYMBOL_SET_MISMATCH = "plans 之鍵與事件 symbol 不一致"
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


def _strict_count(value: Any, *, role: str) -> int:
    """計數欄之型別／值域閘（B4 review R1：codex／composer／grok 三家獨立命中）。

    🔴 原本只寫 `int(value)`，於是：`-1` 原樣寫進報告、`3.7` **被截成 3**、
    `True` 被當成 1。三者都會在畫面上變成一個看起來正常的「驗證段事件數」，
    而使用者分不出「算過」與「壞資料」——那正是本票要消滅的假數字。

    規則（**不做**任何寬容轉換）：
      · `bool` 一律拒（`True` 是 1 但語意不是計數）；
      · 只接受 Python `int` 與 `np.integer`（`np.integer` 轉成 Python int 是正規化，不是猜測）；
      · **拒收 float**，即使是 `3.0`——能給 float 的呼叫端也能給 `3.7`，
        而截斷是靜默改答案（同 B2b 對 `row_index` 為 float 之裁定）；
      · 負數拒收（計數沒有負的）。
    """
    if isinstance(value, bool):
        raise ValueError(f"build_split_unify_disclosure: {role} 為 bool（{value!r}）——計數不是布林（fail-closed）")
    if not isinstance(value, (int, np.integer)):
        raise ValueError(
            f"build_split_unify_disclosure: {role} 型別為 {type(value).__name__}（{value!r}）"
            "——只接受整數；float 會被截斷＝靜默改答案（fail-closed）"
        )
    out = int(value)
    if out < 0:
        raise ValueError(f"build_split_unify_disclosure: {role}={out} 為負——計數沒有負的（fail-closed）")
    return out


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
    n = _strict_count(n_test, role="n_test")
    counts = {str(k): _strict_count(v, role=f"per_symbol_counts[{k!r}]")
              for k, v in (per_symbol_counts or {}).items()}
    # 🔴 B4 review R1（三家獨立命中）：原本寫 `if counts and total != n_test` ⇒
    #    **空的 counts 直接跳過整條對帳**（codex 實測 `empty_counts_n_test=3 ACCEPTED`）。
    #    `n_test > 0` 卻沒有任何 symbol 的分佈，等於宣稱「有 3 個事件，但不屬於任何標的」。
    if n > 0 and not counts:
        raise ValueError(
            f"build_split_unify_disclosure: n_test={n} 卻沒有 per_symbol_counts"
            "——有事件就必然屬於某個標的（fail-closed，不接受無歸屬的數字）"
        )
    total = sum(counts.values())
    if counts and total != n:
        raise ValueError(
            f"build_split_unify_disclosure: per_symbol_counts 合計 {total} != n_test {n}"
            "——兩個數字在同一份揭露裡互相矛盾（fail-closed）"
        )
    return {
        "n_test": n,
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
    # 🔴 D-002 `Task 9.2`：**feature** TF（取自 `per_tf`），與上面的 `timeframe`（**觸發** TF）
    #    是兩個語意（`D-002-C0`）。複合鍵為 `(event_id, feature_timeframe)`。
    "feature_timeframe",
)


def _index_as_ms(index: Any) -> np.ndarray:
    """把 `pd.Index` 正規化為 **epoch 毫秒 int64** 陣列。

    🔴 SPLITUNIFY 之時鐘一律毫秒；**不呼叫** `_normalize_ic_time_index`——那支是
    「秒」語意，餵毫秒會 raise（`ic_filter_orchestrator.py:269-271`；SPEC C-4／R2 之 D7）。
    🔴 單位政策**共用** `split_preview.assert_epoch_ms_array`（B2b review：codex／grok／主委
    三方獨立命中我原本在此手寫 `1e11` ＝ 第二份 policy），且該支是**逐元素**檢查——
    原本的 `np.all(...)` 對**混合**單位會直接放行。
    """
    # 🔴 SPLITUNIFY D-001-C2 第 3 點：**委派**給 `split_preview.epoch_ms_from_index`，
    #    使 producer 端寫入指紋與投影端重算比對共用**同一支**正規化器；本處不得自寫第二套。
    #    原地實作之 DatetimeIndex／數值兩分支已整支搬入該函式（含 NaT 與嚴格遞增檢查）。
    #    🔴 feature_index **必須**嚴格遞增：下游以首列取「最早時刻」。
    return epoch_ms_from_index(
        index, role="split_projection: feature_index", strictly_increasing=True
    )


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
    selected_timeframe: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """由對齊收據組出投影所需的 **keyed** 事件表（SPEC C-4；R4 之 F2）。

    🔴 **producer 具名在此，B3 只傳遞、不臨時組裝**。理由（`CODEX-R3-P1-01`／`R4-P1-02`）：
    `dedupe.py` 會依 `(label_start_ms, event_id)` **重排** manifest，
    `receipts.per_tf` 每個 `(event_id, timeframe)` 可有多列 ⇒ 用 positional zip 對位會
    **靜默錯分**，連 golden 的 oracle 都可能對錯 event。

    🔴 `manifest.table` 只 merge trigger `timeframe`、**沒有** `feature_cutoff_ms`
    ⇒ 不能用它代替 per-TF cutoff。

    🔴 **D-002 `Task 9.2`（Phase 9B，本批核心）：producer 不再單選 feature TF**。
    `selected_timeframe=None`（預設）⇒ **輸出全量**，行粒度為 `(event_id, feature_timeframe)`；
    給字串 ⇒ 只取該 feature TF 並把其餘列數記進 `discarded`（相容既有呼叫端）。
    v9.1 以前之「每個事件在 `selected_timeframe` 下必須**恰有一列** `per_tf`」語意**已作廢**
    ——那正是 `SU-RESID-2` 的成因（其餘 feature TF 被靜默丟棄）。

    🔴 **`feature_timeframe` 為新建欄，取自 `per_tf`；不得用 `event_level.timeframe` 冒充**
    （`D-002-C0`：後者是**觸發** TF，同事件兩列會同值而使複合鍵碰撞）。

    🔴 **D-002 `Task 9.1`（Phase 9A）：回傳 `(keyed, discarded)` 兩值**。
    `discarded` 之鍵為**被單選濾掉之 feature TF 字面**、值為其列數；無丟棄時為 `{}`
    （**不得**省略、不得回 `None`）。存在理由：單選 `selected_timeframe` 會把其餘 feature TF
    的 `per_tf` 列**靜默丟掉**，呼叫端與使用者完全看不到丟了多少——那正是本 Phase 要消滅的
    誠實性缺陷。丟棄時**不得** raise（會擋掉目前合法的單 feature TF 用法）。
    全量模式（`selected_timeframe=None`）下沒有任何列被丟棄 ⇒ `discarded` 恆為 `{}`。
    """
    per_tf = receipts.per_tf
    event_level = receipts.event_level
    if per_tf is None or event_level is None:
        raise ValueError("build_event_keys: receipts 缺 per_tf 或 event_level（fail-closed）")

    # 🔴 R18 codex `CODEX-R18-P1-03`／grok `GROK-R18-P1-01` 撞題：字串化會把 `NaN`／`pd.NA`
    #    變成字面 `"nan"`／`"<NA>"`，於是 `discarded` 長出一個**看起來合法、實際不是 TF** 的鍵，
    #    呼叫端無從分辨。缺 TF 是**壞資料**、不是一種 TF ⇒ fail-closed。
    #    🔴 `Task 9.2` 起此檢查提前到**全欄**（不再只看被丟棄側）——全量模式沒有「被丟棄側」，
    #    但缺值同樣會讓 `feature_timeframe` 欄長出假值，形態相同。
    if bool(per_tf["timeframe"].isna().any()):
        raise ValueError(
            "build_event_keys: per_tf 之 timeframe 欄有缺值（NaN／NA）"
            "——會變成名為 'nan' 的假 feature TF；缺就是缺，不補預設（fail-closed）"
        )

    if selected_timeframe is None:
        # 全量：不丟棄任何 feature TF ⇒ `discarded` 恆為空。
        selected = per_tf
        discarded: Dict[str, int] = {}
    else:
        want = str(selected_timeframe)
        selected = per_tf.loc[per_tf["timeframe"].astype(str) == want]
        if selected.empty:
            raise ValueError(
                f"build_event_keys: per_tf 無 timeframe={selected_timeframe!r} 之列（fail-closed）"
            )
        # 🔴 D-002 Task 9.1：被單選濾掉之列須逐 feature TF 記帳，不得靜默消失。
        dropped = per_tf.loc[per_tf["timeframe"].astype(str) != want, "timeframe"]
        discarded = {str(tf): int(n) for tf, n in dropped.astype(str).value_counts().items()}

    # 🔴 `Task 9.2` (b)：**新建**輸出欄 `feature_timeframe` 取自 `per_tf.timeframe`。
    #    不得以 `event_level.timeframe`（**觸發** TF）冒充——同事件兩列會同值而使複合鍵碰撞
    #    （`D-002-C0`；R5 三家獨立撞題）。
    keyed = selected[["event_id", "timeframe", "feature_cutoff_ms"]].rename(
        columns={"timeframe": "feature_timeframe"}
    )
    # 🔴 `Task 9.2a`：唯一性判準由「每事件一列」改為 **`(event_id, feature_timeframe)` 複合鍵唯一**。
    #    同事件不同 feature TF 為**合法**，不得再以 `event_id` 重複為由擋下。
    dup_mask = keyed.duplicated(subset=["event_id", "feature_timeframe"], keep=False)
    if bool(dup_mask.any()):
        dupes = sorted(
            f"{e}/{tf}" for e, tf in
            keyed.loc[dup_mask, ["event_id", "feature_timeframe"]]
            .astype(str).drop_duplicates().itertuples(index=False, name=None)
        )
        raise ValueError(
            "build_event_keys: (event_id, feature_timeframe) 複合鍵重複："
            f"{dupes[:5]}——同一事件之同一 feature TF 不得有多列 per_tf（fail-closed）"
        )

    # 🔴 `Task 9.2` (a)：舊寫法 `event_level.merge(selected, validate="1:1")` 在全量多 feature TF
    #    **必** `MergeError`。改為**以 `per_tf` 為行粒度**接合，`validate` 改 `many_to_one`
    #    ——多列 per_tf 對一列 event_level；🔴 `event_level` 自身 `event_id` 重複仍會被擋下
    #    （放寬 `validate` 不得順手放掉這一面，見 `Task 9.2` 邊界③）。
    merged = keyed.merge(
        event_level[["event_id", "label_start_ms", "label_end_ms", "symbol", "timeframe"]],
        on="event_id", how="inner", validate="many_to_one",
    )
    missing = set(event_level["event_id"]) - set(merged["event_id"])
    if missing:
        scope = "全量" if selected_timeframe is None else f"timeframe={selected_timeframe!r} 下"
        raise ValueError(
            f"build_event_keys: {len(missing)} 個事件在{scope}缺 cutoff"
            f"（例：{sorted(missing)[:3]}）——缺就是缺，不補預設"
        )
    out = merged[
        ["event_id", "feature_cutoff_ms", "label_start_ms", "label_end_ms", "symbol",
         "timeframe", "feature_timeframe"]
    ].copy()
    return out.reset_index(drop=True), discarded


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


def _assert_event_level_side_consistency(
    assign_rows: List[dict], purge_rows: List[dict]
) -> None:
    """`D-002-C3` (3.2)：同一事件恆同側，否則 `AlignmentViolationError`（SPEC `§P Task 9.2b`）。

    🔴 **兩道分離的檢查，缺一不可**：
      1. `assignments` 內按 `event_id` 分組，`split_label` 須唯一——擋「一列 train、一列 test」。
      2. **跨表互斥**：`set(purged.event_id) ∩ set(assignments.event_id) == ∅`——擋「一列進
         `purged`、另一列進 `assignments`」。🔴 這一道不能省：`purged` **沒有** `split_label`
         欄，第 1 道結構上抓不到這種混態（R6 三家獨立撞題）。
      🔴 **不得**以擴充 `split_label` 值域（新增 `PURGED` 之類）替代——那會動到已戳記之封閉
      值集與前端枚舉面。

    🔴 **獨立函式而非 inline**：SPEC §V `:270` 之 (3.2) 反例逐字為「**直接構造 `assignments`**
    使同一 `event_id` 之兩列異側 THEN raise」——測試要能直接構造那個狀態，檢查就必須有
    可單獨呼叫的入口。inline 在迴圈裡則該反例**無碼可打**。

    🔴 訊息**須含該 `event_id`**（`D-002-C3` (3.2) 明定）；且**不得**靜默取一側、
    **不得**改判 purged（purge 會把實作缺陷偽裝成正常的樣本流失）。
    """
    sides_by_event: Dict[Any, set] = {}
    for row in assign_rows:
        sides_by_event.setdefault(row["event_id"], set()).add(row["split_label"])
    mixed = sorted(eid for eid, labels in sides_by_event.items() if len(labels) > 1)
    if mixed:
        raise AlignmentViolationError(
            f"derive_event_split_from_plans: 事件 {mixed[:5]} 之 feature TF 列被判到**異側**"
            "——(3.1) 事件級錨定落地後這不可能由合法資料產生，代表實作退回了"
            "「各 feature TF 自行判側」；不靜默取一側、不改判 purged（fail-closed）"
        )
    assigned_ids = {row["event_id"] for row in assign_rows}
    purged_ids = {row["event_id"] for row in purge_rows}
    straddling = sorted(assigned_ids & purged_ids)
    if straddling:
        raise AlignmentViolationError(
            f"derive_event_split_from_plans: 事件 {straddling[:5]} 同時出現在 assignments 與 "
            "purged——同一事件的不同 feature TF 列落到不同容器即為混態；`purged` 無 "
            "`split_label`，分組檢查抓不到這一種，故須本跨表互斥閘（fail-closed）"
        )


def _derive_single_symbol(
    train_plan: Any,
    test_plan: Any,
    event_keys: pd.DataFrame,
    feature_index: Any,
    *,
    manifest: EventManifest,
    bucket_ms: Optional[int] = None,
    tier_min_test_events: int = 1,
    # 🔴 D-002 Task 9.1：producer 之 `discarded` **原樣**帶進 summary（跨邊界傳遞，不重算）。
    #    預設 `None` 而非 `{}`：`None` 代表「呼叫端沒給」⇒ 寫入空 dict；給了就原樣寫。
    #    不可變預設值之所以不寫 `{}`，是避免共用可變預設物件。
    discarded_rows_by_feature_tf: Optional[Dict[str, int]] = None,
) -> EventSplitPlan:
    """由 canonical 邊界投影出**完整**的 `EventSplitPlan`（SPEC C-3／C-4／C-5）。

    🔴 `tier_min_test_events`（B2b R1 之 H6；**當輪我寫「列入 B3 Task 3.1」延後，之後就消失了**，
    2026-09-11 歸屬回溯稽核才撈回）：原本只有內部 `_build_summary` 有這個參數、預設 1，
    對外沒開放 ⇒ 投影路徑上使用者設定的「測試段事件數下限」被**靜默換成 1**，
    而舊的 `split_events` 路徑是照設定走的——兩條路對同一個設定給出不同的判定。

    🔴 **D-002 `Task 9.2b`（B9C）起：判側改為事件級 `decision_at_ms` 錨定＋三段式**
    （R27 `GROK-R27-P2-01` 指出本 docstring 仍寫 9.2b 前的兩段式集合成員）：
      0. **步驟 0**：`train_rows`／`test_rows` 皆非空、`train_last_ms < test_start_ms`；
         `index_ms[0] <= decision_at_ms <= index_ms[-1]`，界外 raise（**不是**第四條分支）。
      1. **三段式**（順序不可調）：`decision <= train_last_ms` ⇒ train；`>= test_start_ms` ⇒ test；
         介於兩者 ⇒ purged（隔離帶，合法且預期）。錨點取自 `manifest.table["decision_at_ms"]`。
      2. **答案窗 purge 按事件側一次決定並廣播**：train 側事件若 `label_end_ms >= test_start_ms`
         ⇒ 整事件 purged（`>=` 必須保留）。
      3. **廣播**：側別判完套用到該 `event_id` 之**所有** feature TF 列；
         `feature_cutoff_ms` **完全不參與** `split_label`。
      4. `(3.2)` fail-closed：寫入兩容器**之前**呼叫 `_assert_event_level_side_consistency`。

    以下為 **9.2b 前**之舊描述，保留供追溯，**不得**據以實作：

    ~~🔴 **兩段式判定，先後不可調**（R3 之 E1；式子逐字採 `CODEX-R4-P1-01`）：~~

    1. **答案窗 purge**（保留 `event_split.py:114` 之既有 guard）——
       `train_cutoff and label_end_ms >= test_start_ms` ⇒ purged。
       `purge_gap`／`embargo` 是 **row 單位且已含在 `test_plan.row_index_local[0]` 這個起點裡**
       （🔴 `CODEX-R1-P2-03`：D-001 (4.10)–(4.11) 要求投影端之文件與實作**一律用標的內座標**；
       此處原寫全框 `row_index[0]`，會誘導後人把全框列號當成標的內序號），
       **不得**再以毫秒相減（舊式的 `test_start` 在緩衝**之前**，canonical 的在**之後**）。
    2. **集合成員判定**——以 `row_index_local` 索引該 symbol 之 `feature_index`，
       `feature_cutoff_ms ∈ feature_index[plan.row_index_local]` 決定 train／test；
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
    # 🔴 D-002 `Task 9.2a`：唯一性判準**分兩種粒度**——
    #    `event_keys` 複合鍵後一事件可有多列（每 feature TF 一列）⇒ 判準改為
    #    `(event_id, feature_timeframe)` 唯一；沿用舊的「event_id 不得重複」會把
    #    **合法的多 feature TF 批整批擋死**（本批核心目標之不可達形態）。
    #    `manifest.table` 仍是事件級（一列一事件）⇒ 維持 event_id 唯一。
    #    🔴 **錯誤型別維持 `ValueError`**（前端與既有測試有依賴，不得為統一而改）。
    ek_dup = event_keys.duplicated(subset=["event_id", "feature_timeframe"], keep=False)
    if bool(ek_dup.any()):
        bad = sorted(
            f"{e}/{tf}" for e, tf in
            event_keys.loc[ek_dup, ["event_id", "feature_timeframe"]]
            .astype(str).drop_duplicates().itertuples(index=False, name=None)
        )
        raise ValueError(
            "derive_event_split_from_plans: event_keys 之 (event_id, feature_timeframe) "
            f"複合鍵重複 {bad[:5]}——集合相等吃不掉重複，會重複計數（fail-closed）"
        )
    # 🔴 **R27 `CODEX-R27-P2-06`：錨點唯一性閘必須排在 `man_dupes` 之前，否則不可達**。
    #    原本它寫在下方判側段，而 `manifest.table` 之 `event_id` 重複在此已先被裸 `ValueError`
    #    擋掉 ⇒ 帶著**不同錨點**的重複 manifest 得到的是「重複」這個病名，而不是「錨點不唯一」。
    #    該家實跑 `DUPLICATE_ANCHOR_EXCEPTION ValueError`／`ANCHOR_GUARD_REACHED False`。
    #    ⇒ 先判錨點：同一 `event_id` 之 `decision_at_ms` 去重數 > 1 即 `AlignmentViolationError`
    #    （錨點衝突是側別缺陷，語意上比「manifest 有重複列」更精確）；純重複而錨點一致者
    #    仍落到下方既有之 `ValueError`（錯誤型別契約不變）。
    if "decision_at_ms" in manifest.table.columns:
        _anchor_nuniq = manifest.table.groupby("event_id")["decision_at_ms"].nunique()
        _bad_anchor = sorted(_anchor_nuniq[_anchor_nuniq > 1].index.tolist())
        if _bad_anchor:
            raise AlignmentViolationError(
                "derive_event_split_from_plans: 事件 "
                f"{_bad_anchor[:5]} 之 decision_at_ms 不唯一——事件級錨點必須單值，"
                "取首列會讓同事件的不同 feature TF 落到不同側（fail-closed）"
            )
    man_dupes = manifest.table["event_id"][manifest.table["event_id"].duplicated()].unique().tolist()
    if len(man_dupes):
        raise ValueError(
            f"derive_event_split_from_plans: manifest.table 之 event_id 重複 {sorted(man_dupes)[:5]}"
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
    # 🔴 D-001 (4.12)：缺欄即 fail-closed，且**不得**以 `row_index` 回退
    #    （回退正是交錯標的越界之來源）。非 derive 之呼叫點才給相容 default。
    for _plan, _label in ((train_plan, "train"), (test_plan, "test")):
        if getattr(_plan, "row_index_local", None) is None:
            raise ValueError(
                f"derive_event_split_from_plans: {_label}_plan 缺 row_index_local 欄"
                "——投影端只消費標的內序號，禁以 row_index 回退（fail-closed）"
            )
        if not str(getattr(_plan, "row_time_fingerprint", "")):
            raise ValueError(
                f"derive_event_split_from_plans: {_label}_plan 缺 row_time_fingerprint 欄"
                "——入口重驗是權威守衛，缺指紋即無法證明列未被竄改（fail-closed）"
            )
    # 🔴 D-001 (4.10)：投影端**一律只讀** `row_index_local`，內部不得索引 `row_index`。
    #    🔴 (4.14)：此處之嚴格遞增**不得**關閉——指紋先依序號排序再雜湊，對同集合**重排不敏感**，
    #    擋重排者正是本閘；指紋與遞增閘為**合取**，缺一不可。
    train_rows = assert_positional_rows(
        train_plan.row_index_local, n=index_ms.size, role="derive: train_plan"
    )
    test_rows = assert_positional_rows(
        test_plan.row_index_local, n=index_ms.size, role="derive: test_plan"
    )
    # 🔴 D-001 (4.13) 權威守衛＝入口重驗：以**傳入的** feature_index 重算指紋並與 plan 攜帶值
    #    逐值比對。建構後竄改序號若改變成員集合，必在此擋下（改順序則由上方遞增閘擋）。
    for _plan, _rows, _label in (
        (train_plan, train_rows, "train"), (test_plan, test_rows, "test")
    ):
        _recomputed = build_row_time_fingerprint(
            positions=_rows,
            feature_ts_ms=index_ms[_rows],
            symbol=str(getattr(_plan, "symbol", "")),
            base_universe_hash=str(getattr(_plan, "base_universe_hash", "")),
        )
        if _recomputed != str(_plan.row_time_fingerprint):
            raise ValueError(
                f"derive_event_split_from_plans: {_label}_plan 逐列時刻指紋不符——"
                f"plan 指紋 {str(_plan.row_time_fingerprint)[:12]} vs "
                f"重算指紋 {_recomputed[:12]}"
                "（列被竄改，或 feature_index 與 plan 非同源；fail-closed）"
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
    # 🔴 D-002 `Task 9.2b` 步驟 0（stamp-r5 三家一致裁定）：**兩段皆非空**。
    #    原本此處對空段 `continue`（註解寫「train 可為空（極端切分）」）是 9.2b 前的遺留——
    #    事件級錨定要讀 `train_last_ms = index_ms[train_rows[-1]]`，空 train 會 IndexError；
    #    三家一致裁定**不得**定義哨兵或 fallback，而是在此 fail-closed
    #    （`EventSamplePipeline.run` 之 `validate_split_pair_integrity` 是第一道，本處是投影端第二道）。
    if train_rows.size == 0:
        raise ValueError(
            f"{_REASON_MISSING_TRAIN}: train_plan.row_index 為空"
            "——事件級錨定需要 train 段末刻度，空段無 `train_last_ms` 可定義（fail-closed）"
        )
    for plan, rows, label in ((train_plan, train_rows, "train"), (test_plan, test_rows, "test")):
        lo, hi = _plan_bounds_as_ms(plan, label=label)
        actual_lo, actual_hi = int(index_ms[rows[0]]), int(index_ms[rows[-1]])
        if (lo, hi) != (actual_lo, actual_hi):
            raise ValueError(
                f"derive_event_split_from_plans: {label}_plan 與傳入的 feature_index **不同源**"
                f"——plan.time_bounds=({lo}, {hi})，但 feature_index 在該 plan 首尾列上是"
                f"({actual_lo}, {actual_hi})。同一個 row number 指到不同時刻 ⇒ 會靜默錯分"
                "（fail-closed；`base_universe_hash` 只是字面，擋不住這件事）"
            )

    # 🔴 D-002 `Task 9.2b`（(3.1) 之唯一落地處）：側別改由**事件級** `decision_at_ms` 錨定。
    #    `train_last_ms` 為新增；`test_start_ms` 沿用。兩者皆取自傳入的 `feature_index`
    #    ——與 plan 同源已由上方指紋閘與 `time_bounds` 對證保證。
    train_last_ms = int(index_ms[train_rows[-1]])
    test_start_ms = int(index_ms[test_rows[0]])
    index_lo_ms, index_hi_ms = int(index_ms[0]), int(index_ms[-1])
    # 🔴 步驟 0 之「row set 不重疊」在投影端的**時間面**體現：三段式判準以 `train_last_ms`
    #    與 `test_start_ms` 為兩個閉端點，若 `test_start_ms <= train_last_ms`，第一、二條
    #    分支會**同時成立**，順序便成了靜默的 tie-breaker（先判 train 就全進 train）。
    #    ⇒ 兩段重疊必須在這裡 fail-closed，不得靠分支順序吃掉。
    #    （`EventSamplePipeline.run` 之 `validate_split_pair_integrity` 是第一道；本處是
    #    投影端第二道，涵蓋直接呼叫 `derive_event_split_from_plans` 的路徑。）
    if test_start_ms <= train_last_ms:
        raise ValueError(
            "derive_event_split_from_plans: train 段末刻度 "
            f"{train_last_ms} 不早於 test 段起點 {test_start_ms}——兩段在時間上重疊，"
            "三段式判準之前兩條會同時成立而由分支順序靜默決定側別（fail-closed）"
        )

    # 🔴 錨定來源＝`manifest.table`（事件級、欄已存在），**不是** `event_keys`
    #    （stamp-r5 三家一致：`decision_at_ms` 不得加入 `EVENT_KEY_COLUMNS`、不得改
    #    `build_event_keys` 之 merge——主委原本的假設被 SPEC §P `Task 9.2b` 原文否證）。
    #    `manifest.table` 之 `event_id` 唯一已由上方 `man_dupes` 閘保證，故此處是 1:1 lookup。
    if "decision_at_ms" not in manifest.table.columns:
        raise ValueError(
            "derive_event_split_from_plans: manifest.table 缺 decision_at_ms 欄"
            "——事件級錨定沒有它就退化回 per-cutoff 判側（fail-closed）"
        )
    _anchor_tbl = manifest.table[["event_id", "decision_at_ms"]]
    assert_epoch_ms_array(
        np.asarray(_anchor_tbl["decision_at_ms"]),
        role="derive_event_split_from_plans: manifest.table.decision_at_ms",
    )
    # 🔴 錨點唯一性已於上方（`man_dupes` **之前**）判過——見 `CODEX-R27-P2-06`。
    #    此處不重複判，否則會出現兩份同語意的閘而其中一份永遠不可達。
    anchor_by_event: Dict[Any, int] = {
        eid: int(v) for eid, v in
        _anchor_tbl.drop_duplicates("event_id").itertuples(index=False, name=None)
    }

    # 🔴 步驟 0 之界外閘：`index_ms[0] <= decision_at_ms <= index_ms[-1]`，任一不滿足即 raise
    #    （訊息含 `event_id`）。**不得**寫成第四條分類分支——寫成分支就等於恢復重疊，
    #    越界事件會被合法分到 train／test（TODO `Task 9.2b` 不可做第二條）。
    _out_of_range = sorted(
        eid for eid, d in anchor_by_event.items() if not (index_lo_ms <= d <= index_hi_ms)
    )
    if _out_of_range:
        raise ValueError(
            f"derive_event_split_from_plans: 事件 {_out_of_range[:5]} 之 decision_at_ms 落在 "
            f"feature_index 之外（[{index_lo_ms}, {index_hi_ms}]）"
            "——界外不是一種側別，不得分類（fail-closed）"
        )

    # 🔴 三段式判準，順序不得調換（TODO `Task 9.2b` 實作要點 2）：
    #    `<= train_last_ms` ⇒ train；`>= test_start_ms` ⇒ test；介於兩者之間 ⇒ purged。
    #    邊界取**閉區間**：`== train_last_ms` ⇒ train、`== test_start_ms` ⇒ test。
    #    🔴 `feature_cutoff_ms` **不參與** `split_label`（不可做第一條）。
    def _side_of(decision_ms: int) -> str:
        if decision_ms <= train_last_ms:
            return "train"
        if decision_ms >= test_start_ms:
            return "test"
        return "purged"  # 隔離帶：合法且預期，不得 raise（邊界①）

    # 🔴 答案窗 purge 按**事件側**一次決定並廣播（實作要點 4）——不再逐列 `in_train`。
    #    逐列觸發正是混態（同事件一列進 purged、另一列進 assignments）的來源。
    # 🔴 **R27 `CODEX-R27-P2-05`**：事件級欄位一致性閘——`label_end_ms` 同事件須唯一。
    #    判準與 `decision_at_ms` 之錨點唯一性同源：事件級欄逐列不同即為上游壞掉，
    #    不得以 `max`／`first` 之類的聚合靜默吞掉。
    _le_nuniq = event_keys.groupby("event_id")["label_end_ms"].nunique()
    _bad_le = sorted(_le_nuniq[_le_nuniq > 1].index.tolist())
    if _bad_le:
        raise AlignmentViolationError(
            f"derive_event_split_from_plans: 事件 {_bad_le[:5]} 之 label_end_ms 不唯一"
            "——該欄為事件級，同事件各 feature TF 列必須同值；取 max 會靜默改用較大的"
            "答案窗而把跨界隱形（fail-closed）"
        )
    _label_end_by_event: Dict[Any, int] = {
        eid: int(v) for eid, v in
        event_keys.drop_duplicates("event_id")[["event_id", "label_end_ms"]]
        .itertuples(index=False, name=None)
    }

    event_state: Dict[Any, str] = {}
    for eid, decision_ms in anchor_by_event.items():
        side = _side_of(decision_ms)
        if side == "train":
            # 答案窗跨進 test 段起點 ⇒ 整個事件 purged（保留 `event_split.py:114` 之既有語意）。
            # 🔴 **R27 `CODEX-R27-P2-05`**：原本這裡直接取 `.max()`，而 `label_end_ms` 是**事件級**欄
            #    （來自 `receipts.event_level`）⇒ 同事件各 feature TF 列本應同值。取 `max` 在不一致時
            #    會**靜默**改用較大的答案窗（該家實跑 `LABEL_END_MISMATCH_ACCEPTED True`）。
            #    不一致代表上游事件級欄位壞了，與 `decision_at_ms` 不唯一同型 ⇒ 一律 fail-closed。
            label_end = int(_label_end_by_event[eid])
            if label_end >= test_start_ms:
                side = "purged"
        event_state[eid] = side

    assign_rows: List[dict] = []
    purge_rows: List[dict] = []
    for rec in event_keys.to_dict("records"):
        # 🔴 廣播：側別由事件決定，該 `event_id` 之**所有** feature TF 列同進同一容器
        #    （實作要點 3）。
        side = event_state[rec["event_id"]]
        if side == "purged":
            # 🔴 D-002 `Task 9.2a`：purge 側同樣是複合鍵粒度；缺此欄則同事件多 feature TF
            #    在 `purged` 裡無法區分，且下方跨表互斥檢查會抓不到混態。
            purge_rows.append({
                "event_id": rec["event_id"], "reason": _PURGE_REASON,
                "feature_timeframe": rec["feature_timeframe"],
            })
        else:
            assign_rows.append(
                {"event_id": rec["event_id"], "symbol": rec["symbol"], "split_label": side,
                 "feature_timeframe": rec["feature_timeframe"]}
            )

    # 🔴 `D-002-C3` (3.2) 之 fail-closed（實作要點 5＋6）：在寫入兩容器**之前**檢查。
    #    兩道分離、缺一不可——`purged` 無 `split_label`，只靠分組檢查結構上抓不到跨表混態。
    _assert_event_level_side_consistency(assign_rows, purge_rows)

    # 🔴 D-002 `Task 9.2a`：兩表皆升為複合鍵粒度，欄含 `feature_timeframe`。
    assignments = pd.DataFrame(
        assign_rows, columns=["event_id", "symbol", "split_label", "feature_timeframe"]
    )
    purged = pd.DataFrame(purge_rows, columns=["event_id", "reason", "feature_timeframe"])
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
        # 🔴 單標的路徑：本批只有一個 symbol，逐 symbol 門檻即整批門檻（Task 8.3 同一判定）。
        per_symbol_test_n={s: n_test for s in per_symbol_n},
        bucket=int(time_cluster_bucket_ms(manifest, bucket_ms)),
        tier_min_test_events=_strict_count(tier_min_test_events, role="tier_min_test_events"),
        discarded_rows_by_feature_tf=discarded_rows_by_feature_tf,
        # 🔴 `Task 9.2a`／`D-002-C6`：事件數以 `event_id` **去重**、列數為複合鍵列數。
        n_events=int(event_keys["event_id"].nunique()),
        n_event_tf_rows=int(len(event_keys)),
        n_event_tf_rows_purged=int(len(purged)),
    )
    return EventSplitPlan(
        assignments=assignments, purged=purged, clusters=clusters, summary=summary
    )


def derive_event_split_from_plans(
    plans: Any,
    event_keys: pd.DataFrame,
    feature_index_by_symbol: Any = None,
    *args: Any,
    **kwargs: Any,
) -> EventSplitPlan:
    """由 canonical 邊界投影出 `EventSplitPlan`；支援 per-symbol 批（D-001-C1 第 1 點）。

    **新式**：`plans` 為 `Mapping[symbol, (train_plan, test_plan)]`、
    `feature_index_by_symbol` 為 `Mapping[symbol, pd.Index]`（**該 symbol 自己的 post-trim 索引**，
    短索引；不是全框 universe）。逐 symbol 走同一條單標的路徑後**縱向合併**。

    **舊式（單標的）**：`(train_plan, test_plan, event_keys, feature_index, …)` 保留為**薄 wrapper**，
    內部包成單鍵 Mapping 後轉呼；🔴 wrapper **不得**含第二份判定邏輯——purge／成員判定／
    指紋比對一律只有 `_derive_single_symbol` 一份。

    呼叫端既未給 Mapping、也未走 wrapper ⇒ 維持 `multi_symbol_projection_unsupported`。
    """
    if not isinstance(plans, Mapping):
        # 薄 wrapper：舊式位置參數 (train_plan, test_plan, event_keys, feature_index, …)
        return _derive_single_symbol(plans, event_keys, feature_index_by_symbol, *args, **kwargs)

    if not isinstance(feature_index_by_symbol, Mapping):
        raise ValueError(
            f"{_REASON_MULTI_SYMBOL}: 給了 plans Mapping 卻沒給 feature_index_by_symbol Mapping"
            "——per-symbol 投影需要每個 symbol 自己的 post-trim 索引（fail-closed）"
        )
    manifest = kwargs.pop("manifest")
    bucket_ms = kwargs.pop("bucket_ms", None)
    tier_min_test_events = kwargs.pop("tier_min_test_events", 1)
    discarded_rows_by_feature_tf = kwargs.pop("discarded_rows_by_feature_tf", None)
    if kwargs:
        raise TypeError(f"derive_event_split_from_plans: 未知參數 {sorted(kwargs)}")

    missing_cols = [c for c in EVENT_KEY_COLUMNS if c not in event_keys.columns]
    if missing_cols:
        raise ValueError(f"derive_event_split_from_plans: event_keys 缺欄 {missing_cols}")
    event_symbols = {str(s) for s in event_keys["symbol"].unique()}
    plan_keys = {str(k) for k in plans}
    if event_symbols != plan_keys:
        raise ValueError(
            f"{_SYMBOL_SET_MISMATCH}: 事件 symbol {sorted(event_symbols)} 與 plans 之鍵 "
            f"{sorted(plan_keys)} 不一致——禁以第一個 symbol 冒充整批（fail-closed）"
        )

    assign_parts: List[pd.DataFrame] = []
    purge_parts: List[pd.DataFrame] = []
    per_symbol_test_n: Dict[str, int] = {}
    for sym in sorted(plan_keys):
        if sym not in feature_index_by_symbol:
            raise ValueError(
                f"{_REASON_MULTI_SYMBOL}: feature_index_by_symbol 缺 symbol {sym!r}（fail-closed）"
            )
        tr, te = plans[sym]
        sub_keys = event_keys[event_keys["symbol"].astype(str) == sym].reset_index(drop=True)
        sub_manifest = _manifest_subset(manifest, set(sub_keys["event_id"]))
        part = _derive_single_symbol(
            tr, te, sub_keys, feature_index_by_symbol[sym],
            manifest=sub_manifest, bucket_ms=bucket_ms,
            tier_min_test_events=tier_min_test_events,
        )
        assign_parts.append(part.assignments)
        purge_parts.append(part.purged)
        per_symbol_test_n[sym] = int(
            (part.assignments["split_label"] == "test").sum()
        ) if not part.assignments.empty else 0

    # 🔴 `Task 9.2a`：空批之欄集須與非空批**逐字一致**，否則下游 `duplicated(subset=...)`
    #    在空批上會 `KeyError`（同一個「欄缺」形態，只是發生在空集合）。
    assignments = (
        pd.concat(assign_parts, ignore_index=True) if assign_parts
        else pd.DataFrame(columns=["event_id", "symbol", "split_label", "feature_timeframe"])
    )
    purged = (
        pd.concat(purge_parts, ignore_index=True) if purge_parts
        else pd.DataFrame(columns=["event_id", "reason", "feature_timeframe"])
    )
    clusters = build_time_clusters(manifest, bucket_ms)
    per_symbol_n = {
        str(sym): int(n) for sym, n in event_keys["symbol"].value_counts().items()
    }
    summary = _build_summary(
        manifest=manifest,
        clusters=clusters,
        per_symbol_n=per_symbol_n,
        n_purged=int(len(purged)),
        per_symbol_test_n=per_symbol_test_n,
        bucket=int(time_cluster_bucket_ms(manifest, bucket_ms)),
        tier_min_test_events=_strict_count(tier_min_test_events, role="tier_min_test_events"),
        # 🔴 D-002 Task 9.1：`discarded` 是 **producer 層**（`build_event_keys`）對整批
        #    `receipts.per_tf` 一次算出的，不是逐 symbol 各算一份 ⇒ 多 symbol 路徑
        #    **原樣傳遞**即可，不得在此對各 symbol 的結果再相加（會重複計數）。
        discarded_rows_by_feature_tf=discarded_rows_by_feature_tf,
        # 🔴 `Task 9.2a`／`D-002-C6`：多標的同樣以整批 `event_keys` 算——事件數去重、列數為列數。
        n_events=int(event_keys["event_id"].nunique()),
        n_event_tf_rows=int(len(event_keys)),
        n_event_tf_rows_purged=int(len(purged)),
    )
    return EventSplitPlan(
        assignments=assignments, purged=purged, clusters=clusters, summary=summary
    )


def _manifest_subset(manifest: EventManifest, keep_ids: set) -> EventManifest:
    """取 manifest 中屬於某 symbol 之子集（逐 symbol 投影用）。

    🔴 單標的路徑要求 `event_keys` 與 `manifest.table` 之 event_id 集合**相等**；
    逐 symbol 切片時必須連帶把 manifest 切成同一批，否則會誤報「不是同一批」。
    """
    table = manifest.table[manifest.table["event_id"].isin(keep_ids)].reset_index(drop=True)
    summary = dict(manifest.summary or {})
    summary["n_events_raw"] = int(len(table))
    summary["n_events_effective"] = int(len(table))
    return EventManifest(table=table, summary=summary, policy=getattr(manifest, "policy", {}))


def _build_summary(
    *,
    manifest: EventManifest,
    clusters: pd.DataFrame,
    per_symbol_n: Dict[str, int],
    n_purged: int,
    per_symbol_test_n: Dict[str, int],
    bucket: int,
    tier_min_test_events: int = 1,
    discarded_rows_by_feature_tf: Optional[Dict[str, int]] = None,
    # 🔴 D-002 `Task 9.2a` ＋ `D-002-C6`：**事件數與列數是兩個量**，必須並存、不得互相代用。
    n_events: Optional[int] = None,
    n_event_tf_rows: Optional[int] = None,
    n_event_tf_rows_purged: Optional[int] = None,
) -> Dict[str, Any]:
    """`EventSplitPlan.summary` 之 **16 個必填鍵**（SPEC C-5 ＋ `D-002` `Task 9.1` 之丟棄記帳
    ＋ `Task 9.2a`／`D-002-C6` 之事件數與列數三鍵）。

    🔴 **v/R18 更正（grok `GROK-R18-P3-01`／codex `CODEX-R18-P3-02` 撞題）**：本 docstring
    原寫「12 個必填鍵」且引用 `pipeline.py:696`——前者在 Task 9.1 加入
    `discarded_rows_by_feature_tf` 後已漂移，後者之行號早已不存在。鍵數之權威是
    `test_summary_has_all_sixteen_keys` 之 exact-set 斷言，不是這段散文。

    少一鍵，pipeline 之 summary 轉寫會靜默丟欄、報告整段消失——與 EVTLABEL B5 那條
    「light 視圖漏 `metadata_keep_keys`」同形態。

    🔴 `insufficient_events_in_test` 改看**投影後**的 test 數；
    `single_symbol` 恆亮是**預期的**（多 symbol 已 fail-closed ⇒ 存活路徑恆 `n_symbols == 1`），
    連帶使 `tables.py:138` 之 `formal_pooled_inference_allowed` 恆 `False`——方向保守，
    **不得**為了讓它變 `True` 而清空 `degraded`（SPEC Task 2.2 要點 6／R2 之 D11）。
    """
    # 🔴 `CODEX-R3-P3-04`（B2b R3；**當輪被我漏掉、2026-09-11 歸屬回溯稽核才撈回**）：
    #    原本直接 `manifest.summary["n_events_raw"]` ⇒ 缺鍵時丟出**沒有語意的裸 KeyError**，
    #    使用者看不出是 manifest 壞了還是程式壞了。改為先驗、缺就指名缺什麼（fail-closed）。
    missing = [k for k in ("n_events_raw", "n_events_effective") if k not in (manifest.summary or {})]
    if missing:
        raise ValueError(
            f"derive_event_split_from_plans: manifest.summary 缺 {missing}"
            "——manifest 不完整（應由 build_event_manifest 產生），無法產出切分摘要（fail-closed）"
        )
    n_symbols = len(per_symbol_n)
    # 🔴 SPLITUNIFY D-001 Task 8.3：**逐 symbol** 判定。原式 `n_test < 門檻` 之條件與迴圈變數
    #    `s` 無關，用的是**整批** test 數 ⇒ 多標的一接通就變成「要嘛全部標不足、要嘛全部不標」。
    insufficient = [
        s for s in per_symbol_n
        if int(per_symbol_test_n.get(s, 0)) < int(tier_min_test_events)
    ]
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
        # 🔴 D-002 Task 9.1（Phase 9A）：producer 之丟棄記帳**原樣**落在此鍵。
        #    鍵名依 `D-002-C0` (0.6) 不得含裸 `timeframe`，故用 `feature_tf`。
        #    值為 `{feature TF 字面: 列數}`；無丟棄時為 `{}`（不得缺鍵、不得為 None）。
        "discarded_rows_by_feature_tf": {
            str(k): int(v) for k, v in (discarded_rows_by_feature_tf or {}).items()
        },
        # 🔴 D-002 `Task 9.2a` ＋ `D-002-C6`：事件數與列數並存。
        #    `n_events`＝去重後之事件數；`n_event_tf_rows`＝複合鍵列數（＝事件×feature TF）。
        #    單 feature TF 時兩者相等，但**仍須並存**——相等不是可以省略其一的理由。
        "n_events": int(n_events or 0),
        "n_event_tf_rows": int(n_event_tf_rows or 0),
        "n_event_tf_rows_purged": int(n_event_tf_rows_purged or 0),
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
