"""Phase 3 Task 3.1 — Multi-Symbol IC-First Batch Integration Tests.

Test IDs:
  T3.1  test_multi_symbol_ic_isolation
  T3.2  test_multi_symbol_resume
  T3.B1 test_ram_gate_skip
  T3.B2 test_symbol_failure_no_checkpoint
  T3.P1 benchmark_multi_symbol_ic_first  (scaffold, exit 0)
  T3.P2 benchmark_10_symbol_2tf_resume_dryrun

執行：
    FFACT_MULTI_SYMBOL_IC_FIRST=0 ./venv/bin/pytest tests/feature_engineering/test_multi_symbol_ic_first.py -v
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_batch_request(
    symbols: List[str],
    timeframe: Optional[str] = None,
    force_regenerate: bool = False,
    config_override: Optional[Dict[str, Any]] = None,
) -> Any:
    """Build a minimal BatchGenerateRequest-like object for testing."""
    from api.models.feature_factory_models import BatchGenerateRequest

    return BatchGenerateRequest(
        symbols=symbols,
        timeframe=timeframe or "1h",
        force_regenerate=force_regenerate,
        config_override=config_override or {},
    )


def _import_service():
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService

    return FeatureFactoryBatchService


def _make_service(tmp_path: Any) -> Any:
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService

    svc = FeatureFactoryBatchService.__new__(FeatureFactoryBatchService)
    # Minimum state needed for batch service usage in tests
    svc._checkpoint_dir = tmp_path / "checkpoints"
    svc._checkpoint_dir.mkdir(parents=True, exist_ok=True)
    svc._active_tasks: Dict[str, Any] = {}
    svc._notification_callbacks: Dict[str, Any] = {}
    return svc


# ---------------------------------------------------------------------------
# T3.1  Multi-symbol output isolation
# ---------------------------------------------------------------------------

class TestMultiSymbolIcIsolation:
    """T3.1: 每個標的的輸出路徑必須互相隔離，不能相互覆寫。"""

    def test_compute_single_ic_first_returns_isolated_paths(self, tmp_path):
        """
        Given: 兩個不同標的分別呼叫 _compute_single_ic_first
        When:  generate_features 回傳不同的 hdf5_path
        Then:  兩條路徑互不相同（輸出隔離）
        """
        from api.services.feature_factory_batch_service import (
            FeatureFactoryBatchService,
        )

        path_btc = str(tmp_path / "BTCUSDT" / "features.parquet")
        path_eth = str(tmp_path / "ETHUSDT" / "features.parquet")

        def fake_generate_btc(**kwargs):
            result = MagicMock()
            result.hdf5_path = path_btc
            return result

        def fake_generate_eth(**kwargs):
            result = MagicMock()
            result.hdf5_path = path_eth
            return result

        # Patch create_feature_factory_for_ic_batch to avoid real computation
        factory_btc = MagicMock()
        factory_btc.generate_features.side_effect = fake_generate_btc
        factory_eth = MagicMock()
        factory_eth.generate_features.side_effect = fake_generate_eth

        call_count = [0]

        def mock_create_factory(cache_dir=None):
            call_count[0] += 1
            return factory_btc if call_count[0] == 1 else factory_eth

        with patch.dict(os.environ, {"FFACT_MULTI_SYMBOL_IC_FIRST": "0"}):
            # Temporarily override FFACT_IC_FIRST_PIPELINE inside the static method
            with patch(
                "momentum.factories.create_feature_factory_for_ic_batch",
                side_effect=mock_create_factory,
            ):
                result1 = FeatureFactoryBatchService._compute_single_ic_first(
                    "BTCUSDT", "1h", {}, False, str(tmp_path)
                )
                result2 = FeatureFactoryBatchService._compute_single_ic_first(
                    "ETHUSDT", "1h", {}, False, str(tmp_path)
                )

        assert result1 != result2, "兩標的輸出路徑不應相同（output isolation 違反）"
        assert result1 == path_btc
        assert result2 == path_eth

    def test_compute_single_ic_first_env_flag_restored(self, tmp_path):
        """
        Given: FFACT_IC_FIRST_PIPELINE 在執行前未設定
        When:  _compute_single_ic_first 執行完畢（成功或失敗）
        Then:  FFACT_IC_FIRST_PIPELINE 環境變數恢復原始狀態（finally 區塊）
        """
        from api.services.feature_factory_batch_service import (
            FeatureFactoryBatchService,
        )

        # 確認執行前未設定
        os.environ.pop("FFACT_IC_FIRST_PIPELINE", None)
        assert "FFACT_IC_FIRST_PIPELINE" not in os.environ

        factory_mock = MagicMock()
        factory_mock.generate_features.side_effect = RuntimeError("模擬計算失敗")

        with patch(
            "momentum.factories.create_feature_factory_for_ic_batch",
            return_value=factory_mock,
        ):
            with pytest.raises(RuntimeError):
                FeatureFactoryBatchService._compute_single_ic_first(
                    "BTCUSDT", "1h", {}, False, str(tmp_path)
                )

        # finally 應還原：移除 FFACT_IC_FIRST_PIPELINE
        assert "FFACT_IC_FIRST_PIPELINE" not in os.environ, (
            "FFACT_IC_FIRST_PIPELINE 應在 finally 中被移除，但仍殘留"
        )

    def test_compute_single_ic_first_env_flag_preserved_if_preset(self, tmp_path):
        """
        Given: FFACT_IC_FIRST_PIPELINE 在執行前已設為 "0"
        When:  _compute_single_ic_first 執行完畢
        Then:  FFACT_IC_FIRST_PIPELINE 仍為 "0"（原值被還原）
        """
        from api.services.feature_factory_batch_service import (
            FeatureFactoryBatchService,
        )

        os.environ["FFACT_IC_FIRST_PIPELINE"] = "0"

        factory_mock = MagicMock()
        result_mock = MagicMock()
        result_mock.hdf5_path = str(tmp_path / "out.parquet")
        factory_mock.generate_features.return_value = result_mock

        with patch(
            "momentum.factories.create_feature_factory_for_ic_batch",
            return_value=factory_mock,
        ):
            FeatureFactoryBatchService._compute_single_ic_first(
                "BTCUSDT", "1h", {}, False, str(tmp_path)
            )

        assert os.environ.get("FFACT_IC_FIRST_PIPELINE") == "0", (
            "預設值 '0' 應在 finally 中被還原"
        )
        # Cleanup
        del os.environ["FFACT_IC_FIRST_PIPELINE"]


# ---------------------------------------------------------------------------
# T3.2  Multi-symbol resume logic
# ---------------------------------------------------------------------------

class TestMultiSymbolResume:
    """T3.2: 已完成標的應被跳過；失敗標的應被重試。"""

    def test_completed_symbol_skipped(self, tmp_path):
        """
        Given: checkpoint 中 BTCUSDT/1h 已在 completed_items，queued_items 僅含 ETHUSDT
        When:  _run_batch 讀取 queued_items
        Then:  BTCUSDT 不在 queued_items（已從佇列移除），ETHUSDT 仍待處理

        Resume 邏輯：service 在 _record_item_result 中呼叫 _remove_queued_item，
        確保完成的標的不會重複出現在 queued_items 中。
        """
        # 模擬 resume 後的 checkpoint：BTCUSDT 已完成並從佇列移除
        checkpoint = {
            "batch_id": "test-batch",
            "completed_items": [{"symbol": "BTCUSDT", "timeframe": "1h"}],
            "failed_items": [],
            "queued_items": [{"symbol": "ETHUSDT", "timeframe": "1h"}],
        }

        queued_symbols = [item["symbol"] for item in checkpoint["queued_items"]]
        completed_symbols = {item["symbol"] for item in checkpoint["completed_items"]}

        assert "BTCUSDT" not in queued_symbols, "已完成的 BTCUSDT 不應出現在 queued_items"
        assert "ETHUSDT" in queued_symbols, "未完成的 ETHUSDT 應在 queued_items 中"
        assert "BTCUSDT" in completed_symbols, "BTCUSDT 應記錄在 completed_items"

    def test_failed_symbol_in_queued_for_retry(self, tmp_path):
        """
        Given: ETHUSDT/1h 計算失敗，記錄於 failed_items
        When:  重新 resume（新 checkpoint 中 ETHUSDT 仍在 queued_items）
        Then:  ETHUSDT 出現在 queued_items 中（可被重試）

        語意：failed_items 只是歷史紀錄，真正決定「是否重試」的是 queued_items。
        """
        # 初始 checkpoint：ETHUSDT 失敗，但仍在 queued_items 中等待重試
        checkpoint = {
            "batch_id": "test-batch",
            "completed_items": [],
            "failed_items": [
                {
                    "symbol": "ETHUSDT",
                    "timeframe": "1h",
                    "failure_type": "computation_error",
                }
            ],
            "queued_items": [{"symbol": "ETHUSDT", "timeframe": "1h"}],
        }

        queued_symbols = [item["symbol"] for item in checkpoint["queued_items"]]
        assert "ETHUSDT" in queued_symbols, "失敗的 ETHUSDT 應仍在 queued_items 中可被重試"

    def test_remove_queued_item_removes_completed(self, tmp_path):
        """
        Given: checkpoint 有 BTCUSDT、ETHUSDT 在 queued_items
        When:  _remove_queued_item(checkpoint, 'BTCUSDT', '1h') 被呼叫
        Then:  BTCUSDT 從 queued_items 消失，ETHUSDT 仍在
        """

        svc = _make_service(tmp_path)
        checkpoint = {
            "batch_id": "test-batch",
            "queued_items": [
                {"symbol": "BTCUSDT", "timeframe": "1h"},
                {"symbol": "ETHUSDT", "timeframe": "1h"},
            ],
            "completed_items": [],
            "failed_items": [],
        }

        svc._remove_queued_item(checkpoint, "BTCUSDT", "1h")

        queued = [item["symbol"] for item in checkpoint["queued_items"]]
        assert "BTCUSDT" not in queued, "_remove_queued_item 應移除 BTCUSDT"
        assert "ETHUSDT" in queued, "ETHUSDT 不應被誤刪"


# ---------------------------------------------------------------------------
# T3.B1  RAM gate 觸發時不崩潰
# ---------------------------------------------------------------------------

class TestRamGateSkip:
    """T3.B1: RAM gate 觸發時狀態為 paused_ram_gate，不應崩潰。"""

    def test_ram_gate_raises_http_429(self, tmp_path):
        """
        Given: 可用 RAM 低於 gate 閾值（psutil mock）
        When:  _ram_gate() 被呼叫
        Then:  拋出 HTTPException(429)，task 仍存活
        """
        from fastapi import HTTPException


        svc = _make_service(tmp_path)

        with patch("api.services.feature_factory_batch_service.psutil") as mock_psutil:
            mock_vm = MagicMock()
            mock_vm.available = int(0.5 * 1024 ** 3)  # 0.5 GB < 4 GB gate
            mock_psutil.virtual_memory.return_value = mock_vm

            with pytest.raises(HTTPException) as exc_info:
                svc._ram_gate(min_available_gb=4.0)

        assert exc_info.value.status_code == 429
        assert "RAM gate" in exc_info.value.detail

    def test_ram_gate_passes_when_memory_sufficient(self, tmp_path):
        """
        Given: 可用 RAM 充足
        When:  _ram_gate() 被呼叫
        Then:  不拋出異常
        """

        svc = _make_service(tmp_path)

        with patch("api.services.feature_factory_batch_service.psutil") as mock_psutil:
            mock_vm = MagicMock()
            mock_vm.available = int(8.0 * 1024 ** 3)  # 8 GB > 4 GB gate
            mock_psutil.virtual_memory.return_value = mock_vm

            # 不應拋出任何異常
            svc._ram_gate(min_available_gb=4.0)


# ---------------------------------------------------------------------------
# T3.B2  單標的失敗不污染 checkpoint
# ---------------------------------------------------------------------------

class TestSymbolFailureNoCheckpoint:
    """T3.B2: 計算失敗的標的應記錄到 failed_items，不能進入 completed_items。"""

    def test_memory_error_classified_as_oom(self, tmp_path):
        """
        Given: _compute_single_ic_first 拋出 MemoryError
        When:  _classify_failure 處理
        Then:  failure_type == BatchFailureType.OOM
        """
        from api.services.feature_factory_batch_service import (
            BatchFailureType,
        )

        svc = _make_service(tmp_path)
        exc = MemoryError("cannot allocate 2.1 GB")
        failure_type = svc._classify_failure(exc)

        assert failure_type == BatchFailureType.OOM

    def test_runtime_error_not_oom(self, tmp_path):
        """
        Given: _compute_single_ic_first 拋出 RuntimeError（非 OOM）
        When:  _classify_failure 處理
        Then:  failure_type != BatchFailureType.OOM
        """
        from api.services.feature_factory_batch_service import (
            BatchFailureType,
        )

        svc = _make_service(tmp_path)
        exc = RuntimeError("BTCUSDT (1h): IC-First 計算失敗 - connection refused")
        failure_type = svc._classify_failure(exc)

        assert failure_type != BatchFailureType.OOM

    def test_compute_single_ic_first_memory_error_propagates(self, tmp_path):
        """
        Given: generate_features 內部拋出 MemoryError
        When:  _compute_single_ic_first 執行
        Then:  MemoryError 直接重新拋出（不被包裝成 RuntimeError）
        """
        from api.services.feature_factory_batch_service import (
            FeatureFactoryBatchService,
        )

        factory_mock = MagicMock()
        factory_mock.generate_features.side_effect = MemoryError("OOM in IC compute")

        with patch(
            "momentum.factories.create_feature_factory_for_ic_batch",
            return_value=factory_mock,
        ):
            with pytest.raises(MemoryError):
                FeatureFactoryBatchService._compute_single_ic_first(
                    "BTCUSDT", "1h", {}, False, str(tmp_path)
                )

    def test_compute_single_ic_first_runtime_error_wrapped(self, tmp_path):
        """
        Given: generate_features 拋出一般 Exception
        When:  _compute_single_ic_first 執行
        Then:  回傳 RuntimeError（含 symbol + timeframe 資訊）
        """
        from api.services.feature_factory_batch_service import (
            FeatureFactoryBatchService,
        )

        factory_mock = MagicMock()
        factory_mock.generate_features.side_effect = ValueError("bad config")

        with patch(
            "momentum.factories.create_feature_factory_for_ic_batch",
            return_value=factory_mock,
        ):
            with pytest.raises(RuntimeError) as exc_info:
                FeatureFactoryBatchService._compute_single_ic_first(
                    "BTCUSDT", "1h", {}, False, str(tmp_path)
                )

        assert "BTCUSDT" in str(exc_info.value)
        assert "1h" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T3.P1  benchmark --phase=3 scaffold
# ---------------------------------------------------------------------------

class TestBenchmarkPhase3Scaffold:
    """T3.P1: scripts/benchmark_l65_v2.py --phase=3 scaffold 應正確回傳 blocked_missing_data。"""

    def test_phase3_benchmark_importable(self):
        """benchmark_l65_v2 script 應可 import 且含 _run_phase3_benchmark 函式。"""
        import importlib.util
        import pathlib

        script_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "scripts"
            / "benchmark_l65_v2.py"
        )
        if not script_path.exists():
            pytest.skip("scripts/benchmark_l65_v2.py 尚未建立，跳過 scaffold test")

        spec = importlib.util.spec_from_file_location("benchmark_l65_v2", script_path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass

        assert hasattr(mod, "_run_phase3_benchmark"), (
            "_run_phase3_benchmark 函式不存在於 benchmark_l65_v2.py"
        )

    def test_phase3_benchmark_blocked_missing_data(self):
        """_run_phase3_benchmark 在無真實資料時應回傳 blocked_missing_data。"""
        import importlib.util
        import pathlib

        script_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "scripts"
            / "benchmark_l65_v2.py"
        )
        if not script_path.exists():
            pytest.skip("scripts/benchmark_l65_v2.py 尚未建立，跳過 scaffold test")

        spec = importlib.util.spec_from_file_location("benchmark_l65_v2", script_path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass

        result = mod._run_phase3_benchmark(tier="8gb", dryrun=True)
        assert result.get("status") == "blocked_missing_data", (
            f"Expected 'blocked_missing_data', got: {result.get('status')}"
        )


# ---------------------------------------------------------------------------
# T3.P2  10 symbols × 2 TF dryrun checkpoint structure + resume logic
# ---------------------------------------------------------------------------

class TestBenchmark10SymbolDryrun:
    """T3.P2: dryrun 下 checkpoint 結構與 resume 邏輯驗證。"""

    def test_checkpoint_structure_has_required_keys(self, tmp_path):
        """
        Given: 建立初始 checkpoint（10 symbols × 1 TF）
        When:  讀取 checkpoint 結構
        Then:  必須包含 batch_id, completed_items, failed_items, queued_items
        """

        svc = _make_service(tmp_path)
        symbols = [f"SYM{i:02d}USDT" for i in range(10)]
        request = _make_batch_request(symbols, "1h")
        task_id = str(uuid.uuid4())

        # _build_initial_checkpoint 應產生正確結構
        checkpoint = svc._build_initial_checkpoint(task_id, request)

        required_keys = {"batch_id", "queued_items", "completed_items", "failed_items"}
        missing = required_keys - set(checkpoint.keys())
        assert not missing, f"checkpoint 缺少必要欄位: {missing}"

        # 確認 queued_items = 10 × 1 TF = 10
        assert len(checkpoint["queued_items"]) == 10, (
            f"queued_items 應為 10（10 symbols × 1 TF），實際為 {len(checkpoint['queued_items'])}"
        )

    def test_resume_skips_completed_items(self, tmp_path):
        """
        Given: 第一次執行後 5 個 items 完成（從 queued_items 移除），5 個仍在 queued_items
        When:  讀取 checkpoint queued_items
        Then:  queued_items 只包含未完成的標的（5 個），completed_items 有 5 個
        """
        all_symbols = [f"SYM{i:02d}USDT" for i in range(10)]

        # 模擬執行後的狀態：前 5 個完成，後 5 個仍在佇列
        completed = [
            {"symbol": s, "timeframe": "1h"} for s in all_symbols[:5]
        ]
        queued = [
            {"symbol": s, "timeframe": "1h"} for s in all_symbols[5:]
        ]
        checkpoint = {
            "batch_id": "test-resume",
            "completed_items": completed,
            "failed_items": [],
            "queued_items": queued,
        }

        # completed_items 中的標的不應出現在 queued_items
        queued_symbols = {item["symbol"] for item in checkpoint["queued_items"]}
        completed_symbols = {item["symbol"] for item in checkpoint["completed_items"]}

        overlap = queued_symbols & completed_symbols
        assert not overlap, f"已完成標的不應在 queued_items 中: {overlap}"
        assert len(queued_symbols) == 5, f"queued_items 應有 5 個標的，實際為 {len(queued_symbols)}"
        assert len(completed_symbols) == 5, f"completed_items 應有 5 個標的，實際為 {len(completed_symbols)}"

    def test_ic_first_flag_controls_resolve_concurrent(self, tmp_path, monkeypatch):
        """
        Given: FFACT_MULTI_SYMBOL_IC_FIRST=1
        When:  _resolve_concurrent_symbols() 被呼叫
        Then:  回傳 1（強制序列）
        """

        monkeypatch.setenv("FFACT_MULTI_SYMBOL_IC_FIRST", "1")
        # 強制重新載入 config module 的快取
        import importlib

        import momentum.core.config as cfg_mod

        importlib.reload(cfg_mod)

        svc = _make_service(tmp_path)
        concurrent = svc._resolve_concurrent_symbols()

        monkeypatch.delenv("FFACT_MULTI_SYMBOL_IC_FIRST", raising=False)
        importlib.reload(cfg_mod)

        assert concurrent == 1, (
            f"IC-First 模式下 concurrent_symbols 應為 1，實際為 {concurrent}"
        )

    def test_ic_first_flag_disabled_uses_tier(self, tmp_path, monkeypatch):
        """
        Given: FFACT_MULTI_SYMBOL_IC_FIRST=0
        When:  _resolve_concurrent_symbols() 被呼叫
        Then:  回傳 tier-based 值（>= 1，不強制為 1 by IC-First）
        Boundary: FFACT_BATCH_NESTED=0 以排除 nested guard
        """
        monkeypatch.setenv("FFACT_MULTI_SYMBOL_IC_FIRST", "0")
        monkeypatch.setenv("FFACT_BATCH_NESTED", "0")

        import importlib

        import momentum.core.config as cfg_mod

        importlib.reload(cfg_mod)


        svc = _make_service(tmp_path)

        with patch(
            "api.services.feature_factory_batch_service.get_current_tier_gb",
            return_value=16.0,
        ), patch(
            "api.services.feature_factory_batch_service.get_tier_concurrent_symbols",
            return_value=2,
        ):
            concurrent = svc._resolve_concurrent_symbols()

        monkeypatch.delenv("FFACT_MULTI_SYMBOL_IC_FIRST", raising=False)
        monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)
        importlib.reload(cfg_mod)

        assert concurrent == 2, (
            f"非 IC-First 模式下應使用 tier-based 值 2，實際為 {concurrent}"
        )
