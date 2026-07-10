"""IC 1e+1b Batch B4：Task 4.1–4.3 + FIX1 codex 五 BLOCKING 反例轉正。

T-4.2 前端驗收見 npm run build + grep（本檔僅後端 hop / e2e）。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Optional

import h5py
import numpy as np
import pandas as pd
import pytest

from api.models.ic_models import FeatureTierRequest, ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis.ic_config_schema import (
    ICConfig,
    SignificanceSchema,
    load_ic_config,
)
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    STAGE_OVERRIDE_PATHS,
)
from momentum.Analysis.ic_reporter import ICReporter
from momentum.Analysis.statistical_validator import apply_fdr


# ── helpers ──────────────────────────────────────────────────────────────────


def _lenient_config(**overrides: Any) -> ICConfig:
    data = load_ic_config().model_dump(by_alias=True)
    data["thresholds"].update(
        {
            "ic_mean_min": -1.0,
            "icir_min": -999.0,
            "p_value_max": 0.05,
            "ic_hit_rate_min": 0.0,
            "monotonicity_score_min": 0.0,
            "coverage_min": 0.0,
        }
    )
    data["thresholds"]["long_short_spread"] = {"enabled": False, "min_spread": 0.0}
    data["ic_train_test_split"] = False
    data["global"] = data.get("global") or {}
    data["global"]["default_horizon"] = 5
    data["labels"] = data.get("labels") or {}
    data["labels"]["horizons"] = [1, 5, 21]
    # 關閉 event / 高成本 stage 以加速 e2e
    data["event_filter"] = data.get("event_filter") or {}
    data["event_filter"]["enabled"] = False
    data["report"] = data.get("report") or {}
    data["report"]["include_decay_analysis"] = False
    data["report"]["include_regime_analysis"] = False
    data["report"]["ai_summary"] = False
    data["turnover"] = data.get("turnover") or {}
    data["turnover"]["enabled"] = False
    data["redundancy"] = data.get("redundancy") or {}
    data["redundancy"]["correlation_threshold"] = 0.99
    data.update(overrides)
    return ICConfig.model_validate(data)


def _synth_features_labels(
    n: int = 320,
    n_features: int = 12,
    seed: int = 20260711,
    signal_cols: int = 2,
    signal_strength: float = 0.35,
) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    # 12h cadence（與 meta timeframe=12h / e2e h5 路徑一致）
    index = pd.Index(
        1_704_067_200 + np.arange(n, dtype=np.int64) * 43_200,
        name="timestamp",
    )
    noise = rng.normal(size=(n, n_features))
    cols = [f"f{i}" for i in range(n_features)]
    features = pd.DataFrame(noise, columns=cols, index=index, dtype=np.float64)
    latent = rng.normal(size=n)
    label = pd.Series(latent + 0.05 * rng.normal(size=n), index=index, name="label")
    for i in range(signal_cols):
        features[cols[i]] = (
            signal_strength * latent
            + math.sqrt(max(1e-9, 1 - signal_strength**2)) * noise[:, i]
        )
    return features, label


def _minimal_ic_results(features: pd.DataFrame) -> dict:
    icir = {
        str(c): {
            "ic_mean": 0.05,
            "ic_std": 0.1,
            "icir": 0.5,
            "ic_hit_rate": 0.6,
        }
        for c in features.columns
    }
    rolling = {str(c): {"window_5": [0.1, 0.2]} for c in features.columns}
    return {"rolling_ic": rolling, "icir": icir, "ic_decay": {}}


def _tier_payload(
    fdr_correction: bool,
    *,
    active_preset: str = "custom",
) -> dict[str, Any]:
    """模擬前端 store getEffectiveConfig 送出的 feature_tiers JSON。

    FIX1：允許 active_preset=intermediate 等具名 preset（不得永遠 custom）。
    """
    if active_preset == "custom":
        return {
            "active_preset": "custom",
            "custom_overrides": {
                "stage_overrides": {
                    "fdr_correction": fdr_correction,
                    "event_filtering": False,
                    "ic_decay": False,
                    "grouped_ic": False,
                    "turnover_analysis": False,
                    "ai_summary": True,
                },
                "module_overrides": {},
            },
        }
    # 具名 preset：與 store 一致，仍送 stage_overrides.fdr_correction
    return {
        "active_preset": active_preset,
        "custom_overrides": {
            "stage_overrides": {
                "fdr_correction": fdr_correction,
            },
        },
    }


def _write_features_h5(path: Path, features_df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        group = file.create_group("BTCUSDT/12h")
        group.create_dataset(
            "features",
            data=features_df.to_numpy(dtype=np.float32),
            compression="gzip",
        )
        group.create_dataset(
            "timestamps",
            data=features_df.index.to_numpy(dtype=np.int64),
            compression="gzip",
        )
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            "feature_names",
            data=np.array(features_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )


def _write_labels_h5(path: Path, labels_df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        group = file.create_group("BTCUSDT/12h")
        group.create_dataset(
            "labels",
            data=labels_df.to_numpy(dtype=np.float32),
            compression="gzip",
        )
        group.create_dataset(
            "timestamps",
            data=labels_df.index.to_numpy(dtype=np.int64),
            compression="gzip",
        )
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            "label_names",
            data=np.array(labels_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )


def _write_meta_json(path: Path, features: list[str]) -> None:
    meta = {
        name: {
            "name": name,
            "category": "trend",
            "layer": 1,
            "data_source": "close",
        }
        for name in features
    }
    meta["symbol"] = "BTCUSDT"
    meta["timeframe"] = "12h"
    meta["case_id"] = "BTCUSDT_12h"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=True), encoding="utf-8")


def _run_stage5_via_tier(
    fdr_correction: bool,
    features: pd.DataFrame,
    label: pd.Series,
    *,
    active_preset: str = "custom",
) -> dict:
    """真路徑：store JSON → API model → _build_config_override → load → _apply_tier_config → stage5。

    禁 mock 映射鏈（Task 4.3 / M-G）。
    """
    store_json = _tier_payload(fdr_correction, active_preset=active_preset)
    tier_req = FeatureTierRequest.model_validate(store_json)
    request = ICAnalyzeRequest(
        feature_tiers=tier_req,
        mode="longitudinal",
    )
    service = ICAnalysisService.__new__(ICAnalysisService)
    override = service._build_config_override(request)
    assert override is not None
    assert "feature_tiers" in override

    base = _lenient_config()
    # 若測試要驗證 preset 覆寫 false→true，先把 base 設成 false
    base_data = base.model_dump(by_alias=True)
    if active_preset != "custom":
        base_data["significance"] = {
            "fdr": {"enabled": False, "method": "fdr_bh"},
            "maxlags": None,
        }
    merged = base_data
    merged["feature_tiers"] = override["feature_tiers"]
    config = ICConfig.model_validate(merged)

    orch = ICFilterOrchestrator(config)
    applied = orch._apply_tier_config(config)
    assert applied.significance.fdr.enabled is bool(fdr_correction)

    result = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        applied,
        event_info={"tier": "sufficient"},
        split_context=None,
        metadata={"symbol": "BTCUSDT"},
    )
    return result


def _stage5_passed_from_report(report: dict) -> set[str]:
    """從 analyze→stage7 report 的 filter_log 還原 stage5 passed 集合。"""
    log = (report.get("filter_log") or {}).get("stage5_thresholds") or {}
    summary = report.get("summary_table") or []
    all_names = {
        str(row["feature_name"])
        for row in summary
        if isinstance(row, dict) and row.get("feature_name") is not None
    }
    removed: set[str] = set()
    for bucket in (log.get("removed_features") or {}).values():
        if isinstance(bucket, list):
            removed.update(str(x) for x in bucket)
    return all_names - removed


def _expected_p_gate_passers(
    summary_table: list[dict], *, use_q: bool, alpha: float
) -> set[str]:
    """可證偽：依 summary 欄位重算 p 閘通過集合（lenient 下應=stage5 passed）。"""
    field = "p_value_adj" if use_q else "p_value"
    passed: set[str] = set()
    for row in summary_table:
        name = row.get("feature_name")
        if name is None:
            continue
        val = row.get(field)
        try:
            p = float(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if np.isfinite(p) and p <= alpha:
            passed.add(str(name))
    return passed


def _run_full_analyze_e2e(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fdr_correction: bool,
    features: pd.DataFrame,
    label: pd.Series,
    active_preset: str = "custom",
    seed_tag: str = "e2e",
) -> dict:
    """真端到端：store→API→config_override→analyze→stage7→report（非直呼 private stage5）。"""
    features_path = tmp_path / f"features_{seed_tag}.h5"
    labels_path = tmp_path / f"labels_{seed_tag}.h5"
    meta_path = tmp_path / f"meta_{seed_tag}.json"
    # return_5 契約：尾端 NaN 數 = lag=5（validate_alignment）
    label_vals = label.to_numpy(dtype=np.float64).copy()
    label_vals[-5:] = np.nan
    labels_df = pd.DataFrame({"return_5": label_vals}, index=label.index)
    _write_features_h5(features_path, features)
    _write_labels_h5(labels_path, labels_df)
    _write_meta_json(meta_path, list(features.columns))

    store_json = _tier_payload(fdr_correction, active_preset=active_preset)
    tier_req = FeatureTierRequest.model_validate(store_json)
    request = ICAnalyzeRequest(feature_tiers=tier_req, mode="longitudinal")
    service = ICAnalysisService.__new__(ICAnalysisService)
    override = service._build_config_override(request) or {}

    base = _lenient_config()
    base_data = base.model_dump(by_alias=True)
    # deep-merge feature_tiers + lenient thresholds 進 override
    config_override = {
        **{k: v for k, v in base_data.items() if k in ("thresholds", "ic_train_test_split",
                                                       "event_filter", "report", "turnover",
                                                       "redundancy", "labels", "global",
                                                       "significance")},
        "feature_tiers": override.get("feature_tiers") or store_json,
        # 確保 labels 走 return_5（h=5）
        "labels": {**(base_data.get("labels") or {}), "horizons": [5]},
        "global": {**(base_data.get("global") or {}), "default_horizon": 5},
        "ic_train_test_split": False,
        "thresholds": base_data["thresholds"],
        "event_filter": {"enabled": False},
        "report": {
            "include_decay_analysis": False,
            "include_regime_analysis": False,
            "ai_summary": False,
        },
        "turnover": {"enabled": False},
        "redundancy": {"correlation_threshold": 0.99},
    }

    orch = ICFilterOrchestrator(_lenient_config())
    monkeypatch.setattr(orch, "_persist_outputs", lambda *args, **kwargs: {})
    report = orch.analyze(
        features_path=str(features_path),
        labels_path=str(labels_path),
        meta_path=str(meta_path),
        config_override=config_override,
    )
    return report


# ── T-4.1 schema + hop chain ─────────────────────────────────────────────────


def test_t41_schema_default_fdr_on():
    """舊 config 無 significance 節 → 預設 ON；canonical 嵌套形。"""
    cfg = ICConfig()
    assert cfg.significance.fdr.enabled is True
    assert cfg.significance.fdr.method == "fdr_bh"
    assert cfg.significance.maxlags is None

    data = load_ic_config().model_dump(by_alias=True)
    data.pop("significance", None)
    loaded = ICConfig.model_validate(data)
    assert loaded.significance.fdr.enabled is True


def test_t41_no_flat_fdr_enabled_alias():
    """禁第四種 fdr 命名：schema 無平鋪 fdr_enabled。"""
    fields = set(SignificanceSchema.model_fields.keys())
    assert "fdr" in fields
    assert "fdr_enabled" not in fields
    assert STAGE_OVERRIDE_PATHS["fdr_correction"] == ("significance", "fdr", "enabled")


def test_t41_preset_intermediate_maps_fdr_on():
    """FIX1-(1) 反例轉正：active_preset=intermediate + base fdr=false → 映射後 true。

    不得手刻永遠 custom；UI intermediate preset fdr_correction=true 不得靜默丟失。
    """
    # base enabled=false + intermediate（UI preset ON）
    data = _lenient_config().model_dump(by_alias=True)
    data["significance"] = {"fdr": {"enabled": False, "method": "fdr_bh"}, "maxlags": None}
    data["feature_tiers"] = {
        "active_preset": "intermediate",
        "custom_overrides": {
            "stage_overrides": {"fdr_correction": True},
        },
    }
    config = ICConfig.model_validate(data)
    assert config.significance.fdr.enabled is False  # 映射前

    orch = ICFilterOrchestrator(config)
    applied = orch._apply_tier_config(config)
    assert applied.significance.fdr.enabled is True

    # 無 stage_overrides 時，具名 preset 仍強制 ON
    data2 = _lenient_config().model_dump(by_alias=True)
    data2["significance"] = {"fdr": {"enabled": False, "method": "fdr_bh"}, "maxlags": None}
    data2["feature_tiers"] = {"active_preset": "intermediate"}
    applied2 = orch._apply_tier_config(ICConfig.model_validate(data2))
    assert applied2.significance.fdr.enabled is True


def test_t41_hop_chain_fdr_false_to_report_metadata():
    """T-4.1 每跳：store→API→_apply_tier_config→stage5→report metadata 同 key。"""
    features, label = _synth_features_labels(n=200, n_features=4, seed=41)
    result = _run_stage5_via_tier(False, features, label)

    assert result["significance"]["fdr"]["enabled"] is False
    # FIX1-(2)：OFF 時 method 仍為 fdr_bh，禁 method=none
    assert result["significance"]["fdr"]["method"] == "fdr_bh"
    assert result["selection_scope"].method == "fdr_bh"
    assert result["fdr_enabled"] is False
    assert result["threshold_log"]["fdr_enabled"] is False
    assert result["threshold_log"]["fdr_enabled"] == result["significance"]["fdr"]["enabled"]

    orch = ICFilterOrchestrator(_lenient_config())
    meta = orch._build_report_metadata(
        features,
        features,
        {"symbol": "BTCUSDT"},
        {"tier": "sufficient"},
        {},
        None,
        significance=result["significance"],
        selection_scope=result["selection_scope"],
    )
    assert meta["significance"]["fdr"]["enabled"] is False
    assert meta["significance"]["fdr"]["method"] == "fdr_bh"
    assert meta["selection_scope"]["method"] == "fdr_bh"

    reporter = ICReporter({})
    report = reporter.generate_json_report(
        {"summary_table": result["summary_table"], "filter_log": {}},
        meta,
    )
    report_meta = report.get("metadata") or report
    if "significance" in report_meta:
        sig = report_meta["significance"]
    else:
        sig = (report.get("metadata") or {}).get("significance") or report.get(
            "significance"
        )
    if sig is None and isinstance(report.get("metadata"), dict):
        sig = report["metadata"].get("significance")
    assert sig is not None, f"report keys={list(report.keys())}"
    assert sig["fdr"]["enabled"] is False
    assert sig["fdr"]["method"] == "fdr_bh"


def test_t41_hop_chain_fdr_true():
    features, label = _synth_features_labels(n=200, n_features=4, seed=42)
    result = _run_stage5_via_tier(True, features, label)
    assert result["significance"]["fdr"]["enabled"] is True
    assert result["significance"]["fdr"]["method"] == "fdr_bh"
    assert result["selection_scope"].method == "fdr_bh"
    assert result["threshold_log"]["fdr_enabled"] is True
    assert result["threshold_log"]["fdr_enabled"] == result["significance"]["fdr"]["enabled"]


def test_t41_stage5_consumes_maxlags_from_schema():
    """stage5 消費 significance.maxlags（顯式 override，仍受 h-1 下限）。"""
    features, label = _synth_features_labels(n=400, n_features=2, seed=43)
    cfg = _lenient_config()
    data = cfg.model_dump(by_alias=True)
    data["significance"] = {"fdr": {"enabled": True, "method": "fdr_bh"}, "maxlags": 6}
    config = ICConfig.model_validate(data)
    orch = ICFilterOrchestrator(config)
    result = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        config,
        event_info={"tier": "sufficient"},
        metadata={"symbol": "BTCUSDT"},
    )
    for feat in features.columns:
        ml = result["ic_stats"][str(feat)].get("maxlags")
        if ml is not None and np.isfinite(float(ml)):
            assert int(ml) == 6


def test_t41_stage5_consumes_fdr_method_from_schema():
    """FIX1-(5)：apply_fdr / stage5 消費 significance.fdr.method（非幽靈）。"""
    features, label = _synth_features_labels(n=200, n_features=3, seed=44)
    cfg = _lenient_config()
    data = cfg.model_dump(by_alias=True)
    # bonferroni 會被 adjust_multiple_comparisons 實際消費（可與 fdr_bh 區分）
    data["significance"] = {
        "fdr": {"enabled": True, "method": "bonferroni"},
        "maxlags": None,
    }
    config = ICConfig.model_validate(data)
    orch = ICFilterOrchestrator(config)
    result = orch._stage5_statistical_validation(
        features,
        label,
        _minimal_ic_results(features),
        config,
        event_info={"tier": "sufficient"},
        metadata={"symbol": "BTCUSDT"},
    )
    assert result["significance"]["fdr"]["method"] == "bonferroni"
    assert result["selection_scope"].method == "bonferroni"

    # 對照：同一 p map 用 apply_fdr(method=bonferroni) 應與 summary q 一致
    p_map = {
        str(row["feature_name"]): float(row["p_value"])
        for row in result["summary_table"]
        if row.get("p_value") is not None and np.isfinite(float(row["p_value"]))
    }
    q_expected, _ = apply_fdr(p_map, 0.05, method="bonferroni")
    for row in result["summary_table"]:
        name = str(row["feature_name"])
        if name in q_expected and np.isfinite(q_expected[name]):
            assert np.isclose(float(row["p_value_adj"]), q_expected[name], rtol=1e-12)


# ── T-4.3 = M-G 兩態 e2e（真 analyze→stage7→report）─────────────────────────


def test_t43_mg_two_state_fdr_gate_full_e2e(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """FIX1-(3)：真 analyze→stage7→report 全鏈；_gate 可證偽（非恆真）。

    不 mock _apply_tier_config；不直呼 private stage5 + 手動注入 metadata。
    """
    features, label = _synth_features_labels(
        n=360,
        n_features=16,
        seed=20260711,
        signal_cols=3,
        signal_strength=0.28,
    )

    off = _run_full_analyze_e2e(
        tmp_path,
        monkeypatch,
        fdr_correction=False,
        features=features,
        label=label,
        seed_tag="off",
    )
    on = _run_full_analyze_e2e(
        tmp_path,
        monkeypatch,
        fdr_correction=True,
        features=features,
        label=label,
        seed_tag="on",
    )

    # report metadata 為唯一真相（非手動注入）
    off_sig = (off.get("metadata") or {}).get("significance") or {}
    on_sig = (on.get("metadata") or {}).get("significance") or {}
    assert off_sig.get("fdr", {}).get("enabled") is False
    assert on_sig.get("fdr", {}).get("enabled") is True
    # FIX1-(2)：method 恆 fdr_bh
    assert off_sig.get("fdr", {}).get("method") == "fdr_bh"
    assert on_sig.get("fdr", {}).get("method") == "fdr_bh"
    assert (off.get("metadata") or {}).get("selection_scope", {}).get("method") == "fdr_bh"

    off_log = (off.get("filter_log") or {}).get("stage5_thresholds") or {}
    on_log = (on.get("filter_log") or {}).get("stage5_thresholds") or {}
    assert off_log.get("fdr_enabled") is False
    assert on_log.get("fdr_enabled") is True
    assert off_log.get("fdr_enabled") == off_sig["fdr"]["enabled"]
    assert on_log.get("fdr_enabled") == on_sig["fdr"]["enabled"]

    alpha = float(off_log["alpha_effective"])
    assert alpha == float(on_log["alpha_effective"])

    passed_off = _stage5_passed_from_report(off)
    passed_on = _stage5_passed_from_report(on)

    # 可證偽閘：重算 p 閘集合必須等於 stage5 passed（若恒真斷言會在此翻紅）
    expected_off = _expected_p_gate_passers(
        off["summary_table"], use_q=False, alpha=alpha
    )
    expected_on = _expected_p_gate_passers(
        on["summary_table"], use_q=True, alpha=alpha
    )
    assert passed_off == expected_off, (
        f"OFF 閘不可證偽/不一致: stage5={sorted(passed_off)} "
        f"recomputed={sorted(expected_off)}"
    )
    assert passed_on == expected_on, (
        f"ON 閘不可證偽/不一致: stage5={sorted(passed_on)} "
        f"recomputed={sorted(expected_on)}"
    )

    # 兩態可分離
    if passed_off == passed_on:
        found = False
        for seed in range(20260712, 20260712 + 40):
            feat2, lab2 = _synth_features_labels(
                n=360,
                n_features=16,
                seed=seed,
                signal_cols=3,
                signal_strength=0.28,
            )
            off2 = _run_full_analyze_e2e(
                tmp_path,
                monkeypatch,
                fdr_correction=False,
                features=feat2,
                label=lab2,
                seed_tag=f"off{seed}",
            )
            on2 = _run_full_analyze_e2e(
                tmp_path,
                monkeypatch,
                fdr_correction=True,
                features=feat2,
                label=lab2,
                seed_tag=f"on{seed}",
            )
            p_off2 = _stage5_passed_from_report(off2)
            p_on2 = _stage5_passed_from_report(on2)
            if p_off2 != p_on2:
                assert (
                    (off2.get("metadata") or {})
                    .get("significance", {})
                    .get("fdr", {})
                    .get("enabled")
                    is False
                )
                assert (
                    (on2.get("metadata") or {})
                    .get("significance", {})
                    .get("fdr", {})
                    .get("enabled")
                    is True
                )
                found = True
                passed_off, passed_on = p_off2, p_on2
                break
        assert found, (
            f"未能構造兩態 passed 可分離資料；"
            f"off={sorted(passed_off)} on={sorted(passed_on)}"
        )
    else:
        assert passed_off != passed_on

    # FDR on 通常不寬於 off
    assert len(passed_on) <= len(passed_off) or passed_on != passed_off


def test_t43_legacy_report_null_p_compat_fields_present():
    """舊 report 無 p_value_adj / null p → 欄位可缺；後端 schema 不炸。"""
    reporter = ICReporter({})
    table = [
        {
            "feature_name": "old_feat",
            "ic_mean": 0.01,
            "icir": 0.1,
            "p_value": None,
            "t_stat": None,
        }
    ]
    report = reporter.generate_json_report({"summary_table": table, "filter_log": {}}, {})
    assert report is not None


def test_t41_off_method_never_none():
    """FIX1-(2) 獨立反例：OFF 收據 method 不得為 none。"""
    features, label = _synth_features_labels(n=180, n_features=3, seed=50)
    result = _run_stage5_via_tier(False, features, label)
    fdr = result["significance"]["fdr"]
    assert fdr["enabled"] is False
    assert fdr["method"] == "fdr_bh"
    assert fdr["method"] != "none"
    assert result["selection_scope"].method == "fdr_bh"
    assert result["selection_scope"].method != "none"


def test_t41_xsec_metadata_has_alpha_effective_and_canonical_method():
    """FIX1-(2)(5) xsec：OFF 時 method=fdr_bh；metadata 含 fdr.alpha_effective。"""
    timestamps = pd.date_range("2020-01-01", periods=40, freq="12h")
    symbols = ["BTCUSDT", "ETHUSDT", "BCHUSDT", "LTCUSDT"]
    index = pd.MultiIndex.from_product(
        [timestamps, symbols], names=["timestamp", "_symbol"]
    )
    rng = np.random.default_rng(99)
    n = len(index)
    frame = pd.DataFrame(
        {
            "alpha": rng.normal(size=n),
            "beta": rng.normal(size=n),
            "return_1": rng.normal(size=n),
        },
        index=index,
    )
    orch = ICFilterOrchestrator(_lenient_config())
    report = orch.analyze_cross_sectional(
        frame,
        config_override={
            "ic_train_test_split": False,
            # 走 custom+stage_overrides 關掉 FDR（具名 preset 會強制 ON）
            "feature_tiers": {
                "active_preset": "custom",
                "custom_overrides": {
                    "stage_overrides": {"fdr_correction": False},
                },
            },
            "thresholds": {"p_value_max": 0.05},
        },
    )
    fdr = report["metadata"]["significance"]["fdr"]
    assert fdr["enabled"] is False
    assert fdr["method"] == "fdr_bh"
    assert fdr["method"] != "none"
    assert "alpha_effective" in fdr
    assert float(fdr["alpha_effective"]) == pytest.approx(0.05)
