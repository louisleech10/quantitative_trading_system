#!/usr/bin/env python
"""TFWINDOW SPEC §G 證明：gap2 golden 差異**只含** metadata.ic_window_disclosure；並產 1h golden。

    venv/bin/python handoffs/20260909-probe-tfwindow-refreeze.py [--write-1h | --only-1h]

判定（R5 CODEX-R5-P1-01／COMPOSER-R5-P2-01 修法：對照**不可變**的重凍前 digest，不再讀會被 --write 覆蓋的 PRE_PATH）：
  ① live 報告刪 metadata.ic_window_disclosure 後之 canonical_sha == tests/golden/tfwindow/gap2_pre_disclosure.sha（7a1dd8f0 之投影 digest）
  ② live 報告 canonical_sha == 現行 PRE_PATH（重凍後的 golden 仍與 live 一致）
兩者皆真才 DIFF_ONLY_DISCLOSURE=YES（rc=0）。
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

PRE_DISCLOSURE_SHA = (REPO / "tests/golden/tfwindow/gap2_pre_disclosure.sha").read_text(encoding="utf-8").strip()


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
    print(f"pinned_pre_disclosure={PRE_DISCLOSURE_SHA[:12]} current_pre={pre['canonical_sha'][:12]} live={live_sha[:12]} live_minus_disclosure={stripped_sha[:12]}")
    print(f"disclosure={json.dumps(d, ensure_ascii=False)}")
    only_disclosure = stripped_sha == PRE_DISCLOSURE_SHA
    live_matches_pre = live_sha == pre["canonical_sha"]
    print(f"STRIPPED_EQ_PINNED={'YES' if only_disclosure else 'NO'} LIVE_EQ_CURRENT_PRE={'YES' if live_matches_pre else 'NO'}")
    same = only_disclosure and live_matches_pre
    print("DIFF_ONLY_DISCLOSURE=" + ("YES" if same else "NO"))
    if "--write-1h" in sys.argv:
        _write_1h()
    return 0 if same else 1


def _write_1h() -> None:
    from tests.api.test_tfwindow import GOLDEN_1H, H5_1H, _golden_payload
    from tests.momentum.helpers.ichc_run import run_analyze
    rep = run_analyze(None, h5_glob=H5_1H)
    payload = _golden_payload(rep)
    GOLDEN_1H.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_1H.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"WROTE {GOLDEN_1H} keys={payload['window_keys']} status={payload['analysis_status']} reason={payload['oos_downgrade_reason']}")


if __name__ == "__main__":
    sys.exit(main())
