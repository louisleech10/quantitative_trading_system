"""ICFIRSTALIGN 乙之改前基準凍結（docs/ICFIRSTALIGN_SPEC.md v18 §G、Task 4.0、Task 4.1）。

只准以 HEAD（改前生產碼）執行；真實 kline、一切寫入隔離於暫存目錄。
stage：
- `l3-default`：S2（預設 L3 臂：numba 多窗串流）之 raw L3 欄逐欄 float32 bytes sha256 ⇒
  tests/_golden/icfirstalign/l3_default_arm.json（Task 4.0「預設臂之 registry L3 群組與改前逐位元組相等」）。
- `probe`、`calibration`：§G 預熱探測與校準封包之 HEAD 甲／乙基準（Task 4.1），見各 stage 函式。

用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python scripts/freeze_icfirstalign_baseline.py <stage>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import numpy as np

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "tests" / "_golden" / "icfirstalign"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def column_digest(values: Any) -> str:
    arr = np.ascontiguousarray(np.asarray(values, dtype=np.float32))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def l3_digests(root: Path, config_hash: str) -> Dict[str, str]:
    """raw 成品中 L3 群組之全部欄 → float32 bytes sha256（依欄名排序）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from tests.feature_engineering import icfirstalign_helpers as h

    reader = FeatureReader(str(root))
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = sorted(c for name, g in manifest["artifacts"]["raw"]["groups"].items() if "_L3_" in name
                  for c in g.get("columns", []))
    frame = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    return {c: column_digest(frame[c].to_numpy()) for c in cols}


def stage_l3_default() -> Dict[str, Any]:
    import pytest

    from tests.feature_engineering import icfirstalign_helpers as h

    mp = pytest.MonkeyPatch()
    try:
        tmp = Path(tempfile.mkdtemp(prefix="icfa_freeze_l3_"))
        root = h.isolated(mp, tmp)
        for key in ("FFACT_USE_NUMBA_ROLLING", "FFACT_L3_STREAMING", "FFACT_L3_MULTI_WINDOW", "FFACT_L3_PERSIST_MODE"):
            mp.delenv(key, raising=False)
        _, result = h.generate_s2(root)
        digests = l3_digests(root, str(result.metadata["config_hash"]))
    finally:
        mp.undo()
    return {"schema_version": 1, "setting": "S2 預設 L3 臂（numba 多窗串流）", "window": list(h.S2_WINDOW),
            "column_count": len(digests), "columns": digests}


STAGES = {"l3-default": ("l3_default_arm.json", stage_l3_default)}


def main(argv: Any = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1 or args[0] not in STAGES:
        print(f"用法：{Path(__file__).name} <{'|'.join(STAGES)}>", file=sys.stderr)
        return 2
    name, fn = STAGES[args[0]]
    os.environ.setdefault("PYTHONHASHSEED", "0")
    payload = fn()
    GOLDEN.mkdir(parents=True, exist_ok=True)
    (GOLDEN / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {GOLDEN / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
