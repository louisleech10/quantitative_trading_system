"""同一真實 IC run 在 redirect A/B 與 sacrificial OFF 的 SHA-256 守恆。

B6：移除 B4 暫 xfail。20k×50 split-OFF 全量長跑不可作 CI gate；
改為 la0 凍結輸入（~2k×15）×2 redirect 上下文，assert 數值 hash 守恆 + data_cache 無寫入。
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.ic_persist_redirect import RedirectPatchSet, digest_data_cache
from tests.golden.la0.build_after_and_attribution import collect_after_from_frozen
from tests.golden.la0 import gen_baseline as gb


PATH_OR_MTIME_KEYS = {
    "filtered_features_path",
    "report_paths",
    "artifact_mtime",
    "generated_at",
}

LA0_BEFORE_BTC = Path("tests/golden/la0/BTCUSDT_1h_baseline.json")
LA0_AFTER_BTC = Path("tests/golden/la0/BTCUSDT_1h_baseline_after.json")


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


def _metric_core(baseline: dict[str, Any]) -> dict[str, Any]:
    """取不受 path/mtime 影響的核心數值區塊。"""
    return {
        "rolling_ic": baseline.get("rolling_ic"),
        "icir": baseline.get("icir"),
        "monotonicity": baseline.get("monotonicity"),
        "turnover": baseline.get("turnover"),
        "stage1": {
            "winsorize_value_sha256": (baseline.get("stage1") or {}).get(
                "winsorize_value_sha256"
            ),
            "nan_mask_sha256": (baseline.get("stage1") or {}).get("nan_mask_sha256"),
        },
        "control": baseline.get("control"),
        "passed_features": {
            "sha256": (baseline.get("passed_features") or {}).get("sha256"),
            "count": (baseline.get("passed_features") or {}).get("count"),
        },
        "counts": baseline.get("counts"),
        "pit_stats_version": baseline.get("pit_stats_version"),
    }


def test_golden_redirect_on_off_sha256(
    redirect_patch_set: RedirectPatchSet,
    tmp_path: Path,
    monkeypatch,
) -> None:
    """B6：la0 凍結輸入在 redirect A/B 與 chdir worktree 下數值 hash 守恆。"""
    assert LA0_BEFORE_BTC.is_file()
    assert LA0_AFTER_BTC.is_file()
    before = json.loads(LA0_BEFORE_BTC.read_text(encoding="utf-8"))
    golden_after = json.loads(LA0_AFTER_BTC.read_text(encoding="utf-8"))
    golden_hash = _hash(_metric_core(golden_after))

    hashes: list[str] = []
    for label in ("a", "b"):
        ctx = redirect_patch_set.activate(
            tmp_path / f"tmp_{label}", owner=f"golden-{label}"
        )
        try:
            live, _ = collect_after_from_frozen(before)
            hashes.append(_hash(_metric_core(live)))
            assert not ctx.spy.violations
        finally:
            redirect_patch_set.deactivate(ctx)

    before_digest = digest_data_cache()
    work = tmp_path / "work"
    repo_config = Path(__file__).resolve().parents[3] / "config"
    for bucket in ("features", "reports", "models"):
        (work / "data_cache" / bucket).mkdir(parents=True, exist_ok=True)
    (work / "config").symlink_to(repo_config, target_is_directory=True)
    repo_feature_klines = repo_config.parent / "data_cache" / "feature_klines"
    (work / "data_cache" / "feature_klines").symlink_to(
        repo_feature_klines, target_is_directory=True
    )
    # la0 輸入為相對路徑；chdir 後仍需能讀到 repo 內 golden inputs
    monkeypatch.chdir(work)
    # collect_after 用 REPO_ROOT 絕對路徑，不受 chdir 影響；再跑一次確認
    live3, _ = collect_after_from_frozen(before)
    hashes.append(_hash(_metric_core(live3)))
    after_digest = digest_data_cache()

    assert before_digest == after_digest
    assert hashes[0] == hashes[1] == hashes[2] == golden_hash
    # side-effect isolation 仍生效（不寫 data_cache/reports|features）
    _ = gb  # module import keeps gen_baseline sidefx path available
    print(f"ab_hash={hashes[0]}")
