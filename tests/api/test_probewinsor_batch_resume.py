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
