#!/usr/bin/env python3
"""SPLITUNIFY `Task 10.7`：真實資料兩端對證（事件掃描投影 vs IC 事件分析）。

規格：`docs/SPLITUNIFY_SPEC.md` v7 `R5-C7`（兩端驗證段事件集合）、`R5-C8`（處置帳與觀測收據）、
`R5-C9`（特徵列鍵）、`R5-C10`（標籤參數單一解析）；施工清單：`docs/SPLITUNIFY_TODO.md` Task 10.7。

用法：
  venv/bin/python scripts/splitunify_r5_parity.py            # 對證 ＋ 與 golden 比對（rc=0 才算過）
  venv/bin/python scripts/splitunify_r5_parity.py --update   # 重寫 golden（值有意圖變動時）

🔴 **本腳本不自算任何量**。每一個被比對的值都由**生產路徑**產出後捕獲：
  · 掃描端＝`POST /api/v1/case/events/{id}/analyze`（真 route，非 service 直呼）；
    切分計畫、分析時窗、隔離列數、投影結果以 spy 包住**生產端的同一個呼叫**取得，
    不在腳本內重算一份（重算＝第二份實作，生產端被改壞時本腳本仍會綠）。
  · IC 端＝`api.routes.ic_analysis._resolve_event_batch` ＋
    `ICAnalysisService._run_scan_cell`（內含 `ICFilterOrchestrator.analyze`）。
    測試段列時刻取自 `_derive_stage_masks` **實際**回傳之遮罩，不是由 `time_bounds` 重推。

🔴 **預測與觀測必須不同源**（`R5-C8` 6./7./8.）：
  處置帳之 `ic_disposition` 是**入口的預測**（以特徵列鍵是否落在 post-trim 索引判定）；
  stage3 之 `_stage3_event_observation` 是**實際發生的事**。先驗兩者逐事件相等，再驗集合等式。
  若拿處置帳去推 IC 測試段，整條對證就變成拿自己比自己——那正是 `R5-C8` 5. 明文禁止的。

🔴 **禁合成 fixture**（CLAUDE.md 資料真實性鐵律）：真實事件批、真實 FF run、真實 K 線。
  資料缺席 ⇒ rc=2（缺資料），不得以合成資料頂替；對證失敗 ⇒ rc=1。

🔴 **非零前提是本腳本的防空心綠機制**：每個組合宣告它**必須**非零的剔除欄；實測為 0 即 fail。
  沒有這條，換一組「三種剔除皆 0」的資料照樣全綠，而該綠燈什麼都沒證明
  （`docs/SPLITUNIFY_TODO.md` Task 10.7 邊界②逐字記載該空心綠組合）。
"""
from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

GOLDEN = REPO / "tests/golden/splitunify/r5_parity.json"
RECEIPT_DIR = REPO / "handoffs/run_receipts"
EVENTS_DIR = REPO / "data_cache/events"
FEATURES_DIR = REPO / "data_cache/features"
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"

#: 走 IC 端時物化之特徵欄數（決定性：該 run 自己的 L1 parquet 依檔名字母序取前 N）。
#: 🔴 只影響 IC 報告之統計面，不影響本腳本比對的任何一個值（切分邊界、事件集合、
#:    處置帳與觀測收據都與特徵欄集無關）——但 stage3 需要真的有特徵表才會執行。
_N_FEATURES = 12

#: 🔴 **實測可行之組合**（`docs/SPLITUNIFY_TODO.md` Task 10.7 邊界②）。
#:    規格 r18 原指定之 `20260901T132233Z-363ecc4f` 走 analyze route 回 422
#:    （`label_origin` 之 `conditional_required_missing`，該批早於現行匯入契約）⇒ 不可用。
#:    🔴 **不得**改用 `20260909T130533Z-7f73e4c7` × 長 run `4a8a0b37…`：三種剔除皆 0，空心綠。
COMBOS: List[Dict[str, Any]] = [
    {
        "key": "coverage_drop",
        "batch": "20260906T105851Z-8cc44eea",
        "ff_run": "5ea074390e98405cb83d602fe7b7fb00",
        "run_symbol": "ETHUSDT",
        "spec": None,                       # 由共用出口依宣告深度導出（兩端同一出口）
        "require_nonzero": ["dropped_in_alignment", "dropped_by_coverage"],
    },
    {
        "key": "post_trim_drop",
        "batch": "20260909T130533Z-7f73e4c7",
        "ff_run": "5ea074390e98405cb83d602fe7b7fb00",
        "run_symbol": "ETHUSDT",
        "spec": None,
        "require_nonzero": ["dropped_outside_post_trim_index"],
    },
    {
        # 邊界③：非預設 `event_label_spec`（k=1、h=6）——兩端各自解析，仍須逐鍵相等。
        "key": "non_default_spec",
        "batch": "20260909T130533Z-7f73e4c7",
        "ff_run": "5ea074390e98405cb83d602fe7b7fb00",
        "run_symbol": "ETHUSDT",
        "spec": {
            "horizon_bars": 6,
            "decision_offset_bars": 1,
            "entry_price_semantic": "trigger_open",
            "label_return_mode": "open_to_horizon_close",
        },
        # 🔴 本組合之 `require_nonzero` **刻意為空**：非預設 spec 之答案窗較短
        #    （h=6×12h＝72 列 vs 預設 156 列）⇒ post-trim 界外之那筆事件不再界外，
        #    三種剔除實測皆 0。邊界②（事件被期間剔除）由上面兩組覆蓋，本組合負責的是
        #    邊界③（非預設 spec）；在此宣告一個永遠為 0 的非零前提只會變成假紅。
        "require_nonzero": [],
    },
]


class ParityError(SystemExit):
    """對證失敗（rc=1）——與「資料缺席」（rc=2）分開，兩者要分得出來。"""

    def __init__(self, msg: str) -> None:
        super().__init__(1)
        self.msg = msg


@contextlib.contextmanager
def _patched(owner: Any, name: str, make_wrapper):
    """以 spy 包住生產端的同一個呼叫；離開即還原（例外路徑也還原）。"""
    original = owner.__dict__.get(name, None)
    current = getattr(owner, name)
    setattr(owner, name, make_wrapper(current))
    try:
        yield
    finally:
        if original is None:
            setattr(owner, name, current)
        else:
            setattr(owner, name, original)


def _ms(value: Any) -> int:
    """時刻 → epoch ms。`pd.Timestamp`／`np.datetime64`／int 皆可，不猜單位。"""
    if hasattr(value, "value"):          # pd.Timestamp
        return int(value.value // 10**6)
    if isinstance(value, np.datetime64):
        return int(pd.Timestamp(value).value // 10**6)
    return int(value)


def _run_dir(ff_run: str, symbol: str) -> Path:
    """定位 run 目錄。🔴 同一 `config_hash` 可存在於多個 symbol（實測 BCHUSDT 與 ETHUSDT
    同雜湊）⇒ 以 symbol 篩選後仍多於一個即 fail-closed，不猜。"""
    hits = sorted(FEATURES_DIR.glob(f"{symbol}/*/{ff_run}"))
    if len(hits) != 1:
        raise SystemExit(f"ERROR: run {ff_run!r}（symbol={symbol}）命中 {len(hits)} 個目錄：{hits}")
    return hits[0]


# ══════════════════════════════════════════════════════════════════════════
# 掃描端：真 route ＋ spy
# ══════════════════════════════════════════════════════════════════════════

def _run_scan(batch_id: str, symbol: str, run_tf: str, ff_run: str,
              spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """POST 真 route，並以 spy 捕獲生產端**實際使用**之邊界、時窗、隔離與投影結果。"""
    from fastapi.testclient import TestClient

    import momentum.factories as factories
    from api.main import app
    from momentum.Analysis.event_samples.pipeline import EventSamplePipeline

    cap: Dict[str, Any] = {}

    def wrap_holdout(orig):
        def _factory(*a, **kw):
            resolve, err_cls = orig(*a, **kw)

            def _resolve(**kw2):
                out = resolve(**kw2)
                cap["holdout"] = out
                # 🔴 取 `CanonicalHoldout` 上**生效後**之三個值，不取呼叫端傳入之 kwargs：
                #    `embargo` 由 resolver 依深度抬高，讀傳入之 `ic_config.embargo` 會拿到
                #    抬高**前**的 0，與 IC 端（抬高後）對比恆不等，變成假紅（實跑踩到）。
                cap["holdout_inputs"] = {
                    "purge_gap": int(out.purge_gap) if out.purge_gap is not None else None,
                    "embargo": int(out.embargo) if out.embargo is not None else None,
                    "oos_test_size": (
                        float(out.oos_test_size) if out.oos_test_size is not None else None
                    ),
                    "lookahead_depth_rows": int(kw2.get("lookahead_depth_rows", -1)),
                }
                return out

            return _resolve, err_cls
        return _factory

    def wrap_prepare(orig):
        def _f(*a, **kw):
            out = orig(*a, **kw)
            cap.setdefault("prepared", out)   # 只取**第一次**：那次才是全量輸入
            return out
        return _f

    def wrap_iso(orig):
        def _f(*a, **kw):
            out = orig(*a, **kw)
            cap["isolation"] = out
            return out
        return _f

    def wrap_projection(orig):
        def _f(self, *a, **kw):
            out = orig(self, *a, **kw)
            cap["projection"] = out
            return out
        return _f

    body: Dict[str, Any] = {"horizons": [1],
                            "feature_run": {"symbol": symbol, "timeframe": run_tf,
                                            "config_hash": ff_run}}
    if spec is not None:
        body["event_label_spec"] = spec

    client = TestClient(app)
    with _patched(factories, "create_canonical_holdout_resolver", wrap_holdout), \
         _patched(EventSamplePipeline, "prepare_analysis_windows", lambda o: staticmethod(wrap_prepare(o))), \
         _patched(EventSamplePipeline, "isolation_terms_rows", lambda o: staticmethod(wrap_iso(o))), \
         _patched(EventSamplePipeline, "run_projection_with_params", wrap_projection):
        resp = client.post(f"/api/v1/case/events/{batch_id}/analyze", json=body)
    if resp.status_code != 200:
        raise ParityError(f"掃描端 HTTP {resp.status_code}：{resp.text[:400]}")
    payload = resp.json()
    for key in ("holdout", "prepared", "isolation", "projection"):
        if key not in cap:
            raise ParityError(f"掃描端未經過 {key} 之生產呼叫點——spy 掛點已漂移（fail-closed）")
    holdout = cap["holdout"]
    if getattr(holdout, "reason", None) is not None:
        raise ParityError(f"掃描端無 canonical 邊界（reason={holdout.reason}）——本組合之前提不成立")
    plan = cap["projection"].split_plan
    assignments = plan.assignments
    test_ids = sorted(
        str(e) for e in assignments.loc[assignments["split_label"] == "test", "event_id"].tolist()
    )
    windows = {
        str(w.event_id): {
            "decision_at_ms": int(w.decision_at_ms),
            "label_start_ms": int(w.label_start_ms),
            "label_end_ms": int(w.label_end_ms),
        }
        for w in cap["prepared"].windows
    }
    return {
        "payload": payload,
        "spec": dict(payload["event_label_spec"]["spec"]),
        "label_window_rows": int(cap["isolation"].label_window_rows),
        "lookahead_depth_rows": int(cap["isolation"].lookahead_depth_rows),
        "holdout_inputs": cap["holdout_inputs"],
        "train_plan": holdout.train_plan,
        "test_plan": holdout.test_plan,
        "windows": windows,
        "test_event_ids": test_ids,
    }


# ══════════════════════════════════════════════════════════════════════════
# IC 端：生產 service ＋ spy
# ══════════════════════════════════════════════════════════════════════════

def _materialize(service: Any, symbol: str, run_tf: str, ff_run: str, run_dir: Path) -> Tuple[str, str]:
    """以**生產端**之 `_write_features_h5`／`_build_ic_metadata_from_run` 物化一組具名子集。

    🔴 **重用 `splitunify_ic_event_report_diff.py` 之同一個 helper**，不抄第二份：
    該檔之 `_IC_FEATURES` 是為長 run 寫死的欄名清單（含 `12h_*`），本票用的短 run
    只有 54 個 `1h_*` 欄 ⇒ 以該清單會 fail。改法是在呼叫前把「固定清單」換成空、
    把「額外欄數」設為 `_N_FEATURES`，讓它取**該 run 自己**的 L1 parquet（字母序，決定性）。
    """
    import importlib.util as ilu

    path = REPO / "scripts/splitunify_ic_event_report_diff.py"
    spec_ = ilu.spec_from_file_location("_su_diff", path)
    mod = ilu.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    mod._IC_FEATURES = []
    mod._SUBSET_EXTRA = _N_FEATURES
    return mod._materialize_named_subset(service, symbol, run_tf, ff_run, run_dir)


def _run_ic(batch_id: str, symbol: str, run_tf: str, ff_run: str, run_dir: Path,
            spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """跑 IC 事件路徑（生產端），取處置帳（預測）、stage3 觀測收據與測試段遮罩。"""
    import momentum.Analysis.ic_filter_orchestrator as orch
    from api.models.ic_models import EventLabelSpecModel, ICAnalyzeRequest
    from api.routes.ic_analysis import _resolve_event_batch
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager

    request = ICAnalyzeRequest(
        symbol=symbol, timeframe=run_tf, config_hash=ff_run,
        mode="longitudinal", event_import_id=batch_id,
        event_label_spec=(EventLabelSpecModel(**spec) if spec is not None else None),
    )
    # 🔴 標籤參數之解析走 **IC route 之生產入口**（`R5-C10` 1.）：在腳本內自組 spec
    #    等於讓兩端「因為我餵了同一份」而相等，對證就失去意義。
    event_batch = _resolve_event_batch(request)
    if event_batch is None:
        raise ParityError(f"IC 端解析不到事件批 {batch_id!r}")

    service = ICAnalysisService()
    cfg = service._build_config_override(request)
    features_path, meta_path = _materialize(service, symbol, run_tf, ff_run, run_dir)
    kline_reader = create_kline_storage_manager(cache_dir="data_cache/feature_klines")

    cap: Dict[str, Any] = {}

    # 🔴 `_run_event_label_stages` 是 **staticmethod**（簽名 `(request, cell_batch, *, ...)`）——
    #    包成帶 `self` 的版本會 `TypeError: takes 2 positional arguments but 3 were given`（實跑踩到）。
    def wrap_stages(orig):
        def _f(*a, **kw):
            out = orig(*a, **kw)
            cap["staged"] = out
            return out
        return staticmethod(_f)

    def wrap_builder(orig):
        # 🔴 捕獲 IC 端**實際**送進 canonical builder 之切分參數。兩端邊界不等時，
        #    沒有這一組值就只能看到「指紋不同」而不知道是哪個輸入不同（實跑踩到：
        #    非預設 spec 之組合兩端 test_start 差 60 列，差在 purge_gap 而非切法）。
        def _f(features, config, symbol, expected_freq, **kw):
            cap["builder_inputs"] = {
                "purge_gap": int(kw.get("purge_gap", -1)),
                "oos_test_size": float(getattr(config, "oos_test_size", float("nan"))),
                "embargo": int(getattr(config, "embargo", 0) or 0),
            }
            return orig(features, config, symbol, expected_freq, **kw)
        return _f

    def wrap_masks(orig):
        def _f(train_plan, test_plan, current_index):
            train_mask, test_mask = orig(train_plan, test_plan, current_index)
            # 🔴 取**實際遮罩命中**之列時刻（`R5-C7` 4.），不由 `time_bounds` 重推。
            cap["train_plan"] = train_plan
            cap["test_plan"] = test_plan
            cap["test_row_ms"] = [_ms(v) for v in pd.Index(current_index)[np.asarray(test_mask, bool)]]
            return train_mask, test_mask
        return _f

    def analyzer_factory(config_override):
        analyzer = create_ic_analyzer(config_override)
        cap["analyzer"] = analyzer
        return analyzer

    with _patched(ICAnalysisService, "_run_event_label_stages", wrap_stages), \
         _patched(orch, "_build_holdout_split_plan", wrap_builder), \
         _patched(orch, "_derive_stage_masks", wrap_masks):
        out = ICAnalysisService._run_scan_cell(
            service, analyzer_factory, request, event_batch,
            features_path=features_path, meta_path=meta_path,
            feature_manifest_path=str(run_dir / "feature_manifest.json"),
            labels_path=None, kline_reader=kline_reader,
            config_override=dict(cfg or {}),
            original_embargo=int((cfg or {}).get("embargo") or 0),
        )
    for key in ("staged", "test_plan", "test_row_ms", "analyzer"):
        if key not in cap:
            raise ParityError(f"IC 端未經過 {key} 之生產呼叫點——spy 掛點已漂移（fail-closed）")

    report = out["report"]
    meta = report.get("metadata") or {}
    ef = meta.get("event_filter") or {}
    if str(ef.get("mode") or "none") == "none" or ef.get("statistic_kind") != "conditional_ic":
        raise ParityError(
            f"IC 端未走條件 IC 分支（mode={ef.get('mode')!r}、statistic_kind="
            f"{ef.get('statistic_kind')!r}）——拿全樣本 IC 當事件分析就是偷換統計量"
        )
    staged = cap["staged"]
    observation = getattr(cap["analyzer"], "_stage3_event_observation", None)
    if not observation:
        raise ParityError("IC 端 stage3 未產出逐事件觀測收據（`R5-C8` 7.）——預測無從對證")
    windows = {
        str(w.event_id): {
            "decision_at_ms": int(w.decision_at_ms),
            "label_start_ms": int(w.label_start_ms),
            "label_end_ms": int(w.label_end_ms),
        }
        for w in staged["prepared"].windows
    }
    owners = {int(k): str(v) for k, v in dict(staged.get("event_label_owners") or {}).items()}
    test_row_ms = set(cap["test_row_ms"])
    obs_consumed = {
        eid for eid, row in observation.items()
        if str(row["observed"]) == _observed_values()["consumed"]
    }
    # `R5-C7` 4.：測試段遮罩命中之列時刻經 `event_label_owners` 回綁 `event_id`；
    # 只取 stage3 **實際消費**者（未消費之事件不在 IC 的任何分段裡）。
    ic_test_ids = sorted(
        eid for key, eid in owners.items() if key in test_row_ms and eid in obs_consumed
    )
    return {
        "spec": dict(event_batch["event_label_spec"]),
        "builder_inputs": cap.get("builder_inputs", {}),
        "label_window_rows": int(staged["label_window_rows"]),
        "lookahead_depth_rows": int(staged["lookahead_depth_rows"]),
        "purge_rows": int(staged["purge_rows"]),
        "train_plan": cap["train_plan"],
        "test_plan": cap["test_plan"],
        "windows": windows,
        "ledger": [dict(r) for r in (staged.get("event_disposition_ledger") or ())],
        "observation": {str(k): dict(v) for k, v in observation.items()},
        "owners": owners,
        "ic_test_ids": ic_test_ids,
    }


def _observed_values() -> Dict[str, str]:
    from momentum.Analysis.event_samples.event_disposition import observed_values

    return observed_values()


# ══════════════════════════════════════════════════════════════════════════
# 對證
# ══════════════════════════════════════════════════════════════════════════

def _compare(combo: Dict[str, Any], scan: Dict[str, Any], ic: Dict[str, Any],
             trigger_tfs: List[str], run_tf: str) -> Dict[str, Any]:
    """逐條對證；任一條不成立即 `ParityError`（不累積成報告後放行）。"""
    obs = _observed_values()
    fails: List[str] = []

    # ① 邊界①：至少一組觸發週期與 run 週期不同——組合本身要有鑑別力。
    if run_tf in trigger_tfs and len(set(trigger_tfs)) == 1:
        fails.append(f"觸發週期 {trigger_tfs} 與 run 週期 {run_tf} 相同——本組合不覆蓋跨週期路徑")

    # ② `R5-C10`：兩端各自解析之標籤參數逐鍵相等。
    if scan["spec"] != ic["spec"]:
        fails.append(f"標籤參數不等：掃描端 {scan['spec']} vs IC 端 {ic['spec']}")
    if scan["label_window_rows"] != ic["label_window_rows"]:
        fails.append(
            f"label_window_rows 不等：掃描端 {scan['label_window_rows']} vs IC 端 {ic['label_window_rows']}"
        )

    # ③′ 切分**輸入**逐值：兩端送進 canonical builder 之 purge_gap／embargo／oos_test_size。
    #    邊界不等時這一組才說得出「差在哪個輸入」；相等時它也是一條獨立的對證面
    #    （`M-SU-R5-*`：一側 `oos_test_size=0.3` 在此就會現形，不必等指紋）。
    s_in, i_in = scan["holdout_inputs"], ic.get("builder_inputs") or {}
    for field in ("purge_gap", "embargo", "oos_test_size"):
        s_v, i_v = s_in.get(field), i_in.get(field)
        if s_v is None or i_v is None:
            fails.append(f"切分輸入 {field} 缺席（掃描端 {s_v!r}、IC 端 {i_v!r}）——spy 掛點已漂移")
        elif s_v != i_v:
            fails.append(f"切分輸入 {field} 不等：掃描端 {s_v} vs IC 端 {i_v}")

    # ③ 切分計畫逐值（🔴 **不以 `boundary_hash` 代替**，邊界④）。
    s_test, i_test = scan["test_plan"], ic["test_plan"]
    s_train, i_train = scan["train_plan"], ic["train_plan"]
    if str(s_test.row_time_fingerprint) != str(i_test.row_time_fingerprint):
        fails.append(
            f"test_plan.row_time_fingerprint 不等：{s_test.row_time_fingerprint} vs {i_test.row_time_fingerprint}"
        )
    s_start, i_start = _ms(s_test.time_bounds[0]), _ms(i_test.time_bounds[0])
    if s_start != i_start:
        fails.append(f"test_start_ms 不等：{s_start} vs {i_start}")
    s_tr = np.asarray(s_train.row_index, dtype=int)
    i_tr = np.asarray(i_train.row_index, dtype=int)
    if s_tr.shape != i_tr.shape or not np.array_equal(s_tr, i_tr):
        fails.append(
            f"train_row_index 不等（掃描端 {s_tr.size} 列、IC 端 {i_tr.size} 列；"
            f"首差位置 {int(np.argmax(s_tr != i_tr)) if s_tr.shape == i_tr.shape else 'n/a'}）"
        )

    # ④ 逐事件錨點與答案窗（只比兩端都有窗的事件；身分集合差異另行報出）。
    only_scan = sorted(set(scan["windows"]) - set(ic["windows"]))
    only_ic = sorted(set(ic["windows"]) - set(scan["windows"]))
    if only_scan or only_ic:
        fails.append(f"分析時窗之事件身分不等（只在掃描端 {only_scan[:5]}；只在 IC 端 {only_ic[:5]}）")
    diff_rows = [
        {"event_id": eid, "scan": scan["windows"][eid], "ic": ic["windows"][eid]}
        for eid in sorted(set(scan["windows"]) & set(ic["windows"]))
        if scan["windows"][eid] != ic["windows"][eid]
    ]
    if diff_rows:
        fails.append(f"逐事件 decision_at／label_start／label_end 不等（{len(diff_rows)} 筆，首筆 {diff_rows[0]}）")

    # ⑤ `R5-C8` 8. 第一段：處置帳之**預測** vs stage3 之**觀測**逐事件相等。
    ledger = {str(r["event_id"]): str(r["ic_disposition"]) for r in ic["ledger"]}
    mism = []
    for eid, row in ic["observation"].items():
        predicted = ledger.get(eid)
        observed = str(row["observed"])
        if predicted is None:
            mism.append({"event_id": eid, "predicted": None, "observed": observed})
        elif predicted != observed:
            mism.append({"event_id": eid, "predicted": predicted, "observed": observed})
    # 🔴 **反向**：被預測為 `ic_consumed` 卻**根本沒進 stage3**（不在觀測收據裡）。
    #    只比對觀測側是單向的：預測說「會被消費」而該事件在更早的階段就消失時，
    #    觀測收據裡沒有它 ⇒ 單向迴圈碰不到，預測錯了也不會紅（實跑踩到：一筆事件
    #    在投影測試段內、處置帳記 consumed，IC 端卻連看都沒看到）。
    ghost_pred = sorted(
        eid for eid, d in ledger.items()
        if d == obs["consumed"] and eid not in ic["observation"]
    )
    if ghost_pred:
        mism.extend({"event_id": e, "predicted": obs["consumed"], "observed": "<未進 stage3>"}
                    for e in ghost_pred[:5])
    if mism:
        fails.append(f"處置帳預測與 stage3 觀測不等（{len(mism)} 筆，首筆 {mism[0]}）")

    # ⑥ `R5-C7` 4.：IC 測試段集合 == 投影 test 集合 − 處置帳記為 IC 端未消費者。
    #    🔴 差集之原因**只能**取自處置帳；本腳本不得自行產生、補填或改寫原因。
    scan_test = set(scan["test_event_ids"])
    not_consumed = {eid for eid, d in ledger.items() if d != obs["consumed"]}
    expected = scan_test - not_consumed
    ic_test = set(ic["ic_test_ids"])
    if expected != ic_test:
        only_e = sorted(expected - ic_test)[:5]
        only_i = sorted(ic_test - expected)[:5]
        fails.append(
            f"測試段集合不等（預期 {len(expected)} 筆、IC 實得 {len(ic_test)} 筆；"
            f"只在預期 {only_e}；只在 IC {only_i}）"
        )
    unexplained = sorted(
        eid for eid in (scan_test - ic_test)
        if ledger.get(eid) in (None, obs["consumed"])
    )
    if unexplained:
        detail = [
            {
                "event_id": eid,
                "ledger": ledger.get(eid),
                "in_owners": eid in set(ic["owners"].values()),
                "in_observation": eid in ic["observation"],
                "feature_row_key_ms": next(
                    (k for k, v in ic["owners"].items() if v == eid), None),
            }
            for eid in unexplained[:3]
        ]
        fails.append(
            f"差集事件無處置帳原因（{len(unexplained)} 筆）——不得由本腳本補填原因；明細 {detail}"
        )

    # ⑦ 防空心綠：本組合宣告必須非零的剔除欄。
    pa = combo_period_alignment(scan["payload"])
    for field in combo["require_nonzero"]:
        if int(pa.get(field, {}).get("count", 0)) <= 0:
            fails.append(
                f"{field} 為 0——本組合之非零前提不成立（空心綠：所有守衛都碰不到）"
            )

    if fails:
        raise ParityError(f"[{combo['key']}] 對證失敗：\n  · " + "\n  · ".join(fails))

    return {
        "combo": combo["key"],
        "batch": combo["batch"],
        "ff_run": combo["ff_run"],
        "trigger_timeframes": trigger_tfs,
        "run_timeframe": run_tf,
        "event_label_spec": scan["spec"],
        "label_window_rows": scan["label_window_rows"],
        "lookahead_depth_rows": scan["lookahead_depth_rows"],
        "holdout_inputs": scan["holdout_inputs"],
        "test_plan": {
            "row_time_fingerprint": str(s_test.row_time_fingerprint),
            "test_start_ms": s_start,
            "n_test_rows": int(np.asarray(s_test.row_index).size),
            "n_train_rows": int(s_tr.size),
        },
        "n_windows": len(scan["windows"]),
        "period_alignment": {k: int(v.get("count", 0)) for k, v in pa.items() if isinstance(v, dict)},
        "n_projection_test": len(scan_test),
        "n_ic_test": len(ic_test),
        "n_not_consumed_in_projection_test": len(scan_test & not_consumed),
        "ic_test_event_ids": sorted(ic_test),
    }


def combo_period_alignment(payload: Dict[str, Any]) -> Dict[str, Any]:
    pa = payload.get("period_alignment")
    if not isinstance(pa, dict):
        raise ParityError("掃描端回應缺 `period_alignment`——剔除揭露不存在，非零前提無從驗")
    return pa


# ══════════════════════════════════════════════════════════════════════════

def _head() -> str:
    out = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                         capture_output=True, text=True)
    return out.stdout.strip()[:12] if out.returncode == 0 else "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SPLITUNIFY Task 10.7 兩端對證")
    ap.add_argument("--update", action="store_true", help="重寫 golden（值有意圖變動時）")
    ap.add_argument("--only", default="", help="只跑指定組合（除錯用；🔴 不寫 golden、不寫 receipt）")
    args = ap.parse_args(argv)
    combos = [c for c in COMBOS if not args.only or c["key"] == args.only]
    if not combos:
        print(f"ERROR: --only {args.only!r} 不在組合清單 {[c['key'] for c in COMBOS]}", file=sys.stderr)
        return 2

    if not KLINE.is_file():
        print(f"ERROR: 缺真實 K 線 {KLINE}（禁以合成資料頂替）", file=sys.stderr)
        return 2

    results: List[Dict[str, Any]] = []
    for combo in combos:
        batch_file = EVENTS_DIR / f"{combo['batch']}.json"
        if not batch_file.is_file():
            print(f"ERROR: 缺真實事件批 {batch_file}（禁以合成資料頂替）", file=sys.stderr)
            return 2
        batch = json.loads(batch_file.read_text(encoding="utf-8"))
        trigger_tfs = sorted({str(r["timeframe"]) for r in batch["records"]})
        # 🔴 run 之 symbol **由組合顯式指定**，不由批之 records 推：混 symbol 批（本票之
        #    `excluded_by_symbol` 來源）取 `records[0]` 會拿到 BTCUSDT，而 run 是 ETHUSDT
        #    ⇒ 找不到目錄（實跑踩到）。猜 symbol 的另一個後果更糟：同一 `config_hash`
        #    可存在於多個 symbol（實測 BCHUSDT 與 ETHUSDT 同雜湊），猜中錯的會拿到別的幣種。
        run_dir = _run_dir(combo["ff_run"], str(combo["run_symbol"]))
        run_tf = run_dir.parent.name
        symbol = run_dir.parent.parent.name

        print(f"[parity] {combo['key']}：批 {combo['batch']}（{len(batch['records'])} 筆、"
              f"觸發週期 {trigger_tfs}）× run {symbol}/{run_tf}/{combo['ff_run'][:8]}…", flush=True)
        scan = _run_scan(batch["import_id"], symbol, run_tf, combo["ff_run"], combo["spec"])
        ic = _run_ic(batch["import_id"], symbol, run_tf, combo["ff_run"], run_dir, combo["spec"])
        row = _compare(combo, scan, ic, trigger_tfs, run_tf)
        print(f"[parity] {combo['key']} ✓ 投影 test {row['n_projection_test']}／"
              f"IC test {row['n_ic_test']}／剔除 {row['period_alignment']}", flush=True)
        results.append(row)

    payload = {
        "_doc": "SPLITUNIFY Task 10.7：兩端對證之凍結值。由 scripts/splitunify_r5_parity.py 產生。",
        "combos": results,
    }
    if args.only:
        # 🔴 子集跑**不得**碰 golden 與 receipt：以部分結果覆蓋完整 golden，會讓下一次
        #    完整跑對著一份殘缺基準比，而那份殘缺基準看起來完全正常。
        print(f"[parity] --only {args.only}：對證通過，未寫 golden／receipt（子集跑）")
        return 0
    if GOLDEN.is_file() and not args.update:
        prev = json.loads(GOLDEN.read_text(encoding="utf-8"))
        if prev.get("combos") != results:
            diff = [
                f"{a.get('combo')}：{k}={a.get(k)!r} → {b.get(k)!r}"
                for a, b in zip(prev.get("combos") or [], results)
                for k in sorted(set(a) | set(b))
                if a.get(k) != b.get(k)
            ]
            print("ERROR: 與 golden 不符（值若為意圖變動，附理由後跑 --update）：\n  · "
                  + "\n  · ".join(diff[:20]), file=sys.stderr)
            return 1
        print(f"[parity] golden 相符：{GOLDEN.relative_to(REPO)}")
    else:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
                          encoding="utf-8")
        print(f"[parity] 已寫 golden：{GOLDEN.relative_to(REPO)}")

    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    receipt = RECEIPT_DIR / f"splitunify_r5_parity.{_head()}.json"
    receipt.write_text(json.dumps(
        {"script": "scripts/splitunify_r5_parity.py", "code_commit": _head(),
         # 🔴 receipt 自帶 backing token：活文件（HANDOFF／docs）引用本檔時，
         #    `verification_claim_check` 要求被引用檔本身含 VERIFY／SIGNOFF 之類字樣，
         #    否則判「REF 檔案無 backing 內容」而擋下寫入。
         "verify": f"VERIFY:splitunify-r5-parity.{_head()}",
         "n_combos": len(results), "combos": results},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[parity] receipt：{receipt.relative_to(REPO)}")
    print(f"[parity] PASS（{len(results)} 組合全數逐值相等）")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ParityError as exc:
        print(f"PARITY FAIL: {exc.msg}", file=sys.stderr)
        raise SystemExit(1)
