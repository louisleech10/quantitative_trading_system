"""平穩化校準之資料契約（docs/FFSTAT_SPEC.md §C「校準封包」「前史深度」「未填起始日」、Task 2.1／2.3）。

校準值只取輸出起始日之前之前史（校準資料域），由前置關卡產生封包，交各原生週期之 L6.5 使用。
本模組只放純資料結構與純函式；計算校準域之流程在 `feature_factory.FeatureFactory.run_calibration_preflight`。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

# 封包身分鍵之欄位（§C 校準封包）；順序即錯誤訊息與收據之呈現順序
PACKET_KEY_FIELDS: Tuple[str, ...] = ("symbol", "timeframe", "output_start", "config_hash", "n", "column_set_digest")

# 有效起始日之來源（§C 未填起始日；Task 2.3）
OUTPUT_START_SOURCE_USER = "user"
OUTPUT_START_SOURCE_AUTO = "auto_reserved_calibration"
OUTPUT_START_SOURCES: Tuple[str, ...] = (OUTPUT_START_SOURCE_USER, OUTPUT_START_SOURCE_AUTO)

# `calibration_source_sha256` 之 NaN 正規化位元樣式（§C 位元組框架③）
CANONICAL_NAN_BITS = 0x7FF8000000000000


class CalibrationError(RuntimeError):
    """校準域任一步驟之錯誤：不可降級之生成失敗（§C「校準域錯誤不可降級」）。

    訊息須指名週期、欄與不符之身分欄位或缺少根數（§C 校準封包、前史深度）。"""

    def __init__(self, message: str, *, timeframe: str = "", column: str = "", field: str = "") -> None:
        super().__init__(message)
        self.timeframe = timeframe
        self.column = column
        self.field = field


@dataclass(frozen=True)
class CalibrationKey:
    """封包身分鍵（§C 校準封包）。"""

    symbol: str
    timeframe: str
    output_start: pd.Timestamp
    config_hash: str
    n: int
    column_set_digest: str


@dataclass(frozen=True)
class CalibrationPacket:
    """單一原生週期之校準結果（§C 校準封包；只由前置關卡產生）。"""

    key: CalibrationKey
    values: Mapping[str, np.ndarray]
    last_calibration_ts: Mapping[str, pd.Timestamp]
    calibration_source_sha256: str
    extras: Dict[str, object] = field(default_factory=dict)


def column_set_digest(columns: Sequence[str]) -> str:
    """欄集合指紋：欄名排序後之 sha256（封包身分鍵 `column_set_digest`；Task 2.1）。"""
    ordered = sorted({str(column) for column in columns}, key=lambda c: c.encode("utf-8"))
    return hashlib.sha256("\n".join(ordered).encode("utf-8")).hexdigest()


def _timestamps_ns(index: pd.Index) -> np.ndarray:
    """DatetimeIndex → int64 奈秒（不論儲存單位）。"""
    dt_index = pd.DatetimeIndex(index)
    if hasattr(dt_index, "as_unit"):
        dt_index = dt_index.as_unit("ns")
    return np.asarray(dt_index.asi8, dtype=np.int64)


def calibration_source_sha256(klines: pd.DataFrame) -> str:
    """前史切片 K 線之來源紀錄 sha256（§C 位元組框架：表頭欄名 UTF-8 升序以 `\\n` 連接後接 `\\n\\n`；
    表身列優先、時間戳 int64 奈秒小端＋各欄 float64 小端；NaN 一律 `CANONICAL_NAN_BITS`）。

    `klines` 之 index 為 DatetimeIndex（升序），欄為來源欄（數值）。Task 2.1。"""
    columns = sorted((str(c) for c in klines.columns), key=lambda c: c.encode("utf-8"))
    header = ("\n".join(columns)).encode("utf-8") + b"\n\n"
    values = klines[columns].to_numpy(dtype=np.float64, copy=True) if columns else np.empty((len(klines), 0))
    bits = values.view(np.uint64)
    bits[np.isnan(values)] = np.uint64(CANONICAL_NAN_BITS)
    body = np.empty((len(klines), 1 + len(columns)), dtype="<u8")
    body[:, 0] = _timestamps_ns(klines.index).view(np.uint64)
    body[:, 1:] = bits
    return hashlib.sha256(header + body.tobytes(order="C")).hexdigest()


def verify_packet(packet: CalibrationPacket, expected: CalibrationKey, columns: Sequence[str]) -> None:
    """L6.5 使用封包前之核對：身分鍵逐項相等、欄集合相等、每欄最晚校準時間早於輸出起始日；
    不符 ⇒ 拋 `CalibrationError`（訊息含週期、欄、不符欄位）。Task 2.1。"""
    timeframe = str(expected.timeframe)
    for field_name in PACKET_KEY_FIELDS:
        got, want = getattr(packet.key, field_name), getattr(expected, field_name)
        if got != want:
            raise CalibrationError(
                f"校準封包身分不符：週期 {timeframe} 欄位 {field_name} 封包值 {got!r} ≠ 預期 {want!r}",
                timeframe=timeframe, field=field_name,
            )
    output_start = pd.Timestamp(expected.output_start)
    want_columns = {str(c) for c in columns}
    # b3 審碼 r1 codex P1-02：values／last_calibration_ts 之鍵集須恰為欄集合（缺、多皆拒），
    # 每欄校準值須為一維、長度恰為 N、全為有限值
    for field_name, mapping in (("values", packet.values), ("last_calibration_ts", packet.last_calibration_ts)):
        got_columns = {str(k) for k in mapping}
        missing = sorted(want_columns - got_columns)
        extra = sorted(got_columns - want_columns)
        if missing or extra:
            name = (missing or extra)[0]
            kind = "缺欄" if missing else "多欄"
            raise CalibrationError(
                f"校準封包{kind}：週期 {timeframe} 欄 {name}（欄位 {field_name}；缺 {missing}，多 {extra}）",
                timeframe=timeframe, column=name, field=field_name,
            )
    n = int(expected.n)
    for column in columns:
        name = str(column)
        values = np.asarray(packet.values[name])
        if values.ndim != 1 or values.shape[0] != n:
            raise CalibrationError(
                f"校準值形狀不符：週期 {timeframe} 欄 {name} 形狀 {values.shape}，須為一維 {n} 筆",
                timeframe=timeframe, column=name, field="values",
            )
        if not np.issubdtype(values.dtype, np.number) or not np.isfinite(values.astype(np.float64)).all():
            raise CalibrationError(
                f"校準值含非有限值或非數值：週期 {timeframe} 欄 {name}",
                timeframe=timeframe, column=name, field="values",
            )
        last_ts = pd.Timestamp(packet.last_calibration_ts[name])
        if not last_ts < output_start:
            raise CalibrationError(
                f"校準時間未早於輸出起始日：週期 {timeframe} 欄 {name} 最晚校準時間 {last_ts} ≥ {output_start}",
                timeframe=timeframe, column=name, field="last_calibration_ts",
            )


def calibration_values_before(series: pd.Series, output_start: pd.Timestamp, n: int) -> np.ndarray:
    """取序列於 `output_start` 之前最後 `n` 個有限值（依時間升序）；不足 `n` ⇒ 拋 `CalibrationError`
    （訊息含欄名與缺少根數；§C 前史深度）。Task 2.1。"""
    before = series[series.index < pd.Timestamp(output_start)]
    values = before.to_numpy(dtype=np.float64)
    finite = values[np.isfinite(values)]
    if len(finite) < int(n):
        name = str(series.name)
        raise CalibrationError(
            f"校準前史有效值不足：欄 {name} 於 {output_start} 之前有限值 {len(finite)} 根，需 {int(n)} 根，"
            f"缺少 {int(n) - len(finite)} 根",
            column=name, field="n",
        )
    return finite[-int(n):]


def calibration_ingest_start(kline_index: pd.DatetimeIndex, output_start: pd.Timestamp, depth: int) -> pd.Timestamp:
    """校準域載入起點：`kline_index` 中早於 `output_start` 之列倒數第 `depth` 根之時間（依實際存在之列計數，
    缺口不補）；不足 ⇒ 拋 `CalibrationError`（缺少根數）。§C 前史深度、Task 2.1。"""
    before = kline_index[kline_index < pd.Timestamp(output_start)]
    if len(before) < int(depth):
        raise CalibrationError(
            f"校準前史不足：{output_start} 之前實際 K 線 {len(before)} 根，需 {int(depth)} 根，"
            f"缺少 {int(depth) - len(before)} 根",
            field="depth",
        )
    return pd.Timestamp(before[-int(depth)])


def resolve_effective_output_start(
    kline_indexes: Mapping[str, pd.DatetimeIndex],
    depth_by_tf: Mapping[str, int],
    primary_index: pd.DatetimeIndex,
) -> pd.Timestamp:
    """未填起始日時之有效起始日（§C 未填起始日）：各原生週期取實際 K 線列以 0 起算之索引 `depth` 那一列之時間，
    取最晚者，再對齊為 `primary_index` 中第一個不早於它之時間戳；歷史不足 ⇒ 拋 `CalibrationError`。Task 2.3。"""
    # b3 審碼 r1 codex P2-03：各 index 之時區狀態須一致（全有 tz 或全無），混用即拒收，不隱式轉換
    tz_aware = {name: getattr(idx, "tz", None) is not None
                for name, idx in [("primary", primary_index), *kline_indexes.items()]}
    if len(set(tz_aware.values())) > 1:
        raise CalibrationError(
            f"時間索引時區狀態不一致（有 tz＝True）：{tz_aware}", field="timezone",
        )
    candidates = []
    for timeframe, index in kline_indexes.items():
        depth = int(depth_by_tf[timeframe])
        if len(index) <= depth:
            raise CalibrationError(
                f"可用歷史不足以預留校準段：週期 {timeframe} 實際 K 線 {len(index)} 根，需多於 {depth} 根，"
                f"缺少 {depth + 1 - len(index)} 根",
                timeframe=str(timeframe), field="depth",
            )
        candidates.append(pd.Timestamp(index[depth]))
    latest = max(candidates)
    aligned = primary_index[primary_index >= latest]
    if len(aligned) == 0:
        raise CalibrationError(f"有效起始日 {latest} 晚於主週期資料末端", field="depth")
    return pd.Timestamp(aligned[0])


def load_calibration_klines(factory: object, symbol: str, timeframe: str,
                            start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """前置關卡讀取校準前史 K 線之唯一入口（`[start, end)`，該原生週期；§C 兩個資料域）。

    前置關卡須經此函式讀前史（測試以之注入讀取錯誤）；讀取錯誤轉為 `CalibrationError`。Task 2.1。"""
    raise NotImplementedError("FFSTAT Task 2.1")


def compute_calibration_domain(factory: object, symbol: str, timeframe: str, config: object,
                               klines: pd.DataFrame) -> pd.DataFrame:
    """以獨立 `FeatureFactory` 實例對前史切片計算進入 L6.5 之各層特徵（校準資料域之唯一計算入口；
    不寫 registry／resume、不落盤、暫存目錄算完即刪）。測試以之注入計算錯誤。Task 2.1。"""
    raise NotImplementedError("FFSTAT Task 2.1")
