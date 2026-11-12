"""分批、每批新行程跑一份 pytest 選取（docs/TEST_SELECTION.md §5 過渡工具 6；NOCAP Task 0.3c ④）。

為何：同一 pytest 行程跑久了，重型特徵生成測試釋放之記憶體不歸還作業系統（2026-11-12 實測：單條
`test_dual_start_convergence_default_config[1d]` 後 phys_footprint 停約 3 GB，系統 malloc 使用中 79 MB、保留 5,063 MB），
後續大量呼叫 `gc.collect()` 之測試因而變慢（同一測試單獨 8.5 秒、其後 15.4 秒、L1c 長跑 8.1 GB 時 55.7 秒）。業界同類
作法：測試依檔分片、各片獨立行程（CI 依檔分片；pytest-xdist 以 worker 行程分攤）。

規劃（`plan`）：ledger 紀錄耗時 ≥60 秒（§4 重型）之 nodeid 各自一批；其餘依選取順序按測試檔聚批，同一檔不拆
（module 等共用 fixture 只付一次），一批累計保守估時達 `--chunk-seconds` 即收批。各批估時＝
`scripts/ledger_durations.py` 之 `conservative_estimate`（只採通過紀錄、含共用 fixture 建置成本轉移）＋每行程開銷
`PROCESS_OVERHEAD_S`。
執行：每批以共用監看（`run_watched`）跑 `pytest @<該批 nodeid 參數檔>`；同時最多 `--jobs` 批。重型批獨占（不與
任何批同時跑：單條重型特徵生成測試併跑時實測 footprint 達 6.8 GB、swap 由 3.9 GB 升至 11.4 GB，8 GB 機器不可併）；
快速層併發時，剩餘可用記憶體（`momentum/FeatureEngineering/memory_budget.py` 之 darwin VM 快照，非 darwin 為 psutil；
讀不到視為不足）須 ≥ `--min-free-gb` ×（執行中批數＋1）——快照時點執行中批未必已到峰值，故逐批預留（審碼 r5）。
停止：任一批卡住（hang／memory）⇒ 不再開新批、等執行中者結束、整跑回該原因 rc（4 hang、5 memory；NOCAP：不自動
重跑）；pytest rc 非 0／1（中斷、內部錯誤、用法錯誤、未收集到）或該批啟動／讀 log 拋例外 ⇒ 同樣停開新批、回 3（該批
記 `status: error`，不得消失）。測試失敗（rc 1）照常續跑。
完整性：每批 pytest 摘要之 passed＋failed＋errors＋skipped＋xfailed＋xpassed 須等於該批條數，否則記 `incomplete`、rc 3。

用法：`venv/bin/python scripts/run_chunked.py --select <nodeid 清單> --out <目錄> [--jobs 1] [--min-free-gb 3]
  [--chunk-seconds 900] [--traces <讀檔追蹤.jsonl>...] [--plan-only] [-- <每批額外 pytest 參數>]`
輸出：`<目錄>/plan.json`、`chunk_NNN.args`、`chunk_NNN.log`、`summary.json`；stdout 每批一行 `[chunked]`。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
#: 每批新行程之固定開銷（Python 啟動、import、收集）：2026-11-12 三次單條實測 total−call＝7.0、8.0、7.0 秒
PROCESS_OVERHEAD_S = 8.0
#: 快速層併發時每批預留之剩餘記憶體（GB）：依據為單條重型特徵生成測試 tracemalloc 峰值 2,959 MB——快速層批之峰值
#: 未逐批實測，此值為上限參考而非實測保證；重型批不併發（見檔頭）
DEFAULT_MIN_FREE_GB = 3.0
_SUMMARY = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)")


def _load(name: str, path: Path) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _ld() -> Any:
    return _load("run_chunked_ld", REPO / "scripts" / "ledger_durations.py")


def plan(selection: List[str], durations: Dict[str, float], gaps: Dict[str, float],
         shared: Optional[Dict[str, List[str]]], chunk_seconds: float, fast_limit: float,
         fixture_costs: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """選取 → 批次清單（見檔頭「規劃」）。每批：{"kind": "heavy"|"fast", "nodeids": [...], "estimate_s": 秒}；各批獨立
    估（每批新行程各付共用 fixture 與開銷）。"""
    ld = _ld()

    def est(nodes: List[str]) -> float:
        return ld.conservative_estimate(nodes, durations, gaps, shared, fixture_costs)[0] + PROCESS_OVERHEAD_S

    def make(kind: str, nodes: List[str]) -> Dict[str, Any]:
        total, det = ld.conservative_estimate(nodes, durations, gaps, shared, fixture_costs)
        # 獨占：重型、或本批須重建之共用 fixture 實測成本達重型門檻、或成本未知、或含無通過紀錄之 nodeid（新測試／
        # 從未通過，耗時未知；保守）——歷史秒數短而 fixture 重建重者亦須獨占（審碼 r6、r7）
        exclusive = (kind == "heavy" or bool(det["fixture_cost_unknown"]) or bool(det["unknown"])
                     or any(v >= fast_limit for v in det["fixture_cost_added"].values()))
        return {"kind": kind, "nodeids": nodes, "estimate_s": total + PROCESS_OVERHEAD_S, "exclusive": exclusive,
                "unknown": det["unknown"], "fixture_cost_unknown": det["fixture_cost_unknown"]}

    chunks: List[Dict[str, Any]] = []
    by_file: Dict[str, List[str]] = {}
    for n in dict.fromkeys(selection):
        if durations.get(n, 0.0) >= fast_limit:
            chunks.append(make("heavy", [n]))
        else:
            by_file.setdefault(n.split("::", 1)[0], []).append(n)
    cur: List[str] = []
    for nodes in by_file.values():
        cand = cur + nodes
        if cur and est(cand) > chunk_seconds + PROCESS_OVERHEAD_S:
            chunks.append(make("fast", cur))
            cur = list(nodes)
        else:
            cur = cand
    if cur:
        chunks.append(make("fast", cur))
    return chunks


def plan_uncertainty(chunks: List[Dict[str, Any]]) -> Dict[str, int]:
    """分批後之估時未知項計數（守衛 `uncertain_ack` 與 plan.json 同源；審碼 r6）：unknown＝無通過紀錄之 nodeid 數
    （不重複）；fixture_cost_unknown＝各批成本未知之共用 fixture／檔之**逐批實例數**（每批新行程各重付一次）。"""
    return {"unknown": len({n for c in chunks for n in c.get("unknown", [])}),
            "fixture_cost_unknown": sum(len(c.get("fixture_cost_unknown", [])) for c in chunks)}


def parse_summary(text: str) -> Dict[str, int]:
    """pytest 最後一行摘要（`= 3 failed, 10 passed, 1 error in 5.0s =`）→ 計數；無摘要 ⇒ 空 dict。"""
    lines = [ln for ln in text.splitlines() if ln.startswith("=") and " in " in ln and _SUMMARY.search(ln)]
    if not lines:
        return {}
    out: Dict[str, int] = {}
    for num, kind in _SUMMARY.findall(lines[-1]):
        key = "errors" if kind.startswith("error") else kind
        out[key] = out.get(key, 0) + int(num)
    return out


def failed_nodeids(text: str) -> List[str]:
    """`-rfE` 短摘要之 FAILED／ERROR 列 → nodeid。"""
    out = []
    for ln in text.splitlines():
        m = re.match(r"^(FAILED|ERROR) (\S+)", ln)
        if m:
            out.append(f"{m.group(1)} {m.group(2)}")
    return out


def available_gb() -> Optional[float]:
    """剩餘可用記憶體（GB）；讀不到 ⇒ None（不以讀不到放行併發：呼叫端視為不足）。"""
    try:
        sys.path.insert(0, str(REPO))
        from momentum.FeatureEngineering import memory_budget as mb

        return float(mb.admission_snapshot()["available_bytes"]) / 2 ** 30
    except Exception:  # noqa: BLE001
        return None


def run(chunks: List[Dict[str, Any]], out: Path, jobs: int, min_free_gb: float, extra: List[str],
        runner: Optional[Callable[..., Any]] = None, avail: Callable[[], Optional[float]] = available_gb,
        sleep: Callable[[float], None] = time.sleep) -> Dict[str, Any]:
    """依序開批（同時最多 `jobs`）；見檔頭「執行／停止／完整性」。`runner(cmd, log_path, expected_seconds)` 回
    (status, returncode, cause)；預設為共用監看 `run_watched`。"""
    wd = _load("nocap_shared_watchdog", REPO / "handoffs" / "run_receipts" / "numview_probes" / "_watchdog.py")
    if runner is None:
        sys.path.insert(0, str(REPO))
        from tests.feature_engineering import numview_helpers as nh

        config = wd.load_config(json.loads(nh.current_criteria_path().read_text(encoding="utf-8")))

        def runner(cmd: List[str], log_path: Path, expected_seconds: float):  # type: ignore[misc]
            res = wd.run_watched(cmd, log_path=log_path, config=config, expected_seconds=expected_seconds,
                                 cwd=str(REPO))
            return res.status, res.returncode, res.cause

    results: List[Dict[str, Any]] = []
    lock = threading.Lock()
    stop = {"rc": 0, "why": ""}

    def one(i: int, chunk: Dict[str, Any]) -> None:
        try:
            _one(i, chunk)
        except Exception as exc:  # noqa: BLE001 — 啟動／讀 log 失敗不得使該批消失（r5 CODEX-R5-P1-01）
            with lock:
                results.append({"chunk": i, "kind": chunk["kind"], "n": len(chunk["nodeids"]),
                                "estimate_s": round(chunk["estimate_s"]), "wall_s": 0, "status": "error", "rc": None,
                                "cause": repr(exc), "counts": {}, "failures": [], "log": "", "incomplete": True})
                if not stop["rc"]:
                    stop.update(rc=3, why=f"chunk {i} error {exc!r}")
            print(f"[chunked] chunk {i} error {exc!r}", flush=True)

    def _one(i: int, chunk: Dict[str, Any]) -> None:
        args = out / f"chunk_{i:03d}.args"
        args.write_text("".join(f"{n}\n" for n in chunk["nodeids"]), encoding="utf-8")
        log = out / f"chunk_{i:03d}.log"
        cmd = [str(REPO / "venv" / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rfE",
               *extra, f"@{args}"]
        t0 = time.monotonic()
        status, rc, cause = runner(cmd, log, chunk["estimate_s"])
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        counts = parse_summary(text)
        ran = sum(v for k, v in counts.items() if k != "deselected")
        rec = {"chunk": i, "kind": chunk["kind"], "n": len(chunk["nodeids"]), "estimate_s": round(chunk["estimate_s"]),
               "wall_s": round(time.monotonic() - t0), "status": status, "rc": rc, "cause": cause, "counts": counts,
               "failures": failed_nodeids(text), "log": str(log)}
        rec["incomplete"] = status == wd.EXITED and rc in (0, 1) and ran != len(chunk["nodeids"])
        with lock:
            results.append(rec)
            if status == wd.STALLED and not stop["rc"]:
                stop.update(rc=4 if cause == wd.CAUSE_HANG else 5, why=f"chunk {i} stalled（{cause}）")
            elif status == wd.EXITED and rc not in (0, 1) and not stop["rc"]:
                stop.update(rc=3, why=f"chunk {i} pytest rc={rc}")
        print(f"[chunked] chunk {i} {chunk['kind']} n={len(chunk['nodeids'])} {status} rc={rc} "
              f"{rec['wall_s']}s/估{rec['estimate_s']}s {counts}", flush=True)

    pending = list(enumerate(chunks))
    running: Dict[Future, Dict[str, Any]] = {}

    def reap() -> None:
        done, _ = wait(list(running), return_when=FIRST_COMPLETED)
        for f in done:
            running.pop(f)
            f.result()  # one() 已攔例外；此處再拋即程式錯誤，不得吞

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        while pending and not stop["rc"]:
            i, chunk = pending[0]
            if running:
                # 重型批獨占（單條重型實測 footprint 達 6.8 GB，8 GB 機器不併跑；r5 CODEX-R5-P1-04）；快速層併發時，
                # 剩餘記憶體須夠「每個執行中批＋新批」各 min_free_gb（快照時點執行中批未必已到峰值，故逐批預留）
                heavy_involved = chunk.get("exclusive", chunk["kind"] == "heavy") or any(
                    c.get("exclusive", c["kind"] == "heavy") for c in running.values())
                free = avail()
                if (len(running) >= max(1, jobs) or heavy_involved or free is None
                        or free < min_free_gb * (len(running) + 1)):
                    reap()
                    continue
            pending.pop(0)
            running[pool.submit(one, i, chunk)] = chunk
        while running:
            reap()
    results.sort(key=lambda r: r["chunk"])
    totals: Dict[str, int] = {}
    for r in results:
        for k, v in r["counts"].items():
            totals[k] = totals.get(k, 0) + v
    incomplete = [r["chunk"] for r in results if r["incomplete"]]
    rc = stop["rc"] or (3 if incomplete or pending else (1 if any(r["rc"] == 1 for r in results) else 0))
    summary = {"rc": rc, "stopped": stop["why"], "not_started": [i for i, _ in pending], "incomplete": incomplete,
               "totals": totals, "chunks": results}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra: List[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--select", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--min-free-gb", type=float, default=DEFAULT_MIN_FREE_GB)
    ap.add_argument("--chunk-seconds", type=float, default=900.0)
    ap.add_argument("--traces", nargs="*", default=[])
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args(argv)
    ld = _ld()
    selection = [ln.strip() for ln in (REPO / args.select).read_text(encoding="utf-8").splitlines() if ln.strip()]
    durations, never, gaps = ld.load_all_detail()
    shared = ld.load_shared(REPO / t for t in args.traces) if args.traces else None
    costs = ld.load_fixture_costs(REPO / t for t in args.traces) if args.traces else None
    chunks = plan(selection, durations, gaps, shared, args.chunk_seconds, ld.FAST_LIMIT_S, costs)
    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)
    unknown = [n for n in selection if n not in durations]
    (out / "plan.json").write_text(json.dumps({
        "selection": args.select, "n": len(selection), "chunks": len(chunks),
        "heavy_chunks": sum(1 for c in chunks if c["kind"] == "heavy"),
        "estimate_s_serial": round(sum(c["estimate_s"] for c in chunks)), "unknown": unknown,
        "never_passed": sorted(set(selection) & never),
        "fixture_cost_unknown": [x for c in chunks for x in c["fixture_cost_unknown"]],
        "uncertain_ack_needed": plan_uncertainty(chunks), "exclusive_chunks": sum(1 for c in chunks if c["exclusive"]),
        "jobs": args.jobs, "min_free_gb": args.min_free_gb,
        "chunk_list": [{"kind": c["kind"], "exclusive": c["exclusive"], "n": len(c["nodeids"]),
                        "estimate_s": round(c["estimate_s"]), "first": c["nodeids"][0]} for c in chunks]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[chunked] plan n={len(selection)} chunks={len(chunks)} heavy={sum(1 for c in chunks if c['kind'] == 'heavy')}"
          f" estimate_serial={sum(c['estimate_s'] for c in chunks):.0f}s unknown={len(unknown)}", flush=True)
    if args.plan_only:
        return 0
    summary = run(chunks, out, args.jobs, args.min_free_gb, extra)
    print(f"[chunked] done rc={summary['rc']} totals={summary['totals']} stopped={summary['stopped'] or '-'} "
          f"incomplete={summary['incomplete']} not_started={len(summary['not_started'])}", flush=True)
    return int(summary["rc"])


if __name__ == "__main__":
    raise SystemExit(main())
