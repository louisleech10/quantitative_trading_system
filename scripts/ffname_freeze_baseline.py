#!/usr/bin/env python3
"""FF-NAME 改前凍結腳本（docs/FFNAME_SPEC.md §G、Task 0.1）。

用法：
  venv/bin/python scripts/ffname_freeze_baseline.py            # 於改前 HEAD 碼態凍結（寫 baseline.json 與 baseline.sha256）
  venv/bin/python scripts/ffname_freeze_baseline.py --check    # 驗 baseline.json 封閉涵蓋

職責（SPEC §G）：
- 以真實 `data_cache/feature_klines/kline_cache.h5` 跑 reference 設定（全部產生端；多週期 ["1h","12h"]；
  CGSA 序列 `FFACT_MULTI_TF_PARALLEL=0`；L5 另以三標的小窗 run）；寫入一律經
  `tests.feature_engineering.fftfmeta_golden_helpers.prepare_env`（經 `ffstat_helpers.prepare_stat_env`，另把 d* 快取導向 tmp）
  之隔離（不寫正式 data_cache）。
- 於事實盤點 A1–A12 每個組名點包裝（monkeypatch，不改生產碼檔案），記錄組名零件 `NamingPart`；manifest 任一欄無零件紀錄
  ⇒ 凍結失敗（封閉涵蓋）；同名欄出自兩個組名點 ⇒ 凍結失敗並列出。
- 逐欄（舊名為鍵）記 dtype、shape、NaN mask sha256、值 sha256（值經 `FeatureReader` 讀回）；另記 L2 配對簽名集合、
  L4 lag 輸入集合、欄序、group 結構、平穩化決策（鍵與值）。
- 另記 Task 4.3 範圍 golden（`tests/_golden/ffname/contract.json` 之 `refreeze.baseline_goldens`）之改前逐欄值雜湊
  （`golden_values`：golden 路徑 → {舊欄名 → 值雜湊前 `refreeze.golden_value_hash_len` 碼}）；檔內無逐欄紀錄而登記於
  `refreeze.no_column_records` 者改記檔案 sha256（`golden_file_sha256`）；未登記而無逐欄紀錄 ⇒ `--check` 失敗。
  SPEC v21：Task 4.3 之判定改依契約 `refreeze.dispositions`（K0–K3，工具 `scripts/ffname_refreeze.py`）；
  本段只為不可變基準之完整性（`--check` 以 baseline `frozen_at_head` 之該檔比對 `golden_file_sha256`）。
- 舊名→新名映射由零件以新 formatter 推導（`derive_new_name`）；禁字串清單與全欄 replace。

零件之約定（SPEC v15）：
- `source`／`category`／`indicator` 記產生端實際使用之詞（未正規化，如 `taker_ratio`、`close_volume`、`BBANDS_Lower`）；
  `derive_new_name` 一律經 `canonical_segment` 轉為 canonical。source 不得為 None（Task 0.1 邊界②）：microstructure／
  entropy／tail-risk 之 source 取自該欄 L1 輸出點契約（`l1op.point`）之輸入元組依序 canonical 後以 `-` 串接（輸入元組列有
  而資料缺之鍵如 `trades` 照列）；自製 volatility／volume／pattern 沿用來源標籤 `hlc`／`hlcv`／`ohlc`。indicator 取
  倍數表條目名去引擎前綴之小寫詞（`MS_AMIHUD_ILLIQ`→`amihud_illiq`）。L5／L6 之 indicator 已為 kebab 詞。
- `params` 同 `FeatureIdentity.params`（外層為配對成員；空 tuple 表無參數）；`ops` 為新文法之 op 段字面（`Momentum-L5`、
  `Kurt-W5`、`Lag-1`、`TsCorr-<digest8>-W5`、`zscore-21`、`BinarySignal-Strong-Trend` 等）；`kind` 由身分機械導出。
- raw lag 輸入以 `(tf, "raw", 資料鍵)` 記錄（Task 0.1 邊界③）。
- 生成期間以未標記名記錄（`tf=None`）；落盤時以週期標記組名點（A11 `feature_naming.tag_timeframe`）之實際呼叫把零件改鍵為
  標記後之舊名並填 `tf`。

本檔不得改生產碼。
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BASELINE_PATH = REPO / "tests" / "_golden" / "ffname" / "baseline.json"
# 審查 r13 P1-05：baseline 不可變之錨——Task 0.1 產出 baseline.json 時一併寫其 sha256（單行 hex），Phase 2 起不得再改
BASELINE_SHA_PATH = REPO / "tests" / "_golden" / "ffname" / "baseline.sha256"
RECEIPT_PATH = REPO / "handoffs" / "run_receipts" / "ffname-value-invariance.json"
CONTRACT_PATH = REPO / "tests" / "_golden" / "ffname" / "contract.json"

BASELINE_SCHEMA = "ffname-baseline-v2"
# 凍結時重跑 reference 之次數（決定性：各次之 baseline 位元組須相同）；只供本機除錯縮短，正式凍結維持 2
FREEZE_RUNS_ENV = "FFNAME_FREEZE_RUNS"

# 組名點代號（事實盤點 recon_facts_20261018.md §A）
POINT_A1 = "A1:talib_wrapper._to_dataframe"
POINT_A4_PAIR = "A4:derived_operators.pair"
POINT_A4_DISTANCE = "A4:derived_operators.distance"
POINT_A4_MOMENTUM = "A4:derived_operators.momentum"
POINT_A4_BINARY = "A4:derived_operators.binary_signal"
POINT_A4_SIGNED = "A4:derived_operators.signed_strength"
POINT_A4_WQ = "A4:derived_operators.worldquant"
POINT_A5 = "A5:rolling_aggregator"
POINT_A6 = "A6:lag_processor"
POINT_A6_RAW = "A6:lag_processor.raw"
POINT_A7 = "A7:feature_factory._layer5_cross_sectional"
POINT_A8 = "A8:feature_factory._layer6_meta_features"
POINT_A10 = "A10:feature_preprocessor.append"
POINT_A10_POST = "A10:feature_preprocessor.transform_selected"

_ADV_PREFIX = {"microstructure": "ms", "entropy": "ent", "tail_risk": "tr"}
_CUSTOM_PARAM_RE = re.compile(r"^(?:W\d+|-?\d+(?:\.\d+)?)$")
_ADV_PARAM_RE = re.compile(r"^\d+(?:\.\d+)?(?:pct)?$")
_MOMENTUM_RE = re.compile(r"^(?P<base>.+)_Momentum_L(?P<lag>\d+)$")
_WQ_WINDOW_RE = re.compile(r"^(?P<base>.+)_(?P<op>TsArgmax|TsArgmin|TsRank|DecayLinear)_W(?P<w>\d+)$")
_WQ_CORR_RE = re.compile(r"^(?P<base>.+)_TsCorr_(?P<cw>.+)_W(?P<w>\d+)$")
_WQ_TRANSFORM_RE = re.compile(r"^(?P<base>.+)_(?P<op>Sign|Log1p|Abs|Clip)$")
_L3_RE = re.compile(r"^(?P<base>.+)_(?P<agg>Slope|Std|Mean|Rank|ZScore|Skew|Kurt|Min|Max|Range)_W(?P<w>\d+)$")
_LAG_RE = re.compile(r"^(?P<base>.+)_Lag_(?P<k>\d+)$")
_L65_RES: Tuple[Tuple[re.Pattern, Any], ...] = (
    (re.compile(r"^(?P<base>.+)_(?P<op>fracdiff|rank|gaussian)$"), lambda m: m["op"]),
    (re.compile(r"^(?P<base>.+)_diff(?P<k>\d+)$"), lambda m: f"diff-{m['k']}"),
    (re.compile(r"^(?P<base>.+)_zscore_(?P<w>\d+)$"), lambda m: f"zscore-{m['w']}"),
)


class FreezeError(RuntimeError):
    """凍結失敗（同名欄出自兩個組名點、manifest 欄缺零件紀錄等）；訊息須列出涉及之欄名與組名點。"""


@dataclass(frozen=True)
class NamingPart:
    """單一欄之組名零件（SPEC §G）：`(舊名, kind, source, raw_lookup_key, category, indicator, params, ops, tf)` 與組名點。

    `source` 依 SPEC v15 Task 0.1 邊界②取自組名點之實際輸入（microstructure／entropy／tail-risk 為輸出點輸入元組
    canonical 以 `-` 連接；自製 volatility／volume／pattern 沿用來源標籤），**不得為 None**——收集器本身不擋（單元測試
    以假零件驗重複判定），`--check` 對 baseline 內任一 source 為 None 之零件判失敗。`raw_lookup_key` 只在單一 raw 鍵時有值。
    """

    old_name: str
    kind: str
    source: Optional[str]
    raw_lookup_key: Optional[str]
    category: Optional[str]
    indicator: Optional[str]
    params: Tuple[Tuple[str, ...], ...]  # 同 FeatureIdentity（SPEC v13）：外層為配對成員，空 tuple 表無參數
    ops: Tuple[str, ...]
    tf: Optional[str]
    point: str


class PartRecorder:
    """組名零件之收集器（Task 0.1 邊界①②）。"""

    def __init__(self) -> None:
        self._parts: Dict[str, NamingPart] = {}

    def record(self, part: NamingPart) -> None:
        """記錄一筆零件；同一 `old_name` 已由**另一個**組名點記錄 ⇒ `FreezeError`（訊息列出欄名與兩個組名點）。

        同一組名點重複記錄同一欄（多週期迴圈、校準域重算）而零件相同 ⇒ 不重複；同一組名點對同一欄給出不同零件
        （兩個身分撞同一舊名）⇒ 亦為 `FreezeError`。"""
        previous = self._parts.get(part.old_name)
        if previous is None:
            self._parts[part.old_name] = part
            return
        if previous.point != part.point:
            raise FreezeError(
                f"同名欄出自兩個組名點：{part.old_name!r} ← {previous.point} 與 {part.point}"
            )
        if previous != part:
            raise FreezeError(
                f"同一組名點 {part.point} 對同名欄 {part.old_name!r} 給出不同零件：{previous} 與 {part}"
            )

    def get(self, old_name: str) -> Optional[NamingPart]:
        return self._parts.get(old_name)

    def parts(self) -> Dict[str, NamingPart]:
        """舊名 → 零件。"""
        return dict(self._parts)

    def to_json(self) -> List[Dict[str, Any]]:
        """可序列化形式（None 保留為 JSON null）；依舊名排序。"""
        return [_part_to_row(self._parts[name]) for name in sorted(self._parts)]


def _part_to_row(part: NamingPart) -> Dict[str, Any]:
    row = dataclasses.asdict(part)
    row["params"] = [list(member) for member in part.params]
    row["ops"] = list(part.ops)
    return row


def _part_from_row(row: Mapping[str, Any]) -> NamingPart:
    return NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                         "ops": tuple(row.get("ops") or ())})


# ---------------------------------------------------------------- 身分推導（新 formatter）


def _naming():
    import momentum.FeatureEngineering.feature_naming as fn

    return fn


def _identity(part: NamingPart, timeframe: Optional[str]):
    fn = _naming()
    if part.source is None or part.category is None or part.indicator is None:
        raise FreezeError(f"零件缺 source／category／indicator，無法推導新名：{part}")
    return fn.FeatureIdentity(
        source=fn.canonical_segment(part.source),
        tf=timeframe,
        category=fn.canonical_segment(part.category),
        indicator=fn.canonical_segment(part.indicator),
        params=tuple(tuple(str(t) for t in member) for member in part.params),
        ops=tuple(part.ops),
    )


def _kind_of(source: Optional[str], category: Optional[str], indicator: Optional[str],
             params: Tuple[Tuple[str, ...], ...], ops: Tuple[str, ...]) -> str:
    fn = _naming()
    ident = fn.FeatureIdentity(source=fn.canonical_segment(source or "x"), tf=None,
                               category=fn.canonical_segment(category or ""),
                               indicator=fn.canonical_segment(indicator or "x"), params=params, ops=ops)
    return ident.kind


def derive_new_name(part: NamingPart, timeframe: str) -> str:
    """由零件以新 formatter（`feature_naming.format_feature_name`）推導新名；禁字串 replace。
    `timeframe is None` ⇒ 未標記形（生成期間之欄名）。"""
    fn = _naming()
    try:
        return fn.format_feature_name(_identity(part, timeframe))
    except fn.FeatureNameParseError as exc:
        raise FreezeError(f"零件推導之新名不合文法：{part.old_name!r}（{part.point}）：{exc}") from exc


def derive_mapping(parts: Mapping[str, NamingPart], timeframe_of: Mapping[str, str]) -> Dict[str, str]:
    """舊名（含週期標記）→ 新名之映射；兩個舊名推導出同一新名 ⇒ `FreezeError`（列出撞名者）。"""
    mapping: Dict[str, str] = {}
    owners: Dict[str, str] = {}
    collisions: List[str] = []
    for old in sorted(parts):
        part = parts[old]
        new = derive_new_name(part, timeframe_of.get(old, part.tf))
        if new in owners:
            collisions.append(f"{owners[new]!r} 與 {old!r} → {new!r}")
        owners[new] = old
        mapping[old] = new
    if collisions:
        raise FreezeError(f"映射非單射（{len(collisions)} 筆）：{collisions[:20]}")
    return mapping


def missing_parts(manifest_columns: Iterable[str], parts: Mapping[str, NamingPart]) -> List[str]:
    """manifest 中無零件紀錄之欄（封閉涵蓋；非空 ⇒ 凍結失敗）；依出現序、不重複。"""
    out: List[str] = []
    seen: Set[str] = set()
    for column in manifest_columns:
        name = str(column)
        if name in seen:
            continue
        seen.add(name)
        if name not in parts:
            out.append(name)
    return out


def tscorr_target_digest(corr_with: str) -> str:
    """TsCorr op 內嵌之目標身分摘要（SPEC Task 2.3）：目標 raw 欄之未標記形身分
    `<canonical raw>_raw_value` 經 `format_feature_name` 之 sha256 前 8 碼。"""
    fn = _naming()
    target = fn.format_feature_name(fn.FeatureIdentity(source=fn.canonical_segment(corr_with), tf=None,
                                                       category="raw", indicator="value"))
    return hashlib.sha256(target.encode("utf-8")).hexdigest()[:8]


def _kebab_words(text: str) -> str:
    """`Trend_Consensus`→`trend-consensus`、`Time_DayOfWeek`→`time-day-of-week`（L6 meta 指標詞）。"""
    words: List[str] = []
    for token in str(text).split("_"):
        words.extend(re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", token).lower().split("-"))
    return "-".join(w for w in words if w)


def _fmt_param_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ---------------------------------------------------------------- 組名點包裝（A1–A12）


class _Instrument:
    """把 recon A1–A12 各組名點以 monkeypatch 包裝；生成期間以未標記名記錄零件。"""

    def __init__(self) -> None:
        self.rec = PartRecorder()
        self.tag_calls: Dict[Tuple[str, str], str] = {}  # (tf, 未標記名) → 標記名（A11 feature_naming.tag_timeframe）
        # (tf, 名) → 標記名（A11 改前之第二套標記實作；FF-NAME Task 2.5 已刪除，改後碼態恆為空）
        self.tag2_calls: Dict[Tuple[str, str], str] = {}
        self.pairs: Dict[str, Tuple[str, str, str]] = {}  # L2 配對欄（未標記）→ (fast, slow, op)
        self.lags: Dict[str, str] = {}  # L4 lag 欄（未標記）→ 輸入欄（未標記）
        self.saved_groups: Dict[int, Dict[str, Tuple[str, str, Tuple[str, ...]]]] = {}  # A12：registry → gid → (layer, tf, cols)
        self.raw_stack: List[Set[str]] = []
        self.post_ic: Dict[str, Tuple[str, Tuple[str, ...]]] = {}  # post-IC append 欄（標記）→ (標記基底欄, ops)
        self.anomalies: List[str] = []

    # ---- 共用

    def _base(self, name: str, point: str) -> NamingPart:
        part = self.rec.get(name)
        if part is None:
            raise FreezeError(f"{point}：輸入欄 {name!r} 無零件紀錄（上游組名點未涵蓋）")
        return part

    def _derived(self, base_name: str, column: str, ops: Sequence[str], point: str) -> None:
        base = self._base(base_name, point)
        new_ops = tuple(base.ops) + tuple(ops)
        self.rec.record(NamingPart(
            old_name=column, kind=_kind_of(base.source, base.category, base.indicator, base.params, new_ops),
            source=base.source, raw_lookup_key=base.raw_lookup_key, category=base.category,
            indicator=base.indicator, params=base.params, ops=new_ops, tf=None, point=point,
        ))

    def _simple(self, column: str, source: Optional[str], raw: Optional[str], category: str, indicator: str,
                params: Tuple[Tuple[str, ...], ...], point: str, ops: Tuple[str, ...] = ()) -> None:
        self.rec.record(NamingPart(
            old_name=column, kind=_kind_of(source, category, indicator, params, ops), source=source,
            raw_lookup_key=raw, category=category, indicator=indicator, params=params, ops=ops, tf=None, point=point,
        ))

    # ---- A1：TA-Lib 共用格式器

    def record_talib(self, cls: Any, frame: Any, source_label: str, spec: Any, params: Dict) -> None:
        param_str = cls._format_params(spec.name, params)
        tokens = tuple(param_str.split(cls.PARAM_VALUE_DELIMITER)) if param_str else ()
        for idx, column in enumerate(frame.columns):
            name_suffix = spec.output_names[idx] if len(spec.output_names) > idx else str(idx)
            if len(spec.output_names) == 1:
                indicator = spec.name
            else:
                indicator = spec.name if name_suffix == spec.name else f"{spec.name}_{name_suffix}"
            expected = "_".join([cls.normalize_source_label(source_label), spec.category,
                                 cls.normalize_indicator_name(indicator)] + ([param_str] if param_str else []))
            if expected != str(column):
                raise FreezeError(f"{POINT_A1}：零件重組 {expected!r} != 實際欄名 {column!r}")
            raw = source_label if spec.input_type == "single" else None
            self._simple(str(column), source_label, raw, spec.category, indicator, (tokens,) if tokens else (), POINT_A1)

    # ---- A3：自製 atomic（volatility／volume／pattern）

    def record_custom(self, column: str, engine: str, point_params: Mapping[str, Any], data_columns: Iterable[str],
                      point: str) -> None:
        tokens = column.split("_")
        if len(tokens) < 3 or tokens[1] != engine:
            raise FreezeError(f"{point}：欄名 {column!r} 不合 `<source>_{engine}_<indicator>[_<params>]` 寫死格式")
        source, rest = tokens[0], tokens[2:]
        cut = 0
        while cut < len(rest) and not _CUSTOM_PARAM_RE.fullmatch(rest[cut]):
            cut += 1
        indicator_tokens, param_tokens = rest[:cut], rest[cut:]
        if not indicator_tokens or any(not _CUSTOM_PARAM_RE.fullmatch(t) for t in param_tokens):
            raise FreezeError(f"{point}：欄名 {column!r} 之指標／參數段無法分解")
        values = tuple(t[1:] if t.startswith("W") else t for t in param_tokens)
        if not values and point_params:
            # 欄名未帶參數而輸出點契約有參數（ForceIndex timeperiod；SPEC Task 2.2「補參數」）⇒ 取輸出點參數
            values = tuple(_fmt_param_value(v) for v in point_params.values())
        raw = source if source in set(map(str, data_columns)) else None
        self._simple(column, source, raw, engine, "_".join(indicator_tokens), (values,) if values else (), point)

    # ---- A3：進階 atomic（microstructure／entropy／tail_risk）

    def record_advanced(self, column: str, engine: str, spec: Mapping[str, Any]) -> None:
        fn = _naming()
        table = str(spec["indicator"])
        point = f"A3:{engine}.{table}"
        indicator = table.split("_", 1)[1].lower() if "_" in table else table.lower()
        head = f"{_ADV_PREFIX[engine]}_{indicator}"
        if not (column == head or column.startswith(head + "_")):
            raise FreezeError(f"{point}：欄名 {column!r} 不以 {head!r} 起首")
        rest = column[len(head):].lstrip("_")
        rest_tokens = rest.split("_") if rest else []
        cut = len(rest_tokens)
        while cut > 0 and _ADV_PARAM_RE.fullmatch(rest_tokens[cut - 1]):
            cut -= 1
        label_tokens, param_tokens = rest_tokens[:cut], rest_tokens[cut:]
        if label_tokens and table != "ENT_SHANNON":
            raise FreezeError(f"{point}：欄名 {column!r} 含非參數段 {label_tokens}")
        inputs = tuple(str(k) for k in spec["inputs"])
        if not inputs:
            raise FreezeError(f"{point}：輸出點契約無輸入元組：{column!r}")
        source = "-".join(fn.canonical_segment(k) for k in inputs)
        raw = inputs[0] if len(inputs) == 1 else None
        params = (tuple(param_tokens),) if param_tokens else ()
        self._simple(column, source, raw, engine, indicator, params, point)

    # ---- A4：L2

    def record_pairs(self, specs: Sequence[Tuple[str, str, str]], operator_name: str) -> None:
        fn = _naming()
        for fast_name, slow_name, column in specs:
            fast = self._base(fast_name, POINT_A4_PAIR)
            slow = self._base(slow_name, POINT_A4_PAIR)
            if len(fast.params) != 1 or len(slow.params) != 1:
                raise FreezeError(f"{POINT_A4_PAIR}：配對成員須恰一組參數：{fast_name!r}／{slow_name!r}")
            key_f = tuple(fn.canonical_segment(x) for x in (fast.source, fast.category, fast.indicator))
            key_s = tuple(fn.canonical_segment(x) for x in (slow.source, slow.category, slow.indicator))
            if key_f != key_s:
                self.anomalies.append(f"L2 配對兩員 canonical 基底不同：{column} ← {fast_name} / {slow_name}")
            params = (fast.params[0], slow.params[0])
            ops = (operator_name,)
            self.rec.record(NamingPart(
                old_name=column, kind=_kind_of(fast.source, fast.category, fast.indicator, params, ops),
                source=fast.source, raw_lookup_key=fast.raw_lookup_key, category=fast.category,
                indicator=fast.indicator, params=params, ops=ops, tf=None, point=POINT_A4_PAIR,
            ))
            signature = (fast_name, slow_name, operator_name)
            if self.pairs.get(column, signature) != signature:
                raise FreezeError(f"{POINT_A4_PAIR}：配對欄 {column!r} 出自兩組配對 {self.pairs[column]} 與 {signature}")
            self.pairs[column] = signature

    def record_suffix(self, columns: Iterable[str], inputs: Set[str], regex: re.Pattern, to_op: Any,
                      point: str) -> None:
        for column in map(str, columns):
            match = regex.fullmatch(column)
            if match is None or match["base"] not in inputs:
                raise FreezeError(f"{point}：輸出欄 {column!r} 不是「輸入欄＋本組名點後綴」")
            self._derived(match["base"], column, (to_op(match),), point)

    def record_binary(self, columns: Iterable[str], inputs: Set[str], suffixes: Sequence[str]) -> None:
        fn = _naming()
        for column in map(str, columns):
            idx = column.rfind("_BinarySignal")
            base, rest = column[:idx], column[idx + len("_BinarySignal"):]
            if idx <= 0 or base not in inputs:
                raise FreezeError(f"{POINT_A4_BINARY}：輸出欄 {column!r} 無對應輸入欄")
            if rest == "":
                op = "BinarySignal"
            elif rest.startswith("_") and rest[1:] in suffixes:
                op = f"BinarySignal-{fn.canonical_segment(rest[1:])}"
            else:
                raise FreezeError(f"{POINT_A4_BINARY}：輸出欄 {column!r} 之後綴 {rest!r} 不屬規則 name_suffix")
            self._derived(base, column, (op,), POINT_A4_BINARY)

    def record_worldquant(self, columns: Iterable[str], inputs: Set[str], corr_with: Optional[str]) -> None:
        for column in map(str, columns):
            match = _WQ_WINDOW_RE.fullmatch(column)
            if match is not None and match["base"] in inputs:
                self._derived(match["base"], column, (f"{match['op']}-W{match['w']}",), POINT_A4_WQ)
                continue
            match = _WQ_CORR_RE.fullmatch(column)
            if match is not None and match["base"] in inputs and corr_with is not None and match["cw"] == str(corr_with):
                op = f"TsCorr-{tscorr_target_digest(str(corr_with))}-W{match['w']}"
                self._derived(match["base"], column, (op,), POINT_A4_WQ)
                continue
            match = _WQ_TRANSFORM_RE.fullmatch(column)
            if match is not None and match["base"] in inputs:
                self._derived(match["base"], column, (match["op"],), POINT_A4_WQ)
                continue
            raise FreezeError(f"{POINT_A4_WQ}：輸出欄 {column!r} 無法分解為輸入欄＋WorldQuant 後綴")

    # ---- A6：L4

    def record_lags(self, columns: Iterable[str], inputs: Set[str]) -> None:
        raw_columns = self.raw_stack[-1] if self.raw_stack else set()
        for column in map(str, columns):
            match = _LAG_RE.fullmatch(column)
            if match is None or match["base"] not in inputs:
                raise FreezeError(f"{POINT_A6}：輸出欄 {column!r} 不是「輸入欄＋_Lag_k」")
            base, op = match["base"], f"Lag-{match['k']}"
            if self.rec.get(base) is not None:
                self._derived(base, column, (op,), POINT_A6)
            elif base in raw_columns:
                self._simple(column, base, base, "raw", "value", (), POINT_A6_RAW, ops=(op,))
            else:
                raise FreezeError(f"{POINT_A6}：lag 輸入 {base!r} 既無零件亦非 raw 欄")
            if self.lags.get(column, base) != base:
                raise FreezeError(f"{POINT_A6}：lag 欄 {column!r} 出自兩個輸入 {self.lags[column]!r}／{base!r}")
            self.lags[column] = base

    # ---- A10：L6.5 append 後綴

    @staticmethod
    def _strip_l65(column: str, base_columns: Set[str]) -> Tuple[str, List[str]]:
        current, ops = column, []
        while current not in base_columns:
            for regex, to_op in _L65_RES:
                match = regex.fullmatch(current)
                if match is not None:
                    ops.insert(0, to_op(match))
                    current = match["base"]
                    break
            else:
                raise FreezeError(f"{POINT_A10}：L6.5 輸出欄 {column!r} 無法剝成輸入欄＋L6.5 後綴")
        if not ops:
            raise FreezeError(f"{POINT_A10}：L6.5 輸出欄 {column!r} 無後綴卻不在輸入")
        return current, ops

    def record_l65_tagged(self, column: str, inputs: Set[str]) -> None:
        """post-IC 之 append 欄（名已標記）：記（標記基底欄, ops），零件於標記後零件建好後再推導。"""
        base, ops = self._strip_l65(column, inputs)
        signature = (base, tuple(ops))
        if self.post_ic.get(column, signature) != signature:
            raise FreezeError(f"{POINT_A10_POST}：post-IC 欄 {column!r} 出自兩個基底")
        self.post_ic[column] = signature

    def record_l65(self, column: str, base_columns: Set[str]) -> None:
        current, ops = self._strip_l65(column, base_columns)
        self._derived(current, column, tuple(ops), POINT_A10)

    # ---- 安裝

    def install(self, mp: Any) -> None:  # noqa: C901 — 逐組名點包裝
        from momentum.FeatureEngineering import feature_naming
        from momentum.FeatureEngineering.atomic import l1_output_points as l1op
        from momentum.FeatureEngineering.atomic.pattern_indicators import PatternIndicatorEngine
        from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
        from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
        from momentum.FeatureEngineering.operators.lag_processor import LagProcessor
        from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

        inst = self

        # A1
        orig_to_df = TALibWrapper.__dict__["_to_dataframe"].__func__

        def _to_dataframe(cls, output, index, source_label, spec, params, mask_inputs=None):
            frame = orig_to_df(cls, output, index, source_label, spec, params, mask_inputs=mask_inputs)
            inst.record_talib(cls, frame, source_label, spec, params)
            return frame

        mp.setattr(TALibWrapper, "_to_dataframe", classmethod(_to_dataframe))

        # A3（volatility／volume 自製欄之輸出點）
        orig_mask_frame = l1op.mask_frame

        def mask_frame(frame, engine, indicator, params, data, input_columns):
            out = orig_mask_frame(frame, engine, indicator, params, data, input_columns)
            if frame is not None and not frame.empty:
                for column in frame.columns:
                    inst.record_custom(str(column), str(engine), params or {}, data.columns, f"A3:{engine}.{indicator}")
            return out

        mp.setattr(l1op, "mask_frame", mask_frame)

        # A3（pattern 同引擎衍生：BullishCount／BearishCount／Consensus）
        orig_mask_derived = PatternIndicatorEngine.__dict__["_mask_derived"].__func__

        def _mask_derived(data, pattern_df, freq_df, consensus_df):
            out = orig_mask_derived(data, pattern_df, freq_df, consensus_df)
            for column in list(freq_df.columns) + list(consensus_df.columns):
                inst.record_custom(str(column), "pattern", {}, data.columns, "A3:pattern._mask_derived")
            return out

        mp.setattr(PatternIndicatorEngine, "_mask_derived", staticmethod(_mask_derived))

        # A3（microstructure／entropy／tail_risk 之輸出點契約）
        orig_mask_engine_frame = l1op.mask_engine_frame

        def mask_engine_frame(engine, frame, points, data):
            out = orig_mask_engine_frame(engine, frame, points, data)
            if frame is not None and not frame.empty:
                for column in frame.columns:
                    inst.record_advanced(str(column), str(engine), points[column])
            return out

        mp.setattr(l1op, "mask_engine_frame", mask_engine_frame)

        # A4（CGSA 落盤之 L2 由 compute_category → 各 _apply_* 產生）
        orig_pair = DerivedOperatorEngine._apply_pair_operator

        def _apply_pair_operator(self, layer1_df, feature_info, operator_name):
            out = orig_pair(self, layer1_df, feature_info, operator_name)
            specs = self._collect_pair_specs(layer1_df, feature_info, operator_name)
            if sorted(map(str, out.columns)) != sorted(s[2] for s in specs):
                raise FreezeError(f"{POINT_A4_PAIR}：{operator_name} 輸出欄與配對規格不一致")
            inst.record_pairs(specs, operator_name)
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_pair_operator", _apply_pair_operator)

        orig_distance = DerivedOperatorEngine._apply_distance

        def _apply_distance(self, layer1_df, raw_data, feature_info, config):
            out = orig_distance(self, layer1_df, raw_data, feature_info, config)
            inst.record_suffix(out.columns, set(map(str, layer1_df.columns)), re.compile(r"^(?P<base>.+)_Distance$"),
                               lambda m: "Distance", POINT_A4_DISTANCE)
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_distance", _apply_distance)

        orig_momentum = DerivedOperatorEngine._apply_momentum

        def _apply_momentum(self, layer1_df, feature_info, config):
            out = orig_momentum(self, layer1_df, feature_info, config)
            inst.record_suffix(out.columns, set(map(str, layer1_df.columns)), _MOMENTUM_RE,
                               lambda m: f"Momentum-L{m['lag']}", POINT_A4_MOMENTUM)
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_momentum", _apply_momentum)

        orig_binary = DerivedOperatorEngine._apply_binary_signal

        def _apply_binary_signal(self, layer1_df, feature_info, config):
            out = orig_binary(self, layer1_df, feature_info, config)
            suffixes = [str(r.get("name_suffix")) for r in config.get("rules", []) if r.get("name_suffix")]
            inst.record_binary(out.columns, set(map(str, layer1_df.columns)), suffixes)
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_binary_signal", _apply_binary_signal)

        orig_signed = DerivedOperatorEngine._apply_signed_strength

        def _apply_signed_strength(self, layer1_df, feature_info, config):
            out = orig_signed(self, layer1_df, feature_info, config)
            inst.record_suffix(out.columns, set(map(str, layer1_df.columns)),
                               re.compile(r"^(?P<base>.+)_SignedStrength$"), lambda m: "SignedStrength", POINT_A4_SIGNED)
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_signed_strength", _apply_signed_strength)

        orig_wq = DerivedOperatorEngine._apply_worldquant

        def _apply_worldquant(self, layer1_df, raw_data, feature_info, config):
            out = orig_wq(self, layer1_df, raw_data, feature_info, config)
            inst.record_worldquant(out.columns, set(map(str, layer1_df.columns)), config.get("corr_with"))
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_worldquant", _apply_worldquant)

        # A5（L3：回傳表與串流 callback 兩出口）
        orig_l3 = RollingAggregator.compute_all

        def compute_all_l3(self, features_df, persist_callback=None):
            inputs = set(map(str, features_df.columns))
            callback = persist_callback
            if persist_callback is not None:
                def callback(step_label, chunk_frame, _cb=persist_callback):
                    if chunk_frame is not None and not chunk_frame.empty:
                        inst.record_suffix(chunk_frame.columns, inputs, _L3_RE,
                                           lambda m: f"{m['agg']}-W{m['w']}", POINT_A5)
                    return _cb(step_label, chunk_frame)
            out = orig_l3(self, features_df, persist_callback=callback)
            if out is not None and not out.empty:
                inst.record_suffix(out.columns, inputs, _L3_RE, lambda m: f"{m['agg']}-W{m['w']}", POINT_A5)
            return out

        mp.setattr(RollingAggregator, "compute_all", compute_all_l3)

        # A6（L4：raw 欄集合取自 _layer4_lag_features 之 data）
        orig_l4_layer = FeatureFactory._layer4_lag_features

        def _layer4_lag_features(self, layer1, layer2, layer3, data, config):
            inst.raw_stack.append(set(map(str, data.columns)))
            try:
                return orig_l4_layer(self, layer1, layer2, layer3, data, config)
            finally:
                inst.raw_stack.pop()

        mp.setattr(FeatureFactory, "_layer4_lag_features", _layer4_lag_features)

        orig_lag = LagProcessor.compute_all

        def compute_all_l4(self, features_df):
            out = orig_lag(self, features_df)
            if out is not None and not out.empty:
                inst.record_lags(out.columns, set(map(str, features_df.columns)))
            return out

        mp.setattr(LagProcessor, "compute_all", compute_all_l4)

        # A7（L5）
        orig_l5 = FeatureFactory._layer5_cross_sectional

        def _layer5_cross_sectional(self, layer1, layer2, config):
            result = orig_l5(self, layer1, layer2, config)
            for column in map(str, FeatureFactory.layer_data(result).columns):
                if not column.startswith("cs_"):
                    raise FreezeError(f"{POINT_A7}：L5 欄 {column!r} 不以 cs_ 起首")
                inst._simple(column, "xsec", None, "cross-sectional", _kebab_words(column[3:]), (), POINT_A7)
            return result

        mp.setattr(FeatureFactory, "_layer5_cross_sectional", _layer5_cross_sectional)

        # A8（L6）
        orig_l6 = FeatureFactory._layer6_meta_features

        def _layer6_meta_features(self, layer1, layer2, data, config):
            result = orig_l6(self, layer1, layer2, data, config)
            for column in map(str, FeatureFactory.layer_data(result).columns):
                if not column.startswith("meta_"):
                    raise FreezeError(f"{POINT_A8}：L6 欄 {column!r} 不以 meta_ 起首")
                inst._simple(column, "meta", None, "meta", _kebab_words(column[5:]), (), POINT_A8)
            return result

        mp.setattr(FeatureFactory, "_layer6_meta_features", _layer6_meta_features)

        # A10（L6.5：寫入端 sink 收到之欄中不屬來源群組者＝append 後綴欄）
        orig_sink = FeaturePreprocessor.transform_registry_groups_to_sink

        def transform_registry_groups_to_sink(self, registry, sink, n_workers=1):
            source_columns = {str(gid): set(map(str, group.columns)) for gid, group in registry.iter_all()}

            def sink2(group_id, columns, data, source_group_id, source_disk_path, cleanup_source):
                base_columns = source_columns.get(str(source_group_id), set())
                for column in map(str, columns):
                    if column not in base_columns:
                        inst.record_l65(column, base_columns)
                return sink(group_id, columns, data, source_group_id, source_disk_path, cleanup_source)

            return orig_sink(self, registry, sink2, n_workers=n_workers)

        mp.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink", transform_registry_groups_to_sink)

        # A10（post-IC：transform_selected 於已標記之選欄上 append rank／gaussian／zscore 後綴）
        orig_selected = FeaturePreprocessor.transform_selected

        def transform_selected(self, selected, groups, config=None, arm=None):
            out = orig_selected(self, selected, groups, config, arm)
            inputs = {str(c) for frame in (groups or {}).values() for c in frame.columns}
            for frame in out.values():
                for column in map(str, frame.columns):
                    if column not in inputs:
                        inst.record_l65_tagged(column, inputs)
            return out

        mp.setattr(FeaturePreprocessor, "transform_selected", transform_selected)

        # A11（兩套週期標記）
        orig_tag = feature_naming.tag_timeframe

        def tag_timeframe(column, timeframe):
            out = orig_tag(column, timeframe)
            inst.tag_calls[(str(timeframe), str(column))] = out
            return out

        mp.setattr(feature_naming, "tag_timeframe", tag_timeframe)
        # 改前之第二套標記（FeatureFactory 之靜態標記函式）已於 FF-NAME Task 2.5 刪除；baseline 已於改前凍結
        # （其 tag_disagreements 為空），改後碼態不再包裝。

        # A12（CGSA 群組：group_id 與欄）
        orig_save = ColumnGroupRegistry.save_data

        def save_data(self, group, data):
            out = orig_save(self, group, data)
            layer = getattr(group.layer, "value", group.layer)
            inst.saved_groups.setdefault(id(self), {})[str(group.group_id)] = (
                str(layer), str(group.timeframe), tuple(map(str, group.columns)))
            return out

        mp.setattr(ColumnGroupRegistry, "save_data", save_data)


# ---------------------------------------------------------------- reference 設定與執行


def reference_payloads() -> Dict[str, Dict[str, Any]]:
    """§G reference 設定：`main`（全部產生端、多週期）與 `xsec`（L5 三標的小窗）。"""
    from tests.feature_engineering.fftfmeta_golden_helpers import MULTI_TFS, PRIMARY_TF

    main: Dict[str, Any] = {
        "timeframes": {"primary": PRIMARY_TF, "training": list(MULTI_TFS), "alignment_mode": "open_minus"},
        "global": {"lag_strategy": "custom", "custom_lags": [1, 3]},
        # raw 欄含 taker_ratio、quote_volume、taker_buy_volume（L4 raw lag）；avg-price 為合成欄
        "data_sources": {"enabled_sources": ["close", "volume", "taker_ratio", "quote_volume", "taker_buy_volume"],
                         "synthetic_sources": ["avg-price"]},
        "atomic_indicators": {
            "trend": {"enabled": True, "indicators": [
                {"name": "EMA", "periods": [8, 21, 34]},          # 多參數；L2 配對 8~34；meta 共識所需 EMA_8／21
                {"name": "BBANDS", "periods": [13]},              # 多輸出
                {"name": "T3", "periods": [5]},
            ]},
            "momentum": {"enabled": True, "indicators": [
                {"name": "RSI", "periods": [14]},
                {"name": "CMO", "periods": [13, 55]},             # 多來源配對（含 taker_ratio）
                {"name": "APO", "params": {"fastperiod": 12, "slowperiod": 26, "matype": 0}},  # 多參數單欄
                {"name": "MACD", "combos": [[12, 26, 9]]},       # 多輸出多參數
                {"name": "CCI", "periods": [14]},
                {"name": "STOCH"},
                {"name": "ADX", "periods": [14]},
            ]},
            "volatility": {"enabled": True, "indicators": [{"name": "ATR", "periods": [14, 55]},
                                                            {"name": "NATR", "periods": [14]}]},
            "volume": {"enabled": True, "indicators": [{"name": "OBV"}, {"name": "AD"}]},  # OBV＝close_volume 來源
            "cycle": {"enabled": True, "indicators": [{"name": "HT_DCPHASE"}, {"name": "HT_SINE"}]},
            "pattern": {"enabled": True, "indicators": [{"name": "CDLDOJI"}, {"name": "CDLENGULFING"},
                                                         {"name": "CDLHAMMER"}]},
            "statistics": {"enabled": True, "indicators": [
                {"name": "BETA", "periods": [13]},
                {"name": "Beta_CloseVolume", "periods": [13]},    # close_volume 來源
                {"name": "STDDEV", "periods": [13]},
                {"name": "LINEARREG_SLOPE", "periods": [14]},
            ]},
            "microstructure": {"enabled": True, "windows": [5, 21], "kyle_lambda_windows": [21],
                               "cs_spread_smooth": [5], "vpin_n_buckets": [30], "vpin_zscore_windows": [21]},
            "entropy": {"enabled": True, "windows": [55], "hurst_windows": [55], "perm_windows": [21],
                        "shannon_windows": [21], "apply_to": ["close_return", "volume", "taker_ratio"]},
            "tail_risk": {"enabled": True, "windows": [21], "cvar_alphas": [0.01], "rv_windows": [13],
                          "mdd_windows": [21]},
        },
        "operators": {
            "enabled": True,
            "distance": {"enabled": True, "apply_to": "all"},
            "cross": {"enabled": True},
            "ratio": {"enabled": True},
            "momentum": {"enabled": True, "lags": [5], "apply_to": "all"},
            # 含 config/scan_config.yaml 預設之多字後綴 ADX `Strong_Trend`（SPEC v15 §G；→ op `BinarySignal-Strong-Trend`）
            "binary_signal": {"enabled": True, "rules": [
                {"indicator": "RSI", "condition": "> 70", "name_suffix": "Overbought"},
                {"indicator": "RSI", "condition": "< 30", "name_suffix": "Oversold"},
                {"indicator": "ADX", "condition": "> 25", "name_suffix": "Strong_Trend"},
                {"indicator": "CCI", "condition": "> 100", "name_suffix": "Overbought"},
            ]},
            "worldquant": {"enabled": True, "apply_to": "all_trend", "windows": [5], "corr_with": "volume",
                           "operators": {name: {"enabled": True} for name in
                                         ("ts_argmax", "ts_argmin", "ts_rank", "decay_linear", "ts_corr")}},
        },
        "rolling_aggregation": {"enabled": True, "windows": [5]},  # 聚合器沿用預設全部 10 種
        "lag_features": {"enabled": True, "apply_to": "layer1_and_raw"},
        "cross_sectional": {"enabled": False},
        "meta_features": {"enabled": True},
        "preprocessing": {
            "enabled": True,
            "mode": "append",
            "causal_preprocessing": True,
            "winsorization": {"enabled": True},
            "adf_differencing": {"enabled": True, "apply_to": "non_stationary"},
            "fractional_differencing": {"enabled": True, "apply_to": "non_stationary"},
            "rank_transform": {"enabled": True},
            "gaussian_normalize": {"enabled": True},
            "adaptive_zscore": {"enabled": True, "windows": [21]},
        },
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
        "max_nan_ratio": 1.0,
    }
    xsec: Dict[str, Any] = {
        "timeframes": {"primary": PRIMARY_TF, "training": [PRIMARY_TF], "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "atomic_indicators": {c: {"enabled": c == "trend"} for c in (
            "trend", "momentum", "volatility", "volume", "statistics", "cycle", "pattern", "tail_risk",
            "microstructure", "entropy")},
        "operators": {"enabled": False},
        "rolling_aggregation": {"enabled": False},
        "lag_features": {"enabled": False},
        "meta_features": {"enabled": False},
        "preprocessing": {"enabled": False},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
        "max_nan_ratio": 1.0,
    }
    xsec["atomic_indicators"]["trend"] = {"enabled": True, "indicators": [{"name": "EMA", "periods": [8]}]}
    return {"main": main, "xsec": xsec}


def _reference_spec() -> Dict[str, Any]:
    """reference 之標的、週期與窗（不寫死標的：L5 三標的取自 kline 檔之鍵，參考標的＝既有 helper 常數）。"""
    from tests.feature_engineering.ffname_helpers import kline_symbols
    from tests.feature_engineering.fftfmeta_golden_helpers import MULTI_TFS, PRIMARY_TF, SYMBOL, WINDOW

    symbols = kline_symbols()
    reference = SYMBOL
    targets = [s for s in symbols if s != reference and not s.startswith("_")][:3]
    xsec_window = (WINDOW[0], f"{WINDOW[0][:8]}10")
    return {"symbol": SYMBOL, "primary_tf": PRIMARY_TF, "timeframes": list(MULTI_TFS), "window": list(WINDOW),
            "xsec": {"reference_symbol": reference, "symbols": targets, "window": list(xsec_window),
                     "timeframe": PRIMARY_TF}}


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _column_fingerprint(series: Any) -> Dict[str, Any]:
    import numpy as np

    arr = np.asarray(series.to_numpy())
    if arr.dtype.kind == "f":
        nan_mask = np.isnan(arr)
    else:
        nan_mask = np.asarray(series.isna().to_numpy())
    if arr.dtype.kind in "fiub":
        value_bytes = arr.astype(arr.dtype.newbyteorder("<"), copy=False).tobytes()
    else:
        value_bytes = _canonical_json(arr.tolist())
    return {
        "dtype": str(series.dtype),
        "shape": [int(arr.shape[0])],
        "nan_sha256": _sha(np.packbits(nan_mask.astype(np.uint8)).tobytes() + str(len(nan_mask)).encode()),
        "value_sha256": _sha(value_bytes),
    }


def _generate(work: Path, payload: Dict[str, Any], symbol: str, timeframe: str, window: Sequence[str]):
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR

    root = work / "features"
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    result = factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                       start_date=window[0], end_date=window[1], persist=True)
    return root, factory, result


def _generate_ic_first(work: Path, payload: Dict[str, Any], symbol: str, timeframe: str, window: Sequence[str]):
    """IC-first 正式路徑（生成 raw → IC → 選欄 → post-IC 轉換 → processed）：rank／gaussian／zscore 之 append 後綴只在
    post-IC（`transform_selected`）產生（生成之 L7 raw 只做縮尾與平穩化，`_build_l7_raw_preprocessing_config`）。
    IC 門檻 0.0（選欄＝IC 有定義之全部欄；決定性）。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR

    root = work / "features"
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    config = factory._resolve_config(payload)
    result = factory.run_ic_first(symbol, timeframe, config, start_date=window[0], end_date=window[1],
                                  ic_engine=ICEngine({"methods": ["spearman"]}), feature_reader=FeatureReader(str(root)),
                                  ic_threshold=0.0, allow_partial_ic=True)
    return root, factory, result


def _read_run(root: Path, symbol: str, timeframe: str, config_hash: str,
              artifact_kind: str = "raw") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """經 FeatureReader 讀回 manifest 與逐欄指紋（不直接開 parquet，SPEC Task 3.4 讀取共同邊界）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    reader = FeatureReader(str(root))
    manifest = reader.load_manifest_v2(symbol, timeframe, config_hash, artifact_kind=artifact_kind, allow_partial=True)
    columns: Dict[str, Any] = {}
    for _group, frame in reader.stream_groups_v2(symbol, timeframe, config_hash, artifact_kind=artifact_kind,
                                                 allow_partial=True):
        for column in frame.columns:
            if str(column) in columns:
                raise FreezeError(f"欄名於 run 內重複：{column!r}")
            columns[str(column)] = _column_fingerprint(frame[column])
    return manifest, columns


def _manifest_groups(manifest: Dict[str, Any]) -> Dict[str, List[str]]:
    from tests.feature_engineering.ffname_helpers import manifest_group_columns

    return manifest_group_columns(manifest)


def _tagged_parts(inst: _Instrument, manifest_columns_by_tf: Iterable[Tuple[str, str]]) -> Tuple[Dict[str, NamingPart], List[str]]:
    """把未標記零件依 A11 實際標記呼叫改鍵為標記後舊名；回傳（標記名 → 零件, 無零件之標記名）。"""
    inverse: Dict[str, Tuple[str, str]] = {}
    for (tf, untagged), tagged in inst.tag_calls.items():
        previous = inverse.get(tagged)
        if previous is not None and previous != (tf, untagged):
            raise FreezeError(f"標記名 {tagged!r} 出自兩個 (tf, 未標記名)：{previous} 與 {(tf, untagged)}")
        inverse[tagged] = (tf, untagged)
    out: Dict[str, NamingPart] = {}
    missing: List[str] = []
    for column, group_tf in manifest_columns_by_tf:
        key = inverse.get(column)
        part = inst.rec.get(key[1]) if key is not None else None
        if key is None or part is None:
            missing.append(column)
            continue
        if key[0] != group_tf:
            raise FreezeError(f"欄 {column!r} 之標記週期 {key[0]} 與群組週期 {group_tf} 不一致")
        out[column] = dataclasses.replace(part, old_name=column, tf=key[0])
    return out, missing


def _group_tf(group_id: str) -> str:
    return str(group_id).split("_", 1)[0]


def _collect_main(inst: _Instrument, root: Path, factory: Any, result: Any, spec: Dict[str, Any]) -> Dict[str, Any]:
    from momentum.FeatureEngineering import feature_naming

    symbol, primary = spec["symbol"], spec["primary_tf"]
    config_hash = str(result.metadata["config_hash"])
    manifest, columns = _read_run(root, symbol, primary, config_hash)
    manifest_groups = _manifest_groups(manifest)
    column_order = [c for cols in manifest_groups.values() for c in cols]
    if sorted(column_order) != sorted(columns):
        raise FreezeError("manifest 欄集合與 FeatureReader 讀回欄集合不一致")
    by_tf = [(c, _group_tf(gid)) for gid, cols in manifest_groups.items() for c in cols]
    parts, missing = _tagged_parts(inst, by_tf)
    if missing:
        raise FreezeError(f"manifest 欄無零件紀錄 {len(missing)} 欄（封閉涵蓋失敗）：{missing[:30]}")

    # processed（post-IC）成品：未標記零件已改鍵為標記名，post-IC append 欄由其標記基底之零件推導
    from tests.feature_engineering.ffname_helpers import manifest_group_columns

    processed_manifest, processed_columns = _read_run(root, symbol, primary, config_hash, "processed")
    processed_groups = manifest_group_columns(processed_manifest, "processed")
    processed_order = [c for cols in processed_groups.values() for c in cols]
    if sorted(processed_order) != sorted(processed_columns):
        raise FreezeError("processed manifest 欄集合與 FeatureReader 讀回欄集合不一致")
    processed_missing: List[str] = []
    for column in processed_order:
        if column in parts:
            continue
        signature = inst.post_ic.get(column)
        base = parts.get(signature[0]) if signature is not None else None
        if base is None:
            processed_missing.append(column)
            continue
        ops = tuple(base.ops) + tuple(signature[1])
        parts[column] = dataclasses.replace(
            base, old_name=column, ops=ops, point=POINT_A10_POST,
            kind=_kind_of(base.source, base.category, base.indicator, base.params, ops))
    if processed_missing:
        raise FreezeError(f"processed 欄無零件紀錄 {len(processed_missing)} 欄：{processed_missing[:30]}")

    registry =getattr(factory, "_cgsa_registry", None)
    saved = inst.saved_groups.get(id(registry)) if registry is not None else None
    if not saved:
        raise FreezeError("主 run 之 CGSA registry 群組未錄得（A12）")
    tag = feature_naming.tag_timeframe  # 純函式（包裝期間另記呼叫，不影響結果）

    groups = {gid: [tag(c, tf) for c in cols] for gid, (_layer, tf, cols) in saved.items()}
    l2_pairs, lag_rows = [], []
    for gid, (layer, tf, cols) in saved.items():
        for column in cols:
            if layer == "L2" and column in inst.pairs:
                fast, slow, op = inst.pairs[column]
                l2_pairs.append({"fast": tag(fast, tf), "slow": tag(slow, tf), "op": op, "column": tag(column, tf)})
            if layer == "L4" and column in inst.lags:
                base = inst.lags[column]
                lag_part = inst.rec.get(column)
                is_raw = lag_part is not None and lag_part.category == "raw"
                # raw 欄（kline 資料鍵）不經週期標記（無週期段）⇒ 以 (tf, "raw", 資料鍵) 表示；特徵輸入記標記後舊名
                lag_rows.append({"column": tag(column, tf), "tf": tf, "input_kind": "raw" if is_raw else "feature",
                                 "input": base if is_raw else tag(base, tf)})
    l2_pairs.sort(key=lambda r: (r["column"], r["fast"], r["slow"], r["op"]))
    lag_rows.sort(key=lambda r: (r["column"], r["input"]))

    decisions_raw = dict(result.metadata.get("stationarity_decisions") or {})
    decisions = json.loads(_canonical_json(decisions_raw).decode("utf-8"))
    tag_disagreements = sorted(
        {f"{tf}|{col}|{tagged}|{inst.tag_calls[(tf, col)]}" for (tf, col), tagged in inst.tag2_calls.items()
         if (tf, col) in inst.tag_calls and inst.tag_calls[(tf, col)] != tagged})
    manifest_keep = {k: manifest[k] for k in ("schema_version", "artifact_kind", "row_count", "total_features",
                                              "feature_naming_version") if k in manifest}
    return {
        "columns": columns,
        "column_order": column_order,
        "parts": parts,
        "manifest_groups": manifest_groups,
        "processed": {"columns": processed_columns, "column_order": processed_order,
                      "manifest_groups": processed_groups},
        "group_ids": sorted(groups),
        "groups": groups,
        "l2_pairs": l2_pairs,
        "l4_lags": lag_rows,
        "l4_lag_inputs": [list(t) for t in sorted({(r["tf"], r["input_kind"], r["input"]) for r in lag_rows})],
        "stationarity_keys": sorted(decisions),
        "stationarity_decisions": decisions,
        "manifest": manifest_keep,
        "tag_disagreements": tag_disagreements,
        "run": {"base": str(root), "symbol": symbol, "tf": primary, "config_hash": config_hash},
    }


def _is_l5_column(name: str) -> bool:
    """L5 cross-sectional 欄：改前 `cs_` 前綴；改後碼態以 parser 判 category（FF-NAME Task 2.4）。"""
    if str(name).startswith("cs_"):
        return True
    fn = _naming()
    try:
        return fn.parse_feature_name(str(name)).category == "cross-sectional"
    except fn.FeatureNameParseError:
        return False


class _Observer:
    """改後碼態（`record_parts=False`）之結構觀測（FF-NAME Task 2.6）：L2 配對規格、L4 lag 輸入、CGSA 群組。
    只包裝、不改產生端行為；名稱一律為改後產生端之實際欄名（不經零件推導），供 §G ⑤⑥ 與欄序／群組比對。"""

    def __init__(self) -> None:
        self.pairs: Dict[str, Tuple[str, str, str]] = {}  # L2 配對欄（未標記）→ (fast, slow, op)
        self.lags: Dict[str, Tuple[str, bool]] = {}  # L4 lag 欄（未標記）→ (輸入欄或 raw 資料鍵, 是否 raw)
        self.saved_groups: Dict[int, Dict[str, Tuple[str, str, Tuple[str, ...]]]] = {}

    def install(self, mp: Any) -> None:
        from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
        from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
        from momentum.FeatureEngineering.operators.lag_processor import LagProcessor

        obs = self
        orig_pair = DerivedOperatorEngine._apply_pair_operator

        def _apply_pair_operator(self, layer1_df, feature_info, operator_name):
            out = orig_pair(self, layer1_df, feature_info, operator_name)
            for fast, slow, column in self._collect_pair_specs(layer1_df, feature_info, operator_name):
                obs.pairs[str(column)] = (str(fast), str(slow), str(operator_name))
            return out

        mp.setattr(DerivedOperatorEngine, "_apply_pair_operator", _apply_pair_operator)

        orig_lag_name = LagProcessor._lag_name

        def _lag_name(self, col, lag):
            out = orig_lag_name(self, col, lag)
            obs.lags[str(out)] = (str(col), self._identity_or_none(col) is None)
            return out

        mp.setattr(LagProcessor, "_lag_name", _lag_name)

        orig_save = ColumnGroupRegistry.save_data

        def save_data(self, group, data):
            out = orig_save(self, group, data)
            layer = getattr(group.layer, "value", group.layer)
            obs.saved_groups.setdefault(id(self), {})[str(group.group_id)] = (
                str(layer), str(group.timeframe), tuple(map(str, group.columns)))
            return out

        mp.setattr(ColumnGroupRegistry, "save_data", save_data)

    def structure(self, factory: Any) -> Dict[str, Any]:
        """`l2_pairs`（`[fast, slow, op]`，標記後新名）與 `l4_lag_inputs`（標記後新名；raw 輸入為
        `<canonical raw>_<tf>_raw_value`）。"""
        from momentum.FeatureEngineering import feature_naming as fn

        registry = getattr(factory, "_cgsa_registry", None)
        saved = self.saved_groups.get(id(registry)) if registry is not None else None
        if not saved:
            raise FreezeError("改後 run 之 CGSA registry 群組未錄得")
        pairs: Set[Tuple[str, str, str]] = set()
        lag_inputs: Set[str] = set()
        for _gid, (layer, tf, cols) in saved.items():
            for column in cols:
                if layer == "L2" and column in self.pairs:
                    fast, slow, op = self.pairs[column]
                    pairs.add((fn.tag_timeframe(fast, tf), fn.tag_timeframe(slow, tf), op))
                if layer == "L4" and column in self.lags:
                    source, is_raw = self.lags[column]
                    lag_inputs.add(fn.format_feature_name(fn.raw_value_identity(source, tf)) if is_raw
                                   else fn.tag_timeframe(source, tf))
        return {"l2_pairs": [list(p) for p in sorted(pairs)], "l4_lag_inputs": sorted(lag_inputs)}


def run_reference(work_dir: Path, *, record_parts: bool) -> Dict[str, Any]:
    """跑 reference（真實 kline）並回傳 fingerprint：
    `columns`（名 → {dtype, shape, nan_sha256, value_sha256}）、`column_order`、`group_ids`、`groups`（group_id → 欄名清單）、
    `l2_pairs`、`l4_lag_inputs`、`stationarity_keys`、`stationarity_decisions`（決策鍵 → 決策值；SPEC v13 Task 4.2 比對基準）、
    `manifest`（含 `feature_naming_version`，改前為缺）、
    `manifest_groups`（group_id → 欄名清單）、`parts`（record_parts 時）、
    `run`（`{"base", "symbol", "tf", "config_hash"}`：主週期 run 位置，供以 FeatureReader 讀值驗 lag 位移）。

    `record_parts=False` 時不包裝組名點（改後碼態重跑，供 Task 2.6 比對值；零件由改後之 parser 還原）。"""
    import pytest

    from tests.feature_engineering.ffstat_helpers import prepare_stat_env

    work_dir = Path(work_dir)
    spec = _reference_spec()
    payloads = reference_payloads()
    inst = _Instrument()

    main_dir = work_dir / "main"
    main_dir.mkdir(parents=True, exist_ok=True)
    with pytest.MonkeyPatch.context() as mp:
        prepare_stat_env(mp, main_dir)
        observer = _Observer()
        if record_parts:
            inst.install(mp)
        else:
            observer.install(mp)
        root, factory, result = _generate_ic_first(main_dir, payloads["main"], spec["symbol"], spec["primary_tf"],
                                                   spec["window"])
        info = _collect_main(inst, root, factory, result, spec) if record_parts else None
        if not record_parts:
            config_hash = str(result.metadata["config_hash"])
            manifest, columns = _read_run(root, spec["symbol"], spec["primary_tf"], config_hash)
            _pm, processed_columns = _read_run(root, spec["symbol"], spec["primary_tf"], config_hash, "processed")
            manifest_groups = _manifest_groups(manifest)
            decisions = dict(result.metadata.get("stationarity_decisions") or {})
            info = {"columns": columns, "manifest_groups": manifest_groups,
                    "column_order": [c for cols in manifest_groups.values() for c in cols],
                    "processed": {"columns": processed_columns},
                    "manifest": manifest, "stationarity_decisions": decisions,
                    "stationarity_keys": sorted(decisions),
                    **observer.structure(factory),
                    "run": {"base": str(root), "symbol": spec["symbol"], "tf": spec["primary_tf"],
                            "config_hash": config_hash}}

    xsec_runs: Dict[str, Any] = {}
    xsec_parts: Dict[str, NamingPart] = {}
    xs = spec["xsec"]
    for symbol in xs["symbols"]:
        sym_dir = work_dir / f"xsec_{symbol}"
        sym_dir.mkdir(parents=True, exist_ok=True)
        payload = json.loads(json.dumps(payloads["xsec"]))
        payload["cross_sectional"] = {"enabled": True, "reference_symbol": xs["reference_symbol"]}
        tag_before = dict(inst.tag_calls)
        with pytest.MonkeyPatch.context() as mp:
            prepare_stat_env(mp, sym_dir)
            if record_parts:
                inst.tag_calls = {}
                inst.install(mp)
            root, _factory, result = _generate(sym_dir, payload, symbol, xs["timeframe"], xs["window"])
            config_hash = str(result.metadata["config_hash"])
            manifest, columns = _read_run(root, symbol, xs["timeframe"], config_hash)
            groups = _manifest_groups(manifest)
            if not any(_is_l5_column(c) for cols in groups.values() for c in cols):
                raise FreezeError(f"L5 run {symbol} 無 cs_ 欄（L5 未涵蓋）")
            if record_parts:
                parts, missing = _tagged_parts(inst, [(c, _group_tf(g)) for g, cols in groups.items() for c in cols])
                if missing:
                    raise FreezeError(f"L5 run {symbol} 之 manifest 欄無零件紀錄：{missing[:30]}")
                for name, part in parts.items():
                    if xsec_parts.get(name, part) != part:
                        raise FreezeError(f"L5 run 間同名欄零件不同：{name!r}")
                    xsec_parts[name] = part
                inst.tag_calls = {**tag_before, **inst.tag_calls}
        xsec_runs[symbol] = {"columns": columns, "column_order": [c for cols in groups.values() for c in cols],
                             "manifest_groups": groups}
    info["xsec_runs"] = xsec_runs
    if record_parts:
        merged = dict(info["parts"])
        for name, part in xsec_parts.items():
            if merged.get(name, part) != part:
                raise FreezeError(f"主 run 與 L5 run 同名欄零件不同：{name!r}")
            merged[name] = part
        final = PartRecorder()
        for name in sorted(merged):
            final.record(merged[name])
        info["parts"] = final.to_json()
        info["anomalies"] = sorted(set(inst.anomalies))
    return info


# ---------------------------------------------------------------- Task 2.6 收據（改後碼態）

_FP_KEYS = ("dtype", "shape", "nan_sha256", "value_sha256")


def _baseline_mapping(baseline: Mapping[str, Any]) -> Dict[str, str]:
    parts = {row["old_name"]: _part_from_row(row) for row in baseline["parts"]}
    return derive_mapping(parts, {k: p.tf for k, p in parts.items()})


def value_invariance_receipt(baseline: Mapping[str, Any], current: Mapping[str, Any], *, command: str) -> Dict[str, Any]:
    """§G 通過條件之收據（Task 2.6）：改名差集、L2 合併差集、L4 新增 lag 欄、欄名長度變化、值雜湊不符數；
    各值由 `test_ffname_value_invariance` 以同一定義重算比對（收據只供審閱，不作 oracle）。"""
    from collections import Counter

    fn = _naming()
    mapping = _baseline_mapping(baseline)
    mismatches = [f"{old}->{mapping[old]}" for old, fp in baseline["columns"].items()
                  if current["columns"].get(mapping[old]) is None
                  or any(fp[k] != current["columns"][mapping[old]][k] for k in _FP_KEYS)]
    mapped = {mapping[o] for o in baseline["columns"]}
    groups = current["manifest_groups"]
    l1 = {c for gid, cols in groups.items() if str(gid).split("_")[1:2] == ["L1"] for c in cols}
    new_lags: List[str] = []
    for column in current["columns"]:
        if column in mapped:
            continue
        ident = fn.parse_feature_name(column)
        if not ident.ops or ident.ops[-1].split("-")[0] != "Lag":
            continue
        base = fn.parse_feature_name(fn.format_feature_name(dataclasses.replace(ident, ops=tuple(ident.ops[:-1]))))
        if fn.format_feature_name(base) in l1 or base.category == "raw":
            new_lags.append(column)
    signatures = [(mapping[r["fast"]], mapping[r["slow"]], r["op"]) for r in baseline["l2_pairs"]]
    merged = sorted(sig for sig, n in Counter(signatures).items() if n > 1)
    current_pairs = {tuple(x) for x in current["l2_pairs"]}
    return {
        "schema_version": "ffname-value-invariance-v1",
        "spec": "docs/FFNAME_SPEC.md v16 §G、Task 2.6",
        "command": command,
        "exit_code": 0 if not mismatches else 1,
        "head": _head_commit(),
        "baseline_sha256": _sha(BASELINE_PATH.read_bytes()),
        "value_hash_mismatch_count": len(mismatches),
        "value_hash_mismatches": mismatches[:200],
        "renamed": sorted([o, n] for o, n in mapping.items() if o != n),
        "renamed_count": sum(1 for o, n in mapping.items() if o != n),
        "l2_merged": [list(s) for s in merged],
        "l2_pair_symmetric_difference": sorted(map(list, set(signatures) ^ current_pairs)),
        "l4_new_lag": sorted(new_lags),
        "name_length_change": {o: len(n) - len(o) for o, n in mapping.items()},
        "column_count": {"baseline": len(baseline["columns"]), "current": len(current["columns"])},
        "column_set_extra": sorted(set(current["columns"]) - mapped - set(new_lags)),
        "column_set_missing": sorted(mapped - set(current["columns"])),
        "unparseable_current_names": sorted(c for c in current["columns"] if not _roundtrips(c)),
        "manifest_feature_naming_version": (current.get("manifest") or {}).get("feature_naming_version"),
        "l1_group_merges": _group_merges(baseline, current, mapping, set(new_lags)),
        "stationarity_new_lag_keys": sorted(set(current["stationarity_keys"])
                                            - {mapping[k] for k in baseline["stationarity_keys"]}),
        "diagnostics": _structure_diagnostics(baseline, current, mapping, set(new_lags), l1),
    }


def _group_merges(baseline: Mapping[str, Any], current: Mapping[str, Any], mapping: Mapping[str, str],
                  new_lags: Set[str]) -> Dict[str, List[str]]:
    """SPEC v17 §G ⑧：含多個舊 manifest 群組之新群組（新 group_id → 排序後之舊 group_id）；舊群組成員經映射。
    每個舊群組須恰落入一個新群組，否則 FreezeError。"""
    owner = {c: gid for gid, cols in current["manifest_groups"].items() for c in cols if c not in new_lags}
    merges: Dict[str, List[str]] = {}
    for old_gid, cols in baseline["manifest_groups"].items():
        targets = {owner.get(mapping[c]) for c in cols}
        if len(targets) != 1 or None in targets:
            raise FreezeError(f"舊群組 {old_gid} 未恰落入一個新群組：{sorted(t for t in targets if t)}")
        merges.setdefault(targets.pop(), []).append(old_gid)
    return {new: sorted(olds) for new, olds in sorted(merges.items()) if len(olds) > 1}


def _structure_diagnostics(baseline: Mapping[str, Any], current: Mapping[str, Any], mapping: Mapping[str, str],
                           new_lags: Set[str], l1: Set[str]) -> Dict[str, Any]:
    """欄序、群組結構、平穩化決策鍵、L4 lag 輸入之經映射比對（審閱用診斷；判定由驗收測試為之）。"""
    fn = _naming()
    old_order = [mapping[o] for o in baseline["column_order"]]
    new_order = [c for c in current["column_order"] if c not in new_lags]
    first_diff = next((i for i, (a, b) in enumerate(zip(old_order, new_order)) if a != b), None)
    old_groups = {frozenset(mapping[c] for c in cols) for cols in baseline["groups"].values()}
    new_groups = {frozenset(c for c in cols if c not in new_lags) for cols in current["manifest_groups"].values()}
    old_groups.discard(frozenset())
    new_groups.discard(frozenset())
    raw_inputs = {i for i in current["l4_lag_inputs"] if fn.parse_feature_name(i).category == "raw"}
    lag_input_diff = sorted(set(current["l4_lag_inputs"]) ^ (l1 | raw_inputs))
    return {
        "column_order_equal": old_order == new_order,
        "column_order_same_multiset": sorted(old_order) == sorted(new_order),
        "column_order_first_diff_index": first_diff,
        "column_order_first_diff": ([old_order[first_diff], new_order[first_diff]] if first_diff is not None else None),
        "group_partition_only_baseline": sorted(sorted(g) for g in old_groups - new_groups),
        "group_partition_only_current": sorted(sorted(g) for g in new_groups - old_groups),
        # 同為 manifest 群組之比對（baseline `groups` 取自 registry save_data、不含 L6.5 `_L65` 群組；manifest 含之）
        "manifest_group_partition_only_baseline": sorted(
            sorted(g) for g in ({frozenset(mapping[c] for c in cols) for cols in baseline["manifest_groups"].values()}
                                - new_groups)),
        "manifest_group_partition_only_current": sorted(
            sorted(g) for g in (new_groups
                                - {frozenset(mapping[c] for c in cols) for cols in baseline["manifest_groups"].values()})),
        "manifest_group_id_count": {"baseline": len(baseline["manifest_groups"]),
                                    "current": len(current["manifest_groups"])},
        "stationarity_keys_equal": {mapping[k] for k in baseline["stationarity_keys"]} == set(current["stationarity_keys"]),
        "stationarity_keys_only_baseline": sorted({mapping[k] for k in baseline["stationarity_keys"]}
                                                  - set(current["stationarity_keys"])),
        "stationarity_keys_only_current": sorted(set(current["stationarity_keys"])
                                                 - {mapping[k] for k in baseline["stationarity_keys"]}),
        "stationarity_decision_value_diffs": sorted(
            mapping[k] for k, v in baseline["stationarity_decisions"].items()
            if mapping[k] in current["stationarity_decisions"]
            and _canonical_json(v) != _canonical_json(json.loads(_canonical_json(current["stationarity_decisions"][mapping[k]]).decode("utf-8")))),
        "l4_lag_inputs_vs_l1_plus_raw_symmetric_difference": lag_input_diff,
    }


def _roundtrips(name: str) -> bool:
    fn = _naming()
    try:
        return fn.format_feature_name(fn.parse_feature_name(name)) == name
    except fn.FeatureNameParseError:
        return False


def write_value_receipt(out_path: Path = RECEIPT_PATH) -> int:
    """改後碼態跑一次 reference（隔離同 `fftfmeta_golden_helpers.prepare_env`，CGSA 序列），寫 Task 2.6 收據；
    值雜湊不符數 == 0 ⇒ rc 0。"""
    import pytest

    from tests.feature_engineering.fftfmeta_golden_helpers import prepare_env

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="ffname_value_receipt_") as tmp:
        with pytest.MonkeyPatch.context() as mp:
            prepare_env(mp, Path(tmp), FFACT_MULTI_TF_PARALLEL="0")
            current = run_reference(Path(tmp) / "run", record_parts=False)
        receipt = value_invariance_receipt(
            baseline, current, command="venv/bin/python scripts/ffname_freeze_baseline.py --value-receipt")
    receipt["elapsed_seconds"] = round(time.time() - started, 1)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[ffname-receipt] {_golden_rel(out_path)}：值雜湊不符 {receipt['value_hash_mismatch_count']}、"
          f"改名 {receipt['renamed_count']}、新增 lag {len(receipt['l4_new_lag'])}、"
          f"欄集合多出 {len(receipt['column_set_extra'])}／缺 {len(receipt['column_set_missing'])}")
    return int(receipt["exit_code"])


# ---------------------------------------------------------------- golden 之逐欄值指紋

# 各重凍對象 golden 中「特徵欄名」之結構位置（白名單；`*` 任一鍵／索引、`{K}` 該層之鍵為欄名（值為該欄之紀錄）、
# `[]` 該層清單之元素為欄名（成員資格）、`@f` 該物件之欄位 f 之字串值為欄名（值為整個物件））。
# 空 tuple＝該 golden 無逐欄紀錄（只含群組／整體雜湊或與欄名無關之內容），見回報。
GOLDEN_LAYOUTS: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    "tests/_golden/failopen/baseline.json": (),
    "tests/_golden/framepath/cgsa_fingerprint.json": (
        ("cells", "*", "fingerprint", "columns", "{K}"),
        ("cells", "*", "fingerprint", "result_columns", "columns", "{K}"),
    ),
    "tests/_golden/batch2d/cgsa_baseline.json": (
        ("frame", "per_column", "{K}"), ("frame", "ordered_columns", "[]"), ("manifest_columns", "[]"),
    ),
    "tests/_golden/batch2d/provenance.json": (("cgsa_column_to_layer", "{K}"), ("frame_column_to_layer", "{K}")),
    "tests/_golden/ffstat/baseline.json": (
        ("base", "{K}"), ("decisions", "{K}"), ("auto_off", "base", "{K}"), ("ic_first_supplied_off", "{K}"),
        ("derived", "[]"),
    ),
    "tests/_golden/ffstat/baseline_nostart.json": (("columns", "{K}"),),
    "tests/_golden/ffstat/baseline_dead_drops.json": (("l3_dead_drops", "{K}"),),
    "tests/_golden/ffstat/contract.json": (("stationarity_apply_to_rejected_examples", "*", "[]"),),
    "tests/_golden/ffstat/nan_propagation_classes.json": (),
    "tests/_golden/probewinsor/baseline.json": (("cells", "*", "fingerprints", "{K}"), ("cells", "*", "columns", "[]")),
    "tests/_golden/ratiounsafe/baseline.json": (("*", "columns", "{K}"), ("*", "names", "[]")),
    "tests/_golden/ratiounsafe/baseline_after.json": (("*", "columns", "{K}"), ("*", "names", "[]")),
    "tests/_golden/ratiounsafe/branch_oracle.json": (("*", "{K}"),),
    "tests/_golden/ratiounsafe/contract.json": (
        ("tagging_cases", "*", "@column"), ("tagging_cases", "*", "@tagged"), ("branch_columns", "*", "*", "@name"),
    ),
    "tests/_golden/icfirstalign/calibration_baseline.json": (
        ("*", "*", "*", "first_ts", "{K}"), ("*", "*", "*", "last_ts", "{K}"), ("*", "*", "*", "values", "{K}"),
        ("*", "*", "*", "empty_columns", "[]"),
    ),
    "tests/_golden/icfirstalign/l3_default_arm.json": (("columns", "{K}"),),
    "tests/_golden/icfirstalign/probe_baseline.json": (),
    "tests/_golden/icfirstalign/contract.json": (),
    "tests/_golden/icpostleak/contract.json": (("kline", "l1_features", "*", "@name"),),
    "tests/_golden/fftfmeta/baseline.json": (),
    "tests/_golden/v2_ts/g1_baseline_fingerprint.json": (
        ("feature_fingerprint", "*", "stats", "{K}"), ("manifest_allowlist", "groups", "*", "columns", "[]"),
    ),
}


def _golden_rel(path: Path) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _golden_layout(path: Path) -> Tuple[Tuple[str, ...], ...]:
    rel = _golden_rel(path)
    if rel not in GOLDEN_LAYOUTS:
        raise FreezeError(f"golden {rel} 無登記之欄名位置（GOLDEN_LAYOUTS）")
    return GOLDEN_LAYOUTS[rel]


def _walk_layout(node: Any, pattern: Tuple[str, ...], path: Tuple[str, ...], out: List[Tuple[str, str, Any]]) -> None:
    if not pattern:
        return
    seg, rest = pattern[0], pattern[1:]
    if seg == "{K}":
        if isinstance(node, dict) and not rest:
            for key, value in node.items():
                out.append((str(key), "/".join(path + ("{K}",)), value))
        return
    if seg == "[]":
        if isinstance(node, list) and not rest:
            for value in node:
                if isinstance(value, str):
                    out.append((value, "/".join(path + ("[]",)), "<member>"))
        return
    if seg.startswith("@"):
        field = seg[1:]
        if isinstance(node, dict) and not rest and isinstance(node.get(field), str):
            out.append((node[field], "/".join(path + (seg,)), node))
        return
    if seg == "*":
        if isinstance(node, dict):
            for key, value in node.items():
                _walk_layout(value, rest, path + (str(key),), out)
        elif isinstance(node, list):
            for value in node:
                _walk_layout(value, rest, path + ("#",), out)
        return
    if isinstance(node, dict) and seg in node:
        _walk_layout(node[seg], rest, path + (seg,), out)


def _golden_occurrences(path: Path) -> List[Tuple[str, str, Any]]:
    layout = _golden_layout(path)
    if not layout:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: List[Tuple[str, str, Any]] = []
    for pattern in layout:
        _walk_layout(data, pattern, (), out)
    return out


def _scrub(value: Any, names: Set[str]) -> Any:
    """值中之欄名字串換成定值（值雜湊與欄名無關；Task 4.3 以同函式重算新 golden）。"""
    if isinstance(value, str):
        return "<COL>" if value in names else value
    if isinstance(value, list):
        return [_scrub(v, names) for v in value]
    if isinstance(value, dict):
        return sorted(([_scrub(str(k), names), _scrub(v, names)] for k, v in value.items()),
                      key=lambda kv: _canonical_json(kv))
    return value


def golden_value_fingerprints(path: Path) -> Dict[str, str]:
    """單一 golden 檔之逐欄值雜湊（欄名 → 值雜湊；與欄名無關之值位元組雜湊）。
    同一函式於 Task 0.1 凍結改前 golden（寫入 baseline `golden_values`）、於 Task 4.3 重算新 golden；
    各 golden 檔格式之解讀由本函式負責（`GOLDEN_LAYOUTS`）。值雜湊＝該欄於檔內全部出現位置（位置路徑以 `{K}`／`[]`／`@f`
    代欄名、清單索引以 `#` 代）與其紀錄（欄名字串換成定值）之排序清單之 sha256，取前 `refreeze.golden_value_hash_len`
    個十六進位字元（SPEC v15 §G：控制 baseline 體積）。"""
    hash_len = golden_value_hash_len()
    occurrences = _golden_occurrences(path)
    names = {name for name, _p, _v in occurrences}
    per_name: Dict[str, List[List[str]]] = {}
    for name, location, value in occurrences:
        per_name.setdefault(name, []).append([location, _sha(_canonical_json(_scrub(value, names)))])
    return {name: _sha(_canonical_json(sorted(entries)))[:hash_len] for name, entries in per_name.items()}


def golden_value_hash_len() -> int:
    """golden 逐欄值雜湊之長度（十六進位字元數；單一落點＝契約 `refreeze.golden_value_hash_len`）。"""
    value = int(_contract()["refreeze"]["golden_value_hash_len"])
    if not 8 <= value <= 64:
        raise FreezeError(f"契約 refreeze.golden_value_hash_len={value} 不在 8–64")
    return value


def no_column_records() -> Dict[str, Dict[str, str]]:
    """契約 `refreeze.no_column_records`：檔內無逐欄紀錄之重凍 golden → {class, reason}（SPEC v15 §G）。"""
    return dict(_contract()["refreeze"].get("no_column_records") or {})


def golden_file_sha256(path: Path) -> str:
    return _sha(Path(path).read_bytes())


def _baseline_goldens() -> List[str]:
    """不可變 baseline 之 golden 範圍（契約 `refreeze.baseline_goldens`；SPEC v21 起 `refreeze.goldens` 只列實際重凍者）。"""
    refreeze = _contract()["refreeze"]
    return list(refreeze.get("baseline_goldens") or refreeze["goldens"])


def _blob_sha256(head: Optional[str], rel: str) -> Optional[str]:
    """baseline `frozen_at_head` 之該檔 sha256（git 物件；重凍後磁碟上之檔可變，基準比對以凍結點為準）。"""
    if not head:
        return None
    proc = subprocess.run(["git", "show", f"{head}:{rel}"], cwd=str(REPO), capture_output=True)
    return _sha(proc.stdout) if proc.returncode == 0 else None


def _pre_change_golden_bytes(rel: str, baseline: Mapping[str, Any]) -> Optional[bytes]:
    """改前 golden 位元組：baseline `frozen_at_head` 之該檔（git 物件）。"""
    head = baseline.get("frozen_at_head")
    if not head:
        return None
    proc = subprocess.run(["git", "show", f"{head}:{rel}"], cwd=str(REPO), capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def run_full_reference(work_dir: Path, symbol: str, start: Optional[str], end: Optional[str]) -> Dict[str, Any]:
    """全量 reference（Task 4.3）：reference `main` 設定（週期取契約 `refreeze.full_reference.timeframes`）於 `symbol`
    跑 IC-first 正式路徑；回傳 raw＋processed 全部欄名。寫入隔離同 `fftfmeta_golden_helpers.prepare_env`（由呼叫端設）。"""
    from tests.feature_engineering.fftfmeta_golden_helpers import PRIMARY_TF

    timeframes = list(_contract()["refreeze"]["full_reference"]["timeframes"])
    payload = json.loads(json.dumps(reference_payloads()["main"]))
    primary = PRIMARY_TF if PRIMARY_TF in timeframes else timeframes[0]
    payload["timeframes"] = {**payload["timeframes"], "primary": primary, "training": timeframes}
    root, _factory, result = _generate_ic_first(Path(work_dir), payload, symbol, primary, (start, end))
    config_hash = str(result.metadata["config_hash"])
    manifest, raw = _read_run(root, symbol, primary, config_hash)
    _pm, processed = _read_run(root, symbol, primary, config_hash, "processed")
    return {"symbol": symbol, "timeframes": timeframes, "window": [start, end],
            "feature_naming_version": manifest.get("feature_naming_version"),
            "columns": sorted(set(raw) | set(processed))}


def full_reference_record(info: Mapping[str, Any]) -> Dict[str, Any]:
    fn = _naming()
    parse_failures = roundtrip_failures = 0
    for name in info["columns"]:
        try:
            if fn.format_feature_name(fn.parse_feature_name(name)) != name:
                roundtrip_failures += 1
        except fn.FeatureNameParseError:
            parse_failures += 1
    return {**dict(info), "total_columns": len(info["columns"]), "parse_failures": parse_failures,
            "roundtrip_failures": roundtrip_failures}


def golden_columns(path: Path) -> List[str]:
    """單一 golden 檔所含之特徵欄名清單（與值雜湊分開解讀，供「fingerprint 數 == 欄數」之完整性比對）。"""
    return sorted({name for name, _p, _v in _golden_occurrences(path)})


def _contract() -> Dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _golden_sections() -> Tuple[Dict[str, Dict[str, str]], Dict[str, int], Dict[str, str]]:
    """(golden_values, golden_column_counts, golden_file_sha256)；無逐欄紀錄者須登記於 no_column_records，
    登記者須確無逐欄紀錄（否則凍結失敗）。"""
    registered = no_column_records()
    values: Dict[str, Dict[str, str]] = {}
    counts: Dict[str, int] = {}
    file_sha: Dict[str, str] = {}
    unregistered_empty: List[str] = []
    for rel in _baseline_goldens():
        path = REPO / rel
        values[rel] = golden_value_fingerprints(path)
        counts[rel] = len(golden_columns(path))
        if rel in registered:
            if values[rel]:
                raise FreezeError(f"golden {rel} 登記為無逐欄紀錄，實有 {len(values[rel])} 欄紀錄")
            file_sha[rel] = golden_file_sha256(path)
        elif not values[rel]:
            unregistered_empty.append(rel)
    stray = sorted(set(registered) - set(values))
    if unregistered_empty or stray:
        raise FreezeError(f"無逐欄紀錄而未登記 no_column_records：{unregistered_empty}；登記而不在 goldens：{stray}")
    return values, counts, file_sha


# ---------------------------------------------------------------- 凍結與檢查


def _head_commit() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _summary(parts_rows: Sequence[Mapping[str, Any]], columns: Mapping[str, Any]) -> Dict[str, Any]:
    kinds: Dict[str, int] = {}
    points: Dict[str, int] = {}
    for row in parts_rows:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
        points[row["point"]] = points.get(row["point"], 0) + 1
    return {"column_count": len(columns), "part_count": len(parts_rows), "kind_counts": kinds, "point_counts": points}


def _baseline_payload(info: Dict[str, Any]) -> Dict[str, Any]:
    spec = _reference_spec()
    golden_values, golden_counts, golden_file_sha = _golden_sections()
    columns = info["columns"]
    return {
        "schema": BASELINE_SCHEMA,
        "spec": "docs/FFNAME_SPEC.md v15 §G、Task 0.1",
        "frozen_at_head": _head_commit(),
        "reference": {**spec, "payloads": reference_payloads()},
        "columns": columns,
        "column_order": info["column_order"],
        "column_order_sha256": _sha(_canonical_json(info["column_order"])),
        "parts": info["parts"],
        "l2_pairs": info["l2_pairs"],
        "l4_lags": info["l4_lags"],
        "l4_lag_inputs": info["l4_lag_inputs"],
        "group_ids": info["group_ids"],
        "groups": info["groups"],
        "manifest_groups": info["manifest_groups"],
        "processed": info["processed"],
        "stationarity_keys": info["stationarity_keys"],
        "stationarity_decisions": info["stationarity_decisions"],
        "manifest": info["manifest"],
        "xsec_runs": info["xsec_runs"],
        "tag_disagreements": info["tag_disagreements"],
        "anomalies": info.get("anomalies", []),
        "golden_values": golden_values,
        "golden_column_counts": golden_counts,
        "golden_file_sha256": golden_file_sha,
        "golden_value_hash_len": golden_value_hash_len(),
        "summary": {**_summary(info["parts"], columns),
                    "processed_column_count": len(info["processed"]["columns"]),
                    "xsec_column_count": {s: len(r["columns"]) for s, r in info["xsec_runs"].items()}},
    }


def _first_diff(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    return sorted(k for k in set(a) | set(b) if _canonical_json(a.get(k)) != _canonical_json(b.get(k)))


def freeze(out_path: Path = BASELINE_PATH) -> int:
    """改前 HEAD 碼態凍結（兩次重跑 baseline sha256 須相同）；baseline 另含 `golden_values` 與 `golden_column_counts`；
    同時寫 `BASELINE_SHA_PATH`（baseline.json 之 sha256）；rc 0 成功。"""
    runs = max(1, int(os.environ.get(FREEZE_RUNS_ENV, "2")))
    payloads: List[Dict[str, Any]] = []
    for attempt in range(runs):
        started = time.time()
        with tempfile.TemporaryDirectory(prefix="ffname_freeze_") as tmp:
            info = run_reference(Path(tmp), record_parts=True)
            payloads.append(_baseline_payload(info))
        print(f"[ffname-freeze] reference run {attempt + 1}/{runs}: {time.time() - started:.1f}s，"
              f"欄 {len(payloads[-1]['columns'])}、零件 {len(payloads[-1]['parts'])}", flush=True)
    blobs = [_canonical_json(p) for p in payloads]
    if any(blob != blobs[0] for blob in blobs[1:]):
        diffs = sorted({k for p in payloads[1:] for k in _first_diff(payloads[0], p)})
        print(f"[ffname-freeze] FAIL：重跑之 baseline 不一致（非決定性），差異鍵：{diffs}", file=sys.stderr)
        return 1
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = blobs[0] + b"\n"
    out_path.write_bytes(data)
    sha_path = BASELINE_SHA_PATH if out_path.resolve() == BASELINE_PATH.resolve() else out_path.with_suffix(".sha256")
    sha_path.write_text(_sha(data) + "\n", encoding="utf-8")
    print(f"[ffname-freeze] OK：{_golden_rel(out_path)} sha256={_sha(data)}（{runs} 次重跑位元組相同）")
    return 0


def _golden_problems(data: Mapping[str, Any]) -> List[str]:
    """golden 值 oracle 段之檢查（SPEC v15 §G）：逐欄 golden 須非空、fingerprint 數＝欄數、雜湊長＝契約 hash_len；
    無逐欄紀錄者須登記於 no_column_records（類別屬 oracle_classes、理由非空），且 golden_file_sha256 等於 baseline
    `frozen_at_head` 之該檔（SPEC v21：重凍後磁碟上之檔依 K0–K3 改變，基準之錨為凍結點）。"""
    problems: List[str] = []
    refreeze = _contract()["refreeze"]
    goldens = _baseline_goldens()
    classes = set(refreeze.get("oracle_classes") or ())
    registered = no_column_records()
    hash_len = golden_value_hash_len()
    golden_values = data.get("golden_values") or {}
    golden_counts = data.get("golden_column_counts") or {}
    file_sha = data.get("golden_file_sha256") or {}
    if sorted(golden_values) != sorted(goldens) or sorted(golden_counts) != sorted(goldens):
        return ["golden_values／golden_column_counts 之鍵 != contract refreeze.goldens"]
    if sorted(file_sha) != sorted(rel for rel in goldens if rel in registered):
        problems.append(f"golden_file_sha256 之鍵 {sorted(file_sha)} != 已登記 no_column_records 之 golden")
    for rel in sorted(set(registered) - set(goldens)):
        problems.append(f"no_column_records 登記 {rel} 不在 refreeze.goldens")
    for rel in goldens:
        values = golden_values[rel]
        if rel in registered:
            entry = registered[rel] or {}
            if entry.get("class") not in classes:
                problems.append(f"golden {rel}：no_column_records 類別 {entry.get('class')!r} 不屬 oracle_classes")
            if not str(entry.get("reason") or "").strip():
                problems.append(f"golden {rel}：no_column_records 缺理由")
            if values or golden_counts[rel] != 0:
                problems.append(f"golden {rel} 登記為無逐欄紀錄，baseline 卻有 {len(values)} 筆／欄數 {golden_counts[rel]}")
            anchored = _blob_sha256(data.get("frozen_at_head"), rel)
            if anchored is None or file_sha.get(rel) != anchored:
                problems.append(f"golden {rel}：golden_file_sha256 != baseline frozen_at_head 之該檔 sha256")
            continue
        if not values:
            problems.append(f"golden {rel} 無逐欄紀錄且未登記 refreeze.no_column_records")
            continue
        if len(values) != golden_counts[rel]:
            problems.append(f"golden {rel}：fingerprint 數 {len(values)} != 欄數 {golden_counts[rel]}")
        bad_len = [n for n, h in values.items() if len(h) != hash_len or re.fullmatch(r"[0-9a-f]+", h) is None]
        if bad_len:
            problems.append(f"golden {rel}：值雜湊長度 != {hash_len} 或非十六進位 {len(bad_len)} 筆：{bad_len[:5]}")
    return problems


_REQUIRED_SECTIONS = ("columns", "parts", "l2_pairs", "l4_lag_inputs", "column_order", "group_ids", "groups",
                      "stationarity_keys", "stationarity_decisions")


def check(path: Path = BASELINE_PATH) -> int:
    """驗 baseline：無紀錄欄數 == 0；L2 配對簽名、lag 輸入集合、欄序、group、平穩化決策、golden_values 均已記；rc 0＝通過。"""
    path = Path(path)
    problems: List[str] = []
    warnings: List[str] = []
    if not path.is_file():
        print(f"[ffname-check] FAIL：{path} 不存在", file=sys.stderr)
        return 1
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema") != BASELINE_SCHEMA:
        problems.append(f"schema != {BASELINE_SCHEMA}")
    for key in _REQUIRED_SECTIONS:
        if not data.get(key):
            problems.append(f"缺或空：{key}")
    parts = {row["old_name"]: _part_from_row(row) for row in data.get("parts", [])}
    if len(parts) != len(data.get("parts", [])):
        problems.append("parts 內舊名重複")
    missing = missing_parts(data.get("columns", {}), parts)
    if missing:
        problems.append(f"manifest 欄無零件紀錄 {len(missing)} 欄：{missing[:20]}")
    if sorted(data.get("column_order", [])) != sorted(data.get("columns", {})):
        problems.append("column_order 與 columns 欄集合不一致")
    processed = data.get("processed") or {}
    if not processed.get("columns"):
        problems.append("缺或空：processed（post-IC rank／gaussian／zscore 後綴）")
    lacking_processed = missing_parts(processed.get("columns", {}), parts)
    if lacking_processed:
        problems.append(f"processed 欄無零件紀錄 {len(lacking_processed)} 欄：{lacking_processed[:20]}")
    for symbol, run in (data.get("xsec_runs") or {}).items():
        lacking = missing_parts(run.get("columns", {}), parts)
        if lacking:
            problems.append(f"L5 run {symbol} 欄無零件紀錄：{lacking[:20]}")
    for col, fp in (data.get("columns") or {}).items():
        if not {"dtype", "shape", "nan_sha256", "value_sha256"} <= set(fp):
            problems.append(f"欄指紋缺鍵：{col}")
            break
    for row in data.get("l2_pairs", []):
        if row["column"] not in parts:
            problems.append(f"L2 配對欄無零件：{row['column']}")
            break
    try:
        mapping = derive_mapping(parts, {})
        fn = _naming()
        bad = [n for n in mapping.values() if fn.format_feature_name(fn.parse_feature_name(n)) != n]
        if bad:
            problems.append(f"新名往返失敗：{bad[:20]}")
    except FreezeError as exc:
        problems.append(str(exc))
    none_source = sorted(name for name, part in parts.items() if part.source is None)
    if none_source:  # SPEC v15 Task 0.1 邊界②：source 不得為 None
        problems.append(f"零件 source 為 None {len(none_source)} 筆：{none_source[:20]}")
    problems.extend(_golden_problems(data))
    if BASELINE_SHA_PATH.is_file() and path.resolve() == BASELINE_PATH.resolve():
        if BASELINE_SHA_PATH.read_text(encoding="utf-8").strip() != _sha(raw):
            problems.append("baseline.sha256 != baseline.json 之 sha256")
    for item in warnings:
        print(f"[ffname-check] WARN：{item}")
    if problems:
        for item in problems:
            print(f"[ffname-check] FAIL：{item}", file=sys.stderr)
        return 1
    print(f"[ffname-check] OK：欄 {len(data['columns'])}、零件 {len(parts)}、L2 配對 {len(data['l2_pairs'])}、"
          f"lag 輸入 {len(data['l4_lag_inputs'])}、平穩化決策 {len(data['stationarity_keys'])}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只驗既有 baseline.json")
    parser.add_argument("--out", default=str(BASELINE_PATH))
    parser.add_argument("--value-receipt", action="store_true",
                        help="改後碼態跑 reference 並寫 Task 2.6 收據（handoffs/run_receipts/ffname-value-invariance.json）")
    parser.add_argument("--full-reference-only", metavar="OUT_JSON", default=None,
                        help="Task 4.3：只跑全量 reference，欄名清單寫入 OUT_JSON（供 scripts/ffname_refreeze.py receipt 沿用）")
    parser.add_argument("--full-ref-symbol", default="ETHUSDT", help="全量 reference 標的（SPEC Task 4.3：ETHUSDT）")
    parser.add_argument("--full-ref-start", default=None, help="全量 reference 起日（預設 None＝kline 全史）")
    parser.add_argument("--full-ref-end", default=None)
    args = parser.parse_args(argv)
    if args.value_receipt:
        return write_value_receipt()
    if args.full_reference_only:
        import pytest

        from tests.feature_engineering.fftfmeta_golden_helpers import prepare_env

        started = time.time()
        with tempfile.TemporaryDirectory(prefix="ffname_full_reference_") as tmp:
            with pytest.MonkeyPatch.context() as mp:
                prepare_env(mp, Path(tmp), FFACT_MULTI_TF_PARALLEL="0")
                info = run_full_reference(Path(tmp) / "run", args.full_ref_symbol, args.full_ref_start, args.full_ref_end)
        info["elapsed_seconds"] = round(time.time() - started, 1)
        Path(args.full_reference_only).write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"[ffname-full-reference] {len(info['columns'])} 欄、{info['elapsed_seconds']}s → {args.full_reference_only}")
        return 0
    if args.check:
        return check(Path(args.out))
    return freeze(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
