"""NOCAP Task 0.3b（docs/NOCAP_SPEC.md）：全規模重型跑前之成長曲線——同一入口、同一真實資料取 ≥ 3 個規模點
（`--scale` 明列，每點經共用監看各自啟動），擬合冪次並保守推算全規模，寫 `handoffs/run_receipts/<日期>-<目標>-scale.json`。

起始例外：本腳本列 `heavy_commands.json` 之 `self_watched`（須背景、原始碼須呼叫共用監看），但不要求其自身之成長曲線或估時收據。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

MIN_POINTS = 3
MIN_R2 = 0.9
SUPERLINEAR_EXPONENT = 1.2


def fit(points: Sequence[Mapping[str, Any]], full_scale: float) -> Dict[str, Any]:
    """`points` 每點 {scale, unit, seconds, peak_rss_bytes}。回 {fit: {model, exponent, r2}, projection: {scale, seconds,
    peak_rss_bytes}, superlinear, extrapolation_unreliable, reasons}；`projection` 取冪次推算與末兩點線性外推之較大者；
    點數 < 3、r2 < 0.9、耗時或 RSS 隨規模遞減任一成立 ⇒ `extrapolation_unreliable` 為 True。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def run_watched(cmd: Sequence[str], **kwargs: Any) -> Any:
    """以共用監看（`handoffs/run_receipts/numview_probes/_watchdog.py`）啟動一個規模點。"""
    raise NotImplementedError("NOCAP Task 0.3b")


def main(argv: Optional[Sequence[str]] = None) -> int:
    raise NotImplementedError("NOCAP Task 0.3b")


if __name__ == "__main__":
    raise SystemExit(main())
