"""FFDSTAR Task 1.1（docs/FFDSTAR_SPEC.md）：離開路徑盤點之契約 JSON 驗收。

契約＝`momentum/FeatureEngineering/contracts/run_provenance.json`（唯一真相源）；本檔不列舉任何狀態值，值集一律讀契約。
③ 之「實際紀錄中出現之值」取自 §V 全格（`preprov_helpers.CELLS`）與本檔之單元案例之落盤紀錄、manifest 群組表與
前處理器紀錄；真實 kline 短窗、同模組同格只生成一次。實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import copy
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

import pytest

from momentum.FeatureEngineering import run_provenance as rp
from tests.feature_engineering import ffstat_helpers as fsh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

_SOURCE_RE = re.compile(r"^(?P<path>[^:\s]+):(?P<line>\d+)$")
_PREPROCESSOR = "momentum/FeatureEngineering/preprocessing/feature_preprocessor.py"
#: SPEC Task 1.1 驗證①：`_sources` 之檔須位於特徵工廠寫入路徑（目錄項以 `/` 結尾＝其下任意檔；檔案項＝逐字相等）。
#: 契約 `source_scope` 須等於本集合（防契約自行放寬範圍）。
SPEC_SOURCE_SCOPE = frozenset({
    "momentum/FeatureEngineering/preprocessing/",
    "momentum/FeatureEngineering/feature_storage.py",
    "momentum/FeatureEngineering/feature_factory.py",
})
#: CODEX-R6-P2-01 之反例檔：他域含同字面之行（`ICEngine.set_timeframe` 回傳 "applied"，錨點 :167）
_FOREIGN_SAME_LITERAL = "momentum/Analysis/ic_engine.py"
#: 紀錄函式之判準（唯一定義處）：被呼叫者末段名稱（`f(...)` 之 `f`、`x.f(...)` 之 `f`）含 "record"
#: （如 `_record_execution`、`_record_decision`、`record_*`）
RECORDING_CALLEE_RE = re.compile(r"record")
#: 單元案例之校準長度 N（同 test_preprov_collect.UNIT_CALIBRATION_BARS；短窗 < v58 日內預設 1000）
UNIT_CALIBRATION_BARS = 100


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_contract"))


# ---------------------------------------------------------------------------------------------- oracle（純函式）

_STMT_LIST_FIELDS = ("body", "orelse", "finalbody", "handlers", "cases")


def _innermost_statement(tree: ast.AST, line: int) -> Optional[ast.stmt]:
    """涵蓋 `line` 之最內層陳述式（其子陳述式皆不涵蓋該行者）；無 ⇒ None。"""
    best: Optional[ast.stmt] = None
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and node.lineno <= line <= (node.end_lineno or node.lineno):
            if best is None or (node.lineno, -(node.end_lineno or node.lineno)) >= (
                    best.lineno, -(best.end_lineno or best.lineno)):
                best = node
    return best


def _statement_string_literals(stmt: ast.stmt) -> Set[str]:
    """陳述式本身（複合陳述式只取標頭：排除 body／orelse／finalbody／handlers／cases 之子陳述式）之字串字面集合。"""
    out: Set[str] = set()
    stack: List[ast.AST] = []
    for field, value in ast.iter_fields(stmt):
        if field in _STMT_LIST_FIELDS:
            continue
        stack.extend(value if isinstance(value, list) else [value])
    while stack:
        node = stack.pop()
        if not isinstance(node, ast.AST):
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.add(node.value)
        stack.extend(ast.iter_child_nodes(node))
    return out


_AST_CACHE: Dict[str, ast.AST] = {}


def _parsed(target: Path) -> ast.AST:
    key = str(target)
    if key not in _AST_CACHE:
        _AST_CACHE[key] = ast.parse(target.read_text(encoding="utf-8"))
    return _AST_CACHE[key]


def recording_callee(call: ast.Call) -> Optional[str]:
    """呼叫之被呼叫者末段名稱符合 `RECORDING_CALLEE_RE` ⇒ 該名稱；否則 None。"""
    func = call.func
    name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None
    return name if name is not None and RECORDING_CALLEE_RE.search(name) else None


def statement_record_call(stmt: Optional[ast.stmt]) -> Optional[ast.Call]:
    """陳述式本身即一個紀錄函式呼叫（`f(...)`、`x = f(...)`、`x: T = f(...)`、`return f(...)`）⇒ 該呼叫；否則 None
    （複合陳述式之標頭、其他陳述式、巢狀於其他運算式內之紀錄呼叫皆不算）。"""
    value = stmt.value if isinstance(stmt, (ast.Expr, ast.Assign, ast.AnnAssign, ast.Return)) else None
    return value if isinstance(value, ast.Call) and recording_callee(value) is not None else None


def record_call_literals(call: ast.Call) -> Set[str]:
    """紀錄呼叫之實參（位置與關鍵字引數之值，含其子運算式如條件運算式）中之字串字面集合。"""
    out: Set[str] = set()
    for arg in list(call.args) + [kw.value for kw in call.keywords]:
        for node in ast.walk(arg):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                out.add(node.value)
    return out


def in_source_scope(rel: str, scope: Any) -> bool:
    """`rel`（repo 相對 POSIX 路徑）屬 `scope`：目錄項（`/` 結尾）為其下任意檔，檔案項逐字相等。"""
    return any(rel.startswith(str(s)) if str(s).endswith("/") else rel == str(s) for s in scope or ())


def source_violations(spec: Mapping[str, Any]) -> List[str]:
    """① 每個值集非空；每值恰有 `_sources`（非空清單）；每個 `path:line` 指向 repo 內存在之檔之非註解非空行；該檔屬契約
    `source_scope`（特徵工廠寫入路徑；CODEX-R6-P2-01）；該行所屬之單一 AST 陳述式本身為對紀錄函式之呼叫
    （`RECORDING_CALLEE_RE`），且其實參含該值之字串字面（`ast.Constant` 逐字相等）——指向無關可執行行
    （CODEX-R5-P2-02）、或他域含同字面之行（例 `momentum/Analysis/ic_engine.py:167` 回傳 "applied"）即紅；
    `_sources` 不得有值集外之鍵。"""
    out: List[str] = []
    scope = list(spec.get("source_scope") or [])
    if not scope:
        out.append("契約無 source_scope ⇒ 出處範圍未定")
    for path in ph.enum_paths(spec):
        node = ph.enum_node(path, spec)
        values, sources = list(node["values"]), dict(node["_sources"])
        if not values:
            out.append(f"{path}: 值集為空")
        for extra in sorted(set(sources) - set(values)):
            out.append(f"{path}: _sources 有值集外之鍵 {extra!r}")
        for value in values:
            refs = sources.get(value)
            if not isinstance(refs, list) or not refs:
                out.append(f"{path}.{value}: 無 _sources")
                continue
            for ref in refs:
                m = _SOURCE_RE.match(str(ref))
                if not m:
                    out.append(f"{path}.{value}: _sources 格式非 path:line：{ref!r}")
                    continue
                target = ph.REPO / m["path"]
                if not target.is_file():
                    out.append(f"{path}.{value}: 檔不存在 {ref}")
                    continue
                lines = target.read_text(encoding="utf-8").splitlines()
                n = int(m["line"])
                text = lines[n - 1].strip() if 1 <= n <= len(lines) else ""
                if not text or text.startswith("#"):
                    out.append(f"{path}.{value}: {ref} 為空行或註解行")
                    continue
                if not in_source_scope(m["path"], scope):
                    out.append(f"{path}.{value}: {ref} 不在契約 source_scope（特徵工廠寫入路徑）內")
                if not target.suffix == ".py":
                    out.append(f"{path}.{value}: {ref} 非 Python 原始碼（無法驗字串字面）")
                    continue
                call = statement_record_call(_innermost_statement(_parsed(target), n))
                if call is None:
                    out.append(f"{path}.{value}: {ref} 之陳述式非紀錄函式呼叫（被呼叫者名須合 {RECORDING_CALLEE_RE.pattern!r}）")
                if call is None or value not in record_call_literals(call):
                    out.append(f"{path}.{value}: {ref} 之陳述式之紀錄呼叫實參不含該值之字串字面")
    return out


def pattern_violations(spec: Mapping[str, Any]) -> List[str]:
    """② 每個值合契約 `value_pattern`。"""
    pattern = re.compile(str(spec["value_pattern"]))
    return [f"{path}: {value!r}" for path in ph.enum_paths(spec)
            for value in ph.contract_values(path, spec) if not pattern.fullmatch(str(value))]


def coverage_violations(spec: Mapping[str, Any], observed: Mapping[str, Set[str]]) -> List[str]:
    """③ 觀測值 ⊆ 契約值集；契約每值至少被觀測一次，否則須列於 `_unreachable`（鍵＝`<值集路徑>.<值>` 或值本身，
    值須含至少一個 `path:line` 碼證）。"""
    out: List[str] = []
    unreachable = dict(spec.get("_unreachable") or {})
    for path in ph.enum_paths(spec):
        values = set(ph.contract_values(path, spec))
        seen = set(observed.get(path, set()))
        for value in sorted(seen - values):
            out.append(f"{path}: 觀測值 {value!r} 不在契約")
        for value in sorted(values - seen):
            reason = unreachable.get(f"{path}.{value}", unreachable.get(value))
            if reason is None:
                out.append(f"{path}: 契約值 {value!r} 無任何格／單元案例產出且未列 _unreachable")
            elif not re.search(r"[\w./-]+\.\w+:\d+", json_text(reason)):
                out.append(f"{path}: _unreachable {value!r} 無 path:line 碼證")
    return out


def json_text(obj: Any) -> str:
    import json

    return obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)


def observed_from_table(table: Any, spec: Mapping[str, Any]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for column, path in ph.record_enum_columns(spec).items():
        if column in table.columns:
            out.setdefault(path, set()).update(str(v) for v in table[column].dropna().unique())
    return out


def observed_from_groups(groups: Mapping[str, Mapping[str, Any]]) -> Dict[str, Set[str]]:
    """群組表之觀測值：`arm`→群組臂值集、`status`→群組狀態值集、`fallback`（清單；契約 `fallback_values._doc`）之
    每個元素→回退值集（非清單之舊形亦逐值收入，其型別另由 `manifest_fallback_violations` 判紅）。"""
    out: Dict[str, Set[str]] = {"group_arm_values": set(), "group_status_values": set(), "fallback_values": set()}
    for info in groups.values():
        for key, path in (("arm", "group_arm_values"), ("status", "group_status_values")):
            if info.get(key) is not None:
                out[path].add(str(info[key]))
        fallback = info.get("fallback")
        for item in (fallback if isinstance(fallback, list) else [] if fallback is None else [fallback]):
            out["fallback_values"].add(str(item))
    return out


def manifest_fallback_violations(groups: Mapping[str, Mapping[str, Any]], spec: Mapping[str, Any]) -> List[str]:
    """manifest 群組表之 `fallback`（契約 `manifest_group_keys`）須存在且為清單（可多重、依發生序；無回退＝空清單），
    元素皆屬契約 `fallback_values`（SPEC v3 盤點輸入③）。"""
    allowed = set(ph.contract_values("fallback_values", spec))
    out: List[str] = []
    for gid, info in groups.items():
        fallback = info.get("fallback", "<缺鍵>")
        if not isinstance(fallback, list):
            out.append(f"{gid}: fallback 非清單：{fallback!r}")
            continue
        out.extend(f"{gid}: fallback 元素 {item!r} 不屬 fallback_values" for item in fallback if item not in allowed)
    return out


def observed_from_records(records: Mapping[Tuple[str, str], Mapping[str, Any]], spec: Mapping[str, Any]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    for record in records.values():
        for column, path in ph.record_enum_columns(spec).items():
            if record.get(column) is not None:
                out.setdefault(path, set()).add(str(record[column]))
    return out


def merge(into: Dict[str, Set[str]], more: Mapping[str, Set[str]]) -> None:
    for key, values in more.items():
        into.setdefault(key, set()).update(values)


def observed_from_run(handle: ph.RunHandle, spec: Mapping[str, Any]) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = {}
    manifest = ph.load_manifest(handle.run_dir)
    for kind in ("raw", "processed"):
        if kind in manifest.get("artifacts", {}):
            merge(out, observed_from_table(ph.provenance_table(handle.run_dir, kind), spec))
            merge(out, observed_from_groups(manifest["artifacts"][kind]["provenance"]["groups"]))
    return out


# ---------------------------------------------------------------------------------------------- 單元案例（真實特徵）

def _fracdiff_early_exit_line() -> int:
    """`_apply_fractional_differencing` 內 `if not HAS_STATSMODELS:` 之行號（碼證比對錨點）。"""
    lines = (ph.REPO / _PREPROCESSOR).read_text(encoding="utf-8").splitlines()
    start = next(i for i, t in enumerate(lines) if "def _apply_fractional_differencing(" in t)
    return next(i for i in range(start, len(lines)) if "if not HAS_STATSMODELS" in lines[i]) + 1


def statsmodels_unavailable_records(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """邊界①：statsmodels 不可用 ⇒ fracdiff 於入口早退；以真實 run 之 L1 特徵欄跑單一前處理器。"""
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.preprocessing import feature_preprocessor as fpm

    handle = runs.get("h1_stat_off")
    frame, layers = ph.real_feature_frame(handle, 6, layer="L1")
    factory = create_feature_factory(cache_dir=ph.KLINE_DIR, validate_continuity=False)
    payload = copy.deepcopy(ph.CELLS["h1_stat_on"]["payload"])
    # 單元前處理器以短窗 frame 本身為校準前史（約 720 列 < FFSTAT v58 日內預設 1000）⇒ 明示校準長度 N
    payload["preprocessing"]["calibration_bars"] = UNIT_CALIBRATION_BARS
    config = factory._resolve_config(payload).preprocessing.model_dump()
    monkeypatch.setattr(fpm, "HAS_STATSMODELS", False)
    pre = fpm.FeaturePreprocessor(config, column_layer_map=layers)
    fsh.attach_unit_calibration(pre, frame)
    pre.transform(frame)
    return ph.preprocessor_records(pre)


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_00_load_contract_is_the_file() -> None:
    """`run_provenance.load_contract()` 回傳契約檔本身（單一真相源；不得另組）。"""
    assert rp.CONTRACT_PATH == ph.CONTRACT_PATH
    assert rp.load_contract() == ph.contract()


def test_verification_01_sources_point_to_code_lines() -> None:
    """① 每個狀態值之 `_sources` 之每個 `path:line` 指向非註解非空行，且該行（或其所屬之單一陳述式）含該值之字串字面
    （且值集非空）。"""
    assert source_violations(ph.contract()) == []


def test_verification_02_values_match_pattern() -> None:
    """② 契約值皆合 `value_pattern`。"""
    spec = ph.contract()
    assert spec["value_pattern"] == "^[a-z][a-z0-9_]*$"
    assert all(ph.contract_values(p, spec) for p in ph.enum_paths(spec)), "值集為空 ⇒ ② 空轉"
    assert pattern_violations(spec) == []


def test_verification_03_observed_values_subset_and_covered(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """③ §V 全格之實際紀錄值集 ⊆ 契約；契約每值至少被一格或單元案例產出，否則列 `_unreachable` 附碼證。"""
    spec = ph.contract()
    observed: Dict[str, Set[str]] = {}
    for cell in ph.CELLS:
        for handle in runs.all_of(cell):
            merge(observed, observed_from_run(handle, spec))
            pre = ph.observation(handle).l65_preprocessor
            if pre is not None:
                merge(observed, observed_from_records(ph.preprocessor_records(pre), spec))
                merge(observed, observed_from_groups(ph.preprocessor_groups(pre)))
    merge(observed, observed_from_run(runs.get("h12h1_native_fallback"), spec))
    merge(observed, observed_from_run(runs.get("ic_first_empty"), spec))
    # SPEC v4 §V replace 格之 shard 串流臂：分片目標壓小之 replace 變體（`ph.VARIANTS["h1_replace_sharded"]`）之群組表
    merge(observed, observed_from_groups(ph.preprocessor_groups(
        ph.observation(runs.get("h1_replace_sharded")).l65_preprocessor)))
    merge(observed, observed_from_records(statsmodels_unavailable_records(runs, monkeypatch), spec))
    assert sum(len(v) for v in observed.values()) > 0, "未觀測到任何值 ⇒ ③ 空轉"
    assert coverage_violations(spec, observed) == []


def test_verification_01b_source_scope_is_spec_scope() -> None:
    """① 之出處範圍：契約 `source_scope` 恰為 SPEC Task 1.1 驗證①所列之特徵工廠寫入路徑（不得放寬或縮窄）；
    紀錄函式判準命中既有紀錄函式名、不命中無關函式名（判準本身非空轉）。"""
    spec = ph.contract()
    assert set(spec["source_scope"]) == SPEC_SOURCE_SCOPE
    assert len(spec["source_scope"]) == len(SPEC_SOURCE_SCOPE)
    assert in_source_scope(_PREPROCESSOR, spec["source_scope"])
    assert not in_source_scope(_FOREIGN_SAME_LITERAL, spec["source_scope"])
    hits = [recording_callee(ast.parse(src, mode="eval").body) for src in
            ("self._record_execution(c, 'x')", "_record_decision(c)", "record_group_arm(g, 'x')", "logger.info('x')")]
    assert hits == ["_record_execution", "_record_decision", "record_group_arm", None]


def test_verification_04_fallback_value_set_and_manifest_fallback_is_list(runs: ph.RunCache) -> None:
    """SPEC v3 盤點輸入③：契約另設回退值集 `fallback_values`（與其他值集同受 ①②③ 檢查：已列入 `enum_paths`），
    manifest 群組之 `fallback` 為該值集之值之清單（可多重、依發生序）；native 回退變體至少一群組帶非空回退清單。"""
    spec = ph.contract()
    assert "fallback_values" in ph.enum_paths(spec)
    assert "fallback" in spec["manifest_group_keys"]
    assert "清單" in str(spec["fallback_values"].get("_doc", ""))
    assert ph.contract_values("fallback_values", spec), "回退值集為空（Task 1.1 待填）"
    for cell in ("h1_stat_on", "h12h1_native_fallback"):
        groups = ph.provenance_pointer(runs.get(cell).run_dir, "raw")["groups"]
        assert groups, cell
        assert manifest_fallback_violations(groups, spec) == [], cell
    fb_groups = ph.provenance_pointer(runs.get("h12h1_native_fallback").run_dir, "raw")["groups"]
    assert any(info["fallback"] for info in fb_groups.values()), "native 回退變體無任何群組帶回退 ⇒ 空轉"
    pre = ph.observation(runs.get("h12h1_native_fallback")).l65_preprocessor
    assert manifest_fallback_violations(ph.preprocessor_groups(pre), spec) == []


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_statsmodels_unavailable_fracdiff_early_exit(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界①：statsmodels 不可用之 fracdiff 早退——每欄恰一筆紀錄、fracdiff 未套用（d 為 null），其 fracdiff 狀態值之
    `_sources` 含該早退點（`_apply_fractional_differencing` 之 `if not HAS_STATSMODELS` 起兩行內）。"""
    spec = ph.contract()
    records = statsmodels_unavailable_records(runs, monkeypatch)
    assert records, "無紀錄 ⇒ 早退未記"
    anchor = _fracdiff_early_exit_line()
    statuses = {str(r["fractional_differencing"]) for r in records.values()}
    assert len(statuses) == 1, statuses
    status = statuses.pop()
    assert status in ph.contract_values("step_status_values.fractional_differencing", spec)
    refs = ph.enum_node("step_status_values.fractional_differencing", spec)["_sources"][status]
    hits = [r for r in refs if str(r).startswith(_PREPROCESSOR + ":") and anchor <= int(str(r).rsplit(":", 1)[1]) <= anchor + 2]
    assert hits, f"值 {status!r} 之 _sources {refs} 不含早退點 {_PREPROCESSOR}:{anchor}"
    assert all(r.get("d") is None and r.get("fracdiff") is not True for r in records.values())


def test_boundary_02_columns_outside_fracdiff_layers(runs: ph.RunCache) -> None:
    """邊界②：目標層外之欄（fracdiff 不涵蓋）——其 fracdiff 狀態值屬契約、且不同於實際 fracdiff 之欄之狀態值；d 為 null。"""
    from momentum.core.config import get_fracdiff_layers

    spec = ph.contract()
    handle = runs.get("h1_stat_on")
    table = ph.provenance_table(handle.run_dir, "raw").set_index("output_column")
    layers = get_fracdiff_layers()
    layer_of = {ph.output_name(c, tf): layer for cols, _a, tf, layer in ph.observation(handle).l65_inputs.values()
                for c in cols}
    outside = sorted(n for n, layer in layer_of.items() if "ALL" not in layers and layer not in layers)
    applied = table.index[table["fracdiff"].fillna(False).astype(bool)]
    assert outside and len(applied), "目標層外或已套用 fracdiff 之欄為空 ⇒ 邊界空轉"
    outside_status = set(table.loc[outside, "fractional_differencing"].astype(str))
    applied_status = set(table.loc[applied, "fractional_differencing"].astype(str))
    assert outside_status <= set(ph.contract_values("step_status_values.fractional_differencing", spec))
    assert not outside_status & applied_status
    assert table.loc[outside, "d"].isna().all()


def test_boundary_03_stationarity_off_null_decisions(runs: ph.RunCache) -> None:
    """邊界③：平穩化關閉——平穩化決策欄全 null；fracdiff／ADF 步驟狀態各為單一契約值，且不同於平穩化開啟格中實際套用之值。"""
    spec = ph.contract()
    off = ph.provenance_table(runs.get("h1_stat_off").run_dir, "raw")
    on = ph.provenance_table(runs.get("h1_stat_on").run_dir, "raw")
    assert set(ph.STATIONARITY_DECISION_COLUMNS) <= set(spec["record_columns"])
    assert len(off) > 0
    for column in ph.STATIONARITY_DECISION_COLUMNS:
        assert off[column].isna().all(), column
    applied = on["fracdiff"].fillna(False).astype(bool)
    for step in ("fractional_differencing", "adf_differencing"):
        values = set(off[step].astype(str))
        assert len(values) == 1 and values <= set(ph.contract_values(f"step_status_values.{step}", spec)), (step, values)
    assert not set(off["fractional_differencing"].astype(str)) & set(on.loc[applied, "fractional_differencing"].astype(str))


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_contract_missing_observed_value_breaks_subset(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC Task 1.1）：契約刪一個實際會出現之值 ⇒ ③ 之 oracle 轉紅。"""
    spec = ph.contract()
    observed = observed_from_run(runs.get("h1_stat_on"), spec)
    path = next(p for p in ph.enum_paths(spec) if observed.get(p))
    value = sorted(observed[path])[0]
    mutant = copy.deepcopy(spec)
    node = ph.enum_node(path, mutant)
    node["values"] = [v for v in node["values"] if v != value]
    node["_sources"].pop(value, None)
    monkeypatch.setattr(rp, "load_contract", lambda: mutant)
    assert coverage_violations(rp.load_contract(), {path: {value}}) != []
    assert not [v for v in coverage_violations(spec, {path: {value}}) if "不在契約" in v]


def test_mutation_source_pointing_to_comment_line_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：某值之 `_sources` 改指註解行 ⇒ ① 之 oracle 轉紅。"""
    spec = ph.contract()
    lines = (ph.REPO / _PREPROCESSOR).read_text(encoding="utf-8").splitlines()
    comment = next(i + 1 for i, t in enumerate(lines) if t.strip().startswith("#"))
    mutant = copy.deepcopy(spec)
    path = ph.enum_paths(mutant)[0]
    node = ph.enum_node(path, mutant)
    node["values"] = list(node["values"]) or ["mutant_value"]
    node["_sources"] = {v: [f"{_PREPROCESSOR}:{comment}"] for v in node["values"]}
    monkeypatch.setattr(rp, "load_contract", lambda: mutant)
    assert any("註解行" in v for v in source_violations(rp.load_contract()))


def _violations_of(path: str, value: str, violations: List[str]) -> List[str]:
    return [v for v in violations if v.startswith(f"{path}.{value}:")]


def _literal_anchor(rel: str) -> Tuple[str, int]:
    """檔內第一個「陳述式本身為紀錄函式呼叫、且其實參含合樣式之字串字面」之 (字面, 行號)（契約尚無值時之正對照錨點；
    ① 只認紀錄函式呼叫，故正對照亦須為之。只驗 oracle 機制，字面不必是契約值）。"""
    tree = ast.parse((ph.REPO / rel).read_text(encoding="utf-8"))
    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for node in sorted((n for n in ast.walk(tree) if isinstance(n, ast.stmt)), key=lambda n: n.lineno):
        call = statement_record_call(node)
        literals = sorted(s for s in record_call_literals(call) if pattern.fullmatch(s)) if call is not None else []
        if literals:
            return literals[0], node.lineno
    raise AssertionError(f"{rel} 無「紀錄函式呼叫且實參含合樣式字面」之陳述式可作正對照")


def _unrelated_executable_line(rel: str, value: str) -> int:
    """同檔中一個無關之可執行行：第一個 import 陳述式（非註解非空、且其陳述式不含 `value` 之字串字面）。"""
    tree = ast.parse((ph.REPO / rel).read_text(encoding="utf-8"))
    for node in sorted((n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))),
                       key=lambda n: n.lineno):
        if value not in _statement_string_literals(node):
            return node.lineno
    raise AssertionError(f"{rel} 無 import 陳述式可作無關可執行行")


def test_mutation_source_pointing_to_unrelated_executable_line_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R5-P2-02）：某值之 `_sources` 改指同檔無關可執行行（import 陳述式；非註解非空）⇒ ① 之 oracle 轉紅，
    且紅因為「陳述式不含該值之字串字面」而非註解／空行檢查。正對照：改前之 source（契約有值者取契約實值與其第一個
    source；契約尚無值則取檔內實存字串字面之行）於該值集路徑下無任何違規。"""
    spec = ph.contract()
    filled = [(p, v) for p in ph.enum_paths(spec) for v in ph.contract_values(p, spec)]
    mutant = copy.deepcopy(spec)
    if filled:
        path, value = filled[0]
        good = str(ph.enum_node(path, spec)["_sources"][value][0])
        rel, line = good.rsplit(":", 1)
        node = ph.enum_node(path, mutant)
        node["_sources"][value] = [good]
    else:
        rel = _PREPROCESSOR
        path = ph.enum_paths(mutant)[0]
        value, anchor = _literal_anchor(rel)
        line = str(anchor)
        node = ph.enum_node(path, mutant)
        node["values"] = [value]
        node["_sources"] = {value: [f"{rel}:{line}"]}
    assert _violations_of(path, value, source_violations(mutant)) == [], "正對照不成立 ⇒ mutation 空轉"
    bad = _unrelated_executable_line(rel, value)
    assert str(bad) != line
    node["_sources"][value] = [f"{rel}:{bad}"]
    monkeypatch.setattr(rp, "load_contract", lambda: mutant)
    caught = _violations_of(path, value, source_violations(rp.load_contract()))
    assert any("不含該值之字串字面" in v for v in caught), caught
    assert not any("註解行" in v for v in caught), caught


def _foreign_same_literal_line(rel: str, value: str) -> int:
    """他域檔中第一個「`return <value 之字串字面>`」陳述式之行號（CODEX-R6-P2-01 反例：`ICEngine.set_timeframe` 回傳
    "applied"，審查時錨點 :167；以 AST 定位，行號漂移不影響）。"""
    tree = _parsed(ph.REPO / rel)
    for node in sorted((n for n in ast.walk(tree) if isinstance(n, ast.Return)), key=lambda n: n.lineno):
        if isinstance(node.value, ast.Constant) and node.value.value == value:
            return node.lineno
    raise AssertionError(f"{rel} 無 return {value!r} 之陳述式 ⇒ 反例不存在")


def test_mutation_source_pointing_to_other_domain_same_literal_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R6-P2-01）：`winsorization` 之 SPEC 點名值 `applied` 之 `_sources` 改指
    `momentum/Analysis/ic_engine.py` 中 `return "applied"` 之行 ⇒ ① 轉紅，紅因含「不在 source_scope」與「非紀錄函式
    呼叫」。反證非空轉：該行之陳述式確含該值字面（舊之「陳述式含值字面」判準會放行）。正對照：契約之真實出處無違規。"""
    spec = ph.contract()
    path, value, _where = ph.SPEC_NAMED_VALUES["winsor_applied"]
    good = list(ph.enum_node(path, spec)["_sources"].get(value) or [])
    assert good, f"契約 {path}.{value} 尚無 _sources（Task 1.1 待填）⇒ 無正對照"
    assert _violations_of(path, value, source_violations(spec)) == [], "正對照不成立 ⇒ mutation 空轉"
    line = _foreign_same_literal_line(_FOREIGN_SAME_LITERAL, value)
    stmt = _innermost_statement(_parsed(ph.REPO / _FOREIGN_SAME_LITERAL), line)
    assert stmt is not None and value in _statement_string_literals(stmt), "反例行不含該值字面 ⇒ mutation 空轉"
    mutant = copy.deepcopy(spec)
    node = ph.enum_node(path, mutant)
    node["_sources"][value] = [f"{_FOREIGN_SAME_LITERAL}:{line}"]
    monkeypatch.setattr(rp, "load_contract", lambda: mutant)
    caught = _violations_of(path, value, source_violations(rp.load_contract()))
    assert any("source_scope" in v for v in caught), caught
    assert any("非紀錄函式呼叫" in v for v in caught), caught
    assert not any("註解行" in v or "檔不存在" in v for v in caught), caught


def test_mutation_manifest_group_fallback_scalar_is_caught(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC v3 盤點輸入③）：manifest 紀錄指標之群組回退清單改為單值（舊形）、或元素改為群組臂值（以
    monkeypatch 換入改壞之指標讀取）⇒ `manifest_fallback_violations` 轉紅。正對照：native 回退變體之真實群組表無違規。"""
    spec = ph.contract()
    run_dir = runs.get("h12h1_native_fallback").run_dir
    pointer = copy.deepcopy(ph.provenance_pointer(run_dir, "raw"))
    assert manifest_fallback_violations(pointer["groups"], spec) == [], "正對照不成立 ⇒ mutation 空轉"
    gid = next(g for g, info in pointer["groups"].items() if info.get("fallback"))
    scalar = copy.deepcopy(pointer)
    scalar["groups"][gid]["fallback"] = scalar["groups"][gid]["fallback"][0]
    monkeypatch.setattr(ph, "provenance_pointer", lambda _run_dir, _kind: copy.deepcopy(scalar))
    assert any(v.startswith(f"{gid}: fallback 非清單")
               for v in manifest_fallback_violations(ph.provenance_pointer(run_dir, "raw")["groups"], spec))
    foreign = sorted(set(ph.contract_values("group_arm_values", spec)) - set(ph.contract_values("fallback_values", spec)))
    assert foreign, "群組臂值集與回退值集無差集 ⇒ 第二 mutant 無對象"
    as_arm = copy.deepcopy(pointer)
    as_arm["groups"][gid]["fallback"] = [foreign[0]]
    monkeypatch.setattr(ph, "provenance_pointer", lambda _run_dir, _kind: copy.deepcopy(as_arm))
    assert any("不屬 fallback_values" in v
               for v in manifest_fallback_violations(ph.provenance_pointer(run_dir, "raw")["groups"], spec))
