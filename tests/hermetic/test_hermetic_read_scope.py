"""TESTSEL I1a｜SPEC Task 1.3：HERMETIC 重導只作用於「未給根之寫入預設」，不波及給根之讀取。

背景（I1 原型 red_classified.md）：整合分支 3 條讀真實／物化 run 之測試因 HERMETIC 重導而紅、main 基準通過。
實作前 accept_01 為紅（整合分支現況）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.hermetic._harness import run_repo_nodeids_in_scratch_cwd, REPO

HERMETIC_VICTIMS = [
    "tests/momentum/test_feature_library_row_index.py::test_load_real_run_attaches_persisted_axis",
    "tests/momentum/test_feature_library_row_index.py::test_load_real_run_value_conservation",
    "tests/momentum/Analysis/test_ic_persist_redirect_isolation.py::test_all_seam_probes_stay_under_root[S11]",
]


def test_accept_01_hermetic_victims_pass(tmp_path: Path) -> None:
    """SPEC Task 1.3 驗證：三條於整合分支通過（main 9f059c65 基準已通過）。cwd＝repo 根（與日常執行相同）。"""
    res = run_repo_nodeids_in_scratch_cwd(HERMETIC_VICTIMS, REPO)
    assert res.rc == 0, res.out
    assert "3 passed" in res.out, res.out


def test_boundary_01_unrooted_write_defaults_land_in_hermetic_root() -> None:
    """邊界①：未給根之寫入預設（FeatureRegistry 預設路徑、FeatureStorage 預設根、CGSA 預設根）仍落 HERMETIC_ROOT。"""
    import tests.conftest as root_conftest
    from momentum.FeatureEngineering import feature_registry, run_paths
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    hermetic = Path(root_conftest.HERMETIC_ROOT).resolve()
    assert hermetic in Path(feature_registry.DEFAULT_REGISTRY_PATH).resolve().parents
    assert hermetic in Path(FeatureStorage().base_path).resolve().parents or Path(FeatureStorage().base_path).resolve() == hermetic / "features"
    assert hermetic in (Path.cwd() / run_paths.default_cgsa_root()).resolve().parents


def _load_given_run(tmp_feature_run_env):  # type: ignore[no-untyped-def]
    """呼叫端明給根（tmp_feature_run_env：registry 環境變數＋storage／reader 預設根指物化 run）後讀實際 run。"""
    from momentum.factories import create_feature_library

    run = tmp_feature_run_env.activate("bch_1h")["bch_1h"]
    df = create_feature_library().load(run.symbol, run.timeframe, config_hash=run.config_hash)
    return run, df


def test_boundary_02_rooted_read_reads_given_run(tmp_feature_run_env) -> None:  # type: ignore[no-untyped-def]
    """邊界②：給根之讀取讀實際 run——列數等於物化時之主時間軸長度、且非空（審查 r1 P2-03：不得只比路徑）。"""
    run, df = _load_given_run(tmp_feature_run_env)
    assert len(df) == len(run.index_s) > 0
    assert df.shape[1] > 0


def test_mutation_rooted_read_redirected_to_hermetic_fails(tmp_feature_run_env, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    """改壞對照：讀取根被導回 HERMETIC 空根（模擬重導波及給根之讀取，即整合分支 3 條受害測試之實況
    `V2 feature manifest not found: …/testsel_hermetic_…`）⇒ 同一讀取失敗。"""
    import tests.conftest as root_conftest
    from momentum import factories
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    run = tmp_feature_run_env.activate("bch_1h")["bch_1h"]
    hermetic_features = str(Path(root_conftest.HERMETIC_ROOT) / "features")
    monkeypatch.setattr(FeatureStorage.__init__, "__defaults__", (hermetic_features,))
    monkeypatch.setattr(FeatureReader.__init__, "__defaults__", (hermetic_features,))
    monkeypatch.setattr(factories.create_feature_reader, "__defaults__", (hermetic_features,))
    with pytest.raises(Exception):
        df = factories.create_feature_library().load(run.symbol, run.timeframe, config_hash=run.config_hash)
        assert len(df) == len(run.index_s) > 0
