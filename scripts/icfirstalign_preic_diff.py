"""ICFIRSTALIGN Task 2.3：新舊 pre-IC 差異之明列（docs/ICFIRSTALIGN_SPEC.md）。

同 S2 設定（真實 kline BTCUSDT 12h、`icfirstalign_helpers.s2_payload()`、窗 S2_WINDOW、平穩化關閉）：
- `old <out>`：於改前樹（`git worktree` 之 b2 前 commit；PYTHONPATH 指向該樹）以記憶體路徑（`FFACT_USE_CGSA=0`）跑
  `run_ic_first` 至 raw 落盤；IC 階段之 `AlignmentViolationError`（SPEC Task 2.3 邊界①）只在 raw 已落盤後容許。
- `new <out>`：於本樹以正式 CGSA 生成之 `run_ic_first` 跑完。
- `compare <old_out> <new_out> <receipt.json>`：依 raw sidecar 時間戳對齊，逐欄列出欄集合差與值差，
  並依 `classify` 分類；`unexplained` 為無法歸類之欄數（須為 0）。

一切寫入在 `<out>` 下（features 根、registry、CGSA 工作目錄）；不寫 data_cache。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parents[1]
KLINE_DIR = str(REPO / "data_cache" / "feature_klines")
SYMBOL, TF = "BTCUSDT", "12h"


def _prepare(out: Path, cgsa: bool) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "FFACT_LAYER1_PARALLEL": "0", "FFACT_USE_CGSA": "1" if cgsa else "0", "FFACT_WARMUP_TRIM": "1",
        "FFACT_MULTI_TF_PARALLEL": "0", "FFACT_FEATURE_REGISTRY_PATH": str(out / "features" / "registry.json"),
        "FFACT_CGSA_WORK_DIR": str(out / "cgsa_work"),
    })
    os.chdir(out)
    if not (out / "config").exists():
        (out / "config").symlink_to(REPO / "config")
    return out / "features"


def _factory(root: Path) -> Any:
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    return factory


def run_old(out: Path) -> None:
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.core.contracts import AlignmentViolationError
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.warmup_window import resolve_output_window
    from tests.feature_engineering import icfirstalign_helpers as h

    root = _prepare(out, cgsa=False)
    factory = _factory(root)
    config = factory._resolve_config(h.s2_payload())
    start, end = h.S2_WINDOW
    factory._current_output_window = resolve_output_window(config, TF, start, end)  # 改前用法（test_b6_warmup_trim）
    try:
        factory.run_ic_first(SYMBOL, TF, config,
                             config_hash=factory._compute_config_hash(config, SYMBOL, TF, start_date=start, end_date=end),
                             ic_engine=ICEngine({"methods": ["spearman"]}), feature_reader=FeatureReader(str(root)),
                             storage=factory._storage, ic_threshold=0.0, persist=True)
    except AlignmentViolationError:
        if not list(root.rglob("raw/*.parquet")):
            raise
    print(json.dumps({"old_raw": [str(p) for p in sorted(root.rglob("raw/*.parquet"))][:3]}, ensure_ascii=False))


def run_new(out: Path) -> None:
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from tests.feature_engineering import icfirstalign_helpers as h

    root = _prepare(out, cgsa=True)
    factory = _factory(root)
    config = factory._resolve_config(h.s2_payload())
    result = factory.run_ic_first(SYMBOL, TF, config, start_date=h.S2_WINDOW[0], end_date=h.S2_WINDOW[1],
                                  ic_engine=ICEngine({"methods": ["spearman"]}), feature_reader=FeatureReader(str(root)),
                                  ic_threshold=0.0)
    print(json.dumps({"new_config_hash": result.metadata["config_hash"]}))


def _load_raw(out: Path) -> "Any":
    """raw 成品之全部欄（依 raw sidecar 時間戳為索引）。"""
    import pandas as pd
    import pyarrow.parquet as pq

    manifests = sorted((out / "features").rglob("feature_manifest.json"))
    if len(manifests) != 1:
        raise SystemExit(f"{out}：feature_manifest.json 須恰一份，實得 {len(manifests)}")
    run_dir = manifests[0].parent
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    axis_table = pq.read_table(str(run_dir / manifest["row_index"]["path"]))
    axis = pd.DatetimeIndex(pd.to_datetime(axis_table.column("timestamp").to_numpy(), unit="s"))
    frames = []
    for group in manifest["artifacts"]["raw"]["groups"].values():
        table = pq.read_table(str(run_dir / group["path"]))
        cols = [c for c in table.column_names if c not in ("timestamp", "__index_level_0__", "index")]
        frames.append(table.select(cols).to_pandas())
    frame = pd.concat(frames, axis=1)
    if len(frame) != len(axis):
        raise SystemExit(f"{out}：raw 列數 {len(frame)} ≠ sidecar {len(axis)}")
    frame.index = axis
    return frame, manifest


def classify(name: str, old: Any, new: Any, sanitize_cap: float) -> str:
    """單欄值差之來源分類；回傳類別名，無法歸類 ⇒ "unexplained"。"""
    import numpy as np

    o = np.asarray(old, dtype=np.float64)
    n = np.asarray(new, dtype=np.float64)
    # 遮罩以 NaN 定義（inf 為有值；inf→NaN 屬 numeric_sanitize 之來源）
    both = ~np.isnan(o) & ~np.isnan(n)
    nan_only_new = ~np.isnan(o) & np.isnan(n)
    nan_only_old = np.isnan(o) & ~np.isnan(n)
    # 只認「新值精確等於對舊值施作具名轉換之結果」；不以大小容差歸類（審碼 b2 r1 codex P2-01：容差會吸收真實漂移）
    if not nan_only_old.any() and nan_only_new.any() and np.array_equal(o[both], n[both]):
        if np.all(~np.isfinite(o[nan_only_new]) | (np.abs(o[nan_only_new]) > sanitize_cap)):
            return "numeric_sanitize"  # CGSA 串流之 Layer B：inf／|v|>cap → NaN（逐值精確）
        return "unexplained"
    if not (nan_only_new.any() or nan_only_old.any()):
        with np.errstate(over="ignore"):
            as_f16 = o[both].astype(np.float16).astype(np.float64)
        if np.array_equal(as_f16, n[both]):
            return "cgsa_storage_float16"  # CGSA 落盤逐欄 dtype 政策（manifest storage_dtype=mixed）：新值＝舊值轉 float16
    return "unexplained"


def compare(old_out: Path, new_out: Path, receipt: Path) -> int:
    import numpy as np

    old, old_manifest = _load_raw(old_out)
    new, new_manifest = _load_raw(new_out)
    # 命名差：CGSA 落盤欄名帶週期標記（`close_12h_…`），記憶體路徑不帶（`close_…`）——以去除首個 `_<TF>` 標記之
    # 正規名對應；對應須一對一，否則整欄列入 old_only／new_only 不吸收
    tag = f"_{TF}"
    canonical = {c: (c.replace(tag + "_", "_", 1) if tag + "_" in c else (c[: -len(tag)] if c.endswith(tag) else c))
                 for c in new.columns}
    if len(set(canonical.values())) == len(canonical):
        renamed = {c: canonical[c] for c in new.columns if canonical[c] != c}
        new = new.rename(columns=canonical)
    else:
        renamed = {}
    common_rows = old.index.intersection(new.index)
    old_only = sorted(set(old.columns) - set(new.columns))
    new_only = sorted(set(new.columns) - set(old.columns))
    sanitize_cap = 1e18
    per_column: Dict[str, str] = {}
    for col in sorted(set(old.columns) & set(new.columns)):
        o = old.loc[common_rows, col].to_numpy(dtype=np.float64)
        n = new.loc[common_rows, col].to_numpy(dtype=np.float64)
        same = np.array_equal(np.isnan(o), np.isnan(n)) and np.array_equal(o[~np.isnan(o)], n[~np.isnan(n)])
        per_column[col] = "identical" if same else classify(col, o, n, sanitize_cap)
    counts: Dict[str, int] = {}
    for kind in per_column.values():
        counts[kind] = counts.get(kind, 0) + 1
    payload = {
        "generated_by": "scripts/icfirstalign_preic_diff.py",
        "setting": {"symbol": SYMBOL, "timeframe": TF, "payload": "icfirstalign_helpers.s2_payload()",
                    "old": "記憶體路徑 FFACT_USE_CGSA=0（改前樹）", "new": "正式 CGSA 生成"},
        "rows": {"old": int(len(old)), "new": int(len(new)), "common": int(len(common_rows)),
                 "old_first": str(old.index[0]) if len(old) else None, "new_first": str(new.index[0]) if len(new) else None},
        "columns": {"old": int(old.shape[1]), "new": int(new.shape[1]), "old_only": old_only, "new_only": new_only,
                    "tf_tag_renamed": len(renamed)},
        "value_diff_counts": counts,
        "value_diff_columns": {k: v for k, v in per_column.items() if v != "identical"},
        "unexplained": int(counts.get("unexplained", 0)),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("rows", "value_diff_counts", "unexplained")}, ensure_ascii=False))
    print(json.dumps({"old_only": old_only[:40], "new_only": new_only[:40]}, ensure_ascii=False))
    return 0


def main(argv: List[str]) -> int:
    if len(argv) >= 2 and argv[0] == "old":
        run_old(Path(argv[1]).resolve())
        return 0
    if len(argv) >= 2 and argv[0] == "new":
        run_new(Path(argv[1]).resolve())
        return 0
    if len(argv) == 4 and argv[0] == "compare":
        return compare(Path(argv[1]).resolve(), Path(argv[2]).resolve(), Path(argv[3]).resolve())
    print("用法：icfirstalign_preic_diff.py old <out> | new <out> | compare <old_out> <new_out> <receipt.json>",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
