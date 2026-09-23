"""FF-TFMETA §G 前置探針：同參數真實 run 兩次，列出去除允許路徑後仍不等之 JSON 路徑（唯讀量測）。

用法：venv/bin/python handoffs/run_receipts/fftfmeta_probes/golden_determinism.py <start> <end> <multi|degraded>
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tests.feature_engineering import fftfmeta_golden_helpers as g  # noqa: E402


def _diff(a, b, prefix=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append(f"{prefix}.{key} (presence)")
            else:
                out.extend(_diff(a[key], b[key], f"{prefix}.{key}"))
    elif a != b:
        out.append(f"{prefix} {str(a)[:80]!r} != {str(b)[:80]!r}")
    return out


def main() -> int:
    start, end, kind = sys.argv[1], sys.argv[2], sys.argv[3]
    payload = g.multi_tf_payload() if kind == "multi" else g.degraded_single_tf_payload()
    runs = []
    for idx in range(2):
        root = Path(tempfile.mkdtemp(prefix=f"fftfmeta_det{idx}_"))
        t0 = time.time()
        art = g.run(root / "features", payload, start, end)
        runs.append((art, g.fingerprint(art), time.time() - t0))
    (a, fa, ta), (b, fb, tb) = runs
    print(f"seconds={ta:.1f},{tb:.1f} groups={fa['group_count']} rows={a.row_count}")
    print("group_files_equal", fa["group_files_sha256"] == fb["group_files_sha256"])
    print("groups_equal", fa["groups"] == fb["groups"])
    print("manifest_stripped_equal", fa["manifest_stripped_sha256"] == fb["manifest_stripped_sha256"])
    print("task_stripped_equal", fa["task_stripped_sha256"] == fb["task_stripped_sha256"])
    for line in _diff(g.strip_manifest(a.manifest), g.strip_manifest(b.manifest), "manifest")[:40]:
        print("DIFF", line)
    ma = json.loads(g.canonical_json(a.metadata))
    mb = json.loads(g.canonical_json(b.metadata))
    for line in _diff(g.strip_task(ma), g.strip_task(mb), "task")[:40]:
        print("DIFF", line)
    print("allowed", json.dumps(fa["allowed"], ensure_ascii=False))
    print("validation", json.dumps(ma.get("validation", ma.get("quality_validation")), ensure_ascii=False, default=str)[:400])
    print("metadata_keys", sorted(ma.keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
