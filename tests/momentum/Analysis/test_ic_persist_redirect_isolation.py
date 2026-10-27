"""非 opt-in subprocess 與 S1–S11 隔離驗證。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from tests._nocap_subprocess import run_watched_subprocess

from tests.fixtures.ic_persist_redirect import REQUIRED_SEAM_IDS, RedirectPatchSet


FIXED_NODEIDS = (
    "tests/api/test_ic_run_selector.py::test_disambig_same_tf_different_hash",
    "tests/momentum/test_ic_filter_orchestrator.py::test_refilter_without_cache_raises",
    "tests/momentum/Analysis/test_long_short_analyzer.py::test_insufficient_ls_samples",
)
# 正向對照：模組層 usefixtures("ic_persist_redirect") 之 opt-in 測試，子行程內必啟用 ≥1 次
OPT_IN_CONTROL_NODEID = (
    "tests/momentum/Analysis/test_lightgbm_analyzer.py::test_validate_oot_single_class_returns_none_auc"
)

# 子行程啟動器：先把 RedirectPatchSet.activate／deactivate 包成「累計」計數（plugin 之
# get_activation_count 為即時旗標，fixture teardown 後恆 0，量不到「曾否啟用」），
# 再跑 pytest.main，結束時把累計啟用次數與 spy 違規寫到 argv[1]。
_CUMULATIVE_RUNNER = r"""
import json, sys
import pytest
import tests.fixtures.ic_persist_redirect as r

counts = {"activations": 0, "violations": []}
_orig_activate = r.RedirectPatchSet.activate
_orig_deactivate = r.RedirectPatchSet.deactivate

def _activate(self, root, *, owner):
    ctx = _orig_activate(self, root, owner=owner)
    counts["activations"] += 1
    return ctx

def _deactivate(self, ctx):
    counts["violations"].extend(ctx.spy.violations)
    return _orig_deactivate(self, ctx)

r.RedirectPatchSet.activate = _activate
r.RedirectPatchSet.deactivate = _deactivate
rc = pytest.main([sys.argv[2], "-q", "-p", "no:cacheprovider"])
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(counts, fh)
sys.exit(int(rc))
"""


def _run_cumulative(nodeid: str, out: Path, env: dict[str, str]) -> tuple[subprocess.CompletedProcess, dict]:
    completed = run_watched_subprocess(["venv/bin/python", "-c", _CUMULATIVE_RUNNER, str(out), nodeid], env=env)
    payload = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    return completed, payload


def test_non_opt_in_subprocesses_never_activate(tmp_path: Path) -> None:
    for index, nodeid in enumerate(FIXED_NODEIDS):
        probe = tmp_path / f"probe-{index}.json"
        env = os.environ.copy()
        env["IC_PERSIST_ASSERT_NO_ACTIVATION"] = "1"
        env["IC_PERSIST_PROBE_JSON"] = str(probe)
        completed = run_watched_subprocess(["venv/bin/python", "-m", "pytest", nodeid, "-q"], env=env)
        assert completed.returncode == 0, completed.stdout + completed.stderr
        payload = json.loads(probe.read_text(encoding="utf-8"))
        assert payload == {"activation_count": 0, "violations": []}

        # 累計計數：整個子行程期間 activate 從未被呼叫（非僅結束當下未啟用）
        run, cumulative = _run_cumulative(nodeid, tmp_path / f"cumulative-{index}.json", os.environ.copy())
        assert run.returncode == 0, run.stdout + run.stderr
        assert cumulative == {"activations": 0, "violations": []}, nodeid

    # 正向對照：同一量測對 opt-in 測試必量到啟用（證明上式 0 不是量測失靈）
    run, cumulative = _run_cumulative(OPT_IN_CONTROL_NODEID, tmp_path / "cumulative-control.json", os.environ.copy())
    assert run.returncode == 0, run.stdout + run.stderr
    assert cumulative["activations"] >= 1
    assert cumulative["violations"] == []


_PROBE_META = {"symbol": "PROBE", "timeframe": "1h"}


def _drive_seam(seam_id: str, production_prefix: Path) -> tuple[Path, ...]:
    """以 production 路徑實呼叫各 seam 之生產接點（經已安裝之 wrapper／module Path adapter），回傳落盤／解析路徑。

    cwd 須為 production_prefix 之父目錄，使生產碼之相對字面 ``data_cache/...`` 解析到 production_prefix。
    """
    import api.routes.ic_analysis as route_mod
    import api.services.ic_analysis_service as service_mod
    import tests.api.test_export_api as export_mod
    import tests.test_feature_factory_e2e as ff_test_mod
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_reporter import ICReporter
    from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer

    service_cls = service_mod.ICAnalysisService
    if seam_id == "S1":
        return (Path(ICFilterOrchestrator._resolve_filtered_path(object.__new__(ICFilterOrchestrator), _PROBE_META)),)
    if seam_id == "S2":
        reporter = ICReporter({"ai_summary": False})
        out_dir = str(production_prefix / "reports" / "probe")
        saved = reporter.save_report({}, out_dir, "probe")
        log_path = reporter.save_filter_log({}, out_dir, "probe")
        frame = pd.DataFrame(
            {"f": [1.0, 2.0]}, index=pd.date_range("2026-01-01", periods=2, freq="h", tz="UTC")
        )
        h5_path = reporter.save_filtered_features(frame, ["f"], str(production_prefix / "features" / "probe.h5"))
        return (Path(saved["json"]), Path(log_path), Path(h5_path))
    if seam_id == "S3":
        return (Path(service_cls._resolve_filtered_path(object.__new__(service_cls), _PROBE_META)),)
    if seam_id == "S4":
        # _materialize_features_for_ic 之快取目錄字面，經 service module 之 Path adapter
        return (Path(service_mod.Path("data_cache/reports/ic_ingest_cache")),)
    if seam_id == "S5":
        return (Path(service_cls._write_ic_meta_json(object.__new__(service_cls), "PROBE", "1h", "probe", [])),)
    if seam_id == "S6":
        # _apply_transforms_sync 之輸出目錄字面，經同一 module Path adapter
        return (Path(service_mod.Path("data_cache/reports")),)
    if seam_id == "S7":
        return (Path(route_mod._resolve_filtered_path(_PROBE_META)),)
    if seam_id == "S8":
        return (Path(route_mod.Path("data_cache/reports")),)
    if seam_id == "S9":
        return (Path(export_mod._export_fixture_filtered_path(_PROBE_META)),)
    if seam_id == "S10":
        model_path = str(production_prefix / "models" / "probe.pkl")
        return (
            Path(LightGBMAnalyzer._resolve_model_path(object.__new__(LightGBMAnalyzer), model_path)),
            Path(XGBoostAnalyzer._resolve_model_path(object.__new__(XGBoostAnalyzer), model_path)),
        )
    if seam_id == "S11":
        return (Path(ff_test_mod._create_e2e_factory()._storage.base_path),)
    raise AssertionError(f"未涵蓋之 seam：{seam_id}")


@pytest.mark.parametrize("seam_id", sorted(REQUIRED_SEAM_IDS, key=lambda item: int(item[1:])))
def test_all_seam_probes_stay_under_root(
    seam_id: str, redirect_patch_set: RedirectPatchSet, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    # 假 production 根（tmp 下）：對照組撤除 redirect 時之寫入只落 tmp；monkeypatch 測後還原 session 物件
    monkeypatch.setattr(redirect_patch_set, "production_prefix", (work / "data_cache").resolve())
    ctx = redirect_patch_set.activate(tmp_path / seam_id, owner=f"isolation-{seam_id}")
    try:
        outputs = redirect_patch_set.resolve_all()[seam_id].probe(ctx.redirect_root)
        assert all(path.resolve().is_relative_to(ctx.redirect_root) for path in outputs)
        assert not ctx.spy.violations

        # 實呼叫生產接點：落點須在 redirect root 下、且不在 production 下
        for path in _drive_seam(seam_id, redirect_patch_set.production_prefix):
            assert path.resolve().is_relative_to(ctx.redirect_root), (seam_id, path)
            assert not path.resolve().is_relative_to(redirect_patch_set.production_prefix), (seam_id, path)
        assert ctx.spy.violations == []

        # 對照（mutation）：撤除 redirect 後同一接點必不落 root（證明上式非構造恆真）
        monkeypatch.setenv("IC_PERSIST_REDIRECT_DISABLE", "1")
        if seam_id == "S9":
            with pytest.raises(RuntimeError, match="requires active ic_persist_redirect"):
                _drive_seam(seam_id, redirect_patch_set.production_prefix)
        else:
            for path in _drive_seam(seam_id, redirect_patch_set.production_prefix):
                assert path.resolve().is_relative_to(redirect_patch_set.production_prefix), (seam_id, path)
                assert not path.resolve().is_relative_to(ctx.redirect_root), (seam_id, path)
    finally:
        monkeypatch.delenv("IC_PERSIST_REDIRECT_DISABLE", raising=False)
        redirect_patch_set.deactivate(ctx)
