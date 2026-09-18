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
整份 IC 報告 JSON，而是**事件路徑之可證偽面**：逐事件之特徵列鍵與標籤值、隔離列數、
canonical 邊界、stage3 實際保留之列時刻，以及固定特徵集之條件 IC。
`R5-C9` 7. 所要求之「條件 IC 前後值」與 `Task 10.4` 之 embargo mutation 皆落在此面內；
整份報告之其餘鍵由 G-2（非事件 run 逐位元組不變）守。

🔴 **基準檔有兩代，語意不同，不得混用**（B10A 閉合輪 `CODEX-R32-P1-01`）：
  - `ic_event_report_baseline.{pre,post}_task_10_2.json`＝**凍結之歷史對照**，由本輪修補**之前**
    的 collector 產生；其 `conditional_ic` 是**腳本自算**之 Spearman，母體＝全部 165 個 consumed
    事件。兩檔同源可比，記錄的是 `Task 10.2` 之效果，**不再重新捕獲**。
  - `ic_event_report_baseline.prod_task_10_4.json`＝**生產端基準**，`conditional_ic` 取自
    `ICFilterOrchestrator.analyze` 之 `summary_table[*].ic_mean`，母體＝**canonical 測試段內之
    41 個事件**（`split_mask.test_rows`）。`--mode strict` 一律對這一份。
  🔴 兩者數值差很大且會變號（實測 12h RSI：自算 +0.0698 vs 生產端 −0.1920），因為母體與
     特徵預處理階段都不同——**不是** bug，是「腳本的第二份實作」與「使用者實際看到的值」之差。

🔴 **本腳本不得自行計算任何統計量**：條件 IC、stage3 消費數、切分／purge／embargo 一律只從
生產端報告讀（`_production_evidence`）。修補前實跑證據：monkeypatch `analyze` 直接 raise
⇒ 仍 `STRICT PASS`；`purge_rows` 156→155 ⇒ 仍 `STRICT PASS`。修補後三條 mutation 全數轉紅。
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
_TF_MS = {"1h": 3_600_000, "4h": 14_400_000, "12h": 43_200_000, "1d": 86_400_000}
_EVENTS_DIR = REPO / "data_cache/events"
_FEATURES_DIR = REPO / "data_cache/features"


#: 具名子集之額外特徵數（本比對面五個 L1 之外再取的 L1 欄，依檔名字母序，決定性）。
_SUBSET_EXTRA = 25


def _materialize_named_subset(service, symbol: str, run_tf: str, ff_run: str, run_dir: Path):
    """以**生產端** `_write_features_h5`／`_build_ic_metadata_from_run` 物化一組**具名子集**。

    🔴 **具名偏離（本輪新增，交 r4 裁）**：`_materialize_features_for_ic` 會先
    `_feature_library.load()` 把整個 run 讀進 DataFrame。本 run 之 `raw/` 為 7.5 GB
    （含 L2 chunk，單檔上百 MB、數千欄），本機 8 GB RAM ⇒ 實跑兩次皆 `rc=137`（OOM）。
    ⇒ 改以本比對面之五個 L1 欄＋字母序前 `_SUBSET_EXTRA` 個 L1 欄物化。
    影響：`ic_mean` 之母體與 stage5／stage6 之特徵宇宙是子集；**逐特徵** IC 本身由
    `compute_ic` 逐欄算，不因其他欄存在與否改變（此點未獨立證明，列為本輪殘留）。
    """
    import pandas as _pd

    ts = _pd.read_parquet(run_dir / "timestamps.parquet")["timestamp"].to_numpy()
    index = _pd.to_datetime(ts.astype("int64") * 1000, unit="ms")
    names: List[str] = list(_IC_FEATURES)
    for p in sorted((run_dir / "raw").glob("*_L1_*.parquet")):
        if len(names) >= len(_IC_FEATURES) + _SUBSET_EXTRA:
            break
        if p.stem not in names:
            names.append(p.stem)
    cols: Dict[str, Any] = {}
    for n in names:
        f = run_dir / "raw" / f"{n}.parquet"
        if not f.is_file():
            raise SystemExit(f"ERROR: 子集缺特徵 parquet {f}（不得靜默略過）")
        c = _pd.read_parquet(f)
        cols[n] = c[c.columns[0]].to_numpy().astype(np.float64)
    feats = _pd.DataFrame(cols, index=index)

    from api.services.ic_analysis_service import ICAnalysisService

    cache = REPO / "data_cache/reports/ic_ingest_cache"
    cache.mkdir(parents=True, exist_ok=True)
    key = f"{symbol}_{run_tf}_{ff_run}_splitunify_subset{len(names)}"
    h5, meta = cache / f"{key}.h5", cache / f"{key}_meta.json"
    if h5.exists():
        h5.unlink()
    ICAnalysisService._write_features_h5(h5, symbol, run_tf, feats)
    meta.write_text(json.dumps(
        service._build_ic_metadata_from_run(symbol, run_tf, ff_run, list(feats.columns)),
        ensure_ascii=False,
    ), encoding="utf-8")
    return str(h5.resolve()), str(meta.resolve())


def _production_evidence(
    symbol: str, run_tf: str, ff_run: str, import_id: str,
    event_batch: Dict[str, Any], run_dir: Path, cfg_override: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """走**生產端** `_run_scan_cell`（內含 `ICFilterOrchestrator.analyze`）取證據。

    🔴 `CODEX-R32-P1-01`：本函式存在的唯一理由是「不要有第二份實作」。逐特徵條件 IC、
    stage3 實際消費之事件數、canonical 切分／purge／embargo 一律**只從生產端報告讀**，
    本腳本不再自行計算任何統計量。生產端拋錯即整支 fail（不得吞例外回退自算）。
    """
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    # 🔴 **request 必須是生產端之 model，config_override 必須由生產端之 `_build_config_override`
    #    導出**：`event_filter.enabled` 只在該函式裡因 `event_import_id` 而開啟。手搓最小 stub ＋
    #    `config_override={}` 會讓 orchestrator 回 `event_filter.mode="none"` ⇒ 整份報告其實是
    #    **全樣本 IC**，`statistic_kind` 等條件 IC 標記全部不存在，而 `analysis_status` 仍是 ok
    #    （實跑證實；同型事故已記在 `ic_analysis_service.py:3145-3151` 之 UAT B17 註解）。
    request = ICAnalyzeRequest(
        symbol=symbol, timeframe=run_tf, config_hash=ff_run,
        mode="longitudinal", event_import_id=import_id,
        config_override=dict(cfg_override) if cfg_override else None,
    )
    service = ICAnalysisService()
    cfg = service._build_config_override(request)
    features_path, meta_path = _materialize_named_subset(service, symbol, run_tf, ff_run, run_dir)
    # 事件路徑之 `labels_path` 為空 ⇒ `kline_reader` 必須非 None（stage2 生成鷹架主線標籤）。
    kline_reader = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
    out = ICAnalysisService._run_scan_cell(
        service, create_ic_analyzer, request, event_batch,
        features_path=features_path, meta_path=meta_path,
        feature_manifest_path=str(run_dir / "feature_manifest.json"),
        labels_path=None, kline_reader=kline_reader,
        config_override=dict(cfg or {}),
        original_embargo=int((cfg_override or {}).get("embargo") or 0),
    )
    report = out["report"]
    meta = report.get("metadata") or {}
    ef = meta.get("event_filter") or {}
    split = meta.get("ic_train_test_split") or {}
    su = meta.get("split_unify") or {}

    # 🔴 **事件分支 fail-closed**：`event_filter.mode == "none"` 表示 orchestrator 根本沒走
    #    條件 IC 路徑，`summary_table.ic_mean` 是**全樣本主線 IC**——拿它當條件 IC 就是偷換
    #    統計量，且 `analysis_status` 仍為 ok、從輸出看不出來（本輪實跑踩過一次）。
    if str(ef.get("mode") or "none") == "none":
        raise SystemExit(
            "ERROR: 生產端回 event_filter.mode=none（未走條件 IC 分支）——"
            "config_override 須由 `_build_config_override` 導出（event_import_id ⇒ enabled=True）"
        )
    if ef.get("statistic_kind") != "conditional_ic":
        raise SystemExit(
            f"ERROR: 生產端之 statistic_kind={ef.get('statistic_kind')!r}，非 'conditional_ic'（fail-closed）"
        )

    # 逐特徵條件 IC：只取本比對面之特徵；缺席即 None（不造值）。
    by_name = {
        str(r.get("feature_name")): r.get("ic_mean")
        for r in (report.get("summary_table") or [])
        if isinstance(r, dict)
    }
    cond = {
        name: (None if by_name.get(name) is None else float(by_name[name]))
        for name in _IC_FEATURES
    }
    evidence = {
        "entrypoint": "ICAnalysisService._run_scan_cell → ICFilterOrchestrator.analyze（生產端）",
        "named_deviation": "掃描格恆為報酬版（label_mode_requested=return_rule）；本批亦為報酬版",
        "analysis_status": report.get("analysis_status"),
        "oos_guarantees": report.get("oos_guarantees"),
        "capability": out.get("capability"),
        "n_events_staged": out.get("n_events"),
        "statistic_kind": ef.get("statistic_kind"),
        "label_source": ef.get("label_source"),
        "consumed_event_count": ef.get("consumed_event_count"),
        "split_mask": ef.get("split_mask"),
        "ic_mean_source": (meta.get("ic_window_disclosure") or {}).get("ic_mean_source"),
        "split_unify": {k: su.get(k) for k in ("n_test", "split_authority", "boundary_hash", "reason")},
        "ic_train_test_split": {
            k: split.get(k) for k in (
                "applied", "purge_gap", "embargo", "effective_horizon",
                "train_rows", "test_rows", "train_time_bounds", "test_time_bounds",
                "purge_gap_source", "event_label_window_rows", "lookahead_depth_rows",
                "oos_guarantees",
            )
        },
        "isolation": meta.get("isolation"),
        "split_method": meta.get("split_method"),
        "oos_downgrade": meta.get("oos_downgrade"),
    }
    return {"conditional_ic": cond, "evidence": evidence}


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
    from momentum.Analysis.ic_filter_orchestrator import _build_holdout_split_plan
    from momentum.factories import load_ic_config

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
    # 🔴 B10A 閉合輪 `CODEX-R31-P1-02`：邊界**不得**在腳本內自算（原本寫死 oos_test_size=0.2，
    #    生產端 builder 被改也不會紅）。改為呼叫**生產端**之 `_build_holdout_split_plan`，
    #    切分參數取自生產端之 `load_ic_config`（含 `config_override`），embargo 由 service
    #    之深度交接抬高——與 IC 事件 run 同一條路。
    cfg_override = _Req.config_override
    ic_cfg = load_ic_config(api_override=cfg_override) if cfg_override else load_ic_config()
    try:
        ic_cfg.embargo = max(int(getattr(ic_cfg, "embargo", 0) or 0), int(iso_depth))
    except Exception:  # dataclass frozen 等情形
        import dataclasses as _dc
        ic_cfg = _dc.replace(ic_cfg, embargo=max(int(getattr(ic_cfg, "embargo", 0) or 0), int(iso_depth)))
    feats = pd.DataFrame(index=feat_index)
    expected_freq = pd.Timedelta(milliseconds=int(_TF_MS[run_tf]))
    built = _build_holdout_split_plan(
        feats, ic_cfg, symbol, expected_freq, purge_gap=max(int(staged["purge_rows"]), iso_window),
    )
    if isinstance(built, tuple):
        train_plan, test_plan = built
        boundary = {
            "test_start_ms": int(test_plan.time_bounds[0].value // 10**6)
            if hasattr(test_plan.time_bounds[0], "value") else int(test_plan.time_bounds[0]),
            "train_end_ms": int(train_plan.time_bounds[1].value // 10**6)
            if hasattr(train_plan.time_bounds[1], "value") else int(train_plan.time_bounds[1]),
            "n_test_rows": int(len(test_plan.row_index)),
            "n_train_rows": int(len(train_plan.row_index)),
            "oos_test_size": float(getattr(ic_cfg, "oos_test_size", float("nan"))),
            "embargo": int(getattr(ic_cfg, "embargo", 0) or 0),
            "builder": "ic_filter_orchestrator._build_holdout_split_plan（生產端）",
        }
    else:
        boundary = {"skipped": str(getattr(built, "reason", built))}

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

    # 🔴 B10A 閉合輪 `CODEX-R32-P1-01`：條件 IC **不得**在腳本內自算。
    #    原本以 `run_dir/raw/<feature>.parquet` 重跑 Spearman ＝ 第二份實作：生產端
    #    `ICFilterOrchestrator.analyze` 被炸掉、stage3／purge 證據被改壞時，strict 全部假綠
    #    （實跑：analyze 直接 raise ⇒ 仍 `STRICT PASS`；`purge_rows` 156→155 ⇒ 仍 `STRICT PASS`）。
    #    改為呼叫**生產端**之 `ICAnalysisService._run_scan_cell`——它自己做 staging、抬 embargo、
    #    造 analyzer、跑 `analyze`，並套三個注入（三元組回綁／期間對齊／隔離來源）。
    #    具名偏離：`_run_scan_cell` 恆為報酬版（`label_mode_requested="return_rule"`），
    #    本批亦為報酬版 ⇒ 與主路徑同解；偏離揭露於 payload 之 `production_evidence.entrypoint`。
    prod = _production_evidence(
        symbol, run_tf, ff_run, str(batch["import_id"]), event_batch, run_dir, cfg_override,
    )

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
        "conditional_ic": prod["conditional_ic"],
        "production_evidence": prod["evidence"],
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
    # 🔴 `CODEX-R32-P1-01`：`purge_rows` 原本在 payload 裡卻**不在比對面**
    #    （實跑：156→155 仍 `STRICT PASS`）；`production_evidence` 為本輪新增之生產端證據。
    for k in ("n_events", "n_consumed", "isolation", "purge_rows", "boundary",
              "analysis_alignment_receipt_hash", "production_evidence"):
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
