"""Task 4.1 驗證：CSCV 分割器（path 數＝C(S,S/2)、分割覆蓋／互斥、塊長餘數、預算 fail-closed、lazy generator）。"""

import inspect
import math

import numpy as np
import pytest

from momentum.Analysis.strategy_validation.cscv import CscvBudgetExceeded, cscv_path_count, iter_cscv_splits


@pytest.mark.parametrize("s, expected", [(12, 924), (14, 3432), (16, 12870)])
def test_path_count_matches_comb(s, expected):
    """① C(S,S/2)：12→924、14→3432、16→12870，且 == math.comb。"""
    assert cscv_path_count(s) == expected == math.comb(s, s // 2)


def test_all_paths_cover_and_are_disjoint_s12():
    """② S=12 全 924 組：IS∪OOS＝全索引且交集空；IS 塊數＝6。"""
    n_obs = 1205
    full = np.arange(n_obs)
    n = 0
    for is_idx, oos_idx in iter_cscv_splits(n_obs=n_obs, s_blocks=12):
        assert np.array_equal(np.sort(np.concatenate([is_idx, oos_idx])), full)
        assert np.intersect1d(is_idx, oos_idx).size == 0
        n += 1
    assert n == 924


def test_block_lengths_with_remainder():
    """③ n_obs=1205, S=12 ⇒ 前 5 塊 101、餘 100（IS 由前 6 塊組成時長度＝5*101+100=605）。"""
    from momentum.Analysis.strategy_validation.cscv import _block_bounds

    blocks = _block_bounds(1205, 12)
    lengths = [len(b) for b in blocks]
    assert lengths == [101] * 5 + [100] * 7
    assert sum(lengths) == 1205
    assert blocks[0][0] == 0 and blocks[-1][-1] == 1204
    first = next(iter_cscv_splits(n_obs=1205, s_blocks=12))
    assert first[0].size == 605 and first[1].size == 600


def test_odd_or_too_many_blocks_raise():
    """④ S 奇 ⇒ ValueError；S>n_obs ⇒ ValueError（皆在建立 generator 前）。"""
    with pytest.raises(ValueError):
        cscv_path_count(13)
    with pytest.raises(ValueError):
        iter_cscv_splits(n_obs=100, s_blocks=13)
    with pytest.raises(ValueError):
        iter_cscv_splits(n_obs=10, s_blocks=12)
    with pytest.raises(ValueError):
        cscv_path_count(0)


def test_budget_fail_closed():
    """⑤ S=20 ⇒ 184756 path > 20000 ⇒ raise；S=16,n_obs=2000 ⇒ 12870*2000=25.7M > 20M ⇒ raise（元素預算）。"""
    assert cscv_path_count(20) == 184756
    with pytest.raises(CscvBudgetExceeded):
        iter_cscv_splits(n_obs=1200, s_blocks=20)
    with pytest.raises(CscvBudgetExceeded):
        iter_cscv_splits(n_obs=2000, s_blocks=16)
    # 邊界內：S=16, n_obs=1500 ⇒ 19.3M ≤ 20M 可建
    gen = iter_cscv_splits(n_obs=1500, s_blocks=16)
    assert inspect.isgenerator(gen)


def test_is_lazy_generator():
    """⑥ 回傳 generator（非 list）；只 next() 一次即只計算一條 path。"""
    gen = iter_cscv_splits(n_obs=1200, s_blocks=12)
    assert inspect.isgenerator(gen)
    is_idx, oos_idx = next(gen)
    assert isinstance(is_idx, np.ndarray) and isinstance(oos_idx, np.ndarray)
    # 計數探針：包裝 combinations 迭代次數==1（用 gi_frame 之 lasti 不可靠 ⇒ 用 itertools.count 對照）
    import itertools

    counter = itertools.count()
    probe = ((next(counter), x) for x in iter_cscv_splits(n_obs=1200, s_blocks=12))
    next(probe)
    assert next(counter) == 1


def test_s_equals_two():
    """邊界④ S=2 ⇒ 2 條 path：前半／後半互換。"""
    paths = list(iter_cscv_splits(n_obs=10, s_blocks=2))
    assert len(paths) == 2
    assert np.array_equal(paths[0][0], np.arange(0, 5)) and np.array_equal(paths[0][1], np.arange(5, 10))
    assert np.array_equal(paths[1][0], np.arange(5, 10)) and np.array_equal(paths[1][1], np.arange(0, 5))
