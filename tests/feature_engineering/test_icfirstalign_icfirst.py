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


def _floats(scores: Dict[str, Any], keys: List[str]) -> np.ndarray:
    """分數依 keys 取值為 float64；IC JSON 以 null 表 NaN ⇒ 轉回 NaN（比對以 equal_nan，不吸收任何差異）。"""
    return np.asarray([np.nan if scores[k] is None else scores[k] for k in keys], dtype=np.float64)


def _is_tf_col(name: str, tf: str) -> bool:
    return f"_{tf}_" in name or name.endswith(f"_{tf}")


@pytest.mark.parametrize("training", [["12h"], ["12h", "4h"]], ids=["S2", "S2m"])
def test_ic_first_scores_match_independent_oracle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                  training: List[str]) -> None:
    """§G IC-first oracle（S2、S2m，經 run_ic_first）：全部欄之分數與相同 threshold 之選欄集合皆等於測試端獨立 oracle。

    軸由 raw sidecar 獨立讀取；S2m 另要求兩週期皆有有限 oracle 分數（r23：只驗欄名存在時，
    把 4h 欄分數改 NaN 之破壞不會紅）。
    """
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    threshold = 0.02
    result = _run(factory, h.s2_payload(training), ic_threshold=threshold)
    config_hash = str(result.metadata["config_hash"])
    reader = FeatureReader(str(root))
    axis = reader.load_row_index_v2(h.SYMBOL, h.PRIMARY, config_hash)
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = [c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g.get("columns", [])]
    features = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    features.index = axis
    expected = h.oracle_spearman(features, h.forward_return_label(end=W[1]))  # 預設 label 以 end_date 為界（同 HEAD）
    payload = _ic_json(root, config_hash)
    got = payload["ic_scores"]
    assert set(got) == set(expected)
    keys = sorted(expected)
    assert np.allclose(_floats(got, keys), _floats(expected, keys), rtol=0, atol=1e-12, equal_nan=True)
    for tf in training:
        assert any(_is_tf_col(k, tf) and np.isfinite(expected[k]) for k in keys), f"{tf} 無有限 oracle 分數"
    expected_selected = {k for k, v in expected.items() if np.isfinite(v) and abs(v) >= threshold}
    assert set(payload["selected"]) == expected_selected


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


# ---------------------------------------------------------------- Task 4.2 守護與恢復之正式入口接線（r23）

def _guard_alive(pid: int) -> bool:
    import psutil

    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def _spy_guard(monkeypatch: pytest.MonkeyPatch, root: Path) -> Dict[str, Any]:
    """正式入口之守護／恢復／lease 事件序（呼叫端經 `memory_budget` 模組屬性呼叫，SPEC Task 4.2）。

    只記錄、不改行為；斷言以效果為準（守護行程於 run 出口後已不存在、恢復後暫存已刪）。
    """
    from momentum.FeatureEngineering import memory_budget as mb

    st: Dict[str, Any] = {"events": [], "pids": [], "alive_during_ic": []}
    real_start, real_recover = mb.start_guard, mb.recover_aborted_run
    real_acquire, real_release = RunLease.acquire, RunLease.release

    def start(run_dir: Path, run_id: str, **k: Any) -> Any:
        handle = real_start(run_dir, run_id, **k)
        st["events"].append(("start_guard", str(run_dir)))
        st["pids"].append(handle.pid)
        return handle

    def recover(run_dir: Path) -> Any:
        st["events"].append(("recover", str(run_dir)))
        return real_recover(run_dir)

    def acquire(*a: Any, **k: Any) -> Any:
        lease = real_acquire(*a, **k)
        st["events"].append(("acquire", ""))
        return lease

    def release(self: RunLease) -> None:
        # r24：於實際釋放鎖之前記錄守護是否已回收（先釋放 lease 再停守護之實作 ⇒ 此處為 True）
        st["events"].append(("release", ""))
        st.setdefault("guard_alive_at_release", []).append(any(_guard_alive(p) for p in st["pids"]))
        return real_release(self)

    real_ic = ICEngine.compute_ic_from_l7_raw

    def during_ic(self: ICEngine, *a: Any, **k: Any) -> Any:
        st["alive_during_ic"].append([_guard_alive(p) for p in st["pids"]])
        return real_ic(self, *a, **k)

    monkeypatch.setattr(mb, "start_guard", start)
    monkeypatch.setattr(mb, "recover_aborted_run", recover)
    monkeypatch.setattr(RunLease, "acquire", acquire)
    monkeypatch.setattr(RunLease, "release", release)
    monkeypatch.setattr(ICEngine, "compute_ic_from_l7_raw", during_ic)
    return st


def _kinds(st: Dict[str, Any]) -> List[str]:
    return [e[0] for e in st["events"]]


def _inject(monkeypatch: pytest.MonkeyPatch, where: str) -> None:
    if where == "generation":
        monkeypatch.setattr(FeatureFactory, "_layer3_rolling_aggregation",
                            lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    elif where == "ic":
        monkeypatch.setattr(ICEngine, "compute_ic_from_l7_raw",
                            lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("injected ic failure")))


@pytest.mark.parametrize("entry,failure", [("generate", None), ("generate", "generation"), ("ic_first", None),
                                           ("ic_first", "generation"), ("ic_first", "ic")])
def test_formal_run_guard_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, failure: Any) -> None:
    """正式入口（`generate_features`、`run_ic_first`〔經 `lease_sink` 移交〕）之正常與例外出口：
    恰一個守護、恢復於取得 lease 後且於守護啟動前、守護於 lease 釋放前停止且行程已回收；
    `run_ic_first` 之守護於 IC 期間仍存活（隨 lease 移交至持有者，不於生成返回時停止）。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    _inject(monkeypatch, failure)  # 先注入、spy 後裝：IC 例外案例之 spy 包住注入之 IC，仍記錄 IC 期間守護存活
    st = _spy_guard(monkeypatch, root)
    call = (lambda: _run(factory)) if entry == "ic_first" else (lambda: h.generate_s2(root))
    if failure:
        with pytest.raises(Exception):
            call()
    else:
        call()
    kinds = _kinds(st)
    assert kinds.count("start_guard") == 1 and len(st["pids"]) == 1
    assert kinds.index("acquire") < kinds.index("recover") < kinds.index("start_guard")
    assert not _guard_alive(st["pids"][0]), "run 出口後守護行程仍存活"
    assert "release" in kinds and kinds.count("acquire") == kinds.count("release")
    assert st["guard_alive_at_release"] and not any(st["guard_alive_at_release"]), "守護須於 lease 釋放前停止並回收"
    if entry == "ic_first" and failure != "generation":
        assert st["alive_during_ic"] and all(all(a) for a in st["alive_during_ic"])
        assert kinds.count("acquire") == 1


def test_mutation_formal_run_guard_not_stopped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：正式 run 出口不停止守護（`GuardHandle.stop` 改為無動作）⇒ 守護行程於出口後仍存活而紅。"""
    import os
    import signal

    from momentum.FeatureEngineering import memory_budget as mb

    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    st = _spy_guard(monkeypatch, root)
    monkeypatch.setattr(mb.GuardHandle, "stop", lambda self: None)
    try:
        _run(factory)
        assert st["pids"] and _guard_alive(st["pids"][0])
    finally:
        for pid in st["pids"]:
            if _guard_alive(pid):
                os.kill(pid, signal.SIGKILL)


def _seed_abort(root: Path, factory: FeatureFactory, tmp_path: Path) -> Tuple[Path, Path, Path]:
    """於同 key 之 run 目錄放前次 abort 收據、停止旗標與已登記之暫存；另放一個不屬本 run 之暫存。"""
    from momentum.FeatureEngineering import memory_budget as mb

    run = h.run_dir(root, _config_hash(factory))
    run.mkdir(parents=True, exist_ok=True)
    owned = tmp_path / "owned_tmp"
    owned.mkdir()
    (owned / "x.bin").write_bytes(b"0" * 1024)
    other = tmp_path / "other_run_tmp"
    other.mkdir()
    files = h.CONTRACT["guard_files"]
    (run / files["owned_paths"]).write_text(json.dumps([str(owned)]), encoding="utf-8")
    (run / files["abort_receipt"]).write_text(json.dumps({
        "time": "t", "trigger": "pressure_critical", "readings": {}, "last_checkpoint": "L3", "run_id": "R",
        "owned_paths": [str(owned)]}), encoding="utf-8")
    (run / files["stop_flag"]).write_text("x", encoding="utf-8")
    assert callable(mb.recover_aborted_run)
    return run, owned, other


@pytest.mark.parametrize("entry", ["generate", "ic_first"])
def test_formal_run_recovers_previous_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str) -> None:
    """同 key 下一次正式 run 取得 lease 後之恢復：前次登記之暫存被刪、舊停止旗標清除（run 因而不被誤停）、
    abort 收據保留、他 run 暫存不變。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    run, owned, other = _seed_abort(root, factory, tmp_path)
    if entry == "ic_first":
        _run(factory)
    else:
        h.generate_s2(root)
    files = h.CONTRACT["guard_files"]
    assert not owned.exists() and other.exists()
    assert (run / files["abort_receipt"]).exists()


def test_mutation_formal_run_skips_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：正式入口不呼叫恢復（`recover_aborted_run` 改為無動作）⇒ 前次暫存殘留、或舊停止旗標使 run 被具名停止而紅。"""
    from momentum.FeatureEngineering import memory_budget as mb

    root = h.isolated(monkeypatch, tmp_path)
    factory = h.make_factory(root)
    _, owned, _ = _seed_abort(root, factory, tmp_path)
    monkeypatch.setattr(mb, "recover_aborted_run", lambda run_dir: {})
    try:
        _run(factory)
    except mb.GenerationMemoryBudgetExceeded:
        return
    assert owned.exists()


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
    # 實作期調整：注入點由 L1 改為只屬正式生成之 L3–L6 落盤（L1 亦於預熱探測之校準域執行，於該處失敗即以
    # NON_DEGRADABLE 之 CalibrationError 原樣上拋——Task 2.2 邊界①，由下方 non_degradable 測試涵蓋）
    monkeypatch.setattr(FeatureFactory, "_persist_single_tf_l3_l6_to_cgsa",
                        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("injected generation")))
    with pytest.raises(icc.ICFirstGenerationError) as info:
        _run(h.make_factory(root))
    assert _chain_has(info.value, "injected generation")


def test_boundary_02_label_outside_window_not_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界②：選窗外之 label 不參與 IC（窗外 label 改為極端值，IC 分數不變）。"""
    root = h.isolated(monkeypatch, tmp_path)
    window = {"start": "2025-10-01", "end": W[1]}
    base = _run(h.make_factory(root), selection_window=window)
    base_scores = _ic_json(root, str(base.metadata["config_hash"]))["ic_scores"]
    label = h.forward_return_label(end=W[1])  # 窗內值與預設 label 相同（以 end_date 為界）
    label.loc[label.index < pd.Timestamp(window["start"])] = 1e6
    shutil.rmtree(h.run_dir(root, str(base.metadata["config_hash"])))
    again = _run(h.make_factory(root), selection_window=window, label=label)
    scores = _ic_json(root, str(again.metadata["config_hash"]))["ic_scores"]
    keys = sorted(base_scores)
    assert np.allclose(_floats(scores, keys), _floats(base_scores, keys), rtol=0, atol=0, equal_nan=True)


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


def _chain_has(exc: Any, text: str) -> bool:
    """例外鏈（`__cause__`／`__context__`）中任一節之訊息含 `text`。"""
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if text in str(exc):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def test_l65_failure_raises_named_not_write_raw_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """L6.5 拋例外 ⇒ `ICFirstGenerationError`，且其例外鏈帶 L6.5 之原始失敗（非 `write_raw requires non-empty`）。"""
    root = h.isolated(monkeypatch, tmp_path)
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink", _l65_raises(RuntimeError("l65 boom")))
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", _l65_raises(RuntimeError("l65 boom")))
    with pytest.raises(icc.ICFirstGenerationError) as info:
        _run(h.make_factory(root))
    assert "requires non-empty" not in str(info.value)
    assert _chain_has(info.value, "l65 boom")


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
    # 實作期調整：注入點改為 raw-sink 路徑之逐群組分派 `_transform_single_group_to_arrays`（S2 之群組不走 numba
    # 快路徑，原注入點 `_registry_fast_transform` 從未被呼叫 ⇒ 測不到群組失敗）
    real = FeaturePreprocessor._transform_single_group_to_arrays
    calls = {"n": 0}

    def fail_second(self: FeaturePreprocessor, *a: Any, **k: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("one group fails")
        return real(self, *a, **k)

    monkeypatch.setattr(FeaturePreprocessor, "_transform_single_group_to_arrays", fail_second)
    with pytest.raises(icc.ICFirstGenerationError) as info:
        _run(h.make_factory(root))
    assert calls["n"] == 2 and _chain_has(info.value, "one group fails")


def test_mutation_l65_failure_degrades_to_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：L6.5 拋 `l65 boom` 而被吞成空表（`_safe_execute` 式降級）⇒ run 之結果（成功或其他錯誤）之例外鏈
    不帶 L6.5 原始失敗，正常案例之判定（具名錯誤且鏈帶 `l65 boom`）因而紅。

    （v27 實作期調整：生成之一切非 NON_DEGRADABLE 失敗皆包為 `ICFirstGenerationError`，降級後之下游錯誤
    〔如 `write_raw requires non-empty`〕亦具名 ⇒ 以 isinstance 判定 mutant 不再可區分；改以例外鏈判定。）"""
    root = h.isolated(monkeypatch, tmp_path)
    boom = _l65_raises(RuntimeError("l65 boom"))

    def swallowed(self: FeaturePreprocessor, *a: Any, **k: Any) -> Any:
        try:
            return boom(self, *a, **k)
        except RuntimeError:
            return 0

    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups_to_sink", swallowed)
    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", swallowed)
    try:
        _run(h.make_factory(root))
        raised: Any = None
    except Exception as exc:  # noqa: BLE001
        raised = exc
    assert not (isinstance(raised, icc.ICFirstGenerationError) and _chain_has(raised, "l65 boom"))


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
