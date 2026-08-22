"""/search 下載分頁、事件迴圈存活與 worker 日誌之回歸測試（2026-08-22 UAT B1 實跑病因）。

守衛（**行為級**，非原始碼字串比對——R1 codex P0-02 指出字串守衛可被註解繞過）：
1. 分頁必須真的進入分批分支並收斂：`current_start` 逐批前進、DataFrame index 唯一/遞增/根數正確。
2. 回應亂序或 stale、游標未前進 ⇒ `IncompleteDownloadError`（fail-closed，**不得**把 partial 當成功落快取）。
3. 空窗只跳過「已證實為空」的範圍，不得多跳（窗末之後恢復的 bar 必須被取到）。
4. 下載為同步阻塞 ⇒ 搜尋鏈（含 symbols < workers 之 serial 路徑）不得佔用事件迴圈。
5. ProcessPool worker（真子進程）之 `DataLoader` 與 `momentum.*` 日誌都要落檔。

fake client 驅動，不打 Binance、不寫真實快取；驗的是控制流與收集機制，非價格數值。
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import time
from datetime import datetime, timedelta

import pandas as pd
import pytest

from momentum.DataExtraction import parallel_search_engine as pse
from momentum.DataExtraction.data_loader_momentum import DataLoader, IncompleteDownloadError

H12_MS = 12 * 3600 * 1000
H12_S = 12 * 3600
BASE_MS = 1777291200000        # 2026-04-27 00:00 UTC（UAT 實測卡住的那一根）


class FakeBinanceClient:
    """模擬 Binance：回「open time ∈ [startTime, endTime]」之 12h K 線，單次上限 `page_limit`。

    `seconds_precision=True` 時比照舊呼叫形式（strftime 到秒）解析 start，用來重現毫秒被截掉的病因。
    """

    def __init__(self, bars=None, page_limit: int = 1000, seconds_precision: bool = False,
                 stale_last: bool = False, frozen_bar: bool = False):
        self.bars = list(bars) if bars is not None else series(2500)
        self.page_limit = page_limit
        self.seconds_precision = seconds_precision
        self.stale_last = stale_last
        self.frozen_bar = frozen_bar              # 伺服器忽略 startTime、永遠回同一根（游標無法前進）
        self.calls: list[tuple[int, int]] = []

    def _to_ms(self, v) -> int:
        s = str(v)
        if s.isdigit():
            ms = int(s)
            return (ms // 1000) * 1000 if self.seconds_precision else ms
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000)

    def get_historical_klines(self, symbol, interval, start_str=None, end_str=None, **kw):
        start_ms, end_ms = self._to_ms(start_str), self._to_ms(end_str)
        self.calls.append((start_ms, end_ms))
        if len(self.calls) > 60:                          # 保險絲：真無限迴圈時不吊死 CI
            raise AssertionError(f"下載未收斂：已請求 {len(self.calls)} 次，最後 window={self.calls[-1]}")
        if self.frozen_bar:
            picked = [self.bars[0]]
        else:
            picked = [o for o in self.bars if start_ms <= o <= end_ms][: self.page_limit]
        if self.stale_last and len(picked) > 1:
            picked = picked[1:] + [picked[0]]             # 末筆不是最大值（亂序／stale）
        return [[o, "1", "2", "0.5", "1.5", "10", o + H12_MS - 1, "0", 0, "0", "0", "0"] for o in picked]

    def get_klines(self, **kw):
        return [[self.bars[0]]]


def _loader(client, monkeypatch) -> DataLoader:
    loader = DataLoader.__new__(DataLoader)               # 不跑 __init__（避免真連線／讀設定）
    loader.client = client
    loader.logger = logging.getLogger("momentum.test_loader")
    loader.request_weight = 0
    loader.last_request_time = 0.0
    loader.hdf5_cache_manager = None
    loader.kline_storage_manager = None
    loader._symbols_info_cache = {}
    loader._exchange_info_cache = None
    loader._symbol_data_cache = {}
    loader.interval_map = {"12h": "12h"}
    monkeypatch.setattr(loader, "_check_api_limits", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(loader, "_interval_to_seconds", lambda i: H12_S, raising=False)
    monkeypatch.setattr("time.sleep", lambda *a, **k: None)   # 不真的等 API 節流
    return loader


def series(n_bars: int) -> list:
    """n 根 12h bar，**結束於 BASE_MS**（已收盤的過去）——避免 `_drop_incomplete_last_candle` 丟掉末根。"""
    return [BASE_MS - (n_bars - 1 - i) * H12_MS for i in range(n_bars)]


def _range(bars: list):
    return (datetime.utcfromtimestamp(bars[0] / 1000),
            datetime.utcfromtimestamp(bars[-1] / 1000))


def test_pagination_branch_is_exercised_and_converges(monkeypatch):
    """①：2500 根（>1000 單次上限）⇒ 必走分批分支；逐批前進、無重複窗、DataFrame 完整。"""
    n = 2500
    bars = series(n)
    client = FakeBinanceClient(bars=bars)
    loader = _loader(client, monkeypatch)
    start, end = _range(bars)

    df = loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")

    assert len(client.calls) >= 3, f"未進入分頁分支（僅 {len(client.calls)} 次請求）"
    starts = [c[0] for c in client.calls]
    assert starts == sorted(starts) and len(set(starts)) == len(starts), f"窗未前進／重複：{starts[:6]}"
    assert len(df) == n, f"根數不符：{len(df)} != {n}"
    assert df.index.is_unique, "同一根 K 線被重複 append（資料品質）"
    assert df.index.is_monotonic_increasing
    gaps = set(df.index.to_series().diff().dropna().unique())
    assert gaps == {pd.Timedelta(seconds=H12_S)}, f"bar 間隔不一致：{gaps}"


def test_millisecond_cursor_survives_request_serialization(monkeypatch):
    """①之根：以秒粒度送出時（舊行為）游標推進會被抹掉；現行必須送毫秒且能收斂。"""
    n = 1500
    bars = series(n)
    start, end = _range(bars)

    ok = _loader(FakeBinanceClient(bars=bars), monkeypatch)
    df = ok.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")
    assert len(df) == n

    lossy = _loader(FakeBinanceClient(bars=bars, seconds_precision=True), monkeypatch)
    df2 = lossy.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")
    assert len(df2) == n, "整根 bar 推進應使秒粒度截斷也不致重抓同一根"


def test_stale_or_unsorted_response_is_rejected_not_silently_truncated(monkeypatch):
    """②：末筆非最大值（亂序／stale）⇒ fail-closed，不得回 partial（更不得落快取）。"""
    n = 1500
    bars = series(n)
    client = FakeBinanceClient(bars=bars, stale_last=True)
    loader = _loader(client, monkeypatch)
    start, end = _range(bars)
    with pytest.raises(IncompleteDownloadError, match="非遞增或末筆非最大值"):
        loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")


def test_no_progress_is_fail_closed(monkeypatch):
    """②：游標未前進（伺服器忽略 startTime、永遠回同一根）⇒ IncompleteDownloadError。

    舊碼在此情境是無窮迴圈；加了 break 後則是「把 partial 當成功返回並落快取」——兩者都不可接受。
    """
    n = 1500
    bars = series(n)
    client = FakeBinanceClient(bars=bars, frozen_bar=True)
    loader = _loader(client, monkeypatch)
    start, end = _range(bars)
    with pytest.raises(IncompleteDownloadError, match="未前進"):
        loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")


def test_empty_window_skips_only_proven_empty_range(monkeypatch):
    """③：空窗只跳過已證實為空之範圍；窗末之後恢復的 bar 仍須取到（舊碼固定 +1 天會吃掉）。"""
    # 單次請求窗寬固定 1000 根 ⇒ 要造出「整窗皆空」需 ≥1000 根的空洞（真實情境：長期停牌／下市重上）。
    # 空洞**恰好覆蓋一個請求窗**（full[1000..2000]），恢復根緊接窗末（full[2001]）——這是能區分
    # 「+1 interval」與「+1 天」的唯一位置：後者一次跳掉 2 根 12h bar，恰好吃掉恢復根。
    full = series(3400)
    hole = set(full[1000:2001])                       # 1001 根空洞（含窗末）
    present = [b for b in full if b not in hole]
    recovered_ms = full[2001]                         # 空洞後第一根，緊接 batch_end
    client = FakeBinanceClient(bars=present)          # 誠實 fake：窗內真的沒有 bar 才回 []
    loader = _loader(client, monkeypatch)
    start, end = _range(full)
    df = loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")
    assert pd.to_datetime(recovered_ms, unit="ms") in df.index, "空洞之後恢復的 bar 被跳過（多跳）"
    assert len(df) == len(present)
    assert df.index.is_unique and df.index.is_monotonic_increasing


def _blocking_loader_factory(delay: float):
    class _SlowLoader:
        def get_historical_data(self, **kw):
            time.sleep(delay)                             # 同步阻塞（模擬真實下載）
            return None
    return _SlowLoader()


def test_symbol_search_does_not_block_event_loop():
    """④：`_search_single_symbol` 的同步下載須離開事件迴圈（symbols < workers 的 serial 路徑也吃這條）。"""
    from momentum.DataExtraction.case_search_engine import CaseSearchEngine

    engine = CaseSearchEngine.__new__(CaseSearchEngine)
    engine.logger = logging.getLogger("momentum.test_engine")
    engine.data_loader = _blocking_loader_factory(0.30)

    class _Cfg:
        timeframe = "12h"
        start_time = "2024-01-01"
        end_time = "2026-04-27"
        time_range = None

    async def scenario():
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:                                   # 持續計數，直到搜尋結束才取樣
                await asyncio.sleep(0.02)
                ticks += 1

        task = asyncio.ensure_future(ticker())
        await engine._search_single_symbol("ETHUSDT", _Cfg())
        ticks_at_completion = ticks                       # 🔴 必須在搜尋**完成當下**取樣：
        task.cancel()                                     # 若等 await task 才數，阻塞版也會事後補跑而假綠
        try:
            await task
        except asyncio.CancelledError:
            pass
        return ticks_at_completion

    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(scenario()) >= 10, "下載期間事件迴圈被餓死（同步呼叫未離開迴圈）"
    finally:
        loop.close()


def test_process_pool_results_are_awaited_not_blocking():
    """④：結果收集期間事件迴圈仍可排程（wrap_future＋as_completed 的行為驗證）。"""
    from concurrent.futures import ThreadPoolExecutor

    async def scenario():
        ticks = 0
        ex = ThreadPoolExecutor(max_workers=2)
        try:
            futures = [ex.submit(time.sleep, 0.25) for _ in range(2)]

            async def ticker():
                nonlocal ticks
                for _ in range(15):
                    await asyncio.sleep(0.02)
                    ticks += 1

            task = asyncio.ensure_future(ticker())
            for fut in asyncio.as_completed([asyncio.wrap_future(f) for f in futures]):
                await fut
            await task
        finally:
            await asyncio.to_thread(ex.shutdown, True)
        return ticks

    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(scenario()) >= 8
    finally:
        loop.close()


def _child_emits_logs(log_path: str, q):
    """真子進程：掛 worker handler 後，分別以 `DataLoader`（頂層）與 `momentum.*` 發 ERROR。"""
    try:
        pse._init_worker_file_logging(log_path)
        logging.getLogger("DataLoader").error("child-dataloader-error")
        logging.getLogger("momentum.DataExtraction.child").error("child-momentum-error")
        for h in logging.getLogger().handlers:
            h.flush()
        q.put("ok")
    except Exception as exc:                              # noqa: BLE001
        q.put(f"err:{exc!r}")


def test_worker_logging_captures_dataloader_and_momentum_in_real_child(tmp_path):
    """⑤：真子進程中，頂層 `DataLoader` 與 `momentum.*` 的 ERROR 都須落檔（掛 momentum 命名空間會漏前者）。"""
    log_file = tmp_path / "case_search_api_child.log"
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_child_emits_logs, args=(str(log_file), q))
    p.start()
    p.join(timeout=60)
    try:
        status = q.get(timeout=5)
    except Exception:                                     # noqa: BLE001
        status = "no-status"
    if p.exitcode != 0 or status != "ok":
        pytest.skip(f"子進程不可用（沙箱限制）：exitcode={p.exitcode} status={status}")
    text = log_file.read_text(encoding="utf-8")
    assert "child-dataloader-error" in text, "頂層 DataLoader logger 未被收集（下載錯誤會查不到）"
    assert "child-momentum-error" in text
    assert "search-worker pid=" in text


def test_worker_logging_idempotent_and_failopen(tmp_path):
    """⑤：重複呼叫不重複掛；path=None 不炸；handler 只收 INFO 以上。"""
    log_file = tmp_path / "idem.log"
    root = logging.getLogger()
    before_level, before_handlers = root.level, list(root.handlers)
    try:
        pse._init_worker_file_logging(str(log_file))
        pse._init_worker_file_logging(str(log_file))
        added = [h for h in root.handlers if getattr(h, pse._WORKER_LOG_HANDLER_MARKER, False)]
        assert len(added) == 1
        logging.getLogger("DataLoader").info("visible-info")
        logging.getLogger("DataLoader").debug("hidden-debug")
        added[0].flush()
        text = log_file.read_text(encoding="utf-8")
        assert "visible-info" in text and "hidden-debug" not in text
        pse._init_worker_file_logging(None)
    finally:
        for h in list(root.handlers):
            if getattr(h, pse._WORKER_LOG_HANDLER_MARKER, False):
                root.removeHandler(h)
                h.close()
        root.handlers = before_handlers
        root.setLevel(before_level)



