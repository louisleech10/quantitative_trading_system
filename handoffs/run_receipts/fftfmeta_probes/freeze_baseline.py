"""FF-TFMETA §G 動工前凍結：於當下 HEAD（只有空殼、預設行為未改）以真實 kline 跑兩個 reference，寫 baseline。

用法：venv/bin/python handoffs/run_receipts/fftfmeta_probes/freeze_baseline.py
產出：tests/_golden/fftfmeta/baseline.json（健康多週期 multi、降級單週期 degraded 之指紋與 run 參數）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from _isolate import isolate  # noqa: E402  須先於任何 momentum／helper 匯入（r7 codex P1-01）

ISOLATED_ROOT = isolate()

from tests.feature_engineering import fftfmeta_golden_helpers as g  # noqa: E402


def main() -> int:
    head = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    out = {"frozen_at_head": head, "symbol": g.SYMBOL, "window": list(g.WINDOW), "references": {}}
    for name, payload in (("multi", g.multi_tf_payload()), ("degraded", g.degraded_single_tf_payload())):
        root = Path(tempfile.mkdtemp(prefix=f"fftfmeta_freeze_{name}_"))
        os.environ["FFACT_CGSA_WORK_DIR"] = str(root / "cgsa_work")  # 同 tests/feature_engineering/conftest.py，不落 repo
        art = g.run(root / "features", payload, *g.WINDOW)
        fp = g.fingerprint(art)
        out["references"][name] = {"payload": payload, **fp}
        print(f"FROZEN {name}: groups={fp['group_count']} manifest_bytes={fp['manifest_bytes']} task_bytes={fp['task_bytes']} "
              f"validation_nan_ratio={art.metadata.get('validation', {}).get('nan_ratio')}")
    g.BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    g.BASELINE_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {g.BASELINE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
