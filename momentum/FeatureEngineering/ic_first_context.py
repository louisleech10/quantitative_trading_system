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
    if start in (None, "") or end in (None, ""):
        raise ICFirstContextError(f"IC-first 須帶 start 與 end（{symbol}/{timeframe}）：start={start!r} end={end!r}")
    return ICFirstRunContext(
        symbol=str(symbol),
        timeframe=str(timeframe),
        training=tuple(str(tf) for tf in training),
        start=str(start),
        end=str(end),
        selection_window=freeze_mapping(selection_window),
        split_id=None if split_id is None else str(split_id),
        label_spec=freeze_mapping(label_spec) or MappingProxyType({}),
    )


def _as_timestamp(value: Any) -> Any:
    import pandas as pd

    ts = pd.Timestamp(value)
    return ts.tz_convert("UTC").tz_localize(None) if ts.tzinfo is not None else ts


def complete_context(partial: ICFirstRunContext, generation_metadata: Mapping[str, Any]) -> ICFirstRunContext:
    """以生成結果 metadata 之 `output_window`、`config_hash` 補完並凍結；缺 `output_window` ⇒ `ICFirstContextError`；
    selection_window 超出公開窗 ⇒ `ICFirstContextError`。Task 2.0。"""
    from dataclasses import replace

    window = generation_metadata.get("output_window") if generation_metadata else None
    if not window or any(key not in window for key in OUTPUT_WINDOW_KEYS):
        raise ICFirstContextError(
            f"生成結果缺 output_window（或缺欄 {OUTPUT_WINDOW_KEYS}）；IC-first 之窗只取自本次生成結果"
        )
    config_hash = generation_metadata.get("config_hash")
    if not config_hash:
        raise ICFirstContextError("生成結果缺 config_hash；IC-first 之身分只取自本次生成結果")
    selection = partial.selection_window
    if selection:
        out_start = window.get("output_start")
        out_end = window.get("output_end")
        sel_start = selection.get("start")
        sel_end = selection.get("end")
        if sel_start is not None and out_start is not None and _as_timestamp(sel_start) < _as_timestamp(out_start):
            raise ICFirstContextError(f"selection_window 起 {sel_start} 早於公開窗起 {out_start}")
        if sel_end is not None and out_end is not None and _as_timestamp(sel_end) > _as_timestamp(out_end):
            raise ICFirstContextError(f"selection_window 訖 {sel_end} 晚於公開窗訖 {out_end}")
    return replace(partial, output_window=freeze_mapping(dict(window)), config_hash=str(config_hash), complete=True)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_freeze(v) for v in value)
    return value


def freeze_mapping(value: Optional[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    """dict 之深凍結複本（巢狀 dict ⇒ MappingProxyType、list ⇒ tuple）。Task 2.0。"""
    if value is None:
        return None
    return _freeze(dict(value))


def context_to_metadata(ctx: ICFirstRunContext) -> Mapping[str, Any]:
    """context 之可序列化快照（寫入生成結果 metadata["ic_first_context"]；容器還原為 dict／list 複本）。"""
    def thaw(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {k: thaw(v) for k, v in value.items()}
        if isinstance(value, (tuple, frozenset)):
            return [thaw(v) for v in value]
        return value

    return {
        "symbol": ctx.symbol, "timeframe": ctx.timeframe, "training": list(ctx.training),
        "start": ctx.start, "end": ctx.end, "selection_window": thaw(ctx.selection_window),
        "split_id": ctx.split_id, "label_spec": thaw(ctx.label_spec), "post_ic_arm": ctx.post_ic_arm,
        "output_window": thaw(ctx.output_window), "config_hash": ctx.config_hash, "complete": ctx.complete,
    }


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
    "context_to_metadata",
    "MappingProxyType",
]
