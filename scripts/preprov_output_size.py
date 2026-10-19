#!/usr/bin/env python3
"""FFDSTAR Task 3.2（docs/FFDSTAR_SPEC.md）：逐欄紀錄之輸出增量重量量測。

對 §V 各格（`tests/feature_engineering/preprov_helpers.CELLS`，真實 kline 短窗、逐格單行程串行）及一個全特徵設定之 run
（`--full-run-dir` 給定者；本機不可跑則以最大格之每列位元組外推至 `--full-feature-columns` 欄並明示 `extrapolated`）
量測：紀錄檔絕對位元組、manifest 位元組與其因新鍵（`content_sha256`、`provenance`）之增量、run 目錄總位元組、
紀錄檔佔 run 百分比、紀錄檔讀取秒數（pyarrow，取多次中位數）。小 run 百分比失真 ⇒ 一律同報絕對值（邊界①）；
多標的格逐標的報（邊界②）。全特徵 run 紀錄檔合計 > 2.6 MB（核可估算 1.3 MB 之兩倍）⇒ `needs_user_reapproval`＝true。

用法：
  venv/bin/python scripts/preprov_output_size.py [--cells h1_stat_on ...] [--work-root DIR]
      [--full-run-dir DATA_CACHE_RUN_DIR] [--full-feature-columns 204150] [--out tests/_golden/preprov/output_size.json]
rc：0＝量測完成並寫出收據（是否超出估算看收據旗標，不以 rc 表示）；1＝量測失敗（收據仍寫出，含錯誤）——含任一
artifact 缺 `provenance` 指標、紀錄檔不存在、parquet metadata 不可讀（邊界③；不以 0 位元組累計）。`--full-run-dir`
先於各格生成量測，其不成立即 rc=1。
"""

from __future__ import annotations

import argparse
import json
import shlex
import statistics
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA_VERSION = 1
APPROVED_ESTIMATE_BYTES = 1_300_000  # SPEC §A 已確認結果：使用者 2026-10-19 核可之估算（約 +1.3 MB／全特徵 run）
REAPPROVAL_THRESHOLD_BYTES = 2_600_000  # SPEC Task 3.2：估算兩倍
FULL_FEATURE_COLUMNS_DEFAULT = 204_150  # SPEC §A FACT-RECEIPT：BTCUSDT/12h 全特徵 run 欄數
DEFAULT_OUT = REPO / "tests" / "_golden" / "preprov" / "output_size.json"
READ_REPEATS = 5
NEW_ARTIFACT_KEYS = ("content_sha256", "provenance")


def _dir_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())


def _manifest_delta_bytes(manifest_path: Path) -> Dict[str, int]:
    """manifest 位元組與移除新鍵後以生產同一序列化（indent=2、ensure_ascii=False）之位元組差。"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stripped = json.loads(json.dumps(manifest))
    for node in (stripped.get("artifacts") or {}).values():
        if isinstance(node, dict):
            for key in NEW_ARTIFACT_KEYS:
                node.pop(key, None)
    encode = lambda obj: len(json.dumps(obj, ensure_ascii=False, indent=2, default=str).encode("utf-8"))  # noqa: E731
    return {"manifest_bytes": int(manifest_path.stat().st_size), "manifest_delta_bytes": encode(manifest) - encode(stripped)}


def _read_seconds(path: Path) -> float:
    import pyarrow.parquet as pq

    samples: List[float] = []
    for _ in range(READ_REPEATS):
        t0 = time.perf_counter()
        pq.read_table(str(path))
        samples.append(time.perf_counter() - t0)
    return round(statistics.median(samples), 6)


class MeasurementError(RuntimeError):
    """量測不成立（SPEC Task 3.2 邊界③）：artifact 缺 `provenance` 指標、紀錄檔不存在或 parquet metadata 不可讀。
    不得以 0 位元組累計；`main` 寫錯誤收據並回 rc=1。"""


def measure_run(run_dir: Path) -> Dict[str, Any]:
    """單一 run 目錄：每個 artifact 之紀錄檔量測（只讀 manifest 宣告之紀錄檔路徑）。

    任一 artifact 缺 `provenance` 物件或其 `path`、紀錄檔不存在、parquet metadata 不可讀 ⇒ `MeasurementError`
    （CODEX-R5-P2-04：不得記 error 後以 0 累計而 rc=0）；manifest 無任何 artifact ⇒ 同。"""
    import pyarrow.parquet as pq

    run_dir = Path(run_dir)
    manifest_path = run_dir / "feature_manifest.json"
    if not manifest_path.is_file():
        raise MeasurementError(f"run 無 manifest：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts") or {}
    if not isinstance(artifacts, dict) or not artifacts:
        raise MeasurementError(f"manifest 無任何 artifact 節點：{manifest_path}")
    run_bytes = _dir_bytes(run_dir)
    out: Dict[str, Any] = {"run_dir_name": run_dir.name, "run_bytes": run_bytes, **_manifest_delta_bytes(manifest_path),
                           "artifacts": {}}
    for kind, node in artifacts.items():
        pointer = node.get("provenance") if isinstance(node, dict) else None
        if not isinstance(pointer, dict) or not pointer.get("path"):
            raise MeasurementError(f"{run_dir.name}/{kind}：manifest 節點無 provenance 指標（或缺 path）")
        record = run_dir / str(pointer["path"])
        if not record.is_file():
            raise MeasurementError(f"{run_dir.name}/{kind}：紀錄檔不存在 {pointer['path']}")
        try:
            rows = int(pq.ParquetFile(str(record)).metadata.num_rows)
        except Exception as exc:  # noqa: BLE001 — 任何解析失敗皆為量測不成立（具名改拋）
            raise MeasurementError(f"{run_dir.name}/{kind}：紀錄檔 parquet metadata 不可讀 "
                                   f"{pointer['path']}：{type(exc).__name__}: {exc}") from exc
        size = int(record.stat().st_size)
        out["artifacts"][kind] = {
            "record_bytes": size,
            "record_rows": rows,
            "record_percent_of_run": round(100.0 * size / run_bytes, 4) if run_bytes else None,
            "read_seconds": _read_seconds(record),
        }
    out["record_bytes_total"] = sum(int(a["record_bytes"]) for a in out["artifacts"].values())
    return out


def full_run_entry(cells: Dict[str, Any], full_run_dir: Optional[Path], full_columns: int,
                   measured: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """全特徵 run：實測（給定目錄；`measured` 為已量之結果則沿用）或以最大格（紀錄列數最多者）之每列位元組外推。"""
    if full_run_dir is not None:
        measured = measured if measured is not None else measure_run(full_run_dir)
        total = int(measured["record_bytes_total"])
        return {"extrapolated": False, "source": str(full_run_dir), "record_bytes_total": total, "measured": measured}
    best = None
    for cell, by_symbol in cells.items():
        for symbol, entry in by_symbol.items():
            raw = (entry.get("artifacts") or {}).get("raw") or {}
            if raw.get("record_rows"):
                if best is None or raw["record_rows"] > best[2]["record_rows"]:
                    best = (cell, symbol, raw)
    if best is None:
        raise RuntimeError("無任何格有 raw 紀錄檔可外推")
    per_row = best[2]["record_bytes"] / best[2]["record_rows"]
    return {"extrapolated": True, "source": f"{best[0]}/{best[1]} raw（{best[2]['record_rows']} 列）",
            "bytes_per_row": round(per_row, 3), "full_feature_columns": int(full_columns),
            "record_bytes_total": int(round(per_row * full_columns)),
            "note": "本機未給全特徵 run 目錄；以最大格每列位元組 × 全特徵欄數外推（zstd 壓縮比隨列數變，僅供量級對照）"}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="FFDSTAR Task 3.2 輸出增量量測")
    ap.add_argument("--cells", nargs="*", default=None, help="要量之格（預設 §V 全格）")
    ap.add_argument("--work-root", default=None, help="生成之暫存根（預設系統暫存下新目錄）")
    ap.add_argument("--full-run-dir", default=None, help="全特徵設定之 run 目錄（實作後生成者）")
    ap.add_argument("--full-feature-columns", type=int, default=FULL_FEATURE_COLUMNS_DEFAULT)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    receipt: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": " ".join(shlex.quote(a) for a in [sys.executable, str(Path(__file__).relative_to(REPO)),
                                                      *(argv if argv is not None else sys.argv[1:])]),
        "exit_code": 1,
        "approved_estimate_bytes": APPROVED_ESTIMATE_BYTES,
        "reapproval_threshold_bytes": REAPPROVAL_THRESHOLD_BYTES,
        "cells": {},
    }
    rc = 1
    try:
        from tests.feature_engineering import preprov_helpers as ph

        cells = list(args.cells) if args.cells else list(ph.CELLS)
        unknown = sorted(set(cells) - set(ph.CELLS))
        if unknown:
            raise ValueError(f"未知之格：{unknown}")
        full_run_dir = Path(args.full_run_dir) if args.full_run_dir else None
        # 全特徵 run 先量（不需生成）：其 manifest／紀錄檔不成立 ⇒ 立即 MeasurementError、rc=1，不先耗時生成各格
        full_measured = measure_run(full_run_dir) if full_run_dir is not None else None
        work_root = Path(args.work_root) if args.work_root else Path(tempfile.mkdtemp(prefix="preprov_size_"))
        receipt["work_root"] = str(work_root)
        cache = ph.RunCache(work_root)
        for cell in cells:  # 逐格單行程串行
            receipt["cells"][cell] = {}
            for symbol in ph.cell_symbols(cell):
                t0 = time.perf_counter()
                handle = cache.get(cell, symbol)
                entry = measure_run(handle.run_dir)
                entry["generation_seconds"] = round(time.perf_counter() - t0, 2)
                receipt["cells"][cell][symbol] = entry
        full = full_run_entry(receipt["cells"], full_run_dir, args.full_feature_columns, measured=full_measured)
        receipt["full_feature_run"] = full
        receipt["needs_user_reapproval"] = bool(full["record_bytes_total"] > REAPPROVAL_THRESHOLD_BYTES)
        receipt["vs_approved_estimate_ratio"] = round(full["record_bytes_total"] / APPROVED_ESTIMATE_BYTES, 4)
        rc = 0
    except Exception as exc:  # noqa: BLE001 — 失敗亦寫收據（含錯誤），rc=1
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["traceback"] = traceback.format_exc()
    receipt["exit_code"] = rc
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if receipt.get("needs_user_reapproval"):
        print(f"[preprov_output_size] 全特徵 run 紀錄檔 {receipt['full_feature_run']['record_bytes_total']} B "
              f"> {REAPPROVAL_THRESHOLD_BYTES} B ⇒ 須主委白話報使用者再核可", file=sys.stderr)
    print(f"[preprov_output_size] rc={rc} 收據：{out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
