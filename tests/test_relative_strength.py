import numpy as np
import pandas as pd

from momentum.FeatureEngineering.cross_sectional.relative_strength import RelativeStrengthProcessor


def test_relative_strength_computations():
    processor = RelativeStrengthProcessor()
    btc_close = pd.Series([100, 102, 104, 106, 108])
    sym_close = pd.Series([50, 51, 52, 53, 54])

    relative = processor.compute_relative_price(sym_close, btc_close)
    assert np.isclose(relative.iloc[0], 0.5)

    btc_returns = btc_close.pct_change()
    sym_returns = btc_returns * 2
    beta = processor.compute_beta(sym_returns, btc_returns, window=3)
    assert np.isclose(beta.dropna().iloc[-1], 2.0, atol=1e-6)

    idio = processor.compute_idiosyncratic_momentum(sym_returns, btc_returns, beta)
    assert np.isclose(idio.dropna().iloc[-1], 0.0, atol=1e-6)
