import numpy as np
import pandas as pd

from momentum.FeatureEngineering.labels.label_generator import LabelGenerator


def test_label_generator_binary_and_return():
    close = pd.Series([1.0, 1.1, 1.2, 1.3, 1.4])
    generator = LabelGenerator({"binary": {"horizons": [2], "threshold": 0.0}, "regression": {"horizons": [2]}})
    labels = generator.generate_all(close)

    assert "label_binary_2d" in labels.columns
    assert "label_return_2d" in labels.columns
    assert labels["label_binary_2d"].isna().iloc[-1]
    assert labels["label_return_2d"].isna().iloc[-1]
