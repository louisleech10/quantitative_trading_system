import numpy as np
import pandas as pd

from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer


def _make_correlated_df(n: int = 240) -> pd.DataFrame:
    np.random.seed(42)
    x1 = np.random.randn(n)
    x2 = 0.9 * x1 + 0.1 * np.random.randn(n)
    x3 = -0.6 * x1 + 0.2 * np.random.randn(n)
    return pd.DataFrame({"f1": x1, "f2": x2, "f3": x3})


def test_pca_skip_when_single_feature():
    analyzer = FactorOrthogonalizer(config={})
    transformed, meta = analyzer.pca_orthogonalize(pd.DataFrame({"f1": np.random.randn(20)}))
    assert transformed.empty
    assert meta["skipped"] is True


def test_resolve_priority_with_partial_manual_order():
    analyzer = FactorOrthogonalizer(config={})
    df = pd.DataFrame(np.random.randn(30, 3), columns=["a", "b", "c"])
    order = analyzer._resolve_priority_order(df, ["b", "z"])
    assert order[0] == "b"
    assert set(order) == {"a", "b", "c"}


def test_resolve_priority_fallback_to_proxy_when_icir_nonfinite():
    analyzer = FactorOrthogonalizer(config={"icir_scores": {"a": 0.5, "b": np.nan, "c": 0.3}})
    df = pd.DataFrame(np.random.randn(40, 3), columns=["a", "b", "c"])
    order = analyzer._resolve_priority_order(df, None)
    assert set(order) == {"a", "b", "c"}


def test_mean_off_diagonal_small_matrix():
    assert FactorOrthogonalizer._mean_off_diagonal(pd.DataFrame([[1.0]])) == 0.0
