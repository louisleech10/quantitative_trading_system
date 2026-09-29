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

    # TESTSPEED 方向 B（使用者 2026-09-29）：完整指紋——K 線檔內容雜湊（依路徑／大小／mtime 快取，每檔只讀一次）、
    # momentum/ 產品碼與資料檔內容雜湊（每 session 一次）、依賴版本；另記本測試是否 monkeypatch 了測試以外之目標
    # （mutant 嫌疑，統計重複時排除）。仍只記錄、不快取。
    targets: List[str] = []
    original_setattr = pytest.MonkeyPatch.setattr

    def recording_setattr(mp_self, target, name=None, value=None, raising=True):  # type: ignore[no-untyped-def]
        owner = target if isinstance(target, str) else getattr(target, "__module__", None) or getattr(target, "__name__", "")
        targets.append(f"{owner}:{name if isinstance(name, str) else (target if isinstance(target, str) else '')}")
        if name is None:
            return original_setattr(mp_self, target, value, raising=raising) if value is not None else \
                original_setattr(mp_self, target, name, raising=raising)
        return original_setattr(mp_self, target, name, value, raising=raising)


    def logged(self, symbol, timeframe, *args, **kwargs):  # type: ignore[no-untyped-def]
        cache_dir = getattr(getattr(self, "_adapter_registry", None), "_adapters", {})
        kline_files = []
        for adapter in (cache_dir.values() if isinstance(cache_dir, dict) else []):
            storage = getattr(adapter, "_storage", None)
            cache = getattr(storage, "cache_dir", None)
            path = Path(cache) / getattr(storage, "HDF5_FILENAME", "kline_cache.h5") if cache is not None else None
            if path and os.path.exists(str(path)):
                kline_files.append(_file_content_digest(str(path)))
        request_part = {"symbol": symbol, "timeframe": timeframe, "args": [repr(a) for a in args],
                        "kwargs": {k: (v if isinstance(v, (str, int, float, bool, type(None))) else
                                       json.dumps(v, sort_keys=True, default=str)) for k, v in kwargs.items()},
                        "kline": kline_files,
                        "code": _product_code_digest(),
                        "deps": _dependency_versions(),
                        "env": {k: v for k, v in sorted(os.environ.items())
                                if k.startswith("FFACT_") and k not in ("FFACT_CGSA_WORK_DIR", "FFACT_FEATURE_REGISTRY_PATH")}}
        _isolation = (":_d_star_cache_dir", ":tempdir")  # 測試隔離之路徑重導（prepare_stat_env），非改計算
        suspect = sorted({t for t in targets if not t.startswith(("tests.", "os", "_pytest")) and "environ" not in t
                          and not t.endswith(_isolation)})
        fingerprint = hashlib.sha256(json.dumps(request_part, sort_keys=True, default=str).encode()).hexdigest()[:16]
        t0 = time.perf_counter()
        try:
            return original(self, symbol, timeframe, *args, **kwargs)
        finally:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"test": request.node.nodeid, "fingerprint": fingerprint,
                                     "seconds": round(time.perf_counter() - t0, 2), "symbol": symbol,
                                     "timeframe": timeframe, "mutant_suspect": suspect},
                                    ensure_ascii=False) + "\n")

    monkeypatch.setattr(FeatureFactory, "generate_features", logged)
    monkeypatch.setattr(pytest.MonkeyPatch, "setattr", recording_setattr)  # 於記錄器自身之 patch 之後才開始記錄


_DIGEST_CACHE: dict = {}


def _file_content_digest(path: str) -> str:
    """檔案內容 sha256（依路徑／大小／mtime 於本程序快取）。"""
    import hashlib
    import os

    st = os.stat(path)
    key = (path, st.st_size, st.st_mtime_ns)
    if key not in _DIGEST_CACHE:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        _DIGEST_CACHE[key] = h.hexdigest()
    return _DIGEST_CACHE[key]


def _product_code_digest() -> str:
    """momentum/ 下全部 .py、.yaml、.json 內容之總雜湊（每程序算一次）。"""
    import hashlib

    if "code" not in _DIGEST_CACHE:
        root = Path(__file__).resolve().parents[2] / "momentum"
        h = hashlib.sha256()
        for p in sorted(root.rglob("*")):
            if p.suffix in (".py", ".yaml", ".yml", ".json") and "__pycache__" not in p.parts:
                h.update(str(p.relative_to(root)).encode())
                h.update(p.read_bytes())
        _DIGEST_CACHE["code"] = h.hexdigest()
    return _DIGEST_CACHE["code"]


def _dependency_versions() -> dict:
    import importlib.metadata as md
    import platform

    if "deps" not in _DIGEST_CACHE:
        vers = {"python": platform.python_version()}
        for name in ("numpy", "pandas", "TA-Lib", "numba", "polars", "pyarrow", "scipy", "h5py"):
            try:
                vers[name] = md.version(name)
            except md.PackageNotFoundError:
                vers[name] = None
        _DIGEST_CACHE["deps"] = vers
    return _DIGEST_CACHE["deps"]
