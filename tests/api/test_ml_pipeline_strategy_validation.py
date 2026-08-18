"""GAP-1 Task 3.4 驗證：`POST /api/v1/ml-pipeline/create` 回應附 `strategy_validation`（三鍵投影；降級展示；不拒絕）。

① 成功回應 `display_downgrade is True` 且 `eligibility.eligible is None`、`reason=="n_unknown"`（誠實降級路徑，非 reporter_failed）
② `warning_text_key` 非空 ③ HTTP 狀態碼同既有 ④ reporter raise OSError ⇒ 仍 2xx 且 reason reporter_failed
⑤ reporter raise TypeError／InvalidValidationArgument ⇒ 5xx ⑥ 鍵集合恰為三鍵 ⑧ t_years=-1.0 接線錯誤 ⇒ 5xx 且無 reporter_failed。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import ml_pipeline as route_mod
from momentum.Analysis.strategy_validation.min_btl import InvalidValidationArgument
from momentum.Analysis.strategy_validation.report import WARNING_TEXT_KEY
from momentum.Analysis.strategy_validation.reporter import StrategyValidationReporter

_BODY = {
    "study_name": "sv-test-study",
    "trial_number": 3,
    "strategy_type": "ema_three_line",
    "user_notes": "GAP-1 Task 3.4 test：穩定且參數合理（>=10 chars）",
}


class _FakeIndicator:
    indicator_type = "ema_three_line"
    data_source = "close"
    params = {"short_period": 5}


class _FakeFEC:
    all_feature_names = ["f1", "f2"]
    indicators = [_FakeIndicator()]


class _FakePipelineConfig:
    feature_engineering_config = _FakeFEC()

    def to_dict(self):
        return {"fake": True}


class _FakeMLPipelineConfig:
    @staticmethod
    def from_user_selection(**kwargs):
        return _FakePipelineConfig()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(route_mod, "MLPipelineConfig", _FakeMLPipelineConfig)
    monkeypatch.setattr(route_mod, "PIPELINE_STORAGE_PATH", tmp_path)
    return TestClient(app)


def _post(client):
    return client.post("/api/v1/ml-pipeline/create", json=_BODY)


def test_success_response_has_honest_downgrade_projection(client):
    """①②③⑥：2xx；三鍵；eligible None／reason n_unknown（非 reporter_failed）；警語鍵非空。"""
    resp = _post(client)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    sv = data["strategy_validation"]
    assert set(sv) == {"eligibility", "display_downgrade", "warning_text_key"}
    assert sv["display_downgrade"] is True
    assert sv["warning_text_key"] == WARNING_TEXT_KEY and len(sv["warning_text_key"]) > 0
    assert sv["eligibility"]["eligible"] is None
    assert sv["eligibility"]["reason"] == "n_unknown"
    assert sv["eligibility"]["status"] == "unavailable"
    assert sv["eligibility"]["n_source"] == "assumed_not_ledgered"
    # 其他既有欄位不變
    assert data["pipeline_summary"]["mode"] == "single_indicator"
    assert data["pipeline_id"].startswith("pipeline_sv-test-study_trial3_")


def test_reporter_data_exception_degrades_to_reporter_failed_2xx(client, monkeypatch):
    """④ reporter 內部 OSError（資料型）⇒ 仍 2xx、eligibility.reason=='reporter_failed'、降級。"""

    def _boom(**k):
        raise OSError("disk")

    # reporter 只捕 (OSError, JSONDecodeError, ContractViolation)：讓 reporter try 區塊內之 read_trial_ledger 拋 OSError
    monkeypatch.setattr("momentum.Analysis.strategy_validation.reporter.read_trial_ledger", _boom)

    class _R(StrategyValidationReporter):
        def for_study_trial(self, study_name, trial_number, **kw):
            return super().for_study_trial(study_name, trial_number, dataset_key="ds", t_years=2.0, target_sharpe=1.0)

    monkeypatch.setattr(route_mod, "create_strategy_validation_reporter", lambda: _R())
    resp = _post(client)
    assert resp.status_code == 200, resp.text
    sv = resp.json()["strategy_validation"]
    assert sv["eligibility"]["reason"] == "reporter_failed"
    assert sv["eligibility"]["status"] == "computation_failed"
    assert sv["display_downgrade"] is True and sv["warning_text_key"] == WARNING_TEXT_KEY


@pytest.mark.parametrize("exc", [TypeError("bug"), InvalidValidationArgument("t_years <= 0")])
def test_program_exceptions_are_not_swallowed_5xx(client, monkeypatch, exc):
    """⑤ TypeError／InvalidValidationArgument ⇒ 5xx（不吞成 2xx reporter_failed）。"""

    class _R:
        def for_study_trial(self, *a, **k):
            raise exc

    monkeypatch.setattr(route_mod, "create_strategy_validation_reporter", lambda: _R())
    resp = _post(client)
    assert 500 <= resp.status_code < 600, resp.text
    assert "reporter_failed" not in resp.text


def test_wiring_error_negative_t_years_is_5xx_not_reporter_failed(client, monkeypatch):
    """⑧ A1-16：route 端以 t_years=-1.0 呼叫真 reporter ⇒ InvalidValidationArgument 上拋 ⇒ 5xx，回應無 reporter_failed。"""

    class _R(StrategyValidationReporter):
        def for_study_trial(self, study_name, trial_number, **kw):
            return super().for_study_trial(study_name, trial_number, dataset_key="ds-x", t_years=-1.0, target_sharpe=1.0)

    monkeypatch.setattr(route_mod, "create_strategy_validation_reporter", lambda: _R())
    resp = _post(client)
    assert 500 <= resp.status_code < 600, resp.text
    assert "reporter_failed" not in resp.text


def test_reporter_none_path_does_not_touch_ledger(monkeypatch):
    """A1-16 入口二分：任一 optional 為 None ⇒ 不呼叫 read_trial_ledger／assess_eligibility。"""
    calls = []
    monkeypatch.setattr(
        "momentum.Analysis.strategy_validation.reporter.read_trial_ledger",
        lambda **k: calls.append("ledger"),
    )
    monkeypatch.setattr(
        "momentum.Analysis.strategy_validation.reporter.assess_eligibility",
        lambda **k: calls.append("elig"),
    )
    out = StrategyValidationReporter().for_study_trial("s", 1)
    assert calls == []
    assert out["eligibility"]["eligible"] is None and out["eligibility"]["reason"] == "n_unknown"
    out = StrategyValidationReporter().for_study_trial("s", 1, dataset_key="d", t_years=1.0)
    assert calls == []


def test_failed_section_is_contract_valid():
    """reporter 失敗結構五節皆過契約（靜態字面）。"""
    from momentum.Analysis.strategy_validation.contract import validate_against_contract
    from momentum.Analysis.strategy_validation.reporter import _failed_section

    out = _failed_section()
    for name in ("eligibility", "min_btl", "dsr", "pbo", "provenance"):
        validate_against_contract(out[name], name)
        assert out[name]["status"] == "computation_failed" and out[name]["reason"] == "reporter_failed"
    json.dumps(out)  # 可序列化（無 NaN／非 JSON 型別）
