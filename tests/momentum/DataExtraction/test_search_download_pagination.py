"""/search 下載分頁與並行收集之回歸測試（2026-08-22 UAT B1 實跑病因）。

三條 bug 的可證偽守衛：
1. 分頁推進只加 1 毫秒，但請求時間戳以秒粒度送出 ⇒ 同一根 K 線被重複請求 ⇒ **無窮迴圈**＋重複 append。
2. `future.result()`／`concurrent.futures.as_completed` 在 async 函式內同步阻塞 ⇒ 事件迴圈被鎖死。
3. ProcessPool worker 子進程未掛檔案 handler ⇒ 搜尋期間所有 worker 日誌不進 logs/。

註：本檔以 fake client 驅動（不打 Binance、不碰真實快取）；驗的是**分頁控制流與收集機制**，
非價格數值（數值正確性另由 kline cache 相關測試守）。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from datetime import datetime, timedelta

import pytest

from momentum.DataExtraction import parallel_search_engine as pse
from momentum.DataExtraction.data_loader_momentum import DataLoader

H12_MS = 12 * 3600 * 1000
BASE_MS = 1777291200000        # 2026-04-27 00:00 UTC（UAT 實測卡住的那一根）


class FakeBinanceClient:
    """模擬 Binance：只回「開盤時間 >= startTime 且 <= endTime」的 12h K 線。

    關鍵行為＝**以秒粒度解析 start_str**（真實 client 收 'YYYY-mm-dd HH:MM:SS' 時等價於此），
    因此若呼叫端只把游標推進 1 毫秒，這裡會回同一根 ⇒ 舊碼無限迴圈。
    """

    def __init__(self, n_bars: int = 3):
        self.calls: list[tuple[int, int]] = []
        self.bars = [BASE_MS + i * H12_MS for i in range(n_bars)]

    @staticmethod
    def _to_ms(v) -> int:
        s = str(v)
        if s.isdigit():                                  # epoch ms（修正後的呼叫形式）
            return int(s)
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")   # 秒粒度（舊呼叫形式：毫秒被截掉）
        return int(dt.timestamp() * 1000)

    def get_historical_klines(self, symbol, interval, start_str=None, end_str=None, **kw):
        start_ms, end_ms = self._to_ms(start_str), self._to_ms(end_str)
        self.calls.append((start_ms, end_ms))
        if len(self.calls) > 50:                         # 測試自身的保險絲：真無限迴圈時不吊死 CI
            raise AssertionError(f"下載迴圈未收斂：已請求 {len(self.calls)} 次，最後 window={self.calls[-1]}")
        return [[o, "1", "2", "0.5", "1.5", "10", o + H12_MS - 1, "0", 0, "0", "0", "0"]
                for o in self.bars if start_ms <= o <= end_ms]

    def get_klines(self, **kw):                          # listing-date 探測
        return [[self.bars[0]]]


def _loader_with_fake(client, monkeypatch) -> DataLoader:
    loader = DataLoader.__new__(DataLoader)              # 不跑 __init__（避免真連線／讀設定）
    loader.client = client
    loader.logger = logging.getLogger("momentum.test_loader")
    loader.request_weight = 0
    loader.last_request_time = 0.0
    loader.hdf5_cache_manager = None
    loader._symbols_info_cache = {}
    loader._exchange_info_cache = None
    loader.interval_map = {"12h": "12h", "1h": "1h", "4h": "4h", "1d": "1d"}
    loader._symbol_data_cache = {}
    loader.kline_storage_manager = None
    monkeypatch.setattr(loader, "_check_api_limits", lambda *a, **k: None, raising=False)
    return loader


def test_pagination_terminates_and_has_no_duplicate_bars(monkeypatch):
    """病因①：跨越分頁上限之區間必須結束，且同一根 K 線只出現一次。

    以 max_single_request 縮到 1 逼出「每批只回一根」的最壞情況——正是 UAT 實測卡死的形狀。
    舊碼（+1ms 推進＋秒粒度請求）會反覆請求同一 window，被 FakeBinanceClient 的保險絲判定失敗。
    """
    client = FakeBinanceClient(n_bars=3)
    loader = _loader_with_fake(client, monkeypatch)
    monkeypatch.setattr(loader, "_interval_to_seconds", lambda i: 12 * 3600, raising=False)

    start = datetime.utcfromtimestamp(BASE_MS / 1000)
    end = datetime.utcfromtimestamp((BASE_MS + 2 * H12_MS + H12_MS - 1) / 1000)

    src = inspect.getsource(type(loader).get_historical_klines)
    assert "timedelta(seconds=interval_seconds)" in src, "推進須以整根 bar 為單位（非 1 毫秒）"
    assert "current_start <= previous_start" in src, "須有『未前進即中止』之機械防呆"

    df = loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")

    assert len(client.calls) <= 6, f"請求次數應與批數同量級，得 {len(client.calls)}"
    starts = [c[0] for c in client.calls]
    assert len(set(starts)) == len(starts), f"同一 window 被重複請求（無限迴圈徵兆）：{starts}"
    if df is not None and not df.empty and "timestamp" in df.columns:
        assert df["timestamp"].is_unique, "同一根 K 線被重複 append（資料品質）"


def test_batch_request_sends_millisecond_timestamps(monkeypatch):
    """病因①之根：請求須以 epoch **毫秒**送出；用 strftime 到秒會截掉推進量。"""
    client = FakeBinanceClient()
    loader = _loader_with_fake(client, monkeypatch)
    start = datetime.utcfromtimestamp(BASE_MS / 1000) + timedelta(milliseconds=1)
    loader._fetch_klines_batch("ETHUSDT", start, start + timedelta(hours=12), "12h")
    assert client.calls[0][0] == BASE_MS + 1, f"毫秒被截掉：{client.calls[0][0]}"


def test_result_collection_does_not_block_event_loop():
    """病因②：收集結果期間事件迴圈必須仍可排程其他工作（舊碼 future.result() 會鎖住）。"""
    src = inspect.getsource(pse.ParallelSearchEngine.search_cases_parallel)
    code_only = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    assert "asyncio.wrap_future" in code_only and "asyncio.as_completed" in code_only
    assert "future.result()" not in code_only, "同步 future.result() 會鎖住事件迴圈"

    async def scenario():
        from concurrent.futures import ThreadPoolExecutor
        import time as _t
        ticks = 0
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(_t.sleep, 0.25) for _ in range(2)]

            async def ticker():
                nonlocal ticks
                for _ in range(10):
                    await asyncio.sleep(0.02)
                    ticks += 1

            task = asyncio.ensure_future(ticker())
            for fut in asyncio.as_completed([asyncio.wrap_future(f) for f in futures]):
                await fut
            await task
        return ticks

    assert asyncio.new_event_loop().run_until_complete(scenario()) >= 5, "收集期間事件迴圈被餓死"


def test_worker_file_logging_is_attached_and_idempotent(tmp_path):
    """病因③：worker 子進程須把 momentum 日誌落檔；重複呼叫不重複掛；路徑為 None 不炸。"""
    log_file = tmp_path / "case_search_api_test.log"
    target = logging.getLogger("momentum")
    before = list(target.handlers)
    try:
        pse._init_worker_file_logging(str(log_file))
        pse._init_worker_file_logging(str(log_file))              # idempotent
        added = [h for h in target.handlers if getattr(h, pse._WORKER_LOG_HANDLER_MARKER, False)]
        assert len(added) == 1
        logging.getLogger("momentum.DataExtraction.test").error("worker-error-visible")
        added[0].flush()
        assert "worker-error-visible" in log_file.read_text(encoding="utf-8")
        pse._init_worker_file_logging(None)                        # fail-open
    finally:
        for h in list(target.handlers):
            if getattr(h, pse._WORKER_LOG_HANDLER_MARKER, False):
                target.removeHandler(h)
                h.close()
        target.handlers = before


def test_worker_receives_log_path_from_parent():
    """接線：父進程 submit 時須把 log_path 傳給 worker（否則 handler 永遠掛不上）。"""
    assert "log_path" in inspect.signature(pse._process_chunk_worker).parameters
    src = inspect.getsource(pse.ParallelSearchEngine.search_cases_parallel)
    assert "self._worker_log_path()" in src
    assert "_init_worker_file_logging(log_path)" in inspect.getsource(pse._process_chunk_worker)
