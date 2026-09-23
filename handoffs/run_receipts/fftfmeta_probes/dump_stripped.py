"""FF-TFMETA §G 前置探針：單程序跑一次輕量 run，把去除允許路徑後之 manifest 與 task record 寫成 JSON（跨程序比對用）。

用法：venv/bin/python handoffs/run_receipts/fftfmeta_probes/dump_stripped.py <multi|degraded> <out.json>
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tests.feature_engineering import fftfmeta_golden_helpers as g  # noqa: E402


def main() -> int:
    kind, out = sys.argv[1], Path(sys.argv[2])
    payload = g.multi_tf_payload() if kind == "multi" else g.degraded_single_tf_payload()
    root = Path(tempfile.mkdtemp(prefix="fftfmeta_dump_"))
    art = g.run(root / "features", payload, *g.WINDOW)
    out.write_text(json.dumps({"manifest": g.strip_manifest(art.manifest)}, ensure_ascii=False, indent=1,
                              sort_keys=True, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
