"""FF-STAT §G 基準凍結（docs/FFSTAT_SPEC.md §G）：動工前於當下 HEAD 以輕量真實設定跑一次並錄得基準。

錄得內容（不改生產碼）：
- 基礎欄（非 `*_L65.parquet`）逐欄四 hash（dtype、shape、NaN mask sha256、值 sha256）與列數；
- 衍生欄集合（`*_L65.parquet` 內之 `<欄>_fracdiff`／`<欄>_diffK`）；
- 每基礎欄：是否被名字免檢（現行 `is_safe_skip`）、是否 fracdiff、ADF 差分階數（由衍生欄存在讀得）、
  所用 `d`（由本次隔離 d* 快取檔讀得；鍵不符者記 None）。

用法（須明示其一；無旗標或以 --out 指向基準檔即拒絕，比照 FF-TFMETA r8）：
  venv/bin/python handoffs/run_receipts/ffstat_probes/freeze_baseline.py --refreeze-baseline
  venv/bin/python handoffs/run_receipts/ffstat_probes/freeze_baseline.py --out <tmp 路徑>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from _isolate import isolate  # noqa: E402  須先於任何 momentum／helper 匯入

ISOLATED_ROOT = isolate()

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from _isolate import isolate_dstar_cache  # noqa: E402
from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
from momentum.FeatureEngineering.utils.adf_safe_skip import is_safe_skip  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

DSTAR_DIR = isolate_dstar_cache(ISOLATED_ROOT)
REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO / "tests" / "_golden" / "ffstat" / "baseline.json"
_DERIVED_SUFFIXES = ("_fracdiff", "_diff1", "_diff2")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def column_fingerprint(values: np.ndarray) -> dict:
    """四 hash：dtype、shape、NaN mask、值（NaN 以 0 取代後之位元組）。"""
    arr = np.asarray(values)
    mask = np.isnan(arr) if arr.dtype.kind == "f" else np.zeros(arr.shape, dtype=bool)
    filled = np.where(mask, 0, arr) if arr.dtype.kind == "f" else arr
    return {"dtype": str(arr.dtype), "shape": list(arr.shape), "nan_mask": _sha(mask.tobytes()),
            "values": _sha(np.ascontiguousarray(filled).tobytes())}


def collect(run_dir: Path) -> dict:
    base: dict = {}
    derived: list = []
    rows = None
    for p in sorted(run_dir.rglob("*.parquet")):
        table = pq.read_table(p)
        names = [n for n in table.column_names if n not in ("timestamp", "__index_level_0__", "index")]
        if p.name.endswith("_L65.parquet"):
            derived.extend(names)
            continue
        for n in names:
            col = table.column(n).to_numpy(zero_copy_only=False)
            rows = len(col)
            base[n] = column_fingerprint(col)
    d_entries: dict = {}
    for f in sorted(DSTAR_DIR.glob("*.json")):
        d_entries.update({k: v.get("d_star") for k, v in json.loads(f.read_text(encoding="utf-8")).get("entries", {}).items()})
    derived_set = set(derived)
    decisions = {}
    for n in base:
        order = next((k for k in (1, 2) if f"{n}_diff{k}" in derived_set), 0)
        # 現行 d* 快取之鍵為加週期標記前之欄名（`close_trend_…`），落盤欄名為 `close_1h_trend_…`（主委實跑 2026-09-24）；
        # 此對照僅供讀取舊版基準，不涉任何生產判定
        cache_key = n.replace(f"_{h.PRIMARY_TF}_", "_", 1)
        decisions[n] = {"name_exempt": bool(is_safe_skip(n)), "fracdiff": f"{n}_fracdiff" in derived_set,
                        "adf_diff_order": order, "d": d_entries.get(cache_key)}
    return {"rows": rows, "base": base, "derived": sorted(derived_set), "decisions": decisions,
            "dstar_entries": len(d_entries)}


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--refreeze-baseline", action="store_true")
    g.add_argument("--out")
    args = ap.parse_args()
    out = BASELINE if args.refreeze_baseline else Path(args.out).resolve()
    if not args.refreeze_baseline and out == BASELINE.resolve():
        print("REFUSED: --out 不得指向基準檔；重凍結須用 --refreeze-baseline", file=sys.stderr)
        return 2
    root = ISOLATED_ROOT / "run"
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root / "features"))
    result = factory.generate_features(h.SYMBOL, h.PRIMARY_TF, config_override=h.stat_payload([h.PRIMARY_TF]),
                                       force_regenerate=True, start_date=h.WINDOW[0], end_date=h.WINDOW[1], persist=True)
    run_dir = root / "features" / h.SYMBOL / h.PRIMARY_TF / str(result.metadata["config_hash"])
    data = collect(run_dir)
    data.update({"spec": "docs/FFSTAT_SPEC.md §G", "symbol": h.SYMBOL, "timeframe": h.PRIMARY_TF,
                 "window": list(h.WINDOW), "quality_status": result.metadata.get("quality_status")})
    # Task 2.3「平穩化關閉、未填起始日 ⇒ 行為與改前逐位元組相同」之基準（r18 codex P1-03）
    off_root = ISOLATED_ROOT / "auto_off"
    off_end = "2024-02-29"
    off_factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    off_factory._storage = FeatureStorage(str(off_root / "features"))
    off = off_factory.generate_features(h.SYMBOL, h.PRIMARY_TF,
                                        config_override=h.stat_payload([h.PRIMARY_TF], fracdiff=False, adf=False),
                                        force_regenerate=True, start_date=None, end_date=off_end, persist=True)
    off_dir = off_root / "features" / h.SYMBOL / h.PRIMARY_TF / str(off.metadata["config_hash"])
    data["auto_off"] = {"end_date": off_end, "base": collect(off_dir)["base"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    dec = data["decisions"].values()
    print(f"RESULT out={out} rows={data['rows']} base={len(data['base'])} derived={len(data['derived'])} "
          f"name_exempt={sum(x['name_exempt'] for x in dec)} fracdiff={sum(x['fracdiff'] for x in dec)} "
          f"adf_diff={sum(1 for x in dec if x['adf_diff_order'])} d_known={sum(1 for x in dec if x['d'] is not None)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
