"""ICPERF Task 0.4 ㊸（SPEC v5.57；code review r68 群集 C）：IC 頁七鍵之前後端接線——秒級契約測試。

使用者 2026-11-01：「像是IC篩選這都會影響後續出來的篩出的節果，所以看如何讓使用者知道此項目的開關和方法選擇對IC篩選
會有如何影響。」；2026-09-10：「前後端務必同步，不能再有幽靈狀態」。

單一真相源＝`momentum/Analysis/contracts/ui_stage_toggles.json` 之 `setting_keys`／`merged_keys`／`disclosed_keys`。
前端（`frontend/src/lib/icConfigOverride.ts` 之 `IC_SETTING_SPECS`）＝契約由 vitest 對證；本檔對證契約＝後端：

1. 七鍵各歸一類、`ui_only_keys` 為空（不再有具名殘留）。
2. 每個設定鍵之 `path` 落在 `ICConfig` 之 Literal／bool 欄；`options ∪ unavailable_options`＝schema Literal；`default`＝
   `load_ic_config()` 之現行值（前端只在值≠default 時送出，故 default 必須等於後端實際值，否則即幽靈）。
3. 每個非預設選項：以契約 path 組 `config_override` → 服務 `_build_config_override` → `create_ic_analyzer`（同 IC 頁
   服務路徑）→ 消費點實際收到該值（spy 於消費函式第一次呼叫即中止，不計算任何數值）；未知值於 schema 驗證拒收。
4. mutation 自證：映射斷開（path 改錯）⇒ 消費點收到的是預設值、本檔之等式即紅。
5. `ic_autocorrelation` 之揭露原因（算出但無消費者）以 AST 機械驗證——日後接進報告或門檻即紅，提醒改歸類。
"""

from __future__ import annotations

import ast
import json
import typing
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pytest

from api.models.ic_models import ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService
from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.factories import create_ic_analyzer

REPO = Path(__file__).resolve().parents[3]
CONTRACT = json.loads(
    (REPO / "momentum" / "Analysis" / "contracts" / "ui_stage_toggles.json").read_text(encoding="utf-8")
)
SETTINGS: Dict[str, Dict[str, Any]] = CONTRACT["setting_keys"]
SEVEN = {
    "ic_method_selection",
    "winsorization_method",
    "monotonicity_test",
    "return_type_selection",
    "ic_autocorrelation",
    "redundancy_method_selection",
    "vif_filter",
}


class _Captured(Exception):
    """spy 於消費函式入口拋出，帶出實際收到之值（不往下計算）。"""

    def __init__(self, value: Any) -> None:
        super().__init__(repr(value))
        self.value = value


def _nested(path: List[str], value: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    cur = out
    for part in path[:-1]:
        cur = cur.setdefault(part, {})
    cur[path[-1]] = value
    return out


def _schema_field(path: List[str]) -> Any:
    """沿 alias 形狀之 path 取 schema 欄位之 annotation（頂層 alias `global` ⇒ `global_settings`）。"""
    model: Any = ICConfig
    annotation: Any = None
    for i, part in enumerate(path):
        fields = model.model_fields
        name = next((n for n, f in fields.items() if (f.alias or n) == part or n == part), None)
        assert name is not None, f"契約 path {path} 之 {part!r} 不在 {model.__name__}"
        annotation = fields[name].annotation
        if i < len(path) - 1:
            model = annotation
    return annotation


def _effective_value(cfg: ICConfig, path: List[str]) -> Any:
    data = cfg.model_dump(by_alias=True)
    for part in path:
        data = data[part]
    return data


def _api_analyzer(override: Dict[str, Any]) -> Tuple[ICFilterOrchestrator, ICConfig]:
    """IC 頁服務路徑：請求 `config_override` → `_build_config_override` → `create_ic_analyzer`；回 analyzer 與 analyze 入口
    同法之 effective config（`_apply_tier_config(_apply_config_override(...))`，`ic_filter_orchestrator.py` analyze 開頭）。"""
    svc = ICAnalysisService.__new__(ICAnalysisService)
    built = svc._build_config_override(ICAnalyzeRequest(config_override=override))
    analyzer = create_ic_analyzer(built)
    cfg = analyzer._apply_tier_config(analyzer._apply_config_override(built))
    return analyzer, cfg


def _index(n: int = 6) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="4h")


def _consumed(key: str, override: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> Any:
    """跑該鍵之消費點，回消費函式實際收到之值（spy 中止於入口；輸入只供到達該入口，內容不參與任何計算）。"""
    analyzer, cfg = _api_analyzer(override)
    idx = _index()
    frame = pd.DataFrame({"a": np.arange(6, dtype=float), "b": np.arange(6, dtype=float)[::-1]}, index=idx)
    if key == "ic_method_selection":
        def spy(features, label, method=None, *a, **k):  # noqa: ANN001
            raise _Captured(method)

        monkeypatch.setattr(analyzer._ic_engine, "compute_ic", spy)
        with pytest.raises(_Captured) as got:
            analyzer._stage4_ic_calculation(frame, pd.Series(np.arange(6, dtype=float), index=idx), {}, cfg, None)
        return got.value.value
    if key == "winsorization_method":
        def spy_w(df, *a, method=None, **k):  # noqa: ANN001
            raise _Captured(method)

        monkeypatch.setattr(analyzer._preprocessor, "winsorize", spy_w)
        with pytest.raises(_Captured) as got:
            analyzer._stage1_preprocessing(frame, {}, fit_mode="pit_expanding")
        return got.value.value
    if key == "return_type_selection":
        from momentum.FeatureEngineering.labels.label_generator import LabelGenerator

        def spy_r(self, close, horizon, return_type, *a, **k):  # noqa: ANN001
            raise _Captured(return_type)

        monkeypatch.setattr(LabelGenerator, "generate_returns_by_type", spy_r)

        class _Reader:
            def read_klines(self, symbol: str, timeframe: str) -> pd.DataFrame:
                return pd.DataFrame({"close": np.arange(1.0, 7.0)}, index=idx)

        with pytest.raises(_Captured) as got:
            analyzer._stage2_label_generation(None, {"symbol": "SYM", "timeframe": "4h"}, cfg, _Reader(), frame)
        return got.value.value
    if key == "redundancy_method_selection":
        def spy_d(features_df, ic_scores, method="greedy"):  # noqa: ANN001
            raise _Captured(method)

        monkeypatch.setattr(analyzer._redundancy, "filter", spy_d)
        with pytest.raises(_Captured) as got:
            analyzer._stage6_redundancy(frame, ["a", "b"], {"a": 0.1, "b": 0.05}, {})
        return got.value.value
    if key == "monotonicity_test":
        # 一列除單調性外全過門檻（方向對齊值直接給定）：門檻開 ⇒ 被單調性剔除；關 ⇒ 通過且記入 skipped
        row = {"feature_name": "a", "ic_mean": 0.1, "direction": 1, "icir_aligned": 5.0, "p_value_adj": 0.0,
               "p_value": 0.0, "ic_hit_rate_aligned": 1.0, "monotonicity_score_aligned": 0.0, "coverage": 1.0}
        passed, log = analyzer._apply_thresholds([row], cfg.thresholds, 0.05)
        removed = log["removed_features"]
        return {"passed": passed, "monotonicity": removed["monotonicity"],
                "skipped": removed.get("monotonicity_skipped_disabled")}
    raise AssertionError(f"未知設定鍵 {key}")


def _non_default(key: str) -> List[Any]:
    spec = SETTINGS[key]
    if spec["kind"] == "toggle":
        return [not spec["default"]]
    return [v for v in spec["options"] if v != spec["default"]]


def _expected(key: str, value: Any) -> Any:
    if key != "monotonicity_test":
        return value
    if value:
        return {"passed": [], "monotonicity": ["a"], "skipped": None}
    return {"passed": ["a"], "monotonicity": [], "skipped": ["a"]}


# ── 1. 七鍵歸類 ──────────────────────────────────────────────────────────────────────────────────────


def test_seven_keys_each_classified_once_and_ui_only_empty() -> None:
    groups = [set(SETTINGS), set(CONTRACT["merged_keys"]), set(CONTRACT["disclosed_keys"])]
    assert CONTRACT["ui_only_keys"] == [], "㊸ 後不得再有未接線之 UI 鍵"
    union = set().union(*groups)
    assert union == SEVEN, f"七鍵歸類不全或多鍵：{sorted(union ^ SEVEN)}"
    assert sum(len(g) for g in groups) == len(union), "同一鍵不得歸兩類"
    for merged, target in CONTRACT["merged_keys"].items():
        assert target in SETTINGS, f"{merged} 併入之 {target} 須為設定鍵"
    assert "vif" in SETTINGS["redundancy_method_selection"]["options"], "vif_filter 併入去重方法 ⇒ 選單須含 vif"
    stage_like = set(CONTRACT["stage_keys"]) | set(CONTRACT["module_keys"]) | set(CONTRACT["locked_stage_keys"])
    assert not (union & stage_like), "設定鍵不得與 stage／module／locked 重疊"


# ── 2. 契約 ⇔ schema ⇔ 載入值 ────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("key", sorted(SETTINGS))
def test_setting_path_options_default_match_backend(key: str) -> None:
    spec = SETTINGS[key]
    annotation = _schema_field(spec["path"])
    loaded = _effective_value(load_ic_config(), spec["path"])
    schema_default = _effective_value(ICConfig(), spec["path"])
    assert spec["default"] == loaded == schema_default, (
        f"{key}：契約 default {spec['default']!r}、load_ic_config {loaded!r}、schema {schema_default!r} 須相同"
        "（前端只送非預設值，default 與後端實值不符即幽靈）"
    )
    if spec["kind"] == "toggle":
        assert annotation is bool and "options" not in spec
        return
    assert spec["kind"] == "select"
    literal = set(typing.get_args(annotation))
    unavailable = set((spec.get("unavailable_options") or {}).keys())
    assert set(spec["options"]) | unavailable == literal, f"{key}：選單＋不可用＝schema Literal {sorted(literal)}"
    assert not (set(spec["options"]) & unavailable)
    assert spec["default"] in spec["options"]
    for opt, reason in (spec.get("unavailable_options") or {}).items():
        assert isinstance(reason, str) and reason.strip(), f"{key}.{opt}：不可用須附原因"


def test_excess_return_type_is_really_unreachable_on_ic_page() -> None:
    """`excess` 列為不可用之依據實查：IC 頁第 2 段由 K 線生成標籤時不傳基準價 ⇒ 標籤生成器拒絕（不是猜）。"""
    idx = _index()
    analyzer, cfg = _api_analyzer({"labels": {"return_type": "excess"}})

    class _Reader:
        def read_klines(self, symbol: str, timeframe: str) -> pd.DataFrame:
            return pd.DataFrame({"close": np.arange(1.0, 7.0)}, index=idx)

    frame = pd.DataFrame({"a": np.arange(6, dtype=float)}, index=idx)
    with pytest.raises(ValueError, match="benchmark_close"):
        analyzer._stage2_label_generation(None, {"symbol": "SYM", "timeframe": "4h"}, cfg, _Reader(), frame)


# ── 3. 每選項傳到消費點（IC 頁服務路徑）──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "key,value",
    [(k, v) for k in sorted(SETTINGS) for v in _non_default(k)] + [(k, SETTINGS[k]["default"]) for k in sorted(SETTINGS)],
)
def test_each_option_reaches_consumer(key: str, value: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    got = _consumed(key, _nested(SETTINGS[key]["path"], value), monkeypatch)
    assert got == _expected(key, value), f"{key}={value!r} 未傳到消費點（實得 {got!r}）"


@pytest.mark.parametrize("key", sorted(SETTINGS))
def test_absent_setting_uses_default_at_consumer(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """前端值＝預設時不送；後端缺鍵 ⇒ 消費點收到契約 default（與前端顯示一致）。"""
    assert _consumed(key, {}, monkeypatch) == _expected(key, SETTINGS[key]["default"])


@pytest.mark.parametrize("key", sorted(k for k, s in SETTINGS.items() if s["kind"] == "select"))
def test_unknown_option_rejected_by_schema(key: str) -> None:
    """未知值拒收：schema 驗證失敗（pydantic ValidationError 為 ValueError 子類 ⇒ `/analyze` 回 400）。"""
    with pytest.raises(ValueError):
        _api_analyzer(_nested(SETTINGS[key]["path"], "__no_such_option__"))


# ── 4. mutation 自證 ─────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("key", sorted(SETTINGS))
def test_broken_mapping_is_detected(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """映射斷開（path 末段改成不存在之欄，ICConfig 靜默忽略）⇒ 消費點收到預設值 ≠ 所選值 ⇒ 第 3 節等式必紅。"""
    value = _non_default(key)[0]
    broken = _nested(SETTINGS[key]["path"][:-1] + ["__broken__"], value)
    got = _consumed(key, broken, monkeypatch)
    assert got == _expected(key, SETTINGS[key]["default"]) and got != _expected(key, value)


# ── 4b. 設定指紋相容 ─────────────────────────────────────────────────────────────────────────────────


def test_config_hash_unchanged_at_default_and_distinct_when_off() -> None:
    """㊸ 新增 `thresholds.monotonicity_gate_enabled`：預設值時不入 `_hash_config`（倖存者檔 config_hash 與加欄前之演算法
    逐字相同——加欄前＝同一 dump 不含此欄）；關閉時入雜湊（不同設定不同指紋）。"""
    import hashlib

    orch = ICFilterOrchestrator.__new__(ICFilterOrchestrator)
    default_cfg = ICConfig()
    legacy = default_cfg.model_dump()
    legacy["thresholds"].pop("monotonicity_gate_enabled")
    expected = hashlib.md5(json.dumps(legacy, sort_keys=True).encode("utf-8")).hexdigest()
    assert orch._hash_config(default_cfg) == expected
    off = ICConfig.model_validate({"thresholds": {"monotonicity_gate_enabled": False}})
    assert orch._hash_config(off) != expected
    # 其他欄照常入雜湊（只略去所列之欄）
    other = ICConfig.model_validate({"thresholds": {"monotonicity_score_min": 0.5}})
    assert orch._hash_config(other) != expected


# ── 5. 揭露鍵之原因機械驗證 ──────────────────────────────────────────────────────────────────────────


def test_ic_autocorrelation_has_no_consumer() -> None:
    """`ic_autocorr` 只在第 4 段回傳 dict 中出現為鍵；全 `momentum/`、`api/` 無任何讀取（下標／.get）。日後接進報告或門檻
    ⇒ 本測試紅，須把 `ic_autocorrelation` 自 disclosed_keys 改歸 setting_keys 並補 UI 開關。"""
    reads: List[str] = []
    writes = 0
    for root in ("momentum", "api"):
        for path in sorted((REPO / root).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
                        and node.slice.value == "ic_autocorr":
                    reads.append(f"{path.relative_to(REPO)}:{node.lineno}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" \
                        and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "ic_autocorr":
                    reads.append(f"{path.relative_to(REPO)}:{node.lineno}")
                if isinstance(node, ast.Dict):
                    writes += sum(1 for k in node.keys if isinstance(k, ast.Constant) and k.value == "ic_autocorr")
    assert writes == 1, f"ic_autocorr 之產生點應恰一處（第 4 段回傳），實得 {writes}"
    assert reads == [], f"ic_autocorr 已有消費者 {reads} ⇒ 改歸類並補開關"
    assert "ic_autocorrelation" in CONTRACT["disclosed_keys"]
