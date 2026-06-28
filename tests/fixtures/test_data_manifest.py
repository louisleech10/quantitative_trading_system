"""C4-3 DATA_MANIFEST 校驗與 mutation probe。"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tests.fixtures.data_manifest import (
    ManifestValidationError,
    load_manifest,
    validate_manifest,
)


@pytest.fixture
def manifest_doc() -> dict:
    """載入版本化 manifest 副本供測試使用。"""
    return load_manifest()


@pytest.mark.requires_kline
def test_manifest_valid_passes_when_kline_present(manifest_doc: dict) -> None:
    """健康路徑：manifest 與實際 kline 一致。"""
    validate_manifest(manifest=manifest_doc)


@pytest.mark.requires_kline
def test_mutation_wrong_sha256_fails(manifest_doc: dict) -> None:
    """mutation：改一筆 sha256 → 校驗 FAIL。"""
    mutated = copy.deepcopy(manifest_doc)
    mutated["entries"][0]["sha256"] = "0" * 64
    with pytest.raises(ManifestValidationError, match="sha256 mismatch"):
        validate_manifest(manifest=mutated)


@pytest.mark.requires_kline
def test_mutation_missing_symbol_tf_fails(manifest_doc: dict) -> None:
    """mutation：刪除一筆 symbol×TF → 校驗 FAIL。"""
    mutated = copy.deepcopy(manifest_doc)
    removed = mutated["entries"].pop(0)
    with pytest.raises(ManifestValidationError, match="missing from manifest"):
        validate_manifest(manifest=mutated)
    assert removed["symbol"] and removed["timeframe"]


@pytest.mark.requires_kline
def test_mutation_row_count_below_min_fails(manifest_doc: dict) -> None:
    """mutation：min_row_count 高於實際 → 校驗 FAIL。"""
    mutated = copy.deepcopy(manifest_doc)
    mutated["entries"][0]["min_row_count"] = 9_999_999
    symbol = mutated["entries"][0]["symbol"]
    timeframe = mutated["entries"][0]["timeframe"]
    with pytest.raises(ManifestValidationError, match="row_count"):
        validate_manifest(manifest=mutated)
    assert symbol and timeframe


def test_manifest_file_is_versioned() -> None:
    """manifest 檔案存在且含預期 30 筆條目。"""
    path = Path(__file__).resolve().parent / "DATA_MANIFEST.json"
    assert path.is_file()
    doc = load_manifest(path)
    assert doc["version"] == 1
    assert len(doc["entries"]) == 30
