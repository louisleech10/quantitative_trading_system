"""Shared fixtures for fail-open feature_engineering tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _failopen_isolated_scratch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep CGSA work + feature registry writes off production data_cache paths."""
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
    registry_path = tmp_path / "features" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_path))


@pytest.fixture(autouse=True)
def _testspeed_generation_log(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """TESTSPEED 步驟①（量測，只記錄不快取）：設 `FFSTAT_GEN_LOG=<jsonl 路徑>` 時，每次
    `FeatureFactory.generate_features` 追加一列（測試名、輸入粗指紋、耗時），供統計重複生成與可省時間。
    粗指紋＝請求參數（標的、週期、設定、起訖日、persist）＋ K 線快取檔之路徑／大小／修改時間＋ FFACT_* 環境變數；
    不含程式碼與 monkeypatch 狀態——只作量測估計，不得據以取用快取（快取之指紋設計交委員諮詢輪）。"""
    import os

    log_path = os.environ.get("FFSTAT_GEN_LOG")
    if not log_path:
        return
    import hashlib
    import json
    import time

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    original = FeatureFactory.generate_features

    def logged(self, symbol, timeframe, *args, **kwargs):  # type: ignore[no-untyped-def]
        cache_dir = getattr(getattr(self, "_adapter_registry", None), "_adapters", {})
        kline_files = []
        for adapter in (cache_dir.values() if isinstance(cache_dir, dict) else []):
            storage = getattr(adapter, "_storage", None)
            cache = getattr(storage, "cache_dir", None)
            path = Path(cache) / getattr(storage, "HDF5_FILENAME", "kline_cache.h5") if cache is not None else None
            if path and os.path.exists(str(path)):
                st = os.stat(str(path))
                kline_files.append([str(path), st.st_size, int(st.st_mtime)])
        request_part = {"symbol": symbol, "timeframe": timeframe, "args": [repr(a) for a in args],
                        "kwargs": {k: (v if isinstance(v, (str, int, float, bool, type(None))) else
                                       json.dumps(v, sort_keys=True, default=str)) for k, v in kwargs.items()},
                        "kline": kline_files,
                        "env": {k: v for k, v in sorted(os.environ.items())
                                if k.startswith("FFACT_") and k not in ("FFACT_CGSA_WORK_DIR", "FFACT_FEATURE_REGISTRY_PATH")}}
        fingerprint = hashlib.sha256(json.dumps(request_part, sort_keys=True, default=str).encode()).hexdigest()[:16]
        t0 = time.perf_counter()
        try:
            return original(self, symbol, timeframe, *args, **kwargs)
        finally:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"test": request.node.nodeid, "fingerprint": fingerprint,
                                     "seconds": round(time.perf_counter() - t0, 2), "symbol": symbol,
                                     "timeframe": timeframe}, ensure_ascii=False) + "\n")

    monkeypatch.setattr(FeatureFactory, "generate_features", logged)
