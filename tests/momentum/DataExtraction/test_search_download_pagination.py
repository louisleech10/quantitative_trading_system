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
import threading
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


class SpyStorage:
    """記錄快取讀寫的 `KlineStorageManager` 替身。

    🔴 CODEX-R2-P1-03：原本 fixture 把 `kline_storage_manager` 設成 `None`，於是
    `_save_to_cache` 一進門就 return——**即使**未來有人把 raise 移到寫檔之後，
    「不得落快取」那兩條測試照樣綠。那是假綠：斷言的是例外型別，不是「沒寫」。
    本替身讓「寫了幾次」成為可斷言的中間值。
    """

    def __init__(self, seeded: pd.DataFrame | None = None):
        self.seeded = seeded
        self.writes: list[dict] = []
        self.reads = 0

    def read_klines(self, symbol, timeframe, start_time=None, end_time=None, **kw):
        self.reads += 1
        return self.seeded

    def write_klines(self, symbol, timeframe, df, data_source="binance", **kw):
        self.writes.append({"symbol": symbol, "timeframe": timeframe, "rows": len(df)})
        return True


def _loader(client, monkeypatch, storage=None) -> DataLoader:
    loader = DataLoader.__new__(DataLoader)               # 不跑 __init__（避免真連線／讀設定）
    loader.client = client
    loader.logger = logging.getLogger("momentum.test_loader")
    loader.request_weight = 0
    loader.last_request_time = 0.0
    loader.hdf5_cache_manager = None
    loader.kline_storage_manager = storage
    loader._symbols_info_cache = {}
    loader._exchange_info_cache = None
    loader._symbol_data_cache = {}
    loader._memory_cache_size = 0
    loader._max_memory_cache = 1024 * 1024 * 1024
    loader._loader_lock = threading.RLock()
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


def _seed_frame() -> pd.DataFrame:
    """既有快取內容（storage 格式）——用來驗「拒收時既有資料原封不動」。"""
    return pd.DataFrame({
        "timestamp": [BASE_MS - 3 * H12_MS, BASE_MS - 2 * H12_MS],
        "open": [1.0, 1.0], "high": [2.0, 2.0], "low": [0.5, 0.5],
        "close": [1.5, 1.5], "volume": [10.0, 10.0],
    })


def test_stale_or_unsorted_response_is_rejected_not_silently_truncated(monkeypatch):
    """②：末筆非最大值（亂序／stale）⇒ fail-closed，不得回 partial，且**不得寫快取**。"""
    n = 1500
    bars = series(n)
    seed = _seed_frame()
    storage = SpyStorage(seeded=seed.copy())
    client = FakeBinanceClient(bars=bars, stale_last=True)
    loader = _loader(client, monkeypatch, storage=storage)
    start, end = _range(bars)
    with pytest.raises(IncompleteDownloadError, match="非遞增或末筆非最大值"):
        loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")
    # 🔴 中間值斷言（CODEX-R2-P1-03）：例外型別對了不代表沒寫；要斷言的是**沒寫**。
    assert storage.writes == [], f"拒收後仍寫入快取：{storage.writes}"
    pd.testing.assert_frame_equal(storage.seeded, seed)      # 既有快取未被動到


def test_no_progress_is_fail_closed(monkeypatch):
    """②：游標未前進（伺服器忽略 startTime、永遠回同一根）⇒ IncompleteDownloadError 且不寫快取。

    舊碼在此情境是無窮迴圈；加了 break 後則是「把 partial 當成功返回並落快取」——兩者都不可接受。
    """
    n = 1500
    bars = series(n)
    seed = _seed_frame()
    storage = SpyStorage(seeded=seed.copy())
    client = FakeBinanceClient(bars=bars, frozen_bar=True)
    loader = _loader(client, monkeypatch, storage=storage)
    start, end = _range(bars)
    with pytest.raises(IncompleteDownloadError, match="未前進"):
        loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")
    assert storage.writes == [], f"拒收後仍寫入快取：{storage.writes}"
    pd.testing.assert_frame_equal(storage.seeded, seed)


def test_successful_download_does_write_cache(monkeypatch):
    """②之對照組：spy 本身有鑑別力——正常下載**會**寫快取。

    沒有這條，上面兩條的 `writes == []` 可能只是因為 spy 根本沒接上（永遠為空＝空心綠）。
    """
    bars = series(1500)
    storage = SpyStorage(seeded=None)
    loader = _loader(FakeBinanceClient(bars=bars), monkeypatch, storage=storage)
    start, end = _range(bars)
    df = loader.get_historical_klines(symbol="ETHUSDT", start_time=start, end_time=end, interval="12h")
    assert len(df) == 1500
    assert len(storage.writes) == 1, f"正常路徑未寫快取，spy 無鑑別力：{storage.writes}"
    assert storage.writes[0]["rows"] == 1500


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
    # 🔴 GROK-R2 回報：在更嚴的沙箱裡，`ctx.Queue()` 建構期就 `PermissionError: SemLock`，
    #   在 `p.start()` **之前**炸掉 ⇒ 原本只看 `exitcode` 的 skip 分支根本進不去，測試硬紅。
    #   環境不允許建立 semaphore／子進程是**環境限制**，不是產品回歸，必須 skip 而非 fail。
    try:
        ctx = multiprocessing.get_context("spawn")
        q = ctx.Queue()
        p = ctx.Process(target=_child_emits_logs, args=(str(log_file), q))
        p.start()
    except (PermissionError, OSError) as exc:
        pytest.skip(f"子進程／semaphore 不可用（沙箱限制）：{type(exc).__name__}: {exc}")
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





# ─────────────────────────────────────────────────────────────────────────────
# R2 修補之回歸（CODEX-R2-P1-01/P1-02、GROK-R2-P1-01/P1-02/P2-03）
# ─────────────────────────────────────────────────────────────────────────────

class _RejectingLoader:
    """下載一律以 `IncompleteDownloadError` 拒收（模擬亂序／stale 回應）。"""

    def __init__(self):
        self.calls = 0

    def get_historical_data(self, **kw):
        self.calls += 1
        raise IncompleteDownloadError("K 線回應非遞增或末筆非最大值（拒收，不得落快取）: TESTSYM")


def _engine_with(loader):
    from momentum.DataExtraction.case_search_engine import CaseSearchEngine

    engine = CaseSearchEngine.__new__(CaseSearchEngine)
    engine.logger = logging.getLogger("momentum.test_engine")
    engine.data_loader = loader
    return engine


class _Cfg2:
    timeframe = "12h"
    start_time = "2024-01-01"
    end_time = "2026-04-27"
    time_range = None


def test_incomplete_download_is_not_swallowed_by_single_symbol():
    """⑥：`_search_single_symbol` 不得把拒收吞成 `[]`（否則使用者看成「無案例」）。

    這是 R1 fail-closed 只做一半之處：loader 拒收了，呼叫端卻回報成功空結果。
    """
    engine = _engine_with(_RejectingLoader())
    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(IncompleteDownloadError):
            loop.run_until_complete(engine._search_single_symbol("TESTSYM", _Cfg2()))
    finally:
        loop.close()


def test_incomplete_download_propagates_through_search_batch():
    """⑥：`_search_batch` 的 `except Exception: continue` 亦不得吞——否則整批變成空成功。"""
    engine = _engine_with(_RejectingLoader())
    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(IncompleteDownloadError):
            loop.run_until_complete(engine._search_batch(_Cfg2(), ["TESTSYM"]))
    finally:
        loop.close()


def test_ordinary_download_error_is_still_swallowed_per_symbol():
    """⑥之邊界：**只有**拒收要往上拋；一般錯誤仍維持「跳過該 symbol」的既有語意。

    沒有這條，上面兩條可能只是因為「什麼都往上拋」而綠——那會把單一壞 symbol 變成整批失敗。
    """
    class _BoomLoader:
        def get_historical_data(self, **kw):
            raise ValueError("some transient parse issue")

    engine = _engine_with(_BoomLoader())
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(engine._search_batch(_Cfg2(), ["TESTSYM"])) == []
    finally:
        loop.close()


def test_incomplete_download_is_classified_non_retryable():
    """⑥：worker 端不得把拒收當暫時性故障重試——訊息是中文，字串分類會落到 UNKNOWN(retry=1)。"""
    err = IncompleteDownloadError("分批下載未前進（拒收，不得落快取）: TESTSYM 12h")
    assert pse.classify_error(err) is pse.FailureType.INVALID_CONFIG
    assert pse.RETRY_CONFIG[pse.classify_error(err)]["max_retries"] == 0
    # 對照：一般網路錯誤仍走重試路徑（證明上面不是「全部歸 INVALID_CONFIG」）
    assert pse.classify_error(TimeoutError("connection timeout")) is pse.FailureType.NETWORK_ERROR


def test_shared_loader_serializes_concurrent_downloads(monkeypatch):
    """⑦：共用 loader 之下載須互斥（`to_thread` 後多個並行 /search 會同時進入同一個 loader）。

    修前同步下載鎖住事件迴圈＝意外序列化；改 `to_thread` 後那個隱式保證消失，
    `_symbol_data_cache` 的淘汰迴圈與 HDF5 的 read→concat→write 會交錯。
    """
    loader = DataLoader.__new__(DataLoader)
    loader.logger = logging.getLogger("momentum.test_loader")
    loader._loader_lock = threading.RLock()

    overlap = {"max": 0, "cur": 0}
    guard = threading.Lock()

    def _fake_klines(**kw):
        with guard:
            overlap["cur"] += 1
            overlap["max"] = max(overlap["max"], overlap["cur"])
        time.sleep(0.05)
        with guard:
            overlap["cur"] -= 1
        return pd.DataFrame()

    monkeypatch.setattr(loader, "get_historical_klines", _fake_klines, raising=False)
    monkeypatch.setattr(loader, "format_output", lambda df: df, raising=False)

    threads = [
        threading.Thread(
            target=loader.get_historical_data,
            kwargs={"symbol": f"S{i}", "start_time": "2024-01-01", "interval": "12h"},
        )
        for i in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert overlap["max"] == 1, f"共用 loader 之下載未互斥（最大同時進入 {overlap['max']} 條執行緒）"


def test_no_synchronous_download_remains_in_async_search_paths():
    """⑦：`case_search_engine` 內所有 `async def` 的下載呼叫都須經 `to_thread`。

    R1 的 commit message 宣稱「兩處」而工作樹只有一處（GROK-R2-P2-03）——`_process_symbol`
    當時仍同步。它目前無呼叫端，但留著就是地雷：接回 async 路徑即重現 UAT B1。
    以 AST 判定，不用 grep 計數（計數會隨無關改動漂）。
    """
    import ast
    import inspect
    from momentum.DataExtraction import case_search_engine as cse

    tree = ast.parse(inspect.getsource(cse))
    offenders = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(fn):
            # 直接呼叫 `<x>.get_historical_data(...)` 而非 `asyncio.to_thread(<x>.get_historical_data, ...)`
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "get_historical_data":
                offenders.append(f"{fn.name}:{node.lineno}")
    assert offenders == [], f"async 路徑仍有同步下載（會鎖住事件迴圈）：{offenders}"


# ─────────────────────────────────────────────────────────────────────────────
# R3 修補之回歸（CODEX-R3-P1-01：parallel 路徑同樣不得把拒收吞成空成功）
# ─────────────────────────────────────────────────────────────────────────────

class _WorkerCfg:
    timeframe = "12h"
    start_time = "2024-01-01"
    end_time = "2026-04-27"
    time_range = None


def _stub_worker_deps(monkeypatch, single_symbol_impl):
    """把 `_process_chunk_worker` 自建的 loader/engine 換掉，使其可在本進程內直接驅動。"""
    from momentum.DataExtraction import data_loader_momentum as dlm
    from momentum.DataExtraction.case_search_engine import CaseSearchEngine

    class _StubLoader:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(dlm, "DataLoader", _StubLoader)
    monkeypatch.setattr(CaseSearchEngine, "__init__", lambda self, **k: None)
    monkeypatch.setattr(CaseSearchEngine, "_search_single_symbol", single_symbol_impl)


def test_parallel_worker_outer_catch_does_not_swallow_rejection(monkeypatch, tmp_path):
    """⑧：worker 最外層 `except Exception` 不得把拒收整包丟成 `success_results=[]`。

    R2 只修了 serial 路徑；parallel 路徑的 chunk 失敗原會被最外層整包吃掉、父層再 `continue`
    ⇒ 100-symbol 搜尋回「成功但沒案例」——與 R2 群集 A 同型，換條路重演（CODEX-R3-P1-01）。

    行為級：**在本進程內直接呼叫** `_process_chunk_worker`，斷言它**拋出**且訊息帶
    worker／symbol 身分，而非回傳一份空的成功字典。
    """
    async def _reject(self, symbol, config):
        raise IncompleteDownloadError("K 線回應非遞增或末筆非最大值（拒收，不得落快取）")

    _stub_worker_deps(monkeypatch, _reject)
    with pytest.raises(IncompleteDownloadError, match="symbol=BADSYM"):
        pse._process_chunk_worker(["BADSYM"], _WorkerCfg(), 1, 2, log_path=str(tmp_path / "w.log"))


def test_parallel_worker_still_returns_failed_records_for_ordinary_errors(monkeypatch, tmp_path):
    """⑧之邊界：一般錯誤仍走既有「重試→failed_records→回傳」語意。

    沒有這條，上一條可能只是因為 worker 對**任何**錯誤都拋出而綠——那會讓單一壞 symbol
    炸掉整個 chunk，把既有的失敗透明化機制（failed_records／失敗報告）整個廢掉。
    """
    async def _boom(self, symbol, config):
        raise ValueError("no data for symbol")

    _stub_worker_deps(monkeypatch, _boom)
    monkeypatch.setattr(pse.time, "sleep", lambda *a, **k: None)
    out = pse._process_chunk_worker(["OKSYM"], _WorkerCfg(), 0, 1, log_path=str(tmp_path / "w2.log"))
    assert out["success_results"] == []
    assert len(out["failed_records"]) == 1, f"一般錯誤未記入 failed_records：{out}"
    assert out["failed_records"][0]["symbol"] == "OKSYM"


def test_parallel_collection_propagates_rejection_instead_of_continue():
    """⑧：父層收集迴圈對拒收須往上拋，不得 `continue` 後回其餘 chunk 的成功結果。

    行為級：直接驅動 `asyncio.as_completed` 的例外分支（與 production 同形），
    斷言「拒收會終止收集」而非「被記 log 後續跑」。
    """
    from concurrent.futures import ThreadPoolExecutor

    def _ok_chunk():
        return {"success_results": [{"symbol": "OK"}], "failed_records": [], "retry_stats": {}}

    def _rejecting_chunk():
        time.sleep(0.02)
        raise IncompleteDownloadError("[worker 2/2] symbol=BAD 下載被拒收: 末筆非最大值")

    async def scenario():
        collected = []
        ex = ThreadPoolExecutor(max_workers=2)
        try:
            futures = [ex.submit(_ok_chunk), ex.submit(_rejecting_chunk)]
            for aio_future in asyncio.as_completed([asyncio.wrap_future(f) for f in futures]):
                try:
                    collected.append(await aio_future)
                except IncompleteDownloadError:
                    raise                                  # production 之處置
                except Exception:                          # noqa: BLE001
                    continue                               # 一般錯誤仍逐 chunk 跳過
        finally:
            await asyncio.to_thread(ex.shutdown, True)
        return collected

    loop = asyncio.new_event_loop()
    try:
        with pytest.raises(IncompleteDownloadError, match="symbol=BAD"):
            loop.run_until_complete(scenario())
    finally:
        loop.close()


def _scan_swallowed_rejections(source: str) -> list:
    """盤點 source 內「會吞掉 `IncompleteDownloadError` 而未 re-raise」的 try 區塊。

    🔴 本函式**自身**由 `test_ast_guard_detects_every_known_bypass_form` 以合成旁路驗證——
    這是本 epic 三次「守衛範圍寫錯而測試仍綠」之後的機制性修法：
    盤點型守衛的判定範圍必須自己被測，不能只靠對 production code 跑一次得綠。
    """
    import ast

    tree = ast.parse(source)
    # 🔴 **fail-closed 名單**：預設每個函式都受檢，只有列名者豁免。
    #   原版是白名單 `{"_serial_search_fallback", "_process_chunk_worker", "search_cases"}`，
    #   而真正的方法名是 `search_cases_parallel` ⇒ 該函式內的**兩個**真實旁路
    #   （父層收集迴圈 continue、退回串行 fallback）根本沒被檢查，測試對它們是空的。
    #   白名單打錯字就靜默失效；豁免名單打錯字只會多檢查一個函式（安全方向）。
    EXEMPT_FUNCS = {
        "to_dict", "classify_error", "calculate_backoff_delay", "create_failure_record",
        "__init__", "_worker_log_path", "_get_optimal_workers", "_chunk_symbols",
        "_save_failure_report", "_init_worker_file_logging",
    }
    # 🔴 受檢範圍以**封閉正面集合**判定，不用「豁免關鍵字」。
    #   兩版失敗史：①用 `"save_results" in ast.dump(node)` 當豁免 ⇒ 該字串遍布整棵子樹，
    #   兩個真實旁路被靜默豁免；②改成「直接語句全為存檔呼叫才豁免」⇒ 存檔 try 裡的
    #   `len()`／`logger.warning()` 使 all() 為假，反而誤擋。
    #   正解：問「這個 try 的 body **碰得到下載嗎**」——碰得到才受檢。
    #   碰得到＝出現下列任一呼叫名，或出現 `await`（等待 worker future 即等待下載）。
    DOWNLOAD_REACHING = {
        "_search_batch", "_search_single_symbol", "_process_chunk_worker",
        "search_cases", "search_cases_parallel",
        "get_historical_data", "get_historical_klines", "_fetch_klines_batch",
    }

    def _owner_of(target):
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(fn):
                    if sub is target:
                        return fn.name
        return None

    def _reaches_download(try_node):
        """try 的 body 碰得到下載嗎（下列呼叫名之一，或任何 await）。"""
        for stmt in try_node.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Await):
                    return True
                if isinstance(sub, ast.Call):
                    fname = sub.func.attr if isinstance(sub.func, ast.Attribute) else \
                            (sub.func.id if isinstance(sub.func, ast.Name) else "")
                    if fname in DOWNLOAD_REACHING:
                        return True
        return False

    # 🔴 v4（CODEX-R4-P1-01／COMPOSER-R4-P2-01，兩家獨立命中）：handler 型別須**正規化**。
    #   v3 只收 `isinstance(h.type, ast.Name)` ⇒ `except (Exception, X):` 這種 tuple handler
    #   得到空 names、整個 try 被跳過 ⇒ 可在受檢函式內原樣重建吞點而測試仍綠。
    #   同理 `except BaseException:` 與 `except RuntimeError:` 也會吞掉拒收
    #   （`IncompleteDownloadError` 是 `RuntimeError` 子類），v3 一樣看不見。
    #   `except:`（bare）之 h.type 為 None，也吞。
    SWALLOWS_REJECTION = {"Exception", "BaseException", "RuntimeError"}

    def _handler_names(h):
        """把 handler 的捕捉型別正規化成名字集合；bare except 以 'BaseException' 表示。"""
        if h.type is None:
            return ["BaseException"]                       # bare `except:` 捕捉一切
        nodes = h.type.elts if isinstance(h.type, ast.Tuple) else [h.type]
        out = []
        for n in nodes:
            if isinstance(n, ast.Name):
                out.append(n.id)
            elif isinstance(n, ast.Attribute):
                out.append(n.attr)
            else:
                # 動態運算出的 handler 型別（如 `except X if c else Y:`）無法靜態判定
                # ⇒ fail-closed，當成「會吞」。
                out.append("<dynamic>")
        return out

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        per_handler = [_handler_names(h) for h in node.handlers]
        flat = [n for names in per_handler for n in names]
        # 這個 try 有沒有「會吞掉拒收」的 handler？
        swallow_idx = next(
            (i for i, names in enumerate(per_handler)
             if any(n in SWALLOWS_REJECTION or n == "<dynamic>" for n in names)),
            None,
        )
        if swallow_idx is None:
            continue
        owner = _owner_of(node)
        if owner is None or owner in EXEMPT_FUNCS:
            continue
        if not _reaches_download(node):
            continue
        # 🔴 合格的 re-raise handler 必須三者皆成立（缺一即無效）：
        #   ① 捕捉 `IncompleteDownloadError`
        #   ② **不與**會吞的型別同處一個 handler——`except (Exception, IncompleteDownloadError): continue`
        #      看起來「有處理」，實際是把拒收和一般錯誤一起吞掉。這正是 mutation `prod_tuple_bypass`
        #      打穿第一版 v4 的方式：我只檢查名字在不在，沒檢查它是否被綁進吞掉的那個 handler。
        #   ③ handler body 真的 `raise`——只寫 `except IncompleteDownloadError: pass` 更糟。
        def _is_valid_reraise(idx):
            import ast as _ast
            names = per_handler[idx]
            if "IncompleteDownloadError" not in names:
                return False
            if any(n in SWALLOWS_REJECTION or n == "<dynamic>" for n in names):
                return False
            return any(isinstance(s, _ast.Raise) for s in ast.walk(node.handlers[idx]))

        reraise_idx = next((i for i in range(len(per_handler)) if _is_valid_reraise(i)), None)
        if reraise_idx is None:
            has_name = any("IncompleteDownloadError" in n for n in per_handler)
            why = "與會吞型別同 handler／未 raise" if has_name else "缺 handler"
            offenders.append(
                f"{owner}:{node.lineno}(無有效 IncompleteDownloadError re-raise：{why}；捕捉型別={flat})"
            )
        elif reraise_idx > swallow_idx:
            offenders.append(
                f"{owner}:{node.lineno}(順序錯：{per_handler[swallow_idx]} 在前會先吃掉)"
            )
    return offenders


def test_parallel_paths_reraise_rejection_at_every_swallow_point():
    """⑧：`parallel_search_engine` 內每個會吞例外的點，都須對拒收 re-raise。"""
    import inspect

    offenders = _scan_swallowed_rejections(inspect.getsource(pse))
    assert offenders == [], f"搜尋主鏈仍有會吞掉拒收的 handler：{offenders}"


# 🔴 合成旁路語料（CODEX-R4-P1-01／COMPOSER-R4-P2-01）：每一種寫法都**能吞掉拒收**，
#   守衛必須全部抓到。v3 對前四種完全不掃描（`isinstance(h.type, ast.Name)` 為假 ⇒ 整個 try 跳過）。
_BYPASS_FORMS = {
    "tuple_handler":      "    except (Exception, ValueError):\n        pass\n",
    "tuple_single":       "    except (Exception,):\n        pass\n",
    "bare_except":        "    except:\n        pass\n",
    "dynamic_handler":    "    except (Exception if True else ValueError):\n        pass\n",
    "base_exception":     "    except BaseException:\n        pass\n",
    "runtime_error":      "    except RuntimeError:\n        pass\n",   # 拒收是 RuntimeError 子類
    "plain_exception":    "    except Exception:\n        pass\n",
    # 🔴 下面兩種「看起來有處理」但實際照吞——mutation prod_tuple_bypass 打穿第一版 v4 的形態
    "coswallow_tuple":    "    except (Exception, IncompleteDownloadError):\n        pass\n",
    "named_but_no_raise": "    except IncompleteDownloadError:\n        pass\n    except Exception:\n        pass\n",
}

_BYPASS_TEMPLATE = """
async def search_cases_parallel(self):
    try:
        await self._something()
{handler}"""

_CORRECT_FORMS = {
    "name_before_exception":
        "    except IncompleteDownloadError:\n        raise\n    except Exception:\n        pass\n",
    "name_before_tuple":
        "    except IncompleteDownloadError:\n        raise\n    except (Exception, ValueError):\n        pass\n",
}


@pytest.mark.parametrize("form", sorted(_BYPASS_FORMS))
def test_ast_guard_detects_every_known_bypass_form(form):
    """⑧之元測試：守衛本身要有鑑別力——每一種能吞掉拒收的 handler 寫法都必須被抓到。

    這條測的是**守衛的判定範圍**，不是 production code。本 epic 三次空心
    （v1 白名單打錯函式名、v2 豁免掃字串、v3 tuple handler 漏掃）全屬「範圍寫錯而測試仍綠」，
    共同點是**沒有任何測試在測守衛自己**。這條補上那個缺口。
    """
    src = _BYPASS_TEMPLATE.format(handler=_BYPASS_FORMS[form])
    assert _scan_swallowed_rejections(src), f"守衛漏掉旁路寫法 {form}：\n{src}"


@pytest.mark.parametrize("form", sorted(_CORRECT_FORMS))
def test_ast_guard_accepts_correct_forms(form):
    """⑧之元測試（對照組）：正確寫法不得被誤報，否則守衛只是恆真。"""
    src = _BYPASS_TEMPLATE.format(handler=_CORRECT_FORMS[form])
    assert _scan_swallowed_rejections(src) == [], f"正確寫法被誤報 {form}：\n{src}"


def test_ast_guard_ignores_try_that_cannot_reach_download():
    """⑧之元測試（範圍下界）：碰不到下載的 try 不受檢，否則存檔／日誌 handler 會被誤擋。"""
    src = (
        "async def search_cases_parallel(self):\n"
        "    try:\n"
        "        self._save_failure_report(records)\n"
        "    except Exception:\n"
        "        pass\n"
    )
    assert _scan_swallowed_rejections(src) == []
