"""刪除舊算法之特徵 run（使用者 2026-10-03 核可：A＋B 全刪）。

用法（repo 根目錄）：
  venv/bin/python handoffs/run_receipts/prered_probes/delete_old_feature_runs.py          # 只列清單（乾跑）
  venv/bin/python handoffs/run_receipts/prered_probes/delete_old_feature_runs.py --apply  # 實刪
實刪：data_cache/features/<sym>/<tf>/<config_hash>/ 之合法 run 經正規 RunLifecycleManager.delete_run
（mark-deleting → 刪檔 → 移除 registry 條目）；其餘雜項只印出 rm 指令，由使用者自行貼上執行。
不碰：data_cache/feature_klines*、data_cache/kline_cache.h5（K 線原始資料）、data_cache/features/.locks。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
FEATURES = REPO / "data_cache" / "features"


def _du(p: Path) -> str:
    out = subprocess.run(["du", "-sh", str(p)], capture_output=True, text=True).stdout.split()
    return out[0] if out else "?"


def main(apply: bool) -> int:
    from momentum.factories import create_run_lifecycle_manager
    from momentum.FeatureEngineering.run_paths import validate_config_hash

    runs, odd = [], []
    for d in sorted(FEATURES.glob("*/*/*")):
        if not d.is_dir() or d.parts[-3].startswith("."):
            continue
        sym, tf, h = d.parts[-3], d.parts[-2], d.parts[-1]
        try:
            validate_config_hash(h)
            runs.append((sym, tf, h, d))
        except Exception:
            odd.append(d)
    print(f"合法 run {len(runs)} 個：")
    for sym, tf, h, d in runs:
        print(f"  {_du(d):>6}  {sym}/{tf}/{h}")
    manual = odd + sorted(FEATURES.glob("*.h5")) + sorted(FEATURES.glob("registry.json.bak*"))
    manual += [REPO / "data_cache" / "cgsa_work", REPO / "data_cache" / "feature_preprocessing"]
    manual = [p for p in manual if p.exists()]
    if not apply:
        print("\n（乾跑；加 --apply 實刪上列 run）")
    else:
        mgr = create_run_lifecycle_manager(features_root=FEATURES, cgsa_root=REPO / "data_cache" / "cgsa_work")
        failed = 0
        for sym, tf, h, _d in runs:
            try:
                res = mgr.delete_run(sym, tf, h)
                errs = getattr(res, "errors", None)
                print(f"  刪除 {sym}/{tf}/{h}：{'有錯誤 ' + str(errs) if errs else 'ok'}")
                failed += bool(errs)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  刪除 {sym}/{tf}/{h} 失敗：{type(exc).__name__}: {exc}")
        print(f"\n完成：{len(runs) - failed} 成功、{failed} 失敗")
    print("\n以下雜項請自行貼上執行（非合法 run 目錄、舊 h5、登記表備份、舊 CGSA 工作目錄與 d* 快取）：")
    for p in manual:
        print(f"rm -rf '{p}'   # {_du(p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv[1:]))
