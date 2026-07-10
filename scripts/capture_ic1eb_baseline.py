"""IC 1e+1b Golden baseline 預產腳本 v2(SPEC §G+三方審查 reconcile 後重寫)。

由編排端(Claude)於實作動工前在當前 HEAD 執行;產出舊路徑(pooled i.i.d. p+裸 p 閘)
report 快照+結構化五 hash+順序/序列 hash,經 staging 原子發布至
`handoffs/ic1eb_baseline/`。實作端與 Golden 測試(B5 G-1/G-2)唯讀消費;禁重產。

v2 設計依 `handoffs/IC1EB-BASELINE-RECONCILE.md`(F1-F17 裁決);要點:
- 預物化 inputs 架構(1a cut1 先例):reader.list_features_v2 →
  sha256(name) 排序取前 N(F10 family 均勻)→ load_columns_v2+row_index →
  service._write_features_h5;縱向走 features_path 全真 service 路徑,
  xsec 複刻 service 前置(顯式 config_hashes,F2)。
- data_cache 零寫入(F6):features_path 繞 ingest cache;
  `ICFilterOrchestrator._persist_outputs` patch 為 no-op(B5 重放須同 patch);
  capture 前後 data_cache 樹指紋斷言零 diff。
- passed set 由 filter_log.stage5_thresholds 重建(F3;report 頂層無 passed_features)。
- 五 hash canonical 化(float64/NaN,F8)+嚴格型別 gate(非數值 raise,F5)+
  raw 順序 hash(F4)+rolling/decay/grouped 序列 hash(F9)。
- provenance(F7):HEAD+porcelain+script sha+套件版本+每 report byte sha;
  staging→全驗→atomic rename;OUT_DIR 既存則拒跑。
- 追加覆蓋:full(split off,F12)/event(真 kline 分位導 query,F13)/
  xsec labels_path return_5(舊路徑結構性 raise,錄 receipt,F14)。

用法:source venv/bin/activate && python scripts/capture_ic1eb_baseline.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import h5py  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

FINAL_DIR = REPO_ROOT / "handoffs" / "ic1eb_baseline"
STAGING_DIR = REPO_ROOT / "handoffs" / "ic1eb_baseline.staging"
DATA_CACHE = REPO_ROOT / "data_cache"
MAX_FEATURES = 500

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
CFG_1H = "4a8a0b3726cc906ab3534994605e77f5"
CFG_12H_A = "e53e22906c35363757f4cd49d27f973e"
CFG_12H_B = "f754aad4cc8fe5ccc1532296d6e279ec"

# G-1 非顯著性欄(顯著性欄 p_value/t_stat 走 G-2)
G1_COLUMNS = [
    "ic_mean", "ic_std", "icir", "ic_hit_rate", "monotonicity_score",
    "long_short_spread", "coverage", "turnover_rate", "ic_half_life",
    "regime_robust",
]
SIG_COLUMNS = ["feature_name", "p_value", "t_stat"]
SERIES_KEYS = ["rolling_ic_series", "ic_decay", "grouped_ic"]


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_json(payload: Any) -> str:
    return _sha_bytes(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    )


def _name_key(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def select_columns(names: list[str]) -> list[str]:
    """F10:sha256(name) 排序取前 N——確定性且跨 family 均勻。"""
    if len(set(names)) != len(names):
        raise ValueError("duplicate feature names in source universe")
    return sorted(names, key=_name_key)[:MAX_FEATURES]


def _strict_numeric(col: pd.Series, col_name: str) -> np.ndarray:
    """F5:僅允許 finite numeric/None/NaN;±inf 與非數值型別 raise(R2 codex 反例)。
    F8:NaN 統一 canonical 位元(0x7ff8...),防同義缺值因 bit payload 假紅。"""
    out = np.empty(len(col), dtype=np.float64)
    for i, v in enumerate(col.to_numpy()):
        if v is None:
            out[i] = np.nan
        elif isinstance(v, (int, float, np.integer, np.floating)):
            fv = float(v)
            if math.isinf(fv):
                raise TypeError(f"non-finite value in G1 column {col_name!r}: {fv!r}")
            out[i] = fv
        else:
            raise TypeError(f"non-numeric value in G1 column {col_name!r}: {type(v).__name__}({v!r})")
    out[np.isnan(out)] = np.nan  # canonical quiet-NaN bits
    return out


def five_hash(df: pd.DataFrame) -> dict[str, str]:
    """結構化五 hash(CODEX-7);canonical 政策(F8):缺值=NaN、dtype=float64、
    C-order、little-endian float64 bytes;index/columns 以 canonical JSON array
    (自帶 length-frame)。B5 比對限同 venv/同機(F16)。"""
    canon = pd.DataFrame(
        {c: _strict_numeric(df[c], c) for c in df.columns}, index=df.index
    )[list(df.columns)]
    values_b = b"".join(
        np.ascontiguousarray(canon[c].to_numpy(), dtype="<f8").tobytes() for c in canon.columns
    )
    return {
        "index_sha256": _sha_json(list(map(str, canon.index))),
        "columns_sha256": _sha_json(list(map(str, canon.columns))),
        "dtypes_sha256": _sha_json([str(canon[c].dtype) for c in canon.columns]),
        "nanmask_sha256": _sha_bytes(canon.isna().to_numpy().tobytes()),
        "values_sha256": _sha_bytes(values_b),
        "raw_tobytes_sha256_appendix": _sha_bytes(
            np.ascontiguousarray(canon.to_numpy(), dtype="<f8").tobytes()
        ),
    }


def summary_to_g1_frame(summary_table: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(summary_table)
    if df["feature_name"].duplicated().any():
        raise ValueError("duplicate feature_name in summary_table")
    df = df.set_index("feature_name").sort_index()
    return df.reindex(columns=G1_COLUMNS)


def reconstruct_passed(summary_table: list[dict[str, Any]], filter_log: dict) -> list[str]:
    """F3:passed=summary 集合−union(removed);斷言數量==output_features。"""
    s5 = (filter_log or {}).get("stage5_thresholds") or {}
    removed: set[str] = set()
    for names in (s5.get("removed_features") or {}).values():
        removed.update(names)
    all_names = [row["feature_name"] for row in summary_table]
    passed = sorted(set(all_names) - removed)
    expected = s5.get("output_features")
    if expected is not None and len(passed) != expected:
        raise AssertionError(
            f"passed reconstruction mismatch: {len(passed)} != output_features {expected}"
        )
    return passed


def data_cache_fingerprint() -> str:
    """F6(R2 加嚴):data_cache 樹指紋=path+size+**全內容 sha256**;
    capture 前後必零 diff(mtime 保留型改寫也抓得到)。"""
    entries: list[str] = []
    for root, dirs, files in os.walk(DATA_CACHE):
        dirs.sort()
        for f in sorted(files):
            p = Path(root) / f
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 22), b""):
                    h.update(chunk)
            entries.append(f"{p.relative_to(DATA_CACHE)}|{p.stat().st_size}|{h.hexdigest()}")
    return _sha_bytes("\n".join(entries).encode("utf-8"))


def patch_persist_outputs() -> None:
    """F6:阻斷 stage7 對 data_cache/reports 的落盤;report 走記憶體回傳。
    B5 重放時必須施加同一 patch(寫入 manifest.procedure)。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    def _no_persist(self, *args: Any, **kwargs: Any) -> dict:
        return {"persist_patched": "capture_ic1eb_baseline v2 (F6 data_cache read-only)"}

    ICFilterOrchestrator._persist_outputs = _no_persist  # type: ignore[assignment]


def materialize_subset(
    service: Any, symbol: str, timeframe: str, config_hash: str
) -> tuple[Path, Path, list[str], int]:
    from momentum.factories import create_feature_reader

    reader = create_feature_reader()
    names = reader.list_features_v2(symbol, timeframe, config_hash)
    selected = select_columns(list(names))
    if len(selected) != MAX_FEATURES:
        raise RuntimeError(f"{symbol}/{timeframe}/{config_hash[:8]}: got {len(selected)} cols")
    df = reader.load_columns_v2(symbol, timeframe, config_hash, selected)
    if set(df.columns) != set(selected):
        raise AssertionError(f"loader returned different column set for {symbol}")
    df = df[selected]  # loader 依貨架序回欄,重排回選欄序(確定性)
    row_index = reader.load_row_index_v2(symbol, timeframe, config_hash)
    if row_index is not None:
        df.index = row_index
    inputs_dir = STAGING_DIR / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{symbol}_{timeframe}_{config_hash}_sha{MAX_FEATURES}"
    h5_path = inputs_dir / f"{tag}.h5"
    meta_path = inputs_dir / f"{tag}_meta.json"
    service._write_features_h5(h5_path, symbol, timeframe, df)
    meta = service._build_ic_metadata_from_run(symbol, timeframe, config_hash, selected)
    fam_hist: dict[str, int] = {}
    for n in selected:
        fam = n.split("_", 1)[0]
        fam_hist[fam] = fam_hist.get(fam, 0) + 1
    meta["baseline_subset"] = {
        "selection": "sorted(names, key=sha256(name))[:N] (F10)",
        "max_features": MAX_FEATURES,
        "source_feature_count": len(names),
        "selected_names": selected,
        "selected_names_sha256": _sha_json(selected),
        "family_distribution": dict(sorted(fam_hist.items())),
    }
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8"
    )
    return h5_path, meta_path, selected, len(names)


async def run_service_longitudinal(
    service: Any, spec: dict[str, Any], h5_path: Path, meta_path: Path
) -> dict[str, Any]:
    from api.models.ic_models import ICAnalyzeRequest

    request = ICAnalyzeRequest(
        features_path=str(h5_path.resolve()),
        meta_path=str(meta_path.resolve()),
        symbol=spec["symbol"],
        timeframe=spec["timeframe"],
        config_hash=spec["config_hash"],
        mode="longitudinal",
        config_override=spec.get("config_override"),
        event_query=spec.get("event_query"),
    )
    started = await service.start_analysis(request)
    task_id = started["task_id"]
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        status = service.get_task_status(task_id)
        if status and status.get("status") == "completed":
            result = service.get_result(task_id)
            if result is None:
                raise AssertionError(f"{spec['name']}: completed but no result")
            return result
        if status and status.get("status") == "failed":
            raise AssertionError(f"{spec['name']}: failed: {status.get('error')}")
        await asyncio.sleep(0.5)
    raise TimeoutError(spec["name"])


def build_xsec_frame(service: Any, symbols: list[str], timeframe: str, config_hash: str) -> pd.DataFrame:
    """F1/F2:複刻 service xsec 前置;欄=3sym 特徵名交集的 sha 排序前 N(保證同欄)。"""
    from momentum.factories import create_feature_reader

    reader = create_feature_reader()
    name_sets = [set(reader.list_features_v2(s, timeframe, config_hash)) for s in symbols]
    common = set.intersection(*name_sets)
    selected = select_columns(sorted(common))
    frames: list[pd.DataFrame] = []
    for symbol in symbols:
        frame = reader.load_columns_v2(symbol, timeframe, config_hash, selected)
        row_index = reader.load_row_index_v2(symbol, timeframe, config_hash)
        if row_index is not None:
            frame.index = row_index
        if set(frame.columns) != set(selected):
            raise AssertionError(f"xsec column set mismatch for {symbol}")
        frame = frame[selected].copy()  # 重排回選欄序
        frame["_symbol"] = symbol
        frames.append(frame)
    cross_df = pd.concat(frames, axis=0).set_index("_symbol", append=True)
    return service._append_cross_sectional_labels(cross_df, symbols, timeframe), selected


def build_return5_labels_h5(timeframe: str) -> Path:
    """F14 素材:由真 kline 計 BTC return_5 落單軸 labels h5(舊路徑 xsec 預期 raise)。"""
    from momentum.factories import create_kline_storage_manager

    kline = create_kline_storage_manager(
        cache_dir="data_cache/feature_klines"
    ).read_klines("BTCUSDT", timeframe)
    close = pd.to_numeric(kline["close"], errors="raise").to_numpy(dtype=np.float64)
    ret5 = np.full(len(close), np.nan)
    ret5[:-5] = close[5:] / close[:-5] - 1.0
    idx = pd.DatetimeIndex(pd.to_datetime(kline.index)).view("int64") // 10**9
    inputs_dir = STAGING_DIR / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    path = inputs_dir / f"labels_BTCUSDT_{timeframe}_return5.h5"
    with h5py.File(path, "w") as f:
        g = f.create_group(f"BTCUSDT/{timeframe}")
        g.create_dataset("labels", data=ret5.reshape(-1, 1))
        g.create_dataset("label_names", data=np.array([b"return_5"]))
        g.create_dataset("timestamps", data=np.asarray(idx, dtype=np.int64))
    return path


def derive_event_query(timeframe: str, quantile: float = 0.75) -> str:
    """F13:真 kline volume 分位導出 query(確定性,非合成)。q75=sufficient 帶,q95≈85事件=low-confidence 帶。"""
    from momentum.factories import create_kline_storage_manager

    kline = create_kline_storage_manager(
        cache_dir="data_cache/feature_klines"
    ).read_klines("BTCUSDT", timeframe)
    qv = float(pd.to_numeric(kline["volume"], errors="raise").quantile(quantile))
    return f"volume >= {qv!r}"


def record_run(
    manifest: dict[str, Any], spec: dict[str, Any], result: dict[str, Any], elapsed: float
) -> None:
    name = spec["name"]
    report_path = STAGING_DIR / f"{name}.report.json"
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=1, default=str),
        encoding="utf-8",
    )
    summary = result.get("summary_table") or []
    filter_log = result.get("filter_log") or {}
    passed = reconstruct_passed(summary, filter_log)
    g1 = summary_to_g1_frame(summary)
    # F4(R2)+F4c(R3):raw schema 完整性——G1 欄在**任一列**消失即紅;逐列 keyset 入 hash
    keys_union = sorted({k for row in summary for k in row})
    for i, row in enumerate(summary):
        row_missing = [c for c in G1_COLUMNS if c not in row]
        if row_missing:
            raise AssertionError(
                f"{name}: G1 columns missing from summary row {i}: {row_missing}"
            )
    harness_keys = {"name", "expect_scope", "expect_rows"}
    entry: dict[str, Any] = {
        "request": {
            k: v for k, v in spec.items()
            if not k.startswith("_") and k not in harness_keys
        },
        "capture_asserts": {k: spec.get(k) for k in ("expect_scope", "expect_rows") if k in spec},
        "summary_keys_union_sha256": _sha_json(keys_union),
        "summary_row_key_order_sha256": _sha_json(list(summary[0].keys()) if summary else []),
        # F4c:每列 keyset(排序)逐列入 hash——任一列 missing-vs-null 皆轉紅
        "summary_row_keysets_sha256": _sha_json([sorted(row.keys()) for row in summary]),
        "elapsed_seconds": round(elapsed, 1),
        "report_file": report_path.name,
        "report_sha256": _sha_bytes(report_path.read_bytes()),
        "report_bytes": report_path.stat().st_size,
        "n_summary_rows": len(summary),
        "g1_five_hash": five_hash(g1),
        # F4:raw 輸出順序(排序前),ordering mutation 必轉紅
        "summary_feature_order_sha256": _sha_json(
            [row.get("feature_name") for row in summary]
        ),
        # F3:真 passed 集合+removal reason mapping(G-2 完整性)
        "n_passed_features": len(passed),
        "passed_set_sha256": _sha_json(passed),
        "removed_features_sha256": _sha_json(
            (filter_log.get("stage5_thresholds") or {}).get("removed_features") or {}
        ),
        "significance_old_iid_sha256": _sha_json(
            [{c: row.get(c) for c in SIG_COLUMNS} for row in summary]
        ),
        # F9:§G 明文不變序列
        "series_sha256": {k: _sha_json(result.get(k)) for k in SERIES_KEYS},
        "metadata_scope": (result.get("metadata") or {}).get("scope"),
        "stage0_input_features": (filter_log.get("stage0_ingestion") or {}).get("input_features"),
        "stage5_threshold_log": (filter_log.get("stage5_thresholds") or {}),
    }
    manifest["runs"][name] = entry
    print(f"[baseline] {name} done in {elapsed:.1f}s rows={len(summary)} passed={len(passed)}", flush=True)


def assert_run(spec: dict[str, Any], manifest_entry: dict[str, Any]) -> None:
    expect_scope = spec.get("expect_scope", "test")
    scope = manifest_entry.get("metadata_scope")
    if scope != expect_scope:
        raise AssertionError(f"{spec['name']}: scope={scope!r} expected {expect_scope!r}")
    # 進場斷言對 stage0(=物化子集 N);summary rows 可因 stage1 preprocessing 剔欄而略少,如實記錄
    s0 = manifest_entry.get("stage0_input_features")
    expect_in = spec.get("expect_rows", MAX_FEATURES)
    if expect_in is not None and s0 != expect_in:
        raise AssertionError(f"{spec['name']}: stage0 input={s0} expected {expect_in}")


def main() -> None:
    if FINAL_DIR.exists():
        raise SystemExit(
            f"ERROR: {FINAL_DIR} 已存在(不可變產物,拒絕覆寫);請先人工處置既有目錄"
        )
    if STAGING_DIR.exists():
        raise SystemExit(f"ERROR: staging 殘留 {STAGING_DIR},請先清理")

    patch_persist_outputs()
    from api.services.ic_analysis_service import ICAnalysisService

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=REPO_ROOT
    ).stdout.strip()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True, cwd=REPO_ROOT
    ).stdout
    import scipy
    import statsmodels

    fp_before = data_cache_fingerprint()
    STAGING_DIR.mkdir(parents=True)

    manifest: dict[str, Any] = {
        "purpose": "IC 1e+1b Golden baseline v2(舊路徑 pooled i.i.d. p+裸 p 閘)",
        "spec": "docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md v2.2 §G",
        "reconcile": "handoffs/IC1EB-BASELINE-RECONCILE.md(F1-F17)",
        "head_sha": head,
        "git_status_porcelain": porcelain,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/capture_ic1eb_baseline.py",
        "generator_sha256": _sha_bytes(Path(__file__).read_bytes()),
        "env_versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        },
        "max_features": MAX_FEATURES,
        "column_selection": "sorted(names, key=sha256(name))[:N]",
        "g1_columns": G1_COLUMNS,
        "procedure": {
            "persist_outputs": "patched to no-op (F6);B5 重放須同 patch",
            "materialization": "reader.list_features_v2→sha256 排序前N→load_columns_v2"
                               "+row_index→service._write_features_h5;縱向 features_path 全真路徑",
            "xsec": "複刻 service 前置(顯式 config_hash,欄=3sym 交集 sha 排序前N)"
                    "→_append_cross_sectional_labels→analyze_cross_sectional",
            "environment_pin": "G-1 比對限同 venv/同機;禁跨環境重產(F16)",
        },
        "runs": {},
        "expected_raise_runs": {},
        "notes": [
            "event 模式舊路徑無 train/test split(scope 鍵不存在)=既有行為,G-2 解讀時計入",
            "F14:xsec labels_path 為舊路徑結構性 raise(loader 單軸,orchestrator:951-954),receipt 即真相",
        ],
    }

    service = ICAnalysisService()

    long_specs: list[dict[str, Any]] = []
    for tf, ch in [("1h", CFG_1H), ("12h", CFG_12H_A), ("12h", CFG_12H_B)]:
        for sym in SYMBOLS:
            long_specs.append({
                "name": f"long_{sym}_{tf}_{ch[:8]}",
                "mode": "longitudinal", "symbol": sym, "timeframe": tf, "config_hash": ch,
            })
    # F12 full-sample representative
    long_specs.append({
        "name": "full_BTCUSDT_12h_e53e2290",
        "mode": "longitudinal", "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": CFG_12H_A,
        "config_override": {"ic_train_test_split": False},
        # 舊路徑 split off 時 report_meta.pop("scope")(orchestrator:915)→無 scope 鍵=真相
        "expect_scope": None,
    })
    # F13 event run(真 kline 分位導 query);R2 加 q95 顆命中 30-99 樣本帶(low-confidence α 變更面)
    event_query = derive_event_query("12h")
    long_specs.append({
        "name": "event_BTCUSDT_12h_e53e2290",
        "mode": "longitudinal", "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": CFG_12H_A,
        "event_query": event_query,
        "_note": f"query derived from real kline volume q75: {event_query}",
        "expect_rows": None,
    })
    event_query_q95 = derive_event_query("12h", quantile=0.95)
    long_specs.append({
        "name": "event_lowconf_BTCUSDT_12h_e53e2290",
        "mode": "longitudinal", "symbol": "BTCUSDT", "timeframe": "12h",
        "config_hash": CFG_12H_A,
        "event_query": event_query_q95,
        "_note": f"q95 → 約85事件,落 30-99 low-confidence 帶: {event_query_q95}",
        "expect_rows": None,
    })

    subset_cache: dict[tuple[str, str, str], tuple[Path, Path]] = {}
    manifest["subsets"] = {}
    for spec in long_specs:
        key = (spec["symbol"], spec["timeframe"], spec["config_hash"])
        if key not in subset_cache:
            h5p, metap, selected, total = materialize_subset(service, *key)
            subset_cache[key] = (h5p, metap)
            fam: dict[str, int] = {}
            for n in selected:
                fam[n.split("_", 1)[0]] = fam.get(n.split("_", 1)[0], 0) + 1
            manifest["subsets"][f"{key[0]}_{key[1]}_{key[2][:8]}"] = {
                "selected_names": selected,
                "selected_names_sha256": _sha_json(selected),
                "family_distribution": dict(sorted(fam.items())),
                "source_feature_count": total,
            }
        h5p, metap = subset_cache[key]
        print(f"[baseline] running {spec['name']} ...", flush=True)
        t0 = time.monotonic()
        result = asyncio.run(run_service_longitudinal(service, spec, h5p, metap))
        record_run(manifest, spec, result, time.monotonic() - t0)
        if spec.get("expect_rows", MAX_FEATURES) is not None:
            assert_run(spec, manifest["runs"][spec["name"]])

    # xsec 主顆(F1/F2)
    from momentum.factories import create_ic_analyzer

    xsec_spec = {
        "name": "xsec_3sym_12h_e53e2290", "mode": "cross_sectional",
        "symbols": SYMBOLS, "timeframe": "12h", "config_hash": CFG_12H_A,
    }
    print(f"[baseline] running {xsec_spec['name']} ...", flush=True)
    t0 = time.monotonic()
    cross_df, xsec_selected = build_xsec_frame(service, SYMBOLS, "12h", CFG_12H_A)
    xfam: dict[str, int] = {}
    for n in xsec_selected:
        xfam[n.split("_", 1)[0]] = xfam.get(n.split("_", 1)[0], 0) + 1
    manifest["subsets"]["xsec_3sym_12h_" + CFG_12H_A[:8]] = {
        "selected_names": xsec_selected,
        "selected_names_sha256": _sha_json(xsec_selected),
        "family_distribution": dict(sorted(xfam.items())),
        "note": "3sym 特徵名交集之 sha 排序前 N",
    }
    analyzer = create_ic_analyzer(None)
    xsec_result = analyzer.analyze_cross_sectional(
        features=cross_df, labels_path=None, config_override=None,
        progress_callback=None, timeframe="12h",
    )
    xsec_spec["expect_rows"] = None
    xsec_spec["expect_scope"] = (xsec_result.get("metadata") or {}).get("scope")
    record_run(manifest, xsec_spec, xsec_result, time.monotonic() - t0)

    # F14:xsec labels_path return_5——舊路徑結構性 raise,錄 receipt
    labels_h5 = build_return5_labels_h5("12h")
    try:
        analyzer.analyze_cross_sectional(
            features=cross_df, labels_path=str(labels_h5), config_override=None,
            progress_callback=None, timeframe="12h",
        )
        raise AssertionError("F14: old path unexpectedly accepted single-axis labels_path")
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001 — 舊路徑預期行為即為 raise
        manifest["expected_raise_runs"]["xsec_labels_return5_12h"] = {
            "labels_file": labels_h5.name,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "meaning": "舊路徑 xsec labels_path 單軸不支援(orchestrator:951-954);"
                       "B5 憑此 receipt 檢視 1e+1b 後行為是否仍 fail-closed(Task 3.1 不含此支援)",
        }
        print(f"[baseline] F14 expected raise captured: {type(exc).__name__}", flush=True)

    # F7(R2):inputs 完整性——premat h5/meta/labels 任何 byte 改動必轉紅
    inputs_integrity: dict[str, dict[str, Any]] = {}
    inputs_dir = STAGING_DIR / "inputs"
    if inputs_dir.exists():
        for f in sorted(inputs_dir.iterdir()):
            if f.is_file():
                inputs_integrity[f.name] = {
                    "sha256": _sha_bytes(f.read_bytes()),
                    "bytes": f.stat().st_size,
                }
    manifest["inputs_integrity"] = inputs_integrity

    fp_after = data_cache_fingerprint()
    manifest["data_cache_fingerprint"] = {
        "before": fp_before, "after": fp_after, "unchanged": fp_before == fp_after,
    }
    if fp_before != fp_after:
        raise AssertionError("F6 violated: data_cache tree changed during capture")

    (STAGING_DIR / "baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    os.rename(STAGING_DIR, FINAL_DIR)
    print(f"[baseline] atomic publish → {FINAL_DIR}", flush=True)


if __name__ == "__main__":
    main()
