#!/usr/bin/env python3
"""SPLITUNIFY `Task 10.2`／`Task 10.4`：IC 事件 run 之改前／改後逐鍵 diff 與基準捕獲。

規格：`docs/SPLITUNIFY_SPEC.md` v7 `R5-C9` 7.；施工清單：`docs/SPLITUNIFY_TODO.md` §C-10。

用法（三元組固定，寫入各檔 meta，比對時逐值對證）：
  # 捕獲基準（一律**當下重跑**事件路徑取值；不可變檔以 O_EXCL 建立）
  venv/bin/python scripts/splitunify_ic_event_report_diff.py --capture \
      --out tests/golden/splitunify/ic_event_report_baseline.pre_task_10_2.json \
      --batch <import_id> --ff-run <config_hash> --config-override none

  # 兩份基準互比（允許差異，寫 receipt）
  ... --mode allow-diff --baseline <A.json> --candidate <B.json>

  # 嚴格比對（candidate **只准當下重跑**；以檔路徑充當 candidate ⇒ 拒收）
  ... --mode strict --baseline <post.json> --candidate-run --batch <id> --ff-run <hash> --config-override none

🔴 **具名偏離（交 B10A 審碼輪裁）**：清單寫「IC 報告逐鍵 diff」。本腳本捕獲之 payload 不是
整份 IC 報告 JSON（那需物化全特徵矩陣、分鐘級），而是**事件路徑之可證偽面**：逐事件之
特徵列鍵與標籤值、隔離列數、canonical 邊界、stage3 實際保留之列時刻，以及固定特徵集之條件 IC。
`R5-C9` 7. 所要求之「條件 IC 前後值」與 `Task 10.4` 之 embargo mutation 皆落在此面內；
整份報告之其餘鍵由 G-2（非事件 run 逐位元組不變）守。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

#: 固定特徵集（決定性、與事件無關）——條件 IC 之比對面。只依賴當根者優先，便於人工對證。
_IC_FEATURES = [
    "1h_L1_momentum_BOP", "1h_L1_momentum_RSI", "1h_L1_momentum_ROC",
    "12h_L1_momentum_BOP", "12h_L1_momentum_RSI",
]
_EVENTS_DIR = REPO / "data_cache/events"
_FEATURES_DIR = REPO / "data_cache/features"


def _canonical_bytes(payload: Dict[str, Any]) -> bytes:
    clean = json.loads(json.dumps(payload))
    clean.pop("generated_at", None)
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _run_dir(ff_run: str, symbols: Optional[set] = None) -> Path:
    """以 `config_hash` 定位 run 目錄。

    🔴 同一 `config_hash` 可存在於多個 symbol（實測 BCHUSDT 與 ETHUSDT 同雜湊）⇒ 必須以事件批之
    symbol 篩選，否則會取到別的 symbol 之 run 而被 service 以「無同 symbol 事件」擋下。
    篩選後仍多於一個 ⇒ fail-closed（不猜）。
    """
    hits = sorted(_FEATURES_DIR.glob(f"*/*/{ff_run}"))
    if symbols:
        hits = [h for h in hits if h.parent.parent.name in symbols]
    if not hits:
        raise SystemExit(f"ERROR: 找不到 FF run {ff_run}（symbols={sorted(symbols or [])}）")
    if len(hits) > 1:
        raise SystemExit(f"ERROR: FF run {ff_run} 在多個路徑命中：{[str(h) for h in hits]}")
    return hits[0]


def _collect(batch_id: str, ff_run: str, config_override: str) -> Dict[str, Any]:
    """**當下重跑生產路徑**（`ICAnalysisService._run_event_label_stages`）並收集可證偽面。

    🔴 B10A 審碼 `CODEX-R30-P1-03`：本函式原本自行組裝 pipeline／`isolation_terms_rows`／
    `holdout_boundary`，等於第二份實作——生產 service 之 embargo／isolation 交接被移除時仍會綠。
    改為**呼叫 service 之五階段入口**，逐鍵取其回傳（`event_timestamps`／`event_label_values`／
    `label_window_rows`／`lookahead_depth_rows`／`purge_rows`／收據雜湊），邊界再由該值導出。
    """
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.core.split_preview import holdout_boundary

    batch_path = _EVENTS_DIR / f"{batch_id}.json"
    if not batch_path.is_file():
        raise SystemExit(f"ERROR: 找不到事件批 {batch_path}")
    _syms = {str(r["symbol"]) for r in json.loads(batch_path.read_text())["records"]}
    run_dir = _run_dir(ff_run, _syms)
    run_tf = run_dir.parent.name
    symbol = run_dir.parent.parent.name
    if not batch_path.is_file():
        raise SystemExit(f"ERROR: 找不到事件批 {batch_path}")
    batch = json.loads(batch_path.read_text())
    recs = batch["records"]
    decl = batch["lookahead_declaration"]["lookahead_bars_declared"]
    trigger_tfs = sorted({str(r["timeframe"]) for r in recs})
    spec = {
        "entry_price_semantic": "trigger_open",
        "label_return_mode": "open_to_horizon_close",
        "horizon_bars": int(decl[trigger_tfs[0]]),
        "decision_offset_bars": 0,
    }

    class _Req:  # 最小 request：service 只讀這幾個屬性
        event_import_id = batch["import_id"]

    _Req.symbol = symbol
    _Req.timeframe = run_tf
    _Req.config_override = None if config_override in ("none", "", None) else json.loads(config_override)

    event_batch = {
        "records": tuple(recs),
        "event_label_spec": spec,
        "lookahead_bars_declared": decl,
    }
    staged = ICAnalysisService._run_event_label_stages(
        _Req(), event_batch,
        features_path=None, meta_path=None,
        feature_manifest_path=str(run_dir / "feature_manifest.json"),
    )
    prepared = staged["prepared"]
    label_by_key = dict(staged["event_label_values"])
    ts_keys = sorted(int(x) for x in staged["event_timestamps"])
    iso_window = int(staged["label_window_rows"])
    iso_depth = int(staged["lookahead_depth_rows"])

    ts = pd.read_parquet(run_dir / "timestamps.parquet")["timestamp"].to_numpy().astype(np.int64) * 1000
    feat_index = pd.to_datetime(ts, unit="ms")
    plan = holdout_boundary(
        feat_index, oos_test_size=0.2,
        purge_gap=max(5, iso_window), embargo=max(0, iso_depth),
    )
    boundary = {
        "test_start_ms": None if plan["test_start_ms"] is None else int(plan["test_start_ms"]),
        "train_end_ms": None if plan["train_end_ms"] is None else int(plan["train_end_ms"]),
        "n_test_rows": int(len(plan["test_row_index"])),
        "n_train_rows": int(len(plan["train_row_index"])),
    }

    index_set = set(int(x) for x in ts)
    owners = {int(k): v for k, v in dict(staged.get("event_label_owners") or {}).items()}
    decision_by_id = {w.event_id: int(w.decision_at_ms) for w in prepared.windows}
    rows: List[Dict[str, Any]] = []
    for key in ts_keys:
        eid = owners.get(key, "")
        rows.append({
            "event_id": eid,
            "decision_at_ms": decision_by_id.get(eid),
            "feature_row_key_ms": int(key),
            "row_in_feature_index": bool(int(key) in index_set),
            "label_value": None if label_by_key.get(key) is None else float(label_by_key[key]),
        })
    rows.sort(key=lambda r: (r["event_id"], r["feature_row_key_ms"]))
    consumed = [r["feature_row_key_ms"] for r in rows if r["row_in_feature_index"] and r["label_value"] is not None]

    ic: Dict[str, Optional[float]] = {}
    for name in _IC_FEATURES:
        f = run_dir / "raw" / f"{name}.parquet"
        if not f.is_file():
            ic[name] = None
            continue
        col = pd.read_parquet(f)
        s = pd.Series(col[col.columns[0]].to_numpy().astype(np.float64), index=ts)
        xs, ys = [], []
        for k in consumed:
            v = label_by_key.get(k)
            if v is None or k not in s.index:
                continue
            x = float(s.loc[k])
            if np.isfinite(x) and np.isfinite(v):
                xs.append(x); ys.append(float(v))
        ic[name] = None if len(xs) < 3 else float(pd.Series(xs).corr(pd.Series(ys), method="spearman"))

    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True)
    return {
        "meta": {
            "batch": batch_id,
            "ff_run": ff_run,
            "ff_run_timeframe": run_tf,
            "config_override": config_override,
            "code_commit": head.stdout.strip()[:12] if head.returncode == 0 else "unknown",
            "collector": "ICAnalysisService._run_event_label_stages（生產路徑）",
        },
        "n_events": len(rows),
        "n_consumed": len(consumed),
        "isolation": {"label_window_rows": iso_window, "lookahead_depth_rows": iso_depth},
        "purge_rows": int(staged["purge_rows"]),
        "boundary": boundary,
        "analysis_alignment_receipt_hash": staged["analysis_alignment_receipt_hash"],
        "events": rows,
        "conditional_ic": ic,
    }


def _write_once(path: Path, payload: Dict[str, Any], authorize: Optional[str]) -> int:
    body = _canonical_bytes(payload)
    digest = hashlib.sha256(body).hexdigest()
    out = dict(payload)
    out["canonical_sha256"] = digest
    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists():
        old = json.loads(path.read_text()).get("canonical_sha256", "")
        if not authorize:
            print(f"ERROR: {path} 已存在（sha256 {old[:8]}）；覆蓋須帶 --authorize <old8>:<new8>")
            return 1
        want = f"{old[:8]}:{digest[:8]}"
        if authorize != want:
            print(f"ERROR: --authorize 不符（需 {want}，得 {authorize}）")
            return 1
        path.write_text(text)
        print(f"REFROZEN {path}: {old[:8]} → {digest[:8]}")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    print(f"CAPTURED {path}: sha256={digest[:8]} n_events={payload['n_events']} n_consumed={payload['n_consumed']}")
    return 0


def _diff(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    diffs: List[str] = []
    for k in ("n_events", "n_consumed", "isolation", "boundary", "analysis_alignment_receipt_hash"):
        if a.get(k) != b.get(k):
            diffs.append(f"{k}: {a.get(k)} → {b.get(k)}")
    ea = {r["event_id"]: r for r in a.get("events", [])}
    eb = {r["event_id"]: r for r in b.get("events", [])}
    for eid in sorted(set(ea) | set(eb)):
        ra, rb = ea.get(eid), eb.get(eid)
        if ra != rb:
            diffs.append(f"events[{eid}]: {ra} → {rb}")
    ia, ib = a.get("conditional_ic", {}), b.get("conditional_ic", {})
    for name in sorted(set(ia) | set(ib)):
        if ia.get(name) != ib.get(name):
            diffs.append(f"conditional_ic[{name}]: {ia.get(name)} → {ib.get(name)}")
    return diffs


def _assert_same_triple(base: Dict[str, Any], batch: str, ff_run: str, cfg: str) -> Optional[str]:
    m = base.get("meta", {})
    got = (m.get("batch"), m.get("ff_run"), m.get("config_override"))
    want = (batch, ff_run, cfg)
    return None if got == want else f"三元組不符：baseline {got} vs 本次 {want}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", action="store_true", help="當下重跑並落基準檔")
    ap.add_argument("--out")
    ap.add_argument("--authorize", help="覆蓋既有基準：<old8>:<new8>")
    ap.add_argument("--mode", choices=["allow-diff", "strict"])
    ap.add_argument("--baseline")
    ap.add_argument("--candidate", help="僅 allow-diff：另一份基準檔路徑")
    ap.add_argument("--candidate-run", action="store_true", help="strict：candidate＝當下重跑（唯一合法來源）")
    ap.add_argument("--batch")
    ap.add_argument("--ff-run")
    ap.add_argument("--config-override", default="none")
    ap.add_argument("--receipt-dir", default="handoffs/run_receipts")
    a = ap.parse_args(argv)

    if a.capture:
        if not (a.out and a.batch and a.ff_run):
            print("ERROR: --capture 需 --out／--batch／--ff-run"); return 1
        return _write_once(Path(a.out), _collect(a.batch, a.ff_run, a.config_override), a.authorize)

    if a.mode == "allow-diff":
        if not (a.baseline and a.candidate):
            print("ERROR: allow-diff 需 --baseline 與 --candidate 兩個檔路徑"); return 1
        base = json.loads(Path(a.baseline).read_text())
        cand = json.loads(Path(a.candidate).read_text())
        # 🔴 B10A 審碼 `CODEX-R30-P1-02`：兩份基準之三元組須相同，否則「不同事件批」也會 diff=0。
        mb, mc = base.get("meta", {}), cand.get("meta", {})
        tb = (mb.get("batch"), mb.get("ff_run"), mb.get("config_override"))
        tc = (mc.get("batch"), mc.get("ff_run"), mc.get("config_override"))
        if tb != tc:
            print(f"ERROR: 兩份基準之三元組不符：{tb} vs {tc}")
            return 1
        diffs = _diff(base, cand)
        rec = Path(a.receipt_dir) / "splitunify-ic-event-report-diff.txt"
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(
            f"baseline={a.baseline}\ncandidate={a.candidate}\n"
            f"baseline_meta={json.dumps(base.get('meta'), ensure_ascii=False)}\n"
            f"candidate_meta={json.dumps(cand.get('meta'), ensure_ascii=False)}\n"
            f"n_diffs={len(diffs)}\n" + "\n".join(diffs) + "\n"
        )
        print(f"ALLOW-DIFF: {len(diffs)} 項差異，receipt → {rec}")
        for d in diffs[:12]:
            print("  ·", d)
        return 0

    if a.mode == "strict":
        if a.candidate:
            print("ERROR: strict 之 candidate 只准當下重跑（--candidate-run）；拒收檔路徑"); return 1
        if not (a.baseline and a.candidate_run and a.batch and a.ff_run):
            print("ERROR: strict 需 --baseline／--candidate-run／--batch／--ff-run"); return 1
        base = json.loads(Path(a.baseline).read_text())
        bad = _assert_same_triple(base, a.batch, a.ff_run, a.config_override)
        if bad:
            print(f"ERROR: {bad}"); return 1
        cand = _collect(a.batch, a.ff_run, a.config_override)
        diffs = _diff(base, cand)
        if diffs:
            print(f"STRICT FAIL: {len(diffs)} 項差異")
            for d in diffs[:20]:
                print("  ·", d)
            return 1
        print("STRICT PASS: 逐鍵 diff 為空")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
