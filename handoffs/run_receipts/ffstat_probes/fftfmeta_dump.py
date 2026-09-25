"""FF-STAT：以指定程式樹跑 FF-TFMETA golden 情境，輸出去除允許路徑之 manifest／task 與其 sha256（遷移證明用）。

用法：python fftfmeta_dump.py <repo 根> <情境名 degraded|multi> <輸出 json>
"""
import json
import os
import sys
import tempfile
from pathlib import Path

root, ref, out = Path(sys.argv[1]).resolve(), sys.argv[2], Path(sys.argv[3]).resolve()
real_data = Path(__file__).resolve().parents[3] / "data_cache"
os.chdir(root)
sys.path.insert(0, str(root))
import pytest  # noqa: E402

from tests.feature_engineering import fftfmeta_golden_helpers as g  # noqa: E402

base = g.load_baseline()["references"][ref]
tmp = Path(tempfile.mkdtemp(prefix="fftfmeta_dump_"))
g.prepare_env(pytest.MonkeyPatch(), tmp)
(Path.cwd() / "data_cache").symlink_to(real_data)
art = g.run(tmp / "features", base["payload"], *g.WINDOW)
fp = g.fingerprint(art)
features_root = str(art.run_dir.parents[2])
metadata = json.loads(g.canonical_json(art.metadata).decode("utf-8").replace(features_root, g.ROOT_PLACEHOLDER))
out.write_text(json.dumps({
    "manifest": g.strip_manifest(art.manifest), "task": g.strip_task(metadata),
    "manifest_sha": fp["manifest_stripped_sha256"], "task_sha": fp["task_stripped_sha256"],
    "groups": fp["groups"], "group_files_sha256": fp["group_files_sha256"],
    "config_hash": str(art.metadata.get("config_hash")),
}, sort_keys=True, default=str), encoding="utf-8")
print("ok", ref, fp["manifest_stripped_sha256"][:12])
