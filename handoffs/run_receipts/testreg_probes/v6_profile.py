#!/usr/bin/env python3
"""TESTREG Task 2.4：V-6 慢因收據產生器（docs/TESTREG_SPEC.md Task 2.4；契約 `v6_profile`、`types.v6_profile_receipt`）。

子命令（cwd＝repo 根；`PYTHONPATH=.`）：
  run      D10 執行器（`scripts/framepath_affected_gate.Runner`，記錄器經 tests/conftest.py 開）逐 nodeid 一次 pytest 呼叫跑
           `tests/feature_engineering/test_failopen_correctness.py` 之全部 test_v6_*（收集所得之參數化 nodeid）。各項
           以自己的 tmp_path 生成、無模組層共享 fixture，逐項呼叫不改其計算；為使單次背景執行不跨越單一長呼叫，`--max-seconds`
           預設 1：每段只開一個呼叫，之後於呼叫之間停下（rc 3），同命令接續（同狀態指紋之結果沿用）。
  profile  以 cProfile 單項執行 `--nodeid`（pytest 子行程，記錄器開；包裝見 v6_prof_site/v6_prof_core.py），主執行緒 stats
           寫 `<out>/profile/<slug>.prof`，執行緒／子行程與定期 partial 留 `<out>/profile/<slug>.parts/`。
  receipt  由 run 之結果 meta（ledger_new）取記錄器 ledger 之逐項 duration_s、由 .prof 取前 30 累計熱點（cumtime 由大到小），
           加上歸類與碼證（`--classification`、`--evidence`，人工判讀後給定）寫收據，寫入前依契約與驗收同一檢查自驗。

不做：縮小資料窗、減少 symbol、改測試（SPEC Task 2.4 不可做）。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pstats
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from scripts import framepath_affected_gate as g  # noqa: E402
from scripts import testreg  # noqa: E402

TARGET = "tests/feature_engineering/test_failopen_correctness.py"
OUT = REPO / "handoffs/run_receipts/testreg_probes/v6_run"
RECEIPT = REPO / "handoffs/run_receipts/testreg-v6-profile.json"


def _env() -> dict:
    return dict(os.environ, PYTHONPATH=str(REPO))


def _slug(nodeid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", nodeid.split("::", 1)[1])


def v6_functions() -> list:
    tree = ast.parse((REPO / TARGET).read_text(encoding="utf-8"))
    return sorted(n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_v6_"))


def v6_nodeids(env: dict) -> list:
    """收集所得之全部 test_v6_* nodeid（參數化展開），依檔內順序；函式層名集合須等於 AST 導出者。"""
    ids = [n for n in g.collect(TARGET, REPO, env) if n.split("::")[-1].split("[")[0].startswith("test_v6_")]
    names = {n.split("::")[-1].split("[")[0] for n in ids}
    if names != set(v6_functions()):
        raise SystemExit(f"收集之 test_v6_* 函式 {sorted(names)} ≠ AST {v6_functions()}")
    return ids


def cmd_run(args) -> int:
    env = _env()
    ids = v6_nodeids(env)
    ledger = REPO / testreg.load_schema(REPO)["ledger"]["dir"]
    runner = g.Runner(OUT, args.max_seconds, len(ids), ledger_dir=ledger)
    g._RUNNER = runner
    try:
        for nid in ids:
            meta = OUT / "junit" / f"{_slug(nid)}.meta.json"
            if args.skip_done and meta.is_file():
                m = json.loads(meta.read_text(encoding="utf-8"))
                if m.get("rc") in g.RUN_RC_OK and m.get("ledger_new"):
                    # 已完成之項（結果 meta＋ledger session 齊備）不重跑：期間只提交文件而使狀態指紋改變時用
                    runner.done += 1
                    print(f"{nid}: skip-done（{m.get('seconds')}s）", flush=True)
                    continue
            key = g.state_key(REPO, TARGET, 0, env) + "|" + nid
            rc, res = runner.run(TARGET, OUT / "junit" / f"{_slug(nid)}.xml", REPO, env, [nid], (), key, [nid],
                                 phase="V6")
            print(f"{nid}: rc={rc} outcome={res.get(nid, {}).get('outcome')}", flush=True)
    except g.Paused as exc:
        runner.progress("paused", "", [], state="paused")
        print(f"PAUSED（{exc}）；同命令接續", flush=True)
        return 3
    runner.progress("done", "", [], state="done")
    print("DONE", flush=True)
    return 0


def cmd_profile(args) -> int:
    """經 v6_prof_site/v6_prof_core.py：主執行緒與 `python -m cProfile -m pytest` 同義，另錄執行緒與 spawn 子行程、
    每 --every 秒寫 partial（背景 2 小時上限截斷時留存）。完整結束時主執行緒檔複製為 <OUT>/profile/<slug>.prof＝收據熱點來源；
    其餘檔留在 <slug>.parts/ 供判讀。"""
    slug = _slug(args.nodeid)
    parts = OUT / "profile" / f"{slug}.parts"
    if parts.exists() and any(parts.iterdir()):
        raise SystemExit(f"{parts} 已有內容，先移走再跑")
    site = Path(__file__).resolve().parent / "v6_prof_site"
    env = dict(_env(), PYTHONPATH=f"{site}{os.pathsep}{REPO}", V6_PROF_EVERY=str(args.every))
    env.pop("V6_PROF_DIR", None)
    cmd = [sys.executable, str(site / "v6_prof_core.py"), str(parts), "--", *g.PYTEST_FLAGS, args.nodeid]
    print("cmd:", " ".join(cmd), flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO), env=env)
    g.restore_generated(REPO)
    st = json.loads((parts / "status.json").read_text(encoding="utf-8"))
    mains = sorted(parts.glob("main-*-t0.prof"))
    if st.get("complete") and len(mains) == 1:
        shutil.copyfile(mains[0], OUT / "profile" / f"{slug}.prof")
    print(f"rc={proc.returncode} complete={st.get('complete')} elapsed={time.time() - t0:.1f}s parts={parts}", flush=True)
    return proc.returncode


def durations() -> dict:
    """{nodeid: duration_s}：各 nodeid 之結果 meta 之 ledger_new 中、該 nodeid 之記錄器 test_record。"""
    led = REPO / testreg.load_schema(REPO)["ledger"]["dir"]
    out = {}
    for meta in sorted((OUT / "junit").glob("*.meta.json")):
        m = json.loads(meta.read_text(encoding="utf-8"))
        for sid in m.get("ledger_new") or []:
            for line in (led / sid).read_text(encoding="utf-8").splitlines():
                rec = json.loads(line) if line.strip() else {}
                if rec.get("kind") == "test" and rec.get("nodeid", "").startswith(TARGET + "::test_v6_"):
                    out[rec["nodeid"]] = float(rec["duration_s"])
    return out


def hotspots(prof: Path, n: int) -> list:
    st = pstats.Stats(str(prof))
    rows = sorted(st.stats.items(), key=lambda kv: kv[1][3], reverse=True)[:n]
    return [{"function": f"{fn}:{line}({name})", "cumtime_s": round(float(v[3]), 6)} for (fn, line, name), v in rows]


def cmd_receipt(args) -> int:
    schema = testreg.load_schema(REPO)
    durs = durations()
    slowest = max(durs, key=durs.get)
    prof = OUT / "profile" / f"{_slug(slowest)}.prof"
    r = {"durations_s": durs, "slowest": slowest,
         "hotspots_top30": hotspots(prof, schema["v6_profile"]["hotspot_count"]),
         "classification": args.classification, "evidence": list(args.evidence),
         "window_and_symbols_unchanged": True, "test_changed": False, "outcomes_sha256_before": None,
         "outcomes_sha256_after": None, "mutation_receipt": None}
    errs = testreg.validate_shape(r, {"type": "types.v6_profile_receipt"}, schema)
    names = {k.split("::")[-1].split("[")[0] for k in durs}
    if names != set(v6_functions()):
        errs.append(f"durations_s 函式層名 {sorted(names)} ≠ AST {v6_functions()}")
    for ev in r["evidence"]:
        path, line = ev.rsplit(":", 1)
        p = REPO / path
        if not p.is_file() or int(line) > len(p.read_text(encoding="utf-8", errors="replace").splitlines()):
            errs.append(f"evidence {ev} 不存在")
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1
    RECEIPT.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {RECEIPT.relative_to(REPO)} slowest={slowest} {durs[slowest]:.1f}s", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--max-seconds", type=float, default=1.0)
    p.add_argument("--skip-done", action="store_true",
                   help="結果 meta（rc 0/1 且有 ledger_new）已存在之項不重跑（狀態指紋只因文件提交而變時用）")
    p = sub.add_parser("profile")
    p.add_argument("--nodeid", required=True)
    p.add_argument("--every", type=float, default=600.0, help="partial 快照間隔秒數")
    p = sub.add_parser("receipt")
    p.add_argument("--classification", required=True)
    p.add_argument("--evidence", nargs="+", required=True)
    args = ap.parse_args(argv)
    return {"run": cmd_run, "profile": cmd_profile, "receipt": cmd_receipt}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
