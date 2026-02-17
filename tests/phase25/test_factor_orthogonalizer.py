import numpy as np
import pandas as pd

from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer


def _make_correlated_df(n: int = 240) -> pd.DataFrame:
    np.random.seed(42)
    x1 = np.random.randn(n)
    x2 = 0.9 * x1 + 0.1 * np.random.randn(n)
    x3 = -0.6 * x1 + 0.2 * np.random.randn(n)
    return pd.DataFrame({"f1": x1, "f2": x2, "f3": x3})


def test_single_factor_orth():
    analyzer = FactorOrthogonalizer(config={})
    data = pd.DataFrame({"f1": np.random.randn(100)})
    orth, meta = analyzer.gram_schmidt(data)
    assert orth.empty
    assert meta["skipped"] is True


def test_already_orthogonal():
    analyzer = FactorOrthogonalizer(config={})
    np.random.seed(7)
    base = np.random.randn(180, 3)
    q, _ = np.linalg.qr(base)
    data = pd.DataFrame(q, columns=["f1", "f2", "f3"])
    orth, meta = analyzer.gram_schmidt(data)
    assert meta["correlation_after"] <= 0.05
    assert set(orth.columns) == {"f1", "f2", "f3"}


def test_near_zero_residual():
    analyzer = FactorOrthogonalizer(config={"degenerate_threshold": 1e-6})
    x = np.random.randn(120)
    data = pd.DataFrame({"f1": x, "f2": x + 1e-8 * np.random.randn(120)})
    _, meta = analyzer.gram_schmidt(data)
    assert "f2" in meta["degenerate_features"]


def test_underdetermined_system():
    analyzer = FactorOrthogonalizer(config={})
    data = pd.DataFrame(np.random.randn(4, 8), columns=[f"f{i}" for i in range(8)])
    transformed, meta = analyzer.pca_orthogonalize(data)
    assert transformed.empty
    assert meta["skipped"] is True


def test_default_priority_order():
    data = _make_correlated_df()
    analyzer = FactorOrthogonalizer(config={"icir_scores": {"f2": 0.3, "f3": 0.2, "f1": 0.1}})
    _, meta = analyzer.gram_schmidt(data)
    assert meta["priority_order"][:3] == ["f2", "f3", "f1"]


def test_nan_factors_orth():
    analyzer = FactorOrthogonalizer(config={})
    data = _make_correlated_df()
    data.loc[:20, "f2"] = np.nan
    orth, meta = analyzer.gram_schmidt(data)
    assert not orth.empty
    assert meta["correlation_after"] <= 0.05


def test_pca_outputs_components_and_loadings():
    analyzer = FactorOrthogonalizer(config={})
    data = _make_correlated_df()
    transformed, meta = analyzer.pca_orthogonalize(data, n_components=2)
    assert transformed.shape[1] == 2
    assert "loadings" in meta
    assert set(meta["principal_components"]) == {"PC1", "PC2"}
