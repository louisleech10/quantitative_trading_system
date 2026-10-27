"""NOCAP Task 0.3b（docs/NOCAP_SPEC.md）：全規模重型跑前之成長曲線——同一入口、同一真實資料取 ≥ 3 個規模點
（`--scale` 明列，每點經共用監看各自啟動），擬合冪次並保守推算全規模，寫 `handoffs/run_receipts/<日期>-<目標>-scale.json`。

用法：`venv/bin/python scripts/run_watched.py` 不必另包（本腳本每點自經共用監看）；須背景執行：
  venv/bin/python scripts/scale_probe.py --out <收據> --full-scale N --scale a --scale b --scale c [--unit cols]
      [--data <輸入檔> ...] [--config <設定檔> ...] -- <命令>（命令中之 `{scale}` 代入規模，並設環境變數 NOCAP_SCALE）

起始例外：本腳本列 `heavy_commands.json` 之 `self_watched`（須背景、原始碼須呼叫共用監看），但不要求其自身之成長曲線或估時收據。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import statistics
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
MIN_POINTS = 3
MIN_R2 = 0.9
SUPERLINEAR_EXPONENT = 1.2
REPEAT_BELOW_SECONDS = 60.0  # 單次 < 60 秒者跑 3 次取中位數，否則 1 次
REPEATS = 3


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _loglog(xs: Sequence[float], ys: Sequence[float]) -> Optional[Dict[str, float]]:
    """log y = log a + b·log x 之最小平方；回 {a, b, r2}；任一值 ≤ 0 ⇒ None（冪次無定義）。"""
    if any(v <= 0 for v in list(xs) + list(ys)):
        return None
    lx, ly = [math.log(v) for v in xs], [math.log(v) for v in ys]
    mx, my = statistics.fmean(lx), statistics.fmean(ly)
    sxx = sum((v - mx) ** 2 for v in lx)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sxx
    a = my - b * mx
    ss_tot = sum((y - my) ** 2 for y in ly)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(lx, ly))
    return {"a": a, "b": b, "r2": 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot}


def _project(xs: Sequence[float], ys: Sequence[float], full: float) -> Optional[float]:
    """冪次推算與末兩點斜率線性外推之較大者（保守）。"""
    lin = ys[-1] + (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) * (full - xs[-1]) if xs[-1] != xs[-2] else ys[-1]
    ll = _loglog(xs, ys)
    power = math.exp(ll["a"]) * full ** ll["b"] if ll else None
    return max(v for v in (lin, power) if v is not None)


def fit(points: Sequence[Mapping[str, Any]], full_scale: float) -> Dict[str, Any]:
    """`points` 每點 {scale, unit, seconds, peak_rss_bytes}。回 {fit: {model, exponent, r2}, projection: {scale, seconds,
    peak_rss_bytes}, superlinear, extrapolation_unreliable, reasons}；`projection` 取冪次推算與末兩點線性外推之較大者；
    點數 < 3、r2 < 0.9、耗時或 RSS 隨規模遞減任一成立 ⇒ `extrapolation_unreliable` 為 True。"""
    pts = sorted(points, key=lambda p: float(p["scale"]))
    xs = [float(p["scale"]) for p in pts]
    secs = [float(p["seconds"]) for p in pts]
    rss = [float(p["peak_rss_bytes"]) for p in pts]
    reasons: List[str] = []
    if len(pts) < MIN_POINTS or len(set(xs)) < MIN_POINTS:
        reasons.append(f"規模點不足 {MIN_POINTS} 個相異點")
    if any(b < a for a, b in zip(secs, secs[1:])):
        reasons.append("耗時隨規模遞減")
    if any(b < a for a, b in zip(rss, rss[1:])):
        reasons.append("峰值 RSS 隨規模遞減")
    ll = _loglog(xs, secs) if len(set(xs)) >= 2 else None
    if ll is None:
        reasons.append("冪次擬合無定義（點不足或含非正值）")
    elif ll["r2"] < MIN_R2:
        reasons.append(f"r2 {ll['r2']:.3f} < {MIN_R2}")
    projection = {"scale": full_scale,
                  "seconds": _project(xs, secs, full_scale) if len(xs) >= 2 else None,
                  "peak_rss_bytes": _project(xs, rss, full_scale) if len(xs) >= 2 else None}
    exponent = ll["b"] if ll else None
    return {"fit": {"model": "power", "exponent": exponent, "r2": ll["r2"] if ll else None},
            "projection": projection, "superlinear": bool(exponent is not None and exponent > SUPERLINEAR_EXPONENT),
            "extrapolation_unreliable": bool(reasons), "reasons": reasons}


class _TreeRssSampler:
    """本行程之全部子孫（共用監看所啟動之子行程樹）RSS 總和之峰值；每 `interval` 秒取樣（共用監看之檢查間隔為 30 秒，
    過粗不足以量峰值）。psutil 不可用 ⇒ 峰值 None。"""

    def __init__(self, interval: float = 0.2) -> None:
        self.interval, self.peak = interval, None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _sample(self) -> Optional[int]:
        try:
            import psutil

            total = 0
            for p in psutil.Process(os.getpid()).children(recursive=True):
                try:
                    total += p.memory_info().rss
                except Exception:  # noqa: BLE001 — 列舉後已結束
                    pass
            return total
        except Exception:  # noqa: BLE001
            return None

    def _loop(self) -> None:
        while not self._stop.is_set():
            v = self._sample()
            if v is not None:
                self.peak = v if self.peak is None else max(self.peak, v)
            self._stop.wait(self.interval)

    def __enter__(self) -> "_TreeRssSampler":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._stop.set()
        self._thread.join()


def run_watched(cmd: Sequence[str], **kwargs: Any) -> Any:
    """以共用監看（`handoffs/run_receipts/numview_probes/_watchdog.py`）啟動一個規模點；`scale` 代入命令與環境變數。
    回共用監看之結果另附 `peak_rss_bytes`（行程樹 RSS 峰值）。"""
    wd = _load("nocap_scale_probe_watchdog", REPO / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py")
    rw = _load("nocap_scale_probe_run_watched", REPO / "scripts" / "run_watched.py")
    scale = kwargs["scale"]
    argv = [str(t).replace("{scale}", str(scale)) for t in cmd]
    env = {**os.environ, "NOCAP_SCALE": str(scale)}
    with _TreeRssSampler() as sampler:
        res = wd.run_watched(argv, log_path=Path(kwargs["log_path"]), config=wd.load_config(rw._criteria()),
                             cwd=str(REPO), env=env)
    res.peak_rss_bytes = sampler.peak
    return res


def _peak(result: Any) -> Optional[float]:
    return getattr(result, "peak_rss_bytes", None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    if "--" not in args_in:
        print("scale_probe：須以 `--` 分隔要量測之命令", file=sys.stderr)
        return 2
    cut = args_in.index("--")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--full-scale", type=float, required=True)
    ap.add_argument("--scale", type=int, action="append", required=True)
    ap.add_argument("--unit", default="rows")
    ap.add_argument("--data", action="append", default=[])
    ap.add_argument("--config", action="append", default=[])
    ap.add_argument("--log-dir", default=None)
    opts = ap.parse_args(args_in[:cut])
    cmd = args_in[cut + 1:]
    if not cmd:
        print("scale_probe：`--` 後無命令", file=sys.stderr)
        return 2
    out = Path(opts.out)
    log_dir = Path(opts.log_dir) if opts.log_dir else out.with_suffix(".logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    points: List[Dict[str, Any]] = []
    for scale in opts.scale:
        runs = []
        while True:
            res = run_watched(cmd, scale=scale, log_path=log_dir / f"scale-{scale}-{len(runs)}.log")
            if getattr(res, "status", "") not in ("EXITED", "exited") or getattr(res, "returncode", 1) != 0:
                print(f"scale_probe：規模 {scale} 未正常結束（status={getattr(res, 'status', None)}、"
                      f"rc={getattr(res, 'returncode', None)}、reason={getattr(res, 'reason', None)}）", file=sys.stderr)
                return 1
            runs.append(res)
            if len(runs) >= REPEATS or float(res.wall_seconds) >= REPEAT_BELOW_SECONDS:
                break
        peaks = [p for p in (_peak(r) for r in runs) if p is not None]
        points.append({"scale": scale, "unit": opts.unit, "runs": len(runs),
                       "seconds": statistics.median(float(r.wall_seconds) for r in runs),
                       "peak_rss_bytes": max(peaks) if peaks else None})
    if any(p["peak_rss_bytes"] is None for p in points):
        print("scale_probe：共用監看未回報峰值 RSS ⇒ 無法擬合記憶體曲線", file=sys.stderr)
        return 1
    rid = _load("nocap_scale_probe_identity", REPO / "scripts" / "run_receipt_identity.py")
    entry = next((t for t in cmd if (REPO / t).is_file() and Path(t).suffix in (".py", ".sh")), cmd[0])
    match = rid.compute_match(entry, cmd, [], opts.data, opts.config)
    receipt = {"identity": rid.make_identity(match, "scripts/scale_probe.py"), "points": points,
               **fit(points, opts.full_scale)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    flag = "⚠ 推算不可靠：" + "；".join(receipt["reasons"]) if receipt["extrapolation_unreliable"] else "推算可用"
    print(f"scale_probe：已寫 {out}；{flag}；超線性={receipt['superlinear']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
