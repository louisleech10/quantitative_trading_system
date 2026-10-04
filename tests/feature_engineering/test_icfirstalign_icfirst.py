"""ICFIRSTALIGN 乙 Task 2.1／2.2／2.4／3.2：IC-first 改經正式 CGSA 生成（docs/ICFIRSTALIGN_SPEC.md v18）。

真實 kline S2／S2m；一切寫入隔離於 tmp。新 `run_ic_first(symbol, tf, config, *, start_date, end_date, ...)`：
以 `generate_features(persist=True, lease_sink=..., require_raw=True)` 生成，同一 lease 持有至 IC、processed、cleanup。
實作前應為紅：`run_ic_first` 仍走記憶體 L1–L6（真實資料必拋 AlignmentViolationError）、`raw_data`／`layers` 仍在簽名、
`generate_features` 無 `require_raw`、`transform_selected` 無 `arm`。
"""

from __future__ import annotations

import ast
import inspect
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_engine import ICEngine
from momentum.FeatureEngineering import ic_first_context as icc
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.FeatureEngineering.run_locks import RunBusyError, RunLease
from tests.feature_engineering import icfirstalign_helpers as h

pytestmark = pytest.mark.timeout(900)

W = h.S2_WINDOW
MIGRATED = [
    "tests/feature_engineering/test_b6_warmup_trim.py",
    "tests/feature_engineering/ffstat_helpers.py",
    "tests/feature_engineering/test_ffstat_calibration.py",
    "tests/feature_engineering/test_ffstat_stable_start.py",
    "tests/feature_engineering/test_ic_first_pipeline.py",
]


def _run(factory: FeatureFactory, payload: Dict[str, Any] = None, **kwargs: Any):
    config = factory._resolve_config(payload or h.s2_payload())
    kwargs.setdefault("ic_engine", ICEngine({"methods": ["spearman"]}))
    kwargs.setdefault("ic_threshold", 0.02)
    kwargs.setdefault("label_horizon", "1")
    kwargs.setdefault("selection_window", {"start": W[0], "end": W[1]})
    return factory.run_ic_first(h.SYMBOL, h.PRIMARY, config, start_date=W[0], end_date=W[1], **kwargs)


def _config_hash(factory: FeatureFactory, payload: Dict[str, Any] = None) -> str:
    config = factory._resolve_config(payload or h.s2_payload())
    return factory._compute_config_hash(config, h.SYMBOL, h.PRIMARY, start_date=W[0], end_date=W[1])


def _locks(root: Path) -> Path:
    return root / ".locks"


def _ic_json(root: Path, config_hash: str) -> Dict[str, Any]:
    path = h.run_dir(root, config_hash) / f"ic_selected_features_{h.SYMBOL}_{h.PRIMARY}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- Task 2.1 設計 A

def test_run_ic_first_signature_has_no_second_engine_inputs() -> None:
    params = inspect.signature(FeatureFactory.run_ic_first).parameters
    assert "raw_data" not in params and "layers" not in params
    assert "require_raw" in inspect.signature(FeatureFactory.generate_features).parameters


def test_ic_first_s2_scores_match_independent_oracle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """§G IC-first oracle（S2，經 run_ic_first）。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    result = _run(factory)
    config_hash = str(result.metadata["config_hash"])
    reader = FeatureReader(str(root))
    axis = reader.load_row_index_v2(h.SYMBOL, h.PRIMARY, config_hash)
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = [c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g.get("columns", [])]
    features = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    features.index = axis
    expected = h.oracle_spearman(features, h.forward_return_label())
    got = _ic_json(root, config_hash)["ic_scores"]
    assert set(got) == set(expected)
    keys = sorted(expected)
    assert np.allclose([got[k] for k in keys], [expected[k] for k in keys], rtol=0, atol=1e-12, equal_nan=True)


def test_ic_first_s2m_includes_both_timeframe_columns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """S2m（12h＋4h）：IC 欄含兩週期標記欄。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    result = _run(factory, h.s2_payload(["12h", "4h"]))
    scores = _ic_json(root, str(result.metadata["config_hash"]))["ic_scores"]
    assert any("_4h_" in c or c.endswith("_4h") for c in scores)
    assert any("_12h_" in c or c.endswith("_12h") for c in scores)


def test_run_ic_first_never_uses_memory_combine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    contexts: List[str] = []
    real = FeatureFactory._combine_layers

    def spy(layers: Any, context: str = "unknown") -> Any:  # `_combine_layers` 為 staticmethod
        contexts.append(context)
        return real(layers, context=context)

    monkeypatch.setattr(FeatureFactory, "_combine_layers", staticmethod(spy))
    _run(h.make_factory(root))
    assert "ic_first_l65_pre_input" not in contexts


def test_lease_busy_during_ic_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """run 進行中（IC 階段）同 key 取 lease ⇒ RunBusyError；run 結束後可取。"""
    root = h.isolated(monkeypatch, tmp_path)
    observed: List[str] = []
    real = ICEngine.compute_ic_from_l7_raw

    def during_ic(self: ICEngine, symbol: str, tf: str, config_hash: str, *a: Any, **k: Any) -> Any:
        try:
            RunLease.acquire(_locks(root), symbol, tf, config_hash, timeout=0).release()
            observed.append("acquired")
        except RunBusyError:
            observed.append("busy")
        return real(self, symbol, tf, config_hash, *a, **k)

    monkeypatch.setattr(ICEngine, "compute_ic_from_l7_raw", during_ic)
    factory = h.make_factory(root)
    result = _run(factory)
    assert observed == ["busy"]
    RunLease.acquire(_locks(root), h.SYMBOL, h.PRIMARY, str(result.metadata["config_hash"]), timeout=0).release()


def test_lease_released_after_generation_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    monkeypatch.setattr(FeatureFactory, "_layer3_rolling_aggregation",
                        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(Exception):
        _run(factory)
    RunLease.acquire(_locks(root), h.SYMBOL, h.PRIMARY, _config_hash(factory), timeout=0).release()


def test_lease_released_after_ic_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    monkeypatch.setattr(ICEngine, "compute_ic_from_l7_raw",
                        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("injected ic failure")))
    with pytest.raises(RuntimeError):
        _run(factory)
    RunLease.acquire(_locks(root), h.SYMBOL, h.PRIMARY, _config_hash(factory), timeout=0).release()


def _seed_legacy_h5(root: Path, factory: FeatureFactory, config_hash: str) -> None:
    """模擬使用者機器上既有之 legacy H5 cache（frame 路徑舊 run 所留）：以真實 raw 之少數欄寫一份同 hash 之 H5。"""
    reader = FeatureReader(str(root))
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = [c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g.get("columns", [])][:3]
    frame = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult

    from momentum.FeatureEngineering.consumer_gate import COMPLETENESS_FIELD_NAMES

    run_manifest = json.loads((h.run_dir(root, config_hash) / "feature_manifest.json").read_text(encoding="utf-8"))
    metadata = {"config_hash": config_hash, "run_status": "complete",
                **{k: run_manifest[k] for k in COMPLETENESS_FIELD_NAMES if k in run_manifest}}
    legacy = FeatureGenerationResult(features_df=frame, labels_df=pd.DataFrame(index=frame.index),
                                     metadata=metadata,
                                     feature_count=len(cols), generation_time=0.0, layer_counts={}, config_used={})
    FeatureStorage(str(root)).save_factory_output(h.SYMBOL, h.PRIMARY, legacy)


def test_cleanup_raw_rerun_regenerates_raw_with_single_lease(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cleanup_raw 後再跑（且存在同 hash 之 legacy H5）⇒ raw 重生、結果與首跑相等、該次 acquire／release 各 1。"""
    root = h.isolated(monkeypatch, tmp_path)
    first = _run(h.make_factory(root), cleanup_raw=False)
    config_hash = str(first.metadata["config_hash"])
    _seed_legacy_h5(root, h.make_factory(root), config_hash)
    shutil.rmtree(h.run_dir(root, config_hash) / "raw")
    counts = {"acquire": 0, "release": 0}
    real_acquire, real_release = RunLease.acquire, RunLease.release

    def acquire(*a: Any, **k: Any) -> Any:
        counts["acquire"] += 1
        return real_acquire(*a, **k)

    def release(self: RunLease) -> None:
        counts["release"] += 1
        return real_release(self)

    monkeypatch.setattr(RunLease, "acquire", staticmethod(acquire))
    monkeypatch.setattr(RunLease, "release", release)
    second = _run(h.make_factory(root))
    assert (h.run_dir(root, config_hash) / "raw").is_dir()
    assert sorted(second.metadata["selected_features"]) == sorted(first.metadata["selected_features"])
    assert counts == {"acquire": 1, "release": 1}


def test_require_raw_false_existing_caller_still_hits_h5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """既有 caller（require_raw 預設 False）於 raw 已清時仍回 H5 命中（行為不變）。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory, result = h.generate_s2(root)
    config_hash = str(result.metadata["config_hash"])
    _seed_legacy_h5(root, factory, config_hash)
    shutil.rmtree(h.run_dir(root, config_hash) / "raw")
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, config_hash) is not None
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, config_hash, require_raw=True) is None


def test_mutation_require_raw_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`_try_load_cache` 忽略 require_raw（H5 命中直接回傳）⇒ raw 不存在、IC 失敗。"""
    root = h.isolated(monkeypatch, tmp_path)
    first = _run(h.make_factory(root))
    config_hash = str(first.metadata["config_hash"])
    _seed_legacy_h5(root, h.make_factory(root), config_hash)
    shutil.rmtree(h.run_dir(root, config_hash) / "raw")
    real = FeatureFactory._try_load_cache
    monkeypatch.setattr(FeatureFactory, "_try_load_cache",
                        lambda self, s, t, c, require_raw=False: real(self, s, t, c, require_raw=False))
    with pytest.raises(Exception):
        _run(h.make_factory(root))


def test_boundary_01_generation_failure_raises_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界①：生成失敗 ⇒ `ICFirstGenerationError` 上拋（不回空表）。"""
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(FeatureFactory, "_layer1_atomic_indicators",
                        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("injected L1")))
    with pytest.raises(icc.ICFirstGenerationError):
        _run(h.make_factory(root))


def test_boundary_02_label_outside_window_not_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界②：選窗外之 label 不參與 IC（窗外 label 改為極端值，IC 分數不變）。"""
    root = h.isolated(monkeypatch, tmp_path)
    window = {"start": "2025-10-01", "end": W[1]}
    base = _run(h.make_factory(root), selection_window=window)
    base_scores = _ic_json(root, str(base.metadata["config_hash"]))["ic_scores"]
    label = h.forward_return_label()
    label.loc[label.index < pd.Timestamp(window["start"])] = 1e6
    shutil.rmtree(h.run_dir(root, str(base.metadata["config_hash"])))
    again = _run(h.make_factory(root), selection_window=window, label=label)
    scores = _ic_json(root, str(again.metadata["config_hash"]))["ic_scores"]
    keys = sorted(base_scores)
    assert np.allclose([scores[k] for k in keys], [base_scores[k] for k in keys], rtol=0, atol=0, equal_nan=True)


def test_boundary_03_h5_overwritten_other_hash_misses_not_misused(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界③：legacy H5 為 symbol／timeframe 級；寫入另一 hash 後原 hash 查詢未命中（讀取核 hash，不錯用）。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory, result_a = h.generate_s2(root)
    hash_a = str(result_a.metadata["config_hash"])
    _seed_legacy_h5(root, factory, hash_a)
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, hash_a) is not None
    _, result_b = h.generate_s2(root, h.s2_payload(rolling_aggregation={"enabled": True, "windows": [5]}))
    hash_b = str(result_b.metadata["config_hash"])
    assert hash_b != hash_a
    _seed_legacy_h5(root, factory, hash_b)
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, hash_a) is None


# ---------------------------------------------------------------- Task 2.2 L6.5 失敗語意

def _l65_raises(exc: BaseException):
    def raiser(self: FeaturePreprocessor, *a: Any, **k: Any) -> Any:
        raise exc
    return raiser


def test_l65_failure_raises_named_not_write_raw_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink", _l65_raises(RuntimeError("l65 boom")))
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", _l65_raises(RuntimeError("l65 boom")))
    with pytest.raises(icc.ICFirstGenerationError) as info:
        _run(h.make_factory(root))
    assert "requires non-empty" not in str(info.value)


def test_boundary_01_non_degradable_errors_reraised_as_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 邊界①：NON_DEGRADABLE_ERRORS（CalibrationError 等）原樣上拋。"""
    from momentum.FeatureEngineering.preprocessing.calibration import CalibrationError

    root = h.isolated(monkeypatch, tmp_path)
    err = CalibrationError("non degradable", timeframe="12h", field="compute")
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink", _l65_raises(err))
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", _l65_raises(err))
    with pytest.raises(CalibrationError):
        _run(h.make_factory(root))


def test_boundary_02_single_group_failure_fails_whole_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.2 邊界②：單一群組 L6.5 失敗 ⇒ 整次失敗（不得只略過該群組）。"""
    root = h.isolated(monkeypatch, tmp_path)
    real = FeaturePreprocessor._registry_fast_transform
    calls = {"n": 0}

    def fail_second(self: FeaturePreprocessor, arr: Any, ctx: Any, *a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("one group fails")
        return real(self, arr, ctx, *a, **k)

    monkeypatch.setattr(FeaturePreprocessor, "_registry_fast_transform", fail_second)
    with pytest.raises(icc.ICFirstGenerationError):
        _run(h.make_factory(root))


def test_mutation_l65_failure_degrades_to_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：L6.5 失敗被吞成空表（`_safe_execute` 式降級）⇒ 不再是具名錯誤。"""
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink",
                        lambda self, *a, **k: {})
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", lambda self, *a, **k: 0)
    try:
        _run(h.make_factory(root))
        raised: Any = None
    except Exception as exc:  # noqa: BLE001
        raised = exc
    assert not isinstance(raised, icc.ICFirstGenerationError)


# ---------------------------------------------------------------- Task 2.4 測試遷移

def _run_ic_first_calls(path: str) -> List[ast.Call]:
    tree = ast.parse((h.REPO / path).read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "run_ic_first"]


def test_migrated_callers_have_no_second_engine_kwargs() -> None:
    offenders = []
    for path in MIGRATED:
        for call in _run_ic_first_calls(path):
            names = {kw.arg for kw in call.keywords}
            if names & {"raw_data", "layers"}:
                offenders.append(f"{path}:{call.lineno}")
    assert offenders == []


def test_migrated_files_ic_first_paths_not_cgsa_off() -> None:
    """遷移清單內 IC-first 之呼叫不得在 FFACT_USE_CGSA=0 下（以文字掃描：檔內 IC-first helper 不設 CGSA 關）。"""
    offenders = []
    for path in MIGRATED:
        text = (h.REPO / path).read_text(encoding="utf-8")
        if "IC_FIRST_OFF_ENV" in text and re.search(r"IC_FIRST_OFF_ENV\s*=.*FFACT_USE_CGSA", text):
            offenders.append(path)
        for match in re.finditer(r"def (\w*ic_first\w*)\(.*?\n(?=def |\Z)", text, flags=re.S):
            if '"FFACT_USE_CGSA", "0"' in match.group(0) or "FFACT_USE_CGSA=0" in match.group(0):
                offenders.append(f"{path}:{match.group(1)}")
    assert offenders == []


def _swallows_alignment(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            names = {n.id for n in ast.walk(node.type) if isinstance(n, ast.Name)} | \
                    {n.attr for n in ast.walk(node.type) if isinstance(n, ast.Attribute)}
            if "AlignmentViolationError" in names:
                return True
    return False


def test_helper_does_not_swallow_alignment_violation() -> None:
    assert not _swallows_alignment((h.REPO / "tests/feature_engineering/ffstat_helpers.py").read_text(encoding="utf-8"))


def test_mutation_helper_swallowing_alignment_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：helper 以 try／except AlignmentViolationError 吞錯 ⇒ 偵測函式回 True。"""
    import tests.feature_engineering.test_icfirstalign_icfirst as me

    swallowing = "def f():\n    try:\n        g()\n    except AlignmentViolationError:\n        return None\n"
    monkeypatch.setattr(me, "_swallows_alignment", me._swallows_alignment)
    assert me._swallows_alignment(swallowing)


# ---------------------------------------------------------------- Task 3.2 post-IC 臂

def test_post_ic_arm_polars_even_when_env_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    calls = {"polars": 0}
    real = FeaturePreprocessor._transform_single_polars

    def spy(self: FeaturePreprocessor, *a: Any, **k: Any) -> Any:
        calls["polars"] += 1
        return real(self, *a, **k)

    monkeypatch.setattr(FeaturePreprocessor, "_transform_single_polars", spy)
    result = _run(h.make_factory(root))
    assert calls["polars"] > 0
    manifest = json.loads((h.run_dir(root, str(result.metadata["config_hash"])) / "feature_manifest.json")
                          .read_text(encoding="utf-8"))
    assert manifest["artifacts"]["processed"]["post_ic_arm"] == h.CONTRACT["post_ic_arm"]


def test_post_ic_arm_unavailable_raises_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import momentum.FeatureEngineering.polars_adapter as pa_mod

    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(pa_mod, "_check_polars_available", lambda: False)
    with pytest.raises(icc.PostICArmUnavailableError):
        _run(h.make_factory(root))


def test_boundary_01_other_transform_selected_callers_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.2 邊界①：非 IC-first 之 `transform_selected`（不帶 arm）仍依環境：FFACT_USE_POLARS=0 ⇒ 不走 Polars。"""
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    calls = {"polars": 0}
    real = FeaturePreprocessor._transform_single_polars
    monkeypatch.setattr(FeaturePreprocessor, "_transform_single_polars",
                        lambda self, *a, **k: (calls.__setitem__("polars", calls["polars"] + 1), real(self, *a, **k))[1])
    close = h.kline_close()
    frame = pd.DataFrame({"x": close.pct_change().to_numpy()[:300]}, index=close.index[:300])
    FeaturePreprocessor({"winsorization": {"enabled": True}}).transform_selected(["x"], {"g": frame})
    assert calls["polars"] == 0


def test_ic_first_pipeline_tests_do_not_force_pandas_arm() -> None:
    text = (h.REPO / "tests/feature_engineering/test_ic_first_pipeline.py").read_text(encoding="utf-8")
    assert not re.search(r"FFACT_USE_POLARS[\"']?\s*,\s*[\"']0", text)


def test_mutation_post_ic_arm_reads_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`transform_selected` 忽略 arm 改讀環境 ⇒ FFACT_USE_POLARS=0 下不走 Polars。"""
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    real_ts = FeaturePreprocessor.transform_selected
    monkeypatch.setattr(FeaturePreprocessor, "transform_selected",
                        lambda self, selected, groups, config=None, arm=None: real_ts(self, selected, groups, config))
    calls = {"polars": 0}
    real = FeaturePreprocessor._transform_single_polars
    monkeypatch.setattr(FeaturePreprocessor, "_transform_single_polars",
                        lambda self, *a, **k: (calls.__setitem__("polars", calls["polars"] + 1), real(self, *a, **k))[1])
    _run(h.make_factory(root))
    assert calls["polars"] == 0
