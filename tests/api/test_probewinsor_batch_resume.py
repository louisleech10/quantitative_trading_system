"""PROBEWINSOR Task 1.4（docs/PROBEWINSOR_SPEC.md §V 邊界 09）：批次續跑以目前碼重算完成項之身分，不符即重排。

完成項之 run hash 取自其輸出路徑（`_resolve_completed_run_hash`）；身分＝`FeatureFactory.config_identity`（目前碼之
config_hash）。真實 kline（身分含 `_kline_last_ts`）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from api.models.feature_factory_models import BatchGenerateRequest
from tests.feature_engineering import probewinsor_helpers as ph

pytestmark = pytest.mark.requires_kline

_SPEC = ph.contract()


def _item(root: Path, symbol: str, timeframe: str, run_hash: str, *, manifest: bool = True) -> Dict[str, Any]:
    run_dir = root / "features" / symbol / timeframe / run_hash
    run_dir.mkdir(parents=True, exist_ok=True)
    if manifest:
        (run_dir / "feature_manifest.json").write_text('{"run_status": "complete"}', encoding="utf-8")
    return {"symbol": symbol, "timeframe": timeframe, "output_paths": [str(run_dir / "raw" / "part-0.parquet")]}


def _checkpoint(service: Any, items: List[Dict[str, Any]], config_override: Dict[str, Any],
                timeframe: str = "1h", start: str = "2026-01-01", end: str = "2026-01-31") -> Dict[str, Any]:
    request = BatchGenerateRequest(symbols=sorted({i["symbol"] for i in items} | {"ETHUSDT"}), timeframe=timeframe,
                                   start_date=start, end_date=end, config_override=config_override)
    checkpoint = service._build_initial_checkpoint("batch-probewinsor", request)
    checkpoint["completed_items"] = list(items)
    checkpoint["queued_items"] = [{"symbol": "ETHUSDT", "timeframe": timeframe}]
    return checkpoint


def _partition(service: Any, checkpoint: Dict[str, Any], identity: Any) -> Tuple[List[str], List[str]]:
    retained, requeued = service._partition_completed_items(checkpoint, identity)
    return [i["symbol"] for i in retained], [i["symbol"] for i in requeued]


def test_boundary_09a_identity_match_retained(batch_service_factory: Any, tmp_path: Path) -> None:
    """身分相符且 manifest 在 ⇒ 保留（不重算）。"""
    service = batch_service_factory(tmp_path / "ckpt")
    checkpoint = _checkpoint(service, [_item(tmp_path, "BTCUSDT", "1h", "aaaa1111")], {})
    assert _partition(service, checkpoint, lambda symbol, timeframe: "aaaa1111") == (["BTCUSDT"], [])


def test_boundary_09b_identity_mismatch_requeued(batch_service_factory: Any, tmp_path: Path) -> None:
    """身分不符（碼或資料已變）⇒ 重排，即使 manifest 仍在。"""
    service = batch_service_factory(tmp_path / "ckpt")
    checkpoint = _checkpoint(service, [_item(tmp_path, "BTCUSDT", "1h", "aaaa1111")], {})
    assert _partition(service, checkpoint, lambda symbol, timeframe: "bbbb2222") == ([], ["BTCUSDT"])


def test_boundary_09c_manifest_missing_requeued(batch_service_factory: Any, tmp_path: Path) -> None:
    """manifest 不在 ⇒ 重排（改前行為不變）。"""
    service = batch_service_factory(tmp_path / "ckpt")
    checkpoint = _checkpoint(service, [_item(tmp_path, "BTCUSDT", "1h", "aaaa1111", manifest=False)], {})
    assert _partition(service, checkpoint, lambda symbol, timeframe: "aaaa1111") == ([], ["BTCUSDT"])


def test_boundary_09d_legacy_unresolvable_retained(batch_service_factory: Any, tmp_path: Path) -> None:
    """輸出路徑無法解析 run hash 之舊項 ⇒ 保留（改前行為不變；身分函式不被呼叫）。"""
    service = batch_service_factory(tmp_path / "ckpt")
    legacy = {"symbol": "BTCUSDT", "timeframe": "1h", "output_paths": ["/tmp/BTCUSDT_1h.h5"]}
    checkpoint = _checkpoint(service, [legacy], {})

    def _never(symbol: str, timeframe: str) -> str:
        raise AssertionError("legacy 項不得重算身分")

    assert _partition(service, checkpoint, _never) == (["BTCUSDT"], [])


def test_boundary_09e_identity_error_requeued(batch_service_factory: Any, tmp_path: Path) -> None:
    """身分重算拋例外 ⇒ 重排（不得以無法確認之舊結果充當完成）。"""
    service = batch_service_factory(tmp_path / "ckpt")
    checkpoint = _checkpoint(service, [_item(tmp_path, "BTCUSDT", "1h", "aaaa1111")], {})

    def _boom(symbol: str, timeframe: str) -> str:
        raise ValueError("identity failure")

    assert _partition(service, checkpoint, _boom) == ([], ["BTCUSDT"])


def test_boundary_09f_resume_identity_is_factory_identity(batch_service_factory: Any, tmp_path: Path) -> None:
    """`_resume_identity` 以 checkpoint 之請求（設定、起訖日）建目前碼之身分：等於 `FeatureFactory.config_identity`
    與 `_compute_config_hash`；對「總開關關＋縮尾開」格不等於錨點凍結之 hash（改前完成項於續跑時被重排）。"""
    from momentum.factories import create_feature_factory

    cell = ph.cell_by_id("e1h.off.w1")
    payload = ph.cell_payload(cell)
    service = batch_service_factory(tmp_path / "ckpt")
    checkpoint = _checkpoint(service, [], payload)
    identity = service._resume_identity(checkpoint)
    factory = create_feature_factory(cache_dir=str(ph.REPO / _SPEC["kline_dir"]), validate_continuity=False)
    expected = factory.config_identity("BTCUSDT", "1h", payload, "2026-01-01", "2026-01-31")
    direct = factory._compute_config_hash(factory._resolve_config(payload), "BTCUSDT", "1h",
                                          start_date="2026-01-01", end_date="2026-01-31")
    assert identity("BTCUSDT", "1h") == expected == direct
    assert expected != ph.baseline()["cells"]["e1h.off.w1"]["config_hash"]
    assert factory.config_identity("BTCUSDT", "1h", ph.cell_payload(ph.cell_by_id("e1h.on.w1")),
                                   "2026-01-01", "2026-01-31") == ph.baseline()["cells"]["e1h.on.w1"]["config_hash"]


# 公開入口對每個可解析之完成項各呼叫一次 `FeatureFactory.config_identity`（依完成項順序；參數＝該項與請求之設定、起訖日）
_EXPECTED_IDENTITY_ARGS = [
    {"symbol": "BTCUSDT", "timeframe": "1h", "config_override": {}, "start_date": "2026-01-01", "end_date": "2026-01-31"},
    {"symbol": "SOLUSDT", "timeframe": "1h", "config_override": {}, "start_date": "2026-01-01", "end_date": "2026-01-31"},
]


def _identity_args(identity_calls: List[Any]) -> List[Dict[str, Any]]:
    """監聽到之 `config_identity` 呼叫 → 依簽章綁定後之參數字典（不論位置或關鍵字傳入）。"""
    import inspect

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    signature = inspect.signature(FeatureFactory.config_identity)
    out = []
    for args, kwargs in identity_calls:
        bound = signature.bind(None, *args, **kwargs)
        bound.apply_defaults()
        out.append({k: v for k, v in bound.arguments.items() if k != "self"})
    return out


async def _public_resume(service: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                         identity_calls: Any = None,
                         substitute: Any = None) -> Tuple[Dict[str, Any], List[str]]:
    """經公開 `resume_batch`（**不替換**身分函式）：完成項 A 之 run hash＝目前碼之真實身分（同 `_resume_identity` 之
    kline 目錄與請求）、B 之 run hash 為舊值；待排 ETHUSDT；生成函式以替身記錄被重算者。給 `substitute`（symbol →
    身分）時監聽仍委派原方法，但改回傳替代身分（驗續跑之決策取自公開方法之回傳值）。"""
    import asyncio

    from api.core.config import settings
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from tests.api.batch_wave_helpers import use_thread_wave

    calls: List[str] = []

    def _compute(symbol: str, timeframe: str, *_args: Any, **_kw: Any) -> str:
        calls.append(symbol)
        return f"/tmp/{symbol}_{timeframe}.out"

    use_thread_wave(monkeypatch)
    monkeypatch.setattr(FeatureFactoryBatchService, "_compute_single", staticmethod(_compute))
    real = create_feature_factory(cache_dir=str(settings.data_cache_path / "feature_klines")).config_identity(
        "BTCUSDT", "1h", {}, "2026-01-01", "2026-01-31")
    items = [_item(tmp_path, "BTCUSDT", "1h", real), _item(tmp_path, "SOLUSDT", "1h", "cccc3333")]
    checkpoint = _checkpoint(service, items, {})
    service._safe_persist_checkpoint(checkpoint)
    if identity_calls is not None:  # 監聽（不替換）公開身分方法：記錄參數後委派原方法
        import functools

        original = FeatureFactory.config_identity

        @functools.wraps(original)  # 保留原簽章（`_identity_args` 依簽章綁定參數）
        def _spy(self: Any, *args: Any, **kwargs: Any) -> str:
            identity_calls.append((args, kwargs))
            result = original(self, *args, **kwargs)
            if substitute is None:
                return result
            return substitute[_identity_args([(args, kwargs)])[0]["symbol"]]

        monkeypatch.setattr(FeatureFactory, "config_identity", _spy)
    response = await service.resume_batch("batch-probewinsor")
    for _ in range(250):  # 同 test_feature_factory_batch_resume._wait_until_done 之終止狀態（上限 5 秒）
        status = service.get_status("batch-probewinsor")
        if status and status["status"] in {"completed", "partial", "failed", "paused_ram_gate"}:
            break
        await asyncio.sleep(0.02)
    else:
        raise TimeoutError("batch-probewinsor 未於 5 秒內結束")
    return response, sorted(calls)


@pytest.mark.asyncio
async def test_boundary_09g_public_resume_requeues_identity_mismatch(
        monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any, tmp_path: Path) -> None:
    """經公開 `resume_batch`：身分相符之完成項跳過（skipped 1）、不符者與原待排者重算（queued 2）。"""
    service = batch_service_factory(tmp_path / "ckpt")
    identity_calls: List[Any] = []
    response, calls = await _public_resume(service, tmp_path, monkeypatch, identity_calls)
    assert response["skipped_items"] == 1
    assert response["queued_items"] == 2
    assert calls == ["ETHUSDT", "SOLUSDT"]
    assert _identity_args(identity_calls) == _EXPECTED_IDENTITY_ARGS


@pytest.mark.asyncio
async def test_boundary_09h_public_resume_decides_on_public_return(
        monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any, tmp_path: Path) -> None:
    """經公開 `resume_batch`：公開身分方法之回傳值被替換（BTCUSDT 改為不符、SOLUSDT 改為等於其完成項之 run hash）⇒
    跳過與重算隨替代值反轉（決策取自公開方法之回傳值，非另行計算）。"""
    service = batch_service_factory(tmp_path / "ckpt")
    identity_calls: List[Any] = []
    response, calls = await _public_resume(service, tmp_path, monkeypatch, identity_calls,
                                           substitute=_SUBSTITUTE_IDENTITY)
    assert response["skipped_items"] == 1
    assert response["queued_items"] == 2
    assert calls == ["BTCUSDT", "ETHUSDT"]
    assert _identity_args(identity_calls) == _EXPECTED_IDENTITY_ARGS


# 09h 之替代身分：BTCUSDT（完成項為真實身分）改為不符、SOLUSDT（完成項為舊值 cccc3333）改為相符
_SUBSTITUTE_IDENTITY = {"BTCUSDT": "zzzz9999", "SOLUSDT": "cccc3333"}


@pytest.mark.asyncio
async def test_mutation_m7e_public_call_private_return(
        monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any, tmp_path: Path) -> None:
    """M7e：續跑呼叫公開身分方法（參數相同、監聽可見）卻丟棄其回傳值、改回傳私有 `_compute_config_hash` ⇒
    邊界 09h 偵出（決策不隨替代值反轉）。"""
    from api.core.config import settings
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService
    from momentum.factories import create_feature_factory

    def _public_call_private_return(checkpoint: Dict[str, Any]) -> Any:
        payload = checkpoint.get("request_payload") or {}
        factory = create_feature_factory(cache_dir=str(settings.data_cache_path / "feature_klines"))

        def _identity(symbol: str, timeframe: str) -> str:
            factory.config_identity(symbol, timeframe, payload.get("config_override"), payload.get("start_date"),
                                    payload.get("end_date"))
            return factory._compute_config_hash(
                factory._resolve_config(payload.get("config_override")), symbol, timeframe,
                start_date=payload.get("start_date"), end_date=payload.get("end_date"))

        return _identity

    monkeypatch.setattr(FeatureFactoryBatchService, "_resume_identity", staticmethod(_public_call_private_return))
    service = batch_service_factory(tmp_path / "ckpt")
    identity_calls: List[Any] = []
    response, calls = await _public_resume(service, tmp_path, monkeypatch, identity_calls,
                                           substitute=_SUBSTITUTE_IDENTITY)
    assert _identity_args(identity_calls) == _EXPECTED_IDENTITY_ARGS  # 公開方法確被同參數呼叫（09g 之監聽看不出）
    assert (response["skipped_items"], calls) != (1, ["BTCUSDT", "ETHUSDT"])


@pytest.mark.asyncio
async def test_mutation_m7b_public_resume_ignores_identity(
        monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any, tmp_path: Path) -> None:
    """M7b：續跑分割改回只看 manifest ⇒ 經公開入口時身分不符之完成項被跳過（邊界 09g 偵出）。"""
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService

    def _manifest_only(self: Any, checkpoint: Dict[str, Any], identity: Any) -> Tuple[list, list]:
        kept = [i for i in checkpoint.get("completed_items", [])
                if self._resolve_completed_run_hash(i) is None
                or self._completed_manifest_exists(i, self._resolve_completed_run_hash(i))]
        return kept, [i for i in checkpoint.get("completed_items", []) if i not in kept]

    monkeypatch.setattr(FeatureFactoryBatchService, "_partition_completed_items", _manifest_only)
    service = batch_service_factory(tmp_path / "ckpt")
    response, calls = await _public_resume(service, tmp_path, monkeypatch)
    assert (response["skipped_items"], calls) != (1, ["ETHUSDT", "SOLUSDT"])


@pytest.mark.asyncio
async def test_mutation_m7c_public_resume_uses_fixed_identity(
        monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any, tmp_path: Path) -> None:
    """M7c：續跑之身分改為固定值（不經目前碼之 config_identity）⇒ 經公開入口時身分相符之完成項被重排（邊界 09g 偵出）。"""
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService

    monkeypatch.setattr(FeatureFactoryBatchService, "_resume_identity",
                        staticmethod(lambda _checkpoint: (lambda _symbol, _timeframe: "aaaa1111")))
    service = batch_service_factory(tmp_path / "ckpt")
    response, calls = await _public_resume(service, tmp_path, monkeypatch)
    assert (response["skipped_items"], calls) != (1, ["ETHUSDT", "SOLUSDT"])


@pytest.mark.asyncio
async def test_mutation_m7d_public_resume_bypasses_public_identity(
        monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any, tmp_path: Path) -> None:
    """M7d：續跑之身分改走私有 `_compute_config_hash`（結果相同、繞過公開方法）⇒ 邊界 09g 之公開方法呼叫紀錄偵出。"""
    from api.core.config import settings
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService
    from momentum.factories import create_feature_factory

    def _private_identity(checkpoint: Dict[str, Any]) -> Any:
        payload = checkpoint.get("request_payload") or {}
        factory = create_feature_factory(cache_dir=str(settings.data_cache_path / "feature_klines"))
        return lambda symbol, timeframe: factory._compute_config_hash(
            factory._resolve_config(payload.get("config_override")), symbol, timeframe,
            start_date=payload.get("start_date"), end_date=payload.get("end_date"))

    monkeypatch.setattr(FeatureFactoryBatchService, "_resume_identity", staticmethod(_private_identity))
    service = batch_service_factory(tmp_path / "ckpt")
    identity_calls: List[Any] = []
    await _public_resume(service, tmp_path, monkeypatch, identity_calls)
    assert _identity_args(identity_calls) != _EXPECTED_IDENTITY_ARGS


def test_mutation_m7_resume_ignores_identity(monkeypatch: pytest.MonkeyPatch, batch_service_factory: Any,
                                              tmp_path: Path) -> None:
    """M7：續跑分割改回只看 manifest（不比身分）⇒ 邊界 09b 之情境不再重排。"""
    from api.services.feature_factory_batch_service import FeatureFactoryBatchService

    def _manifest_only(self: Any, checkpoint: Dict[str, Any], identity: Any) -> Tuple[list, list]:
        retained, requeued = [], []
        for item in checkpoint.get("completed_items", []):
            run_hash = self._resolve_completed_run_hash(item)
            if run_hash is None or self._completed_manifest_exists(item, run_hash):
                retained.append(item)
            else:
                requeued.append(item)
        return retained, requeued

    monkeypatch.setattr(FeatureFactoryBatchService, "_partition_completed_items", _manifest_only)
    service = batch_service_factory(tmp_path / "ckpt")
    checkpoint = _checkpoint(service, [_item(tmp_path, "BTCUSDT", "1h", "aaaa1111")], {})
    assert _partition(service, checkpoint, lambda symbol, timeframe: "bbbb2222") != ([], ["BTCUSDT"])
