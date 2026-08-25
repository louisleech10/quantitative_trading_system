"""GAP-3 UX Task 1.9／1.11 — 答案窗宣告之解析與投影（D-7 之 L2）。

L1（Task 1.10 registry）解析不出深度時，L2 **強制使用者宣告**；本檔把該宣告
①逐 tf 驗收 ②經 Task 2.1b 之**唯一** exported 深度函式 `depth_by_timeframe()` 解析
③投影到 `label_definition.window.horizon_bars` 與 per-symbol embargo 下界。

🔴 五個做錯就洩漏的點（SPEC Task 1.9「不可做」／「邊界」）：

1. **逐 tf**，不是逐批：`future72_*` 在 1h 是 72 根、在 12h 是 6 根 ⇒ 混 TF 批之「該批所屬 tf」
   無唯一值。宣告與深度皆為 `Mapping[tf -> int]`；以**單一輸入框套用全部 tf** ⇒ fail-closed
   （鍵集不等於批內 tf 集即拒）。
2. **逐列**取該列自己的 `timeframe` 寫 `horizon_bars`，不取批次代表值。
3. 預設值取**檔內最大可用 horizon**（有 `future_1..12` ⇒ 12）；**不得**給更小的預設值。
   往下調＝無法驗證之聲明 ⇒ **必須勾選**，否則 fail-closed。
4. **不得**由「檔內有哪些 `future_N` 欄」推斷實際用到第幾根（D-7：偵測不可能）
   ⇒ 檔內欄只決定**預設值**，不決定**下界**；下界由宣告決定。
5. 深度公式**只有一份**（`lookahead_depth.depth_by_timeframe`）；本檔不重寫 max／換算。

🔴 `referenced_columns` 之取得：**條件實際引用**之欄＝`label_definition.filters` 內出現、
且確實存在於該批可見欄集合中的欄名。採「字串出現即算引用」之 shape-agnostic 取法——
`filters` 之物件形狀由 Task 2.2（Phase 2）定案，本檔**不預設其形狀**，只做集合交集；
交集使誤判方向為**多要一次宣告**（安全側），不會漏掉引用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Set, Tuple

from momentum.Analysis.event_samples.lookahead_depth import depth_by_timeframe
from momentum.Analysis.event_samples.lookahead_gate import LookaheadGate
from momentum.Analysis.event_samples.lookahead_registry import (
    PROVENANCE_EXTERNAL_UPLOAD,
    load_lookahead_registry,
    registry_resolvable_columns,
    requires_declaration,
    resolve_lookahead_bars,
)

#: 宣告缺失時之兩種處置（見檔尾 `resolve_declaration` docstring）。
ON_MISSING_REJECT = "reject"
ON_MISSING_BLOCK = "block"
_ON_MISSING_KINDS = (ON_MISSING_REJECT, ON_MISSING_BLOCK)


class LookaheadDeclarationError(ValueError):
    """宣告缺失或不合規（fail-closed；`kind` 由 api 層轉 4xx，非契約 reason 字面）。"""

    def __init__(self, kind: str, message: str, detail: Optional[Dict[str, Any]] = None):
        self.kind = str(kind)
        self.detail = dict(detail or {})
        super().__init__(message)


@dataclass(frozen=True)
class DeclarationOutcome:
    """一次匯入之 L2 解析結果（落檔時整塊寫進批次 receipt）。"""

    requires_declaration: bool
    referenced_columns: Tuple[str, ...]
    default_window_bars: Dict[str, int]
    declared_window_bars: Optional[Dict[str, int]]
    lookahead_bars_declared: Optional[Dict[str, int]]
    acknowledged_unverifiable: bool
    embargo_ms_by_symbol: Dict[str, int]
    gate: LookaheadGate = field(default_factory=LookaheadGate.allowed)

    def to_receipt(self) -> Dict[str, Any]:
        """批次 receipt 形（落檔用；鍵名＝契約 `receipt_schema.batch` 之 `lookahead_bars_declared`）。"""
        return {
            "requires_declaration": bool(self.requires_declaration),
            "referenced_columns": list(self.referenced_columns),
            "default_window_bars": dict(self.default_window_bars),
            "declared_window_bars": None if self.declared_window_bars is None else dict(self.declared_window_bars),
            "lookahead_bars_declared": None if self.lookahead_bars_declared is None else dict(self.lookahead_bars_declared),
            "acknowledged_unverifiable": bool(self.acknowledged_unverifiable),
            "embargo_ms_by_symbol": dict(self.embargo_ms_by_symbol),
            "split_blocked": bool(self.gate.blocked),
        }


# --------------------------------------------------------------------------- 引用欄
def _strings_in(node: Any, out: Set[str]) -> None:
    """遞迴收集物件內之所有字串（鍵與值皆算）；shape-agnostic。"""
    if isinstance(node, str):
        out.add(node)
        return
    if isinstance(node, Mapping):
        for k, v in node.items():
            if isinstance(k, str):
                out.add(k)
            _strings_in(v, out)
        return
    if isinstance(node, (list, tuple, set)):
        for v in node:
            _strings_in(v, out)


def filters_referenced_columns(filters: Any, candidate_columns: Iterable[str]) -> Set[str]:
    """`label_definition.filters` 所引用之欄（∩ 可見欄集合）。

    🔴 不預設 `filters` 之物件形狀（Task 2.2 才定案）；以「字串出現 ∩ 候選欄」判定引用。
    """
    if not filters:
        return set()
    found: Set[str] = set()
    _strings_in(filters, found)
    return {str(c) for c in candidate_columns if str(c) in found}


def batch_referenced_columns(records: Sequence[Mapping[str, Any]], candidate_columns: Iterable[str]) -> Tuple[str, ...]:
    """整批之引用欄聯集（逐列讀 `label_definition.filters`）。"""
    cands = [str(c) for c in candidate_columns]
    out: Set[str] = set()
    for rec in records:
        ld = rec.get("label_definition")
        if isinstance(ld, Mapping):
            out |= filters_referenced_columns(ld.get("filters"), cands)
    return tuple(sorted(out))


# --------------------------------------------------------------------------- 預設值
def default_window_bars_by_timeframe(
    data_columns: Iterable[str],
    timeframes: Iterable[str],
    registry: Optional[Mapping[str, Any]] = None,
) -> Dict[str, int]:
    """逐 tf 之**預設**宣告值＝檔內可解析未來欄之最大深度（SPEC Task 1.9 ①）。

    🔴 這是**預設值**，不是下界——使用者可勾選聲明後往下調（那正是 L2 的存在理由）。
    檔內無可解析未來欄 ⇒ 0（無可用 horizon，不假造）。
    """
    r = registry if registry is not None else load_lookahead_registry()
    cols = [str(c) for c in data_columns]
    out: Dict[str, int] = {}
    for tf in timeframes:
        tf = str(tf)
        depths = [resolve_lookahead_bars(c, tf, r) for c in cols]
        out[tf] = max([int(d) for d in depths if d is not None], default=0)
    return out


# --------------------------------------------------------------------------- 投影
def embargo_ms_by_symbol(
    records: Sequence[Mapping[str, Any]],
    lookahead_bars_declared: Mapping[str, int],
    *,
    timeframe_seconds: Mapping[str, int],
) -> Dict[str, int]:
    """宣告深度投影出之 per-symbol embargo 下界（毫秒）。

    `embargo(symbol) = max over 該 symbol 之列 of depth[列.timeframe] * timeframe_seconds[列.timeframe] * 1000`

    🔴 `timeframe_seconds` 為**注入之 map**（SPEC §D-3′-a(ii) R22），不得取 module-level 常數。
    🔴 本函式只做**宣告面之投影**；`purge_lower_bound_ms(scope)` 之完整式（另取 `label_window_ms`
       之 max、scope＝`prepared0.windows`）唯一定義在 SPEC §D-3′-a(ii)，由 Task 7.0b 實作，本檔不重述。
       兩者在 CSV 路徑同值：`horizon_bars` 正是由同一個 depth 投影而來（見 `apply_horizon_projection`）。
    """
    out: Dict[str, int] = {}
    for rec in records:
        sym = rec.get("symbol")
        tf = rec.get("timeframe")
        if sym is None or tf is None:
            continue
        tf = str(tf)
        if tf not in lookahead_bars_declared or tf not in timeframe_seconds:
            raise LookaheadDeclarationError(
                "lookahead_declaration_invalid",
                f"timeframe {tf!r} 不在宣告鍵集或 timeframe_seconds（fail-closed，不以其他 tf 之值默認替代）",
            )
        ms = int(lookahead_bars_declared[tf]) * int(timeframe_seconds[tf]) * 1000
        key = str(sym)
        out[key] = max(out.get(key, 0), ms)
    return out


def apply_horizon_projection(
    records: Sequence[Mapping[str, Any]],
    lookahead_bars_declared: Mapping[str, int],
) -> int:
    """就地把 `max(1, depth[該列 timeframe])` 寫進 `label_definition.window.horizon_bars`；回寫入列數。

    🔴 **逐列**取該列自己的 `timeframe`（SPEC R11：批內可有多 TF，「該批所屬 tf」無唯一值）。
    🔴 `max(1, ...)` 是**契約下限之投影**（深度 0 時 `horizon_bars=1` 只是 serialization floor，
       深度語意另住 `lookahead_bars_declared`；SPEC §D-3′-a(i) R9）。
    🔴 **呼叫時機＝Task 1.8 之批次同質檢查之後**：多 TF 批之逐 tf 深度不同 ⇒ 逐列 `horizon_bars`
       本就不同，若在 validate 前投影會被 `label_definition` 同質維度判為異質列而整批拒收
       （Task 1.8 之標的是**使用者宣告**之異質，不是平台導出之逐 tf 投影）。
    """
    n = 0
    for rec in records:
        tf = rec.get("timeframe")
        if tf is None:
            continue
        tf = str(tf)
        if tf not in lookahead_bars_declared:
            raise LookaheadDeclarationError(
                "lookahead_declaration_invalid",
                f"timeframe {tf!r} 不在宣告鍵集（fail-closed）",
            )
        ld = rec.get("label_definition")
        if not isinstance(ld, dict):
            continue
        window = ld.get("window")
        if not isinstance(window, dict):
            window = {}
            ld["window"] = window
        window["horizon_bars"] = max(1, int(lookahead_bars_declared[tf]))
        n += 1
    return n


# --------------------------------------------------------------------------- 主入口
def _validate_declaration_shape(
    declaration: Mapping[str, Any],
    timeframes: Sequence[str],
) -> Tuple[Dict[str, int], bool]:
    if not isinstance(declaration, Mapping):
        raise LookaheadDeclarationError(
            "lookahead_declaration_invalid",
            f"lookahead_declaration 須為物件，實得 {type(declaration).__name__}",
        )
    declared = declaration.get("declared_window_bars")
    if not isinstance(declared, Mapping):
        raise LookaheadDeclarationError(
            "lookahead_declaration_invalid",
            "lookahead_declaration.declared_window_bars 須為 {timeframe: 正整數} 之物件"
            "（🔴 逐 tf 各一值；單一輸入框套用全部 tf 不被接受）",
        )
    keys = {str(k) for k in declared}
    expected = {str(tf) for tf in timeframes}
    if keys != expected:
        raise LookaheadDeclarationError(
            "lookahead_declaration_invalid",
            f"declared_window_bars 鍵集須恰為批內 timeframe 集合 {sorted(expected)}，實得 {sorted(keys)}"
            "（fail-closed：缺鍵不以其他 tf 之值默認替代，多鍵不靜默忽略）",
            {"expected_timeframes": sorted(expected), "declared_timeframes": sorted(keys)},
        )
    out: Dict[str, int] = {}
    by_str = {str(k): v for k, v in declared.items()}
    for tf in sorted(expected):
        v = by_str[tf]
        if type(v) is not int or v < 1:  # noqa: E721 —— bool 是 int 子類，須用 type() 擋
            raise LookaheadDeclarationError(
                "lookahead_declaration_invalid",
                f"declared_window_bars[{tf!r}] 須為正整數（任意正整數，不限 1..12；bool 亦拒），實得 {v!r}",
            )
        out[tf] = int(v)
    ack = declaration.get("acknowledged_unverifiable", False)
    if type(ack) is not bool:  # noqa: E721
        raise LookaheadDeclarationError(
            "lookahead_declaration_invalid",
            f"acknowledged_unverifiable 須為 bool，實得 {ack!r}",
        )
    return out, ack


def resolve_declaration(
    records: Sequence[Dict[str, Any]],
    *,
    data_columns: Iterable[str],
    declaration: Optional[Mapping[str, Any]],
    timeframe_seconds: Mapping[str, int],
    on_missing: str = ON_MISSING_REJECT,
    provenance: str = PROVENANCE_EXTERNAL_UPLOAD,
    registry: Optional[Mapping[str, Any]] = None,
) -> DeclarationOutcome:
    """解析一次匯入之 L2 宣告；必要時**就地**寫回 `label_definition.window.horizon_bars`。

    Args:
        records: 已解析之契約記錄（就地投影 `horizon_bars`）。
        data_columns: 該批**可見**之欄集合（CSV header／記錄鍵；含未對映欄）——只用於
            ①預設值 ②引用欄之候選集合，**不**當作引用欄本身。
        declaration: `{"declared_window_bars": {tf: int}, "acknowledged_unverifiable": bool}`；
            `None` ＝使用者未填。
        timeframe_seconds: 注入之 tf → 秒 map（SPEC R22；不得取 module-level 常數）。
        on_missing: 需宣告卻未填時之處置——
            `"reject"`＝有宣告 UI 之路徑（Task 1.11 邊界②：fail-closed，落檔數 0）；
            `"block"`＝無宣告 UI 之路徑（JSON／平台產生器），落檔但 L3 封鎖切分（Task 1.12）。
        provenance: 信任邊界（預設 `external_upload`：欄名對外部來源不具證據力）。

    Raises:
        LookaheadDeclarationError: 需宣告卻未填（`on_missing="reject"`）、宣告形狀不合、
            或未勾聲明而調低。
    """
    if on_missing not in _ON_MISSING_KINDS:
        raise ValueError(f"未知 on_missing: {on_missing!r}（封閉集合 {_ON_MISSING_KINDS}）")
    r = registry if registry is not None else load_lookahead_registry()
    cols = [str(c) for c in data_columns]
    timeframes = sorted({str(rec["timeframe"]) for rec in records if rec.get("timeframe") is not None})

    referenced = batch_referenced_columns(records, cols)
    unknown_tfs = [tf for tf in timeframes if tf not in timeframe_seconds]
    if unknown_tfs and (referenced or declaration is not None):
        raise LookaheadDeclarationError(
            "lookahead_declaration_invalid",
            f"批內 timeframe {unknown_tfs} 不在 timeframe_seconds（深度換算無定義，fail-closed）",
        )

    needs = any(
        requires_declaration(referenced, tf, provenance=provenance, registry=r) for tf in timeframes
    ) if referenced else False
    defaults = default_window_bars_by_timeframe(cols, timeframes, r) if timeframes and not unknown_tfs else {}

    if declaration is None:
        if needs and on_missing == ON_MISSING_REJECT:
            raise LookaheadDeclarationError(
                "lookahead_declaration_required",
                "本批之篩選條件引用了深度無法由 registry 驗證之欄位 ⇒ 依 D-7 之 L2 必須宣告答案窗"
                "（逐 timeframe 各一值）；未宣告一律拒收，不以任何預設深度代替",
                {"referenced_columns": list(referenced), "default_window_bars": defaults},
            )
        gate = (
            LookaheadGate.blocked_by(
                "未填答案窗宣告，深度不可證（L2 未完成）", tuple(referenced)
            )
            if needs
            else LookaheadGate.allowed()
        )
        return DeclarationOutcome(
            requires_declaration=needs, referenced_columns=tuple(referenced), default_window_bars=defaults,
            declared_window_bars=None, lookahead_bars_declared=None, acknowledged_unverifiable=False,
            embargo_ms_by_symbol={}, gate=gate,
        )

    declared, ack = _validate_declaration_shape(declaration, timeframes)
    lowered = sorted(tf for tf in timeframes if declared[tf] < int(defaults.get(tf, 0)))
    if lowered and not ack:
        raise LookaheadDeclarationError(
            "lookahead_declaration_unacknowledged_lowering",
            f"宣告值低於檔內最大可用 horizon（{ {tf: defaults[tf] for tf in lowered} }）"
            "，須勾選「我的篩選條件未用到超過第 N 根」之聲明才可調低；該聲明無法由系統驗證，"
            "錯報將導致資料洩漏",
            {"lowered_timeframes": lowered, "default_window_bars": defaults, "declared_window_bars": declared},
        )

    # 🔴 調低＝使用者聲明「未用到那些欄」⇒ 該批之引用欄不再納入 max（否則調低永遠無效）；
    #    未調低時把可解析欄一併餵進去，讓同一式在兩種情形都做**真正的** max（交叉檢查，非儀式）。
    referenced_for_depth: Tuple[str, ...] = ()
    if not lowered:
        resolvable: Set[str] = set()
        for tf in timeframes:
            resolvable |= registry_resolvable_columns(referenced, tf, r)
        referenced_for_depth = tuple(sorted(resolvable))

    depth = depth_by_timeframe(referenced_for_depth, declared, timeframes, registry=r)
    # 🔴 本函式**不**就地投影 `horizon_bars`：投影須發生在 Task 1.8 之批次同質檢查**之後**，
    #    否則多 TF 批（1.9 ⑥）之逐 tf 不同 horizon 會被 `label_definition` 同質維度誤判為異質列。
    #    投影由呼叫端於 validate 後呼叫 `apply_horizon_projection()`（見其 docstring）。
    embargo = embargo_ms_by_symbol(records, depth, timeframe_seconds=timeframe_seconds)
    return DeclarationOutcome(
        requires_declaration=needs, referenced_columns=tuple(referenced), default_window_bars=defaults,
        declared_window_bars=declared, lookahead_bars_declared=dict(depth), acknowledged_unverifiable=bool(ack),
        embargo_ms_by_symbol=embargo, gate=LookaheadGate.allowed(),
    )


def gate_from_receipt(receipt: Optional[Mapping[str, Any]]) -> LookaheadGate:
    """由落檔之批次 receipt 還原 L3 閘（analyze 時用）。

    🔴 receipt 缺整塊 ⇒ **不封鎖**：那是 Task 1.9 上線前落檔之舊批
    （使用者 2026-08-05「面向未來不溯及既往」）；新落檔一律帶本塊。
    """
    if not receipt:
        return LookaheadGate.allowed()
    if receipt.get("split_blocked") or (receipt.get("requires_declaration") and not receipt.get("lookahead_bars_declared")):
        return LookaheadGate.blocked_by(
            "本批之答案窗宣告缺失，深度不可證（L2 未完成）",
            tuple(str(c) for c in (receipt.get("referenced_columns") or ())),
        )
    return LookaheadGate.allowed()


__all__ = [
    "ON_MISSING_BLOCK",
    "ON_MISSING_REJECT",
    "DeclarationOutcome",
    "LookaheadDeclarationError",
    "apply_horizon_projection",
    "batch_referenced_columns",
    "default_window_bars_by_timeframe",
    "embargo_ms_by_symbol",
    "filters_referenced_columns",
    "gate_from_receipt",
    "resolve_declaration",
]
