"""NUMVIEW Task 0.3（事前登記判準與決定紀錄 schema）、Task 0.4（量測格清單與估時收據）、Task 1.5（政策決定點）之驗收
（docs/NUMVIEW_SPEC.md）。

選取規則：Task 0.4 之全部測試（含其邊界與 mutation）名稱皆含子字串 `estimate`（SPEC Task 0.4 驗證命令 `-k estimate`）；
Task 0.3／1.5 之測試名稱一律不含該子字串。

驗證（Task 0.3）：①判準檔（`numview_helpers.CRITERIA_PATH`；或邊界 05 之 `preregistered_criteria_v2.json`）合其內嵌 schema
（頂層鍵 `schema`，以 jsonschema 驗），含量測格定義規則、各比較對輸出欄、`material` 判準、每個決定點之決定規則、決定紀錄
schema（`decisions_schema`）；數值門檻只准 exact 集合比較／NaN 遮罩 exact／IC 正負號／float32 ulp（`threshold_kinds`），
不得有 atol／rtol 類鍵、不得有非整數數值；②判準檔於 git 恰一筆提交且工作樹位元組等於該提交之 blob；③每份
`handoffs/run_receipts/*-numview-*.json`（含估時與凍結收據——兩者亦依判準檔之格定義，且 Task 0.3 先於 0.4／0.5 執行）之
`criteria_sha256` 等於現檔 sha256，且其首次提交為判準檔提交之嚴格後代；④測試內依設計選擇⑥＋R2-D 實作之參考 `material`
判定對全 ties、全 NaN、有效對數 < 2 三案皆回 material（且對同序有限 IC 回非 material），判準檔 `material` 段登記同一
fail-closed 規則。
mutation（Task 0.3）：判準檔改一字 ⇒ ②③紅；收據改寫 `criteria_sha256` ⇒ ③紅；判定改為 `tau < 1`（NaN 視為未翻轉）⇒ ④紅。
邊界（Task 0.3）：05 判準須改 ⇒ 只准以新檔名 v2 取代並刪舊檔，且早於任何收據；06 收據產出後判準不得再有提交，缺陷記於
決定紀錄 `measurement_limitations`。

驗證（Task 0.4，名稱含 estimate）：①估時收據（`_estimate_gate.ESTIMATE_RECEIPT_GLOB`，恰一份）具 `reported_at`、格清單
（自 `kline_cache.h5` 獨立列舉比對，不缺格）、逐跑別格清單／單格秒數／外推總秒數、省時作法，跑別涵蓋 `estimate.RUN_KINDS`
（凍結跑別之 G1 四臂〔臂集＝契約 `post_ic_arm_values`〕／G2／G3，與 Phase 1 全部生成）；格 C 之 12h 基準可引
`handoffs/run_receipts/20261020-preprov-fullrun-size.md`，其餘 tf 各實測；②`_estimate_gate.require` 於收據缺、`reported_at`
缺、格不在清單三案各拋 `EstimateGateError`（另以清單內之格為正對照）；③AST：`scripts/numview_freeze_baseline.py` 與
`handoffs/run_receipts/numview_probes/` 下每個呼叫生成入口之腳本（SPEC Task 1.1–1.3 點名之三探針一律須呼叫；`estimate.py`
為估時器本身、`_estimate_gate.py` 為閘本身，豁免），於其 `main` 之頂層敘述呼叫 `require(<跑別>, …)`，且行序早於 `main`
內任何（直接或經本模組函式間接之）生成呼叫。
mutation（Task 0.4）：凍結腳本刪前置呼叫 ⇒ ③紅；`require` 改只 log ⇒ ②紅。
邊界（Task 0.4）：07 格 C 單格實測逾機器上限 ⇒ 該 tf 之格 C 全列 blocked-by 硬體、無逐格耗時；08 磁碟 < 30 GB ⇒
`estimate.main` rc=1、輸出列所需空間、未啟動任何生成、未寫收據。

驗證（Task 1.5）：①每個決定點恰一筆且合判準檔登記之 schema；②每筆之觸發判定由測試依判準檔規則自所引收據列機械重算
（不讀決定紀錄之結論欄）；③`changes_public_output=true` ⇒ `user_ruling`（日期＋原話）；④D-ICPAGE-ARM＝鎖臂、
`changes_public_output=true`、`user_ruling.date=2026-10-21` 且原話等於 SPEC §A 兩句（不論 G1 各臂份是否兩兩相等）；
⑤D-POSTIC 選 `polars_float64` 必具 `user_ruling`，否則只能 `retain`；⑥任一改特徵階段或公開輸出值之筆（含核心決定點之非
`retain` 選項）皆具 `user_ruling`。
mutation（Task 1.5）：觸發判定與收據不符 ⇒ ②紅；刪 `user_ruling` ⇒ ③紅；D-ICPAGE-ARM 標 `changes_public_output=false`
（含 G1 兩兩相等）或缺 2026-10-21 `user_ruling` ⇒ ④紅；D-POSTIC 選 `polars_float64` 而無 `user_ruling` ⇒ ⑤紅。
邊界（Task 1.5，流程邊界以 schema／一致性斷言編碼）：21 判準未預見之情況 ⇒ 記為量測限制、不事後加判準（判準檔於首份收據後
無提交，且決定紀錄 schema 具 `measurement_limitations`）；22 委員分歧 ⇒ 依碼證與收據（每筆 `evidence` 皆可解析至收據列），
不決者採較嚴版並具名殘留（`split_resolution=stricter_with_residual` ⇒ `residual_id` 合 `NUMVIEW-R<n>`）。

本檔定義之介面（判準檔、決定紀錄、估時收據之欄名；實作須依此產出）：
- 判準檔頂層：`schema`、`cell_rules{enumerate_from, output_bars, insufficient_history}`、
  `comparison_outputs{<比較對>: {reference, variant, columns[]}}`、`material{components[], tau_b{pairs, undefined_verdict,
  undefined_cases[]}, non_finite_statistic_verdict}`、`decision_rules{<決定鍵>: {label, trigger{kind, receipt, rows_key,
  where, field}, choices[], candidate_conditions{}}}`、`decisions_schema`、`threshold_kinds[]`。
- 決定紀錄（`numview_helpers.DECISIONS_PATH`）：`{criteria_sha256, decisions: {<決定點鍵>: record}, measurement_limitations:
  [{id, kind, description}]}`（全票統一形：物件鍵即決定點；record 可省 `key`，自帶時須等於物件鍵）；record 至少 `label、triggered、choice、changes_public_output、changes_feature_stage、evidence[{receipt,
  rows_key, row}]`，視情況 `user_ruling{date, quote[]}`、`report{}`、`committee_split`、`split_resolution`、`residual_id`。
- 估時收據：`criteria_sha256、reported_at、cells{A|B|C: [{id, kind, symbol, timeframes[]}]}（全票唯一格描述子；A／C 之 timeframes 恰一項，B 依週期長度升冪、首項＝主週期）、
  cell_c_baseline{<tf>: {seconds, peak_rss_bytes, source} | {blocked_by, reason}}、run_kinds{<跑別>: {cells[],
  single_cell_seconds{<格類>: 秒}, extrapolated_total_seconds, per_cell_seconds?{}, groups?{G1{cells, arms}, G2{cells},
  G3{cells}}}}、savings[{method, saved_seconds}]、blocked[{cell, blocked_by, reason}]`。
測試接縫：`_estimate_gate.require(run_kind, cells, *, receipts_dir=)` 依 `receipts_dir` 讀收據；`estimate.main` 經模組屬性
`disk_free_gb` 查磁碟（monkeypatch 可換）、磁碟不足時先於任何生成回 rc=1；腳本主入口名 `main`。
純 JSON／AST／git 級（秒級，不生成；`kline_cache.h5` 只讀鍵名）；實作前應為紅（判準檔、收據、決定紀錄未產出，閘與估時器為
NotImplementedError）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import h5py
import jsonschema
import numpy as np
import pytest

from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from tests.feature_engineering import numview_helpers as nh

REPO = nh.REPO
CRITERIA_V1: Path = nh.CRITERIA_PATH
CRITERIA_V2: Path = nh.GOLDEN_DIR / "preregistered_criteria_v2.json"
RECEIPT_GLOB = "*-numview-*.json"
PROBES_DIR: Path = REPO / "handoffs" / "run_receipts" / "numview_probes"
FREEZE_SCRIPT: Path = REPO / "scripts" / "numview_freeze_baseline.py"
FULLRUN_SIZE_RECEIPT = "handoffs/run_receipts/20261020-preprov-fullrun-size.md"
FULLRUN_SIZE_TF = "12h"   # SPEC Task 0.4：該收據為 BTCUSDT 12h 生產預設全特徵 run


def _load_probe(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"numview_probe_{name.strip('_')}", PROBES_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None, name
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_probe("_estimate_gate")
ESTIMATOR = _load_probe("estimate")
BRANCHDIFF = _load_probe("postic_branchdiff")

#: SPEC Task 1.5 之決定點（決定紀錄鍵 → SPEC 標籤）；核心六鍵＝`numview_helpers.CORE_DECISION_KEYS`
DECISION_POINTS: Dict[str, str] = {
    "d_icpage_arm": "D-ICPAGE-ARM", "d_postic": "D-POSTIC", "d_mtf": "D-MTF", "d_memmap": "D-MEMMAP",
    "d_winsor_dtype": "D-WINSOR-DTYPE", "d_codec": "D-CODEC", "d_l2": "D-L2", "d_research": "D-RESEARCH",
}
#: SPEC Task 3.1–3.3 ASSERT 行之 WHEN 值集
SPEC_CHOICES: Dict[str, Set[str]] = {
    "d_postic": {"polars_float64", "retain"}, "d_mtf": {"unify", "retain"}, "d_memmap": {"decouple", "retain"},
    "d_winsor_dtype": {"unify", "retain"}, "d_codec": {"provenance", "retain"}, "d_l2": {"unify", "retain"},
}
RETAIN = "retain"
POSTIC_CANDIDATE = "polars_float64"
ICPAGE_LOCK = "lock"   # 本檔定義之 D-ICPAGE-ARM 選項名（SPEC 只寫「鎖臂」）
ICPAGE_RULING_DATE = "2026-10-21"
ICPAGE_RULING_QUOTE: Tuple[str, str] = (
    "跑13-107小時這是什麼東西？這時間完全不能接受",
    "Ok, 你確保相關的文件和檔案有更新到最新的方向和結論",
)
#: SPEC Task 0.3 允許之數值門檻類別（exact 集合比較、NaN 遮罩 exact、IC 正負號、float32 ulp）
ALLOWED_THRESHOLD_KINDS = frozenset({"exact_set", "nan_mask_exact", "ic_sign", "float32_ulp"})
TRIGGER_KINDS = frozenset({"always", "any_true", "any_nonzero"})
CRITERIA_REQUIRED_KEYS = ("schema", "cell_rules", "comparison_outputs", "material", "decision_rules",
                          "decisions_schema", "threshold_kinds")
CELL_RULE_KEYS = ("enumerate_from", "output_bars", "insufficient_history")
#: 設計選擇⑥＋R2-D 之 material 規則登記
MATERIAL_COMPONENTS = frozenset({"nan_mask_diff", "ic_sign_flip", "survivor_set_change", "tau_b_below_1"})
MATERIAL_TAU_B = {"pairs": "both_finite", "undefined_verdict": "material",
                  "undefined_cases": ["all_ties", "all_nan", "fewer_than_2_pairs"]}
#: Task 1.1 輸出欄（`postic_branchdiff.cell_diff`／`ic_material` 之鍵）
TASK11_COLUMNS = frozenset({"max_abs", "p99_abs", "max_rel", "nan_mask_diff", "tau_b", "sign_flips", "material"})
_FORBIDDEN_KEY_RE = re.compile(r"(?i)(^|_)(atol|rtol|tol|tolerance)($|_)")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RESIDUAL_RE = re.compile(r"^NUMVIEW-R\d+$")
LIMITATION_KINDS = frozenset({"criteria_defect", "unforeseen_situation"})
SPLIT_RESOLUTIONS = frozenset({"evidence", "stricter_with_residual"})
CELL_CATEGORIES = ("A", "B", "C")
BLOCKED_BY_HARDWARE = "hardware"
#: 生成入口（AST 呼叫名）：FeatureFactory 生成、IC-first、IC 頁轉換、既有測試 helper 之生成
GENERATION_CALL_NAMES = frozenset({
    "generate_features", "_generate_features_impl", "run_ic_first", "generate_short_run", "_apply_transforms_sync",
    "run_stat", "ic_first_to_l65", "write_canonical_run",
})
_GENERATION_PREFIX_RE = re.compile(r"^generate_")
#: SPEC 點名須呼叫前置之重型跑腳本 → 跑別
MANDATED_GATED_SCRIPTS: Dict[Path, str] = {
    FREEZE_SCRIPT: "freeze_baseline",
    PROBES_DIR / "postic_branchdiff.py": "postic_branchdiff",
    PROBES_DIR / "precision_chain.py": "precision_chain",
    PROBES_DIR / "l2_arm_matrix.py": "l2_arm_matrix",
}
GATE_EXEMPT = frozenset({PROBES_DIR / "estimate.py", PROBES_DIR / "_estimate_gate.py"})


# ---------------------------------------------------------------------------------------------- 讀取接縫

def _rel(path: Path) -> str:
    return str(Path(path).resolve().relative_to(REPO))


def _strict_json(text: str) -> Any:
    def hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        keys = [k for k, _ in pairs]
        dup = sorted({k for k in keys if keys.count(k) > 1})
        assert not dup, f"JSON 重複鍵：{dup}"
        return dict(pairs)
    return json.loads(text, object_pairs_hook=hook)


def _criteria_path() -> Path:
    """現行判準檔名：v2 存在即 v2，否則 v1（邊界 05）。"""
    return CRITERIA_V2 if CRITERIA_V2.is_file() else CRITERIA_V1


def _read_criteria_bytes(path: Path) -> bytes:
    """判準檔位元組之唯一讀取入口（mutation 以 monkeypatch 換之）。"""
    assert path.is_file(), f"判準檔不存在：{_rel(path)}（Task 0.3 未產出）"
    return path.read_bytes()


def _load_criteria() -> Dict[str, Any]:
    return _strict_json(_read_criteria_bytes(_criteria_path()).decode("utf-8"))


def _criteria_sha256() -> str:
    return hashlib.sha256(_read_criteria_bytes(_criteria_path())).hexdigest()


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True)


def _git_commits(rel: str) -> List[str]:
    """觸及 `rel` 之提交（新到舊；含刪除提交）。mutation 以 monkeypatch 換之。"""
    out = _git("log", "--format=%H", "--", rel)
    assert out.returncode == 0, out.stderr.decode("utf-8", "replace")
    return out.stdout.decode().split()


def _blob_at(commit: str, rel: str) -> Optional[bytes]:
    out = _git("show", f"{commit}:{rel}")
    return out.stdout if out.returncode == 0 else None


def _strictly_before(earlier: str, later: str) -> bool:
    return earlier != later and _git("merge-base", "--is-ancestor", earlier, later).returncode == 0


def _receipt_paths() -> List[Path]:
    return sorted(p for p in nh.RECEIPTS_DIR.glob(RECEIPT_GLOB) if p.is_file())


def _load_receipt(path: Path) -> Dict[str, Any]:
    """收據讀取之唯一入口（mutation 以 monkeypatch 換之）。"""
    return _strict_json(Path(path).read_text(encoding="utf-8"))


def _load_decisions() -> Dict[str, Any]:
    """決定紀錄讀取之唯一入口（mutation 以 monkeypatch 換之）。"""
    path = nh.DECISIONS_PATH
    assert path.is_file(), f"決定紀錄不存在：{_rel(path)}（Task 1.5 未產出）"
    return _strict_json(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    """腳本原始碼讀取之唯一入口（Task 0.4 ③；mutation 以 monkeypatch 換之）。"""
    return Path(path).read_text(encoding="utf-8")


def _schema_errors(schema: Mapping[str, Any], instance: Any) -> List[str]:
    cls = jsonschema.validators.validator_for(schema)
    try:
        cls.check_schema(schema)
    except jsonschema.exceptions.SchemaError as exc:
        return [f"schema 本身不合法：{exc.message}"]
    return sorted(f"{list(e.absolute_path)}: {e.message}" for e in cls(schema).iter_errors(instance))


def _kline_index() -> Dict[str, List[str]]:
    """真實 `kline_cache.h5` 之 symbol → tf 清單（只讀鍵名；不寫死清單）。"""
    with h5py.File(nh.KLINE_PATH, "r") as f:
        return {str(s): sorted(str(tf) for tf in f[s].keys()) for s in sorted(f.keys())}


# ---------------------------------------------------------------------------------------------- Task 0.3 ① schema

def _walk(node: Any, where: str = "") -> Iterable[Tuple[str, Any, Any]]:
    if isinstance(node, Mapping):
        for k, v in node.items():
            yield where, k, v
            yield from _walk(v, f"{where}.{k}" if where else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{where}[{i}]")


def criteria_violations(criteria: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    missing = [k for k in CRITERIA_REQUIRED_KEYS if k not in criteria]
    if missing:
        return [f"判準檔缺頂層鍵：{missing}"]
    schema = criteria["schema"]
    if not isinstance(schema, Mapping):
        return ["內嵌 schema 非物件"]
    if not set(CRITERIA_REQUIRED_KEYS) <= set(schema.get("required") or []):
        out.append(f"內嵌 schema 之 required 未涵蓋 {CRITERIA_REQUIRED_KEYS}（空殼 schema 不得充數）")
    out += [f"內嵌 schema：{e}" for e in _schema_errors(schema, criteria)]
    rules = criteria["cell_rules"]
    if not isinstance(rules, Mapping) or any(k not in rules for k in CELL_RULE_KEYS):
        out.append(f"cell_rules 須含 {CELL_RULE_KEYS}")
    else:
        if not str(rules["enumerate_from"]).endswith("kline_cache.h5"):
            out.append("cell_rules.enumerate_from 須為 kline_cache.h5")
        if not (isinstance(rules["output_bars"], int) and not isinstance(rules["output_bars"], bool)
                and rules["output_bars"] > 0):
            out.append("cell_rules.output_bars 須為正整數")
    pairs = criteria["comparison_outputs"]
    columns: Set[str] = set()
    if not isinstance(pairs, Mapping) or not pairs:
        out.append("comparison_outputs 為空")
    else:
        for name, pair in pairs.items():
            if not (isinstance(pair, Mapping) and isinstance(pair.get("reference"), str)
                    and isinstance(pair.get("variant"), str) and pair.get("columns")):
                out.append(f"comparison_outputs.{name} 須含 reference、variant、非空 columns")
                continue
            columns |= set(pair["columns"])
        if not TASK11_COLUMNS <= columns:
            out.append(f"comparison_outputs 缺 Task 1.1 輸出欄 {sorted(TASK11_COLUMNS - columns)}")
    material = criteria["material"]
    if not isinstance(material, Mapping):
        out.append("material 非物件")
    else:
        if set(material.get("components") or []) != MATERIAL_COMPONENTS:
            out.append(f"material.components ≠ {sorted(MATERIAL_COMPONENTS)}")
        if material.get("tau_b") != MATERIAL_TAU_B:
            out.append(f"material.tau_b ≠ {MATERIAL_TAU_B}（R2-D fail-closed 未登記）")
        if material.get("non_finite_statistic_verdict") != "material":
            out.append("material.non_finite_statistic_verdict ≠ material")
    kinds = criteria["threshold_kinds"]
    if not isinstance(kinds, list) or not kinds or not set(kinds) <= ALLOWED_THRESHOLD_KINDS:
        out.append(f"threshold_kinds 須為 {sorted(ALLOWED_THRESHOLD_KINDS)} 之非空子集，實得 {kinds!r}")
    for where, key, value in _walk({k: v for k, v in criteria.items() if k not in ("schema", "decisions_schema")}):
        if _FORBIDDEN_KEY_RE.search(str(key)):
            out.append(f"{where}.{key}：自訂容差鍵（SPEC 不准 atol／rtol）")
        if key == "threshold_kind" and value not in (kinds if isinstance(kinds, list) else []):
            out.append(f"{where}.threshold_kind={value!r} 不屬 threshold_kinds")
        if isinstance(value, float) and not float(value).is_integer():
            out.append(f"{where}.{key}={value!r}：非整數數值（門檻只准 exact／ulp）")
    out += decision_rule_violations(criteria["decision_rules"])
    dschema = criteria["decisions_schema"]
    if not isinstance(dschema, Mapping):
        out.append("decisions_schema 非物件")
    else:
        out += [f"decisions_schema：{e}" for e in _schema_errors(dschema, {}) if e.startswith("schema 本身")]
        if not {"criteria_sha256", "decisions", "measurement_limitations"} <= set(dschema.get("required") or []):
            out.append("decisions_schema.required 須含 criteria_sha256、decisions、measurement_limitations")
    return out


def decision_rule_violations(rules: Any) -> List[str]:
    out: List[str] = []
    if not isinstance(rules, Mapping) or set(rules) != set(DECISION_POINTS):
        return [f"decision_rules 之鍵 ≠ {sorted(DECISION_POINTS)}"]
    for key, rule in rules.items():
        if rule.get("label") != DECISION_POINTS[key]:
            out.append(f"decision_rules.{key}.label ≠ {DECISION_POINTS[key]}")
        trigger = rule.get("trigger") or {}
        if trigger.get("kind") not in TRIGGER_KINDS:
            out.append(f"decision_rules.{key}.trigger.kind 不屬 {sorted(TRIGGER_KINDS)}")
        elif trigger["kind"] != "always":
            for fld, typ in (("receipt", str), ("rows_key", str), ("field", str), ("where", Mapping)):
                if not isinstance(trigger.get(fld), typ):
                    out.append(f"decision_rules.{key}.trigger.{fld} 缺或型別錯")
        choices = rule.get("choices")
        if not isinstance(choices, list) or not choices or len(set(choices)) != len(choices):
            out.append(f"decision_rules.{key}.choices 須為非空且不重複")
            continue
        if key in SPEC_CHOICES and set(choices) != SPEC_CHOICES[key]:
            out.append(f"decision_rules.{key}.choices ≠ SPEC ASSERT 值集 {sorted(SPEC_CHOICES[key])}")
        if key == "d_icpage_arm" and (choices != [ICPAGE_LOCK] or trigger.get("kind") != "always"):
            out.append("decision_rules.d_icpage_arm 須為 choices=[lock]、trigger.kind=always（已定案）")
        conditions = rule.get("candidate_conditions")
        if not isinstance(conditions, Mapping) or not set(conditions) <= set(choices):
            out.append(f"decision_rules.{key}.candidate_conditions 須為以 choices 為鍵之物件")
    return out


# ---------------------------------------------------------------------------------------------- Task 0.3 ②③

def frozen_violations() -> List[str]:
    """②：現行判準檔恰一筆提交，且工作樹位元組＝該提交之 blob。"""
    path = _criteria_path()
    rel = _rel(path)
    commits = _git_commits(rel)
    if len(commits) != 1:
        return [f"{rel} 之提交數 {len(commits)} ≠ 1（判準凍結後不得修改）"]
    if _blob_at(commits[0], rel) != _read_criteria_bytes(path):
        return [f"{rel} 工作樹內容 ≠ 其唯一提交之內容（未提交之改動）"]
    return []


def receipt_violations() -> List[str]:
    """③：每份 numview 收據之 `criteria_sha256`＝現檔 sha256，且其首次提交為判準檔提交之嚴格後代；無收據亦違規。"""
    receipts = _receipt_paths()
    if not receipts:
        return ["無任何 *-numview-*.json 收據（③無對象）"]
    rel = _rel(_criteria_path())
    commits = _git_commits(rel)
    if not commits:
        return [f"{rel} 未提交"]
    criteria_commit = commits[-1]
    current = _criteria_sha256()
    out: List[str] = []
    for path in receipts:
        receipt = _load_receipt(path)
        if receipt.get("criteria_sha256") != current:
            out.append(f"{path.name}：criteria_sha256 ≠ 現行判準檔")
        receipt_commits = _git_commits(_rel(path))
        if not receipt_commits:
            out.append(f"{path.name}：未提交")
        elif not _strictly_before(criteria_commit, receipt_commits[-1]):
            out.append(f"{path.name}：首次提交未晚於判準檔提交")
    return out


def _first_receipt_commits() -> List[str]:
    commits = [_git_commits(_rel(p)) for p in _receipt_paths()]
    return [c[-1] for c in commits if c]


def criteria_after_receipt_violations() -> List[str]:
    """收據產出後判準檔（v1、v2 兩檔名）不得再有提交：每筆觸及判準檔之提交皆為每份收據首次提交之嚴格祖先。"""
    firsts = _first_receipt_commits()
    if not firsts or len(firsts) != len(_receipt_paths()):
        return ["無收據或有收據未提交（無從判定先後）"]
    out: List[str] = []
    for path in (CRITERIA_V1, CRITERIA_V2):
        for commit in _git_commits(_rel(path)):
            late = [f for f in firsts if not _strictly_before(commit, f)]
            if late:
                out.append(f"{path.name} 之提交 {commit[:10]} 不早於收據提交 {late[0][:10]}")
    return out


# ---------------------------------------------------------------------------------------------- Task 0.3 ④ 參考 material 判定

def _kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    """Kendall τ-b（測試端獨立實作）；n < 2 或任一邊全 ties（分母 0）⇒ NaN。"""
    n = len(x)
    if n < 2:
        return float("nan")
    concordant = discordant = ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = np.sign(x[i] - x[j])
            dy = np.sign(y[i] - y[j])
            if dx == 0:
                ties_x += 1
            if dy == 0:
                ties_y += 1
            if dx != 0 and dy != 0:
                if dx == dy:
                    concordant += 1
                else:
                    discordant += 1
    n0 = n * (n - 1) / 2
    denom = math.sqrt((n0 - ties_x) * (n0 - ties_y))
    return float("nan") if denom == 0 else (concordant - discordant) / denom


def _tau_b_material(tau: float) -> bool:
    """R2-D：τ-b 非有限 ⇒ material（fail-closed）；否則 τ-b < 1 ⇒ material。"""
    return (not math.isfinite(tau)) or tau < 1.0


def reference_material(ic_reference: Sequence[float], ic_variant: Sequence[float]) -> bool:
    """設計選擇⑥＋R2-D：NaN 遮罩差、IC 正負號翻轉、或 τ-b（只對兩者皆有限之欄對）< 1 或未定義 ⇒ material。"""
    a = np.asarray(ic_reference, dtype=np.float64)
    b = np.asarray(ic_variant, dtype=np.float64)
    if bool(np.any(np.isfinite(a) != np.isfinite(b))):
        return True
    both = np.isfinite(a) & np.isfinite(b)
    if bool(np.any(np.sign(a[both]) != np.sign(b[both]))):
        return True
    return _tau_b_material(_kendall_tau_b(a[both], b[both]))


#: ④之三個未定義案（皆應 material）與一個正對照（同序有限 IC ⇒ 非 material）
MATERIAL_CASES: Tuple[Tuple[str, List[float], List[float], bool], ...] = (
    ("all_ties", [0.1, 0.1, 0.1], [0.2, 0.2, 0.2], True),
    ("all_nan", [float("nan")] * 3, [float("nan")] * 3, True),
    ("fewer_than_2_pairs", [0.1, float("nan")], [0.2, float("nan")], True),
    ("identical_order_control", [0.1, 0.2, 0.3], [0.1, 0.2, 0.3], False),
)


def material_judge_violations() -> List[str]:
    return [f"{name}：判定 {reference_material(a, b)} ≠ 期望 {want}" for name, a, b, want in MATERIAL_CASES
            if reference_material(a, b) != want]


# ---------------------------------------------------------------------------------------------- Task 1.5

def _records(decisions: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    """決定紀錄之 `decisions`＝{決定點鍵: 紀錄}（全票統一形；鍵即決定點，JSON 物件鍵不重複 ⇒ 每點至多一筆）。
    回傳每筆之檢視複本並注入 `key`＝其物件鍵；紀錄內若自帶 `key` 而與物件鍵不同 ⇒ 注入 `key_mismatch` 供 ① 判違規。
    非物件形（如清單）⇒ 空清單（① 之逐點計數因而全紅，fail-closed）。"""
    records = decisions.get("decisions")
    if not isinstance(records, Mapping):
        return []
    out: List[Mapping[str, Any]] = []
    for key, record in records.items():
        if not isinstance(record, Mapping):
            continue
        view = dict(record)
        if "key" in record and record["key"] != key:
            view["key_mismatch"] = record["key"]
        view["key"] = key
        out.append(view)
    return out


def _record(decisions: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    found = [r for r in _records(decisions) if r.get("key") == key]
    assert len(found) == 1, f"決定點 {key} 之紀錄數 {len(found)} ≠ 1"
    return found[0]


def _ruling_ok(record: Mapping[str, Any]) -> bool:
    ruling = record.get("user_ruling")
    if not isinstance(ruling, Mapping) or not _DATE_RE.match(str(ruling.get("date", ""))):
        return False
    quote = ruling.get("quote")
    return isinstance(quote, list) and bool(quote) and all(isinstance(q, str) and q.strip() for q in quote)


def decision_schema_violations(decisions: Mapping[str, Any], criteria: Mapping[str, Any]) -> List[str]:
    """①：合判準檔 `decisions_schema`；每個決定點恰一筆、無未知鍵；選項屬判準檔該點 choices；`criteria_sha256` 相符。"""
    out = [f"decisions_schema：{e}" for e in _schema_errors(criteria["decisions_schema"], decisions)]
    if decisions.get("criteria_sha256") != _criteria_sha256():
        out.append("決定紀錄 criteria_sha256 ≠ 現行判準檔")
    records = _records(decisions)
    keys = [r.get("key") for r in records]
    for key in DECISION_POINTS:
        if keys.count(key) != 1:
            out.append(f"{key}：紀錄數 {keys.count(key)} ≠ 1")
    out += [f"未知決定點：{k!r}" for k in keys if k not in DECISION_POINTS]
    if not isinstance(decisions.get("decisions"), Mapping):
        out.append("decisions 須為 {決定點鍵: 紀錄} 物件")
    for r in records:
        key = r.get("key")
        if "key_mismatch" in r:
            out.append(f"{key}：紀錄內 key={r['key_mismatch']!r} 與物件鍵不同")
        if key not in DECISION_POINTS:
            continue
        if r.get("label") != DECISION_POINTS[key]:
            out.append(f"{key}：label ≠ {DECISION_POINTS[key]}")
        for flag in ("triggered", "changes_public_output", "changes_feature_stage"):
            if not isinstance(r.get(flag), bool):
                out.append(f"{key}：{flag} 須為 bool")
        if r.get("choice") not in criteria["decision_rules"][key]["choices"]:
            out.append(f"{key}：choice {r.get('choice')!r} 不屬判準檔 choices")
    return out


def _is_finite_zero(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            and value == 0)


def recompute_trigger(rule: Mapping[str, Any]) -> Tuple[Optional[bool], str]:
    """依判準檔規則自收據列重算觸發（fail-closed：欄缺、非 bool、非有限 ⇒ 觸發）；不可重算 ⇒ (None, 原因)。"""
    trigger = rule["trigger"]
    kind = trigger.get("kind")
    if kind == "always":
        return True, ""
    if kind not in TRIGGER_KINDS:
        return None, f"未知觸發類別 {kind!r}"
    slug = str(trigger["receipt"]).replace("_", "-")
    paths = sorted(nh.RECEIPTS_DIR.glob(f"*-numview-{slug}.json"))
    if len(paths) != 1:
        return None, f"收據 *-numview-{slug}.json 數 {len(paths)} ≠ 1"
    rows = _load_receipt(paths[0]).get(trigger["rows_key"])
    if not isinstance(rows, list):
        return None, f"{paths[0].name} 無列表 {trigger['rows_key']!r}"
    where = trigger["where"]
    selected = [r for r in rows if isinstance(r, Mapping) and all(r.get(k) == v for k, v in where.items())]
    if not selected:
        return None, f"{paths[0].name} 依 where={dict(where)} 選無列"
    field = trigger["field"]
    if kind == "any_true":
        return any(r.get(field) is not False for r in selected), ""
    return any(not _is_finite_zero(r.get(field)) for r in selected), ""


def trigger_violations(decisions: Mapping[str, Any], criteria: Mapping[str, Any]) -> List[str]:
    """②：每筆 `triggered`＝測試依判準檔規則自收據列重算之值。"""
    out: List[str] = []
    for r in _records(decisions):
        key = r.get("key")
        if key not in DECISION_POINTS:
            continue
        expected, why = recompute_trigger(criteria["decision_rules"][key])
        if expected is None:
            out.append(f"{key}：觸發不可重算（{why}）")
        elif r.get("triggered") is not expected:
            out.append(f"{key}：triggered={r.get('triggered')!r} ≠ 收據重算 {expected}")
    return out


def ruling_violations(decisions: Mapping[str, Any]) -> List[str]:
    """③：`changes_public_output=true` 之筆具 `user_ruling`（日期＋原話）。"""
    return [f"{r.get('key')}：changes_public_output=true 而缺 user_ruling（日期＋原話）"
            for r in _records(decisions) if r.get("changes_public_output") is True and not _ruling_ok(r)]


def icpage_violations(decisions: Mapping[str, Any]) -> List[str]:
    """④：D-ICPAGE-ARM＝鎖臂、改公開輸出、2026-10-21 原話兩句；不參考 `report` 之任何欄（G1 兩兩相等與否不改此判）。"""
    r = _record(decisions, "d_icpage_arm")
    out: List[str] = []
    if r.get("choice") != ICPAGE_LOCK:
        out.append(f"d_icpage_arm：choice {r.get('choice')!r} ≠ {ICPAGE_LOCK}")
    if r.get("changes_public_output") is not True:
        out.append("d_icpage_arm：changes_public_output 須為 true")
    ruling = r.get("user_ruling")
    if not isinstance(ruling, Mapping) or ruling.get("date") != ICPAGE_RULING_DATE:
        out.append(f"d_icpage_arm：缺 {ICPAGE_RULING_DATE} user_ruling")
    elif ruling.get("quote") != list(ICPAGE_RULING_QUOTE):
        out.append("d_icpage_arm：user_ruling.quote ≠ SPEC §A 所引兩句")
    return out


def postic_violations(decisions: Mapping[str, Any]) -> List[str]:
    """⑤：D-POSTIC 選 `polars_float64` ⇒ 具 `user_ruling` 且 `changes_public_output=true`；否則只能 `retain`。"""
    r = _record(decisions, "d_postic")
    choice = r.get("choice")
    if choice == POSTIC_CANDIDATE:
        out = [] if _ruling_ok(r) else ["d_postic：選 polars_float64 而缺 user_ruling"]
        if r.get("changes_public_output") is not True:
            out.append("d_postic：選 polars_float64 而 changes_public_output 非 true")
        return out
    return [] if choice == RETAIN else [f"d_postic：無 user_ruling 時只能 retain，實得 {choice!r}"]


def change_ruling_violations(decisions: Mapping[str, Any]) -> List[str]:
    """⑥：改特徵階段或公開輸出值之筆（`changes_*` 為 true，或核心決定點選非 `retain`）皆具 `user_ruling`。"""
    out: List[str] = []
    for r in _records(decisions):
        key = r.get("key")
        changes = (r.get("changes_public_output") is True or r.get("changes_feature_stage") is True
                   or (key in SPEC_CHOICES and r.get("choice") != RETAIN))
        if changes and not _ruling_ok(r):
            out.append(f"{key}：改案而缺 user_ruling（量測觸發不得自動標改案）")
    return out


def evidence_violations(decisions: Mapping[str, Any]) -> List[str]:
    """邊界 22：每筆 `evidence` 非空且每個引用可解析至收據列；`split_resolution=stricter_with_residual` ⇒ 具名殘留。"""
    out: List[str] = []
    for r in _records(decisions):
        key = r.get("key")
        refs = r.get("evidence")
        if not isinstance(refs, list) or not refs:
            out.append(f"{key}：evidence 為空（不得在無收據列支持下選定處置）")
            refs = []
        for ref in refs:
            if not isinstance(ref, Mapping):
                out.append(f"{key}：evidence 引用非物件：{ref!r}")
                continue
            path = REPO / str(ref.get("receipt", ""))
            if not (path.is_file() and path.parent == nh.RECEIPTS_DIR and path.match(RECEIPT_GLOB)):
                out.append(f"{key}：evidence 收據不存在或非 numview 收據：{ref!r}")
                continue
            rows = _load_receipt(path).get(ref.get("rows_key"))
            row = ref.get("row")
            if not (isinstance(rows, list) and isinstance(row, int) and not isinstance(row, bool)
                    and 0 <= row < len(rows)):
                out.append(f"{key}：evidence 列不可解析：{ref!r}")
        if r.get("committee_split") is True:
            resolution = r.get("split_resolution")
            if resolution not in SPLIT_RESOLUTIONS:
                out.append(f"{key}：committee_split 而 split_resolution {resolution!r} 不屬 {sorted(SPLIT_RESOLUTIONS)}")
            elif resolution == "stricter_with_residual" and not _RESIDUAL_RE.match(str(r.get("residual_id", ""))):
                out.append(f"{key}：不決採較嚴版而缺具名殘留 residual_id")
    return out


def limitation_violations(decisions: Mapping[str, Any]) -> List[str]:
    """邊界 06／21：`measurement_limitations` 為清單，每項具唯一 `id`、`kind`（criteria_defect／unforeseen_situation）、
    非空 `description`。"""
    items = decisions.get("measurement_limitations")
    if not isinstance(items, list):
        return ["決定紀錄缺 measurement_limitations 清單"]
    out: List[str] = []
    ids = [i.get("id") if isinstance(i, Mapping) else None for i in items]
    for item, ident in zip(items, ids):
        if not (isinstance(ident, str) and ident.strip()) or ids.count(ident) != 1:
            out.append(f"measurement_limitations：id {ident!r} 缺或重複")
        if not isinstance(item, Mapping) or item.get("kind") not in LIMITATION_KINDS:
            out.append(f"measurement_limitations.{ident}：kind 不屬 {sorted(LIMITATION_KINDS)}")
        elif not str(item.get("description", "")).strip():
            out.append(f"measurement_limitations.{ident}：description 為空")
    return out


# ---------------------------------------------------------------------------------------------- Task 0.4

def _estimate_receipt_path() -> Path:
    paths = sorted(p for p in nh.RECEIPTS_DIR.glob(GATE.ESTIMATE_RECEIPT_GLOB) if p.is_file())
    assert len(paths) == 1, f"估時收據數 {len(paths)} ≠ 1（{GATE.ESTIMATE_RECEIPT_GLOB}）"
    return paths[0]


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _single_tf(cell: Mapping[str, Any]) -> Optional[str]:
    """單週期格（A／C）描述子之唯一週期：`timeframes` 恰一項 ⇒ 該項；否則 None（比對因而不等 ⇒ 紅）。"""
    tfs = cell.get("timeframes")
    return str(tfs[0]) if isinstance(tfs, list) and len(tfs) == 1 else None


def _cell_index(receipt: Mapping[str, Any]) -> Dict[str, Tuple[str, Mapping[str, Any]]]:
    """格 id → （格類, 格物件）。"""
    out: Dict[str, Tuple[str, Mapping[str, Any]]] = {}
    for category in CELL_CATEGORIES:
        for cell in (receipt.get("cells") or {}).get(category) or []:
            if isinstance(cell, Mapping) and isinstance(cell.get("id"), str):
                out[cell["id"]] = (category, cell)
    return out


def estimate_receipt_violations(receipt: Mapping[str, Any], kline: Mapping[str, List[str]]) -> List[str]:
    out: List[str] = []
    try:
        dt.datetime.fromisoformat(str(receipt.get("reported_at")))
    except ValueError:
        out.append("reported_at 缺或非 ISO-8601（主委白話報告後寫入）")
    cells = receipt.get("cells")
    if not isinstance(cells, Mapping) or set(cells) != set(CELL_CATEGORIES):
        return out + [f"cells 須恰含格類 {CELL_CATEGORIES}"]
    index = _cell_index(receipt)
    if len(index) != sum(len(cells[c] or []) for c in CELL_CATEGORIES):
        out.append("cells 之 id 缺或重複")
    pairs = {(s, tf) for s, tfs in kline.items() for tf in tfs}
    a_pairs = {(c.get("symbol"), _single_tf(c)) for c in cells["A"] if isinstance(c, Mapping)}
    c_pairs = {(c.get("symbol"), _single_tf(c)) for c in cells["C"] if isinstance(c, Mapping)}
    if a_pairs != pairs:
        out.append(f"格 A ≠ kline 之 symbol×tf：缺 {sorted(pairs - a_pairs)[:3]}、多 {sorted(a_pairs - pairs)[:3]}")
    if c_pairs != pairs:
        out.append(f"格 C ≠ kline 之 symbol×tf：缺 {sorted(pairs - c_pairs)[:3]}、多 {sorted(c_pairs - pairs)[:3]}")
    b_map = {c.get("symbol"): sorted(c.get("timeframes") or []) for c in cells["B"] if isinstance(c, Mapping)}
    if b_map != {s: sorted(tfs) for s, tfs in kline.items()} or len(cells["B"]) != len(kline):
        out.append("格 B ≠ 每個 symbol 一格且含其全部週期")
    ids = {c: {i for i, (cat, _) in index.items() if cat == c} for c in CELL_CATEGORIES}
    run_kinds = receipt.get("run_kinds")
    if not isinstance(run_kinds, Mapping):
        return out + ["run_kinds 缺"]
    required_cover = {
        "freeze_baseline": ids["A"] | ids["B"], "postic_branchdiff": ids["A"] | ids["B"],
        "precision_chain": ids["A"] | ids["B"] | ids["C"], "l2_arm_matrix": ids["A"] | ids["B"],
    }
    for kind in ESTIMATOR.RUN_KINDS:
        node = run_kinds.get(kind)
        if not isinstance(node, Mapping):
            out.append(f"run_kinds 缺跑別 {kind}")
            continue
        listed = set(node.get("cells") or [])
        if not listed or not listed <= set(index):
            out.append(f"{kind}：cells 為空或含未列舉之格")
        missing = required_cover.get(kind, set()) - listed
        if missing:
            out.append(f"{kind}：未涵蓋 {len(missing)} 格（不得以縮減格降低總估時）")
        categories = {index[i][0] for i in listed if i in index}
        per_cat = node.get("single_cell_seconds") or {}
        for cat in categories:
            if not _positive_number(per_cat.get(cat)):
                out.append(f"{kind}：缺格類 {cat} 之單格實測秒數")
        if not _positive_number(node.get("extrapolated_total_seconds")):
            out.append(f"{kind}：缺外推總秒數")
    groups = (run_kinds.get("freeze_baseline") or {}).get("groups") or {}
    arms = set(nv.load_contract()["post_ic_arm_values"]["values"])
    if not arms:
        out.append("契約 post_ic_arm_values 為空（G1 臂集無從比對）")
    g1 = groups.get("G1") or {}
    if set(g1.get("cells") or []) != ids["A"] or set(g1.get("arms") or []) != arms:
        out.append("freeze_baseline.groups.G1 須涵蓋全部格 A 且臂集＝契約 post_ic_arm_values")
    if set((groups.get("G2") or {}).get("cells") or []) != ids["A"]:
        out.append("freeze_baseline.groups.G2 須涵蓋全部格 A")
    if set((groups.get("G3") or {}).get("cells") or []) != ids["B"]:
        out.append("freeze_baseline.groups.G3 須涵蓋全部格 B")
    savings = receipt.get("savings")
    if not isinstance(savings, list) or not savings or not all(
            isinstance(s, Mapping) and str(s.get("method", "")).strip()
            and isinstance(s.get("saved_seconds"), (int, float)) and not isinstance(s.get("saved_seconds"), bool)
            and s["saved_seconds"] >= 0 for s in savings):
        out.append("savings 須為非空之 {method, saved_seconds≥0} 清單")
    baseline = receipt.get("cell_c_baseline")
    all_tfs = sorted({tf for tfs in kline.values() for tf in tfs})
    if not isinstance(baseline, Mapping) or set(baseline) != set(all_tfs):
        out.append(f"cell_c_baseline 須逐 tf 一項：{all_tfs}")
    else:
        for tf, node in baseline.items():
            if not isinstance(node, Mapping):
                out.append(f"cell_c_baseline.{tf}：非物件")
                continue
            if node.get("blocked_by") == BLOCKED_BY_HARDWARE:
                continue
            ok_source = node.get("source") == "measured" or (
                tf == FULLRUN_SIZE_TF and node.get("source") == FULLRUN_SIZE_RECEIPT and (REPO / FULLRUN_SIZE_RECEIPT).is_file())
            if not (isinstance(node, Mapping) and ok_source and _positive_number(node.get("seconds"))
                    and _positive_number(node.get("peak_rss_bytes"))):
                out.append(f"cell_c_baseline.{tf}：須實測（12h 可引 {FULLRUN_SIZE_RECEIPT}）或標 blocked_by=hardware")
    return out


def cell_c_blocked_violations(receipt: Mapping[str, Any]) -> List[str]:
    """邊界 07：某 tf 之格 C 單格實測逾機器上限（`cell_c_baseline[tf].blocked_by=hardware`）⇒ 該 tf 全部格 C 列於
    `blocked`（`blocked_by=hardware`、具 reason），且任何跑別之 `per_cell_seconds` 皆無其逐格耗時；反之未阻擋之 tf 不得
    部分阻擋（不逐格試）。"""
    out: List[str] = []
    index = _cell_index(receipt)
    baseline = receipt.get("cell_c_baseline") or {}
    blocked = {b.get("cell"): b for b in receipt.get("blocked") or [] if isinstance(b, Mapping)}
    timed: Set[str] = set()
    for node in (receipt.get("run_kinds") or {}).values():
        if isinstance(node, Mapping):
            timed |= set((node.get("per_cell_seconds") or {}).keys())
    c_by_tf: Dict[str, Set[str]] = {}
    for ident, (cat, cell) in index.items():
        if cat == "C":
            c_by_tf.setdefault(str(_single_tf(cell)), set()).add(ident)
    for tf, members in sorted(c_by_tf.items()):
        is_blocked = isinstance(baseline.get(tf), Mapping) and baseline[tf].get("blocked_by") == BLOCKED_BY_HARDWARE
        listed = {i for i in members if i in blocked}
        if is_blocked:
            for ident in sorted(members):
                entry = blocked.get(ident)
                if not (isinstance(entry, Mapping) and entry.get("blocked_by") == BLOCKED_BY_HARDWARE
                        and str(entry.get("reason", "")).strip()):
                    out.append(f"{tf}：格 C {ident} 未列 blocked-by 硬體")
                if ident in timed:
                    out.append(f"{tf}：已阻擋之格 C {ident} 仍有逐格耗時（不得逐格試）")
        elif listed:
            out.append(f"{tf}：未判阻擋而部分格 C 列 blocked（{sorted(listed)[:3]}）")
    return out


def gate_require_violations(gate: ModuleType, tmp_path: Path) -> List[str]:
    """②：收據缺／`reported_at` 缺／格不在清單 ⇒ 各拋 `EstimateGateError`；清單內之格 ⇒ 不拋（正對照）。"""
    in_list, not_in_list, kind = "numview_cell_listed", "numview_cell_unlisted", "freeze_baseline"
    name = "20261021-numview-estimate.json"
    base = {"reported_at": "2026-10-21T00:00:00+08:00", "run_kinds": {kind: {"cells": [in_list]}}}
    cases: List[Tuple[str, Optional[Dict[str, Any]], str]] = [
        ("收據不存在", None, in_list),
        ("reported_at 缺", {k: v for k, v in base.items() if k != "reported_at"}, in_list),
        ("格不在清單", base, not_in_list),
    ]
    out: List[str] = []
    for i, (label, receipt, cell) in enumerate(cases):
        rdir = tmp_path / f"case{i}"
        rdir.mkdir(parents=True)
        if receipt is not None:
            (rdir / name).write_text(json.dumps(receipt), encoding="utf-8")
        try:
            gate.require(kind, [cell], receipts_dir=rdir)
        except gate.EstimateGateError:
            continue
        except Exception as exc:  # noqa: BLE001 — 錯誤型別不符亦屬違規
            out.append(f"{label}：拋 {type(exc).__name__} 而非 EstimateGateError")
            continue
        out.append(f"{label}：未拋錯（前置閘失效）")
    ok_dir = tmp_path / "positive"
    ok_dir.mkdir(parents=True)
    (ok_dir / name).write_text(json.dumps(base), encoding="utf-8")
    try:
        result = gate.require(kind, [in_list], receipts_dir=ok_dir)
    except Exception as exc:  # noqa: BLE001
        out.append(f"正對照（格在清單）：拋 {type(exc).__name__}")
    else:
        if result is not None:
            out.append(f"正對照：回傳 {result!r}（應為 None）")
    return out


def _call_name(call: ast.Call) -> str:
    func = call.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


def _is_generation_call(call: ast.Call) -> bool:
    name = _call_name(call)
    if name in GENERATION_CALL_NAMES or _GENERATION_PREFIX_RE.match(name):
        return True
    func = call.func
    if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "subprocess"
            and name in ("run", "Popen", "call", "check_call", "check_output")):
        for node in ast.walk(call):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                    node.value.endswith(".py") or "pytest" in node.value or "run_api" in node.value):
                return True
    return False


def _is_require_call(call: ast.Call) -> bool:
    return _call_name(call) == "require"


def gate_call_violations_for(path: Path, expected_kind: Optional[str], mandated: bool) -> List[str]:
    """③：單一腳本之前置呼叫檢查（行序判定；間接生成經本模組頂層函式之遞移閉包）。"""
    rel = _rel(path)
    tree = ast.parse(_read_text(path), filename=rel)
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    generating = {name for name, fn in funcs.items()
                  if any(isinstance(c, ast.Call) and _is_generation_call(c) for c in ast.walk(fn))}
    changed = True
    while changed:
        changed = False
        for name, fn in funcs.items():
            if name in generating:
                continue
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in generating
                   for c in ast.walk(fn)):
                generating.add(name)
                changed = True
    module_generates = any(isinstance(c, ast.Call) and _is_generation_call(c) for c in ast.walk(tree))
    if not module_generates and not mandated:
        return []
    main = funcs.get("main")
    if main is None:
        return [f"{rel}：無主入口 main"]
    gen_lines = sorted(c.lineno for c in ast.walk(main) if isinstance(c, ast.Call) and (
        _is_generation_call(c) or (isinstance(c.func, ast.Name) and c.func.id in generating)))
    if mandated and not gen_lines:
        return [f"{rel}：SPEC 點名之重型跑腳本，其 main 未見任何生成呼叫（未實作或生成入口未被辨識）"]
    top_level_requires: List[ast.Call] = []
    for stmt in main.body:
        if isinstance(stmt, (ast.Expr, ast.Assign, ast.AnnAssign)) and isinstance(stmt.value, ast.Call) \
                and _is_require_call(stmt.value):
            top_level_requires.append(stmt.value)
    if not top_level_requires:
        return [f"{rel}：main 頂層未呼叫 _estimate_gate.require"]
    first = top_level_requires[0]
    out: List[str] = []
    kind_arg = first.args[0].value if first.args and isinstance(first.args[0], ast.Constant) else None
    allowed = {expected_kind} if expected_kind else set(ESTIMATOR.RUN_KINDS)
    if kind_arg not in allowed:
        out.append(f"{rel}：require 之跑別 {kind_arg!r} 不屬 {sorted(allowed)}")
    if gen_lines and gen_lines[0] <= first.lineno:
        out.append(f"{rel}：生成呼叫（第 {gen_lines[0]} 行）早於 require（第 {first.lineno} 行）")
    return out


def gate_call_violations() -> List[str]:
    out: List[str] = []
    for path, kind in MANDATED_GATED_SCRIPTS.items():
        if kind not in ESTIMATOR.RUN_KINDS:
            out.append(f"{kind} 不屬 estimate.RUN_KINDS")
        out += gate_call_violations_for(path, kind, mandated=True)
    for path in sorted(PROBES_DIR.glob("*.py")):
        if path in MANDATED_GATED_SCRIPTS or path in GATE_EXEMPT:
            continue
        out += gate_call_violations_for(path, None, mandated=False)
    return out


class _DropRequire(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        node.body = [s for s in node.body if not (
            isinstance(s, (ast.Expr, ast.Assign, ast.AnnAssign)) and isinstance(s.value, ast.Call)
            and _is_require_call(s.value))] or [ast.Pass()]
        return node


# ---------------------------------------------------------------------------------------------- 驗證（Task 0.3）

def test_criteria_file_matches_embedded_schema() -> None:
    """Task 0.3 ①：判準檔合其內嵌 schema，且含格定義、比較對輸出欄、material、決定規則、決定紀錄 schema、門檻類別。"""
    assert criteria_violations(_load_criteria()) == []


def test_criteria_file_committed_once_and_unchanged() -> None:
    """Task 0.3 ②：現行判準檔於 git 恰一筆提交（凍結後未改），工作樹＝該提交內容。"""
    assert frozen_violations() == []


def test_receipts_record_current_criteria_sha_after_criteria_commit() -> None:
    """Task 0.3 ③：每份 numview 收據之 `criteria_sha256`＝現檔 sha256，且其提交晚於判準檔提交。"""
    assert receipt_violations() == []


def test_material_judge_fail_closed_on_undefined_tau_b() -> None:
    """Task 0.3 ④：參考 material 判定對全 ties、全 NaN、有效對數 < 2 皆回 material（正對照：同序有限 IC 非 material）；
    判準檔 `material` 段登記同一 fail-closed 規則（τ-b 只對兩者皆有限之欄對、未定義 ⇒ material、非有限統計量 ⇒ material）。"""
    assert material_judge_violations() == []
    material = _load_criteria()["material"]
    assert material.get("tau_b") == MATERIAL_TAU_B
    assert material.get("non_finite_statistic_verdict") == "material"
    assert set(material.get("components") or []) == MATERIAL_COMPONENTS


def test_material_judge_agrees_with_task11_probe_judge() -> None:
    """Task 0.3 ④（交叉）：Task 1.1 探針之 `ic_material` 對四案之 `material` 與參考判定一致（探針候選臂名＝SPEC 之
    `polars_float64`）。"""
    assert BRANCHDIFF.CANDIDATE_ARM == POSTIC_CANDIDATE
    for name, a, b, want in MATERIAL_CASES:
        assert bool(BRANCHDIFF.ic_material(a, b)["material"]) is want, name


# ---------------------------------------------------------------------------------------------- 驗證（Task 1.5）

def test_decision_records_one_per_point_and_match_schema() -> None:
    """Task 1.5 ①：每個決定點恰一筆且合判準檔登記之 schema（含選項屬判準檔 choices、criteria_sha256 相符）。"""
    assert decision_schema_violations(_load_decisions(), _load_criteria()) == []


def test_decision_triggers_recomputed_from_receipt_rows() -> None:
    """Task 1.5 ②：每筆觸發判定由所引收據列依判準檔規則機械重算（不讀結論欄）。"""
    assert trigger_violations(_load_decisions(), _load_criteria()) == []


def test_public_output_change_has_user_ruling() -> None:
    """Task 1.5 ③：`changes_public_output=true` 之筆具 `user_ruling`（日期＋原話）。"""
    assert ruling_violations(_load_decisions()) == []


def test_icpage_arm_decision_locked_with_spec_ruling() -> None:
    """Task 1.5 ④：D-ICPAGE-ARM＝鎖臂、`changes_public_output=true`、2026-10-21 原話＝SPEC §A 兩句（原話逐字取自 SPEC）。"""
    spec_text = (REPO / "docs" / "NUMVIEW_SPEC.md").read_text(encoding="utf-8")
    for sentence in ICPAGE_RULING_QUOTE:
        assert f"「{sentence}」" in spec_text, sentence
    assert icpage_violations(_load_decisions()) == []


def test_postic_float64_requires_user_ruling() -> None:
    """Task 1.5 ⑤：D-POSTIC 選 `polars_float64` 必具 `user_ruling`，無則只能 `retain`。"""
    assert postic_violations(_load_decisions()) == []


def test_value_changing_decisions_have_user_ruling() -> None:
    """Task 1.5 ⑥：任一改特徵階段或公開輸出值之筆皆具 `user_ruling`。"""
    assert change_ruling_violations(_load_decisions()) == []


# ---------------------------------------------------------------------------------------------- 驗證（Task 0.4，名含 estimate）

def test_estimate_receipt_fields_and_coverage() -> None:
    """Task 0.4 ①：估時收據（恰一份）欄位齊全，格清單＝`kline_cache.h5` 獨立列舉，跑別涵蓋 G1（四臂）／G2／G3 與
    Phase 1 全部生成，格 C 基準逐 tf。"""
    receipt = _load_receipt(_estimate_receipt_path())
    assert estimate_receipt_violations(receipt, _kline_index()) == []


def test_estimate_gate_require_raises_in_three_cases(tmp_path: Path) -> None:
    """Task 0.4 ②：`_estimate_gate.require` 於收據缺、`reported_at` 缺、格不在清單三案各拋 `EstimateGateError`。"""
    assert gate_require_violations(GATE, tmp_path) == []


def test_estimate_gate_called_before_generation_in_heavy_scripts() -> None:
    """Task 0.4 ③：凍結腳本與每個生成型探針於 `main` 頂層、任何生成呼叫之前呼叫 `require(<跑別>, …)`。"""
    assert gate_call_violations() == []


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_05_criteria_change_only_via_v2_before_receipts() -> None:
    """邊界①（SPEC Task 0.3）：判準須改 ⇒ 只准於任何收據產出前以新檔名 `preregistered_criteria_v2.json` 取代並刪舊檔。
    斷言：兩檔名恰一存在；v1 現行 ⇒ v2 無任何歷史；v2 現行 ⇒ v1 不在 HEAD、v2 恰一提交，且 v1／v2 每筆提交皆早於每份收據之
    首次提交（收據之判定範圍同③：全部 *-numview-*.json）。"""
    v1, v2 = CRITERIA_V1.is_file(), CRITERIA_V2.is_file()
    assert v1 != v2, f"判準檔須恰一存在（v1={v1}、v2={v2}）"
    if v1:
        assert _git_commits(_rel(CRITERIA_V2)) == []
    else:
        assert _git("cat-file", "-e", f"HEAD:{_rel(CRITERIA_V1)}").returncode != 0, "v1 仍在 HEAD（須刪舊檔）"
        assert len(_git_commits(_rel(CRITERIA_V2))) == 1
        assert criteria_after_receipt_violations() == []


def test_boundary_06_criteria_unchanged_after_receipts_defect_recorded() -> None:
    """邊界②（SPEC Task 0.3）：收據產出後發現判準缺陷 ⇒ 不改判準（v1／v2 皆無晚於首份收據之提交），於決定紀錄
    `measurement_limitations` 具名列為量測限制（`kind=criteria_defect` 之項具唯一 id 與描述）。"""
    assert criteria_after_receipt_violations() == []
    assert limitation_violations(_load_decisions()) == []


@pytest.mark.parametrize("source", ["real_receipt", "partial_block_mutant"])
def test_boundary_07_estimate_cell_c_blocked_whole_tf(source: str) -> None:
    """邊界①（SPEC Task 0.4）：格 C 單格實測逾機器上限 ⇒ 該 tf 之格 C 全列 blocked-by 硬體、不逐格試（無逐格耗時）。
    真實收據須一致；以收據結構之 mutant（某 tf 判阻擋而只列一格、且他格仍有逐格耗時）驗檢查器翻紅（閘邏輯單元，非特徵資料）。"""
    if source == "real_receipt":
        assert cell_c_blocked_violations(_load_receipt(_estimate_receipt_path())) == []
    else:
        receipt = {
            "cells": {"A": [], "B": [], "C": [{"id": "c1", "kind": "C", "symbol": "S1", "timeframes": ["t1"]},
                                             {"id": "c2", "kind": "C", "symbol": "S2", "timeframes": ["t1"]}]},
            "cell_c_baseline": {"t1": {"blocked_by": BLOCKED_BY_HARDWARE, "reason": "memory guard"}},
            "blocked": [{"cell": "c1", "blocked_by": BLOCKED_BY_HARDWARE, "reason": "memory guard"}],
            "run_kinds": {"precision_chain": {"per_cell_seconds": {"c2": 1.0}}},
        }
        violations = cell_c_blocked_violations(receipt)
        assert "t1：格 C c2 未列 blocked-by 硬體" in violations, violations
        assert "t1：已阻擋之格 C c2 仍有逐格耗時（不得逐格試）" in violations, violations


def test_boundary_08_estimate_low_disk_rc1_lists_required_space(monkeypatch: pytest.MonkeyPatch,
                                                                capsys: pytest.CaptureFixture) -> None:
    """邊界②（SPEC Task 0.4）：磁碟 < 30 GB ⇒ `estimate.main` rc=1、輸出列所需空間（含下限 GB 數）、未啟動任何生成
    （spy `FeatureFactory.generate_features`／`run_ic_first`）、未新寫估時收據。"""
    calls: List[str] = []

    def spy(name: str):
        def _spy(*args: Any, **kwargs: Any) -> Any:
            calls.append(name)
            raise RuntimeError(f"磁碟不足時不得啟動生成：{name}")
        return _spy

    monkeypatch.setattr(FeatureFactory, "generate_features", spy("generate_features"))
    monkeypatch.setattr(FeatureFactory, "run_ic_first", spy("run_ic_first"))
    monkeypatch.setattr(ESTIMATOR, "disk_free_gb", lambda path: ESTIMATOR.MIN_FREE_DISK_GB - 0.1)
    before = sorted(p.name for p in nh.RECEIPTS_DIR.glob(GATE.ESTIMATE_RECEIPT_GLOB))
    rc = ESTIMATOR.main([])
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert rc == 1
    assert calls == []
    assert str(ESTIMATOR.MIN_FREE_DISK_GB) in output and "GB" in output.upper(), output
    assert sorted(p.name for p in nh.RECEIPTS_DIR.glob(GATE.ESTIMATE_RECEIPT_GLOB)) == before


def test_boundary_21_unforeseen_situation_recorded_as_limitation() -> None:
    """邊界①（SPEC Task 1.5）：收據顯示判準未預見之情況 ⇒ 記為量測限制、不事後加判準。流程邊界以結構斷言編碼：判準檔於
    首份收據後無任何提交；判準檔之 `decisions_schema` 要求 `measurement_limitations`；決定紀錄該清單合格式。"""
    assert criteria_after_receipt_violations() == []
    schema = _load_criteria()["decisions_schema"]
    assert "measurement_limitations" in (schema.get("required") or [])
    assert limitation_violations(_load_decisions()) == []


def test_boundary_22_committee_split_decided_by_evidence_or_named_residual() -> None:
    """邊界②（SPEC Task 1.5）：委員分歧 ⇒ 依碼證與收據（每筆 `evidence` 皆可解析至 numview 收據之列），不決者採較嚴版並
    具名殘留（`split_resolution=stricter_with_residual` ⇒ `residual_id` 合 `NUMVIEW-R<n>`）。"""
    assert evidence_violations(_load_decisions()) == []


# ---------------------------------------------------------------------------------------------- mutation（Task 0.3）

def test_mutation_criteria_one_char_changed_turns_frozen_and_receipts_red(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：判準檔改一字（工作樹位元組改一字，並以多一筆提交模擬已提交之改動）⇒ ②③皆紅。"""
    assert frozen_violations() == [] and receipt_violations() == []
    this = sys.modules[__name__]
    original_bytes, original_commits = _read_criteria_bytes, _git_commits
    criteria_rel = _rel(_criteria_path())

    def mutated_bytes(path: Path) -> bytes:
        data = bytearray(original_bytes(path))
        index = next(i for i, ch in enumerate(data) if chr(ch).isalpha())
        data[index] = ord("x") if chr(data[index]) != "x" else ord("y")
        return bytes(data)

    monkeypatch.setattr(this, "_read_criteria_bytes", mutated_bytes)
    assert frozen_violations() != []
    assert any("criteria_sha256" in v for v in receipt_violations())
    monkeypatch.setattr(this, "_git_commits",
                        lambda rel: (["f" * 40] + original_commits(rel)) if rel == criteria_rel else original_commits(rel))
    assert any("提交數" in v for v in frozen_violations())


def test_mutation_receipt_criteria_sha_rewritten(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：收據改寫 `criteria_sha256` ⇒ ③紅。"""
    assert receipt_violations() == []
    original = _load_receipt
    monkeypatch.setattr(sys.modules[__name__], "_load_receipt",
                        lambda path: {**original(path), "criteria_sha256": "0" * 64})
    assert any("criteria_sha256 ≠ 現行判準檔" in v for v in receipt_violations())


def test_mutation_material_judge_tau_lt_1_treats_nan_as_unflipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：判定改為 `tau < 1`（NaN 視為未翻轉）⇒ ④紅（全 ties／全 NaN／有效對數 < 2 誤判非 material）。"""
    assert material_judge_violations() == []
    monkeypatch.setattr(sys.modules[__name__], "_tau_b_material", lambda tau: tau < 1.0)
    violations = material_judge_violations()
    assert {v.split("：", 1)[0] for v in violations} == {"all_ties", "all_nan", "fewer_than_2_pairs"}, violations


# ---------------------------------------------------------------------------------------------- mutation（Task 1.5）

def _mutated_decisions(mutate) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
    decisions = copy.deepcopy(_load_decisions())
    mutate(decisions)
    return decisions


def _record_of(decisions: Dict[str, Any], key: str) -> Dict[str, Any]:
    record = decisions["decisions"].get(key)
    assert isinstance(record, dict), key
    return record


def test_mutation_trigger_judgment_inconsistent_with_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：把某觸發判定改為與收據不符 ⇒ ②紅。"""
    criteria = _load_criteria()
    assert trigger_violations(_load_decisions(), criteria) == []

    key = sorted(_load_decisions()["decisions"])[0]

    def flip(decisions: Dict[str, Any]) -> None:
        record = decisions["decisions"][key]
        record["triggered"] = not record["triggered"]

    mutated = _mutated_decisions(flip)
    monkeypatch.setattr(sys.modules[__name__], "_load_decisions", lambda: copy.deepcopy(mutated))
    assert any(v.startswith(f"{key}：triggered=") for v in trigger_violations(_load_decisions(), criteria))


def test_mutation_user_ruling_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：自 `changes_public_output=true` 之筆（D-ICPAGE-ARM 必為之）刪 `user_ruling` ⇒ ③紅。"""
    assert ruling_violations(_load_decisions()) == []
    mutated = _mutated_decisions(lambda d: _record_of(d, "d_icpage_arm").pop("user_ruling"))
    monkeypatch.setattr(sys.modules[__name__], "_load_decisions", lambda: copy.deepcopy(mutated))
    assert any(v.startswith("d_icpage_arm：") for v in ruling_violations(_load_decisions()))


@pytest.mark.parametrize("variant", ["public_false", "public_false_g1_pairwise_equal", "ruling_missing",
                                     "ruling_other_date"])
def test_mutation_icpage_arm_not_public_or_missing_ruling(variant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：D-ICPAGE-ARM 標 `changes_public_output=false`（含報告欄記 G1 各臂份兩兩相等之情形）或缺
    2026-10-21 `user_ruling` ⇒ ④紅。"""
    assert icpage_violations(_load_decisions()) == []

    def mutate(decisions: Dict[str, Any]) -> None:
        record = _record_of(decisions, "d_icpage_arm")
        if variant.startswith("public_false"):
            record["changes_public_output"] = False
        if variant == "public_false_g1_pairwise_equal":
            record.setdefault("report", {})["g1_arm_copies_pairwise_equal"] = True
        if variant == "ruling_missing":
            record.pop("user_ruling", None)
        if variant == "ruling_other_date":
            record["user_ruling"] = {**record["user_ruling"], "date": "2026-10-20"}

    mutated = _mutated_decisions(mutate)
    monkeypatch.setattr(sys.modules[__name__], "_load_decisions", lambda: copy.deepcopy(mutated))
    assert icpage_violations(_load_decisions()) != []


def test_mutation_postic_float64_without_user_ruling(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：D-POSTIC 選 `polars_float64` 而無 `user_ruling` ⇒ ⑤紅。"""
    assert postic_violations(_load_decisions()) == []

    def mutate(decisions: Dict[str, Any]) -> None:
        record = _record_of(decisions, "d_postic")
        record["choice"] = POSTIC_CANDIDATE
        record["changes_public_output"] = True
        record.pop("user_ruling", None)

    mutated = _mutated_decisions(mutate)
    monkeypatch.setattr(sys.modules[__name__], "_load_decisions", lambda: copy.deepcopy(mutated))
    assert "d_postic：選 polars_float64 而缺 user_ruling" in postic_violations(_load_decisions())


# ---------------------------------------------------------------------------------------------- mutation（Task 0.4，名含 estimate）

def test_mutation_estimate_freeze_script_without_gate_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：凍結腳本刪去前置呼叫（以 `_read_text` 接縫餵入 AST 移除 `require` 敘述後之原始碼）⇒ ③紅。"""
    assert gate_call_violations_for(FREEZE_SCRIPT, "freeze_baseline", mandated=True) == []
    original = _read_text

    def stripped(path: Path) -> str:
        text = original(path)
        if Path(path) != FREEZE_SCRIPT:
            return text
        tree = ast.fix_missing_locations(_DropRequire().visit(ast.parse(text)))
        return ast.unparse(tree)

    monkeypatch.setattr(sys.modules[__name__], "_read_text", stripped)
    violations = gate_call_violations()
    assert any(v.startswith(f"{_rel(FREEZE_SCRIPT)}：") for v in violations), violations


def test_mutation_estimate_require_log_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutation：`_estimate_gate.require` 改為只 log 不拋 ⇒ ②紅。"""
    assert gate_require_violations(GATE, tmp_path / "real") == []
    logged: List[Tuple[str, Tuple[str, ...]]] = []
    monkeypatch.setattr(GATE, "require",
                        lambda run_kind, cells, *, receipts_dir=None: logged.append((run_kind, tuple(cells))))
    violations = gate_require_violations(GATE, tmp_path / "mutant")
    assert len(violations) == 3 and all(v.endswith("未拋錯（前置閘失效）") for v in violations), violations
    assert len(logged) == 4
