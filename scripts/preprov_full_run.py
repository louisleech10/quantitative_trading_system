#!/usr/bin/env python3
"""FFDSTAR Task 3.2 前置：生成「一個全特徵設定」之真實 run，供 `scripts/preprov_output_size.py --full-run-dir` 量測。

對照之參考 run：`data_cache/features/BTCUSDT/12h/0729db3a2de860b6c7d01be16ca22d22`（2026-10-05 起經 UI／API 預設路徑生成，
204,150 欄、1,951 列、247 群組；L1／L2／L3／L4／L6，只有 12h）。該 run 之 manifest 只存 `config_hash`，**未存原始 config_override**，
故本腳本之設定是由 manifest `generation_metadata` 與生產預設反推（非逐字還原）：

- **config_override＝None**（不覆寫任何鍵）：走 `config/scan_config.yaml`（受版控）＋`config/user_scan_config.yaml`（僅註解）
  之生產預設，與 API `FeatureGenerateRequest.config_override` 預設 None 同（`api/models/feature_factory_models.py:34`）。
  此預設之前處理旗標與參考 run 之 `generation_metadata.preprocessing_config_enabled.steps` 逐項相符：
  winsorization／rank_transform／adaptive_zscore＝開、gaussian_normalize／fractional_differencing／adf_differencing＝關
  （`scan_config.yaml:460-500`、`feature_config.py:167,243,261,284,290,296`）；`preprocessing.enabled`＝True、`mode`＝replace
  （`feature_config.py:303-304,317`）⇒ 前處理總開關開、平穩化關（`stationarity_enabled=false`）、`l65_mode=ic_first_pre`
  （`feature_factory.py:3229`）、raw 件只套縮尾（`raw_artifact_applied.steps`）。
- 標的／週期：BTCUSDT／12h（`timeframes.primary/training` 預設皆 12h，`feature_config.py:58-61`）；L5 不啟（單標的、參考標的即自身，
  參考 run `expected_layers` 無 L5）。
- 起訖：`--start-date 2024-01-01`、`--end-date 2026-09-02`。參考 run `time_range`＝1704067200～1788307200
  ＝2024-01-01 00:00～2026-09-02 00:00 UTC（含端點 12h 柱，1,951 列＝975 日×2＋1）；`end_date` 過濾為 `<=`
  （`feature_factory.py:934-936`），故需 `2026-09-02`（上游若以 2026-09-01 描述，為少一日之筆誤）。
- 呼叫入口：`create_feature_factory(cache_dir=data_cache/feature_klines, validate_continuity=False)`
  ＋`generate_features(..., force_regenerate=True, persist=True)`，與 `tests/feature_engineering/preprov_helpers.py::_dispatch`
  （`:542-557`）同；`cleanup_intermediate`、`npy_freed_bytes` 等中繼清理由生產碼預設決定，不在此覆寫。

**已知與參考 run 不同之處（明示，不隱藏）**
1. 參考 run 當時之 config_override／起訖字串無法自 manifest 取回；本腳本結束時比對 `config_hash` 與 `--reference-hash`
   （預設 0729db3a…）並記入收據 `config_hash_matches_reference`。不相符不代表欄數不同，欄數／列數另記於收據供對照。
   `config_hash` 另受程式碼版本（含 PRE-PROV 新增之紀錄欄位）與起訖字串影響。
2. 寫入根隔離於 `--out-root`（不碰 `data_cache/`）：features 根、registry（`FFACT_FEATURE_REGISTRY_PATH`）、CGSA 工作目錄
   （`FFACT_CGSA_WORK_DIR`）、系統暫存皆置其下；cwd 切到 `--out-root/cwd` 並以 symlink 指回 repo `config/`。
   kline 仍唯讀自 `data_cache/feature_klines/kline_cache.h5`。
3. 不設 `FIXED_ENV`（單行程旗標）：維持生產預設平行度，以貼近參考 run；單週期 12h 本就無多週期平行。

欄數預期：參考 run 204,150 欄（L1+L2 決策欄 43,536，見 `handoffs/run_receipts/20261019-preprov-output-size-approval.json`）。
同碼同設定應得相同欄數；若收據 `total_features` 不同，量測報告須明示並以實測為準。

資源（`handoffs/run_receipts/20261020-ffdstar-b4-plan.md` §4 估計）：牆鐘約 60–100 分、峰值 footprint 約 14 GB、
輸出約 0.6 GB＋暫存約 8 GB。**須獨占機器**，不得與委員輪或其他重型跑並行。

用法：
  venv/bin/python scripts/preprov_full_run.py --out-root /private/tmp/preprov_full --receipt /private/tmp/preprov_full/receipt.json
  # 末行輸出 `RUN_DIR=<path>`，接著：
  venv/bin/python scripts/preprov_output_size.py --full-run-dir <path>
rc：0＝生成完成並寫收據；1＝生成失敗（收據仍寫出，含錯誤）；2＝參數不合（out-root 位於 repo data_cache 下或非空）。
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA_VERSION = 1
KLINE_DIR = REPO / "data_cache" / "feature_klines"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_TIMEFRAME = "12h"
DEFAULT_START = "2024-01-01"
DEFAULT_END = "2026-09-02"
REFERENCE_HASH = "0729db3a2de860b6c7d01be16ca22d22"
REFERENCE_TOTAL_FEATURES = 204_150
REFERENCE_ROW_COUNT = 1_951
MANIFEST_NAME = "feature_manifest.json"


def _peak_rss_bytes() -> int:
    """本行程歷來峰值常駐記憶體（位元組）；macOS 的 ru_maxrss 單位為位元組，Linux 為 KiB。"""
    raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw if sys.platform == "darwin" else raw * 1024


def _check_out_root(out_root: Path) -> Optional[str]:
    """out-root 不得在 repo `data_cache/` 之下且須為空或不存在；不合回傳原因字串。"""
    resolved = out_root.resolve()
    protected = (REPO / "data_cache").resolve()
    if resolved == protected or protected in resolved.parents:
        return f"out-root 不得位於 repo data_cache 之下：{resolved}"
    if resolved.exists() and any(resolved.iterdir()):
        return f"out-root 須為空目錄或不存在：{resolved}"
    return None


def _prepare_isolation(out_root: Path) -> Path:
    """隔離一切寫入於 out-root；回傳 features 根。chdir 至 out-root/cwd 並以 symlink 指回 repo config/。"""
    out_root.mkdir(parents=True, exist_ok=True)
    cwd = out_root / "cwd"
    cwd.mkdir(exist_ok=True)
    if not (cwd / "config").exists():
        (cwd / "config").symlink_to(REPO / "config")
    sys_tmp = out_root / "sys_tmp"
    sys_tmp.mkdir(exist_ok=True)
    tempfile.tempdir = str(sys_tmp)
    features_root = out_root / "features"
    os.environ["FFACT_FEATURE_REGISTRY_PATH"] = str(features_root / "registry.json")
    os.environ["FFACT_CGSA_WORK_DIR"] = str(out_root / "cgsa_work")
    os.chdir(cwd)
    return features_root


def _manifest_facts(run_dir: Path) -> Dict[str, Any]:
    """自 manifest 取欄數／列數／群組數／層／時間範圍（manifest 可達數十 MB，只取所需鍵）。"""
    manifest = json.loads((run_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    groups = manifest.get("groups")
    return {
        "total_features": manifest.get("total_features"),
        "row_count": manifest.get("row_count"),
        "group_count": len(groups) if groups is not None else None,
        "expected_layers": manifest.get("expected_layers"),
        "expected_timeframes": manifest.get("expected_timeframes"),
        "time_range": manifest.get("time_range"),
        "run_status": manifest.get("run_status"),
    }


def _write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-root", required=True, help="生成工作根（features／registry／CGSA／暫存皆置其下；不得在 data_cache 下）")
    parser.add_argument("--receipt", required=True, help="收據 JSON 路徑（牆鐘秒、峰值 RSS、config_hash、欄列數）")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME)
    parser.add_argument("--start-date", default=DEFAULT_START)
    parser.add_argument("--end-date", default=DEFAULT_END)
    parser.add_argument("--reference-hash", default=REFERENCE_HASH)
    parser.add_argument("--stationarity-on", action="store_true",
                        help="只另開分數差分與 ADF 差分（apply_to=non_stationary，同 ffstat_helpers.stat_payload），其餘生產預設；"
                             "核可估算以 L1＋L2 決策欄寫滿計，此為同條件對照")
    args = parser.parse_args()
    config_override: Optional[Dict[str, Any]] = None
    if args.stationarity_on:
        config_override = {"preprocessing": {
            "fractional_differencing": {"enabled": True, "apply_to": "non_stationary"},
            "adf_differencing": {"enabled": True, "apply_to": "non_stationary"},
        }}

    out_root = Path(args.out_root).expanduser()
    receipt_path = Path(args.receipt).expanduser().resolve()
    problem = _check_out_root(out_root)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    out_root = out_root.resolve()
    if not (KLINE_DIR / "kline_cache.h5").is_file():
        print(f"缺真實 kline：{KLINE_DIR / 'kline_cache.h5'}", file=sys.stderr)
        return 2

    receipt: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "config_override": config_override,
        "reference_hash": args.reference_hash,
        "reference_total_features": REFERENCE_TOTAL_FEATURES,
        "reference_row_count": REFERENCE_ROW_COUNT,
        "out_root": str(out_root),
    }
    rc = 0
    run_dir: Optional[Path] = None
    started = time.monotonic()
    try:
        features_root = _prepare_isolation(out_root)
        from momentum.factories import create_feature_factory
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        factory = create_feature_factory(cache_dir=str(KLINE_DIR), validate_continuity=False)
        factory._storage = FeatureStorage(str(features_root))
        result = factory.generate_features(
            args.symbol, args.timeframe, config_override=config_override, force_regenerate=True,
            start_date=args.start_date, end_date=args.end_date, persist=True,
        )
        config_hash = str((result.metadata or {})["config_hash"])
        run_dir = features_root / args.symbol / args.timeframe / config_hash
        receipt["config_hash"] = config_hash
        receipt["config_hash_matches_reference"] = config_hash == args.reference_hash
        receipt["run_dir"] = str(run_dir)
        receipt.update(_manifest_facts(run_dir))
        receipt["matches_reference_shape"] = (
            receipt["total_features"] == REFERENCE_TOTAL_FEATURES and receipt["row_count"] == REFERENCE_ROW_COUNT
        )
    except BaseException as exc:  # noqa: BLE001 - 失敗亦須寫收據
        rc = 1
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["traceback"] = traceback.format_exc()
    receipt["wall_seconds"] = round(time.monotonic() - started, 1)
    receipt["peak_rss_bytes"] = _peak_rss_bytes()
    receipt["peak_rss_gib"] = round(receipt["peak_rss_bytes"] / 2**30, 2)
    _write_receipt(receipt_path, receipt)
    print(f"receipt={receipt_path} rc={rc}")
    if rc == 0 and run_dir is not None:
        print(f"RUN_DIR={run_dir}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
