"""FeatureReader V2 artifact 公開委派 API 契約。"""

from __future__ import annotations

import pytest

from momentum.FeatureEngineering.feature_reader import FeatureReader


def test_public_artifact_matches_private_delegate() -> None:
    """公開 API 必須保留 private helper 的回傳語義。"""

    manifest = {
        "artifacts": {
            "raw": {
                "complete": True,
                "groups": {"group_a": {"columns": ["feature_a"]}},
            }
        }
    }

    assert FeatureReader.get_v2_artifact(manifest, "raw") == FeatureReader._get_v2_artifact(
        manifest,
        "raw",
    )


def test_public_artifact_matches_private_missing_kind_error() -> None:
    """缺少 kind 時公開與 private API 必須拋出相同錯誤。"""

    manifest = {"artifacts": {}}

    with pytest.raises(FileNotFoundError) as public_error:
        FeatureReader.get_v2_artifact(manifest, "raw")
    with pytest.raises(FileNotFoundError) as private_error:
        FeatureReader._get_v2_artifact(manifest, "raw")

    assert public_error.value.args == private_error.value.args
