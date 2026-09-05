"""GAP-3 `G3-D2` D5.2 — 隨機對照批之**確定性抽樣**（純函式）。

## 這支在回答什麼

觸發批（`/search` 或產生器產出的那批事件）的 prevalence 是**條件**機率：
「符合這個條件的 bar 裡，有多少比例後來漲到門檻」。要判斷這個數字有沒有訊息，
需要一個**無條件**基準：「隨便挑的 bar 裡，有多少比例後來漲到門檻」。
本模組就是產出那個基準樣本——同一個 universe、同一條標籤規則、同一個 producer，
差別**只在於**「有沒有符合觸發條件」。

## 為什麼要排除區間

隨機抽到的 bar 若落在某個觸發事件的答案窗（或其鄰域）裡，它的報酬與該觸發事件的報酬
高度重疊 ⇒ 對照組不再獨立於處理組，prevalence 差會被自身重疊稀釋。
故候選 bar `i` 被排除 iff ∃ 觸發事件 `t`：
`t0_idx(t) − neighborhood_bars ≤ i ≤ label_end_idx(t) + embargo_bars`。

## 標籤路徑只有一條

`all_bars_eval._label_from_rule(direction_sign, close, i, horizon, threshold)`。
**不呼叫 `evaluate_condition`**——隨機批的定義就是「不套條件」，走條件引擎等於
把對照組變成另一個條件樣本。`horizon`／`threshold` 取自
`random_control_spec.label_rule`（契約必填），缺 ⇒ `random_control_label_rule_missing`。

## 分層粒度

`strata.period` 為 `{start_ms, end_ms}` 區間，分層鍵＝`symbol|timeframe|YYYY-MM|direction`
（自然月，UTC）。`D-001` D5.2 只寫 `strata{symbol,timeframe,period,direction}` 而未定義
`period` 如何產生**多個** stratum，D5.4 邊界寫「universe 跨月分層」⇒ 本模組定為自然月。
此為 SPEC 洞之 fail-closed 細化（殘留 `B5-SPECGAP-1`），契約 `doc` 亦具名。
"""

from __future__ import annotations

import datetime as _dt
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples import all_bars_eval as _ab
from momentum.Analysis.event_samples.canonical_serialize import canonical_event_table_sha256
from momentum.Analysis.event_samples.import_contract import (
    canonical_event_id,
    load_event_import_contract,
)
from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.core.logging import get_logger

logger = get_logger(__name__)

#: 隨機批之 `control_kind`／`label_origin`（字面取自契約，載入時對證，不硬寫第二份）。
RANDOM_CONTROL_KIND = "platform_random_bars"
RANDOM_LABEL_ORIGIN = "platform_random"

#: `label_definition.rule_id`（wire 唯一；D-001 D5.2「record」段逐字）。
RANDOM_RULE_ID = "random_control:label_rule"

#: 隨機批之報酬量法恆為 `close_to_close`（規則身分閘之第四項比對對象）。
RANDOM_LABEL_RETURN_MODE = "close_to_close"

#: 本產生器之版本字面（進 receipt；抽樣演算法改動須改此值，否則 golden 無從辨別）。
GENERATOR_VERSION = "gap3-d5.2-v1"

#: `allocation` 之封閉單值（`D-001` D5.2 定死；禁 `round`）。
ALLOCATION_PROPORTIONAL = "proportional_to_candidates"

#: `trigger_receipts` 逐列之**必要鍵**。
#: 🔴 `D-001` 未列舉此參數之鍵集 ⇒ 在此定死並 fail-closed 檢查：
#:    少一個鍵就靜默少排除一段區間，那是「看起來有跑」的最壞失敗形態。
_TRIGGER_KEYS = ("event_id", "symbol", "timeframe", "t0_ms", "label_end_ms")


class RandomControlError(ValueError):
    """帶契約 reason 字面之 fail-closed 例外（`reason` 屬契約封閉集合）。"""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(f"{reason}: {message}")


def _assert_contract_literals(contract: Mapping[str, Any]) -> None:
    """字面對證：本模組寫死的四個值必須真的住在契約裡（漂移 ⇒ 當場炸）。"""
    accepted = contract["required_fields"]["control_kind"]["accepted"]
    if RANDOM_CONTROL_KIND not in accepted:
        raise ValueError(f"sample_random_bars: {RANDOM_CONTROL_KIND!r} 不在契約 control_kind.accepted")
    lo = contract["optional_fields"]["label_origin"]
    if RANDOM_LABEL_ORIGIN not in lo["enum"] or RANDOM_LABEL_ORIGIN in lo["not_importable"]:
        raise ValueError(f"sample_random_bars: {RANDOM_LABEL_ORIGIN!r} 不可用作 label_origin")
    modes = contract["required_fields"]["label_definition"]["fields"]["label_return_mode"]["enum"]
    if RANDOM_LABEL_RETURN_MODE not in modes:
        raise ValueError(f"sample_random_bars: {RANDOM_LABEL_RETURN_MODE!r} 不在契約 label_return_mode.enum")


def _resolve_label_rule(
    spec: Mapping[str, Any], label_rule: Optional[Mapping[str, Any]]
) -> Dict[str, Any]:
    """`label_rule` 之解析（參數與 spec 內容**必須一致**，不設優先序）。

    🔴 `D-001` D5.2 的簽章把 `label_rule` 列為參數，同段又寫「取自
    `random_control_spec.label_rule`（契約必填）」。兩者同時出現時若定「參數優先」，
    落檔的 spec 與實際用來標籤的規則就可能不同——那正是規則身分閘要防的事。
    ⇒ 兩者皆有且不等 ⇒ 直接拒（不猜）。
    """
    in_spec = spec.get("label_rule")
    if label_rule is not None and in_spec is not None and dict(label_rule) != dict(in_spec):
        raise RandomControlError(
            "random_control_label_rule_missing",
            f"label_rule 參數 {dict(label_rule)} 與 spec.label_rule {dict(in_spec)} 不一致；"
            "不設優先序（落檔 spec 與實際標籤規則必須是同一件事）")
    rule = label_rule if label_rule is not None else in_spec
    if rule is None:
        raise RandomControlError(
            "random_control_label_rule_missing",
            "random_control_spec 缺 label_rule{threshold, horizon_bars}；隨機批之 label 無從產生")
    out = dict(rule)
    if set(out) != {"threshold", "horizon_bars"}:
        raise RandomControlError(
            "random_control_label_rule_missing",
            f"label_rule 鍵集須恰為 {{threshold, horizon_bars}}，實得 {sorted(out)}")
    if type(out["threshold"]) is not float:
        raise RandomControlError(
            "random_control_label_rule_missing",
            f"label_rule.threshold 須為 float（契約嚴格判定），實得 {type(out['threshold']).__name__}")
    if type(out["horizon_bars"]) is not int or out["horizon_bars"] < 1:
        raise RandomControlError(
            "random_control_label_rule_missing",
            f"label_rule.horizon_bars 須為 int 且 ≥1，實得 {out['horizon_bars']!r}")
    return out


def _month_key(open_ms: int) -> str:
    """bar open（epoch ms, UTC）→ `YYYY-MM`。"""
    return _dt.datetime.fromtimestamp(open_ms / 1000.0, tz=_dt.timezone.utc).strftime("%Y-%m")


def _exclusion_mask(
    n_rows: int,
    open_ms: np.ndarray,
    close_ms: np.ndarray,
    trigger_rows: Sequence[Mapping[str, Any]],
    neighborhood: int,
    embargo: int,
) -> np.ndarray:
    """排除遮罩：`True` ＝該 index 落在某觸發事件之鄰域／答案窗／embargo 內。"""
    mask = np.zeros(n_rows, dtype=bool)
    for r in trigger_rows:
        t0 = int(r["t0_ms"])
        end = int(r["label_end_ms"])
        t0_pos = int(np.searchsorted(open_ms, t0))
        if t0_pos >= n_rows or int(open_ms[t0_pos]) != t0:
            raise RandomControlError(
                "random_control_period_mismatch",
                f"觸發事件 {r['event_id']!r} 之 t0={t0} 不落在 universe bar 網格上"
                "（觸發批與抽樣母體須同一 symbol／timeframe／快照）")
        end_pos = int(np.searchsorted(close_ms, end))
        if end_pos >= n_rows or int(close_ms[end_pos]) != end:
            raise RandomControlError(
                "random_control_period_mismatch",
                f"觸發事件 {r['event_id']!r} 之 label_end_ms={end} 不落在 universe bar 網格上")
        lo = max(0, t0_pos - neighborhood)
        hi = min(n_rows - 1, end_pos + embargo)
        mask[lo:hi + 1] = True
    return mask


def _allocate(n_target: int, per_key_candidates: List[Tuple[str, int]]) -> Dict[str, int]:
    """`proportional_to_candidates`：floor ＋ 最大餘數 ＋ cap ＋ 同序再分配（禁 `round`）。

    餘數序＝小數部分**降冪**，同分依 stratum key **UTF-8 升冪**（決定性）。
    不變式：`Σ n_drawn == n_target` 且逐層 `n_drawn ≤ n_candidates`。

    🔴 **沒有「cap 後再分配」分支**，因為那個分支證明上不可達：
    呼叫端恆以 `n_target = min(n_requested, candidate_count) ≤ total` 進來，
    於是 `base = floor(n_target × c / total) ≤ floor(c) = c`——base 永不超過該層候選；
    而 `base == c` 只在 `n_target == total` 時發生，那時餘數為 0、也不會再 +1。
    寫一段永遠跑不到的 cap 迴圈只會製造「看起來有防護」的假象且無法被測試覆蓋
    ⇒ 改成把前提**顯式擋在門口**（`n_target > total` 直接全取）。
    """
    total = sum(c for _, c in per_key_candidates)
    if total <= 0 or n_target <= 0:
        return {k: 0 for k, _ in per_key_candidates}
    if n_target >= total:
        # 候選不足以滿足需求 ⇒ 全取（呼叫端已把 n_target 夾到 candidate_count，
        # 此分支只在 `n_target == total` 時經由正常路徑進來）。
        return {k: c for k, c in per_key_candidates}
    alloc: Dict[str, int] = {}
    fracs: List[Tuple[float, str]] = []
    for key, cand in per_key_candidates:
        exact = n_target * cand / total
        base = int(math.floor(exact))
        alloc[key] = base
        fracs.append((exact - base, key))
    order = [k for _, k in sorted(fracs, key=lambda x: (-x[0], x[1]))]
    for key in order[: n_target - sum(alloc.values())]:
        alloc[key] += 1
    if sum(alloc.values()) != n_target:
        raise RuntimeError(f"_allocate: 配額和 {sum(alloc.values())} != n_target {n_target}")
    return alloc


def sample_random_bars(
    bars: Mapping[str, Mapping[str, pd.DataFrame]],
    spec: Mapping[str, Any],
    trigger_receipts: Sequence[Mapping[str, Any]],
    label_rule: Optional[Mapping[str, Any]] = None,
    *,
    scenario: str,
    contract: Optional[dict] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """抽出隨機對照批之 records 與**完整** `random_control_spec`（輸入鍵＋收據鍵）。

    Args:
        bars: `{symbol: {timeframe: DataFrame(open_time_ms, close_time_ms, open, close)}}`（真實 kline）。
        spec: 抽樣契約之**輸入**部分——`universe`／`strata`／`allocation`／`exclusion`／
            `label_rule`／`seed`／`n_requested`／`replacement`。收據鍵（`n_drawn`／`per_stratum`／
            `candidate_count`／`sample_ids_digest`／`data_snapshot_digest`／`generator_version`）
            由本函式填回；輸入若已帶這些鍵一律**覆寫**（它們是產出，不是輸入）。
        trigger_receipts: 觸發批之逐事件收據，每列須含 `_TRIGGER_KEYS`
            （`event_id`／`symbol`／`timeframe`／`t0_ms`／`label_end_ms`）。
        label_rule: 可選；與 `spec["label_rule"]` 不一致 ⇒ 拒（見 `_resolve_label_rule`）。
        scenario: 隨機批之 `scenario`，須與**觸發批相同**（`D-001` D5.2「scenario 同觸發批」）。
            🔴 keyword-only 且**無預設**：`trigger_receipts` 之對齊收據不帶 scenario，
            而猜一個預設值會讓對照批與處理批走不同去重 policy。呼叫端必須顯式給。
        contract: 測試注入用；預設讀 production 契約。

    Returns:
        `(records, receipt)`——`records` 為契約形狀之逐列 dict（未過 validator，由呼叫端
        以同一支 `validate_event_import` 驗，無 profile 分裂）；`receipt` 即完整 spec。

    Raises:
        RandomControlError: `reason` 屬契約 `import_failure_reasons`／
            `capability_unavailable_reasons` 之封閉集合（`random_control_label_rule_missing`／
            `random_control_period_mismatch`）。
    """
    c = contract if contract is not None else load_event_import_contract()
    _assert_contract_literals(c)

    rule = _resolve_label_rule(spec, label_rule)
    horizon = int(rule["horizon_bars"])
    threshold = float(rule["threshold"])

    universe = dict(spec["universe"])
    strata = dict(spec["strata"])
    exclusion = dict(spec["exclusion"])
    symbol = str(universe["symbol"])
    tf = str(universe["timeframe"])

    if str(strata["symbol"]) != symbol or str(strata["timeframe"]) != tf:
        raise RandomControlError(
            "random_control_period_mismatch",
            f"strata（{strata['symbol']}／{strata['timeframe']}）與 universe（{symbol}／{tf}）不同；"
            "跨 symbol／timeframe 之 universe 一律拒（D-001 D5.1 邊界②）")
    if str(spec.get("allocation")) != ALLOCATION_PROPORTIONAL:
        raise RandomControlError(
            "random_control_period_mismatch",
            f"allocation 須為 {ALLOCATION_PROPORTIONAL!r}，實得 {spec.get('allocation')!r}")
    if spec.get("replacement") is not False:
        raise RandomControlError(
            "random_control_period_mismatch",
            "replacement 須為 False（無放回抽樣）")

    trigger_rows = [dict(r) for r in trigger_receipts]
    if not trigger_rows:
        raise RandomControlError(
            "random_control_period_mismatch",
            "trigger_receipts 為空；沒有觸發批就沒有要對照的對象")
    for r in trigger_rows:
        missing = [k for k in _TRIGGER_KEYS if r.get(k) is None]
        if missing:
            raise RandomControlError(
                "random_control_period_mismatch",
                f"trigger_receipts 某列缺鍵 {missing}；排除區間無從計算（不以缺值當 0）")
        if str(r["symbol"]) != symbol or str(r["timeframe"]) != tf:
            raise RandomControlError(
                "random_control_period_mismatch",
                f"觸發事件 {r['event_id']!r} 之 {r['symbol']}／{r['timeframe']} 與 universe "
                f"{symbol}／{tf} 不同；跨 symbol universe ⇒ 拒")

    # ---- period 交集（D-001 D5.2；R1 GROK-R1-P2-02） ----
    trig_lo = min(int(r["t0_ms"]) for r in trigger_rows)
    trig_hi = max(int(r["label_end_ms"]) for r in trigger_rows)
    per_lo, per_hi = int(strata["period"]["start_ms"]), int(strata["period"]["end_ms"])
    if per_hi < trig_lo or per_lo > trig_hi:
        raise RandomControlError(
            "random_control_period_mismatch",
            f"strata.period [{per_lo}, {per_hi}] 與觸發期 [{trig_lo}, {trig_hi}] 無交集；"
            "不同時期的無條件基準不能拿來對照（市況不同）")

    df = bars[symbol][tf]
    open_ms = df["open_time_ms"].to_numpy().astype("int64")
    close_ms = df["close_time_ms"].to_numpy().astype("int64")
    open_ = df["open"].to_numpy()
    close = df["close"].to_numpy()
    n_rows = int(len(df))
    step_ms = int(TIMEFRAME_SECONDS[tf]) * 1000

    neighborhood = int(exclusion["neighborhood_bars"])
    embargo = int(exclusion["embargo_bars"])
    if neighborhood < 0 or embargo < 0:
        raise RandomControlError(
            "random_control_period_mismatch",
            f"neighborhood_bars／embargo_bars 須 ≥0，實得 {neighborhood}／{embargo}")
    excluded = _exclusion_mask(n_rows, open_ms, close_ms, trigger_rows, neighborhood, embargo)

    uni_lo, uni_hi = int(universe["start_ms"]), int(universe["end_ms"])
    direction = str(strata["direction"])
    sign = 1.0 if direction == "long" else -1.0

    # ---- 候選（universe ∩ period ∩ eligible ∩ ¬excluded） ----
    by_key: Dict[str, List[int]] = {}
    for i in range(n_rows):
        ot = int(open_ms[i])
        if ot < uni_lo or ot > uni_hi or ot < per_lo or ot > per_hi:
            continue
        if excluded[i]:
            continue
        # 🔴 與 `evaluate_all_bars`／`generate_events` **同一支** eligibility（同一分母）：
        #    對照組與處理組若用不同的「哪些 bar 算數」，prevalence 差就不是同一個估計量。
        if _ab._is_eligible(i, n_rows, horizon, 0, open_, close, open_ms, step_ms) is not None:
            continue
        by_key.setdefault(f"{symbol}|{tf}|{_month_key(ot)}|{direction}", []).append(i)

    per_key_candidates = sorted((k, len(v)) for k, v in by_key.items())
    candidate_count = sum(c for _, c in per_key_candidates)
    n_requested = int(spec["n_requested"])
    n_target = min(n_requested, candidate_count)
    alloc = _allocate(n_target, per_key_candidates)

    # ---- 抽樣（決定性：strata key 升冪 × 單一 rng） ----
    rng = np.random.default_rng(int(spec["seed"]))
    drawn: List[int] = []
    per_stratum: List[Dict[str, Any]] = []
    for key, cand_n in per_key_candidates:
        take = int(alloc.get(key, 0))
        pool = np.asarray(by_key[key], dtype="int64")
        picked = rng.choice(pool, size=take, replace=False) if take else np.empty(0, dtype="int64")
        drawn.extend(int(x) for x in np.sort(picked))
        per_stratum.append({"key": key, "n_candidates": int(cand_n), "n_drawn": take})
    n_drawn = len(drawn)
    if n_drawn != sum(s["n_drawn"] for s in per_stratum) or n_drawn != n_target:
        raise RuntimeError(
            f"sample_random_bars: 配額不變式失敗（Σper_stratum={sum(s['n_drawn'] for s in per_stratum)}"
            f" n_drawn={n_drawn} n_target={n_target}）")

    # ---- 標籤與 records ----
    rule_digest = canonical_event_table_sha256(rule)
    data_digest = canonical_event_table_sha256({
        "symbol": symbol, "timeframe": tf,
        "open_time_ms": [int(x) for x in open_ms],
        "close": [float(x) for x in close],
    })
    label_definition = {
        "rule_id": RANDOM_RULE_ID,
        "canonical_digest": rule_digest,
        "window": {"horizon_bars": horizon},
        "label_return_mode": RANDOM_LABEL_RETURN_MODE,
    }
    entry_semantic = str(c["required_fields"]["entry_price_semantic"]["default"])
    records: List[Dict[str, Any]] = []
    for i in sorted(drawn):
        t0 = int(open_ms[i])
        y = _ab._label_from_rule(sign, close, i, horizon, threshold)
        records.append({
            "event_id": canonical_event_id(symbol, tf, t0, contract=c),
            "symbol": symbol,
            "timeframe": tf,
            "t0": t0,
            "decision_offset_bars": 0,
            "entry_price_semantic": entry_semantic,
            "direction": direction,
            "scenario": scenario,
            "label_origin": RANDOM_LABEL_ORIGIN,
            "label": int(y),
            "label_value": float(sign * (close[i + horizon] / close[i] - 1.0)),
            "label_definition": dict(label_definition),
            # 🔴 答案窗深度＝`horizon`，是機械事實不是宣告偏好：隨機批之 label 用了
            #    `close[i+horizon]`，即 t₀ 之後 `horizon` 根。匯入端之「全部批次一律須宣告」
            #    （Task 1.11）由此欄滿足，不必另開表單路徑。
            "lookahead_bars_declared": {tf: horizon},
            "control_kind": RANDOM_CONTROL_KIND,
            "source_file_digest": rule_digest,
            "data_snapshot_digest": data_digest,
            "kind_source": "platform_auto",
            "event_source": "platform_generator",
        })

    receipt = {
        **{k: v for k, v in spec.items()},
        "universe": dict(universe),
        "strata": {**strata, "period": {"start_ms": per_lo, "end_ms": per_hi}},
        "allocation": ALLOCATION_PROPORTIONAL,
        "exclusion": {
            "trigger_ids_digest": canonical_event_table_sha256(
                sorted(str(r["event_id"]) for r in trigger_rows)),
            "neighborhood_bars": neighborhood,
            "embargo_bars": embargo,
        },
        "label_rule": dict(rule),
        "seed": int(spec["seed"]),
        "n_requested": n_requested,
        "n_drawn": int(n_drawn),
        "replacement": False,
        "candidate_count": int(candidate_count),
        "per_stratum": per_stratum,
        "sample_ids_digest": canonical_event_table_sha256(sorted(r["event_id"] for r in records)),
        "data_snapshot_digest": data_digest,
        "generator_version": GENERATOR_VERSION,
    }
    logger.info(
        "sample_random_bars: %s/%s 候選 %d、抽出 %d（分層 %d、seed %s）",
        symbol, tf, candidate_count, n_drawn, len(per_stratum), spec["seed"])
    return records, receipt
