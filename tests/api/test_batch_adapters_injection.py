"""Batch adapter 的 composition-root 顯式注入契約。"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from api.services.feature_factory_batch_adapters import (
    FeatureFactoryBrowseAdapter,
    FeatureFactoryQualityAdapter,
)
from api.services.feature_factory_service import feature_factory_service


@pytest.mark.parametrize(
    "adapter_class",
    [FeatureFactoryBrowseAdapter, FeatureFactoryQualityAdapter],
)
def test_batch_adapters_require_explicit_service(adapter_class) -> None:
    """未注入 service 時必須 fail-fast。"""

    with pytest.raises(TypeError):
        adapter_class()


@pytest.mark.parametrize(
    "relative_path",
    [
        Path("api/main.py"),
        Path("tests/performance/step6_multitf_batch_benchmark.py"),
    ],
)
def test_composition_roots_inject_service_and_construct_adapters(relative_path: Path) -> None:
    """兩個 composition root 都顯式注入 service，且 adapter 可完成建構。"""

    module = ast.parse(relative_path.read_text(encoding="utf-8"))
    injected_adapters = {
        node.func.id
        for node in ast.walk(module)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"FeatureFactoryBrowseAdapter", "FeatureFactoryQualityAdapter"}
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "feature_factory_service"
    }
    assert injected_adapters == {
        "FeatureFactoryBrowseAdapter",
        "FeatureFactoryQualityAdapter",
    }

    browse = FeatureFactoryBrowseAdapter(feature_factory_service)
    quality = FeatureFactoryQualityAdapter(feature_factory_service)
    assert browse._service is feature_factory_service
    assert quality._service is feature_factory_service
