"""FF-TFMETA 前置探針：輕量設定之真實 run 單次計時與品質欄觀測（唯讀量測）。

用法：venv/bin/python handoffs/run_receipts/fftfmeta_probes/time_one_run.py <start> <end> <multi|single|degraded>
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from _isolate import isolate  # noqa: E402  須先於任何 momentum／helper 匯入（r7 codex P1-01）

ISOLATED_ROOT = isolate()

from tests.feature_engineering import fftfmeta_golden_helpers as g  # noqa: E402


def main() -> int:
    start, end, kind = sys.argv[1], sys.argv[2], sys.argv[3]
    payload = {"multi": g.multi_tf_payload, "single": lambda: g.fast_payload(["1h"]),
               "degraded": g.degraded_single_tf_payload}[kind]()
    root = Path(tempfile.mkdtemp(prefix="fftfmeta_time_"))
    t0 = time.time()
    art = g.run(root / "features", payload, start, end)
    fp = g.fingerprint(art)
    print(f"RESULT seconds={time.time() - t0:.1f} groups={fp['group_count']} rows={art.row_count}")
    print("RESULT allowed", json.dumps(fp["allowed"], ensure_ascii=False))
    print("RESULT validation", json.dumps(art.metadata.get("validation"), ensure_ascii=False, default=str)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
