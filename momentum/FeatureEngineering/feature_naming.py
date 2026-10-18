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


def parse_either_form(column: str) -> Optional[FeatureIdentity]:
    """完整形或未標記形欄名 → 身分；形態依第 2 段是否屬週期鍵機械判定（未標記形之第 2 段為 category，與週期鍵
    不相交）。`label_*`、不合文法 ⇒ None（呼叫端自行具名處理，不猜）。"""
    name = str(column)
    if is_label_column(name):
        return None
    parts = name.split("_", 2)
    tagged = len(parts) >= 2 and parts[1] in timeframe_keys()
    try:
        return parse_feature_name(name, tagged=tagged)
    except FeatureNameParseError:
        return None


@dataclasses.dataclass(frozen=True)
class IdentitySpec:
    """結構化選欄之身分條件（FF-NAME Task 3.2）：indicator 精確相等；`params` 給定時第一個參數成員須相等；
    `source` 給定時 source 須相等；只取無 op 之原子欄（L1）。"""

    indicator: str
    params: Optional[Tuple[str, ...]] = None
    source: Optional[str] = None

    def matches(self, identity: FeatureIdentity) -> bool:
        if identity.ops or identity.indicator != self.indicator:
            return False
        if self.source is not None and identity.source != self.source:
            return False
        if self.params is not None and (not identity.params or tuple(identity.params[0]) != tuple(self.params)):
            return False
        return True


def find_identity_column(columns: Iterable[object], specs: Iterable[IdentitySpec]) -> Optional[object]:
    """依 `specs` 之優先序回第一個身分相符之欄（同一 spec 內依欄序取第一個）；皆無 ⇒ None。
    欄名以 `parse_either_form` 解析（完整形或未標記形）；不以子字串比對（`ATR`／`14` 不命中 `NATR`／`144`）。"""
    parsed = [(col, parse_either_form(str(col))) for col in columns]
    for spec in specs:
        for col, identity in parsed:
            if identity is not None and spec.matches(identity):
                return col
    return None


def feature_layer(identity: FeatureIdentity) -> str:
    """管線層由身分導出（FF-NAME Task 3.1；最外層 op 決定）：L6.5 op ⇒ `layer6_5`；category `meta` ⇒ `layer6`、
    `cross-sectional` ⇒ `layer5`；`Lag` ⇒ `layer4`；L3 滾動彙總 ⇒ `layer3`；其餘 op ⇒ `layer2`；無 op ⇒ `layer1`。"""
    names = [_op_name(op) for op in identity.ops]
    last = names[-1] if names else ""
    if last in L65_OPS:
        return "layer6_5"
    if identity.category == "meta":
        return "layer6"
    if identity.category == "cross-sectional":
        return "layer5"
    if last == "Lag":
        return "layer4"
    if last in L3_OPS:
        return "layer3"
    if names:
        return "layer2"
    return "layer1"


def ratio_unsafe_category(column: str) -> Optional[str]:
    """共同核心（FF-NAME Task 3.1）：`parse` 後之 category 屬 `RATIO_UNSAFE_CATEGORIES` 則回之；label、不合文法或
    非該類 ⇒ None（完整形與未標記形皆可；不以子字串或位置切段判定）。"""
    identity = parse_either_form(column)
    if identity is not None and identity.category in RATIO_UNSAFE_CATEGORIES:
        return identity.category
    return None


# ---------------------------------------------------------------- 命名世代閘（FF-NAME Task 3.4）

FEATURE_NAMING_VERSION_KEY = "feature_naming_version"
_REGENERATION_HINT = "請以現行 Feature Factory 重新生成該 run（舊命名世代之產物不支援讀取，開發階段以重產取代遷移）"


def _manifest_naming_version(manifest: object) -> object:
    if not isinstance(manifest, dict):
        return None
    return manifest.get(FEATURE_NAMING_VERSION_KEY)


def assert_feature_naming_version(manifest: object, *, where: str = "") -> int:
    """manifest 之 `feature_naming_version` 須存在、為整數且等於 `CURRENT_FEATURE_NAMING_VERSION`；
    缺鍵、舊版／未知版、無法解析 ⇒ `FeatureNamingVersionError`（訊息含鍵名與重生指引）。"""
    label = f"（{where}）" if where else ""
    if not isinstance(manifest, dict) or FEATURE_NAMING_VERSION_KEY not in manifest:
        raise FeatureNamingVersionError(
            f"特徵 manifest 缺 {FEATURE_NAMING_VERSION_KEY}{label}；預期 {CURRENT_FEATURE_NAMING_VERSION}。{_REGENERATION_HINT}")
    raw = manifest[FEATURE_NAMING_VERSION_KEY]
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise FeatureNamingVersionError(
            f"特徵 manifest 之 {FEATURE_NAMING_VERSION_KEY}={raw!r} 無法解析{label}；預期整數 "
            f"{CURRENT_FEATURE_NAMING_VERSION}。{_REGENERATION_HINT}")
    if raw != CURRENT_FEATURE_NAMING_VERSION:
        raise FeatureNamingVersionError(
            f"特徵 manifest 之 {FEATURE_NAMING_VERSION_KEY}={raw} 與現行 {CURRENT_FEATURE_NAMING_VERSION} 不符{label}。"
            f"{_REGENERATION_HINT}")
    return raw


def _normalize_h5_attr(value: object) -> object:
    """h5 屬性值 → JSON 等價值（numpy 整數 ⇒ int；bytes ⇒ str；numpy bool 保持 bool 以便拒收）。"""
    try:
        import numpy as np
    except ImportError:  # pragma: no cover - numpy 為必要依賴
        return value
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("utf-8", errors="replace")
    return value


def assert_h5_feature_naming_version(attrs: object, path: object = "") -> int:
    """IC 交接 h5（SPEC v18 Task 3.4）之命名世代閘：根屬性 `feature_naming_version` 須存在、為整數且等於
    `CURRENT_FEATURE_NAMING_VERSION`；缺屬性、舊版／未知版、無法解析 ⇒ `FeatureNamingVersionError`（訊息含鍵名與
    重生指引）。讀取端須於產生任何 DataFrame 前呼叫（`attrs`＝`h5py.File(...).attrs` 或等價對映）。"""
    try:
        present = FEATURE_NAMING_VERSION_KEY in attrs  # type: ignore[operator]
    except TypeError:
        present = False
    probe = {FEATURE_NAMING_VERSION_KEY: _normalize_h5_attr(attrs[FEATURE_NAMING_VERSION_KEY])} if present else {}  # type: ignore[index]
    return assert_feature_naming_version(probe, where=f"IC 交接 h5 {path}" if path else "IC 交接 h5")


def stamp_h5_feature_naming_version(attrs: object, version: int = CURRENT_FEATURE_NAMING_VERSION) -> None:
    """IC 交接 h5 寫出端：於根屬性寫 `feature_naming_version`（＝寫入時資料之世代；資料來自已過世代閘之
    FeatureLibrary ⇒ 預設現行版）。"""
    attrs[FEATURE_NAMING_VERSION_KEY] = int(version)  # type: ignore[index]


def assert_single_feature_naming_version(manifests: "dict[str, object]") -> int:
    """多標的合併點：各 manifest 之 `feature_naming_version` 須一致且皆通過 `assert_feature_naming_version`；
    混世代 ⇒ `FeatureNamingVersionError`（訊息列各標的之版本值）。`manifests` 以標的（或 run 鍵）為鍵。"""
    if not manifests:
        raise FeatureNamingVersionError(f"多標的合併點未取得任何 manifest，無法驗 {FEATURE_NAMING_VERSION_KEY}")
    versions = {str(key): _manifest_naming_version(m) for key, m in manifests.items()}
    distinct = {repr(v) for v in versions.values()}
    if len(distinct) > 1:
        detail = "、".join(f"{k}={v!r}" for k, v in sorted(versions.items()))
        raise FeatureNamingVersionError(
            f"多標的合併之 {FEATURE_NAMING_VERSION_KEY} 不一致（{detail}）；不得混合命名世代。{_REGENERATION_HINT}")
    result = CURRENT_FEATURE_NAMING_VERSION
    for key, manifest in manifests.items():
        result = assert_feature_naming_version(manifest, where=str(key))
    return result


def is_ratio_unsafe_column(column: str) -> bool:
    """＝ `ratio_unsafe_category(column) is not None`。"""
    return ratio_unsafe_category(column) is not None
