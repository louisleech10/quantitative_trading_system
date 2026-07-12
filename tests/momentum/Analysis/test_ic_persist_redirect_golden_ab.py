"""同一真實 IC run 在 redirect A/B 與 sacrificial OFF 的 SHA-256 守恆。"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from tests.fixtures.ic_persist_redirect import RedirectPatchSet, digest_data_cache
from tests.momentum.Analysis import test_ic_1a_cut1_golden as golden


PATH_OR_MTIME_KEYS = {
    "filtered_features_path",
    "report_paths",
    "artifact_mtime",
    "generated_at",
}


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize(item)
            for key, item in sorted(value.items())
            if key not in PATH_OR_MTIME_KEYS
        }
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def _hash(result: dict[str, Any]) -> str:
    payload = json.dumps(normalize(copy.deepcopy(result)), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_golden_redirect_on_off_sha256(
    redirect_patch_set: RedirectPatchSet,
    tmp_path: Path,
    monkeypatch,
) -> None:
    features_path = golden.FEATURES_PATH.resolve()
    meta_path = golden.META_PATH.resolve()
    assert features_path.is_file(), features_path
    assert meta_path.is_file(), meta_path

    hashes: list[str] = []
    for label in ("a", "b"):
        ctx = redirect_patch_set.activate(tmp_path / f"tmp_{label}", owner=f"golden-{label}")
        try:
            hashes.append(_hash(asyncio.run(golden._run_baseline(split_on=False))))
            assert not ctx.spy.violations
        finally:
            redirect_patch_set.deactivate(ctx)

    before = digest_data_cache()
    work = tmp_path / "work"
    repo_config = Path(__file__).resolve().parents[3] / "config"
    for bucket in ("features", "reports", "models"):
        (work / "data_cache" / bucket).mkdir(parents=True, exist_ok=True)
    (work / "config").symlink_to(repo_config, target_is_directory=True)
    repo_feature_klines = repo_config.parent / "data_cache" / "feature_klines"
    (work / "data_cache" / "feature_klines").symlink_to(
        repo_feature_klines, target_is_directory=True
    )
    monkeypatch.chdir(work)
    monkeypatch.setattr(golden, "FEATURES_PATH", features_path)
    monkeypatch.setattr(golden, "META_PATH", meta_path)
    hashes.append(_hash(asyncio.run(golden._run_baseline(split_on=False))))
    after = digest_data_cache()

    assert before == after
    assert hashes[0] == hashes[1] == hashes[2]
    print(f"ab_hash={hashes[0]}")
