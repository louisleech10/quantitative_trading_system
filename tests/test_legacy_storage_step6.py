"""Step 6: Legacy 儲存清理邊界測試（E18, E19）。"""

from __future__ import annotations

import inspect

import pytest

from momentum.DataExtraction.data_loader_momentum import DataLoader
from momentum.DataExtraction.kline_storage import KlineStorageManager


def test_data_loader_save_cache_uses_kline_storage_manager() -> None:
    """E18: 確認 DataLoader 已不再主動寫入 legacy *.h5。"""
    source = inspect.getsource(DataLoader._save_to_cache)
    assert "write_klines" in source
    assert "to_hdf" not in source


def test_import_from_legacy_cache_missing_file_returns_false_and_warns(tmp_path, monkeypatch) -> None:
    """E19: legacy 檔案不存在時，lazy import 應安全返回 False。"""
    legacy_dir = tmp_path / "legacy"
    cache_dir = tmp_path / "cache"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("LEGACY_KLINE_CACHE_DIR", str(legacy_dir))
    manager = KlineStorageManager(cache_dir=str(cache_dir))

    with pytest.deprecated_call(match="deprecated"):
        imported = manager._import_from_legacy_cache("FAKEUSDT", "12h")

    assert imported is False
