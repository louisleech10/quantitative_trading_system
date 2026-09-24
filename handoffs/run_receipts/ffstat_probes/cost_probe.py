"""FF-STAT Task 4.1 成本收據（docs/FFSTAT_SPEC.md Task 4.1；使用者 2026-09-24「先實測再定」窗長）。

3 標的 × 2 週期 × N＝500／1000／2000 之真實冷 run（各自子程序、隔離 tmp 與 d* 快取），逐 run 記：
- 分段耗時：校準域（`run_calibration_preflight`）、ADF（`_adf_pvalue_for_values` 累計）、d* 搜尋（`_find_min_d` 累計）、總計；
- 分階段峰值記憶體：取樣執行緒每 50 ms 記「本程序＋全部子程序」之 RSS 合計與 USS 合計，依當下階段
  （校準／交接／公開；交接＝送出第一個 worker 至第一個 worker 完成）分別取最大；tier 判定用 USS，
  任一程序 USS 被拒之筆整筆改用 RSS 合計（上界，不漏算；macOS 子程序 USS 必被拒），取樣不完整即判失敗；
- 暫存清理：run 後隔離系統 tmp 下校準暫存前綴（契約 `calibration_tmp_prefix`）之殘留數；
- 各 N 與最大 N 之決策一致率。
另於 FFACT_MEMORY_TIER=8gb 跑一次多週期平行（含封包交接 worker 之父＋子峰值），峰值超過 8 GiB 即判失敗。
任一 run 失敗、有暫存殘留或超過 tier 上限 ⇒ 退出碼非 0。輸出 `handoffs/run_receipts/<日期>-ffstat-cost.json`。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/cost_probe.py
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


STAGES = ("calibration", "handoff", "public")


class _Sampler:
    """每 50 ms 取樣「本程序＋全部子程序」之 RSS 合計與 USS 合計，依當下階段各記最大值。

    tier 判定值（`peak_judged_*`）逐筆取：該筆全部程序皆取得 USS ⇒ USS 合計（不重計共享頁；r19 codex P2-03）；
    任一程序 USS 被拒（macOS 對同使用者之 spawn 子程序 `task_for_pid` 即拒，主委實跑 2026-09-24）⇒ 該筆整筆改用
    RSS 合計（每程序 RSS ≥ USS，只會高估、不會漏算；r20 codex P1-01），計入 `samples_rss_fallback`。任一程序連
    RSS 亦取不到 ⇒ 該筆記入 `samples_incomplete`，verdict 判量測失敗。`peak_uss_*` 只取全數取得 USS 之筆。"""

    def __init__(self) -> None:
        import psutil

        self._proc = psutil.Process()
        self.stage = "public"
        self.peaks: dict = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _sample(self) -> tuple:
        """回傳 (RSS 合計, USS 合計或 None〔任一程序 USS 取不到〕, 是否完整〔每程序皆取得 RSS〕)。"""
        import psutil

        rss = uss = 0
        uss_ok = complete = True
        for proc in [self._proc, *self._proc.children(recursive=True)]:
            try:
                rss += proc.memory_info().rss
            except psutil.NoSuchProcess:
                continue  # 取樣期間已結束之程序
            except Exception:
                complete = uss_ok = False
                continue
            try:
                uss += proc.memory_full_info().uss
            except psutil.NoSuchProcess:
                continue
            except Exception:
                uss_ok = False
        return rss, (uss if uss_ok else None), complete

    def _record(self, sample: tuple) -> None:
        """把一筆 `_sample()` 結果計入當下階段之峰值與計數。"""
        rss, uss, complete = sample
        judged = uss if uss is not None else rss
        if uss is None:
            self.peaks["samples_rss_fallback"] = self.peaks.get("samples_rss_fallback", 0) + 1
        if not complete:
            self.peaks["samples_incomplete"] = self.peaks.get("samples_incomplete", 0) + 1
        for metric, value in (("rss", rss), ("uss", uss), ("judged", judged)):
            if value is None:
                continue
            key = f"peak_{metric}_{self.stage}_bytes"
            self.peaks[key] = max(self.peaks.get(key, 0), value)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._record(self._sample())
            time.sleep(0.05)

    def __enter__(self) -> "_Sampler":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()


def child(symbol: str, timeframe: str, n: int, multi: bool) -> None:
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
    timers = {"calibration": 0.0, "adf": 0.0, "dstar": 0.0}
    sampler = _Sampler()
    real_pre = FeatureFactory.run_calibration_preflight
    real_adf = FeaturePreprocessor._adf_pvalue_for_values
    real_dstar = FeaturePreprocessor._find_min_d

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

    tfs = ["1h", "12h"] if multi else [timeframe]
    payload = h.stat_payload(tfs)
    payload["timeframes"]["primary"] = timeframe
    payload["preprocessing"]["calibration_bars"] = n
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root / "features"))
    t0 = time.perf_counter()
    with sampler:
        result = factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                           start_date="2025-10-01", end_date="2025-12-31", persist=True)
    total = time.perf_counter() - t0
    import tempfile

    leftover = len(list(Path(tempfile.gettempdir()).glob(CONTRACT["calibration_tmp_prefix"] + "*")))
    dec = h.decisions(result)
    print("RESULT " + json.dumps({
        "seconds_total": round(total, 2), "seconds_calibration": round(timers["calibration"], 2),
        "seconds_adf": round(timers["adf"], 2), "seconds_dstar": round(timers["dstar"], 2),
        **{k: int(v) for k, v in sampler.peaks.items()},
        "workers_submitted": handoff["submitted"],
        "calibration_tmp_leftover": leftover,
        "decisions": {c: [bool(d["fracdiff"]), int(d["adf_differenced"] or 0)] for c, d in dec.items()},
    }))


def run_child(args: list, env: dict) -> dict:
    r = subprocess.run([sys.executable, __file__, "--child", *args], capture_output=True, text=True,
                       env={**os.environ, **env}, cwd=str(REPO))
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if r.returncode != 0 or line is None:
        return {"rc": r.returncode or 1, "error": r.stderr[-800:]}
    return {"rc": 0, **json.loads(line[len("RESULT "):])}


def verdict(rows: list, tier: dict) -> list:
    """失敗原因清單（空＝通過）：任一 run 失敗、暫存殘留、tier run 缺任一階段峰值（含交接）、
    tier run 有取樣不完整之筆、tier run 任一階段判定值（`peak_judged_*`：USS 合計，USS 取不到之筆以 RSS 合計為上界）
    超過上限。"""
    problems = [f"run failed: {r.get('symbol')} {r.get('timeframe')} N={r.get('n')}" for r in rows if r.get("rc") != 0]
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


def main() -> int:
    rows = []
    for symbol in CONTRACT["cost_measure_symbols"]:
        for tf in CONTRACT["cost_measure_timeframes"]:
            by_n = {n: run_child([symbol, tf, str(n), "single"], {}) for n in CONTRACT["cost_measure_n"]}
            ref = by_n[max(by_n)].get("decisions", {})
            for n, res in by_n.items():
                dec = res.pop("decisions", {})
                common = [c for c in dec if c in ref]
                agree = sum(dec[c] == ref[c] for c in common) / len(common) if common else None
                rows.append({"symbol": symbol, "timeframe": tf, "n": n, **res,
                             "agreement_vs_max_n": None if agree is None else round(agree, 4)})
    tier = run_child([CONTRACT["cost_measure_symbols"][0], "1h", str(CONTRACT["calibration_n_default"]), "multi"],
                     {"FFACT_MEMORY_TIER": f"{CONTRACT['min_memory_tier_gb']}gb", "FFACT_MULTI_TF_PARALLEL": "1"})
    tier.pop("decisions", None)
    problems = verdict(rows, tier)
    out = REPO / "handoffs" / "run_receipts" / f"{_dt.date.today():%Y%m%d}-ffstat-cost.json"
    out.write_text(json.dumps({"spec": "docs/FFSTAT_SPEC.md Task 4.1", "rows": rows, "min_tier_multi_tf": tier,
                               "problems": problems}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] == "multi")
    else:
        raise SystemExit(main())
