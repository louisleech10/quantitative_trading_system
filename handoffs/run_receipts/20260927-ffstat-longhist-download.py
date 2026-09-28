"""FF-STAT §G⑦：以既有 K 線下載模組（Binance）抓 12h 全史真實 K 線至獨立快取目錄。

獨立目錄 data_cache/feature_klines_longhist/，不動 data_cache/feature_klines/kline_cache.h5
（既有 golden 與測試依賴其現行範圍）。起點 2017-01-01＝feature_kline_service 之「最早」預設。
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")
from momentum.factories import (  # noqa: E402
    create_binance_provider,
    create_kline_download_service,
    create_kline_storage_manager,
)

OUT_DIR = Path("data_cache/feature_klines_longhist")
import os  # noqa: E402

# 預設三標的；`LONGHIST_SYMBOLS=BCHUSDT` 可只補抓指定標的（2026-09-28 補 BCH 12h：Task 2.1 邊界⑧之 3 標的
# ［cost_measure_symbols］於 12h 需長歷史，承 R8「資料不足以下載模組抓真實資料驗證」）
SYMBOLS = os.environ.get("LONGHIST_SYMBOLS", "BTCUSDT,ETHUSDT,ADAUSDT").split(",")
# 週期 → 起點：12h、1d 取全史（2017-01-01＝最早預設）；5m 取最近一年（倍數量測只需數千根，
# 全史近百萬根用不到）。使用者 2026-09-27 同意（R9）。以命令列參數選週期，預設 12h。
END = datetime.utcnow()
START_BY_TF = {"12h": datetime(2017, 1, 1), "1d": datetime(2017, 1, 1),
               "5m": datetime(END.year - 1, END.month, END.day)}
TIMEFRAMES = sys.argv[1:] or ["12h"]
# 晚上市標的之起點覆寫（BCHUSDT 於 Binance 2019-11 上市；自 2017 起抓首頁為空、下載服務即停止）
if os.environ.get("LONGHIST_START"):
    _start = datetime.strptime(os.environ["LONGHIST_START"], "%Y-%m-%d")
    START_BY_TF = {tf: _start for tf in START_BY_TF}

storage = create_kline_storage_manager(cache_dir=str(OUT_DIR))
svc = create_kline_download_service(storage_manager=storage)
svc.registry.register("binance", create_binance_provider())

end = END
for sym in SYMBOLS:
    for tf in TIMEFRAMES:
        start = START_BY_TF[tf]
        svc.download_klines(source="binance", symbol=sym, timeframe=tf,
                            start_time=start, end_time=end, save_to_storage=True)
        df = storage.read_klines(sym, tf, validate_continuity=False)
        first = datetime.utcfromtimestamp(int(df["timestamp"].iloc[0]))
        last = datetime.utcfromtimestamp(int(df["timestamp"].iloc[-1]))
        print(f"RESULT {sym} {tf} rows={len(df)} first={first:%Y-%m-%d %H:%M} last={last:%Y-%m-%d %H:%M}")
