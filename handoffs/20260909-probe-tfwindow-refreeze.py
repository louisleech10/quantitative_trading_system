#!/usr/bin/env python
"""TFWINDOW SPEC §G 證明：gap2 golden 差異**只含** metadata.ic_window_disclosure；並產 1h golden。

    venv/bin/python handoffs/20260909-probe-tfwindow-refreeze.py [--write-1h]

判定：live report 刪除 metadata.ic_window_disclosure 後之 canonical_sha == pre 檔 canonical_sha ⇒ 可 --write 重凍。
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import gap2_freeze_golden as g  # noqa: E402


def main() -> int:
    if "--only-1h" in sys.argv:
        _write_1h(); return 0
    pre = json.loads(g.PRE_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        report, _ = g._run(Path(td))
    live_sha = g._extract(report)["canonical_sha"]
    stripped = copy.deepcopy(report)
    d = stripped["metadata"].pop("ic_window_disclosure", None)
    stripped_sha = g._extract(stripped)["canonical_sha"]
    print(f"pre={pre['canonical_sha'][:12]} live={live_sha[:12]} live_minus_disclosure={stripped_sha[:12]}")
    print(f"disclosure={json.dumps(d, ensure_ascii=False)}")
    same = stripped_sha == pre["canonical_sha"]
    print("DIFF_ONLY_DISCLOSURE=" + ("YES" if same else "NO"))
    if "--write-1h" in sys.argv:
        _write_1h()
    return 0 if same else 1




def _write_1h() -> None:
    from tests.api.test_tfwindow import GOLDEN_1H, H5_1H, _golden_payload
    from tests.momentum.helpers.ichc_run import run_analyze
    rep = run_analyze(None, h5_glob=H5_1H)
    payload = _golden_payload(rep)
    payload["analysis_status"] = rep.get("analysis_status")
    payload["ic_window_disclosure"] = rep["metadata"].get("ic_window_disclosure")
    GOLDEN_1H.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_1H.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {GOLDEN_1H} keys={payload['window_keys']} status={payload['analysis_status']}")


if __name__ == "__main__":
    sys.exit(main())
