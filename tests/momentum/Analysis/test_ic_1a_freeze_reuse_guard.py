from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import ModuleType

import h5py
import numpy as np
import pandas as pd
import pytest

from api.services.ic_analysis_service import ICAnalysisService

from tests.golden.ic_phase1_1a_cut1 import freeze_baseline, freeze_baseline_new


FREEZE_MODULES = (freeze_baseline, freeze_baseline_new)
FEATURES = ["feature_a", "feature_b"]


class _RegistryReader:
    def list_features_v2(self, symbol: str, timeframe: str, config_hash: str) -> list[str]:
        return list(reversed(FEATURES))

    def load_row_index_v2(
        self, symbol: str, timeframe: str, config_hash: str
    ) -> None:
        return None

    def load_columns_v2(
        self, symbol: str, timeframe: str, config_hash: str, selected: list[str]
    ) -> pd.DataFrame:
        return pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], columns=selected)


class _FreezeService:
    _write_features_h5 = staticmethod(ICAnalysisService._write_features_h5)

    @staticmethod
    def _build_ic_metadata_from_run(
        symbol: str, timeframe: str, config_hash: str, selected: list[str]
    ) -> dict[str, object]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "config_hash": config_hash,
            **{name: {"name": name, "category": "unknown", "layer": 1} for name in selected},
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_pair(module: ModuleType, input_dir: Path) -> tuple[Path, Path]:
    h5_path = input_dir / f"{module.SYMBOL}_{module.TIMEFRAME}_{module.CONFIG_HASH}_top2.h5"
    meta_path = input_dir / f"{module.SYMBOL}_{module.TIMEFRAME}_{module.CONFIG_HASH}_top2_meta.json"
    input_dir.mkdir(parents=True)
    with h5py.File(h5_path, "w") as handle:
        group = handle.create_group(f"{module.SYMBOL}/{module.TIMEFRAME}")
        group.create_dataset("features", data=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))
        group.create_dataset("timestamps", data=np.arange(2, dtype=np.int64))
        dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset("feature_names", data=np.array(FEATURES, dtype=object), dtype=dtype)
    meta_path.write_text(
        json.dumps(
            {
                "symbol": module.SYMBOL,
                "timeframe": module.TIMEFRAME,
                "config_hash": module.CONFIG_HASH,
                "baseline_subset": {
                    "max_features": 2,
                    "selected_features": FEATURES,
                },
            }
        ),
        encoding="utf-8",
    )
    return h5_path, meta_path


def _pin_manifest(module: ModuleType, baseline_meta: Path, h5_path: Path, meta_path: Path) -> None:
    baseline_meta.write_text(
        json.dumps(
            {
                "input_manifest": {
                    "h5_sha256": _sha256(h5_path),
                    "meta_sha256": _sha256(meta_path),
                }
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture(params=FREEZE_MODULES, ids=("flag_off", "flag_on"))
def guarded_freeze(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = request.param
    input_dir = tmp_path / "inputs"
    baseline_meta = tmp_path / "baseline_meta.json"
    input_dir.mkdir(parents=True)
    h5_path = input_dir / f"{module.SYMBOL}_{module.TIMEFRAME}_{module.CONFIG_HASH}_top2.h5"
    meta_path = input_dir / f"{module.SYMBOL}_{module.TIMEFRAME}_{module.CONFIG_HASH}_top2_meta.json"
    service = _FreezeService()
    reader = _RegistryReader()
    service._write_features_h5(
        h5_path,
        module.SYMBOL,
        module.TIMEFRAME,
        reader.load_columns_v2(module.SYMBOL, module.TIMEFRAME, module.CONFIG_HASH, FEATURES),
    )
    meta_payload = service._build_ic_metadata_from_run(
        module.SYMBOL, module.TIMEFRAME, module.CONFIG_HASH, FEATURES
    )
    meta_payload["baseline_subset"] = {
        "selection": "sorted(feature_names)[:max_features]",
        "max_features": 2,
        "selected_features": FEATURES,
        "source_feature_count": 2,
    }
    meta_path.write_bytes(module._canonical_bytes(meta_payload))
    _pin_manifest(module, baseline_meta, h5_path, meta_path)
    monkeypatch.setattr(module, "INPUT_DIR", input_dir)
    monkeypatch.setattr(module, "META_PATH", baseline_meta)
    monkeypatch.setattr(module, "create_feature_reader", lambda: _RegistryReader())
    return module, baseline_meta, h5_path, meta_path


def test_reuse_rejects_h5_value_mutation_with_unchanged_meta(guarded_freeze) -> None:
    module, _baseline_meta, h5_path, _meta_path = guarded_freeze
    with h5py.File(h5_path, "r+") as handle:
        handle[f"{module.SYMBOL}/{module.TIMEFRAME}/features"][0, 0] = 99.0

    with pytest.raises(RuntimeError, match="H5 SHA256"):
        module._materialize_deterministic_subset(object(), 2)


def test_reuse_rejects_selected_features_h5_divergence(guarded_freeze) -> None:
    module, baseline_meta, h5_path, meta_path = guarded_freeze
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["baseline_subset"]["selected_features"] = list(reversed(FEATURES))
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _pin_manifest(module, baseline_meta, h5_path, meta_path)

    with pytest.raises(RuntimeError, match="feature order"):
        module._materialize_deterministic_subset(object(), 2)


def test_reuse_rejects_embedded_config_hash_mutation(guarded_freeze) -> None:
    module, baseline_meta, h5_path, meta_path = guarded_freeze
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["config_hash"] = "mutated-config-hash"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    _pin_manifest(module, baseline_meta, h5_path, meta_path)

    with pytest.raises(RuntimeError, match="meta identity/subset"):
        module._materialize_deterministic_subset(object(), 2)


@pytest.mark.parametrize("module", FREEZE_MODULES, ids=("flag_off", "flag_on"))
def test_gate_b_registry_rebuild_matches_pinned_input_sha(
    module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_dir = tmp_path / "inputs"
    baseline_meta = tmp_path / "baseline_meta.json"
    input_dir.mkdir(parents=True)
    h5_path = input_dir / f"{module.SYMBOL}_{module.TIMEFRAME}_{module.CONFIG_HASH}_top2.h5"
    meta_path = input_dir / f"{module.SYMBOL}_{module.TIMEFRAME}_{module.CONFIG_HASH}_top2_meta.json"
    service = _FreezeService()
    reader = _RegistryReader()
    service._write_features_h5(
        h5_path,
        module.SYMBOL,
        module.TIMEFRAME,
        reader.load_columns_v2(module.SYMBOL, module.TIMEFRAME, module.CONFIG_HASH, FEATURES),
    )
    meta_payload = service._build_ic_metadata_from_run(
        module.SYMBOL, module.TIMEFRAME, module.CONFIG_HASH, FEATURES
    )
    meta_payload["baseline_subset"] = {
        "selection": "sorted(feature_names)[:max_features]",
        "max_features": 2,
        "selected_features": FEATURES,
        "source_feature_count": 2,
    }
    meta_path.write_bytes(module._canonical_bytes(meta_payload))
    expected_h5_sha = _sha256(h5_path)
    expected_meta_sha = _sha256(meta_path)
    baseline_meta.write_text(
        json.dumps(
            {
                "input_manifest": {
                    "h5_sha256": expected_h5_sha,
                    "meta_sha256": expected_meta_sha,
                }
            }
        ),
        encoding="utf-8",
    )
    h5_path.unlink()
    meta_path.unlink()
    monkeypatch.setattr(module, "INPUT_DIR", input_dir)
    monkeypatch.setattr(module, "META_PATH", baseline_meta)
    monkeypatch.setattr(module, "create_feature_reader", lambda: _RegistryReader())

    rebuilt_h5, rebuilt_meta, selected = module._materialize_deterministic_subset(
        service, 2
    )

    assert selected == FEATURES
    assert _sha256(rebuilt_h5) == expected_h5_sha
    assert _sha256(rebuilt_meta) == expected_meta_sha
