import numpy as np
import pandas as pd

from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.feature_validator import FeatureValidator




def test_feature_validator_factory():
    features_df = pd.DataFrame({"f1": [1.0, 1.0, 1.0], "f2": [1.0, 2.0, 3.0]})
    labels_df = pd.DataFrame({"label_binary_3d": [1, 0, np.nan]})
    result = FeatureGenerationResult(
        features_df=features_df,
        labels_df=labels_df,
        metadata={},
        feature_count=2,
        generation_time=0.0,
        layer_counts={},
        config_used={},
    )

    validator = FeatureValidator()
    validation = validator.validate_factory_output(result)
    assert "f1" in validation.constant_features_removed
    assert result.features_df.shape[1] == 1
