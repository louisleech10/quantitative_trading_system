"""票 TIERTOGGLE：具名 preset 之開關必須真的生效，且前後端鍵集機械對證。

使用者 2026-09-10：「確保前後端務必是同步，不能再有幽靈狀態」。
出生事故：UI「基礎」preset 之 `ic_decay:false`／`grouped_ic:false` 送到後端被丟掉
（具名 preset 分支只逐鍵映射 `fdr_correction`／`marginal_ic`），2026-09-09 事件 run
選基礎仍產出 `ic_decay`（5,909 特徵×7 horizon）與 `grouped_ic`。

本檔守三件事：
1. 後端三張表（STAGE_OVERRIDE_PATHS／MODULE_ENABLED_PATHS／LOCKED_STAGE_KEYS）＝契約檔鍵集。
2. 具名 preset **全量**消費 stage_overrides（mutation：改回只映射兩鍵 ⇒ 本檔紅）。
3. 既有行為不被本次改動破壞（缺 fdr_correction ⇒ 強制 ON；locked 鍵不得被改）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import (
    LOCKED_STAGE_KEYS,
    MODULE_ENABLED_PATHS,
    STAGE_OVERRIDE_PATHS,
    ICFilterOrchestrator,
)

CONTRACT = json.loads(
    (Path(__file__).resolve().parents[2] / "momentum/Analysis/contracts/ui_stage_toggles.json").read_text(
        encoding="utf-8"
    )
)


def _apply(active_preset: str, stage_overrides: dict | None = None) -> ICConfig:
    """以 tier 設定跑 `_apply_tier_config`，回生效後的 ICConfig。"""
    payload: dict = {"active_preset": active_preset}
    if stage_overrides is not None:
        payload["custom_overrides"] = {"stage_overrides": stage_overrides}
    config = ICConfig.model_validate({"feature_tiers": payload})
    return ICFilterOrchestrator._apply_tier_config(ICFilterOrchestrator, config)  # type: ignore[arg-type]


def test_backend_tables_match_contract():
    assert set(STAGE_OVERRIDE_PATHS) == set(CONTRACT["stage_keys"])
    assert set(MODULE_ENABLED_PATHS) == set(CONTRACT["module_keys"])
    assert set(LOCKED_STAGE_KEYS) == set(CONTRACT["locked_stage_keys"])


def test_contract_key_sets_are_disjoint_except_documented_ai_summary():
    stage, module = set(CONTRACT["stage_keys"]), set(CONTRACT["module_keys"])
    ui_only = set(CONTRACT["ui_only_keys"])
    assert stage & module == set()
    assert (stage | module) & ui_only == set()
    # ai_summary 是唯一同時 stage＋locked 者（契約 `_locked_doc` 具名）
    assert stage & set(CONTRACT["locked_stage_keys"]) == {"ai_summary"}


@pytest.mark.parametrize("preset", ["foundation", "intermediate", "advanced"])
def test_named_preset_consumes_all_stage_overrides(preset: str):
    """具名 preset 關掉的每一個 stage 開關都必須真的關掉（幽靈開關回歸測試）。"""
    off = {key: False for key in CONTRACT["stage_keys"]}
    cfg = _apply(preset, off)
    assert cfg.report.include_decay_analysis is False, "ic_decay 未生效（幽靈開關回歸）"
    assert cfg.report.include_regime_analysis is False, "grouped_ic 未生效（幽靈開關回歸）"
    assert cfg.turnover.enabled is False
    assert cfg.event_filter.enabled is False
    assert cfg.significance.fdr.enabled is False
    assert cfg.marginal_ic.enabled is False


@pytest.mark.parametrize("preset", ["foundation", "intermediate", "advanced"])
def test_named_preset_on_toggles_turn_sections_on(preset: str):
    on = {key: True for key in CONTRACT["stage_keys"]}
    cfg = _apply(preset, on)
    assert cfg.report.include_decay_analysis is True
    assert cfg.report.include_regime_analysis is True
    assert cfg.turnover.enabled is True
    assert cfg.event_filter.enabled is True


def test_locked_keys_are_not_writable_from_ui():
    """locked 鍵即使送 False 也不得改到 config（兩分支同語意）。"""
    before = _apply("intermediate", {}).report.ai_summary
    after = _apply("intermediate", {"ai_summary": not before}).report.ai_summary
    assert after == before


def test_missing_fdr_correction_still_forced_on():
    """既有行為：具名 preset 未送 fdr_correction ⇒ 強制 ON（非 UI 客戶端不得因本次改動變 OFF）。"""
    assert _apply("intermediate", {"ic_decay": False}).significance.fdr.enabled is True
    assert _apply("intermediate", None).significance.fdr.enabled is True


def test_custom_preset_unchanged():
    """custom 分支語意不變（本票只改具名分支）。"""
    cfg = _apply("custom", {key: False for key in CONTRACT["stage_keys"]})
    assert cfg.report.include_decay_analysis is False
    assert cfg.report.include_regime_analysis is False


def test_unknown_toggle_key_is_ignored_not_crash():
    cfg = _apply("intermediate", {"no_such_toggle": False, "ic_decay": False})
    assert cfg.report.include_decay_analysis is False
