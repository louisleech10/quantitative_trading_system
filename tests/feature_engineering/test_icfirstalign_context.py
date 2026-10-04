"""ICFIRSTALIGN 乙 Task 2.0：IC-first 不可變 run context（docs/ICFIRSTALIGN_SPEC.md v17）。

單元：`begin_context`／`complete_context` 之必填、深凍結、選窗超出公開窗、生成結果缺 output_window。
整合（真實 S2，經新 `run_ic_first`）：同一 factory 連續兩次不同起訖 ⇒ 第二次之 OutputWindow 與 config_hash
只由第二次參數決定（平穩化開、關各一）；第一次中途例外不影響第二次；生成結果 metadata 帶 `output_window`。
實作前應為紅：`ic_first_context` 為空殼、`run_ic_first` 不回 context、生成結果無 `output_window`。
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, Tuple

import pytest

from momentum.Analysis.ic_engine import ICEngine
from momentum.FeatureEngineering import ic_first_context as icc
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(900)

W1: Tuple[str, str] = ("2025-07-01", "2026-01-31")
W2: Tuple[str, str] = ("2025-09-01", "2026-03-31")
OW_KEYS = tuple(h.CONTRACT["output_window_keys"])


def test_isolated_redirects_d_star_cache_per_root(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """隔離前提（r23）：兩個測試根之 d* 快取根互異、各在其根內、且不落專案 data_cache（不生成，秒級）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    project = (h.REPO / "data_cache").resolve()
    seen = []
    for name in ("a", "b"):
        with monkeypatch.context() as mp:
            h.isolated(mp, tmp_path / name)
            path = FeaturePreprocessor._d_star_cache_dir().resolve()
        seen.append(path)
        assert (tmp_path / name).resolve() in path.parents
        assert project not in path.parents
    assert seen[0] != seen[1]


def _begin(**over: Any) -> icc.ICFirstRunContext:
    kw: Dict[str, Any] = dict(symbol=h.SYMBOL, timeframe=h.PRIMARY, training=["12h"], start=W1[0], end=W1[1],
                              selection_window={"start": W1[0], "end": W1[1]}, split_id=None,
                              label_spec={"kind": "forward_return", "h": 1})
    kw.update(over)
    return icc.begin_context(**kw)


def _meta(output_window: Dict[str, Any]) -> Dict[str, Any]:
    return {"config_hash": "abc123", "output_window": output_window}


def _ow(start: str = W1[0], end: str = W1[1]) -> Dict[str, Any]:
    return {"output_start": start, "output_end": end, "ingest_start": "2025-03-01", "max_warmup_bars": 100,
            "warmup_enabled": True}


# ---------------------------------------------------------------- 單元

@pytest.mark.parametrize("missing", ["start", "end"])
def test_begin_context_requires_start_and_end(missing: str) -> None:
    with pytest.raises(icc.ICFirstContextError):
        _begin(**{missing: None})


def test_context_deep_frozen_against_caller_mutation() -> None:
    training = ["12h"]
    window = {"start": W1[0], "end": W1[1]}
    label_spec = {"kind": "forward_return", "h": 1}
    ctx = _begin(training=training, selection_window=window, label_spec=label_spec)
    training.append("4h")
    window["start"] = "2000-01-01"
    label_spec["h"] = 99
    assert ctx.training == ("12h",)
    assert ctx.selection_window["start"] == W1[0]
    assert ctx.label_spec["h"] == 1


def test_context_container_assignment_raises() -> None:
    ctx = icc.complete_context(_begin(), _meta(_ow()))
    with pytest.raises(TypeError):
        ctx.selection_window["start"] = "2000-01-01"  # type: ignore[index]
    with pytest.raises(TypeError):
        ctx.label_spec["h"] = 2  # type: ignore[index]
    with pytest.raises(TypeError):
        ctx.output_window["output_start"] = "2000-01-01"  # type: ignore[index]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.config_hash = "x"  # type: ignore[misc]


def test_complete_context_takes_window_and_hash_from_metadata() -> None:
    ctx = icc.complete_context(_begin(), _meta(_ow()))
    assert ctx.complete and ctx.config_hash == "abc123"
    assert dict(ctx.output_window) == _ow()


def test_boundary_01_selection_outside_public_window_raises() -> None:
    """Task 2.0 邊界①：選窗超出公開窗 ⇒ `ICFirstContextError`。"""
    partial = _begin(selection_window={"start": "2024-01-01", "end": W1[1]})
    with pytest.raises(icc.ICFirstContextError):
        icc.complete_context(partial, _meta(_ow()))


def test_boundary_02_generation_metadata_missing_output_window_raises() -> None:
    """Task 2.0 邊界②：生成結果缺 `output_window` ⇒ `ICFirstContextError`。"""
    with pytest.raises(icc.ICFirstContextError):
        icc.complete_context(_begin(), {"config_hash": "abc123"})


# ---------------------------------------------------------------- 整合（真實 S2）

def _run(factory: FeatureFactory, window: Tuple[str, str], payload: Dict[str, Any]):
    config = factory._resolve_config(payload)
    return factory.run_ic_first(h.SYMBOL, h.PRIMARY, config, start_date=window[0], end_date=window[1],
                                ic_engine=ICEngine({"methods": ["spearman"]}), ic_threshold=0.02,
                                label_horizon="1", selection_window={"start": window[0], "end": window[1]})


def _ctx(result: Any) -> Dict[str, Any]:
    return result.metadata["ic_first_context"]


def _stationary_payload() -> Dict[str, Any]:
    payload = h.s2_payload()
    # N＝200：S2 前史（2024-01 起）在 N＝500（≥1 日週期預設）時有 56 欄校準不足致 run partial（主委實跑 2026-10-04）
    payload["preprocessing"] = {**payload["preprocessing"], "fractional_differencing": {"enabled": True},
                                "calibration_bars": 200, "calibration_bars_by_timeframe": {"12h": 200}}
    return payload


@pytest.mark.parametrize("stationary", [False, True], ids=["stationarity_off", "stationarity_on"])
def test_second_call_window_and_hash_from_its_own_params(tmp_path: Any, monkeypatch: pytest.MonkeyPatch,
                                                         stationary: bool) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    payload = _stationary_payload() if stationary else h.s2_payload()
    shared = h.make_factory(root)
    _run(shared, W1, payload)
    second = _ctx(_run(shared, W2, payload))
    fresh = _ctx(_run(h.make_factory(root), W2, payload))
    assert second["output_window"] == fresh["output_window"]
    assert second["config_hash"] == fresh["config_hash"]
    assert second["output_window"]["output_start"].startswith(W2[0])


def test_first_call_failure_does_not_leak_into_second(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    shared = h.make_factory(root)
    real = FeatureFactory._layer3_rolling_aggregation
    calls = {"n": 0}

    def fail_once(self: FeatureFactory, *args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("injected generation failure")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(FeatureFactory, "_layer3_rolling_aggregation", fail_once)
    with pytest.raises(Exception):
        _run(shared, W1, h.s2_payload())
    monkeypatch.setattr(FeatureFactory, "_layer3_rolling_aggregation", real)
    second = _ctx(_run(shared, W2, h.s2_payload()))
    fresh = _ctx(_run(h.make_factory(root), W2, h.s2_payload()))
    assert second == fresh


def test_generation_result_metadata_has_output_window(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    _, result = h.generate_s2(root)
    assert set(OW_KEYS) <= set(result.metadata["output_window"])


def test_mutation_context_reads_stale_output_window(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：context 之 OutputWindow 改取前一次 run 留下之值（模擬讀 `_current_output_window`）⇒ 第二次窗錯。"""
    root = h.isolated(monkeypatch, tmp_path)
    shared = h.make_factory(root)
    first_ow = _ctx(_run(shared, W1, h.s2_payload()))["output_window"]
    real = icc.complete_context

    def stale(partial: Any, metadata: Any) -> Any:
        return real(partial, {**dict(metadata), "output_window": first_ow})

    monkeypatch.setattr(icc, "complete_context", stale)
    second = _ctx(_run(shared, W2, h.s2_payload()))
    assert second["output_window"] == first_ow  # 斷言「只由第二次參數決定」因而翻轉


def test_mutation_context_reads_stale_config_hash(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：context 之 config_hash 改取前一次 run 留下之值（模擬讀 `_current_config_hash`）。"""
    root = h.isolated(monkeypatch, tmp_path)
    shared = h.make_factory(root)
    first_hash = _ctx(_run(shared, W1, h.s2_payload()))["config_hash"]
    real = icc.complete_context

    def stale(partial: Any, metadata: Any) -> Any:
        return real(partial, {**dict(metadata), "config_hash": first_hash})

    monkeypatch.setattr(icc, "complete_context", stale)
    second = _ctx(_run(shared, W2, h.s2_payload()))
    fresh = _ctx(_run(h.make_factory(root), W2, h.s2_payload()))
    assert second["config_hash"] != fresh["config_hash"]
