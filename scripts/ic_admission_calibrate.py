"""IC 准入估算器校準之薄量測入口（ICPERF SPEC v5.87 Task 0.6 (h)「⑤ IC 分析啟動准入」；諮詢 r165 收斂檔 C4）。

空殼（L1b 施工清單階段）。施工批實作：以完整請求（可選模組、full-analysis、事件）於新行程跑 IC 分析至真實終態，
全程取樣 Physical footprint（與 scripts/measure_ic_footprint.sh 同一工具），無採樣截止、不以 RAM 比例殺行程
（容量保護沿產品正式預算）；成功終態才計校準／驗證點，被守護停止、失敗、取消者標 censored／failed；
經 scripts/run_watched.py 背景執行並附估時收據。
"""
from __future__ import annotations

import sys


def main(argv: list) -> int:
    raise NotImplementedError("ICPERF Task 0.6 L1b 施工批實作")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
