from types import SimpleNamespace

import pytest

from momentum.FeatureEngineering.utils import hardware_utils


class _PsutilStub:
    def __init__(self, total_bytes: int) -> None:
        self._total_bytes = total_bytes

    def virtual_memory(self) -> SimpleNamespace:
        return SimpleNamespace(total=self._total_bytes)


def test_get_memory_tier_auto_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 get_memory_tier 自動偵測：8GB 記憶體應回傳 8gb。"""
    monkeypatch.delenv("FFACT_MEMORY_TIER", raising=False)
    monkeypatch.setattr(hardware_utils, "_psutil", _PsutilStub(8 * 1024 ** 3))

    assert hardware_utils.get_memory_tier() == "8gb"


def test_get_memory_tier_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 FFACT_MEMORY_TIER 環境變數覆蓋：設定 16gb 應直接回傳。"""
    monkeypatch.setenv("FFACT_MEMORY_TIER", "16gb")
    monkeypatch.setattr(hardware_utils, "_psutil", _PsutilStub(32 * 1024 ** 3))

    assert hardware_utils.get_memory_tier() == "16gb"


def test_get_tier_config_returns_valid_dict() -> None:
    """測試 get_tier_config：所有 tier 都應回傳完整設定鍵。"""
    expected_keys = {
        "l65_workers", "cgsa_memory_buffer", "l7_workers", "chunk_bars",
        "multi_tf_max_workers", "layer3_chunk_size", "l3_persist_mode",
        "l3_streaming_buffer_cols", "l65_split_threshold", "l2_category_workers",
        "cgsa_shard_bytes", "concurrent_symbols", "l7_zstd_level",
        "cgsa_stats_sync_cap", "cgsa_stats_q_sample", "cgsa_stats_warmup_workers",
    }

    for tier in ("8gb", "16gb", "24gb", "32gb"):
        assert set(hardware_utils.get_tier_config(tier).keys()) == expected_keys


def test_get_tier_config_unknown_tier_fallback() -> None:
    """測試未知 tier fallback：應回退到 8GB 保守設定。"""
    config = hardware_utils.get_tier_config("64gb")

    assert config == hardware_utils.get_tier_config("8gb")
    assert config["l65_workers"] == 2


def test_get_memory_tier_env_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 FFACT_MEMORY_TIER=auto：應走 psutil 偵測路徑。"""
    monkeypatch.setenv("FFACT_MEMORY_TIER", "auto")
    monkeypatch.setattr(hardware_utils, "_psutil", _PsutilStub(24 * 1024 ** 3))

    assert hardware_utils.get_memory_tier() == "24gb"


def test_get_memory_tier_env_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 FFACT_MEMORY_TIER 空字串：應走 psutil 偵測路徑。"""
    monkeypatch.setenv("FFACT_MEMORY_TIER", "")
    monkeypatch.setattr(hardware_utils, "_psutil", _PsutilStub(32 * 1024 ** 3))

    assert hardware_utils.get_memory_tier() == "32gb"


def test_get_memory_tier_psutil_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """測試 psutil 不可用：應回退到最保守的 8gb。"""
    monkeypatch.delenv("FFACT_MEMORY_TIER", raising=False)
    monkeypatch.setattr(hardware_utils, "_psutil", None)

    assert hardware_utils.get_memory_tier() == "8gb"
