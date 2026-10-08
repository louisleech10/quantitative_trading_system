"""FRAMEPATH Task 1.2–1.4：唯一 CGSA 分派、多週期 legacy 刪除與死碼掃除之具名驗收（docs/FRAMEPATH_SPEC.md）。

- Task 1.2：registry 為 None 之 L3（串流／hybrid）、L6.5、L7 分派點拋 `CGSARegistryRequiredError`（訊息含 symbol、
  timeframe、呼叫點）；`_combine_layers` 只收 `layer3_input`／`layer4_input`；momentum／api／scripts 之全部
  `_combine_layers(` 呼叫 context 為白名單字面；`FFACT_USE_CGSA` 生產碼零讀取、殘留 `=0` 無作用；`persist=False`
  走 CGSA 且 completeness 照寫；L3 `in_memory` 非串流分支保留。
- Task 1.3：legacy 多週期與 frame 列對應之符號於 momentum 零出現；`set_no_start_calibration()` 無參數；
  `MultiTFGenerator._apply_timeframe_tag` registry 為 None ⇒ 具名例外、非 None ⇒ 原樣回傳。
- Task 1.4：三檔之「零引用且非公開入口、且非 HEAD 既有死碼、且未具名保留」之 def 數 == 0。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）之生成案例沿用 `ffstat_helpers` 輕量設定，單組串行。
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Set, Tuple

import pandas as pd
import pytest

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError, FeatureFactory
from momentum.FeatureEngineering.feature_storage import COMPLETENESS_FIELD_NAMES
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from tests.feature_engineering.ffstat_helpers import (
    PRIMARY_TF,
    SYMBOL,
    kline_frame,
    prepare_stat_env,
    run_stat,
    stat_payload,
)
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, MULTI_TFS

REPO = Path(__file__).resolve().parents[2]
WHITELIST = ("layer3_input", "layer4_input")
REJECTED_CONTEXTS = ("layer6_5_input", "layer7_final", "multi_tf_layers", "multi_tf_legacy_merged",
                     "multi_tf_merged", "unknown", "framepath_arbitrary_context")
SCAN_ROOTS = ("momentum", "api", "scripts")
LEGACY_SYMBOLS = ("_legacy_native_row_maps", "_generate_multi_tf_legacy", "_no_start_native_maps",
                  "multi_tf_legacy_merged", "multi_tf_layers")
# frame 專屬之 FeatureFactory 方法（HEAD 生產呼叫者只在 frame 單週期尾段 :569–597、frame L7 體、legacy 多週期）；
# 主委 2026-10-08 於暫存工作樹試作刪除至不動點而得（收據 handoffs/run_receipts/20261008-framepath-trial-dead.txt）
FRAME_ONLY_FACTORY_DEFS = (
    "_cgsa_enabled", "_layer6_5_preprocessing", "_layer6_5_pre_ic", "_layer6_5_post_ic",
    "_run_layer6_5_preprocessor", "_layer7_validate_and_persist", "_layer7_validate_and_persist_cgsa",
    "_apply_timeframe_tag", "_execute_l65_with_degradation", "_apply_l7_dead_feature_drop",
    # HEAD 生產即零呼叫者、唯一測試引用（test_failopen_producer::test_l65_failure_records_effective_config_and_continues）
    # 由本票刪除 ⇒ Task 1.4「只被已刪測試引用者視為零引用」（Phase 2 試作死碼掃描實得）
    "_apply_preprocessing_degradation_metadata",
)
FRAME_ONLY_MODULE_DEFS = ("_build_column_layer_map",)  # momentum/FeatureEngineering/feature_factory.py 模組層
DEAD_SCAN_FILES = (
    "momentum/FeatureEngineering/feature_factory.py",
    "momentum/FeatureEngineering/timeframe/multi_tf_generator.py",
    "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py",
)
DEAD_REF_ROOTS = ("momentum", "api", "scripts", "tests")
# HEAD 6e07e0ad 時三檔內即已「零引用且非公開入口」之 def（qualname）；非本票造成，不計入（凍結值，產生方式見
# handoffs/run_receipts/framepath_probes/dead_scan_head.py 與其收據）
HEAD_DEAD: Tuple[str, ...] = (
    "FeatureFactory._calibration_short_columns",
    "FeatureFactory._resolve_config_float",
    "FeaturePreprocessor._rolling_last_rank_pct_for_preprocess",
)
# 具名保留（qualname → 理由）；實作批若保留零引用 def 須於此列理由並經審碼
RETAINED: Dict[str, str] = {}


def _factory_without_registry() -> FeatureFactory:
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._cgsa_registry = None
    factory._current_symbol = SYMBOL
    factory._current_timeframe = PRIMARY_TF
    return factory


def _real_close_frame(rows: int = 400) -> pd.DataFrame:
    """真實 kline 之 close（尾段 rows 列）作單欄輸入；只用於驗分派點是否先於計算拒絕。"""
    close = kline_frame()["close"].astype("float32")
    return close.iloc[-rows:].to_frame(name=f"close_{PRIMARY_TF}_trend_SMA_21")


def _raises_named(call: Callable[[], object], site: str) -> bool:
    """呼叫拋 `CGSARegistryRequiredError` 且訊息含 symbol、timeframe、呼叫點 ⇒ True。"""
    try:
        call()
    except CGSARegistryRequiredError as exc:
        msg = str(exc)
        return SYMBOL in msg and PRIMARY_TF in msg and site in msg
    return False


# ---------------------------------------------------------------- Task 1.2 分派點

@pytest.mark.parametrize("mode", ["streaming", "hybrid"])
def test_boundary_01_l3_streaming_registry_none_raises_named(monkeypatch, mode):
    monkeypatch.setenv("FFACT_L3_PERSIST_MODE", mode)
    factory = _factory_without_registry()
    config = factory._resolve_config(stat_payload())
    layer1 = _real_close_frame()
    assert _raises_named(lambda: factory._layer3_rolling_aggregation(layer1, pd.DataFrame(index=layer1.index), config),
                         "_layer3_rolling_aggregation")


def test_boundary_02_l3_in_memory_keeps_non_streaming_branch(monkeypatch):
    monkeypatch.setenv("FFACT_L3_PERSIST_MODE", "in_memory")
    factory = _factory_without_registry()
    config = factory._resolve_config(stat_payload())
    layer1 = _real_close_frame()
    result = factory._layer3_rolling_aggregation(layer1, pd.DataFrame(index=layer1.index), config)
    assert result.data.index.equals(layer1.index)
    # 非串流分支須真的算出 L3 欄（審查 r20 CODEX-R20-P1-02：只驗 index 會放過「回傳空表」）
    assert result.data.shape[1] > 0
    assert result.data.notna().to_numpy().any()
    assert int(getattr(result, "present_engines", 1)) >= 1


def test_boundary_03_frame_l65_l7_entries_removed():
    """HEAD 之 L6.5／L7 frame 入口於生產只從 frame 單週期尾段與 legacy 多週期可達（CGSA L6.5／L7 走
    `_layer7_raw_from_cgsa_pipeline`）；刪 frame 後零生產呼叫者 ⇒ 整族刪除（SPEC v16 Task 1.2／1.4）。"""
    import momentum.FeatureEngineering.feature_factory as ff_module

    for name in FRAME_ONLY_FACTORY_DEFS:
        assert not hasattr(FeatureFactory, name), name
    for name in FRAME_ONLY_MODULE_DEFS:
        assert not hasattr(ff_module, name), name
    assert hasattr(FeatureFactory, "_layer7_raw_from_cgsa_pipeline")


def test_boundary_04_generation_without_registry_raises_named(monkeypatch, tmp_path):
    """單週期生成之 L3–L7 分派點：registry 為 None（如 `_prepare_cgsa_registry` 回 None）⇒ 具名例外，不回退記憶體路徑。"""
    prepare_stat_env(monkeypatch, tmp_path)
    monkeypatch.setattr(FeatureFactory, "_prepare_cgsa_registry", lambda self, *a, **k: None)
    assert _raises_named(lambda: run_stat(tmp_path, stat_payload()), "generate_features")
    assert _no_factory_h5(tmp_path)


def test_boundary_04b_multi_tf_without_registry_raises_named(monkeypatch, tmp_path):
    prepare_stat_env(monkeypatch, tmp_path)
    monkeypatch.setattr(FeatureFactory, "_prepare_cgsa_registry", lambda self, *a, **k: None)
    payload = stat_payload([PRIMARY_TF, MULTI_TFS[-1]])
    assert _raises_named(lambda: run_stat(tmp_path, payload), "generate_multi_tf")
    assert _no_factory_h5(tmp_path)


@pytest.mark.parametrize("context", REJECTED_CONTEXTS)
def test_boundary_05_combine_layers_rejects_non_whitelist(context):
    frame = _real_close_frame(10)
    with pytest.raises(CGSARegistryRequiredError) as exc:
        FeatureFactory._combine_layers([frame], context=context)
    assert context in str(exc.value)


def test_boundary_06_combine_layers_rejects_default_context():
    with pytest.raises(CGSARegistryRequiredError):
        FeatureFactory._combine_layers([_real_close_frame(10)])


@pytest.mark.parametrize("context", WHITELIST)
def test_boundary_07_combine_layers_whitelist_concats(context):
    a = _real_close_frame(10)
    b = a.rename(columns=lambda c: c + "_b") * 2
    out = FeatureFactory._combine_layers([a, b], context=context)
    pd.testing.assert_frame_equal(out, pd.concat([a, b], axis=1))


def combine_layers_call_violations(sources: Iterable[Tuple[str, str]]) -> List[str]:
    """`_combine_layers(` 呼叫之 context 引數：須為白名單字串字面（關鍵字或第二位置引數）；缺漏或非字面皆違規。"""
    bad: List[str] = []
    for path, src in sources:
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            bad.append(f"{path}: 無法解析 {exc}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else None
            if name != "_combine_layers":
                continue
            ctx = next((k.value for k in node.keywords if k.arg == "context"), None)
            if ctx is None and len(node.args) >= 2:
                ctx = node.args[1]
            if not (isinstance(ctx, ast.Constant) and ctx.value in WHITELIST):
                bad.append(f"{path}:{node.lineno}")
    return bad


def _py_sources(roots: Iterable[str]) -> List[Tuple[str, str]]:
    out = []
    for root in roots:
        for p in sorted((REPO / root).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            out.append((str(p.relative_to(REPO)), p.read_text(encoding="utf-8")))
    return out


def test_boundary_08_combine_layers_call_sites_are_whitelist_literals():
    assert combine_layers_call_violations(_py_sources(SCAN_ROOTS)) == []


def test_boundary_09_no_ffact_use_cgsa_reads_in_production():
    hits = [path for path, src in _py_sources(("momentum", "api")) if "FFACT_USE_CGSA" in src]
    assert hits == []
    assert not hasattr(FeatureFactory, "_cgsa_enabled")
    assert not hasattr(MultiTFGenerator, "_cgsa_enabled")


def _no_factory_h5(root: Path) -> bool:
    return not any(root.rglob("*_factory.h5")) and not any(root.rglob("*_factory_meta.json"))


def test_boundary_10_residual_env_zero_still_generates_cgsa(monkeypatch, tmp_path):
    """殘留 `FFACT_USE_CGSA=0` ⇒ 無作用（不報錯、不分派），仍產 CGSA manifest 且無 `*_factory.h5`。"""
    prepare_stat_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    root, _factory, result = run_stat(tmp_path, stat_payload())
    manifests = sorted(root.rglob("feature_manifest.json"))
    assert len(manifests) == 1
    assert str(result.metadata.get("manifest_path", "")).endswith(".json")
    assert _no_factory_h5(tmp_path)


def test_boundary_11_persist_false_runs_cgsa_and_writes_completeness(monkeypatch, tmp_path):
    prepare_stat_env(monkeypatch, tmp_path)
    root, _factory, result = run_stat(tmp_path, stat_payload(), persist=False)
    for field in COMPLETENESS_FIELD_NAMES:
        assert field in result.metadata, field
    assert result.metadata["present_timeframes"] == [PRIMARY_TF]
    assert result.metadata.get("run_status") == "complete"
    # CGSA 之 features_df 只帶時間索引（欄值在 registry／落盤），persist=False 亦同；以特徵數與 registry 群組驗有算
    assert int(result.feature_count) > 0
    assert _factory._cgsa_registry is not None
    assert not any(root.rglob("feature_manifest.json"))
    assert _no_factory_h5(tmp_path)


# ---------------------------------------------------------------- Task 1.3 多週期與列對應

def test_boundary_12_legacy_symbols_absent_from_momentum():
    hits = [(path, sym) for path, src in _py_sources(("momentum",)) for sym in LEGACY_SYMBOLS if sym in src]
    assert hits == []
    assert not hasattr(MultiTFGenerator, "_generate_multi_tf_legacy")
    assert not hasattr(MultiTFGenerator, "_combine_layers")


def test_boundary_13_set_no_start_calibration_takes_no_arguments():
    params = list(inspect.signature(FeaturePreprocessor.set_no_start_calibration).parameters)
    assert params == ["self"]


def test_boundary_14_frame_timeframe_taggers_removed():
    """`MultiTFGenerator._apply_timeframe_tag` 刪 registry 為 None 側後只剩原樣回傳、且 HEAD 兩處呼叫
    （multi_tf_generator.py:1568 legacy、feature_factory.py:4492 frame L7）皆隨 frame 碼刪除 ⇒ 零生產呼叫者，
    依 Task 1.4 整刪；`FeatureFactory._apply_timeframe_tag`（frame L7 專用）同。CGSA 標記走
    `feature_naming.tag_timeframe`／`FeatureFactory._timeframe_tagged_name`（§C 保留）。"""
    assert not hasattr(MultiTFGenerator, "_apply_timeframe_tag")
    assert not hasattr(FeatureFactory, "_apply_timeframe_tag")
    assert hasattr(FeatureFactory, "_timeframe_tagged_name")


# ---------------------------------------------------------------- Task 1.4 死碼掃除

def _defs(src: str) -> List[str]:
    """三檔內全部 def（含巢狀函式與巢狀類別方法；審查 r20 CODEX-R20-P1-03），以 `.` 連接之限定名。"""
    out: List[str] = []

    def visit(body: list, prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append(prefix + node.name)
                visit(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, ast.ClassDef):
                visit(node.body, f"{prefix}{node.name}.")
            else:  # if／for／while／with／try 等複合敘述內之定義
                for field in ("body", "orelse", "finalbody"):
                    sub = getattr(node, field, None)
                    if isinstance(sub, list):
                        visit(sub, prefix)
                for handler in getattr(node, "handlers", []) or []:
                    visit(handler.body, prefix)

    visit(ast.parse(src).body, "")
    return out


def _referenced_names(sources: Iterable[Tuple[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for _path, src in sources:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.isidentifier():
                name = node.value
            if name:
                counts[name] = counts.get(name, 0) + 1
    return counts


def dead_defs(scan_sources: Iterable[Tuple[str, str]], ref_sources: Iterable[Tuple[str, str]]) -> Set[str]:
    """`scan_sources` 內之 def（模組層函式與類別方法）中，非公開入口（名稱以單底線起、非 dunder）且於
    `ref_sources` 全部 .py 之 Name／Attribute／識別字字串常數零出現者（qualname 集合）。"""
    refs = _referenced_names(ref_sources)
    out: Set[str] = set()
    for _path, src in scan_sources:
        for qual in _defs(src):
            name = qual.split(".")[-1]
            if name.startswith("__") or not name.startswith("_"):
                continue
            if refs.get(name, 0) == 0:
                out.add(qual)
    return out


def ticket_dead_defs() -> Set[str]:
    scan = [(p, (REPO / p).read_text(encoding="utf-8")) for p in DEAD_SCAN_FILES]
    return dead_defs(scan, _py_sources(DEAD_REF_ROOTS)) - set(HEAD_DEAD) - set(RETAINED)


def test_boundary_15_no_ticket_dead_defs_remain():
    assert sorted(ticket_dead_defs()) == []
    assert all(isinstance(v, str) and v.strip() for v in RETAINED.values())
    # HEAD_DEAD 須等於其產生收據（審查 r22 CODEX-R22-P1-02：豁免集合不得自行擴張；本檔內容另由處置驗證器之
    # sha256 凍結，掃描器與豁免改動皆須回 TODO 重審）
    import json

    receipt = json.loads((REPO / "handoffs/run_receipts/20261008-framepath-dead-scan-head.json").read_text(encoding="utf-8"))
    assert tuple(receipt["head_dead"]) == HEAD_DEAD
    assert receipt["scan_files"] == list(DEAD_SCAN_FILES) and receipt["ref_roots"] == list(DEAD_REF_ROOTS)


# ---------------------------------------------------------------- mutation

def test_mutation_dispatch_without_named_raise_is_detected(monkeypatch):
    """分派點之具名例外改回靜默返回（舊分支）⇒ `_raises_named` 為 False（驗收轉紅）。"""
    monkeypatch.setenv("FFACT_L3_PERSIST_MODE", "streaming")
    factory = _factory_without_registry()
    config = factory._resolve_config(stat_payload())
    layer1 = _real_close_frame()
    monkeypatch.setattr(FeatureFactory, "_layer3_rolling_aggregation", lambda self, l1, l2, cfg: None)
    assert not _raises_named(
        lambda: factory._layer3_rolling_aggregation(layer1, pd.DataFrame(index=layer1.index), config),
        "_layer3_rolling_aggregation",
    )


def test_mutation_combine_layers_scan_flags_nonliteral_and_unlisted():
    src = (
        "def f(x, ctx):\n"
        "    FeatureFactory._combine_layers([x], context=ctx)\n"
        "    FeatureFactory._combine_layers([x], context='layer7_final')\n"
        "    FeatureFactory._combine_layers([x])\n"
        "    FeatureFactory._combine_layers([x], 'layer3_input')\n"
    )
    assert combine_layers_call_violations([("m.py", src)]) == ["m.py:2", "m.py:3", "m.py:4"]


def test_mutation_dead_scan_counts_added_zero_reference_def():
    scan = [("m.py", "class A:\n    def _used(self):\n        pass\n\n    def _orphan_framepath_probe(self):\n        pass\n")]
    refs = [("n.py", "A()._used()\n")]
    assert dead_defs(scan, refs) == {"A._orphan_framepath_probe"}
    nested = [("m.py", "def outer():\n    def _orphan_nested_probe():\n        pass\n    return 1\n\n"
                       "class B:\n    class C:\n        def _orphan_inner_method(self):\n            pass\n")]
    assert dead_defs(nested, [("n.py", "outer()\nB.C\n")]) == {"outer._orphan_nested_probe", "B.C._orphan_inner_method"}
