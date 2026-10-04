"""IC-first 一次執行之不可變 run context（docs/ICFIRSTALIGN_SPEC.md v17 Task 2.0）。

`run_ic_first` 入口以呼叫參數建立前半（`begin_context`），生成後以生成結果之 metadata 補完並凍結
（`complete_context`），全程只讀之；不讀 factory 之 `_current_output_window`／`_current_config_hash`。
容器欄位深凍結：selection_window、label 規格以 `types.MappingProxyType` 包裝之複本存放，training 以 tuple 存放，
不持有呼叫端可變物件之參照。
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence, Tuple


class ICFirstContextError(ValueError):
    """context 建立失敗：start／end 缺、選窗超出公開窗、生成結果缺 `output_window`（Task 2.0 邊界①②）。"""


class ICFirstGenerationError(RuntimeError):
    """IC-first 之正式生成失敗（含 L6.5 失敗；Task 2.1 邊界①、Task 2.2），不回空表。"""


class PostICArmUnavailableError(RuntimeError):
    """IC-first 之 post-IC 正式臂（Polars）不可用（Task 3.2）。"""


OUTPUT_WINDOW_KEYS: Tuple[str, ...] = ("output_start", "output_end", "ingest_start", "max_warmup_bars", "warmup_enabled")
POST_IC_ARM = "polars"


@dataclass(frozen=True)
class ICFirstRunContext:
    """IC-first 一次執行之身分單一來源（Task 2.0）。生成前之欄位由 `begin_context` 填，
    `output_window`／`config_hash` 由 `complete_context` 自生成結果補完；`complete` 為 True 方可用於 IC。"""

    symbol: str
    timeframe: str
    training: Tuple[str, ...]
    start: str
    end: str
    selection_window: Optional[Mapping[str, Any]]
    split_id: Optional[str]
    label_spec: Mapping[str, Any]
    post_ic_arm: str = POST_IC_ARM
    output_window: Optional[Mapping[str, Any]] = None
    config_hash: Optional[str] = None
    complete: bool = False


def begin_context(
    *,
    symbol: str,
    timeframe: str,
    training: Sequence[str],
    start: Optional[str],
    end: Optional[str],
    selection_window: Optional[Mapping[str, Any]],
    split_id: Optional[str],
    label_spec: Mapping[str, Any],
) -> ICFirstRunContext:
    """以呼叫參數建立 context 前半（深複本凍結）；start／end 缺 ⇒ `ICFirstContextError`。Task 2.0。"""
    raise NotImplementedError("ICFIRSTALIGN Task 2.0")


def complete_context(partial: ICFirstRunContext, generation_metadata: Mapping[str, Any]) -> ICFirstRunContext:
    """以生成結果 metadata 之 `output_window`、`config_hash` 補完並凍結；缺 `output_window` ⇒ `ICFirstContextError`；
    selection_window 超出公開窗 ⇒ `ICFirstContextError`。Task 2.0。"""
    raise NotImplementedError("ICFIRSTALIGN Task 2.0")


def freeze_mapping(value: Optional[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    """dict 之深凍結複本（巢狀 dict ⇒ MappingProxyType、list ⇒ tuple）。Task 2.0。"""
    raise NotImplementedError("ICFIRSTALIGN Task 2.0")


__all__ = [
    "ICFirstContextError",
    "ICFirstGenerationError",
    "PostICArmUnavailableError",
    "ICFirstRunContext",
    "OUTPUT_WINDOW_KEYS",
    "POST_IC_ARM",
    "begin_context",
    "complete_context",
    "freeze_mapping",
    "MappingProxyType",
]
