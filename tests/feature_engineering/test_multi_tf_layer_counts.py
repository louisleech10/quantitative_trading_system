from __future__ import annotations

from types import SimpleNamespace

from momentum.FeatureEngineering.core.column_group import LayerSource
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator


class _Registry:
    def __init__(self, groups):
        self._groups = groups

    def iter_all(self):
        for idx, group in enumerate(self._groups):
            yield f"group_{idx}", group


def test_collect_layer_counts_from_registry_uses_persisted_groups() -> None:
    registry = _Registry(
        [
            SimpleNamespace(timeframe="1h", layer=LayerSource.L1, shape=(10, 2)),
            SimpleNamespace(timeframe="1h", layer=LayerSource.L3, shape=(10, 5)),
            SimpleNamespace(timeframe="12h", layer=LayerSource.L3, shape=(10, 7)),
        ]
    )

    counts = MultiTFGenerator._collect_layer_counts_from_registry(registry, "1h")

    assert counts["layer1"] == 2
    assert counts["layer3"] == 5
    assert counts["layer2"] == 0


def test_apply_total_layer_counts_preserves_layer65_when_feature_total_matches() -> None:
    generator = MultiTFGenerator.__new__(MultiTFGenerator)
    generator._primary_tf = "1h"
    result = SimpleNamespace(feature_count=3, layer_counts={"layer6_5": 1}, metadata={})

    counts = generator._apply_total_layer_counts_to_result(
        result,
        {"1h": {"layer1": 2}},
    )

    assert counts == {"layer1": 2, "layer6_5": 1}
    assert result.layer_counts == counts
    assert result.metadata["layer_counts"] == counts
