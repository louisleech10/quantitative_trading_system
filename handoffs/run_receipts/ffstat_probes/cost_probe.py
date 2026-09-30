"""FF-STAT Task 4.1 成本收據（docs/FFSTAT_SPEC.md Task 4.1；使用者 2026-09-24「先實測再定」窗長）。

3 標的 × 2 週期 × N＝500／1000／2000 之真實冷 run（各自子程序、隔離 tmp 與 d* 快取），逐 run 記：
- 分段耗時：校準域（`run_calibration_preflight`）、ADF（`_adf_pvalue_for_values` 累計）、d* 搜尋（`_find_min_d` 累計）、總計；
- 分階段峰值記憶體：取樣執行緒每筆取樣後睡 50 ms（實際起點間隔最大值另記）記「本程序＋全部子程序」之 RSS 合計與 USS 合計，依當下階段
  （校準／交接／公開；交接＝送出第一個 worker 至第一個 worker 完成）分別取最大；tier 判定用 USS，
  任一程序 USS 被拒之筆整筆改用 RSS 合計（上界，不漏算；macOS 子程序 USS 必被拒），取樣不完整即判失敗；
- 暫存清理：run 後隔離系統 tmp 下校準暫存前綴（契約 `calibration_tmp_prefix`）之殘留數；
- 各 N 與最大 N 之決策一致率；
- （b5，SPEC v41）各 N 與獨立後段之一致率：公開輸出之基礎欄（輸出窗在校準窗之後、不重疊）以生產 ADF 核心全長檢定
  （p>0.05＝不平穩），對照校準判定（決策之 `adf_pvalue`>0.05）；另記危險方向比例（校準判平穩、後段不平穩）；
- （b5，SPEC v32）公開域預熱耗時（`FeatureFactory._resolve_public_window` 累計）與加倍次數（metadata `warmup_doubling`）。
資料與窗（b5）：1h 讀 `kline_cache.h5`、輸出 2025-10-01～2025-12-31；12h 讀長歷史快取（`kline_cache.h5` 之 12h 於
2025-10-01 前只 1,278 根，N＝2000 前史不足）、輸出 2024-01-01～2025-12-31（獨立後段約 1,460 根）。
另跑（b5，SPEC v32）：①平穩化關閉（每標的×週期一次；預熱恆開對其為新增成本）；②改前（`BEFORE_COMMIT` 之 git worktree，
同一 payload 開／關各一次，只量總耗時與峰值——改前無校準域與預熱，逐階段計時不適用）。
另於 FFACT_MEMORY_TIER=8gb 跑一次多週期平行（含封包交接 worker 之父＋子峰值），峰值超過 8 GiB 即判失敗。
任一 run 失敗、有暫存殘留或超過 tier 上限 ⇒ 退出碼非 0。輸出 `handoffs/run_receipts/<日期>-ffstat-cost.json`。
量峰值與耗時須獨占機器（委員審碼、評測、其他重測試期間不跑）。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/cost_probe.py [--only-one]
（`--only-one`：只跑 BTC 1h N＝500 一列供估時，不寫收據）
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((REPO / "tests" / "_golden" / "ffstat" / "contract.json").read_text(encoding="utf-8"))
GIB = 1024 ** 3
KLINE_DIR = "data_cache/feature_klines"
LONGHIST_DIR = "data_cache/feature_klines_longhist"
# 逐週期之資料來源與輸出窗（b5；見模組說明）
WINDOWS = {"1h": (KLINE_DIR, "2025-10-01", "2025-12-31"), "12h": (LONGHIST_DIR, "2024-01-01", "2025-12-31")}
BEFORE_COMMIT = "5a148b8e"  # FF-STAT 生產碼改動前（SPEC v49「改前原始碼」同一 commit）
ADF_ALPHA = 0.05
LATE_MIN_VALUES = 100  # 後段有限值少於此數之欄不計入後段一致率


STAGES = ("calibration", "handoff", "public")
SAMPLE_INTERVAL_S = 0.05  # 每筆取樣完成後之睡眠秒數；實際起點間隔＝取樣耗時＋此值，逐 run 實測最大值記 max_sample_gap_seconds


class _Sampler:
    """每筆取樣後睡 50 ms 取樣「本程序＋全部子程序」之 RSS 合計與 USS 合計，依階段各記最大值。

    tier 判定值（`peak_judged_*`）逐筆取：該筆全部程序皆取得 USS ⇒ USS 合計（不重計共享頁；r19 codex P2-03）；
    任一程序 USS 被拒（macOS 對同使用者之 spawn 子程序 `task_for_pid` 即拒，主委實跑 2026-09-24）⇒ 該筆整筆改用
    RSS 合計（每程序 RSS ≥ USS，只會高估、不會漏算；r20 codex P1-01），計入 `samples_rss_fallback`；RSS 已計入後
    USS 才遇程序結束者同。任一程序連 RSS 亦取不到、或列舉子程序本身失敗 ⇒ 該筆記入 `samples_incomplete`、不留判定值，
    verdict 判量測失敗（r21 codex P1-01）。`peak_uss_*` 只取全數取得 USS 之筆。取樣途中經過之每個階段皆計入該筆（見 `_tick`）。"""

    def __init__(self) -> None:
        import psutil

        self._proc = psutil.Process()
        # 階段設定（改當下值＋附加歷史）與取樣之階段快照共用此鎖，兩者不得交錯（r23 codex P2-02）
        self._lock = threading.Lock()
        self._history: list = []  # 每次設定階段即附加（取樣途中經過之全部階段皆可查；r22 codex P2-01）
        self.stage = "public"
        self.peaks: dict = {}
        self._last_start = None  # 上一筆取樣起點（monotonic）；實際起點間隔最大值入收據（r22 codex P2-02）
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    @property
    def stage(self) -> str:
        return self._stage

    @stage.setter
    def stage(self, value: str) -> None:
        with self._lock:
            self._stage = value
            self._history.append(value)

    def _sample(self) -> tuple:
        """回傳 (RSS 合計, USS 合計或 None〔任一程序 USS 取不到〕, 是否完整〔每程序皆取得 RSS〕)。"""
        import psutil

        rss = uss = 0
        uss_ok = complete = True
        try:
            procs = [self._proc, *self._proc.children(recursive=True)]
        except Exception:
            # 列舉子程序失敗（沙箱禁 sysctl 時拋 PermissionError／AccessDenied；r21 codex P1-01）⇒ 不知有哪些 worker，
            # 本筆不完整、不作判定值
            procs = [self._proc]
            complete = uss_ok = False
        for proc in procs:
            try:
                rss += proc.memory_info().rss
            except psutil.NoSuchProcess:
                continue  # 讀 RSS 前已結束之程序：本筆未佔用
            except Exception:
                complete = uss_ok = False
                continue
            try:
                uss += proc.memory_full_info().uss
            except Exception:
                # 含 RSS 已計入後才結束（NoSuchProcess）：其 RSS 已在合計內，本筆改以 RSS 為判定值（r21 codex P2-01）
                uss_ok = False
        return rss, (uss if uss_ok else None), complete

    def _record(self, sample: tuple, stages: tuple) -> None:
        """把一筆 `_sample()` 結果計入 `stages` 內各階段之峰值（計數只加一次）。
        不完整之筆不計入任何判定值（由 verdict 之 samples_incomplete 判失敗）。"""
        rss, uss, complete = sample
        judged = None if not complete else (uss if uss is not None else rss)
        if uss is None:
            self.peaks["samples_rss_fallback"] = self.peaks.get("samples_rss_fallback", 0) + 1
        if not complete:
            self.peaks["samples_incomplete"] = self.peaks.get("samples_incomplete", 0) + 1
        for stage in stages:
            for metric, value in (("rss", rss), ("uss", uss), ("judged", judged)):
                if value is None:
                    continue
                key = f"peak_{metric}_{stage}_bytes"
                self.peaks[key] = max(self.peaks.get(key, 0), value)

    def _tick(self) -> None:
        """取一筆：該筆計入取樣開始時之階段＋取樣途中設定過之每個階段（如 public→handoff→public 亦記交接；
        r21 codex P2-02、r22 codex P2-01）；並記相鄰取樣起點之實際間隔最大值 `max_sample_gap_seconds`。"""
        start = time.monotonic()
        if self._last_start is not None:
            gap = start - self._last_start
            self.peaks["max_sample_gap_seconds"] = max(self.peaks.get("max_sample_gap_seconds", 0.0), gap)
        self._last_start = start
        with self._lock:
            mark = len(self._history)
            before = self._stage
        sample = self._sample()
        with self._lock:
            stages = tuple(dict.fromkeys((before, *self._history[mark:])))
        self._record(sample, stages)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._tick()
            time.sleep(SAMPLE_INTERVAL_S)

    def __enter__(self) -> "_Sampler":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()


def child(symbol: str, timeframe: str, n: int, mode: str, kline_dir: str, start: str, end: str) -> None:
    """`mode`：single（開平穩化單週期）／multi（開平穩化 1h＋12h，tier run）／off（平穩化關閉單週期）。"""
    multi = mode == "multi"
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPO))
    from _isolate import isolate  # noqa: E402

    root = isolate("ffstat_cost_")
    from _isolate import isolate_dstar_cache  # noqa: E402
    from momentum.factories import create_feature_factory  # noqa: E402
    from momentum.FeatureEngineering.feature_factory import FeatureFactory  # noqa: E402
    from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402
    from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

    isolate_dstar_cache(root)
    timers = {"calibration": 0.0, "adf": 0.0, "dstar": 0.0, "public_warmup": 0.0}
    sampler = _Sampler()
    real_pre = FeatureFactory.run_calibration_preflight
    real_adf = FeaturePreprocessor._adf_pvalue_for_values
    real_dstar = FeaturePreprocessor._find_min_d
    real_window = FeatureFactory._resolve_public_window

    def _window(self, *a, **k):
        t = time.perf_counter()
        try:
            return real_window(self, *a, **k)
        finally:
            timers["public_warmup"] += time.perf_counter() - t

    FeatureFactory._resolve_public_window = _window

    def _preflight(self, *a, **k):
        sampler.stage = "calibration"
        t = time.perf_counter()
        try:
            return real_pre(self, *a, **k)
        finally:
            timers["calibration"] += time.perf_counter() - t
            sampler.stage = "public"

    def _adf(values, sample_size=500):
        t = time.perf_counter()
        try:
            return real_adf(values, sample_size=sample_size)
        finally:
            timers["adf"] += time.perf_counter() - t

    def _dstar(self, series, **kw):
        t = time.perf_counter()
        try:
            return real_dstar(self, series, **kw)
        finally:
            timers["dstar"] += time.perf_counter() - t

    FeatureFactory.run_calibration_preflight = _preflight
    FeaturePreprocessor._adf_pvalue_for_values = staticmethod(_adf)
    FeaturePreprocessor._find_min_d = _dstar

    # 交接階段（SPEC Task 4.1「封包交接 worker 之瞬間」）：自送出第一個 worker 起，至第一個 worker 完成止
    # ——涵蓋父程序持有封包＋序列化送出＋子程序反序列化載入。multi_tf_generator 於函式內匯入
    # ProcessPoolExecutor，故於類別層級包裝 submit。
    from concurrent.futures import ProcessPoolExecutor

    real_submit = ProcessPoolExecutor.submit
    handoff = {"submitted": 0}

    def _submit(self, fn, *a, **k):
        if handoff["submitted"] == 0:
            sampler.stage = "handoff"
        handoff["submitted"] += 1
        future = real_submit(self, fn, *a, **k)

        def _done(_f):
            if sampler.stage == "handoff":
                sampler.stage = "public"

        future.add_done_callback(_done)
        return future

    ProcessPoolExecutor.submit = _submit

    payload = build_payload(h, timeframe, n, mode)
    factory = create_feature_factory(cache_dir=kline_dir, validate_continuity=False)
    factory._storage = FeatureStorage(str(root / "features"))
    t0 = time.perf_counter()
    with sampler:
        result = factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                           start_date=start, end_date=end, persist=True)
    total = time.perf_counter() - t0
    import tempfile

    leftover = len(list(Path(tempfile.gettempdir()).glob(CONTRACT["calibration_tmp_prefix"] + "*")))
    dec = h.decisions(result) if mode != "off" else {}
    doubling = (result.metadata or {}).get("warmup_doubling") or {}
    late = {} if mode == "off" else late_agreement(
        dec, h.base_column_values(root / "features", list(dec)), lambda v: real_adf(v, sample_size=len(v)))
    print("RESULT " + json.dumps({
        "seconds_total": round(total, 2), "seconds_calibration": round(timers["calibration"], 2),
        "seconds_adf": round(timers["adf"], 2), "seconds_dstar": round(timers["dstar"], 2),
        "seconds_public_warmup": round(timers["public_warmup"], 2),
        "warmup_doublings": doubling.get("doublings"), "warmup_depth_bars": doubling.get("depth_bars"),
        **peaks_for_result(sampler.peaks),
        "workers_submitted": handoff["submitted"],
        "calibration_tmp_leftover": leftover,
        **late,
        "decisions": {c: [bool(d["fracdiff"]), int(d["adf_differenced"] or 0)] for c, d in dec.items()},
    }))


def build_payload(h, timeframe: str, n: int, mode: str) -> dict:
    """探針 payload：開平穩化之輕量真實設定（`stat_payload`）；off＝同設定關 fracdiff 與 ADF 差分。"""
    tfs = ["1h", "12h"] if mode == "multi" else [timeframe]
    payload = h.stat_payload(tfs, fracdiff=mode != "off", adf=mode != "off")
    payload["timeframes"]["primary"] = timeframe
    payload["preprocessing"]["calibration_bars"] = n
    return payload


def late_agreement(dec: dict, late_values: dict, adf_pvalue) -> dict:
    """校準判定對獨立後段之一致率（SPEC v41）。校準判定＝決策 `adf_pvalue`>α（無 p 值之欄不計）；後段判定＝
    公開輸出該基礎欄之有限值以 `adf_pvalue`（生產核心、全長）檢定 >α；後段有限值 < LATE_MIN_VALUES 之欄不計。
    回傳一致率、危險方向比例（校準判平穩而後段不平穩；此方向不處理非平穩欄）、計入欄數與略過欄數。"""
    import numpy as np

    agree = danger = counted = skipped = 0
    for col, d in dec.items():
        p_cal = d.get("adf_pvalue")
        values = late_values.get(col)
        if p_cal is None or values is None:
            skipped += 1
            continue
        finite = np.asarray(values, dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        if finite.size < LATE_MIN_VALUES:
            skipped += 1
            continue
        cal_nonstat = float(p_cal) > ADF_ALPHA
        late_nonstat = float(adf_pvalue(finite)) > ADF_ALPHA
        counted += 1
        agree += cal_nonstat == late_nonstat
        danger += (not cal_nonstat) and late_nonstat
    return {"late_columns_counted": counted, "late_columns_skipped": skipped,
            "agreement_vs_late": None if not counted else round(agree / counted, 4),
            "danger_rate_vs_late": None if not counted else round(danger / counted, 4)}


def child_payload(timeframe: str, n: int, mode: str, out: str) -> None:
    """把與 `child` 同一之 payload 寫成 JSON（供改前 worktree 之子程序使用，避免其匯入新版 helper）。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPO))
    from _isolate import isolate  # noqa: E402

    isolate("ffstat_cost_payload_")
    from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

    Path(out).write_text(json.dumps(build_payload(h, timeframe, n, mode)), encoding="utf-8")


def child_before(worktree: str, payload_file: str, symbol: str, timeframe: str, kline_dir: str, start: str,
                 end: str) -> None:
    """改前原始碼（`BEFORE_COMMIT` 之 worktree）之同一 payload 生成：只量總耗時與峰值（改前無校準域與預熱）。
    kline 讀 repo 之真實快取（絕對路徑）；d* 快取若改前版本有 `_d_star_cache_dir` 即隔離。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _isolate import isolate  # noqa: E402

    root = isolate("ffstat_cost_before_")
    sys.path.insert(0, worktree)
    from momentum.factories import create_feature_factory  # noqa: E402
    from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402

    assert Path(sys.modules["momentum"].__file__).resolve().is_relative_to(Path(worktree).resolve()), \
        "改前子程序載入之 momentum 非改前 worktree"
    if hasattr(FeaturePreprocessor, "_d_star_cache_dir"):
        target = root / "dstar_cache"
        target.mkdir(parents=True, exist_ok=True)
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: target)  # type: ignore[assignment]
    payload = json.loads(Path(payload_file).read_text(encoding="utf-8"))
    factory = create_feature_factory(cache_dir=str(REPO / kline_dir), validate_continuity=False)
    factory._storage = FeatureStorage(str(root / "features"))
    sampler = _Sampler()
    t0 = time.perf_counter()
    with sampler:
        factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                  start_date=start, end_date=end, persist=True)
    total = time.perf_counter() - t0
    print("RESULT " + json.dumps({"seconds_total": round(total, 2), **peaks_for_result(sampler.peaks)}))


def peaks_for_result(peaks: dict) -> dict:
    """取樣器結果轉收據：位元組與筆數為整數，秒數保留小數（r23 codex P2-01：`int()` 曾把 0.1 秒間隔截為 0）。"""
    return {k: (round(float(v), 4) if k.endswith("_seconds") else int(v)) for k, v in peaks.items()}


def run_child(args: list, env: dict, flag: str = "--child", cwd: Path = REPO) -> dict:
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), flag, *args], capture_output=True, text=True,
                       env={**os.environ, **env}, cwd=str(cwd))
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if r.returncode != 0 or line is None:
        return {"rc": r.returncode or 1, "error": r.stderr[-800:]}
    return {"rc": 0, **json.loads(line[len("RESULT "):])}


def verdict(rows: list, tier: dict) -> list:
    """失敗原因清單（空＝通過）：任一 run 失敗、暫存殘留、tier run 缺任一階段峰值（含交接）、
    tier run 有取樣不完整之筆、tier run 任一階段判定值（`peak_judged_*`：USS 合計，USS 取不到之筆以 RSS 合計為上界）
    超過上限。"""
    problems = [f"run failed: {r.get('symbol')} {r.get('timeframe')} N={r.get('n')} mode={r.get('mode', 'on')}"
                f"{' before=' + r['commit'] if r.get('commit') else ''}" for r in rows if r.get("rc") != 0]
    problems += [f"tmp leftover: {r.get('symbol')} {r.get('timeframe')} N={r.get('n')}"
                 for r in rows if r.get("calibration_tmp_leftover")]
    limit = CONTRACT["min_memory_tier_gb"] * GIB
    if tier.get("rc") != 0:
        problems.append("tier run failed")
        return problems
    if tier.get("samples_incomplete"):
        problems.append(f"tier sampling incomplete: {tier['samples_incomplete']} samples")
    for stage in STAGES:
        key = f"peak_judged_{stage}_bytes"
        if key not in tier:
            problems.append(f"tier run missing {stage} peak")
        elif tier[key] > limit:
            problems.append(f"tier {stage} peak exceeds {CONTRACT['min_memory_tier_gb']} GiB")
    return problems


def _log(msg: str) -> None:
    """進度行（停滯監看讀 stderr 之行數與時間）。"""
    print(f"[{_dt.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def before_worktree() -> Path:
    """改前原始碼之 worktree（`BEFORE_COMMIT`；系統 tmp 下固定路徑，已存在且 HEAD 相符即重用）。"""
    import tempfile

    path = Path(tempfile.gettempdir()) / f"ffstat_cost_before_{BEFORE_COMMIT}"
    head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0 or not head.stdout.startswith(BEFORE_COMMIT):
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", str(path), BEFORE_COMMIT],
                       check=True, capture_output=True, text=True)
    return path


def main(only_one: bool = False) -> int:
    rows, off_rows, before_rows = [], [], []
    symbols = CONTRACT["cost_measure_symbols"][:1] if only_one else CONTRACT["cost_measure_symbols"]
    tfs = ["1h"] if only_one else CONTRACT["cost_measure_timeframes"]
    ns = [CONTRACT["calibration_n_default"]] if only_one else CONTRACT["cost_measure_n"]
    for symbol in symbols:
        for tf in tfs:
            kline_dir, start, end = WINDOWS[tf]
            by_n = {}
            for n in ns:
                _log(f"single {symbol} {tf} N={n}")
                by_n[n] = run_child([symbol, tf, str(n), "single", kline_dir, start, end], {})
                _log(f"  rc={by_n[n].get('rc')} seconds={by_n[n].get('seconds_total')}")
            ref = by_n[max(by_n)].get("decisions", {})
            for n, res in by_n.items():
                dec = res.pop("decisions", {})
                common = [c for c in dec if c in ref]
                agree = sum(dec[c] == ref[c] for c in common) / len(common) if common else None
                rows.append({"symbol": symbol, "timeframe": tf, "n": n, "kline_dir": kline_dir, "window": [start, end],
                             **res, "agreement_vs_max_n": None if agree is None else round(agree, 4)})
            if only_one:
                continue
            _log(f"off {symbol} {tf}")
            off = run_child([symbol, tf, str(CONTRACT["calibration_n_default"]), "off", kline_dir, start, end], {})
            off.pop("decisions", None)
            off_rows.append({"symbol": symbol, "timeframe": tf, "mode": "off", "kline_dir": kline_dir,
                             "window": [start, end], **off})
            worktree = before_worktree()
            for mode in ("single", "off"):
                payload_file = Path(worktree) / f"_cost_payload_{tf}_{mode}.json"
                got = run_child([tf, str(CONTRACT["calibration_n_default"]), mode, str(payload_file)], {}, "--payload")
                if got.get("rc") not in (0, None) and not payload_file.exists():
                    before_rows.append({"symbol": symbol, "timeframe": tf, "mode": mode, "rc": 1,
                                        "error": "payload 產生失敗"})
                    continue
                _log(f"before {symbol} {tf} {mode}")
                res = run_child([str(worktree), str(payload_file), symbol, tf, kline_dir, start, end], {},
                                "--before", cwd=worktree)
                before_rows.append({"symbol": symbol, "timeframe": tf, "mode": "on" if mode == "single" else "off",
                                    "commit": BEFORE_COMMIT, "kline_dir": kline_dir, "window": [start, end], **res})
    if only_one:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0 if all(r.get("rc") == 0 for r in rows) else 1
    _log("tier multi")
    tier_dir, tier_start, tier_end = WINDOWS["1h"]
    tier = run_child([CONTRACT["cost_measure_symbols"][0], "1h", str(CONTRACT["calibration_n_default"]), "multi",
                      tier_dir, tier_start, tier_end],
                     {"FFACT_MEMORY_TIER": f"{CONTRACT['min_memory_tier_gb']}gb", "FFACT_MULTI_TF_PARALLEL": "1"})
    tier.pop("decisions", None)
    problems = verdict(rows + off_rows + before_rows, tier)
    out = REPO / "handoffs" / "run_receipts" / f"{_dt.date.today():%Y%m%d}-ffstat-cost.json"
    out.write_text(json.dumps({"spec": "docs/FFSTAT_SPEC.md Task 4.1", "sleep_after_sample_seconds": SAMPLE_INTERVAL_S,
                               "windows": WINDOWS, "before_commit": BEFORE_COMMIT, "rows": rows,
                               "stationarity_off_rows": off_rows, "before_rows": before_rows,
                               "min_tier_multi_tf": tier, "problems": problems},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8])
    elif len(sys.argv) > 1 and sys.argv[1] == "--payload":
        child_payload(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5])
        print("RESULT {}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--before":
        child_before(*sys.argv[2:9])
    else:
        raise SystemExit(main(only_one="--only-one" in sys.argv))
