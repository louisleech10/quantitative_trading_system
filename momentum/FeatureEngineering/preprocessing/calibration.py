"""平穩化校準之資料契約（docs/FFSTAT_SPEC.md §C「校準封包」「前史深度」「未填起始日」、Task 2.1／2.3）。

校準值只取輸出起始日之前之前史（校準資料域），由前置關卡產生封包，交各原生週期之 L6.5 使用。
本模組只放純資料結構與純函式；計算校準域之流程在 `feature_factory.FeatureFactory.run_calibration_preflight`。
"""

from __future__ import annotations

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
    raise NotImplementedError("FFSTAT Task 2.1")


def calibration_source_sha256(klines: pd.DataFrame) -> str:
    """前史切片 K 線之來源紀錄 sha256（§C 位元組框架：表頭欄名 UTF-8 升序以 `\\n` 連接後接 `\\n\\n`；
    表身列優先、時間戳 int64 奈秒小端＋各欄 float64 小端；NaN 一律 `CANONICAL_NAN_BITS`）。

    `klines` 之 index 為 DatetimeIndex（升序），欄為來源欄（數值）。Task 2.1。"""
    raise NotImplementedError("FFSTAT Task 2.1")


def verify_packet(packet: CalibrationPacket, expected: CalibrationKey, columns: Sequence[str]) -> None:
    """L6.5 使用封包前之核對：身分鍵逐項相等、欄集合相等、每欄最晚校準時間早於輸出起始日；
    不符 ⇒ 拋 `CalibrationError`（訊息含週期、欄、不符欄位）。Task 2.1。"""
    raise NotImplementedError("FFSTAT Task 2.1")


def calibration_values_before(series: pd.Series, output_start: pd.Timestamp, n: int) -> np.ndarray:
    """取序列於 `output_start` 之前最後 `n` 個有限值（依時間升序）；不足 `n` ⇒ 拋 `CalibrationError`
    （訊息含欄名與缺少根數；§C 前史深度）。Task 2.1。"""
    raise NotImplementedError("FFSTAT Task 2.1")


def calibration_ingest_start(kline_index: pd.DatetimeIndex, output_start: pd.Timestamp, depth: int) -> pd.Timestamp:
    """校準域載入起點：`kline_index` 中早於 `output_start` 之列倒數第 `depth` 根之時間（依實際存在之列計數，
    缺口不補）；不足 ⇒ 拋 `CalibrationError`（缺少根數）。§C 前史深度、Task 2.1。"""
    raise NotImplementedError("FFSTAT Task 2.1")


def resolve_effective_output_start(
    kline_indexes: Mapping[str, pd.DatetimeIndex],
    depth_by_tf: Mapping[str, int],
    primary_index: pd.DatetimeIndex,
) -> pd.Timestamp:
    """未填起始日時之有效起始日（§C 未填起始日）：各原生週期取實際 K 線列以 0 起算之索引 `depth` 那一列之時間，
    取最晚者，再對齊為 `primary_index` 中第一個不早於它之時間戳；歷史不足 ⇒ 拋 `CalibrationError`。Task 2.3。"""
    raise NotImplementedError("FFSTAT Task 2.3")


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
