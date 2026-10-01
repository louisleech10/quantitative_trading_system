"""探針：驗 tests/feature_engineering/test_icpostleak.py 之逐步驟 oracle 之 dtype／核心建模。
令 oracle 之遮罩為 identity，與**現行未遮罩之生產**逐分支 × 七組合逐位元組比對；全等 ⇒ 實作後之差異只剩遮罩本身。
（registry sink 之 spy 斷言與分片前提不在本探針範圍；sharded 以同一 monkeypatch 實跑。）"""
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "handoffs/run_receipts/ffstat_probes"))
from _isolate import isolate  # noqa: E402

isolate("probe_oracle_unmasked_")

import pytest  # noqa: E402

from tests.feature_engineering import test_icpostleak as t  # noqa: E402

t._oracle_mask = lambda output, step_input, window: np.array(output, dtype=np.float64, copy=True)  # identity
frame = t._real_frame()
bad = 0
for branch in t.BRANCHES:
    for steps in t.COMBOS:
        mp = pytest.MonkeyPatch()
        spec = dict(t.BRANCHES[branch])
        spec.pop("spy", None)  # 現行生產無遮罩；spy 與本探針無關
        try:
            got = t._run_branch(mp, Path(tempfile.mkdtemp()), branch, steps, frame,
                                spec_override=spec).to_numpy(dtype=np.float64)
        finally:
            mp.undo()
        want = t._oracle(branch, steps, frame)
        diff = int((~((got == want) | (np.isnan(got) & np.isnan(want)))).sum())
        bad += diff > 0
        print(f"{branch:22s} {'+'.join(steps):22s} diff_cells={diff}")
mp = pytest.MonkeyPatch()
cfg = t.CONTRACT["registry_chunked_append"]
try:
    got = t._run_branch(mp, Path(tempfile.mkdtemp()), "registry_chunked", cfg["steps"], frame, mode=cfg["mode"],
                        spec_override={"env": cfg["env"], "entry": "transform_registry_groups_to_sink"})
finally:
    mp.undo()
values = t._f32(frame.to_numpy(dtype=np.float64))
by_window = t.FeaturePreprocessor(t._config(cfg["steps"], "append"))._rolling_zscore_2d(values, list(t.Z_WINDOWS), 1e-8,
                                                                                         mode="append")
for w in t.Z_WINDOWS:
    cols = [f"{c}_zscore_{w}" for c in frame.columns]
    want = t._f32(np.asarray(by_window[w], dtype=np.float64))
    a = got[cols].to_numpy(dtype=np.float64)
    diff = int((~((a == want) | (np.isnan(a) & np.isnan(want)))).sum())
    bad += diff > 0
    print(f"registry_chunked_append window={w} diff_cells={diff}")
print(f"MISMATCH_CASES={bad}")
