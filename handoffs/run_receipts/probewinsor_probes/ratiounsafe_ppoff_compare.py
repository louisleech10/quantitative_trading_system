"""PROBEWINSOR Task 1.3：RATIOUNSAFE 前處理關臂於目前碼態重產，與 tests/_golden/ratiounsafe/baseline.json 所記逐鍵比對。

用法：venv/bin/python handoffs/run_receipts/probewinsor_probes/ratiounsafe_ppoff_compare.py <out.json>
比對法＝RATIOUNSAFE 凍結腳本之既有紀錄器 `s1_record(arm, False)`（`--stage before` 產 `s1_<arm>_preprocessing_disabled`
所用同一函式），兩臂（off、on）各重產一次，與基準逐鍵精確相等（不容差）；不同之鍵列出供歸因 §C。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


def _freeze_module() -> Any:
    spec = importlib.util.spec_from_file_location("freeze_ratiounsafe_baseline",
                                                  REPO / "scripts" / "freeze_ratiounsafe_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list) -> int:
    out_path = Path(argv[0])
    freeze = _freeze_module()
    golden = json.loads((REPO / "tests/_golden/ratiounsafe/baseline.json").read_text(encoding="utf-8"))
    result: Dict[str, Any] = {"compare": "freeze_ratiounsafe_baseline.s1_record(arm, False) vs "
                                         "tests/_golden/ratiounsafe/baseline.json#s1_<arm>_preprocessing_disabled",
                              "arms": {}}
    for arm in ("off", "on"):
        t0 = time.time()
        got = json.loads(json.dumps(freeze.s1_record(arm, False), ensure_ascii=False, default=str))
        ref = golden[f"s1_{arm}_preprocessing_disabled"]
        diff_keys = sorted(k for k in set(ref) | set(got) if ref.get(k) != got.get(k))
        result["arms"][arm] = {"equal": not diff_keys, "diff_keys": diff_keys,
                               "seconds": round(time.time() - t0, 1)}
    result["equal"] = all(a["equal"] for a in result["arms"].values())
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if k != "arms" else {a: {"equal": x["equal"], "diff_keys": x["diff_keys"][:8]}
                                                  for a, x in v.items()}) for k, v in result.items()},
                     ensure_ascii=False))
    return 0 if result["equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
