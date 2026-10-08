"""C5 前提探針（HEAD 6e07e0ad）：單週期 CGSA 同 work dir 第二次生成——resume 是否被呼叫、L1 是否重算、
群組 id 是否出現 `_2` 後綴、基礎欄指紋是否與第一次相等。"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, ".")
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry  # noqa: E402
from momentum.FeatureEngineering.feature_factory import FeatureFactory  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="c5probe_"))
mp = pytest.MonkeyPatch()
h.prepare_stat_env(mp, tmp)
calls, l1 = [], []
orig_resume = ColumnGroupRegistry.resume_from_manifest.__func__
orig_l1 = FeatureFactory._layer1_atomic_indicators


def spy(cls, work_dir):
    reg = orig_resume(cls, work_dir)
    calls.append(sum(1 for _ in reg.iter_all()))
    return reg


def l1_spy(self, *a, **k):
    l1.append(len(calls))
    return orig_l1(self, *a, **k)


mp.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(spy))
mp.setattr(FeatureFactory, "_layer1_atomic_indicators", l1_spy)
payload = h.stat_payload()
root, f1, r1 = h.run_stat(tmp, payload, force_regenerate=False)
fp1 = h.base_fingerprints(root)
ids1 = sorted(gid for gid, _ in f1._cgsa_registry.iter_all()) if f1._cgsa_registry else []
root, f2, r2 = h.run_stat(tmp, payload, force_regenerate=False)
fp2 = h.base_fingerprints(root)
ids2 = sorted(gid for gid, _ in f2._cgsa_registry.iter_all()) if f2._cgsa_registry else []
out = {
    "resume_calls_nonempty_groups": calls,
    "l1_calls_resume_count_at_time": l1,
    "run_status": [r1.metadata.get("run_status"), r2.metadata.get("run_status")],
    "groups_first": len(ids1), "groups_second": len(ids2),
    "suffixed_second": [g for g in ids2 if g.endswith("_2")][:10],
    "fingerprint_equal": fp1 == fp2, "n_cols": [len(fp1), len(fp2)],
    "fp_diff_cols": sorted(set(fp1) ^ set(fp2))[:10] + [c for c in fp1 if c in fp2 and fp1[c] != fp2[c]][:10],
}
print("C5PROBE", json.dumps(out, ensure_ascii=False))
mp.undo()
