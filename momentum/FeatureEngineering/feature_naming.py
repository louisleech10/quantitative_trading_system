"""特徵欄名之單一真相源：文法、具型身分、formatter／parser、週期標記之加與剝、ratio-unsafe 類別判定、命名世代
（docs/FFNAME_SPEC.md Task 1.1；docs/RATIOUNSAFE_SPEC.md Task 1.1）。

純函式、無狀態。週期鍵一律取自 `TimeframeAligner._timeframe_seconds_keys()`（不寫死週期清單或正則）。
文法：`<source>_<tf>_<category>_<indicator>[_<params>][_<op>]*`；段間 `_`、段內 `-`；任一段不得含 `_`。
生成期間（儲存標記前）之未標記形去掉第 2 段（`parse_feature_name(name, tagged=False)`）；`tag_timeframe` 只把未標記形
轉為完整形：`label_` 開頭、少於 2 段、或 `parts[1] == timeframe` ⇒ 原樣；否則插於第一段後。
"""

from __future__ import annotations

import dataclasses
import re
from functools import lru_cache
from typing import FrozenSet, Iterable, Optional, Tuple

# FF-NAME Task 1.1：命名世代（config hash 鹽與 manifest 鍵之唯一來源；manifest 無此鍵者視為 1）
CURRENT_FEATURE_NAMING_VERSION: int = 2

# 封閉 category 集合（取代 `ms_`／`tr_`／`ent_`／`cs_`／`meta_` 前綴族）
FEATURE_CATEGORIES: FrozenSet[str] = frozenset({
    "trend", "momentum", "volatility", "volume", "cycle", "statistics", "pattern", "price-transform",
    "entropy", "microstructure", "tail-risk", "raw", "cross-sectional", "meta", "custom",
})

# op 段：名稱 → 參數段之正則（None＝不可帶參數）；op 名與參數以 `-` 連接於同一段
_W = r"W[0-9]+"
_OP_ARGS = {
    # L2 配對
    "Cross": None, "Ratio": None,
    # L2 單欄
    "Distance": None, "SignedStrength": None, "Sign": None, "Log1p": None, "Abs": None, "Clip": None,
    "Momentum": r"L[0-9]+", "BinarySignal": r"[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*", "TsArgmax": _W, "TsArgmin": _W, "TsRank": _W,
    "DecayLinear": _W, "TsCorr": r"[0-9a-f]{8}-" + _W,
    # L3 滾動彙總（`rolling_aggregator._format_agg_label`）
    "Slope": _W, "Std": _W, "Mean": _W, "Rank": _W, "ZScore": _W, "Skew": _W, "Kurt": _W, "Min": _W, "Max": _W,
    "Range": _W,
    # L4 lag
    "Lag": r"[0-9]+",
    # L6.5（append 模式後綴）
    "fracdiff": None, "diff": r"[0-9]+", "rank": None, "gaussian": None, "zscore": r"[0-9]+",
}
BINARY_SIGNAL_OPTIONAL = "BinarySignal"  # BinarySignal 之後綴可省略
L3_OPS: FrozenSet[str] = frozenset({"Slope", "Std", "Mean", "Rank", "ZScore", "Skew", "Kurt", "Min", "Max", "Range"})
L65_OPS: FrozenSet[str] = frozenset({"fracdiff", "diff", "rank", "gaussian", "zscore"})

_LABEL_PREFIX = "label_"
_WORD = r"[A-Za-z0-9.]+"
_SOURCE_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
_INDICATOR_RE = re.compile(r"^[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*$")
_PARAM_MEMBER = rf"{_WORD}(?:-{_WORD})*"
_PARAMS_RE = re.compile(rf"^{_PARAM_MEMBER}(?:~{_PARAM_MEMBER})*$")
_CUSTOM_SLUG_RE = re.compile(r"^[a-z0-9-]+$")


class FeatureNameParseError(ValueError):
    """欄名不合文法（不猜、不回退）。"""


class LabelColumnNotFeatureError(FeatureNameParseError):
    """`label_*` 不屬特徵文法。"""


class FeatureNamingVersionError(RuntimeError):
    """特徵產物之命名世代缺失、過舊、無法解析或多標的不一致（訊息含 `feature_naming_version` 與重生指引）。"""


@dataclasses.dataclass(frozen=True)
class FeatureIdentity:
    """特徵欄之具型身分；欄名為其唯一序列化（`format_feature_name`）。`tf is None` 表生成期間之未標記形。"""

    source: str
    tf: Optional[str]
    category: str
    indicator: str
    params: Tuple[Tuple[str, ...], ...] = ()
    ops: Tuple[str, ...] = ()

    @property
    def kind(self) -> str:
        """kind 由身分機械導出（SPEC v13 Task 1.1）。"""
        fixed = {"custom": "custom", "raw": "raw-lag", "cross-sectional": "cross-sectional", "meta": "meta"}
        if self.category in fixed:
            return fixed[self.category]
        names = [_op_name(op) for op in self.ops]
        if names and names[-1] in L65_OPS:
            return "preprocess"
        if any(n in L3_OPS for n in names):
            return "rolling"
        if names:
            return "derived"
        return "atomic"


def canonical_segment(label: str) -> str:
    """段內正規化：`_`→`-`（冪等）。"""
    return str(label).replace("_", "-")


def is_label_column(name: str) -> bool:
    """`label_*` 標籤欄（不屬特徵文法）。"""
    return str(name).startswith(_LABEL_PREFIX)


def _op_name(op: str) -> str:
    return op.split("-", 1)[0]


def _is_op_segment(seg: str) -> bool:
    return _op_name(seg) in _OP_ARGS


def _validate_op(seg: str) -> None:
    name, _, arg = seg.partition("-")
    if name not in _OP_ARGS:
        raise FeatureNameParseError(f"未知 op 段 {seg!r}")
    pattern = _OP_ARGS[name]
    if pattern is None:
        if arg:
            raise FeatureNameParseError(f"op {name!r} 不帶參數：{seg!r}")
        return
    if not arg:
        if name == BINARY_SIGNAL_OPTIONAL:
            return
        raise FeatureNameParseError(f"op {name!r} 缺參數：{seg!r}")
    if not re.fullmatch(pattern, arg):
        raise FeatureNameParseError(f"op {name!r} 參數不合：{seg!r}")


def _parse_params(seg: str) -> Tuple[Tuple[str, ...], ...]:
    if not _PARAMS_RE.fullmatch(seg):
        raise FeatureNameParseError(f"參數段含非法字元或格式：{seg!r}")
    return tuple(tuple(member.split("-")) for member in seg.split("~"))


def parse_feature_name(name: str, tagged: bool = True) -> FeatureIdentity:
    """欄名 → `FeatureIdentity`；不合文法 ⇒ `FeatureNameParseError`（`label_*` ⇒ `LabelColumnNotFeatureError`）。"""
    text = str(name)
    if is_label_column(text):
        raise LabelColumnNotFeatureError(f"{text!r} 為標籤欄，不屬特徵文法")
    segs = text.split("_")
    if any(s == "" for s in segs):
        raise FeatureNameParseError(f"{text!r} 含空段")
    head = 4 if tagged else 3
    if len(segs) < head:
        raise FeatureNameParseError(f"{text!r} 段數不足（需 source{'、tf' if tagged else ''}、category、indicator）")
    source = segs[0]
    if tagged:
        tf: Optional[str] = segs[1]
        if tf not in timeframe_keys():
            raise FeatureNameParseError(f"{text!r} 第 2 段 {tf!r} 不屬週期鍵")
        category, indicator = segs[2], segs[3]
    else:
        tf = None
        category, indicator = segs[1], segs[2]
    if not _SOURCE_RE.fullmatch(source):
        raise FeatureNameParseError(f"{text!r} 來源段 {source!r} 不合")
    if category not in FEATURE_CATEGORIES:
        raise FeatureNameParseError(f"{text!r} category {category!r} 不屬封閉集合")
    if not _INDICATOR_RE.fullmatch(indicator):
        raise FeatureNameParseError(f"{text!r} 指標段 {indicator!r} 不合")
    if category == "custom" and not _CUSTOM_SLUG_RE.fullmatch(indicator):
        raise FeatureNameParseError(f"{text!r} custom slug {indicator!r} 不合 [a-z0-9-]")
    rest = segs[head:]
    params: Tuple[Tuple[str, ...], ...] = ()
    if rest and not _is_op_segment(rest[0]):
        params = _parse_params(rest[0])
        rest = rest[1:]
    for seg in rest:
        _validate_op(seg)
    return FeatureIdentity(source=source, tf=tf, category=category, indicator=indicator, params=params,
                           ops=tuple(rest))


def format_feature_name(identity: FeatureIdentity) -> str:
    """`FeatureIdentity` → 欄名（唯一序列化；`tf is None` 時為未標記形）。"""
    segs = [identity.source]
    if identity.tf is not None:
        segs.append(identity.tf)
    segs += [identity.category, identity.indicator]
    if identity.params:
        segs.append("~".join("-".join(member) for member in identity.params))
    segs += list(identity.ops)
    name = "_".join(segs)
    parse_feature_name(name, tagged=identity.tf is not None)  # 產出端即驗文法（不合即拋，不落盤不合文法之名）
    return name


# ---------------------------------------------------------------- 產生端共用之身分建構（FF-NAME Phase 2）


def source_from_inputs(inputs: Iterable[str]) -> str:
    """輸出點輸入元組 → source 段：依輸出點契約之順序逐鍵 `canonical_segment` 後以 `-` 串接（SPEC Task 2.2；
    例 `("close", "quote_volume")` ⇒ `close-quote-volume`）。空元組 ⇒ ValueError（source 不得為空）。"""
    keys = [canonical_segment(k) for k in inputs]
    if not keys:
        raise ValueError("source_from_inputs：輸入元組為空，無法決定 source")
    return "-".join(keys)


def build_identity(source: str, category: str, indicator: str, params: Iterable[object] = (),
                   timeframe: Optional[str] = None) -> FeatureIdentity:
    """產生端身分常數之建構（自製 atomic、entropy、microstructure、tail-risk、custom、L5、L6 共用）：source／category／
    indicator 經 `canonical_segment`；`params` 之值以 `str` 成單一成員之 token（空 ⇒ 無參數段）。"""
    tokens = tuple(str(v) for v in params)
    return FeatureIdentity(source=canonical_segment(source), tf=timeframe, category=canonical_segment(category),
                           indicator=canonical_segment(indicator), params=(tokens,) if tokens else ())


def raw_value_identity(raw_key: str, timeframe: Optional[str] = None) -> FeatureIdentity:
    """raw kline 欄之身分 `<canonical raw>_<tf>_raw_value`（L4 raw lag 輸入與 TsCorr 目標；SPEC Task 2.4）。"""
    return FeatureIdentity(source=canonical_segment(raw_key), tf=timeframe, category="raw", indicator="value")


def tscorr_op(corr_with: str, window: int) -> str:
    """TsCorr op 段：`TsCorr-<digest8>-W<w>`；digest＝目標 raw 欄未標記形身分之 `format_feature_name` 字串
    （UTF-8）sha256 前 8 碼（SPEC Task 1.1／2.3；與 Task 0.1 凍結同一定義）。"""
    import hashlib

    target = format_feature_name(raw_value_identity(corr_with))
    return f"TsCorr-{hashlib.sha256(target.encode('utf-8')).hexdigest()[:8]}-W{int(window)}"


def binary_signal_op(name_suffix: Optional[str]) -> str:
    """BinarySignal op 段：後綴經 `canonical_segment` 成單一段（`Strong_Trend`→`BinarySignal-Strong-Trend`）；
    無後綴 ⇒ `BinarySignal`；後綴不合字母表 ⇒ `FeatureNameParseError`（ValueError 子類，設定載入時即拋）。"""
    if name_suffix is None:
        return "BinarySignal"
    suffix = canonical_segment(name_suffix)
    if not re.fullmatch(_OP_ARGS["BinarySignal"], suffix):
        raise FeatureNameParseError(f"BinarySignal 後綴 {name_suffix!r} 經 canonical 後 {suffix!r} 不合 [A-Za-z0-9.]+(-…)*")
    return f"BinarySignal-{suffix}"


def is_valid_custom_slug(slug: str) -> bool:
    """custom 指標 slug 是否合 `[a-z0-9-]+`（SPEC Task 2.2）。"""
    return _CUSTOM_SLUG_RE.fullmatch(str(slug)) is not None


def custom_output_indicator(slug: str, output_key: str, single_output: bool) -> str:
    """custom 輸出欄之 indicator 段：單一輸出＝定義 slug；多輸出＝`<slug>-<canonical 輸出鍵>`。
    不合 `[a-z0-9-]+` ⇒ ValueError（設定驗證時即拋，於呼叫任何使用者函式之前；SPEC Task 2.2）。"""
    indicator = str(slug) if single_output else f"{slug}-{canonical_segment(output_key)}"
    if not is_valid_custom_slug(indicator):
        raise ValueError(f"custom 指標 slug {indicator!r}（定義 {slug!r}、輸出 {output_key!r}）不合 [a-z0-9-]+")
    return indicator


def append_op_segments(name: str, *ops: str) -> str:
    """熱路徑之 op 段追加（L3 滾動彙總每次可達 10^5 欄）：文法之 op 段以 `_` 接於既有欄名之後；不逐欄重跑 parser。
    呼叫端保證 `name` 為合法欄名、`ops` 由封閉 op 名與數值參數組成；落盤前之文法驗收由 Task 2.6／3.x 測試把關。"""
    return "_".join([str(name), *map(str, ops)])


def with_ops(name: str, *ops: str, tagged: bool = False) -> str:
    """於既有欄名之身分後追加 op 段（L2 單欄算子與 L4 用；經 parser 與 formatter 驗文法，不做字串拼接）。"""
    identity = parse_feature_name(name, tagged=tagged)
    return format_feature_name(dataclasses.replace(identity, ops=tuple(identity.ops) + tuple(ops)))


UNSUPPORTED_KIND = "unsupported"


def feature_descriptor(name: str) -> dict:
    """欄名 → 版本化描述（FF-NAME Task 1.2／3.3 之單一來源；API 與向量匯出器共用）。

    合法名：`{version, kind, source, tf, category, indicator, params, ops, display}`（params 逐層轉 list）；
    不合文法：`{version, kind: "unsupported", error: <例外類別名>, display}`（fail-closed，不猜）。
    """
    text = str(name)
    try:
        ident = parse_feature_name(text)
    except FeatureNameParseError as exc:
        return {"version": CURRENT_FEATURE_NAMING_VERSION, "kind": UNSUPPORTED_KIND, "error": type(exc).__name__,
                "display": text}
    return {"version": CURRENT_FEATURE_NAMING_VERSION, "kind": ident.kind, "source": ident.source, "tf": ident.tf,
            "category": ident.category, "indicator": ident.indicator,
            "params": [list(member) for member in ident.params], "ops": list(ident.ops), "display": text}


# RATIOUNSAFE Task 1.1：ratio-unsafe 類別之單一常數（`derived_operators`、`rolling_aggregator`、`feature_preprocessor` re-export 同一物件）
RATIO_UNSAFE_CATEGORIES: FrozenSet[str] = frozenset({"pattern"})

_LABEL_PREFIX = "label_"


@lru_cache(maxsize=1)
def timeframe_keys() -> FrozenSet[str]:
    """全部合法週期鍵（取自 `TimeframeAligner._timeframe_seconds_keys()`）。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    return frozenset(str(k) for k in TimeframeAligner._timeframe_seconds_keys())


def tag_timeframe(column: str, timeframe: str) -> str:
    """欄名加週期標記（群組週期身分規則）；`timeframe` 不屬週期鍵 ⇒ ValueError。"""
    tf = str(timeframe)
    if tf not in timeframe_keys():
        raise ValueError(f"tag_timeframe：週期 {tf!r} 不屬週期鍵 {sorted(timeframe_keys())}")
    name = str(column)
    if name.startswith(_LABEL_PREFIX):
        return name
    parts = name.split("_")
    if len(parts) < 2 or parts[1] == tf:
        return name
    return "_".join([parts[0], tf] + parts[1:])


def strip_timeframe_tag(column: str) -> str:
    """去除第二段之週期標記（非 `label_`、至少 3 段且 `parts[1]` 屬週期鍵）；否則原樣。"""
    name = str(column)
    if name.startswith(_LABEL_PREFIX):
        return name
    parts = name.split("_")
    if len(parts) >= 3 and parts[1] in timeframe_keys():
        return "_".join([parts[0]] + parts[2:])
    return name


def ratio_unsafe_category(column: str) -> Optional[str]:
    """共同核心：去標記後 `split("_", 2)[1]` 屬 `RATIO_UNSAFE_CATEGORIES` 則回之，否則 None。"""
    parts = strip_timeframe_tag(column).split("_", 2)
    if len(parts) >= 2 and parts[1] in RATIO_UNSAFE_CATEGORIES:
        return parts[1]
    return None


def is_ratio_unsafe_column(column: str) -> bool:
    """＝ `ratio_unsafe_category(column) is not None`。"""
    return ratio_unsafe_category(column) is not None
