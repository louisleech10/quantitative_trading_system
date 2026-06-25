import numpy as np
import pandas as pd

from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator


class _DummyReader:
    def read_klines(self, _symbol: str, _timeframe: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "timestamp": [1704067200 + 86400 * idx for idx in range(80)],
                "close": np.linspace(100.0, 120.0, 80),
                "close_EMA_55": np.linspace(99.0, 119.0, 80),
            }
        )


def _real_grouped_config() -> ICConfig:
    config_data = load_ic_config().model_dump(by_alias=True)
    config_data["report"]["include_decay_analysis"] = False
    config_data["report"]["include_regime_analysis"] = True
    config_data["ic_calculation"]["grouped_analysis"].update(
        {
            "by_year": True,
            "by_quarter": False,
            "by_regime": False,
            "by_category": False,
            "by_data_source": False,
            "by_layer": False,
            "by_volatility": False,
        }
    )
    return ICConfig.model_validate(config_data)


def test_stage4_grouped_uses_real_pydantic_config() -> None:
    """真 ICConfig 走 grouped 路徑時不可因 Pydantic config 崩潰。"""

    config = _real_grouped_config()
    orchestrator = ICFilterOrchestrator(config)
    index = pd.RangeIndex(80)
    features_df = pd.DataFrame(
        {
            "feature_pos": np.linspace(0.0, 1.0, 80),
            "feature_neg": np.linspace(1.0, 0.0, 80),
        },
        index=index,
    )
    label = pd.Series(np.linspace(0.0, 1.0, 80), index=index)

    results = orchestrator._stage4_ic_calculation(
        features_df,
        label,
        {"symbol": "BTCUSDT", "timeframe": "1h"},
        config,
        _DummyReader(),
    )

    assert "grouped_ic" in results
    assert "by_year" in results["grouped_ic"]
    assert "2024" in results["grouped_ic"]["by_year"]


def test_default_grouped_config_does_not_raise_with_kline() -> None:
    """預設 YAML grouped config 不應啟用尚未實作的 by_volatility。"""

    config = load_ic_config()
    orchestrator = ICFilterOrchestrator(config)
    index = pd.RangeIndex(80)
    features_df = pd.DataFrame(
        {
            "feature_pos": np.linspace(0.0, 1.0, 80),
            "feature_neg": np.linspace(1.0, 0.0, 80),
        },
        index=index,
    )
    label = pd.Series(np.linspace(0.0, 1.0, 80), index=index)
    metadata = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "feature_pos": {
            "name": "feature_pos",
            "category": "trend",
            "data_source": "close",
            "layer": 1,
        },
        "feature_neg": {
            "name": "feature_neg",
            "category": "trend",
            "data_source": "close",
            "layer": 1,
        },
    }

    results = orchestrator._stage4_ic_calculation(
        features_df,
        label,
        metadata,
        config,
        _DummyReader(),
    )

    assert config.ic_calculation.grouped_analysis.by_volatility is False
    assert "by_year" in results["grouped_ic"]
    assert "2024" in results["grouped_ic"]["by_year"]
