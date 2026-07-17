"""LA-1 B3 Task 3.2：五 oracle OOS-gate + missing_marker + B3-FIX/FIX2。

SPEC B3.1 oracle ①–⑤；唯一 exception = DegradedOOSViolation。
B3-FIX：CX-01 / H5-01 / TASK-01 / ENUM-01。
B3-FIX2：ENUM 全讀取點 / TEST 真 TestClient 鏈 / XFORM attr raise / G-C persist。
"""

from __future__ import annotations

import asyncio
import copy
from pathlib import Path
from typing import Any, Dict, List, Tuple

import h5py
import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from momentum.Analysis.ic_reporter import (
    DegradedOOSViolation,
    ICReporter,
    gate_ai_json_oos_text,
    gate_api_csv_carrier,
    gate_api_transforms_carrier,
    gate_filter_log_output_features,
    gate_hdf5_analysis_status_attr,
    gate_summary_table_pass_class,
    gate_task_payload_status,
    normalize_analysis_status,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _degraded_report(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "version": "1.0",
        "analysis_status": "degraded_full_sample",
        "oos_guarantees": False,
        "metadata": {
            "fit_mode": "full_sample",
            "oos_guarantees": False,
            "symbol": "BTCUSDT",
            "timeframe": "1h",
        },
        "summary_table": [
            {
                "feature_name": "feat_a",
                "icir": 0.5,
                "ic_mean": 0.02,
                "p_value": 0.01,
                "pass_class": "full_sample_research_only",
            },
            {
                "feature_name": "feat_b",
                "icir": 0.3,
                "ic_mean": 0.01,
                "p_value": 0.02,
                "pass_class": "full_sample_research_only",
            },
        ],
        "filter_log": {
            "stage5_thresholds": {
                "input_features": 2,
                "output_features": {
                    "count": 2,
                    "pass_class": "full_sample_research_only",
                },
                "pass_class": "full_sample_research_only",
                "removed_features": {},
            }
        },
    }
    base.update(overrides)
    return base


def _ok_report() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "analysis_status": "ok_oos",
        "oos_guarantees": True,
        "metadata": {"fit_mode": "train", "oos_guarantees": True},
        "summary_table": [
            {
                "feature_name": "feat_a",
                "icir": 0.5,
                "pass_class": "oos",
            }
        ],
        "filter_log": {
            "stage5_thresholds": {
                "output_features": {"count": 1, "pass_class": "oos"},
                "pass_class": "oos",
            }
        },
    }


@pytest.fixture()
def degraded_hdf5(tmp_path: Path) -> Path:
    path = tmp_path / "filtered_degraded.h5"
    with h5py.File(path, "w") as handle:
        grp = handle.create_group("filtered")
        grp.create_dataset("features", data=np.zeros((4, 1), dtype=np.float32))
        grp.attrs["analysis_status"] = "degraded_full_sample"
        handle.attrs["analysis_status"] = "degraded_full_sample"
        handle.attrs["oos_guarantees"] = False
    return path


@pytest.fixture()
def missing_attr_hdf5(tmp_path: Path) -> Path:
    path = tmp_path / "filtered_no_attr.h5"
    with h5py.File(path, "w") as handle:
        grp = handle.create_group("filtered")
        grp.create_dataset("features", data=np.zeros((4, 1), dtype=np.float32))
        # intentionally no analysis_status
    return path


# ---------------------------------------------------------------------------
# Oracle ① summary_table pass_class
# ---------------------------------------------------------------------------
def test_summary_table_pass_class_gate() -> None:
    report = _degraded_report()
    gate_summary_table_pass_class(report)  # no raise


def test_summary_table_pass_class_missing_marker() -> None:
    report = _degraded_report()
    for row in report["summary_table"]:
        row.pop("pass_class", None)
    with pytest.raises(DegradedOOSViolation):
        gate_summary_table_pass_class(report)


# ---------------------------------------------------------------------------
# Oracle ② filter_log.stage5_thresholds.output_features
# ---------------------------------------------------------------------------
def test_filter_log_output_features_gate() -> None:
    report = _degraded_report()
    gate_filter_log_output_features(report)


def test_filter_log_output_features_missing_marker() -> None:
    report = _degraded_report()
    report["filter_log"]["stage5_thresholds"]["output_features"] = 2  # bare count, no marker
    report["filter_log"]["stage5_thresholds"].pop("pass_class", None)
    with pytest.raises(DegradedOOSViolation):
        gate_filter_log_output_features(report)


# ---------------------------------------------------------------------------
# Oracle ③ HDF5 attr
# ---------------------------------------------------------------------------
def test_hdf5_attr_gate(degraded_hdf5: Path) -> None:
    gate_hdf5_analysis_status_attr(degraded_hdf5, expect_degraded=True)


def test_hdf5_attr_missing_marker(missing_attr_hdf5: Path) -> None:
    with pytest.raises(DegradedOOSViolation):
        gate_hdf5_analysis_status_attr(missing_attr_hdf5, expect_degraded=True)


# ---------------------------------------------------------------------------
# Oracle ④ generate_ai_json top_features OOS text
# ---------------------------------------------------------------------------
def test_ai_json_oos_text_gate() -> None:
    report = _degraded_report()
    reporter = ICReporter({})
    payload = reporter.generate_ai_json(report)
    assert payload.get("research_only") is True
    assert payload.get("analysis_status") == "degraded_full_sample"
    gate_ai_json_oos_text(payload, report)


def test_ai_json_oos_text_missing_marker() -> None:
    """degraded report 但 AI payload 冒充 OOS / 缺 research-only。"""
    report = _degraded_report()
    bad_payload = {
        "analysis_status": "ok_oos",  # 冒充
        "research_only": False,
        "top_features": [
            {
                "feature_name": "feat_a",
                "icir": 0.5,
                "pass_class": "oos",
            }
        ],
        "key_findings": ["oos-passed"],
    }
    with pytest.raises(DegradedOOSViolation):
        gate_ai_json_oos_text(bad_payload, report)


# ---------------------------------------------------------------------------
# Oracle ⑤ API carriers (HDF5 / CSV / transforms) + task payload
# ---------------------------------------------------------------------------
def test_api_hdf5_carrier(degraded_hdf5: Path, tmp_path: Path) -> None:
    """HDF5 FileResponse 路徑：檔內 attr 即 carrier（route 透傳檔案）。"""
    # writer 路徑：ICReporter.save_filtered_features 必寫 attr
    reporter = ICReporter({})
    import pandas as pd

    df = pd.DataFrame({"feat_a": [1.0, 2.0, 3.0]})
    out = tmp_path / "written.h5"
    reporter.save_filtered_features(
        df,
        ["feat_a"],
        str(out),
        analysis_status="degraded_full_sample",
        oos_guarantees=False,
    )
    gate_hdf5_analysis_status_attr(out, expect_degraded=True)
    # 既有 degraded fixture 亦過
    gate_hdf5_analysis_status_attr(degraded_hdf5, expect_degraded=True)


def test_api_hdf5_carrier_missing_marker(missing_attr_hdf5: Path) -> None:
    with pytest.raises(DegradedOOSViolation):
        gate_hdf5_analysis_status_attr(missing_attr_hdf5, expect_degraded=True)


def test_api_csv_carrier() -> None:
    body = "# analysis_status=degraded_full_sample\nfeat_a\n1.0\n"
    headers = {"X-Analysis-Status": "degraded_full_sample"}
    gate_api_csv_carrier(
        headers=headers,
        body=body,
        report=_degraded_report(),
        expect_degraded=True,
    )


def test_api_csv_carrier_missing_marker() -> None:
    body = "feat_a\n1.0\n"  # no comment
    headers = {}  # no header
    with pytest.raises(DegradedOOSViolation):
        gate_api_csv_carrier(
            headers=headers,
            body=body,
            report=_degraded_report(),
            expect_degraded=True,
        )


def test_api_transforms_carrier(tmp_path: Path) -> None:
    path = tmp_path / "post_ic_transforms_t1.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("features", data=np.zeros((2, 1), dtype=np.float32))
        handle.attrs["analysis_status"] = "degraded_full_sample"
    response = {
        "task_id": "t1",
        "selected_feature_count": 1,
        "transforms_applied": ["rank"],
        "output_path": str(path),
        "output_rows": 2,
        "output_cols": 1,
        "analysis_status": "degraded_full_sample",
        "oos_guarantees": False,
    }
    gate_api_transforms_carrier(response, hdf5_path=path, expect_degraded=True)


def test_api_transforms_carrier_missing_marker(tmp_path: Path) -> None:
    path = tmp_path / "post_ic_transforms_bad.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("features", data=np.zeros((2, 1), dtype=np.float32))
        # no attr
    response = {
        "task_id": "t1",
        "output_path": str(path),
        # missing analysis_status on response
    }
    with pytest.raises(DegradedOOSViolation):
        gate_api_transforms_carrier(response, hdf5_path=path, expect_degraded=True)


def test_task_payload_status() -> None:
    report = _degraded_report()
    gate_task_payload_status(report)
    gate_task_payload_status({"result": report, "status": "completed"})


def test_task_payload_status_missing_marker() -> None:
    bad = {"summary_table": [], "metadata": {}}  # no root 紅標
    with pytest.raises(DegradedOOSViolation):
        gate_task_payload_status(bad)


# ---------------------------------------------------------------------------
# B3-FIX negatives（Codex BLOCKING B3-CX/H5/TASK/ENUM）
# ---------------------------------------------------------------------------
def test_b3_cx01_cross_sectional_report_has_root_status() -> None:
    """B3-CX-01：analyze_cross_sectional 真路徑必有 root analysis_status/oos/pass_class。"""
    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    timestamps = pd.date_range("2020-01-01", periods=40, freq="12h")
    symbols = ["BTCUSDT", "ETHUSDT"]
    index = pd.MultiIndex.from_product(
        [timestamps, symbols], names=["timestamp", "_symbol"]
    )
    rng = np.random.default_rng(0)
    features = pd.DataFrame(
        {
            "alpha": rng.normal(size=len(index)).astype(np.float32),
            "return_1": rng.normal(size=len(index)).astype(np.float32),
        },
        index=index,
    )
    orch = ICFilterOrchestrator(load_ic_config())
    # 有 split → ok_oos；無 fallback 但仍必標 root
    report = orch.analyze_cross_sectional(
        features,
        timeframe="12h",
        config_override={
            "ic_train_test_split": True,
            "min_test_rows": 5,
            "oos_test_size": 0.25,
            "embargo": 0,
        },
    )
    assert "analysis_status" in report
    assert "oos_guarantees" in report
    assert report["analysis_status"] in {"ok_oos", "degraded_full_sample"}
    for row in report.get("summary_table") or []:
        assert "pass_class" in row
    # 負例：剝掉 root 後 gate 必 raise
    stripped = dict(report)
    stripped.pop("analysis_status", None)
    stripped.pop("oos_guarantees", None)
    with pytest.raises(DegradedOOSViolation):
        gate_task_payload_status(stripped)


def test_b3_h501_export_rejects_stale_or_empty_filtered(tmp_path: Path) -> None:
    """B3-H5-01：當次 filtered 空 / provenance 不符 → 拒 stable-path 舊檔。"""
    from momentum.Analysis.ic_reporter import assert_filtered_export_fresh

    stale = tmp_path / "BTCUSDT_1h_filtered.h5"
    with h5py.File(stale, "w") as handle:
        grp = handle.create_group("filtered")
        grp.create_dataset("features", data=np.zeros((4, 1), dtype=np.float32))
        handle.attrs["source_generated_at"] = "2020-01-01T00:00:00"
        handle.attrs["analysis_status"] = "ok_oos"

    # 1) 當次 empty filtered → written=False → 拒
    empty_run = {
        "generated_at": "2026-07-16T12:00:00",
        "metadata": {"filtered_features_written": False, "symbol": "BTCUSDT", "timeframe": "1h"},
    }
    with pytest.raises(FileNotFoundError, match="empty for this run|refuse stale"):
        assert_filtered_export_fresh(empty_run, stale)

    # 2) 當次有 generated_at 但檔案是上一輪 → stale
    current_run = {
        "generated_at": "2026-07-16T12:00:00",
        "metadata": {
            "filtered_features_written": True,
            "filtered_generated_at": "2026-07-16T12:00:00",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
        },
    }
    with pytest.raises(FileNotFoundError, match="stale"):
        assert_filtered_export_fresh(current_run, stale)

    # 3) 缺 provenance → 拒
    no_prov = {"metadata": {"filtered_features_written": True}}
    with pytest.raises(FileNotFoundError, match="provenance missing"):
        assert_filtered_export_fresh(no_prov, stale)

    # 正例：stamp 對得上 → 過
    with h5py.File(stale, "w") as handle:
        grp = handle.create_group("filtered")
        grp.create_dataset("features", data=np.zeros((4, 1), dtype=np.float32))
        handle.attrs["source_generated_at"] = "2026-07-16T12:00:00"
    assert assert_filtered_export_fresh(current_run, stale) == stale


def test_b3_task01_completion_callback_payload_requires_status() -> None:
    """B3-TASK-01：completion callback 形狀缺 analysis_status/oos → DegradedOOSViolation。"""
    # 修前的兩處 payload 形狀（僅 stage/status，無紅標）
    bare_completed = {
        "task_id": "t1",
        "stage": "completed",
        "progress": 1.0,
        "message": "completed",
        "status": "completed",
    }
    with pytest.raises(DegradedOOSViolation):
        gate_task_payload_status(bare_completed)

    bare_full = {
        "task_id": "t1",
        "stage": "completed",
        "current_step": "completed",
        "progress": 1.0,
        "message": "full analysis completed",
        "status": "completed",
    }
    with pytest.raises(DegradedOOSViolation):
        gate_task_payload_status(bare_full)

    # 正例：補齊 root 紅標
    ok_payload = {
        **bare_completed,
        "analysis_status": "ok_oos",
        "oos_guarantees": True,
    }
    gate_task_payload_status(ok_payload)
    degraded_payload = {
        **bare_full,
        "analysis_status": "degraded_full_sample",
        "oos_guarantees": False,
    }
    gate_task_payload_status(degraded_payload)


def test_b3_enum01_unknown_or_missing_status_is_degraded() -> None:
    """B3-ENUM-01：缺失/未知 status fail-closed 當 degraded（禁 default ok_oos）。"""
    from momentum.Analysis.ic_reporter import (
        _is_degraded,
        normalize_analysis_status,
        gate_summary_table_pass_class,
    )

    assert normalize_analysis_status(None) == "degraded_full_sample"
    assert normalize_analysis_status("") == "degraded_full_sample"
    assert normalize_analysis_status("weird_status") == "degraded_full_sample"
    assert normalize_analysis_status("ok_oos") == "ok_oos"
    assert normalize_analysis_status("degraded_full_sample") == "degraded_full_sample"

    assert _is_degraded({}) is True  # missing
    assert _is_degraded({"analysis_status": "unknown_xyz"}) is True
    assert _is_degraded({"analysis_status": "ok_oos"}) is False
    assert _is_degraded(None) is True

    # 未知 status 的 report 走 degraded gate → 缺 pass_class 必 raise
    unknown_report = {
        "analysis_status": "totally_unknown",
        "oos_guarantees": True,  # 即便 oos 旗標 True 也不能宣稱 OOS
        "summary_table": [{"feature_name": "a", "icir": 0.1}],  # 無 pass_class
    }
    assert _is_degraded(unknown_report) is True
    with pytest.raises(DegradedOOSViolation):
        gate_summary_table_pass_class(unknown_report)

    # missing status 同 fail-closed
    missing_report = {
        "summary_table": [{"feature_name": "a", "pass_class": "oos"}],
    }
    with pytest.raises(DegradedOOSViolation):
        gate_summary_table_pass_class(missing_report)


# ---------------------------------------------------------------------------
# B3-FIX2：ENUM 三讀取點 + 真 TestClient 鏈 + XFORM raise + G-C persist
# ---------------------------------------------------------------------------
_TASK_ID = "la1-b3-fix2-degraded"


class _FakeAnalyzer:
    """最小 analyzer：export-csv 讀 filtered features。"""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def get_filtered_features(self) -> pd.DataFrame:
        return self._df.copy()


@pytest.fixture()
def degraded_task_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """構造 degraded completed task，注入 singleton service（真 API 鏈）。"""
    from api.routes.ic_analysis import router
    from api.services.ic_analysis_service import ic_analysis_service

    features_path = tmp_path / "features_for_transforms.h5"
    df = pd.DataFrame({"feat_a": [1.0, 2.0, 3.0, 4.0, 5.0]})
    df.to_hdf(str(features_path), key="features", mode="w")

    report = _degraded_report()
    analyzer = _FakeAnalyzer(df)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    original_tasks = dict(ic_analysis_service._tasks)
    original_last = ic_analysis_service._last_task_id
    original_callbacks = dict(ic_analysis_service._callbacks)

    ic_analysis_service._tasks = {
        _TASK_ID: {
            "task_id": _TASK_ID,
            "status": "completed",
            "progress": 1.0,
            "error": None,
            "result": copy.deepcopy(report),
            "analyzer": analyzer,
            "req_features_path": str(features_path),
            "req_symbol": "BTCUSDT",
            "req_timeframe": "1h",
            "req_config_hash": None,
        }
    }
    ic_analysis_service._last_task_id = _TASK_ID
    ic_analysis_service._callbacks = {_TASK_ID: []}

    # transforms 輸出導 tmp（chdir + 相對 data_cache/reports）
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data_cache" / "reports").mkdir(parents=True, exist_ok=True)

    try:
        yield {
            "client": client,
            "service": ic_analysis_service,
            "task_id": _TASK_ID,
            "report": report,
            "tmp_path": tmp_path,
            "features_path": features_path,
        }
    finally:
        ic_analysis_service._tasks = original_tasks
        ic_analysis_service._last_task_id = original_last
        ic_analysis_service._callbacks = original_callbacks


def test_b3_enum01_read_points_fail_closed_reporter_route_service(
    degraded_task_env: Dict[str, Any],
) -> None:
    """B3-ENUM-01：三讀取點（reporter/route/service）非字面 ok_oos → degraded。"""
    # --- reporter generate_ai_json ---
    reporter = ICReporter({})
    missing = {"summary_table": [], "version": "1.0"}  # 無 analysis_status
    ai = reporter.generate_ai_json(missing)
    assert ai["analysis_status"] == "degraded_full_sample"
    assert ai["research_only"] is True
    assert ai["analysis_status"] != "ok_oos"

    unknown = {"analysis_status": "weird", "summary_table": []}
    ai2 = reporter.generate_ai_json(unknown)
    assert ai2["analysis_status"] == "degraded_full_sample"

    # non-dict report → degraded（禁 default ok_oos）
    ai3 = reporter.generate_ai_json({})  # empty dict still missing status
    assert normalize_analysis_status(None) == "degraded_full_sample"
    assert ai3["analysis_status"] == "degraded_full_sample"

    # --- route CSV（真 TestClient）---
    client: TestClient = degraded_task_env["client"]
    tid = degraded_task_env["task_id"]
    # 缺 status 的 task
    from api.services.ic_analysis_service import ic_analysis_service

    bare = copy.deepcopy(ic_analysis_service._tasks[tid])
    bare["result"] = {"summary_table": [], "metadata": {}}  # missing status
    ic_analysis_service._tasks[tid] = bare
    resp = client.get(f"/api/v1/ic/export-csv/{tid}")
    assert resp.status_code == 200
    assert resp.headers.get("X-Analysis-Status") == "degraded_full_sample"
    assert resp.text.splitlines()[0].startswith("# analysis_status=degraded_full_sample")
    assert "ok_oos" not in resp.headers.get("X-Analysis-Status", "")

    # unknown status on route
    bare2 = copy.deepcopy(bare)
    bare2["result"] = {"analysis_status": "totally_unknown"}
    ic_analysis_service._tasks[tid] = bare2
    resp2 = client.get(f"/api/v1/ic/export-csv/{tid}")
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Analysis-Status") == "degraded_full_sample"

    # restore degraded for subsequent tests in fixture lifetime
    ic_analysis_service._tasks[tid] = {
        **bare,
        "result": copy.deepcopy(degraded_task_env["report"]),
        "analyzer": bare["analyzer"],
        "req_features_path": bare["req_features_path"],
    }

    # --- service get_task_status + transforms normalize ---
    status = ic_analysis_service.get_task_status(tid)
    assert status is not None
    assert status["analysis_status"] == "degraded_full_sample"
    assert status["oos_guarantees"] is False

    # inject unknown → still degraded on task status
    ic_analysis_service._tasks[tid]["result"] = {
        "analysis_status": "not_a_real_status",
        "oos_guarantees": True,
    }
    status2 = ic_analysis_service.get_task_status(tid)
    assert status2 is not None
    assert status2["analysis_status"] == "degraded_full_sample"
    ic_analysis_service._tasks[tid]["result"] = copy.deepcopy(
        degraded_task_env["report"]
    )


def test_b3_test01_routes_service_callback_real_chain(
    degraded_task_env: Dict[str, Any],
) -> None:
    """B3-TEST-01：routes/service/callback 各一條走真實 TestClient 請求鏈。"""
    client: TestClient = degraded_task_env["client"]
    service = degraded_task_env["service"]
    tid = degraded_task_env["task_id"]

    # 1) routes：export-csv
    resp = client.get(f"/api/v1/ic/export-csv/{tid}")
    assert resp.status_code == 200
    assert resp.headers.get("X-Analysis-Status") == "degraded_full_sample"
    assert "# analysis_status=degraded_full_sample" in resp.text
    gate_api_csv_carrier(
        headers=dict(resp.headers),
        body=resp.text,
        report=degraded_task_env["report"],
        expect_degraded=True,
    )

    # 2) routes/service：task status
    st = client.get(f"/api/v1/ic/task/{tid}")
    assert st.status_code == 200
    body = st.json()
    assert body["analysis_status"] == "degraded_full_sample"
    assert body["oos_guarantees"] is False
    gate_task_payload_status(body)

    # 3) service apply_transforms（真 service 同步路徑 + response carrier）
    import asyncio

    xform = asyncio.get_event_loop().run_until_complete(
        service.apply_transforms(
            task_id=tid,
            selected_features=["feat_a"],
            rank=True,
            zscore=False,
            gaussian=False,
        )
    )
    assert xform["analysis_status"] == "degraded_full_sample"
    assert xform["oos_guarantees"] is False
    out = Path(xform["output_path"])
    assert out.is_file()
    gate_api_transforms_carrier(xform, hdf5_path=out, expect_degraded=True)
    gate_hdf5_analysis_status_attr(out, expect_degraded=True)

    # 4) callback：completion payload 必含紅標（模擬 notify 後 shape）
    captured: List[Dict[str, Any]] = []

    def _cb(payload: Dict[str, Any]) -> None:
        captured.append(dict(payload))

    # 註冊 callback 後走 _notify_callbacks（completion 同形狀）
    with service._lock:
        service._callbacks.setdefault(tid, []).append(_cb)
    completed_payload = {
        "task_id": tid,
        "stage": "completed",
        "progress": 1.0,
        "message": "completed",
        "status": "completed",
        "analysis_status": normalize_analysis_status("degraded_full_sample"),
        "oos_guarantees": False,
    }
    service._notify_callbacks(tid, completed_payload)
    assert captured, "callback must receive completion payload"
    gate_task_payload_status(captured[-1])
    assert captured[-1]["analysis_status"] == "degraded_full_sample"


def test_b3_test01_gc_persisted_output_has_status() -> None:
    """B3-TEST-01 G-C：annotate 後 persist 的 filtered HDF5 必含 analysis_status。"""
    from momentum.factories import create_ic_analyzer, create_kline_storage_manager
    from tests.golden.la1.gen_baseline import _isolate_orchestrator_persist

    inputs = Path("tests/golden/la1/inputs")
    features_path = inputs / (
        "BTCUSDT_1h_4a8a0b3726cc906ab3534994605e77f5_fallback_tail100.h5"
    )
    meta_path = inputs / (
        "BTCUSDT_1h_4a8a0b3726cc906ab3534994605e77f5_fallback_tail100_meta.json"
    )
    assert features_path.is_file(), features_path
    assert meta_path.is_file(), meta_path

    orch = create_ic_analyzer()
    side = _isolate_orchestrator_persist(orch)
    written: List[Path] = []
    orig = orch._reporter.save_filtered_features

    def _capture(features_df, selected_features, output_path, **kwargs):
        path = orig(features_df, selected_features, output_path, **kwargs)
        written.append(Path(path))
        # G-C 時序：寫入當下 kwargs 必已有 analysis_status（非先寫後補）
        assert kwargs.get("analysis_status") is not None
        assert kwargs.get("analysis_status") == "degraded_full_sample"
        return path

    orch._reporter.save_filtered_features = _capture  # type: ignore[method-assign]
    kline_reader = create_kline_storage_manager(cache_dir="data_cache/feature_klines")

    report = orch.analyze(
        features_path=str(features_path.resolve()),
        labels_path="",
        meta_path=str(meta_path.resolve()),
        config_override={
            "ic_train_test_split": True,
            "min_test_rows": 10_000,
            "thresholds": {
                "ic_mean_min": -1.0,
                "icir_min": -1.0,
                "p_value_max": 1.0,
                "ic_hit_rate_min": 0.0,
                "monotonicity_score_min": 0.0,
                "coverage_min": 0.0,
                "long_short_spread": {"enabled": False},
            },
            "grouped_analysis": {"by_regime": False},
            "report": {"include_regime_analysis": False},
        },
        kline_reader=kline_reader,
    )
    assert report.get("analysis_status") == "degraded_full_sample"
    assert written, "expected filtered HDF5 persist after annotate"
    for p in written:
        gate_hdf5_analysis_status_attr(p, expect_degraded=True)
    assert side.exists()


def test_b3_xform01_attr_write_failure_raises(
    degraded_task_env: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """B3-XFORM-01：transforms HDF5 attr 寫失敗 → DegradedOOSViolation（禁吞 success）。"""
    service = degraded_task_env["service"]
    tid = degraded_task_env["task_id"]

    import h5py as h5py_mod

    real_file = h5py_mod.File

    class _BoomFile:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise OSError("simulated attr write failure")

        def __enter__(self) -> Any:
            raise OSError("simulated attr write failure")

        def __exit__(self, *args: Any) -> None:
            return None

    def _file_side_effect(name: Any, mode: str = "r", *args: Any, **kwargs: Any):
        # to_hdf 可能不走 h5py.File；僅 "a" mode（attr 補寫）炸
        if mode == "a":
            raise OSError("simulated attr write failure")
        return real_file(name, mode, *args, **kwargs)

    monkeypatch.setattr(h5py_mod, "File", _file_side_effect)

    import asyncio

    with pytest.raises(DegradedOOSViolation, match="analysis_status attr"):
        asyncio.get_event_loop().run_until_complete(
            service.apply_transforms(
                task_id=tid,
                selected_features=["feat_a"],
                rank=True,
                zscore=False,
                gaussian=False,
            )
        )


# ---------------------------------------------------------------------------
# B3-TEST-01：completion callback 真鏈（_run_analysis / _run_full_analysis）
# 規格：handoffs/LA1-B3TEST01-COMMITTEE-SYNTHESIS.md（零自由度）
# ---------------------------------------------------------------------------
_LA1_INPUTS = Path("tests/golden/la1/inputs")
_LA1_BTC_HASH = "4a8a0b3726cc906ab3534994605e77f5"
_LA1_TAIL100_STEM = f"BTCUSDT_1h_{_LA1_BTC_HASH}_fallback_tail100"
_LA1_TAIL2000_STEM = f"BTCUSDT_1h_{_LA1_BTC_HASH}_strat_p3r12_a0_tail2000"


def _la1_degraded_config_override() -> Dict[str, Any]:
    """與 test_b3_test01_gc_persisted_output_has_status 對齊的 degraded override。"""
    return {
        "ic_train_test_split": True,
        "min_test_rows": 10_000,
        "thresholds": {
            "ic_mean_min": -1.0,
            "icir_min": -1.0,
            "p_value_max": 1.0,
            "ic_hit_rate_min": 0.0,
            "monotonicity_score_min": 0.0,
            "coverage_min": 0.0,
            "long_short_spread": {"enabled": False},
        },
        "grouped_analysis": {"by_regime": False},
        "report": {"include_regime_analysis": False},
    }


def _la1_ok_config_override() -> Dict[str, Any]:
    """tail2000 → ok_oos；min_test_rows 放寬至可 OOS split。"""
    cfg = _la1_degraded_config_override()
    cfg["min_test_rows"] = 5
    return cfg


def _require_la1_pair(stem: str) -> Tuple[Path, Path]:
    features = _LA1_INPUTS / f"{stem}.h5"
    meta = _LA1_INPUTS / f"{stem}_meta.json"
    if not features.is_file():
        pytest.fail(f"LA1 B0 input missing: {features} (run gen_baseline first)")
    if not meta.is_file():
        pytest.fail(f"LA1 B0 meta missing: {meta}")
    return features, meta


def _write_real_labels_for_features(features_path: Path, out_path: Path) -> Path:
    """由真 kline + create_label_generator 物化 labels HDF5（path B 用；禁合成值）。"""
    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.factories import create_kline_storage_manager, create_label_generator

    with h5py.File(features_path, "r") as handle:
        group = handle["BTCUSDT"]["1h"]
        timestamps = np.asarray(group["timestamps"][:], dtype=np.int64)

    storage = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
    kline = storage.read_klines("BTCUSDT", "1h", validate_continuity=False)
    if kline is None or kline.empty or "close" not in kline.columns:
        pytest.fail("requires_kline: BTCUSDT/1h unavailable for label materialization")

    # kline 常以 RangeIndex + timestamp 欄；對齊必須用 timestamp 值而非 0..n
    if "timestamp" in kline.columns:
        close_index = pd.Index(
            np.asarray(kline["timestamp"].to_numpy(), dtype=np.int64),
            name="timestamp",
        )
    else:
        close_index = pd.Index(
            np.asarray(kline.index.to_numpy(), dtype=np.int64),
            name="timestamp",
        )
    close = pd.Series(kline["close"].to_numpy(copy=False), index=close_index)
    ic_cfg = load_ic_config()
    horizon = int(ic_cfg.global_settings.default_horizon)
    label_series = create_label_generator().generate_returns_by_type(
        close, horizon, ic_cfg.labels.return_type
    )
    aligned = label_series.reindex(pd.Index(timestamps, name="timestamp"))
    if int(aligned.notna().sum()) < 10:
        pytest.fail(
            f"label alignment too sparse: finite={int(aligned.notna().sum())}/{len(aligned)}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(out_path, "w") as handle:
        grp = handle.create_group("data")
        grp.create_dataset(
            "labels",
            data=aligned.to_numpy(dtype=np.float64).reshape(-1, 1),
            compression="gzip",
        )
        grp.create_dataset("timestamps", data=timestamps, compression="gzip")
        dtype = h5py.string_dtype(encoding="utf-8")
        grp.create_dataset(
            "label_names",
            data=np.asarray([f"return_{horizon}"], dtype=object),
            dtype=dtype,
        )
    return out_path


def _prefill_task(service: Any, task_id: str) -> None:
    service._tasks[task_id] = {
        "task_id": task_id,
        "status": "running",
        "progress": 0.0,
        "current_stage": None,
        "current_step": None,
        "error": None,
        "result": None,
        "deep_analysis_result": None,
    }


def _completed_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("status") == "completed"]


def _assert_callback_task_mirror(
    service: Any,
    task_id: str,
    payload: Dict[str, Any],
    *,
    expect_status: str,
    expect_oos: bool,
) -> None:
    gate_task_payload_status(payload)
    assert payload.get("analysis_status") == expect_status
    assert payload.get("oos_guarantees") is expect_oos
    assert payload.get("status") == "completed"
    assert payload.get("progress") == 1.0
    assert payload.get("task_id") == task_id

    task_info = service._tasks[task_id]
    assert task_info["status"] == "completed"
    assert task_info.get("error") is None
    result = task_info.get("result")
    assert isinstance(result, dict)
    assert result.get("analysis_status") == payload.get("analysis_status")
    assert bool(result.get("oos_guarantees")) is bool(payload.get("oos_guarantees"))


@pytest.mark.asyncio
async def test_callback_completion_degraded_real_chain_a() -> None:
    """Path A：真 _run_analysis + fallback_tail100 → degraded completion callback。"""
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer
    from tests.golden.la1.gen_baseline import _isolate_orchestrator_persist

    features, meta = _require_la1_pair(_LA1_TAIL100_STEM)
    cfg = _la1_degraded_config_override()
    service = ICAnalysisService()
    task_id = "b3-cb-chain-a-degraded"
    analyzer = create_ic_analyzer(cfg)
    _isolate_orchestrator_persist(analyzer)
    _prefill_task(service, task_id)

    recorded: List[Dict[str, Any]] = []

    def _recorder(payload: Dict[str, Any]) -> None:
        recorded.append(dict(payload))

    service.register_notification_callback(task_id, _recorder)
    request = ICAnalyzeRequest(
        features_path=str(features.resolve()),
        meta_path=str(meta.resolve()),
        labels_path="",
        config_override=cfg,
    )
    await asyncio.wait_for(
        service._run_analysis(task_id, analyzer, request, cfg),
        timeout=120,
    )
    await asyncio.sleep(0)

    completed = _completed_events(recorded)
    assert len(completed) == 1, (
        f"completion callback never fired — payload assembly or notify regression; "
        f"events={[e.get('status') for e in recorded]} "
        f"task={service._tasks.get(task_id)}"
    )
    assert completed[0].get("message") == "completed"
    _assert_callback_task_mirror(
        service,
        task_id,
        completed[0],
        expect_status="degraded_full_sample",
        expect_oos=False,
    )

    service.unregister_notification_callback(task_id, _recorder)
    assert task_id not in service._callbacks


@pytest.mark.asyncio
async def test_callback_completion_ok_real_chain_a() -> None:
    """Path A：真 _run_analysis + tail2000 → ok_oos completion callback。"""
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer
    from tests.golden.la1.gen_baseline import _isolate_orchestrator_persist

    features, meta = _require_la1_pair(_LA1_TAIL2000_STEM)
    cfg = _la1_ok_config_override()
    service = ICAnalysisService()
    task_id = "b3-cb-chain-a-ok"
    analyzer = create_ic_analyzer(cfg)
    _isolate_orchestrator_persist(analyzer)
    _prefill_task(service, task_id)

    recorded: List[Dict[str, Any]] = []

    def _recorder(payload: Dict[str, Any]) -> None:
        recorded.append(dict(payload))

    service.register_notification_callback(task_id, _recorder)
    request = ICAnalyzeRequest(
        features_path=str(features.resolve()),
        meta_path=str(meta.resolve()),
        labels_path="",
        config_override=cfg,
    )
    await asyncio.wait_for(
        service._run_analysis(task_id, analyzer, request, cfg),
        timeout=180,
    )
    await asyncio.sleep(0)

    completed = _completed_events(recorded)
    assert len(completed) == 1, (
        f"completion callback never fired — payload assembly or notify regression; "
        f"events={[e.get('status') for e in recorded]} "
        f"task={service._tasks.get(task_id)}"
    )
    assert completed[0].get("message") == "completed"
    _assert_callback_task_mirror(
        service,
        task_id,
        completed[0],
        expect_status="ok_oos",
        expect_oos=True,
    )

    service.unregister_notification_callback(task_id, _recorder)
    assert task_id not in service._callbacks


@pytest.mark.asyncio
async def test_callback_completion_degraded_real_chain_b(tmp_path: Path) -> None:
    """Path B：真 _run_full_analysis + tail100 + 真 labels → degraded completion。"""
    from api.models.ic_models import ICFullAnalysisRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer
    from tests.golden.la1.gen_baseline import _isolate_orchestrator_persist

    features, meta = _require_la1_pair(_LA1_TAIL100_STEM)
    labels_path = _write_real_labels_for_features(
        features, tmp_path / "labels_tail100.h5"
    )
    cfg = _la1_degraded_config_override()
    service = ICAnalysisService()
    task_id = "b3-cb-chain-b-degraded"
    analyzer = create_ic_analyzer(cfg)
    _isolate_orchestrator_persist(analyzer)
    _prefill_task(service, task_id)

    recorded: List[Dict[str, Any]] = []

    def _recorder(payload: Dict[str, Any]) -> None:
        recorded.append(dict(payload))

    service.register_notification_callback(task_id, _recorder)
    request = ICFullAnalysisRequest(
        features_path=str(features.resolve()),
        meta_path=str(meta.resolve()),
        labels_path=str(labels_path.resolve()),
        deep_analysis=False,
        config_override=cfg,
    )
    await asyncio.wait_for(
        service._run_full_analysis(task_id, analyzer, request, cfg),
        timeout=120,
    )
    await asyncio.sleep(0)

    completed = _completed_events(recorded)
    assert len(completed) == 1, (
        f"completion callback never fired — payload assembly or notify regression; "
        f"events={[e.get('status') for e in recorded]} "
        f"task={service._tasks.get(task_id)}"
    )
    assert completed[0].get("message") == "full analysis completed"
    assert completed[0].get("current_step") == "completed"
    _assert_callback_task_mirror(
        service,
        task_id,
        completed[0],
        expect_status="degraded_full_sample",
        expect_oos=False,
    )

    service.unregister_notification_callback(task_id, _recorder)
    assert task_id not in service._callbacks


@pytest.mark.asyncio
async def test_callback_payload_missing_status_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """負例：payload 組裝丟 analysis_status → gate_task_payload_status 必 raise。

    以 notify 邊界 strip 模擬「completion 組裝漏欄」mutant；gate 在 callback 外呼叫
    （_notify_callbacks 會吞 callback 內 exception）。
    """
    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.factories import create_ic_analyzer
    from tests.golden.la1.gen_baseline import _isolate_orchestrator_persist

    features, meta = _require_la1_pair(_LA1_TAIL100_STEM)
    cfg = _la1_degraded_config_override()
    service = ICAnalysisService()
    task_id = "b3-cb-missing-status"
    analyzer = create_ic_analyzer(cfg)
    _isolate_orchestrator_persist(analyzer)
    _prefill_task(service, task_id)

    recorded: List[Dict[str, Any]] = []

    def _recorder(payload: Dict[str, Any]) -> None:
        recorded.append(dict(payload))

    service.register_notification_callback(task_id, _recorder)

    real_notify = service._notify_callbacks

    def _mutant_notify(tid: str, payload: Dict[str, Any]) -> None:
        mutated = dict(payload)
        if mutated.get("status") == "completed":
            mutated.pop("analysis_status", None)
        real_notify(tid, mutated)

    monkeypatch.setattr(service, "_notify_callbacks", _mutant_notify)

    request = ICAnalyzeRequest(
        features_path=str(features.resolve()),
        meta_path=str(meta.resolve()),
        labels_path="",
        config_override=cfg,
    )
    await asyncio.wait_for(
        service._run_analysis(task_id, analyzer, request, cfg),
        timeout=120,
    )
    await asyncio.sleep(0)

    completed = _completed_events(recorded)
    assert len(completed) == 1, (
        f"expected stripped completed payload; events={[e.get('status') for e in recorded]}"
    )
    assert "analysis_status" not in completed[0]
    with pytest.raises(DegradedOOSViolation):
        gate_task_payload_status(completed[0])

    service.unregister_notification_callback(task_id, _recorder)
    assert task_id not in service._callbacks
