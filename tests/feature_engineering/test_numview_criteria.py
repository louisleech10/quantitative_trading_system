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
（凍結跑別之 G1 四臂〔臂集＝契約 `post_ic_arm_values`〕／G2／G3、Phase 1 全部生成，與 Phase 2–4 驗收重產之
`regen_*` 跑別〔`REGEN_REQUIREMENTS`；R15-A〕，後者另以 `preprov_cells` 列測試直接生成之 PRE-PROV 格）；格 C 之 12h 基準可引
`handoffs/run_receipts/20261020-preprov-fullrun-size.md`，其餘 tf 各實測；②`_estimate_gate.require` 於收據缺、`reported_at`
缺、格不在清單三案各拋 `EstimateGateError`（另以清單內之格為正對照）；③AST：`scripts/numview_freeze_baseline.py` 與
`handoffs/run_receipts/numview_probes/` 下每個呼叫生成入口之腳本（SPEC Task 1.1–1.3 點名之三探針一律須呼叫；`estimate.py`
為估時器本身、`_estimate_gate.py` 為閘本身，豁免），於其 `main` 之頂層敘述呼叫 `require(<跑別>, …)`，且行序早於 `main`
內任何（直接或經本模組函式間接之）生成呼叫；另（R15-A）凍結腳本之 `generate_cell` 以必填 `run_kind` 接收跑別、首個陳述式級
呼叫為 `require(run_kind, …)`，`freeze_cell` 之生成一律經 `generate_cell(..., run_kind=run_kind)`。
mutation（Task 0.4）：凍結腳本刪前置呼叫 ⇒ ③紅；`require` 改只 log ⇒ ②紅；`generate_cell` 刪 `require` ⇒ R15-A 閘紅；
收據缺任一 `regen_*` 跑別 ⇒ ①紅。
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
import inspect
import json
import math
import os
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
#: 判準 v2 之檔名（歷史；判準 v3 起之取代規則以 vN 泛化）
CRITERIA_V2_NAME = "preregistered_criteria_v2.json"
_PRESENT_CRITERIA = sorted(p for p in nh.GOLDEN_DIR.glob("preregistered_criteria*.json") if p.is_file())
#: 現行之取代版判準（vN，N≥2；邊界 05「v2 現行」分支之 v2 泛化為現行取代版）；無取代版 ⇒ v2 檔名
CRITERIA_V2: Path = (_PRESENT_CRITERIA[0] if len(_PRESENT_CRITERIA) == 1 and _PRESENT_CRITERIA[0] != CRITERIA_V1
                     else nh.GOLDEN_DIR / CRITERIA_V2_NAME)
#: 判準檔名樣式（v1＝preregistered_criteria.json，其後 preregistered_criteria_v<N>.json；判準 v3 起之取代規則）
CRITERIA_GLOB = "preregistered_criteria*.json"
#: 估時收據（Task 0.4）：綁現行判準之 sha256、判準變動即須重估（`_estimate_gate`）——非「判準凍結後不得再改」所指之量測收據
ESTIMATE_RECEIPT_SUFFIX = "-numview-estimate.json"
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
#: Phase 2–4 驗收重產之跑別（SPEC Task 0.4 驗證①、R15-A）→ 須涵蓋之格：`cells` 之格類（"A"／"AB"／"" 無）或
#: "A:BTCUSDT:1h"（單一格 A），`preprov` 為測試直接經 `preprov_helpers` 生成之 PRE-PROV 格名（"*legacy*"＝沿用基準
#: `tests/_golden/preprov/pre_change_fingerprints.json` 之全部格）。來源（各測試檔實際之生成呼叫）：
#:   regen_t21 ← test_numview_policy.py `CellLab`（④，格 A BTCUSDT 1h）；regen_t22 ← tests/api/test_numview_ic_page.py `G1Lab`
#:   （契約 arm_policy 狀態）；regen_t3_core ← test_numview_core.py `_Runs`／`_generate`（Task 3.1–3.3 共用）＋`ic_first_default`；
#:   regen_t34 ← `G1Lab`（契約 arm_ref 狀態）＋邊界 38 之 `ic_first_empty`；regen_t42 ← test_numview_identity.py
#:   `CELL`／`IC_FIRST_CELL`；regen_t43 ← tests/api/test_numview_ic_page.py `REGEN_CELL`；regen_section_g ←
#:   test_numview_acceptance.py `_Regen`（freeze_cell）＋`legacy_runs`。
REGEN_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "regen_t21": {"cells": "A:BTCUSDT:1h", "preprov": ()},
    "regen_t22": {"cells": "A", "preprov": ()},
    "regen_t3_core": {"cells": "AB", "preprov": ("ic_first_default",)},
    "regen_t34": {"cells": "A", "preprov": ("ic_first_empty",)},
    "regen_t42": {"cells": "", "preprov": ("h1_stat_off", "ic_first")},
    "regen_t43": {"cells": "", "preprov": ("h1_pp_off",)},
    "regen_section_g": {"cells": "AB", "preprov": ("*legacy*",)},
}
#: 凍結腳本中受估時前置閘之生成函式（R15-A）：`generate_cell` 首個陳述式級呼叫須為 `require(run_kind, …)`；
#: `freeze_cell` 之生成一律經 `generate_cell(..., run_kind=run_kind)`
CELL_GATED_FUNCTIONS = ("generate_cell", "freeze_cell")


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
    """現行判準檔名：`preregistered_criteria*.json`（v1、v2、v3…）恰一存在者（邊界 05：vN→vN+1 取代並刪舊檔）；非恰一 ⇒
    沿原規則（v2 存在即 v2，否則 v1；其後之讀取斷言即紅）。"""
    present = sorted(p for p in nh.GOLDEN_DIR.glob(CRITERIA_GLOB) if p.is_file())
    if len(present) == 1:
        return present[0]
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
    """真實 `kline_cache.h5` 之 symbol → tf 清單（只讀鍵名；不寫死清單）；只計含 `data` 資料集之週期，
    無週期之頂層鍵（如 `_metadata`）不算 symbol（同 `test_numview_baseline.kline_inventory`）。"""
    out: Dict[str, List[str]] = {}
    with h5py.File(nh.KLINE_PATH, "r") as f:
        for s in sorted(f.keys()):
            group = f[s]
            if not hasattr(group, "keys"):
                continue
            tfs = sorted(str(tf) for tf in group.keys() if hasattr(group[tf], "keys") and "data" in group[tf])
            if tfs:
                out[str(s)] = tfs
    return out


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


def _measurement_receipt_paths() -> List[Path]:
    """「判準凍結後不得再改」所指之收據：全部 *-numview-*.json 除估時收據（估時收據綁現行判準之 sha256，判準以 vN+1 取代時
    須重估，本即不約束判準；③ 之 sha 相符與提交序仍涵蓋之）。"""
    return [p for p in _receipt_paths() if not p.name.endswith(ESTIMATE_RECEIPT_SUFFIX)]


def _criteria_name_paths() -> List[Path]:
    """判準檔之全部版本檔名（工作樹現存者∪git 歷史中曾出現者；樣式 `preregistered_criteria*.json`）。"""
    names = {p.name for p in nh.GOLDEN_DIR.glob(CRITERIA_GLOB)} | {CRITERIA_V1.name, CRITERIA_V2_NAME, CRITERIA_V2.name}
    out = _git("log", "--all", "--format=", "--name-only", "--", _rel(nh.GOLDEN_DIR))
    if out.returncode == 0:
        names |= {Path(n).name for n in out.stdout.decode().split() if re.fullmatch(r"preregistered_criteria.*\.json", Path(n).name)}
    return [nh.GOLDEN_DIR / n for n in sorted(names)]


def _first_receipt_commits() -> List[str]:
    commits = [_git_commits(_rel(p)) for p in _measurement_receipt_paths()]
    return [c[-1] for c in commits if c]


def criteria_after_receipt_violations() -> List[str]:
    """收據產出後判準檔（全部版本檔名）不得再有提交：每筆觸及判準檔之提交皆為每份量測收據（估時收據除外）首次提交之嚴格祖先。"""
    firsts = _first_receipt_commits()
    if not firsts or len(firsts) != len(_measurement_receipt_paths()):
        return ["無收據或有收據未提交（無從判定先後）"]
    out: List[str] = []
    for path in _criteria_name_paths():
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
    out += re_presentation_violations(r)
    return out


def _repo_file_exists(rel: str) -> bool:
    return (REPO / rel).is_file()


def _perf_receipt_first_commit_date(rel: str) -> Optional[str]:
    """效能基準收據之首次提交日（委由 `numview_helpers.perf_receipt_first_commit_date`；mutation 以 monkeypatch 換之）。"""
    return nh.perf_receipt_first_commit_date(rel)


def re_presentation_violations(record: Mapping[str, Any]) -> List[str]:
    """⑦（SPEC v17 §A 重新呈報條件、Task 1.5 ⑦、Task 3.4 施工前提）：委由 `numview_helpers.re_presentation_violations`
    （與 b4 IC 頁閘同一判定），收據存在與提交日經本模組可注入之查詢函式。不含 assert。"""
    return nh.re_presentation_violations(record, exists=lambda rel: _repo_file_exists(rel),
                                         committed_date=lambda rel: _perf_receipt_first_commit_date(rel),
                                         load=lambda rel: _load_perf_receipt(rel))


def _load_perf_receipt(rel: str) -> Any:
    """效能基準收據內容（mutation 以 monkeypatch 換之）。"""
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


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


def regen_required_cells(spec: str, index: Mapping[str, Tuple[str, Mapping[str, Any]]],
                         ids: Mapping[str, Set[str]]) -> Set[str]:
    """`REGEN_REQUIREMENTS[*]["cells"]` → 須涵蓋之格 id：""＝無；"A"／"AB"＝該格類全部；"A:<symbol>:<tf>"＝該單一格 A
    （收據中須恰一格，否則以不存在之佔位 id 使涵蓋檢查紅）。"""
    if not spec:
        return set()
    if ":" in spec:
        cat, symbol, tf = spec.split(":")
        hits = {i for i, (c, cell) in index.items() if c == cat and cell.get("symbol") == symbol
                and _single_tf(cell) == tf}
        return hits if len(hits) == 1 else {f"<{spec} 須恰一格，實得 {len(hits)}>"}
    return set().union(*(ids.get(cat, set()) for cat in spec))


def regen_required_preprov(names: Sequence[str]) -> Set[str]:
    """`REGEN_REQUIREMENTS[*]["preprov"]` → 須涵蓋之 PRE-PROV 格名；"*legacy*"＝沿用基準之全部格（讀檔，不寫死）。"""
    out: Set[str] = set()
    for name in names:
        if name == "*legacy*":
            legacy = json.loads((REPO / "tests/_golden/preprov/pre_change_fingerprints.json").read_text(encoding="utf-8"))
            out |= set(legacy["cells"])
        else:
            out.add(name)
    return out


def known_preprov_cells() -> Set[str]:
    """PRE-PROV 之合法格名（`preprov_helpers.CELLS` ∪ `VARIANTS`）。"""
    from tests.feature_engineering import preprov_helpers as ph

    return set(ph.CELLS) | set(ph.VARIANTS)


def _cell_index(receipt: Mapping[str, Any]) -> Dict[str, Tuple[str, Mapping[str, Any]]]:
    """格 id → （格類, 格物件）。"""
    out: Dict[str, Tuple[str, Mapping[str, Any]]] = {}
    for category in CELL_CATEGORIES:
        for cell in (receipt.get("cells") or {}).get(category) or []:
            if isinstance(cell, Mapping) and isinstance(cell.get("id"), str):
                out[cell["id"]] = (category, cell)
    return out


def estimate_receipt_violations(receipt: Mapping[str, Any], kline: Mapping[str, List[str]]) -> List[str]:
    if nh.criteria_cell_list() is not None:  # 判準 v3 起：封閉格清單（路徑覆蓋）
        return closed_estimate_receipt_violations(receipt, kline)
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
    multi = {s: sorted(tfs) for s, tfs in kline.items() if len(tfs) >= 2}  # 格 B 只對有 ≥2 週期之 symbol
    if b_map != multi or len(cells["B"]) != len(multi):
        out.append("格 B ≠ 每個 symbol 一格且含其全部週期")
    ids = {c: {i for i, (cat, _) in index.items() if cat == c} for c in CELL_CATEGORIES}
    run_kinds = receipt.get("run_kinds")
    if not isinstance(run_kinds, Mapping):
        return out + ["run_kinds 缺"]
    required_cover = {
        "freeze_baseline": ids["A"] | ids["B"], "postic_branchdiff": ids["A"] | ids["B"],
        "precision_chain": ids["A"] | ids["B"] | ids["C"], "l2_arm_matrix": ids["A"] | ids["B"],
    }
    required_preprov: Dict[str, Set[str]] = {}
    for kind, req in REGEN_REQUIREMENTS.items():
        if kind not in ESTIMATOR.RUN_KINDS:
            out.append(f"estimate.RUN_KINDS 缺 Phase 2–4 驗收重產跑別 {kind}（R15-A）")
        required_cover[kind] = regen_required_cells(req["cells"], index, ids)
        required_preprov[kind] = regen_required_preprov(req["preprov"])
    for kind in ESTIMATOR.RUN_KINDS:
        node = run_kinds.get(kind)
        if not isinstance(node, Mapping):
            out.append(f"run_kinds 缺跑別 {kind}")
            continue
        listed = set(node.get("cells") or [])
        preprov_listed = set(node.get("preprov_cells") or [])
        if (not listed and not preprov_listed) or not listed <= set(index):
            out.append(f"{kind}：cells 為空或含未列舉之格")
        missing = required_cover.get(kind, set()) - listed
        if missing:
            out.append(f"{kind}：未涵蓋 {len(missing)} 格（不得以縮減格降低總估時）")
        missing_preprov = required_preprov.get(kind, set()) - preprov_listed
        if missing_preprov:
            out.append(f"{kind}：未涵蓋 PRE-PROV 格 {sorted(missing_preprov)}")
        unknown_preprov = preprov_listed - known_preprov_cells()
        if unknown_preprov:
            out.append(f"{kind}：preprov_cells 含未知格 {sorted(unknown_preprov)}")
        categories = {index[i][0] for i in listed if i in index} | ({"preprov"} if preprov_listed else set())
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


def _current_criteria_sha(gate: ModuleType) -> str:
    """估時前置閘所綁之現行判準檔 sha256（`_estimate_gate.CRITERIA_PATH`）。"""
    return hashlib.sha256(Path(gate.CRITERIA_PATH).read_bytes()).hexdigest()


def stale_criteria_violations(gate: ModuleType, tmp_path: Path) -> List[str]:
    """估時收據須綁現行判準（審碼 b1 r1）：`criteria_sha256` 缺、或不等於現行判準檔 ⇒ 各拋 `EstimateGateError`。"""
    kind, cell, name = "freeze_baseline", "numview_cell_listed", "20261021-numview-estimate.json"
    base = {"reported_at": "2026-10-21T00:00:00+08:00", "run_kinds": {kind: {"cells": [cell]}}}
    out: List[str] = []
    for i, (label, receipt) in enumerate([("criteria_sha256 缺", base),
                                          ("criteria_sha256 不等於現行判準檔", {**base, "criteria_sha256": "0" * 64})]):
        rdir = tmp_path / f"stale{i}"
        rdir.mkdir(parents=True)
        (rdir / name).write_text(json.dumps(receipt), encoding="utf-8")
        try:
            gate.require(kind, [cell], receipts_dir=rdir)
        except gate.EstimateGateError:
            continue
        except Exception as exc:  # noqa: BLE001 — 錯誤型別不符亦屬違規
            out.append(f"{label}：拋 {type(exc).__name__} 而非 EstimateGateError")
            continue
        out.append(f"{label}：未拋錯（判準綁定失效）")
    return out


def gate_require_violations(gate: ModuleType, tmp_path: Path) -> List[str]:
    """②：收據缺／`reported_at` 缺／格不在清單 ⇒ 各拋 `EstimateGateError`；清單內之格且綁現行判準 ⇒ 不拋（正對照）。
    （判準綁定之兩案見 `stale_criteria_violations`。）"""
    in_list, not_in_list, kind = "numview_cell_listed", "numview_cell_unlisted", "freeze_baseline"
    name = "20261021-numview-estimate.json"
    base = {"reported_at": "2026-10-21T00:00:00+08:00", "criteria_sha256": _current_criteria_sha(gate),
            "run_kinds": {kind: {"cells": [in_list]}}}
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


def _kwonly_without_default(fn: ast.FunctionDef, name: str) -> bool:
    for arg, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults):
        if arg.arg == name:
            return default is None
    return False


def cell_gate_violations(path: Path = FREEZE_SCRIPT) -> List[str]:
    """R15-A：凍結腳本之 `generate_cell` 以必填關鍵字 `run_kind` 接收跑別，其首個陳述式級呼叫為 `require(run_kind, …)`，
    且任何生成呼叫皆晚於之（函式內須有生成呼叫，否則判未實作）；`freeze_cell` 亦以必填 `run_kind` 接收，其生成一律為
    `generate_cell(..., run_kind=run_kind)`（無其他生成入口）。AST 秒級。"""
    rel = _rel(path)
    tree = ast.parse(_read_text(path), filename=rel)
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out: List[str] = []
    for name in CELL_GATED_FUNCTIONS:
        if name not in funcs:
            out.append(f"{rel}：缺函式 {name}")
            continue
        if not _kwonly_without_default(funcs[name], "run_kind"):
            out.append(f"{rel}：{name} 須以無預設之關鍵字參數 run_kind 接收估時跑別")
    if out:
        return out
    gen = funcs["generate_cell"]
    calls = [c for c in ast.walk(gen) if isinstance(c, ast.Call)]
    gen_lines = sorted(c.lineno for c in calls if _is_generation_call(c) and _call_name(c) != "generate_cell")
    first_call = None
    for stmt in gen.body:
        if isinstance(stmt, (ast.Expr, ast.Assign, ast.AnnAssign)) and isinstance(stmt.value, ast.Call):
            first_call = stmt.value
            break
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)):
            break
    if first_call is None or not _is_require_call(first_call):
        out.append(f"{rel}：generate_cell 之首個陳述式級呼叫非 _estimate_gate.require")
    else:
        arg0 = first_call.args[0] if first_call.args else None
        if not (isinstance(arg0, ast.Name) and arg0.id == "run_kind"):
            out.append(f"{rel}：generate_cell 之 require 首參數須為 run_kind（原樣傳遞呼叫端跑別）")
        if gen_lines and gen_lines[0] <= first_call.lineno:
            out.append(f"{rel}：generate_cell 之生成呼叫（第 {gen_lines[0]} 行）早於 require")
    if not gen_lines:
        out.append(f"{rel}：generate_cell 未見任何生成呼叫（未實作或生成入口未被辨識）")
    frz = funcs["freeze_cell"]
    frz_gen = [c for c in ast.walk(frz) if isinstance(c, ast.Call) and _is_generation_call(c)]
    if not frz_gen:
        out.append(f"{rel}：freeze_cell 未見生成呼叫（須經 generate_cell）")
    for call in frz_gen:
        kw = {k.arg: k.value for k in call.keywords}
        if _call_name(call) != "generate_cell" or not (isinstance(kw.get("run_kind"), ast.Name)
                                                       and kw["run_kind"].id == "run_kind"):
            out.append(f"{rel}：freeze_cell 第 {call.lineno} 行之生成未經 generate_cell(..., run_kind=run_kind)")
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


def swap_calibration_violations(receipt: Mapping[str, Any]) -> List[str]:
    """判準 `cell_rules.watchdog._basis` 校準規則（審碼 r12 CODEX-R12-P1-01）：收據中正常完成（measured）之格，最重之
    格 C 必記 `swap_growth_max_mb` 與 `swap_growth_threshold_mb`；凡記有者其最大增長須 < 門檻之半（否則 Phase 1 前須以
    vN→vN+1 調整比例）。不含 assert。"""
    out: List[str] = []
    current = {str(c.get("id")) for cells in (receipt.get("cells") or {}).values() if isinstance(cells, list)
               for c in cells if isinstance(c, Mapping)}  # 現行判準格清單；快取殘留之舊格（如 v3 前之 C 4h／12h）不計
    for key, m in sorted((receipt.get("measurements") or {}).items()):
        if not isinstance(m, Mapping) or m.get("status") != "measured" or (current and key not in current):
            continue
        grow, cap = m.get("swap_growth_max_mb"), m.get("swap_growth_threshold_mb")
        if grow is None:
            if m.get("category") == "C":
                out.append(f"{key}：最重之格 C 未記 swap_growth_max_mb（未經現行判準正常跑記錄）")
            continue
        if cap is None:  # 判準 v6：swap 終止條件停用（比例 null）⇒ 只記錄、不比門檻
            continue
        if float(grow) >= 0.5 * float(cap):
            out.append(f"{key}：swap 增長 {float(grow):.0f} MB ≥ 門檻 {float(cap):.0f} MB 之半 ⇒ Phase 1 前須調整比例")
    return out


def measurement_identity_violations(receipt: Mapping[str, Any]) -> List[str]:
    """收據實測列之身分（審碼 r13 CODEX-R13-P1-01）：格類（A／B／C）之列，外層鍵＝內層 `cell_id`＝現行格清單之 id；不在現行格清單之
    格類列不得出現在 `measurements`（舊格只准在 `legacy_measurements`）。不含 assert。"""
    current = {str(c.get("id")) for cells in (receipt.get("cells") or {}).values() if isinstance(cells, list)
               for c in cells if isinstance(c, Mapping)}
    out: List[str] = []
    for key, m in sorted((receipt.get("measurements") or {}).items()):
        if not isinstance(m, Mapping) or m.get("category") not in ("A", "B", "C"):
            continue
        if key not in current:
            out.append(f"{key}：格類實測列不在現行格清單（應隔離於 legacy_measurements）")
        if str(m.get("cell_id")) != key:
            out.append(f"{key}：內層 cell_id={m.get('cell_id')!r} ≠ 外層鍵（前史表等以 cell_id 對接會對不到）")
    return out


def test_estimate_receipt_measurement_identity() -> None:
    """Task 0.4：現行估時收據之格類實測列身分一致且只含現行格（見 `measurement_identity_violations`）。"""
    assert measurement_identity_violations(_load_receipt(_estimate_receipt_path())) == []


@pytest.mark.parametrize("mutant", [None, "nested_id_stale", "legacy_cell_in_measurements", "preprov_ignored"])
def test_mutation_measurement_identity(mutant: Optional[str]) -> None:
    """mutation：內層 cell_id 為舊 id ⇒ 紅；現行清單外之格類列混入 measurements ⇒ 紅；非格類（preprov）列不受此檢查 ⇒ 不紅。"""
    receipt: Dict[str, Any] = {"cells": {"B": [{"id": "B_BTCUSDT_1h_4h"}], "C": [{"id": "C_BTCUSDT_1h"}]},
                               "measurements": {"B_BTCUSDT_1h_4h": {"category": "B", "cell_id": "B_BTCUSDT_1h_4h"},
                                                "C_BTCUSDT_1h": {"category": "C", "cell_id": "C_BTCUSDT_1h"}}}
    if mutant == "nested_id_stale":
        receipt["measurements"]["B_BTCUSDT_1h_4h"]["cell_id"] = "B_BTCUSDT_1h_4h_12h"
    elif mutant == "legacy_cell_in_measurements":
        receipt["measurements"]["C_BTCUSDT_4h"] = {"category": "C", "cell_id": "C_BTCUSDT_4h"}
    elif mutant == "preprov_ignored":
        receipt["measurements"]["preprov:h1_stat_on"] = {"category": "preprov", "cell_id": None}
    assert (measurement_identity_violations(receipt) != []) is (mutant in ("nested_id_stale", "legacy_cell_in_measurements"))


def test_migrate_cache_rewrites_nested_cell_id_for_rehomed_b() -> None:
    """估時器 `migrate_cache`：舊格 B（三週期 id）依訓練週期改歸現行格 B 時，內層 cell_id 同步為新鍵、原值記 migrated_cell_id。"""
    cells = {"B": [{"id": "B_BTCUSDT_1h_4h", "timeframes": ["1h", "4h"]}]}
    old = {"B": {"category": "B", "cell_id": "B_BTCUSDT_1h_4h_12h", "training_timeframes": ["1h", "4h"]}}
    row = ESTIMATOR.migrate_cache(old, cells)["B_BTCUSDT_1h_4h"]
    assert row["cell_id"] == "B_BTCUSDT_1h_4h" and row["migrated_cell_id"] == "B_BTCUSDT_1h_4h_12h", row
    assert row["migrated_from"] == "B", row


def test_estimate_receipt_swap_growth_calibrated() -> None:
    """Task 0.4：現行估時收據之卡住偵測 swap 門檻已以正常跑校準（見 `swap_calibration_violations`）。收據未依現行判準
    重產前為紅。"""
    assert swap_calibration_violations(_load_receipt(_estimate_receipt_path())) == []


@pytest.mark.parametrize("mutant", [None, "c_missing_fields", "growth_over_half", "non_c_missing_ok"])
def test_mutation_swap_calibration(mutant: Optional[str]) -> None:
    """mutation：C 格缺 swap 欄 ⇒ 紅；任一格增長 ≥ 門檻之半 ⇒ 紅；非 C 格缺欄（沿用舊快取）⇒ 不紅；合規收據 ⇒ 綠。"""
    receipt = {"measurements": {
        "C_BTCUSDT_1h": {"category": "C", "status": "measured", "swap_growth_max_mb": 500.0, "swap_growth_threshold_mb": 4096.0},
        "A_BTCUSDT_1h": {"category": "A", "status": "measured", "swap_growth_max_mb": 10.0, "swap_growth_threshold_mb": 4096.0},
        "B_BTCUSDT_1h_4h": {"category": "B", "status": "stalled"}}}
    if mutant == "c_missing_fields":
        del receipt["measurements"]["C_BTCUSDT_1h"]["swap_growth_max_mb"]
    elif mutant == "growth_over_half":
        receipt["measurements"]["A_BTCUSDT_1h"]["swap_growth_max_mb"] = 2048.0
    elif mutant == "non_c_missing_ok":
        del receipt["measurements"]["A_BTCUSDT_1h"]["swap_growth_threshold_mb"]
    assert (swap_calibration_violations(receipt) != []) is (mutant in ("c_missing_fields", "growth_over_half"))


def test_estimate_gate_require_raises_in_three_cases(tmp_path: Path) -> None:
    """Task 0.4 ②：`_estimate_gate.require` 於收據缺、`reported_at` 缺、格不在清單三案各拋 `EstimateGateError`。"""
    assert gate_require_violations(GATE, tmp_path) == []


def test_estimate_gate_rejects_receipt_not_bound_to_current_criteria(tmp_path: Path) -> None:
    """審碼 b1 r1：估時收據之 `criteria_sha256` 缺或不等於現行判準檔 ⇒ `require` 拋 `EstimateGateError`。"""
    assert stale_criteria_violations(GATE, tmp_path) == []


def test_mutation_estimate_gate_without_criteria_binding(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutation：拿掉 `_estimate_gate` 之判準綁定 ⇒ 判準綁定兩案皆未拋錯。"""
    assert stale_criteria_violations(GATE, tmp_path / "real") == []
    monkeypatch.setattr(GATE, "_require_current_criteria", lambda receipt: None)
    violations = stale_criteria_violations(GATE, tmp_path / "mutant")
    assert len(violations) == 2 and all(v.endswith("未拋錯（判準綁定失效）") for v in violations), violations


def test_estimate_gate_called_before_generation_in_heavy_scripts() -> None:
    """Task 0.4 ③：凍結腳本與每個生成型探針於 `main` 頂層、任何生成呼叫之前呼叫 `require(<跑別>, …)`。"""
    assert gate_call_violations() == []


def _freeze_script_module() -> Any:
    spec = importlib.util.spec_from_file_location("numview_freeze_under_criteria_test", FREEZE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mutant", [None, "no_manifest", "group_file_deleted", "status_partial", "no_config_hash",
                                    "manifest_partial", "manifest_identity_mismatch", "stale_explicit_complete"])
def test_generate_cell_cache_hit_requires_complete_run(tmp_path: Path, mutant: Optional[str]) -> None:
    """批次快取命中（審碼 r21 CODEX-R21-P1-01、r22 CODEX-R22-P1-01）：sidecar complete＋config_hash、manifest 有效狀態
    complete 且身分（symbol／tf／config_hash）＝sidecar、宣告群組檔皆在 ⇒ 命中；缺 manifest／刪一群組檔／sidecar 狀態非
    complete／無 config_hash／manifest 狀態 partial／manifest 身分不符 ⇒ 不命中（呼叫端重生）。run 以正式
    `FeatureStorage.write_raw` 寫真實 kline 欄，manifest 之 run 狀態以正式 `update_manifest` 標 complete。"""
    import pandas as pd

    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering import ffstat_helpers as fsh
    from tests.feature_engineering import preprov_helpers as ph

    frz = _freeze_script_module()
    work = tmp_path / "work"
    k = fsh.kline_frame().iloc[-200:]
    raw_dir = FeatureStorage(str(work / "features")).write_raw(
        "BTCUSDT", "1h", "cfg_cache", {"ga": k[["open", "close"]].astype(float).reset_index(drop=True)},
        row_index=pd.DatetimeIndex(k.index))
    side = {"symbol": "BTCUSDT", "primary_tf": "1h", "config_hash": "cfg_cache", "status": "complete"}
    if mutant == "status_partial":
        side["status"] = "partial"
    elif mutant == "no_config_hash":
        side["config_hash"] = None
    (work / frz.SIDECAR).write_text(json.dumps(side), encoding="utf-8")
    run_dir = raw_dir.parent
    manifest_path = run_dir / "feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(run_status="partial" if mutant == "manifest_partial" else "complete",
                    complete=mutant not in ("manifest_partial", "stale_explicit_complete"), failure_reasons=[],
                    tf="4h" if mutant == "manifest_identity_mismatch" else "1h")
    # 審碼 r23 CODEX-R23-P1-01：writer 不完整窗口——根與 raw artifact 之 complete 標記為 False 而 explicit run_status 仍 complete
    manifest["artifacts"]["raw"]["complete"] = mutant != "stale_explicit_complete"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    if mutant == "group_file_deleted":
        ph.declared_group_files(run_dir, "raw")[0].unlink()
    elif mutant == "no_manifest":
        (run_dir / "feature_manifest.json").unlink()
    assert frz._cache_complete(work) is (mutant is None), mutant


@pytest.mark.parametrize("mutant", [None, "freeze_groups_doc_only", "g3_artifacts_policy", "helper_seam",
                                    "freeze_group_membership", "b_training_timeframes", "output_window",
                                    "hardware_tier"])
def test_result_identity_binds_seam_and_freeze_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                      mutant: Optional[str]) -> None:
    """凍結結果身分（審碼 r25 CODEX-R25-P1-01／GROK-R25-P1-01、r26 CODEX-R26-P1-01）：接縫檔（凍結腳本之 `G3_ARTIFACTS`
    政策、值指紋助手）、該格之凍結組成員、或生成輸入（格 B 之訓練週期〔估時收據 `b_membership`〕、輸出段）一改 ⇒ 身分不等
    （不沿用舊結果）；只改說明字面 `_doc` ⇒ 身分相等。接縫檔複製至暫存根、只改複本。"""
    frz = _freeze_script_module()
    for pattern in nh.SEAM_GLOBS:
        for path in REPO.glob(pattern):
            target = tmp_path / path.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    criteria = frz._criteria()
    monkeypatch.setattr(nh, "REPO", tmp_path)
    monkeypatch.setattr(nh, "code_state_sha256", lambda: "code")
    monkeypatch.setattr(nh, "cell_dataset_records", lambda cell: {"tf": "data"})
    monkeypatch.setattr(frz, "_criteria", lambda: criteria)
    cell = next(c for c in frz._cells() if c["kind"] == ("B" if mutant == "b_training_timeframes" else "C"))
    before = frz.result_identity(cell)
    mutated = copy.deepcopy(criteria)
    if mutant == "b_training_timeframes":
        training = frz._training_timeframes(cell)
        assert len(training) >= 2, training
        monkeypatch.setattr(frz, "_training_timeframes", lambda c: training[:1])
    elif mutant == "output_window":
        est = frz._estimator()
        window = est.cell_window
        monkeypatch.setattr(est, "cell_window", lambda c, crit: (window(c, crit)[0], "2000-01-01"))
    elif mutant == "hardware_tier":
        hardware = frz._hardware()
        monkeypatch.setattr(frz, "_hardware", lambda: {**hardware, "memory_tier": hardware["memory_tier"] + "_other"})
    if mutant == "freeze_groups_doc_only":
        mutated["cell_rules"]["freeze_groups"]["_doc"] = "說明字面改動"
    elif mutant == "freeze_group_membership":
        mutated["cell_rules"]["freeze_groups"]["G3"].remove(cell["id"])
    elif mutant == "g3_artifacts_policy":
        script = tmp_path / "scripts" / "numview_freeze_baseline.py"
        text = script.read_text(encoding="utf-8")
        policy = '"C": ("raw",)}'
        assert text.count(policy) == 1
        script.write_text(text.replace(policy, '"C": ("raw", "processed")}'), encoding="utf-8")
    elif mutant == "helper_seam":
        helper = tmp_path / "tests" / "feature_engineering" / "numview_helpers.py"
        helper.write_text(helper.read_text(encoding="utf-8") + "\n# 改動\n", encoding="utf-8")
    monkeypatch.setattr(frz, "_criteria", lambda: mutated)
    after = frz.result_identity(cell)
    assert (after == before) is (mutant in (None, "freeze_groups_doc_only")), (mutant, before, after)


@pytest.mark.parametrize("context", ["generation", "ic_page_arm", "ic_page_entry"])
def test_freeze_contexts_clear_ambient_ffact_selectors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                       context: str) -> None:
    """審碼 r27 CODEX-R27-P1-01、r28 CODEX-R28-P1-01：環境殘留之影響值變數（契約 `selectors` 例 `FFACT_L65_NATIVE_TF`、
    `FFACT_ROLLING_QUANTILE_KERNEL`；`ICFA_PHYSICAL_BYTES`、`QTS_RELATIVE_ONLY`、`NUMBA_NUM_THREADS`）於生成隔離
    （`_isolated`）、IC 頁臂環境（`_arm_env`）與公開 IC 頁入口（`ic_page_output` → `_ic_page_run`；只保留呼叫端之臂鍵）內一律
    清除，只剩明示環境；離開後原樣還原。"""
    frz = _freeze_script_module()
    ambient = {"FFACT_L65_NATIVE_TF": "0", "FFACT_ROLLING_QUANTILE_KERNEL": "legacy", "FFACT_USE_POLARS": "0",
               "ICFA_PHYSICAL_BYTES": "1024", "QTS_RELATIVE_ONLY": "1", "NUMBA_NUM_THREADS": "1"}
    for key, value in ambient.items():
        monkeypatch.setenv(key, value)
    if context == "generation":
        explicit = {"FFACT_USE_POLARS": "1"}
        with frz._isolated(tmp_path / "work", explicit):
            inside = {key: os.environ[key] for key in frz._cleared_env_keys()}
        assert {k: v for k, v in inside.items() if k in ambient or k in explicit} == explicit, inside
    elif context == "ic_page_arm":
        with frz._arm_env("polars", 10) as explicit:
            inside = {key: os.environ[key] for key in frz._cleared_env_keys()}
        assert inside == explicit, inside
    else:
        seen: Dict[str, str] = {}

        def capture(handle: Any, work: Path) -> Tuple[Any, Dict[str, Any], List[str]]:
            seen.update({key: os.environ[key] for key in frz._cleared_env_keys()})
            return None, {}, []

        monkeypatch.setattr(frz, "_ic_page_run_in_env", capture)
        frz.ic_page_output(None, tmp_path)
        assert seen == {"FFACT_USE_POLARS": "0"}, seen
    assert {key: os.environ.get(key) for key in ambient} == ambient


def _str_set(node: ast.AST) -> Optional[Set[str]]:
    """字串字面或字串字面之 tuple／list／set ⇒ 字串集合；其他 ⇒ None。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        out: Set[str] = set()
        for elt in node.elts:
            got = _str_set(elt)
            if got is None:
                return None
            out |= got
        return out
    return None


def _env_scan(sources: Mapping[str, str]) -> Tuple[Set[str], Set[str]]:
    """AST 盤點環境存取（審碼 r29 CODEX-R29-P1-01）：`os.environ`／`environ` 之 `get`／`setdefault`／`pop`／下標／`in`、
    `os.getenv`。鍵之解析：字串字面；本模組或類層級字串常數；迴圈／推導式遍歷之字面集合（tuple／list／dict 之鍵或值，含
    `.items()`／`.keys()`／`.values()`）；函式參數 ⇒ 全部呼叫點之該引數（遞迴同規則，呼叫點零個或任一不可解析 ⇒ 不可解析）。
    其他形式（整體迭代 `os.environ.items()`、`dict(os.environ)`、整份傳入子行程、動態名稱）一律記為不可解析之存取點
    `路徑::函式`。回（可解析之名稱集合, 不可解析之存取點集合）。`sources`＝{repo 相對路徑: 原始碼}。"""
    trees = {rel: ast.parse(text) for rel, text in sources.items()}
    parents_of = {rel: {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
                  for rel, tree in trees.items()}

    def chain(node: ast.AST, rel: str) -> List[ast.AST]:
        parents, out = parents_of[rel], []
        while node in parents:
            node = parents[node]
            out.append(node)
        return out[::-1]

    consts: Dict[Tuple[str, str], Set[str]] = {}
    attr_consts: Dict[str, Set[str]] = {}
    colls: Dict[str, Dict[str, Set[str]]] = {}
    calls: Dict[str, List[Tuple[ast.Call, str]]] = {}
    for rel, tree in trees.items():
        top = set(tree.body)
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            top |= set(cls.body)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
                if fn:
                    calls.setdefault(fn, []).append((node, rel))
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", None)
                if name is None:
                    continue
                value = node.value
                if isinstance(value, ast.Constant):
                    if node in top and isinstance(value.value, str):
                        consts.setdefault((rel, name), set()).add(value.value)
                        attr_consts.setdefault(name, set()).add(value.value)
                elif _str_set(value) is not None:
                    colls.setdefault(name, {}).setdefault("elts", set()).update(_str_set(value) or set())
                elif isinstance(value, ast.Dict):
                    keys = [_str_set(k) if k is not None else None for k in value.keys]
                    vals = [_str_set(v) for v in value.values]
                    if keys and all(k is not None for k in keys):
                        colls.setdefault(name, {}).setdefault("keys", set()).update(*keys)
                    if vals and all(v is not None for v in vals):
                        colls.setdefault(name, {}).setdefault("values", set()).update(*vals)

    def resolve(expr: ast.AST, scope: Sequence[ast.AST], rel: str, depth: int = 0) -> Optional[Set[str]]:
        if depth > 4:
            return None
        if isinstance(expr, ast.Constant):
            return _str_set(expr)
        if isinstance(expr, ast.Attribute):
            return set(attr_consts[expr.attr]) if expr.attr in attr_consts else None
        if not isinstance(expr, ast.Name):
            return None
        for node in reversed(scope):
            if isinstance(node, (ast.For, ast.AsyncFor)):
                generators = [(node.target, node.iter)]
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                generators = [(g.target, g.iter) for g in node.generators]
            else:
                continue
            for target, iterable in generators:
                parts = [target] if isinstance(target, ast.Name) else list(getattr(target, "elts", []))
                for index, part in enumerate(parts):
                    if not (isinstance(part, ast.Name) and part.id == expr.id):
                        continue
                    base, section = iterable, ("elts" if isinstance(target, ast.Name) else
                                               ("keys" if index == 0 else "values"))
                    if isinstance(iterable, ast.Call) and isinstance(iterable.func, ast.Attribute):
                        base = iterable.func.value
                        section = {"items": "keys" if index == 0 else "values", "keys": "keys",
                                   "values": "values"}.get(iterable.func.attr, section)
                    elif isinstance(target, ast.Name):
                        bname = iterable.id if isinstance(iterable, ast.Name) else getattr(iterable, "attr", "")
                        section = "elts" if "elts" in colls.get(bname, {}) else "keys"
                    bname = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
                    got = colls.get(bname or "", {}).get(section)
                    return set(got) if got else None
        for node in reversed(scope):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = [a.arg for a in node.args.args]
            if expr.id not in params:
                continue
            position, method = params.index(expr.id), bool(params) and params[0] in ("self", "cls")
            sites = calls.get(node.name, [])
            if not sites:
                return None
            out: Set[str] = set()
            for call, caller in sites:
                arg = next((kw.value for kw in call.keywords if kw.arg == expr.id), None)
                if arg is None:
                    i = position - (1 if method and isinstance(call.func, ast.Attribute) else 0)
                    arg = call.args[i] if 0 <= i < len(call.args) else None
                got = resolve(arg, chain(call, caller), caller, depth + 1) if arg is not None else None
                if got is None:
                    return None
                out |= got
            return out
        return set(consts[(rel, expr.id)]) if (rel, expr.id) in consts else None

    names: Set[str] = set()
    unresolved: Set[str] = set()
    for rel, tree in trees.items():
        parents = parents_of[rel]
        # 別名表（審碼 r30 CODEX-R30-P1-01）：本模組任一處之 `import os [as X]`、`from os import environ [as X]`、
        # `from os import getenv [as X]` 所綁定之名稱
        os_names, environ_names, getenv_names = {"os"}, {"environ"}, set()
        for imp in ast.walk(tree):
            if isinstance(imp, ast.Import):
                os_names |= {a.asname or a.name for a in imp.names if a.name == "os"}
            elif isinstance(imp, ast.ImportFrom) and imp.module == "os":
                environ_names |= {a.asname or a.name for a in imp.names if a.name == "environ"}
                getenv_names |= {a.asname or a.name for a in imp.names if a.name == "getenv"}
        for node in ast.walk(tree):
            key: Optional[ast.AST] = None
            is_env = ((isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name)
                       and node.value.id in os_names) or (isinstance(node, ast.Name) and node.id in environ_names))
            is_getenv = isinstance(node, ast.Call) and (
                (isinstance(node.func, ast.Attribute) and node.func.attr == "getenv" and isinstance(node.func.value, ast.Name)
                 and node.func.value.id in os_names) or (isinstance(node.func, ast.Name) and node.func.id in getenv_names))
            if is_env:
                parent = parents.get(node)
                if isinstance(parent, ast.Attribute) and parent.attr in ("get", "setdefault", "pop"):
                    call = parents.get(parent)
                    key = call.args[0] if isinstance(call, ast.Call) and call.args else None
                elif isinstance(parent, ast.Subscript):
                    key = parent.slice
                elif isinstance(parent, ast.Compare) and parent.comparators and parent.comparators[0] is node:
                    key = parent.left
            elif not is_getenv:
                continue
            else:
                key = node.args[0] if node.args else None
            got = resolve(key, chain(node, rel), rel) if key is not None else None
            if got is None:
                func = next((a.name for a in reversed(chain(node, rel))
                             if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef))), "<module>")
                unresolved.add(f"{rel}::{func}")
            else:
                names |= got
    return names, unresolved


def _product_sources() -> Dict[str, str]:
    return {str(p.relative_to(REPO)): p.read_text(encoding="utf-8", errors="replace")
            for root in ("momentum", "api") for p in sorted((REPO / root).rglob("*.py"))}


def test_freeze_cleared_env_covers_product_env_reads() -> None:
    """審碼 r28 CODEX-R28-P1-01、r29 CODEX-R29-P1-01：產品碼（momentum／api）之每個環境存取，其可解析之名稱須屬凍結腳本
    之清除類（`CLEARED_ENV_PREFIXES`／`CLEARED_ENV_NAMES`）或具名不清除（`ENV_NOT_CLEARED`，附理由）；不可解析之存取點須恰為
    `ENV_UNRESOLVED_SITES`（附理由；不多不少）。新增未分類名稱或未登錄之動態／整體存取 ⇒ 紅。"""
    frz = _freeze_script_module()
    names, unresolved = _env_scan(_product_sources())
    assert {"ICFA_PHYSICAL_BYTES", "QTS_RELATIVE_ONLY", "FF_CORRECTNESS_MODE", "PYTEST_CURRENT_TEST",
            "FFACT_LAYER4_CHUNK_SIZE", "POLARS_MAX_THREADS"} <= names, "掃描未涵蓋已知讀取（掃描失效）"
    unclassified = sorted(n for n in names if not (n.startswith(frz.CLEARED_ENV_PREFIXES) or n in frz.CLEARED_ENV_NAMES
                                                   or n in frz.ENV_NOT_CLEARED))
    assert unclassified == [], unclassified
    assert sorted(unresolved) == sorted(frz.ENV_UNRESOLVED_SITES), (sorted(unresolved), sorted(frz.ENV_UNRESOLVED_SITES))
    assert all(isinstance(v, str) and v for v in {**frz.ENV_NOT_CLEARED, **frz.ENV_UNRESOLVED_SITES}.values())


@pytest.mark.parametrize("mutant", ["dynamic_getenv", "bulk_items", "bulk_dict", "literal_unclassified", "alias_os",
                                    "alias_environ", "alias_getenv"])
def test_mutation_env_scan_reports_new_access(mutant: str) -> None:
    """審碼 r29 CODEX-R29-P1-01 、r30 CODEX-R30-P1-01 之 MUTATION：單一注入模組（自足）含動態名稱 `os.getenv(NAME)`、整體迭代
    `os.environ.items()`、`dict(os.environ)`、或未分類之字面讀取 ⇒ 掃描報出（不可解析存取點或未分類名稱）。"""
    frz = _freeze_script_module()
    body = {"dynamic_getenv": "import os\ndef f(n):\n    return os.getenv(n)\ndef g():\n    return f(compute())\n",
            "bulk_items": "import os\ndef f():\n    return list(os.environ.items())\n",
            "bulk_dict": "import os\ndef f():\n    return dict(os.environ)\n",
            "literal_unclassified": "import os\ndef f():\n    return os.environ.get('NUMVIEW_SCAN_PROBE_X')\n",
            "alias_os": "import os as _os\ndef f():\n    return _os.environ.get('NUMVIEW_SCAN_PROBE_X')\n",
            "alias_environ": "from os import environ as _env\ndef f():\n    return _env['NUMVIEW_SCAN_PROBE_X']\n",
            "alias_getenv": "from os import getenv as _ge\ndef f():\n    return _ge('NUMVIEW_SCAN_PROBE_X')\n"}[mutant]
    names, unresolved = _env_scan({"momentum/_numview_scan_probe.py": body})  # 注入模組自足（函式與呼叫點皆在其內）
    unclassified = {n for n in names if not (n.startswith(frz.CLEARED_ENV_PREFIXES) or n in frz.CLEARED_ENV_NAMES
                                             or n in frz.ENV_NOT_CLEARED)}
    assert (unresolved - set(frz.ENV_UNRESOLVED_SITES)) or unclassified, mutant


def test_estimate_gate_called_first_in_generate_cell() -> None:
    """Task 0.4 改法（R15-A）：Phase 2–4 驗收重產之唯一生成接縫 `generate_cell`（與經之之 `freeze_cell`）以必填
    `run_kind` 接收跑別，首個陳述式級呼叫為 `require(run_kind, …)`、先於任何生成呼叫。"""
    assert cell_gate_violations() == []


def test_estimate_regen_run_kinds_registered() -> None:
    """Task 0.4 驗證①（R15-A）：`estimate.RUN_KINDS` 含 Phase 2–4 驗收重產之全部跑別（`REGEN_REQUIREMENTS`）。"""
    assert set(REGEN_REQUIREMENTS) <= set(ESTIMATOR.RUN_KINDS), sorted(set(REGEN_REQUIREMENTS) - set(ESTIMATOR.RUN_KINDS))


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_05_criteria_change_only_via_v2_before_receipts() -> None:
    """邊界①（SPEC Task 0.3）：判準須改 ⇒ 只准於任何收據產出前以新檔名 `preregistered_criteria_v2.json` 取代並刪舊檔。
    斷言：兩檔名恰一存在；v1 現行 ⇒ v2 無任何歷史；v2 現行 ⇒ v1 不在 HEAD、v2 恰一提交，且 v1／v2 每筆提交皆早於每份收據之
    首次提交（收據之判定範圍同③：全部 *-numview-*.json）。現行判準為 v3 起（vN，N≥3）⇒ 本案之 v1→v2 規則已無對象，委由
    `test_boundary_05_vn_replacement_rule`（vN→vN+1：舊版檔不在 HEAD、現行版恰一提交、早於量測收據）判定。"""
    if nh.criteria_version() > 2:
        return
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


def test_mutation_estimate_generate_cell_without_gate_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（R15-A）：`generate_cell` 刪去 `require` 敘述（以 `_read_text` 接縫餵入 AST 移除後之原始碼）⇒ 前置閘檢查翻紅。"""
    assert cell_gate_violations() == []
    original = _read_text

    def stripped(path: Path) -> str:
        text = original(path)
        if Path(path) != FREEZE_SCRIPT:
            return text
        return ast.unparse(ast.fix_missing_locations(_DropRequire().visit(ast.parse(text))))

    monkeypatch.setattr(sys.modules[__name__], "_read_text", stripped)
    violations = cell_gate_violations()
    assert any("generate_cell 之首個陳述式級呼叫非" in v for v in violations), violations


@pytest.mark.parametrize("kind", sorted(REGEN_REQUIREMENTS))
def test_mutation_estimate_receipt_missing_regen_kind(kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（R15-A）：估時收據缺任一 Phase 2–4 驗收重產跑別 ⇒ ①翻紅（總估時不得漏列驗收重產）。"""
    receipt = _load_receipt(_estimate_receipt_path())
    kline = _kline_index()
    assert estimate_receipt_violations(receipt, kline) == []
    mutated = copy.deepcopy(receipt)
    mutated["run_kinds"].pop(kind)
    monkeypatch.setattr(sys.modules[__name__], "_load_receipt", lambda _path: copy.deepcopy(mutated))
    violations = estimate_receipt_violations(_load_receipt(_estimate_receipt_path()), kline)
    assert f"run_kinds 缺跑別 {kind}" in violations, violations


def test_mutation_estimate_require_log_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutation：`_estimate_gate.require` 改為只 log 不拋 ⇒ ②紅。"""
    assert gate_require_violations(GATE, tmp_path / "real") == []
    logged: List[Tuple[str, Tuple[str, ...]]] = []
    monkeypatch.setattr(GATE, "require",
                        lambda run_kind, cells, *, receipts_dir=None: logged.append((run_kind, tuple(cells))))
    violations = gate_require_violations(GATE, tmp_path / "mutant")
    assert len(violations) == 3 and all(v.endswith("未拋錯（前置閘失效）") for v in violations), violations
    assert len(logged) == 4


# ---------------------------------------------------------------------------------------------- 判準 v2：前史不足之權威判定（追加）
#
# 判準檔 v2 `cell_rules.insufficient_history`（權威＝生成之完整度：run_status＝partial 且 failure_reasons 非空、每條皆合
# `reason_pattern` ⇒ blocked〔history〕；其餘非 complete ⇒ failed）與 `cell_rules.b_membership`（格 B 訓練週期排除格 A
# 判前史不足之週期，主週期不足或剩不足兩週期 ⇒ blocked）。受測＝`estimate.classify_run_completeness`／`b_membership`／
# `build_receipt`、`_estimate_gate.resolve_criteria_path`。manifest 案為完整度欄位之閘邏輯單元（非特徵資料）；事件名取自
# 判準檔 `known_events`，不另寫字面。

#: 判準 v2 新增之前史判定段鍵（結構，非值集）
HISTORY_RULE_KEYS = ("authoritative", "reason_pattern", "known_events", "prefilter", "allow_partial")


def _history_rule() -> Mapping[str, Any]:
    return _load_criteria()["cell_rules"]["insufficient_history"]


def history_classification_violations(estimator: ModuleType) -> List[str]:
    """`classify_run_completeness` 對下列案之判定：complete ⇒ complete；partial 而原因全為前史事件 ⇒ blocked（history、
    事件欄數加總）；partial 而混入任一其他原因、partial 而原因為空、非 partial 之未完成 ⇒ failed（fail-closed）。"""
    criteria = _load_criteria()
    events = sorted(criteria["cell_rules"]["insufficient_history"]["known_events"])
    history_only = [f"{events[0]}:7", f"{events[-1]}:5", f"{events[0]}:2"]
    cases: List[Tuple[str, Dict[str, Any], str]] = [
        ("complete", {"run_status": "complete", "failure_reasons": []}, "complete"),
        ("history_only", {"run_status": "partial", "failure_reasons": history_only}, "blocked"),
        ("mixed_reason", {"run_status": "partial", "failure_reasons": [history_only[0], "L6.5:preprocessing_failed"]},
         "failed"),
        ("quality_ratio", {"run_status": "partial", "failure_reasons": [history_only[0], "nan_ratio=1>max_nan_ratio=0"]},
         "failed"),
        ("empty_reasons", {"run_status": "partial", "failure_reasons": []}, "failed"),
        ("failed_status", {"run_status": "failed", "failure_reasons": history_only}, "failed"),
        ("unknown_status", {"failure_reasons": history_only}, "failed"),
    ]
    out: List[str] = []
    for label, manifest, want in cases:
        got = estimator.classify_run_completeness(manifest, criteria)
        if got.get("status") != want:
            out.append(f"{label}：判定 {got.get('status')!r} ≠ {want!r}")
        if want == "blocked":
            expected = {events[0]: 9, events[-1]: 5} if events[0] != events[-1] else {events[0]: 14}
            if got.get("blocked_by") != "history" or got.get("reason_counts") != expected:
                out.append(f"{label}：blocked_by／reason_counts {got.get('blocked_by')!r}／{got.get('reason_counts')!r}"
                           f" ≠ history／{expected}")
    return out


def _full_candidate_b_descriptor() -> Dict[str, Any]:
    """主檔第一個 symbol 之全部週期（依長度升冪）之格 B 候選描述子（成員規則之單元輸入）。無斷言。"""
    symbol, tfs = next(iter(_kline_index().items()))
    ordered = sorted(tfs, key=ESTIMATOR.tf_seconds)
    return {"id": ESTIMATOR.cell_id("B", symbol, ordered), "kind": "B", "symbol": symbol, "timeframes": ordered}


def _closed_symbol_timeframes(cells: Sequence[Mapping[str, Any]]) -> List[Tuple[str, List[str]]]:
    """格描述子 → (symbol, timeframes)。無斷言。"""
    return [(str(c["symbol"]), [str(t) for t in c["timeframes"]]) for c in cells]


def _closed_ids(kind: str) -> Set[str]:
    """判準封閉清單中某格類之格 id。無斷言。"""
    return {str(c["id"]) for c in (nh.criteria_cell_list() or []) if c["kind"] == kind}


def _closed_timeframe(cell_id_: str) -> str:
    """判準封閉清單中某格之主週期。無斷言。"""
    return next(str(c["timeframes"][0]) for c in (nh.criteria_cell_list() or []) if c["id"] == cell_id_)


def _b_descriptor() -> Mapping[str, Any]:
    cells = [_full_candidate_b_descriptor()]  # 判準 v3 封閉清單之格 B 只兩週期 ⇒ 成員規則單元改用主檔全週期之候選描述子
    assert cells and len(cells[0]["timeframes"]) >= 3, "前提：真實 kline 之格 B 須具 ≥3 候選週期（本案需排除一週期後仍 ≥2）"
    return cells[0]


def b_membership_violations(estimator: ModuleType) -> List[str]:
    """格 B 訓練週期：非主週期之格 A 判前史不足 ⇒ 排除、其餘照列且主週期起首；主週期不足 ⇒ blocked；剩不足 min_timeframes
    ⇒ blocked；任一週期判定未知 ⇒ 拋錯（不猜測）。"""
    criteria = _load_criteria()
    cell = _b_descriptor()
    tfs = list(cell["timeframes"])
    out: List[str] = []
    one_out = estimator.b_membership(cell, {tf: tf == tfs[-1] for tf in tfs}, criteria)
    if one_out.get("status") != "ok" or one_out.get("training_timeframes") != tfs[:-1]:
        out.append(f"排除最長週期：{one_out}")
    main_out = estimator.b_membership(cell, {tf: tf == tfs[0] for tf in tfs}, criteria)
    if main_out.get("status") != "blocked":
        out.append(f"主週期不足未 blocked：{main_out}")
    few = estimator.b_membership(cell, {tf: tf != tfs[0] for tf in tfs}, criteria)
    if few.get("status") != "blocked":
        out.append(f"只剩主週期未 blocked：{few}")
    try:
        estimator.b_membership(cell, {tf: (None if tf == tfs[1] else False) for tf in tfs}, criteria)
    except estimator.EstimateError:
        pass
    else:
        out.append("判定未知之週期未拋錯")
    return out


def test_estimate_criteria_history_rule_registered() -> None:
    """判準 v2：前史判定以生成完整度為權威（`authoritative=run_completeness`）、不以 allow_partial 讀取、不降門檻；
    `reason_pattern` 可編譯且涵蓋 `known_events` 全部事件而不涵蓋其他已知降級原因；`b_membership` 至少兩週期。"""
    rule = _history_rule()
    assert all(k in rule for k in HISTORY_RULE_KEYS), sorted(set(HISTORY_RULE_KEYS) - set(rule))
    assert rule["authoritative"] == "run_completeness" and rule["allow_partial"] is False
    assert rule["lower_threshold_allowed"] is False
    pattern = re.compile(rule["reason_pattern"])
    assert rule["known_events"] and all(pattern.fullmatch(f"{event}:3") for event in rule["known_events"])
    assert not any(pattern.fullmatch(r) for r in ("L6.5:preprocessing_failed", "timeframe:1h", "nan_ratio=1>max_nan_ratio=0"))
    assert int(_load_criteria()["cell_rules"]["b_membership"]["min_timeframes"]) >= 2


def test_estimate_classify_history_only_partial_as_blocked() -> None:
    """`classify_run_completeness`：只因前史事件而 partial ⇒ blocked（history），其餘未完成 ⇒ failed。"""
    assert history_classification_violations(ESTIMATOR) == []


def test_mutation_estimate_classify_any_partial_as_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：判定改為「任何 partial 皆 blocked」（混入他種原因亦放行）⇒ 檢查翻紅（mixed／quality／empty 三案）。"""
    assert history_classification_violations(ESTIMATOR) == []
    real = ESTIMATOR.classify_run_completeness

    def lax(manifest: Mapping[str, Any], criteria: Mapping[str, Any]) -> Dict[str, Any]:
        if manifest.get("run_status") == "partial":
            return {"status": "blocked", "blocked_by": "history", "reason_counts": {}}
        return real(manifest, criteria)

    monkeypatch.setattr(ESTIMATOR, "classify_run_completeness", lax)
    labels = {v.split("：", 1)[0] for v in history_classification_violations(ESTIMATOR)}
    assert {"mixed_reason", "quality_ratio", "empty_reasons"} <= labels, labels


def test_estimate_b_membership_excludes_history_blocked_timeframes() -> None:
    """`b_membership`（判準 v2 `cell_rules.b_membership`）於真實 kline 之格 B 描述子。"""
    assert b_membership_violations(ESTIMATOR) == []


def test_mutation_estimate_b_membership_keeps_blocked_timeframe(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：格 B 不排除前史不足週期（訓練週期恆為全部候選）⇒ 檢查翻紅。"""
    assert b_membership_violations(ESTIMATOR) == []
    monkeypatch.setattr(ESTIMATOR, "b_membership",
                        lambda cell, status, criteria: {"status": "ok", "training_timeframes": list(cell["timeframes"])})
    assert b_membership_violations(ESTIMATOR) != []


def test_estimate_gate_resolves_exactly_one_criteria_file(tmp_path: Path) -> None:
    """`_estimate_gate.resolve_criteria_path`：v1／v2 恰一存在 ⇒ 回該檔；皆無或皆在 ⇒ 拋 `EstimateGateError`（不可判定）。
    現行判準（`_criteria_path()`）＝閘之解析結果。"""
    assert Path(GATE.resolve_criteria_path()).resolve() == _criteria_path().resolve()
    for present in ((), (CRITERIA_V1.name,), (CRITERIA_V2.name,), (CRITERIA_V1.name, CRITERIA_V2.name)):
        d = tmp_path / ("_".join(present) or "none")
        d.mkdir()
        for name in present:
            (d / name).write_text("{}", encoding="utf-8")
        if len(present) == 1:
            assert GATE.resolve_criteria_path(d) == d / present[0]
        else:
            with pytest.raises(GATE.EstimateGateError):
                GATE.resolve_criteria_path(d)


def test_estimate_receipt_lists_history_blocked_cells_outside_extrapolation() -> None:
    """估時收據之組裝（`build_receipt`，閘邏輯單元；實測秒數為結構佔位）：某週期格 A 單格實測 blocked（history）⇒ 該週期
    根數不多於受測格之全部格 A 列於 `history_blocked`（history、附事件欄數與根數；`blocked` 只放硬體）、不在任何跑別之 per_cell_seconds、其嘗試秒數只計入
    freeze_baseline；格 B 訓練週期排除該週期；收據仍通過估時收據檢查（格清單完整）。"""
    criteria = _load_criteria()
    kline = _kline_index()
    inventory = ESTIMATOR.kline_inventory(nh.KLINE_PATH)
    cells = ESTIMATOR.enumerate_cells(nh.KLINE_PATH)
    src_inv = ESTIMATOR.source_inventory(inventory, criteria)  # 根數取各週期之來源檔（判準 kline_source）
    tfs = sorted({tf for t in inventory.values() for tf in t}, key=ESTIMATOR.tf_seconds)
    blocked_tf = tfs[-1]
    probe_symbol = next(s for s, t in _closed_symbol_timeframes(cells["A"]) if blocked_tf in t)
    measurements = _synthetic_measurements(inventory, cells)
    event = sorted(criteria["cell_rules"]["insufficient_history"]["known_events"])[0]
    output_bars = int(criteria["cell_definitions"]["A"]["output_bars"])
    # 受測格之定案所需前史設為「恰使根數不多於受測格者不足」（靜態判定之邊界；判準 window_rule）
    measurements[ESTIMATOR.cell_id("A", probe_symbol, [blocked_tf])] = {"target": f"A:{blocked_tf}", "category": "A", "status": "blocked",
                                       "blocked_by": "history", "symbol": probe_symbol,
                                       "cell_id": ESTIMATOR.cell_id("A", probe_symbol, [blocked_tf]),
                                       "source_path": str(ESTIMATOR.kline_source(blocked_tf, criteria)),
                                       "bar_counts": {blocked_tf: src_inv[probe_symbol][blocked_tf]},
                                       "pre_history": {"required_pre_history_bars":
                                                       src_inv[probe_symbol][blocked_tf] - output_bars + 1},
                                       "reason_counts": {event: 1}, "attempt_seconds": 2.0}
    body = ESTIMATOR.build_receipt(cells, inventory, criteria, measurements,
                                   nv.load_contract()["post_ic_arm_values"]["values"])
    receipt = json.loads(json.dumps({"reported_at": "2026-10-22T00:00:00+08:00", "cells": cells, **body}))
    expected = {c["id"] for c in cells["A"] if c["timeframes"] == [blocked_tf]
                and src_inv[c["symbol"]][blocked_tf] <= src_inv[probe_symbol][blocked_tf]}
    listed = {b["cell"] for b in receipt["history_blocked"] if b.get("blocked_by") == "history"}
    assert not any(b.get("blocked_by") == "history" for b in receipt["blocked"]), "前史 blocked 不得列入硬體 blocked"
    assert expected and expected <= listed, sorted(expected - listed)
    assert all(b.get("reason_counts") for b in receipt["history_blocked"] if b["cell"] in expected)
    for name, node in receipt["run_kinds"].items():
        assert not (expected & set(node["per_cell_seconds"])), name
        assert set(node.get("blocked_attempt_seconds") or {}) <= (expected if name == "freeze_baseline" else set()), name
    assert set(receipt["run_kinds"]["freeze_baseline"]["blocked_attempt_seconds"]) == expected
    assert all(blocked_tf not in m["training_timeframes"] for m in receipt["b_membership"].values()
               if m["status"] == "ok")
    assert estimate_receipt_violations(receipt, kline) == []


# ---------------------------------------------------------------------------------------------- 審碼 b1 r3（追加）：格 C 前史
# blocked 之路由（CODEX-R3-P1-01）、所需前史以定案預熱深度計（CODEX-R3-P1-02）。皆為收據組裝與純函式之閘邏輯單元（不生成）。

def _synthetic_measurements(inventory: Mapping[str, Mapping[str, int]], cells: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """全部實測目標之結構佔位（秒數非量測值；只驗組裝邏輯）：受測格帶 cell_id、來源檔、來源根數，所需前史 0（他格靜態判定
    皆足夠）。"""
    criteria = _load_criteria()
    src_inv = ESTIMATOR.source_inventory(inventory, criteria)
    out: Dict[str, Dict[str, Any]] = {}
    for target in ESTIMATOR.measurement_targets(cells, inventory, None, criteria):
        record: Dict[str, Any] = {"target": target["target"], "category": target["category"], "status": "measured",
                                  "seconds": 1.0, "peak_rss_bytes": 1}
        cell = target.get("cell")
        if cell is not None:
            record["arm_seconds"] = {arm: 1.0 for arm in nv.load_contract()["post_ic_arm_values"]["values"]}
            record["branch_seconds"] = {b: 1.0 for b in _icpostleak_registry_branches()}
            record["training_timeframes"] = list(cell["timeframes"])
        if cell is not None and target["category"] in ("A", "C"):
            tf = cell["timeframes"][0]
            record.update(cell_id=cell["id"], symbol=cell["symbol"],
                          source_path=str(ESTIMATOR.kline_source(tf, criteria)),
                          bar_counts={tf: src_inv[cell["symbol"]][tf]},
                          pre_history={"required_pre_history_bars": 0,
                                       "ingest_floor": ESTIMATOR.cell_window(cell, criteria)[0]})
        if target["category"] in ("A", "B"):
            record["arm_seconds"] = {arm: 1.0 for arm in nv.load_contract()["post_ic_arm_values"]["values"]}
        out[target["target"]] = record
    return out


def cell_c_history_violations(estimator: ModuleType) -> List[str]:
    """某週期格 C 單格實測 blocked（blocked_by=history）⇒ 實測結果可接受（`measurement_accepted`）；該週期根數不多於受測格之
    全部格 C 列於 `history_blocked`、不在硬體 `blocked`、不在任何 per_cell_seconds；其嘗試秒數只計入 precision_chain；
    `cell_c_baseline` 該週期記為實測（history_blocked）；收據通過估時收據檢查與邊界 07 之格 C 阻擋檢查。"""
    criteria = _load_criteria()
    inventory = estimator.kline_inventory(nh.KLINE_PATH)
    cells = estimator.enumerate_cells(nh.KLINE_PATH)
    measurements = _synthetic_measurements(inventory, cells)
    c_keys = sorted(k for k in measurements if k in _closed_ids("C"))
    assert c_keys, "前提：須有實測之格 C 目標"
    key = c_keys[0]
    tf = _closed_timeframe(key)
    probe_symbol = next(c["symbol"] for c in cells["C"] if c["timeframes"] == [tf])
    event = sorted(criteria["cell_rules"]["insufficient_history"]["known_events"])[0]
    src_inv = estimator.source_inventory(inventory, criteria)
    output_bars = int(criteria["cell_definitions"]["C"]["output_bars"])
    measurements[key] = {"target": key, "category": "C", "status": "blocked", "blocked_by": "history",
                         "symbol": probe_symbol, "cell_id": estimator.cell_id("C", probe_symbol, [tf]),
                         "source_path": str(estimator.kline_source(tf, criteria)),
                         "bar_counts": {tf: src_inv[probe_symbol][tf]},
                         "pre_history": {"required_pre_history_bars": src_inv[probe_symbol][tf] - output_bars + 1},
                         "reason_counts": {event: 1}, "attempt_seconds": 3.0, "peak_rss_bytes": 7}
    out: List[str] = []
    if not estimator.measurement_accepted(measurements[key]):
        out.append("measurement_accepted 拒收格 C 之前史 blocked")
        return out
    body = estimator.build_receipt(cells, inventory, criteria, measurements,
                                   nv.load_contract()["post_ic_arm_values"]["values"])
    receipt = json.loads(json.dumps({"reported_at": "2026-10-22T00:00:00+08:00", "cells": cells, **body}))
    expected = {c["id"] for c in cells["C"] if c["timeframes"] == [tf]
                and src_inv[c["symbol"]][tf] <= src_inv[probe_symbol][tf]}
    hist = {b["cell"] for b in receipt.get("history_blocked") or [] if b.get("blocked_by") == "history"}
    if not expected <= hist:
        out.append(f"history_blocked 缺格 C {sorted(expected - hist)[:3]}")
    if expected & {b.get("cell") for b in receipt.get("blocked") or []}:
        out.append("前史 blocked 之格 C 誤入硬體 blocked")
    for name, node in receipt["run_kinds"].items():
        if expected & set(node["per_cell_seconds"]):
            out.append(f"{name}：前史 blocked 之格 C 入外推")
    if set((receipt["run_kinds"]["freeze_baseline"].get("blocked_attempt_seconds") or {})) != expected:
        out.append("freeze_baseline 之嘗試秒數未涵蓋前史 blocked 之格 C（判準 v3：前史 blocked 之格於凍結生成至判定）")
    if any(node.get("blocked_attempt_seconds") for name, node in receipt["run_kinds"].items() if name != "freeze_baseline"):
        out.append("嘗試秒數誤計入凍結以外之跑別")
    base = receipt["cell_c_baseline"].get(tf) or {}
    if base.get("blocked_by") == "hardware" or base.get("history_blocked") is not True:
        out.append(f"cell_c_baseline.{tf} 未依 blocked_by 走前史路徑：{base}")
    out += [f"估時收據檢查：{v}" for v in estimate_receipt_violations(receipt, _kline_index())]
    out += [f"格 C 阻擋檢查：{v}" for v in cell_c_blocked_violations(receipt)]
    return out


def test_estimate_cell_c_history_blocked_routed_by_blocked_by() -> None:
    """審碼 b1 r3 CODEX-R3-P1-01：格 C 之前史 blocked 依 `blocked_by` 走前史路徑（非硬體路徑）。"""
    assert cell_c_history_violations(ESTIMATOR) == []


def test_mutation_estimate_cell_c_history_rejected_as_hardware_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：`measurement_accepted` 回到「格 C 只接受硬體 blocked」⇒ 檢查翻紅。"""
    assert cell_c_history_violations(ESTIMATOR) == []

    def legacy(m: Mapping[str, Any]) -> bool:
        if m.get("status") == "measured":
            return True
        if m.get("category") == "C" and m.get("status") in ("blocked", "killed"):
            return m.get("blocked_by", "hardware") == "hardware"
        return m.get("category") in ("A", "B") and m.get("status") == "blocked" and m.get("blocked_by") == "history"

    monkeypatch.setattr(ESTIMATOR, "measurement_accepted", legacy)
    assert "measurement_accepted 拒收格 C 之前史 blocked" in cell_c_history_violations(ESTIMATOR)


def final_warmup_violations(estimator: ModuleType) -> List[str]:
    """所需前史以定案預熱深度計（加倍規則；判準 v2 window_rule）：定案深度取 metadata `output_window.max_warmup_bars`，
    其次加倍探測末輪；給定定案深度（模擬一次加倍＝2×D₀）⇒ required＝定案＋N_cal、basis＝final、clipped／ingest_floor 依之；
    未給 ⇒ 以 D₀ 計並標 initial_d0_lower_bound。以真實 kline 之格 C（可得前史介於 D₀ 與 2×D₀ 間者）驗 clipped 翻轉。"""
    out: List[str] = []
    if estimator.final_warmup_bars({"max_warmup_bars": 7}, [{"depth": 3}]) != 7:
        out.append("final_warmup_bars 未優先取 metadata")
    if estimator.final_warmup_bars(None, [{"depth": 3}, {"depth": 6}]) != 6:
        out.append("final_warmup_bars 未取探測末輪")
    if estimator.final_warmup_bars(None, []) is not None:
        out.append("final_warmup_bars 無來源時須為 None")
    from momentum.factories import create_feature_factory

    criteria = _load_criteria()
    symbol, tfs = next(iter(_kline_index().items()))  # 加倍案之格 C 描述子：真實主檔第一個 symbol 之各週期（不限封閉清單）
    candidates = [{"id": estimator.cell_id("C", symbol, [tf]), "kind": "C", "symbol": symbol, "timeframes": [tf]} for tf in tfs]
    factory = create_feature_factory(cache_dir=str(nh.KLINE_PATH.parent), validate_continuity=False)
    chosen = None
    for cell in candidates:  # 選格只依初值與可得前史之算術（不依受測之加倍處理）
        config = factory._resolve_config(estimator.cell_payload(cell, criteria))
        initial = estimator.pre_history_requirement(cell, criteria, config)
        doubled_need = 2 * initial["d0_bars"] + initial["calibration_bars_primary"]
        if not initial["clipped"] and initial["available_pre_history_bars"] < doubled_need:
            chosen = (cell, config, initial)
            break
    if chosen is None:
        return out + ["前提：真實 kline 無「D₀ 不截斷而 2×D₀ 截斷」之格 C（無從構造加倍案）"]
    cell, config, initial = chosen
    doubled = estimator.pre_history_requirement(cell, criteria, config, final_warmup=2 * initial["d0_bars"])
    if initial["warmup_basis"] != "initial_d0_lower_bound" or initial["final_warmup_bars"] is not None:
        out.append(f"未給定案深度而 basis／final 非下界：{initial}")
    if doubled["warmup_basis"] != "final" or doubled["final_warmup_bars"] != 2 * initial["d0_bars"]:
        out.append(f"定案深度未記錄：{doubled}")
    want = 2 * initial["d0_bars"] + initial["calibration_bars_primary"]
    if doubled["required_pre_history_bars"] != want:
        out.append(f"required {doubled['required_pre_history_bars']} ≠ 定案＋N_cal {want}")
    if doubled["clipped"] is not True or doubled["ingest_floor"] > initial["ingest_floor"]:
        out.append("加倍後 clipped／ingest_floor 未隨定案深度更新")
    return out


def test_estimate_pre_history_uses_final_warmup_depth() -> None:
    """審碼 b1 r3 CODEX-R3-P1-02：所需前史以生成定案之預熱深度計，未實測者標 D₀ 下界。"""
    assert final_warmup_violations(ESTIMATOR) == []


def test_mutation_estimate_pre_history_ignores_doubling(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：所需前史忽略定案深度（恆以 D₀ 計）⇒ 加倍案翻紅。"""
    assert final_warmup_violations(ESTIMATOR) == []
    real = ESTIMATOR.pre_history_requirement

    def d0_only(cell, criteria, resolved_config, kline_path=None, training_timeframes=None, final_warmup=None):  # type: ignore[no-untyped-def]
        return real(cell, criteria, resolved_config, kline_path, training_timeframes)

    monkeypatch.setattr(ESTIMATOR, "pre_history_requirement", d0_only)
    violations = final_warmup_violations(ESTIMATOR)
    assert any(v.startswith(("定案深度未記錄", "required", "加倍後")) for v in violations), violations


# ---------------------------------------------------------------------------------------------- 判準 v2 kline_source（追加）：
# 依週期之 K 線來源（使用者 2026-10-22：12h 讀長歷史檔、主檔不動）。只讀 h5 鍵與資料集（不生成）。

def _independent_dataset_sha256(path: Path, symbol: str, tf: str) -> str:
    """測試端獨立重算（判準 kline_source.dataset_sha256 之定義）：dtype 描述＋C 連續位元組之 sha256。"""
    with h5py.File(str(path), "r") as handle:
        arr = handle[symbol][tf]["data"][()]
    digest = hashlib.sha256()
    digest.update(str(arr.dtype.descr).encode("utf-8"))
    digest.update(np.ascontiguousarray(arr).tobytes())
    return digest.hexdigest()


def kline_source_violations(estimator: ModuleType) -> List[str]:
    """判準 `cell_rules.kline_source`：①主檔列舉之每個週期皆有封閉對映；未列之週期拒收。②單週期格之來源＝其週期之對映
    檔；多週期格 B 之來源＝其主週期之來源（單一 cache_dir）。③輸出段之終點＝來源序列之末根（依來源之 series_end）。④逐格
    資料集紀錄之 sha256 等於測試端獨立重算、根數等於來源檔該資料集長度。全部以判準檔對映為準（不寫死檔名）。"""
    criteria = _load_criteria()
    rule = criteria["cell_rules"]["kline_source"]
    mapping = rule["by_timeframe"]
    out: List[str] = []
    kline = _kline_index()
    missing = sorted({tf for tfs in kline.values() for tf in tfs} - set(mapping))
    if missing:
        out.append(f"kline_source 缺週期 {missing}")
    try:
        estimator.kline_source("numview_unlisted_tf", criteria)
        out.append("未列之週期未拒收")
    except estimator.EstimateError:
        pass
    cells = estimator.enumerate_cells(nh.KLINE_PATH)
    for kind in ("A", "C"):
        for cell in cells[kind]:
            tf = cell["timeframes"][0]
            want = (REPO / mapping[tf]).resolve()
            got = Path(estimator.cell_source(cell, criteria)).resolve()
            if got != want:
                out.append(f"{cell['id']}：來源 {got} ≠ 判準對映 {want}")
                break
    for cell in cells["B"]:
        if Path(estimator.cell_source(cell, criteria)).resolve() != (REPO / mapping[cell["timeframes"][0]]).resolve():
            out.append(f"{cell['id']}：格 B 來源 ≠ 主週期之來源")
            break
    sample = [c for c in cells["A"] if c["symbol"] == cells["A"][0]["symbol"]]
    for cell in sample:
        tf = cell["timeframes"][0]
        src = REPO / mapping[tf]
        record = estimator.cell_kline_records(cell, criteria)[tf]
        if record.get("source") != mapping[tf]:
            out.append(f"{cell['id']}：紀錄之 source {record.get('source')!r} ≠ {mapping[tf]!r}")
        if record.get("dataset_sha256") != _independent_dataset_sha256(src, cell["symbol"], tf):
            out.append(f"{cell['id']}：dataset_sha256 ≠ 獨立重算")
        with h5py.File(str(src), "r") as handle:
            n = int(handle[cell["symbol"]][tf]["data"].shape[0])
        if record.get("bar_count") != n:
            out.append(f"{cell['id']}：bar_count {record.get('bar_count')} ≠ 來源 {n}")
        if estimator.cell_window(cell, criteria)[1] != record.get("series_end"):
            out.append(f"{cell['id']}：輸出段終點 ≠ 來源序列末根 {record.get('series_end')}")
    return out


def test_estimate_kline_source_rule_per_timeframe() -> None:
    """判準 v2 `cell_rules.kline_source`：依週期之來源檔、格 B 單一來源、輸出段依來源序列、逐格資料集 sha256。"""
    assert kline_source_violations(ESTIMATOR) == []


def test_estimate_kline_source_long_history_differs_from_main() -> None:
    """前提與鑑別力：判準對映中有週期之來源不同於主檔（長歷史），且該週期之格之輸出段終點與資料集 sha256 皆異於主檔同週期
    （若相同則 mutation 無從鑑別）。"""
    criteria = _load_criteria()
    mapping = criteria["cell_rules"]["kline_source"]["by_timeframe"]
    main_rel = criteria["cell_rules"]["enumerate_from"]
    long_tfs = sorted(tf for tf, src in mapping.items() if src != main_rel)
    assert long_tfs, "判準對映無任何週期讀長歷史檔"
    cell = next(c for c in ESTIMATOR.enumerate_cells(nh.KLINE_PATH)["A"] if c["timeframes"] == [long_tfs[0]])
    record = ESTIMATOR.cell_kline_records(cell, criteria)[long_tfs[0]]
    assert record["dataset_sha256"] != _independent_dataset_sha256(nh.KLINE_PATH, cell["symbol"], long_tfs[0])


def test_mutation_estimate_kline_source_reads_main_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：來源一律讀主檔（忽略判準對映）⇒ 長歷史週期之格來源／sha256／輸出段終點檢查翻紅。"""
    assert kline_source_violations(ESTIMATOR) == []
    monkeypatch.setattr(ESTIMATOR, "kline_source", lambda tf, criteria: nh.KLINE_PATH)
    monkeypatch.setattr(ESTIMATOR, "_DATASET_RECORDS", {})
    assert kline_source_violations(ESTIMATOR) != []


# ---------------------------------------------------------------------------------------------- 判準 v3（追加）：路徑覆蓋之封閉格清單
# 使用者 2026-10-22 裁定量測設計＝路徑覆蓋、非重複；格＝判準 `cell_rules.cell_list`（每格之獨有覆蓋 covers），各跑別之重型跑＝
# 判準 `run_coverage`（(格, covers) 唯一）。以下皆讀判準與 git／檔名，不生成。

def _closed_cells() -> List[Dict[str, Any]]:
    cells = nh.criteria_cell_list()
    return list(cells or [])


def _closed_descriptor(cell: Mapping[str, Any]) -> Tuple[str, str, str, Tuple[str, ...]]:
    return (str(cell["id"]), str(cell["kind"]), str(cell["symbol"]), tuple(str(t) for t in cell["timeframes"]))


def _present_criteria_files() -> List[Path]:
    """工作樹現存之判準版本檔（`preregistered_criteria*.json`）。不含 assert。"""
    return sorted(p for p in nh.GOLDEN_DIR.glob(CRITERIA_GLOB) if p.is_file())


def vn_replacement_violations() -> List[str]:
    """判準 vN（N≥2）取代之流程規則（SPEC Task 0.3 邊界①，判準 v3 起之 vN→vN+1）：判準檔名恰一存在；其餘版本檔不在 HEAD；
    現行版恰一提交；全部版本之提交皆早於每份量測收據（估時收據除外）之首次提交（尚無量測收據 ⇒ 無對象）。不含 assert。"""
    out: List[str] = []
    present = _present_criteria_files()
    if len(present) != 1:
        return [f"判準檔須恰一存在，實得 {[p.name for p in present]}"]
    current = present[0]
    for path in _criteria_name_paths():
        if path != current and _git("cat-file", "-e", f"HEAD:{_rel(path)}").returncode == 0:
            out.append(f"舊版判準 {path.name} 仍在 HEAD（須刪舊檔）")
    log = _git("log", "--format=%H", "--", _rel(current))
    if log.returncode != 0 or len(log.stdout.decode().split()) != 1:
        out.append(f"{current.name} 之提交數 ≠ 1")
    if _measurement_receipt_paths():
        out += criteria_after_receipt_violations()
    return out


def closed_estimate_receipt_violations(receipt: Mapping[str, Any], kline: Mapping[str, List[str]]) -> List[str]:
    """判準 v3 之估時收據檢查（取代「全部 symbol×tf」列舉之涵蓋檢查）：格＝封閉清單；每跑別之格與 runs（格, covers）涵蓋判準
    run_coverage；Phase 2–4 驗收重產跑別另涵蓋 `REGEN_REQUIREMENTS`（於封閉清單之格）；PRE-PROV 格涵蓋；凍結組＝判準
    freeze_groups、G1 臂集＝契約；格 C 基準逐封閉清單之格 C 週期；省法清單。"""
    out: List[str] = []
    try:
        dt.datetime.fromisoformat(str(receipt.get("reported_at")))
    except ValueError:
        out.append("reported_at 缺或非 ISO-8601（主委白話報告後寫入）")
    cells = receipt.get("cells")
    if not isinstance(cells, Mapping) or set(cells) != set(CELL_CATEGORIES):
        return out + [f"cells 須恰含格類 {CELL_CATEGORIES}"]
    got = {_closed_descriptor(c) for kind in CELL_CATEGORIES for c in cells[kind] or [] if isinstance(c, Mapping)}
    want = {_closed_descriptor(c) for c in _closed_cells()}
    if got != want:
        out.append(f"cells ≠ 判準封閉清單：缺 {sorted(want - got)[:3]} 多 {sorted(got - want)[:3]}")
    for descriptor in want:
        if any(tf not in kline.get(descriptor[2], []) for tf in descriptor[3]):
            out.append(f"封閉清單之格 {descriptor[0]} 不在主檔列舉")
    index = _cell_index(receipt)
    ids = {c: {i for i, (cat, _) in index.items() if cat == c} for c in CELL_CATEGORIES}
    criteria = json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))
    coverage = criteria.get("run_coverage") or {}
    run_kinds = receipt.get("run_kinds")
    if not isinstance(run_kinds, Mapping):
        return out + ["run_kinds 缺"]
    for kind in ESTIMATOR.RUN_KINDS:
        node = run_kinds.get(kind)
        plan = coverage.get(kind)
        if not isinstance(node, Mapping):
            out.append(f"run_kinds 缺跑別 {kind}")
            continue
        if not isinstance(plan, Mapping):
            out.append(f"判準 run_coverage 缺跑別 {kind}")
            continue
        listed = set(node.get("cells") or [])
        preprov_listed = set(node.get("preprov_cells") or [])
        want_cells = {str(r["cell"]) for r in plan.get("runs") or []}
        if kind in REGEN_REQUIREMENTS:
            want_cells |= regen_required_cells(REGEN_REQUIREMENTS[kind]["cells"], index, ids)
        if (not listed and not preprov_listed) or not listed <= set(index):
            out.append(f"{kind}：cells 為空或含未列舉之格")
        if want_cells - listed:
            out.append(f"{kind}：未涵蓋 {sorted(want_cells - listed)[:3]}")
        want_runs = {(str(r["cell"]), str(r["covers"])) for r in plan.get("runs") or []}
        got_runs = {(str(r.get("cell")), str(r.get("covers"))) for r in node.get("runs") or [] if isinstance(r, Mapping)
                    and isinstance(r.get("seconds"), (int, float)) and r["seconds"] >= 0}
        if want_runs - got_runs:
            out.append(f"{kind}：runs 未逐一列（格, 獨有覆蓋, 外推秒數）：缺 {len(want_runs - got_runs)} 筆")
        want_preprov = regen_required_preprov(REGEN_REQUIREMENTS[kind]["preprov"]) if kind in REGEN_REQUIREMENTS else set()
        want_preprov |= regen_required_preprov(list((plan.get("preprov") or {}).keys()))
        if want_preprov - preprov_listed:
            out.append(f"{kind}：未涵蓋 PRE-PROV 格 {sorted(want_preprov - preprov_listed)}")
        if preprov_listed - known_preprov_cells():
            out.append(f"{kind}：preprov_cells 含未知格 {sorted(preprov_listed - known_preprov_cells())}")
        # 須有正單格秒數之格類：本跑別中有重型 run（生成／轉換／分支差／效能）且該格未 blocked（收據 run 列無 skipped）者
        heavy = {index[str(r.get("cell"))][0] for r in node.get("runs") or [] if isinstance(r, Mapping)
                 and str(r.get("cell")) in index and not r.get("skipped")
                 and (r.get("generations") or r.get("transform_passes") or r.get("branchdiff") or r.get("perf"))}
        # PRE-PROV 生成只記於生成型跑別（檢查型跑別以 0 次列其所讀格名，不計秒數）
        heavy |= {"preprov"} if any(int(n) for n in (node.get("preprov_generations") or {}).values()) else set()
        per_cat = node.get("single_cell_seconds") or {}
        for cat in heavy:
            if not _positive_number(per_cat.get(cat)):
                out.append(f"{kind}：缺格類 {cat} 之單格實測秒數")
        if heavy and not _positive_number(node.get("extrapolated_total_seconds")):
            out.append(f"{kind}：缺外推總秒數")
    groups = (run_kinds.get("freeze_baseline") or {}).get("groups") or {}
    want_groups = criteria["cell_rules"]["freeze_groups"]
    arms = set(nv.load_contract()["post_ic_arm_values"]["values"])
    for name in ("G1", "G2", "G3"):
        if set((groups.get(name) or {}).get("cells") or []) != set(want_groups[name]):
            out.append(f"freeze_baseline.groups.{name} ≠ 判準 freeze_groups")
    if set((groups.get("G1") or {}).get("arms") or []) != arms or not arms:
        out.append("freeze_baseline.groups.G1 之臂集 ≠ 契約 post_ic_arm_values")
    savings = receipt.get("savings")
    if not isinstance(savings, list) or not savings or not all(
            isinstance(s, Mapping) and str(s.get("method", "")).strip()
            and isinstance(s.get("saved_seconds"), (int, float)) and not isinstance(s.get("saved_seconds"), bool)
            and s["saved_seconds"] >= 0 for s in savings):
        out.append("savings 須為非空之 {method, saved_seconds≥0} 清單")
    c_tfs = {str(c["timeframes"][0]) for c in _closed_cells() if c["kind"] == "C"}
    baseline = receipt.get("cell_c_baseline")
    if not isinstance(baseline, Mapping) or set(baseline) != c_tfs:
        out.append(f"cell_c_baseline 須逐封閉清單之格 C 週期一項：{sorted(c_tfs)}")
    else:
        for tf, node in baseline.items():
            if not isinstance(node, Mapping):
                out.append(f"cell_c_baseline.{tf}：非物件")
            elif node.get("blocked_by") != BLOCKED_BY_HARDWARE and not (
                    node.get("source") == "measured" and _positive_number(node.get("seconds"))
                    and _positive_number(node.get("peak_rss_bytes"))):
                out.append(f"cell_c_baseline.{tf}：須實測或標 blocked_by=hardware")
    # 審查 r6 CODEX-R6-P1-05：任一列之轉換成本缺實測臂／分支（不代補）⇒ 估時無效、不得寫 reported_at
    bad_rows = [f"{k}:{r.get('cell')}" for k, node in run_kinds.items() if isinstance(node, Mapping)
                for r in node.get("runs") or [] if isinstance(r, Mapping) and r.get("incomplete")]
    if bad_rows or receipt.get("incomplete"):
        out.append(f"估時不完整（轉換成本缺實測、不代補）：{sorted(set(bad_rows) | set(receipt.get('incomplete') or []))[:5]}")
    # 判準檔 cell_rules.continuity：逐格連續性紀錄；來源全序列無缺口 ⇒ 生產設定（True）；生成窗內零缺口
    production = criteria["cell_rules"]["continuity"]["production_validate_continuity"]
    continuity = receipt.get("continuity")
    if not isinstance(continuity, Mapping) or set(continuity) != {str(c["id"]) for c in _closed_cells()}:
        out.append("continuity 須逐封閉清單之格一項")
    else:
        for cid, rec in continuity.items():
            gaps = rec.get("series_gaps") if isinstance(rec, Mapping) else None
            if not isinstance(gaps, Mapping):
                out.append(f"continuity.{cid}：缺 series_gaps")
                continue
            if not any(gaps.values()) and rec.get("validate_continuity") is not production:
                out.append(f"continuity.{cid}：來源無缺口而未用生產連續性設定 {production}")
            if rec.get("window_gaps"):
                out.append(f"continuity.{cid}：生成窗內有缺口 {rec.get('window_gaps')}")
    return out


def closed_list_violations(estimator: ModuleType) -> List[str]:
    """估時器之格＝判準封閉清單（`enumerate_cells`）；實測目標＝封閉清單之格（鍵＝格 id）＋判準涉及之 PRE-PROV 格。"""
    want = {_closed_descriptor(c) for c in _closed_cells()}
    if not want:
        return ["判準無封閉格清單（cell_rules.cell_list.cells）"]
    cells = estimator.enumerate_cells(nh.KLINE_PATH)
    got = {_closed_descriptor(c) for kind in CELL_CATEGORIES for c in cells[kind]}
    out: List[str] = []
    if got != want:
        out.append(f"enumerate_cells ≠ 判準封閉清單：缺 {sorted(want - got)[:3]} 多 {sorted(got - want)[:3]}")
    targets = [t["target"] for t in estimator.measurement_targets(cells, estimator.kline_inventory(nh.KLINE_PATH))
               if t["category"] in CELL_CATEGORIES]
    if sorted(targets) != sorted(d[0] for d in want):
        out.append(f"實測目標 ≠ 封閉清單之格：{sorted(targets)}")
    return out


def test_estimate_cells_equal_criteria_closed_list() -> None:
    """判準 v3：估時器之格與實測目標＝判準封閉清單（路徑覆蓋），不再列舉全部 symbol×tf。"""
    assert closed_list_violations(ESTIMATOR) == []


def test_mutation_estimate_cells_full_enumeration(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：估時器回到「全部 symbol×tf」列舉（忽略封閉清單）⇒ 檢查翻紅。"""
    assert closed_list_violations(ESTIMATOR) == []

    def full(kline_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {k: [] for k in CELL_CATEGORIES}
        for symbol, tfs in _kline_index().items():
            for tf in tfs:
                for kind in ("A", "C"):
                    out[kind].append({"id": ESTIMATOR.cell_id(kind, symbol, [tf]), "kind": kind, "symbol": symbol,
                                      "timeframes": [tf]})
        return out

    monkeypatch.setattr(ESTIMATOR, "enumerate_cells", full)
    assert closed_list_violations(ESTIMATOR) != []


def test_estimate_run_coverage_unique_paths() -> None:
    """判準 v3 `run_coverage`：每個重型跑別之每個 run 皆具非空之獨有覆蓋（covers）、格屬封閉清單、(格, covers) 全票唯一；
    封閉清單每格具非空 covers；每格至少被一個跑別覆蓋。"""
    criteria = _load_criteria()
    assert ESTIMATOR.coverage_violations(criteria) == []
    closed = _closed_cells()
    assert closed and all(str(c.get("covers") or "").strip() for c in closed)
    used = {str(r["cell"]) for node in criteria["run_coverage"].values() if isinstance(node, Mapping)
            for r in node.get("runs") or []}
    assert {str(c["id"]) for c in closed} <= used, sorted({str(c["id"]) for c in closed} - used)
    heavy = [k for k in ESTIMATOR.RUN_KINDS if any(r.get("generations") for r in criteria["run_coverage"][k]["runs"])]
    assert heavy and all(all(str(r.get("covers") or "").strip() for r in criteria["run_coverage"][k]["runs"]) for k in heavy)


@pytest.mark.parametrize("mutant", ["duplicate_run", "empty_covers", "cell_outside_list"])
def test_mutation_estimate_run_coverage_duplicate_path(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：同一路徑重複跑（複製一個 run 至另一跑別）／covers 為空／格不在封閉清單 ⇒ 路徑覆蓋檢查翻紅（變異經
    估時器之判準讀取入口 `load_criteria` 注入）。"""
    criteria = copy.deepcopy(_load_criteria())
    monkeypatch.setattr(ESTIMATOR, "load_criteria", lambda *_a, **_k: criteria)
    assert ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria()) == []
    runs = criteria["run_coverage"]["freeze_baseline"]["runs"]
    if mutant == "duplicate_run":
        criteria["run_coverage"]["regen_t21"]["runs"].append(copy.deepcopy(runs[0]))
        expect = "重複路徑"
    elif mutant == "empty_covers":
        runs[0]["covers"] = "  "
        expect = "缺 covers"
    else:
        runs[0]["cell"] = "A_NUMVIEWMUTANT_1h"
        expect = "不在封閉清單"
    violations = ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria())
    assert any(expect in v for v in violations), violations


# 判準 `run_coverage` 之「同一碼態每個生成身分只生成一次」（使用者 2026-10-22 路徑覆蓋裁定；判準檔 cell_rules.batch_cache）：
# 測試端獨立帳（不呼叫估時器），與估時器 `coverage_violations` 互為對照。

def _generation_ledger_violations(criteria: Mapping[str, Any]) -> List[str]:
    """獨立重算：生成型跑別（code_state）內每個生成身分 (格, env, 變體) 於同碼態合計至多 1 次；檢查型跑別（reads_from）不生成；
    每個 generations＝0 之 run 所讀之生成存在於其 source 跑別且同碼態；批次跑別（b3／b4／b5）之每個生成至少被一個檢查型跑別
    之 run 讀取。不含 assert。"""
    coverage = {k: v for k, v in (criteria.get("run_coverage") or {}).items() if isinstance(v, Mapping)}
    out: List[str] = []

    def ident(r: Mapping[str, Any]) -> Tuple[str, str, str]:
        return (str(r.get("cell")), json.dumps({str(k): str(v) for k, v in dict(r.get("env") or {}).items()},
                                               sort_keys=True), str(r.get("variant") or ""))

    count: Dict[Tuple[str, Tuple[str, str, str]], int] = {}
    owner: Dict[Tuple[str, Tuple[str, str, str]], Set[str]] = {}
    transforms: Dict[Tuple[str, Tuple[str, str, str]], int] = {}
    for kind, node in coverage.items():
        for r in node.get("runs") or []:
            gens = int(r.get("generations") or 0)
            tp = int(r.get("transform_passes") or 0)
            if gens and node.get("reads_from"):
                out.append(f"{kind} 為檢查型卻生成 {r.get('cell')}")
            if tp and node.get("reads_from"):
                out.append(f"{kind} 為檢查型卻自行轉換 {r.get('cell')}")
            if node.get("code_state"):
                key = (str(node["code_state"]), ident(r))
                if gens:
                    count[key] = count.get(key, 0) + gens
                    owner.setdefault(key, set()).add(kind)
                if tp:
                    transforms[key] = transforms.get(key, 0) + tp
    out += [f"碼態 {s} 之 {i} 生成 {n} 次" for (s, i), n in count.items() if n > 1]
    out += [f"碼態 {s} 之 {i} 轉換 {n} 次" for (s, i), n in transforms.items() if n > 1]
    for kind, node in coverage.items():
        for r in node.get("runs") or []:
            if r.get("reads_transforms"):
                state = (coverage.get(str(r.get("source"))) or {}).get("code_state")
                if (str(state), ident(r)) not in transforms:
                    out.append(f"{kind} 讀 {r.get('source')} 之 {ident(r)} 轉換不存在")
    read: Set[Tuple[str, Tuple[str, str, str]]] = set()
    for kind, node in coverage.items():
        for r in node.get("runs") or []:
            if int(r.get("generations") or 0):
                continue
            source = str(r.get("source"))
            state = (coverage.get(source) or {}).get("code_state")
            if node.get("code_state") and state != node.get("code_state"):
                out.append(f"{kind} 讀 {source} 跨碼態")
            if source not in owner.get((str(state), ident(r)), set()):
                out.append(f"{kind} 讀 {source} 之 {ident(r)} 無對應生成")
            if node.get("reads_from"):
                read.add((str(state), ident(r)))
    for (state, i), kinds in owner.items():
        if state in ("b3", "b4", "b5") and (state, i) not in read:
            out.append(f"批次 {sorted(kinds)} 之 {i} 無檢查讀取")
    return out


def test_estimate_run_coverage_one_generation_per_code_state() -> None:
    """判準 run_coverage：同一碼態內每個生成身分只生成一次——Task 1.3 L2 不重生凍結已生成之 (格, 環境)（只生成凍結所無之環境）；
    Phase 2–4 每批每 (格, 環境, 變體) 一次、檢查型跑別只讀批次生成、無檢查讀取之重生不存在；格 C 每碼態每環境至多一次，且
    Phase 2–4 之批次只在該批有檢查讀 C 時生成 C。估時器檢查與測試端獨立帳一致為零違規。"""
    criteria = _load_criteria()
    assert _generation_ledger_violations(criteria) == []
    assert ESTIMATOR.coverage_violations(criteria) == []
    coverage = criteria["run_coverage"]
    freeze_ids = {(r["cell"], json.dumps(r.get("env") or {}, sort_keys=True)) for r in coverage["freeze_baseline"]["runs"]}
    l2_gen = [(r["cell"], json.dumps(r.get("env") or {}, sort_keys=True)) for r in coverage["l2_arm_matrix"]["runs"]
              if r.get("generations")]
    assert not set(l2_gen) & freeze_ids, sorted(set(l2_gen) & freeze_ids)
    c_ids = {str(c["id"]) for c in _closed_cells() if c.get("kind") == "C"}
    for kind, node in coverage.items():
        if not isinstance(node, Mapping) or node.get("code_state") not in ("b3", "b4", "b5"):
            continue
        for r in node["runs"]:
            if r["cell"] in c_ids and r.get("generations"):
                readers = [k for k in r.get("feeds") or []
                           if any(x.get("source") == kind and x["cell"] == r["cell"] for x in coverage[k]["runs"])]
                assert readers, f"{kind} 生成格 C 而該批無檢查讀取"


@pytest.mark.parametrize("mutant", ["l2_regenerates_freeze", "batch_duplicate_c", "check_generates",
                                    "unread_batch_generation", "reader_without_generation", "reader_outside_reads_from",
                                    "check_recomputes_transform", "batch_duplicate_transform", "reader_without_transform"])
def test_mutation_estimate_duplicate_generation_per_code_state(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（路徑覆蓋：同碼態每生成身分一次）：L2 重生凍結已生成之格／同批重複生成格 C／檢查型跑別自行生成／批次生成無
    檢查讀取／檢查讀取不存在之生成／檢查讀 reads_from 以外之批次 ⇒ 估時器 `coverage_violations` 翻紅（變異經 `load_criteria`
    注入）；前兩案與檢查型生成另由測試端獨立帳翻紅。"""
    criteria = copy.deepcopy(_load_criteria())
    monkeypatch.setattr(ESTIMATOR, "load_criteria", lambda *_a, **_k: criteria)
    assert ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria()) == []
    cov = criteria["run_coverage"]
    ledger_red = True
    if mutant == "l2_regenerates_freeze":
        row = next(r for r in cov["l2_arm_matrix"]["runs"] if not r.get("generations") and not r.get("env"))
        row["generations"] = 1
        row.pop("source", None)
        expect = "同碼態重複生成"
    elif mutant == "batch_duplicate_c":
        row = copy.deepcopy(next(r for r in cov["regen_b3"]["runs"] if r["cell"].startswith("C_")))
        row["covers"] = row["covers"] + "（變異：同批再生成一次）"
        cov["regen_b3"]["runs"].append(row)
        expect = "同碼態重複生成"
    elif mutant == "check_generates":
        cov["regen_t22"]["runs"][0]["generations"] = 1
        expect = "檢查型跑別不得生成"
    elif mutant == "unread_batch_generation":
        cov["regen_b5"]["runs"].append({"cell": "A_BTCUSDT_4h", "covers": "變異：無檢查讀取之重生", "generations": 1,
                                        "transform_passes": 0, "env": {"FFACT_USE_POLARS": "0"},
                                        "feeds": ["regen_section_g"]})
        expect = "無檢查讀取"
    elif mutant == "reader_without_generation":
        row = next(r for r in cov["regen_section_g"]["runs"] if r["cell"].startswith("C_"))
        row["env"] = {"FFACT_USE_POLARS": "0"}
        expect = "無對應生成"
    elif mutant == "check_recomputes_transform":  # t22 自行再算 b3 已算之 IC 頁各臂輸出
        cov["regen_t22"]["runs"][0]["transform_passes"] = 1
        expect = "檢查型跑別不得自行轉換"
    elif mutant == "batch_duplicate_transform":  # 同碼態同身分之轉換算兩次
        next(r for r in cov["regen_b3"]["runs"] if r.get("transform_passes"))["transform_passes"] = 2
        expect = "同碼態重複轉換"
    elif mutant == "reader_without_transform":  # 批次生成列不算轉換，檢查卻宣稱讀其轉換
        reader = next(r for r in cov["regen_section_g"]["runs"] if r.get("reads_transforms") and r["source"] == "regen_b5")
        next(r for r in cov["regen_b5"]["runs"] if r["cell"] == reader["cell"] and not r.get("env"))["transform_passes"] = 0
        expect = "無轉換"
    else:
        cov["regen_t34"]["runs"][0]["source"] = "regen_b3"
        expect = "不在 reads_from"
        ledger_red = False
    violations = ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria())
    assert any(expect in v for v in violations), violations
    if ledger_red:
        assert _generation_ledger_violations(criteria) != []


def test_estimate_receipt_closed_list_checker_discriminates() -> None:
    """判準 v3 之估時收據檢查（閘邏輯單元；實測秒數為結構佔位）：依判準組裝之收據無違規；刪一個 run（獨有路徑漏估）、
    格清單多一格（非封閉清單）各翻紅。"""
    criteria = _load_criteria()
    inventory = ESTIMATOR.kline_inventory(nh.KLINE_PATH)
    cells = ESTIMATOR.enumerate_cells(nh.KLINE_PATH)
    body = ESTIMATOR.build_receipt(cells, inventory, criteria, _synthetic_measurements(inventory, cells),
                                   nv.load_contract()["post_ic_arm_values"]["values"])
    receipt = json.loads(json.dumps({"reported_at": "2026-10-22T00:00:00+08:00", "cells": cells, **body}))
    assert closed_estimate_receipt_violations(receipt, _kline_index()) == []
    dropped = copy.deepcopy(receipt)
    dropped["run_kinds"]["precision_chain"]["runs"].pop(0)
    assert any("runs 未逐一列" in v for v in closed_estimate_receipt_violations(dropped, _kline_index()))
    extra = copy.deepcopy(receipt)
    extra["cells"]["A"].append({"id": "A_ETHUSDT_1h", "kind": "A", "symbol": "ETHUSDT", "timeframes": ["1h"]})
    assert any("≠ 判準封閉清單" in v for v in closed_estimate_receipt_violations(extra, _kline_index()))
    # 判準檔 cell_rules.continuity：來源無缺口之格未用生產連續性設定／生成窗內有缺口 ⇒ 紅
    clean = next(cid for cid, rec in receipt["continuity"].items() if not any(rec["series_gaps"].values()))
    loosened = copy.deepcopy(receipt)
    loosened["continuity"][clean]["validate_continuity"] = False
    assert any("未用生產連續性設定" in v for v in closed_estimate_receipt_violations(loosened, _kline_index()))
    gapped = copy.deepcopy(receipt)
    gapped["continuity"][clean]["window_gaps"] = ["1h：變異缺口"]
    assert any("生成窗內有缺口" in v for v in closed_estimate_receipt_violations(gapped, _kline_index()))


def test_boundary_05_vn_replacement_rule() -> None:
    """邊界①（判準 v3 起之 vN→vN+1）：`vn_replacement_violations` 對現行判準（v1／v2 不在工作樹時）判定；且以工作樹臨時多放
    一個版本檔之情形（不寫檔：monkeypatch 讀取）判「須恰一存在」。只在 vN（N≥3）現行時有對象。"""
    present = sorted(p.name for p in nh.GOLDEN_DIR.glob(CRITERIA_GLOB) if p.is_file())
    assert len(present) == 1, present
    if present[0] in (CRITERIA_V1.name, CRITERIA_V2_NAME):
        return
    assert vn_replacement_violations() == []


def test_mutation_vn_replacement_two_versions_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """變異：工作樹同時存在兩個判準版本檔（不寫檔：monkeypatch `_present_criteria_files` 多回一個舊版檔名）⇒ 判「須恰一
    存在」；對照：未變異 ⇒ 不出此條。"""
    real = _present_criteria_files()
    assert not any("須恰一存在" in v for v in vn_replacement_violations())
    stale = nh.GOLDEN_DIR / "preregistered_criteria_v0.json"
    monkeypatch.setattr(sys.modules[__name__], "_present_criteria_files", lambda: real + [stale])
    assert any("須恰一存在" in v for v in vn_replacement_violations())


# ---------------------------------------------------------------------------------------------- Task 1.5 ⑦ D-ICPAGE-ARM 重新呈報
# 決定紀錄（decisions.json）於 Task 1.5 才產出；以下以合 schema 之單筆紀錄驗判準 schema 與 `icpage_violations` 之⑦（秒級、不讀
# 決定紀錄檔），效能基準收據之存在與提交日經可注入之查詢函式。

_FAKE_PERF_RECEIPT = "handoffs/run_receipts/20261030-numview-perf-benchmark.json"


def _icpage_record_schema(criteria: Mapping[str, Any]) -> Dict[str, Any]:
    ds = criteria["decisions_schema"]
    return {"$schema": ds["$schema"], "$defs": ds["$defs"], **ds["properties"]["decisions"]["properties"]["d_icpage_arm"]}


def _valid_icpage_record() -> Dict[str, Any]:
    return {"label": "D-ICPAGE-ARM", "triggered": True, "choice": ICPAGE_LOCK, "changes_public_output": True,
            "changes_feature_stage": False, "evidence": [{"receipt": _FAKE_PERF_RECEIPT, "rows_key": "speed", "row": 0}],
            "user_ruling": {"date": ICPAGE_RULING_DATE, "quote": list(ICPAGE_RULING_QUOTE)},
            "re_presentation": {"date": "2026-10-31", "quote": ["維持鎖 Polars"], "perf_benchmark_receipt": _FAKE_PERF_RECEIPT,
                                "confirmed_choice": ICPAGE_LOCK}}


def test_icpage_re_presentation_schema_and_checker_accept_valid_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """⑦：合規之 D-ICPAGE-ARM 紀錄（具 re_presentation，日期不早於效能基準收據之提交）過判準 schema 與 `icpage_violations`。"""
    monkeypatch.setattr(sys.modules[__name__], "_repo_file_exists", lambda rel: rel == _FAKE_PERF_RECEIPT)
    monkeypatch.setattr(sys.modules[__name__], "_perf_receipt_first_commit_date", lambda rel: "2026-10-30")
    monkeypatch.setattr(sys.modules[__name__], "_load_perf_receipt", lambda rel: _valid_perf_receipt())
    record = _valid_icpage_record()
    assert _schema_errors(_icpage_record_schema(_load_criteria()), record) == []
    assert icpage_violations({"decisions": {"d_icpage_arm": record}}) == []


@pytest.mark.parametrize("mutant", ["deleted", "date_before_receipt", "receipt_uncommitted", "receipt_missing",
                                    "empty_quote", "wrong_receipt_path", "choice_mismatch"])
def test_mutation_icpage_re_presentation_invalid(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（Task 1.5 ⑦、SPEC v17 §A）：刪 re_presentation／日期早於效能基準收據之提交／收據未提交／收據不存在／原話空／
    收據路徑非效能基準收據／confirmed_choice ≠ choice ⇒ `icpage_violations` 紅；刪除與欄位形態錯另由判準 schema 紅。"""
    committed: Optional[str] = "2026-10-30"
    exists = True
    record = _valid_icpage_record()
    rp = record["re_presentation"]
    schema_red = False
    if mutant == "deleted":
        del record["re_presentation"]
        schema_red = True
    elif mutant == "date_before_receipt":
        rp["date"] = "2026-10-29"
    elif mutant == "receipt_uncommitted":
        committed = None
    elif mutant == "receipt_missing":
        exists = False
    elif mutant == "empty_quote":
        rp["quote"] = []
        schema_red = True
    elif mutant == "wrong_receipt_path":
        rp["perf_benchmark_receipt"] = "handoffs/run_receipts/20261030-numview-postic-branchdiff.json"
        schema_red = True
    else:
        rp["confirmed_choice"] = "retain"
    monkeypatch.setattr(sys.modules[__name__], "_repo_file_exists", lambda rel: exists and rel.endswith("perf-benchmark.json"))
    monkeypatch.setattr(sys.modules[__name__], "_perf_receipt_first_commit_date", lambda rel: committed)
    monkeypatch.setattr(sys.modules[__name__], "_load_perf_receipt", lambda rel: _valid_perf_receipt())
    assert icpage_violations({"decisions": {"d_icpage_arm": record}}) != []
    if schema_red:
        assert _schema_errors(_icpage_record_schema(_load_criteria()), record) != []


# ---------------------------------------------------------------------------------------------- 封閉路徑登錄（審查 r5 CODEX-R5-P1-03）
# 重型生成之獨有覆蓋以判準檔 path_registry 之 id 機械判定（covers 文字只作人讀說明）；測試端獨立帳與估時器
# `coverage_violations`（⑦ path_registry_violations）互為對照。

def _path_registry_ledger_violations(criteria: Mapping[str, Any]) -> List[str]:
    """獨立重算：(a) 同碼態一 id 至多一個生成宣稱（distinct_by 所列 env／variant 兩兩相異者除外）；(b) 每個登錄 id 至少一個
    生成宣稱；(c) 錨點 path:line 解析至存在之非空行；生成列 covers_ids 非空且 ⊆ 登錄。不含 assert。"""
    paths = (criteria.get("path_registry") or {}).get("paths") or []
    reg = {str(p.get("id")): p for p in paths}
    out: List[str] = [] if len(reg) == len(paths) and paths else ["登錄為空或 id 重複"]
    for pid, entry in reg.items():
        for anchor in entry.get("code_anchors") or [""]:
            rel, _, line = str(anchor).rpartition(":")
            target = REPO / rel
            text = target.read_text(encoding="utf-8", errors="replace").splitlines() if rel and target.is_file() else []
            if not line.isdigit() or not (1 <= int(line) <= len(text)) or not text[int(line) - 1].strip():
                out.append(f"{pid} 錨點 {anchor} 不解析")
    seen: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}
    for kind, node in (criteria.get("run_coverage") or {}).items():
        if not isinstance(node, Mapping) or not node.get("code_state"):
            continue
        for r in node.get("runs") or []:
            if not int(r.get("generations") or 0):
                continue
            ids = list(r.get("covers_ids") or [])
            if not ids or not set(ids) <= set(reg):
                out.append(f"{kind} {r.get('cell')} covers_ids {ids} 空或含未登錄")
            env = json.dumps({str(k): str(v) for k, v in dict(r.get("env") or {}).items()}, sort_keys=True)
            for pid in ids:
                seen.setdefault((str(node["code_state"]), pid), []).append((env, str(r.get("variant") or "")))
    for (state, pid), who in seen.items():
        dims = list((reg.get(pid) or {}).get("distinct_by") or [])
        proj = [tuple(e if d == "env" else v for d in dims) for e, v in who]
        if len(who) > 1 and (not dims or len(set(proj)) != len(proj)):
            out.append(f"碼態 {state} 之 {pid} 重複宣稱 {len(who)} 次")
    out += [f"{pid} 無生成宣稱" for pid in reg if not any(p == pid for (_, p) in seen)]
    return out


def test_estimate_path_registry_closed_and_complete() -> None:
    """判準 path_registry：每個生成列具 covers_ids ⊆ 登錄；同碼態一路徑至多一個生成宣稱（distinct_by 例外）；每個登錄路徑至少
    一個生成宣稱；錨點解析至存在之非空行。估時器檢查與測試端獨立帳一致為零違規。"""
    criteria = _load_criteria()
    assert _path_registry_ledger_violations(criteria) == []
    assert ESTIMATOR.coverage_violations(criteria) == []
    assert len(criteria["path_registry"]["paths"]) >= len(_closed_cells())


@pytest.mark.parametrize("mutant", ["reworded_duplicate_same_id", "registry_id_unclaimed", "anchor_missing_line",
                                    "generation_without_covers_ids"])
def test_mutation_estimate_path_registry(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R5-P1-03）：以新措辭重複同一路徑 id（同碼態、非 distinct_by 維度）／登錄 id 無生成宣稱／錨點指向不存在
    之行／生成列缺 covers_ids ⇒ 估時器 `coverage_violations` 與測試端獨立帳皆紅（變異經 `load_criteria` 注入）。"""
    criteria = copy.deepcopy(_load_criteria())
    monkeypatch.setattr(ESTIMATOR, "load_criteria", lambda *_a, **_k: criteria)
    assert ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria()) == []
    cov = criteria["run_coverage"]
    if mutant == "reworded_duplicate_same_id":
        src = next(r for r in cov["freeze_baseline"]["runs"] if r["cell"] == "A_BTCUSDT_4h")
        cov["l2_arm_matrix"]["runs"].append({**copy.deepcopy(src), "env": {"FFACT_USE_POLARS": "0"},
                                             "covers": "變異：同一週期換算路徑之另一種說法", "transform_passes": 0})
        expect = "同碼態重複路徑"
    elif mutant == "registry_id_unclaimed":
        criteria["path_registry"]["paths"].append({"id": "mutant.unclaimed", "description": "變異",
                                                    "code_anchors": ["momentum/factories.py:327"]})
        expect = "無任何生成宣稱"
    elif mutant == "anchor_missing_line":
        criteria["path_registry"]["paths"][0]["code_anchors"] = ["momentum/factories.py:999999"]
        expect = "不解析至存在之非空行"
    else:
        next(r for r in cov["regen_b4"]["runs"] if r.get("variant"))["covers_ids"] = []
        expect = "缺 covers_ids"
    violations = ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria())
    assert any(expect in v for v in violations), violations
    assert _path_registry_ledger_violations(criteria) != []


# ---------------------------------------------------------------------------------------------- 效能基準收據內容（審查 r6 CODEX-R6-P1-04）

def _valid_perf_receipt() -> Dict[str, Any]:
    """合 SPEC Task 1.1「效能基準」之收據樣本（結構；秒數為佔位）：判準 perf_benchmark 之每格一輸入、契約臂＋polars_float64
    各三次與中位數、Polars 慢因剖析。"""
    arms = list(nv.load_contract()["post_ic_arm_values"]["values"]) + [nh.PERF_CANDIDATE_ARM]
    return {"inputs": [{"cell": cid, "arms": {arm: {"reachable": True, "runs_seconds": [3.0, 1.0, 2.0], "median_seconds": 2.0}
                                              for arm in arms}}
                       for cid in nh.criteria_run_cells("perf_benchmark")],
            "polars_profile": {"steps": [{"step": "rank_udf", "seconds": 80.0}, {"step": "zscore", "seconds": 5.0}],
                               "rank_udf_per_column_python_loop": True}}


def test_perf_benchmark_receipt_checker_accepts_valid_receipt() -> None:
    """效能基準收據之內容檢查（D-ICPAGE-ARM 重新呈報所據）：合 SPEC 之樣本無違規。"""
    assert nh.perf_benchmark_receipt_violations(_valid_perf_receipt()) == []


@pytest.mark.parametrize("mutant", ["single_run", "missing_arm", "missing_profiling", "missing_input", "median_wrong",
                                    "unreachable_without_reason"])
def test_mutation_icpage_re_presentation_perf_receipt_content(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R6-P1-04）：重新呈報所據之效能基準收據只一次牆鐘／缺一臂／缺 Polars 慢因剖析／缺一個輸入格／中位數
    不符／不可達臂無理由 ⇒ `icpage_violations`（⑦，經 re_presentation）紅；未變異時同紀錄為綠（對照）。"""
    monkeypatch.setattr(sys.modules[__name__], "_repo_file_exists", lambda rel: rel == _FAKE_PERF_RECEIPT)
    monkeypatch.setattr(sys.modules[__name__], "_perf_receipt_first_commit_date", lambda rel: "2026-10-30")
    receipt = _valid_perf_receipt()
    monkeypatch.setattr(sys.modules[__name__], "_load_perf_receipt", lambda rel: receipt)
    decisions = {"decisions": {"d_icpage_arm": _valid_icpage_record()}}
    assert icpage_violations(decisions) == []
    first = receipt["inputs"][0]["arms"]
    if mutant == "single_run":
        first[nh.PERF_CANDIDATE_ARM] = {"reachable": True, "runs_seconds": [2.0], "median_seconds": 2.0}
    elif mutant == "missing_arm":
        first.pop(sorted(first)[0])
    elif mutant == "missing_profiling":
        receipt.pop("polars_profile")
    elif mutant == "missing_input":
        receipt["inputs"].pop()
    elif mutant == "median_wrong":
        first[nh.PERF_CANDIDATE_ARM]["median_seconds"] = 3.0
    else:
        first[nh.PERF_CANDIDATE_ARM] = {"reachable": False, "unreachable_reason": " "}
    assert any("效能基準收據" in v for v in icpage_violations(decisions))


# ---------------------------------------------------------------------------------------------- 轉換成本缺實測不代補（審查 r6 CODEX-R6-P1-05）

def _icpostleak_registry_branches() -> List[str]:
    """ICPOSTLEAK 契約之非 IC 頁臂分支（registry 系；估時器 `branch_seconds` 之鍵）。不含 assert。"""
    contract = json.loads((REPO / "tests" / "_golden" / "icpostleak" / "contract.json").read_text(encoding="utf-8"))
    return [b for b in contract["branches"] if b not in ESTIMATOR.BRANCH_ARM]


@pytest.mark.parametrize("mutant", ["drop_contract_arm", "drop_registry_branch", "drop_candidate_proxy_arm"])
def test_mutation_estimate_missing_arm_invalidates_receipt(mutant: str) -> None:
    """mutation：某格之實測缺一個契約臂／缺一個 registry 系分支／缺候選臂之代理臂（polars）⇒ 估時器不以中位數／最大值代補：
    該列標 incomplete、收據列入 `incomplete`，估時收據檢查拒收；未變異時同收據無此違規（對照）。"""
    criteria = _load_criteria()
    inventory = ESTIMATOR.kline_inventory(nh.KLINE_PATH)
    cells = ESTIMATOR.enumerate_cells(nh.KLINE_PATH)
    arms = nv.load_contract()["post_ic_arm_values"]["values"]

    def receipt_for(measurements: Mapping[str, Any]) -> Dict[str, Any]:
        body = ESTIMATOR.build_receipt(cells, inventory, criteria, measurements, arms)
        return json.loads(json.dumps({"reported_at": "2026-10-22T00:00:00+08:00", "cells": cells, **body}))

    measurements = _synthetic_measurements(inventory, cells)
    assert not any("估時不完整" in v for v in closed_estimate_receipt_violations(receipt_for(measurements), _kline_index()))
    target = measurements["A_BTCUSDT_1h"]
    if mutant == "drop_contract_arm":
        target["arm_seconds"].pop("pandas_legacy")
    elif mutant == "drop_registry_branch":
        target["branch_seconds"].pop(_icpostleak_registry_branches()[0])
    else:
        target["arm_seconds"].pop(ESTIMATOR.CANDIDATE_BRANCH_ARM)
    mutated = receipt_for(measurements)
    assert any(item.endswith(":A_BTCUSDT_1h") for item in mutated["incomplete"]), mutated["incomplete"]
    assert any("估時不完整" in v for v in closed_estimate_receipt_violations(mutated, _kline_index()))
    # 成本函式本身亦不代補：缺臂 ⇒ perf／branchdiff 回 None（registry 分支缺只影響 branchdiff）
    if mutant == "drop_registry_branch":
        assert ESTIMATOR.branchdiff_seconds(target["arm_seconds"], target["branch_seconds"]) is None
    else:
        assert ESTIMATOR.perf_seconds(target["arm_seconds"], list(arms)) is None


# ---------------------------------------------------------------------------------------------- 批次快取鍵（審查 r6 CODEX-R6-P1-01）

def test_regen_cache_key_binds_datasets_and_seam_state() -> None:
    """批次共用生成快取鍵之組成含格描述子、env、產品碼態、生成接縫碼態與格之 K 線資料集紀錄；每格之資料集 sha256 等於估時器
    `dataset_record`（同一定義：dtype 描述＋C 連續位元組），來源依判準 kline_source。"""
    criteria = _load_criteria()
    for cell in _closed_cells():
        payload = nh.regen_cache_key_payload(cell)
        assert set(payload) == {"cell", "env", "code_state", "seam_state", "datasets"}, sorted(payload)
        source = ESTIMATOR.cell_source(cell, criteria)
        for tf in cell["timeframes"]:
            want = ESTIMATOR.dataset_record(source, cell["symbol"], tf)["dataset_sha256"]
            assert payload["datasets"][tf]["dataset_sha256"] == want, (cell["id"], tf)


@pytest.mark.parametrize("mutant", ["dataset_changed", "seam_file_changed", "code_state_changed", "env_changed"])
def test_mutation_regen_cache_key_miss_on_dataset_or_seam_change(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R6-P1-01）：格之 K 線資料集改變／生成接縫檔（凍結腳本）改變／產品碼態改變／env 改變 ⇒ 快取鍵改變
    （不命中、須重生）；未變異時同格同 env 之鍵不變（對照）。"""
    cell = next(c for c in _closed_cells() if c["id"] == "A_BTCUSDT_12h")
    base = nh.regen_cache_key(cell)
    assert nh.regen_cache_key(cell) == base
    env = None
    if mutant == "dataset_changed":
        monkeypatch.setattr(nh, "kline_dataset_sha256", lambda *a, **k: "0" * 64)
    elif mutant == "seam_file_changed":
        real = nh._read_bytes
        monkeypatch.setattr(nh, "_read_bytes", lambda p: real(p) + (b"\n# mutant" if Path(p).name == "numview_freeze_baseline.py"
                                                                      else b""))
    elif mutant == "code_state_changed":
        monkeypatch.setattr(nh, "code_state_sha256", lambda: "f" * 64)
    else:
        env = {"FFACT_USE_POLARS": "0"}
    assert nh.regen_cache_key(cell, env) != base


# ---------------------------------------------------------------------------------------------- b4 mutant 生成之估時（審查 r6 CODEX-R6-P1-02）

CORE_TEST_PATH = REPO / "tests" / "feature_engineering" / "test_numview_core.py"


def _read_core_source() -> str:
    return CORE_TEST_PATH.read_text(encoding="utf-8")


def core_patched_generation_tests(source: str) -> Set[str]:
    """`test_numview_core.py` 中以 patch（mutant／故障注入）真實生成之測試：其本體呼叫 `_generate(..., patches=...)`（AST）。
    不含 assert。"""
    out: Set[str] = set()
    for fn in ast.parse(source).body:
        if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_"):
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_generate"
                        and any(k.arg == "patches" for k in node.keywords)):
                    out.add(fn.name)
    return out


def mutant_rows_violations(criteria: Mapping[str, Any], source: str) -> List[str]:
    """判準 `run_coverage.regen_b4_mutants` 之列＝核心測試之 patch 生成測試（逐支一列，`mutation_test` 指名）；每列 generations≥1、
    covers_ids 為 `mutation.*`。不含 assert。"""
    rows = (criteria.get("run_coverage") or {}).get("regen_b4_mutants", {}).get("runs") or []
    listed = {str(r.get("mutation_test", "")).rpartition("::")[2] for r in rows}
    want = core_patched_generation_tests(source)
    out = [f"核心 patch 生成測試未列估時：{sorted(want - listed)}"] if want - listed else []
    out += [f"估時列之 mutation_test 不存在：{sorted(listed - want)}"] if listed - want else []
    for r in rows:
        if not int(r.get("generations") or 0) or not all(str(i).startswith("mutation.") for i in r.get("covers_ids") or [""]):
            out.append(f"{r.get('variant')}：generations／covers_ids 不合")
    return out


def test_estimate_b4_mutant_generations_listed_and_costed() -> None:
    """b4 之 mutant／故障注入生成逐支列於 `regen_b4_mutants`（＝核心測試 AST 列舉之 patch 生成，最壞情形全部決定分支），且估時
    收據逐列計秒（>0）並載 `mutation_test`。"""
    criteria = _load_criteria()
    assert mutant_rows_violations(criteria, _read_core_source()) == []
    inventory = ESTIMATOR.kline_inventory(nh.KLINE_PATH)
    cells = ESTIMATOR.enumerate_cells(nh.KLINE_PATH)
    body = ESTIMATOR.build_receipt(cells, inventory, criteria, _synthetic_measurements(inventory, cells),
                                   nv.load_contract()["post_ic_arm_values"]["values"])
    rows = body["run_kinds"]["regen_b4_mutants"]["runs"]
    assert rows and all(r["seconds"] > 0 and r.get("mutation_test") for r in rows), rows
    assert body["run_kinds"]["regen_b4_mutants"]["extrapolated_total_seconds"] > 0


def test_mutation_estimate_unlisted_core_patched_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：核心測試新增一支 patch 生成測試而判準未列 ⇒ 檢查紅（經 `_read_core_source` 注入）。"""
    assert mutant_rows_violations(_load_criteria(), _read_core_source()) == []
    extra = ("\n\ndef test_mutation_numview_unlisted(tmp_path):\n"
             "    run = _generate(tmp_path, 'B', _cells('B')[0], patches=[lambda mp, run: None])\n")
    monkeypatch.setattr(sys.modules[__name__], "_read_core_source", lambda: CORE_TEST_PATH.read_text(encoding="utf-8") + extra)
    assert any("未列估時" in v for v in mutant_rows_violations(_load_criteria(), _read_core_source()))


# ---------------------------------------------------------------------------------------------- 卡住偵測（使用者 2026-10-22；判準 v6 cell_rules.watchdog）
# 秒級：以極小門檻與不寫 log／持續寫 log 之假子行程驗三條件；不生成特徵。

_SILENT_CHILD = [sys.executable, "-c", "import time; time.sleep(20)"]
_CHATTY_CHILD = [sys.executable, "-u", "-c", "import time\nfor i in range(400):\n    print(i, flush=True); time.sleep(0.05)"]


def _fast_config(**overrides: Any) -> Any:
    wd = ESTIMATOR.watchdog_module()
    base = {"check_interval_seconds": 0.05, "log_stall_seconds": 0.4, "swap_growth_fraction_of_ram": 0.125,
            "swap_consecutive_checks": 2, "wall_multiple_of_expected": 3.0, "wall_ceiling_seconds": 30.0}
    return wd.WatchdogConfig(**{**base, **overrides})


def test_watchdog_thresholds_come_from_criteria_and_estimator_uses_it() -> None:
    """門檻唯一來源＝判準 `cell_rules.watchdog`（封閉物件）；估時器之子行程實測經 `_watchdog.run_watched`（預設開）。"""
    wd = ESTIMATOR.watchdog_module()
    config = wd.load_config(_load_criteria())
    node = _load_criteria()["cell_rules"]["watchdog"]
    assert all(getattr(config, k) == node[k] for k in wd.WATCHDOG_KEYS)
    assert "run_watched" in inspect.getsource(ESTIMATOR._run_target)
    assert wd.ENABLED is True


def test_watchdog_silent_child_stalled(tmp_path: Path) -> None:
    """(a) 子行程 log 未增長逾門檻 ⇒ stalled（理由具名 log）並終止子行程。"""
    wd = ESTIMATOR.watchdog_module()
    result = wd.run_watched(_SILENT_CHILD, log_path=tmp_path / "silent.log", config=_fast_config(), probe_swap=lambda: 0.0)
    assert result.status == wd.STALLED and "log" in result.reason, result
    assert result.wall_seconds < 15


def test_watchdog_wall_cap_stalled(tmp_path: Path) -> None:
    """(c) 持續寫 log 但牆鐘逾上限（有預期 ⇒ 3×預期；此處預期 0.2 秒 ⇒ 上限 0.6 秒）⇒ stalled（理由具名牆鐘）。"""
    wd = ESTIMATOR.watchdog_module()
    result = wd.run_watched(_CHATTY_CHILD, log_path=tmp_path / "wall.log", config=_fast_config(log_stall_seconds=30.0),
                            expected_seconds=0.2, probe_swap=lambda: 0.0)
    assert result.status == wd.STALLED and "牆鐘" in result.reason, result


def test_watchdog_swap_over_threshold_stalled(tmp_path: Path) -> None:
    """(b) swap 已用量（注入，MB）自啟動基線增長 > 門檻連續 2 次 ⇒ stalled（理由具名 swap）；子行程持續寫 log、牆鐘未逾。"""
    wd = ESTIMATOR.watchdog_module()
    readings = iter([6000.0] + [9000.0] * 100000)
    result = wd.run_watched(_CHATTY_CHILD, log_path=tmp_path / "swap.log", config=_fast_config(log_stall_seconds=30.0),
                            probe_swap=lambda: next(readings), probe_ram=lambda: 8000.0)
    assert result.status == wd.STALLED and "swap" in result.reason, result
    assert result.swap_growth_threshold_mb == 1000.0 and result.swap_growth_max_mb == 3000.0, result


def test_watchdog_high_preexisting_swap_not_stalled(tmp_path: Path) -> None:
    """回歸（2026-10-22 判準 v4 誤殺）：系統既有 swap 高（注入恆 7000 MB，相當 8 GB 之 85%）而本跑未增長 ⇒ 不判 stalled、正常
    結束；`swap_growth_max_mb` 記 0。"""
    wd = ESTIMATOR.watchdog_module()
    result = wd.run_watched([sys.executable, "-c", "import time; print('a', flush=True); time.sleep(0.2); print('b')"],
                            log_path=tmp_path / "hi.log", config=_fast_config(), probe_swap=lambda: 7000.0,
                            probe_ram=lambda: 8000.0)
    assert result.status == wd.EXITED and result.returncode == 0, result
    assert result.swap_growth_max_mb == 0.0, result


_SHORT_CHATTY_CHILD = [sys.executable, "-u", "-c", "import time\nfor i in range(8):\n    print(i, flush=True); time.sleep(0.05)"]


@pytest.mark.parametrize("ram_mb, expect_stalled", [(8000.0, True), (32000.0, False)])
def test_watchdog_swap_threshold_scales_with_physical_memory(tmp_path: Path, ram_mb: float, expect_stalled: bool) -> None:
    """跨記憶體級距（CLAUDE.md Optimization Priority 1）：同一 swap 增長 3000 MB，實體 8000 MB（門檻 1000）⇒ stalled；
    實體 32000 MB（門檻 4000）⇒ 正常結束。"""
    wd = ESTIMATOR.watchdog_module()
    readings = iter([6000.0] + [9000.0] * 100000)
    result = wd.run_watched(_SHORT_CHATTY_CHILD, log_path=tmp_path / "tier.log", config=_fast_config(log_stall_seconds=30.0),
                            probe_swap=lambda: next(readings), probe_ram=lambda: ram_mb)
    assert (result.status == wd.STALLED) is expect_stalled, result
    assert result.swap_growth_threshold_mb == 0.125 * ram_mb, result


def test_watchdog_swap_condition_disabled_records_growth_only(tmp_path: Path) -> None:
    """判準 v6：`swap_growth_fraction_of_ram`＝None ⇒ swap 大增（注入 6000→9000 MB）不終止、門檻 None，仍記
    `swap_growth_max_mb`＝3000；現行判準確為停用。"""
    wd = ESTIMATOR.watchdog_module()
    assert wd.load_config(_load_criteria()).swap_growth_fraction_of_ram is None
    readings = iter([6000.0] + [9000.0] * 100000)
    result = wd.run_watched(_SHORT_CHATTY_CHILD, log_path=tmp_path / "off.log",
                            config=_fast_config(log_stall_seconds=30.0, swap_growth_fraction_of_ram=None),
                            probe_swap=lambda: next(readings), probe_ram=lambda: 8000.0)
    assert result.status == wd.EXITED and result.swap_growth_threshold_mb is None, result
    assert result.swap_growth_max_mb == 3000.0, result


def test_watchdog_physical_memory_unreadable_skips_swap_condition(tmp_path: Path) -> None:
    """實體記憶體讀不到 ⇒ 本跑不判 swap 條件（門檻 None）：swap 大增仍不以 swap 終止，子行程正常結束；(a)(c) 另有測試。"""
    wd = ESTIMATOR.watchdog_module()
    readings = iter([6000.0] + [9000.0] * 100000)
    result = wd.run_watched(_SHORT_CHATTY_CHILD, log_path=tmp_path / "noram.log", config=_fast_config(log_stall_seconds=30.0),
                            probe_swap=lambda: next(readings), probe_ram=lambda: None)
    assert result.status == wd.EXITED and result.swap_growth_threshold_mb is None, result


class _FakeCompleted:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


class _FakePath:
    text: Optional[str] = None

    def __init__(self, *_a: Any) -> None:
        pass

    def read_text(self, encoding: str = "utf-8") -> str:
        if _FakePath.text is None:
            raise OSError("unreadable")
        return _FakePath.text


@pytest.mark.parametrize("system, source, want_swap, want_ram", [
    ("Darwin", {"vm.swapusage": "total = 8192.00M  used = 6955.44M  free = 1236.56M  (encrypted)\n",
                "hw.memsize": "8589934592\n"}, 6955.44, 8192.0),
    ("Darwin", {"vm.swapusage": "garbage\n", "hw.memsize": "n/a\n"}, None, None),
    ("Linux", "MemTotal:       16384000 kB\nSwapTotal:       4194304 kB\nSwapFree:        1048576 kB\n", 3072.0, 16000.0),
    ("Linux", None, None, None),
    ("Linux", "MemTotal: x\n", None, None),
])
def test_watchdog_platform_probes_parse_fixed_samples(monkeypatch: pytest.MonkeyPatch, system: str, source: Any,
                                                      want_swap: Optional[float], want_ram: Optional[float]) -> None:
    """swap 已用量與實體記憶體探測之平台解析（固定樣本，不讀本機）：macOS `sysctl -n vm.swapusage`／`hw.memsize`、Linux
    `/proc/meminfo`；格式不符或讀不到 ⇒ None（該次不計）。"""
    wd = ESTIMATOR.watchdog_module()
    monkeypatch.setattr(wd.platform, "system", lambda: system)
    if system == "Darwin":
        monkeypatch.setattr(wd.subprocess, "run", lambda cmd, **k: _FakeCompleted(source[cmd[-1]]))
    else:
        monkeypatch.setattr(_FakePath, "text", source)
        monkeypatch.setattr(wd, "Path", _FakePath)
    assert wd.swap_used_mb() == want_swap
    assert wd.physical_memory_mb() == want_ram


def test_watchdog_normal_child_exits(tmp_path: Path) -> None:
    """對照：正常結束之子行程 ⇒ exited、rc 0（不誤殺）。"""
    wd = ESTIMATOR.watchdog_module()
    result = wd.run_watched([sys.executable, "-c", "print('ok')"], log_path=tmp_path / "ok.log", config=_fast_config(),
                            probe_swap=lambda: 0.0)
    assert result.status == wd.EXITED and result.returncode == 0, result


def test_watchdog_swap_probe_parses_platform_source() -> None:
    """swap 探測回 None 或 [0, 1] 之比例（macOS sysctl vm.swapusage／Linux /proc/meminfo；讀不到 ⇒ None 不計）。"""
    frac = ESTIMATOR.watchdog_module().swap_used_fraction()
    assert frac is None or 0.0 <= frac <= 1.0, frac


def test_mutation_watchdog_disabled_stall_undetected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutation：關閉卡住偵測（`_watchdog.ENABLED=False`）⇒ 不寫 log 之子行程不再被判 stalled（偵測案紅）。子行程 1.5 秒後自行
    結束以免測試掛住。"""
    wd = ESTIMATOR.watchdog_module()
    child = [sys.executable, "-c", "import time; time.sleep(1.5)"]
    assert wd.run_watched(child, log_path=tmp_path / "a.log", config=_fast_config(),
                          probe_swap=lambda: 0.0).status == wd.STALLED
    monkeypatch.setattr(wd, "ENABLED", False)
    assert wd.run_watched(child, log_path=tmp_path / "b.log", config=_fast_config(),
                          probe_swap=lambda: 0.0).status != wd.STALLED


def test_estimate_stalled_target_fails_fast_without_receipt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """估時器 fail-fast：某目標之子行程判 stalled ⇒ 停止後續目標、rc≠0、不寫收據（實測以注入之 stalled 結果代替，不生成）。"""
    wd = ESTIMATOR.watchdog_module()
    calls: List[str] = []

    def fake_run(target: Mapping[str, Any], *a: Any, **k: Any) -> Dict[str, Any]:
        calls.append(str(target["target"]))
        return {"target": target["target"], "category": target["category"], "status": wd.STALLED,
                "error": "卡住偵測終止：注入", "child_wall_seconds": 1.0}

    monkeypatch.setattr(ESTIMATOR, "_run_target", fake_run)
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    rc = ESTIMATOR.main(["--work-root", str(tmp_path / "work"), "--receipts-dir", str(receipts),
                         "--targets", "A_BTCUSDT_1h,A_BTCUSDT_4h", "--remeasure"])
    assert rc != 0
    assert calls == ["A_BTCUSDT_1h"], calls
    assert not list(receipts.glob("*-numview-estimate.json"))


@pytest.mark.parametrize("mutant", ["c_claims_s5", "ic_first_cell_drops_s5", "segments_missing"])
def test_mutation_estimate_precision_segments_follow_generation_entry(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（審查 r8 GROK-R8-P1-01）：精度鏈讀取列之 segments——只生成之格 C 宣稱 S5／IC-first 之格缺 S5／缺 segments 欄
    ⇒ 估時器 `coverage_violations` 紅；未變異時為零違規（對照；判準 v4：C＝S0–S4、A／B＝S0–S5）。"""
    criteria = copy.deepcopy(_load_criteria())
    monkeypatch.setattr(ESTIMATOR, "load_criteria", lambda *_a, **_k: criteria)
    assert ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria()) == []
    reads = {r["cell"]: r for r in criteria["run_coverage"]["precision_chain"]["runs"] if not r.get("generations")}
    if mutant == "c_claims_s5":
        reads["C_BTCUSDT_1h"]["segments"] = ["S0", "S1", "S2", "S3", "S4", "S5"]
    elif mutant == "ic_first_cell_drops_s5":
        reads["A_BTCUSDT_1h"]["segments"] = ["S0", "S1", "S2", "S3", "S4"]
    else:
        reads["B_BTCUSDT_1h_4h"].pop("segments")
    assert any("precision_chain" in v for v in ESTIMATOR.coverage_violations(ESTIMATOR.load_criteria()))


# ---------------------------------------------------------------------------------------------- 重型腳本之卡住偵測接線（審查 r8 CODEX-R8-P1-02）
# 凍結腳本與每支 SPEC 點名之生成型探針：生成一律於子行程（模組函式 `_child`，由 main 以子行程啟動）內執行，且 main 啟動該
# 子行程一律經 `_watchdog.run_watched`（判準 cell_rules.watchdog）。AST、秒級；未實作前為紅。

WATCHDOG_CHILD_ENTRY = "_child"


def watchdog_wiring_violations_for(rel: str, source: str) -> List[str]:
    """單一腳本：①具子行程入口 `_child`；② main 之呼叫閉包（不進入 `_child`）無任何生成呼叫（main 不在本行程生成；與 `_child`
    共用之 helper 亦計入，不以差集抵消——審查 r9 CODEX-R9-P1-01）；③ 同閉包含 `run_watched` 呼叫且其引數引用 `__file__`
    （子行程經卡住偵測啟動本腳本），並於同閉包呼叫 `_child`（子行程分派入口，比照 estimate.py）；④ 生成呼叫只出現於 `_child`
    之呼叫閉包。不含 assert。"""
    tree = ast.parse(source, filename=rel)
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if "main" not in funcs:
        return [f"{rel}：無主入口 main"]
    out: List[str] = []
    if WATCHDOG_CHILD_ENTRY not in funcs:
        out.append(f"{rel}：無子行程入口 {WATCHDOG_CHILD_ENTRY}（生成須於受監看之子行程內執行）")

    def closure(start: str, skip: Set[str]) -> Set[str]:
        seen, stack = set(), [start]
        while stack:
            name = stack.pop()
            if name in seen or name in skip or name not in funcs:
                continue
            seen.add(name)
            stack += [c.func.id for c in ast.walk(funcs[name]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        return seen

    main_side = closure("main", {WATCHDOG_CHILD_ENTRY})
    child_side = closure(WATCHDOG_CHILD_ENTRY, set()) if WATCHDOG_CHILD_ENTRY in funcs else set()
    calls_in = lambda names: [c for n in names for c in ast.walk(funcs[n]) if isinstance(c, ast.Call)]  # noqa: E731
    direct = sorted({f"{_call_name(c)}@{c.lineno}" for c in calls_in(main_side) if _is_generation_call(c)})
    if direct:
        out.append(f"{rel}：main 之呼叫閉包於本行程生成（未經受監看子行程）：{direct[:3]}")
    watched = [c for c in calls_in(main_side) if _call_name(c) == "run_watched"]
    if not watched:
        out.append(f"{rel}：main 之呼叫閉包未經 _watchdog.run_watched 啟動生成子行程")
    elif not any(isinstance(n, ast.Name) and n.id == "__file__" for c in watched for a in c.args for n in ast.walk(a)):
        out.append(f"{rel}：run_watched 之子行程命令未指向本腳本（引數未引用 __file__）")
    if WATCHDOG_CHILD_ENTRY in funcs and not any(_call_name(c) == WATCHDOG_CHILD_ENTRY for c in calls_in(main_side)):
        out.append(f"{rel}：main 未分派子行程入口 {WATCHDOG_CHILD_ENTRY}（子行程命令無從到達生成入口）")
    stray = sorted({f"{_call_name(c)}@{c.lineno}" for c in calls_in(set(funcs) - child_side - {"main"})
                    if _is_generation_call(c)} - {d for d in direct})
    if stray and not child_side:
        out.append(f"{rel}：生成呼叫 {stray[:3]} 不在任何受監看之子行程入口內")
    return out


def watchdog_wiring_violations() -> List[str]:
    out: List[str] = []
    for path in MANDATED_GATED_SCRIPTS:
        out += watchdog_wiring_violations_for(_rel(path), _read_text(path))
    return out


def test_heavy_scripts_run_generation_children_under_watchdog() -> None:
    """凍結腳本與生成型探針（postic_branchdiff、precision_chain、l2_arm_matrix）之生成子行程一律經 `_watchdog.run_watched`
    （預設開；判準 cell_rules.watchdog）。未實作（空殼 NotImplementedError）前為紅。"""
    assert watchdog_wiring_violations() == []


_WIRED_SOURCE = '''
def _generate(spec_path):
    return generate_features(spec_path)


def _child(spec_path):
    return _generate(spec_path)


def main(argv=None):
    args = parse_args(argv)
    if args.measure_one:
        return _child(args.measure_one)
    require("freeze_baseline", ["A"])
    result = _watchdog.run_watched([sys.executable, str(Path(__file__).resolve()), "--measure-one", "s.json"],
                                   log_path="l", config=None)
    return 0
'''


@pytest.mark.parametrize("mutant", ["direct_generation_in_main", "no_run_watched", "no_child_entry",
                                    "shared_helper_generation_in_main", "watched_cmd_not_this_script",
                                    "main_never_dispatches_child"])
def test_mutation_heavy_script_generation_bypasses_watchdog(mutant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（CODEX-R8-P1-02、CODEX-R9-P1-01）：main 於本行程直接生成／main 未經 run_watched／無子行程入口／main 呼叫與
    `_child` 共用之生成 helper／run_watched 命令不指向本腳本／main 不分派 `_child` ⇒ 接線檢查紅；合規樣本為綠（對照）。
    樣本經 `_read_text` 注入（不改真實腳本）。"""
    target = next(iter(MANDATED_GATED_SCRIPTS))
    monkeypatch.setattr(sys.modules[__name__], "_read_text", lambda path: _WIRED_SOURCE)
    assert watchdog_wiring_violations_for(_rel(target), _read_text(target)) == []
    if mutant == "direct_generation_in_main":
        bad = _WIRED_SOURCE.replace('    return 0\n', '    generate_features("in-process")\n    return 0\n')
    elif mutant == "no_run_watched":
        bad = _WIRED_SOURCE.replace("_watchdog.run_watched(", "subprocess_run(")
    elif mutant == "shared_helper_generation_in_main":
        bad = _WIRED_SOURCE.replace('    return 0\n', '    _generate("in-process")\n    return 0\n')
    elif mutant == "watched_cmd_not_this_script":
        bad = _WIRED_SOURCE.replace("str(Path(__file__).resolve())", '"other.py"')
    elif mutant == "main_never_dispatches_child":
        bad = _WIRED_SOURCE.replace("        return _child(args.measure_one)\n", "        return 0\n")
    else:
        bad = _WIRED_SOURCE.replace("def _child(spec_path):", "def _worker(spec_path):")
    assert bad != _WIRED_SOURCE
    monkeypatch.setattr(sys.modules[__name__], "_read_text", lambda path: bad)
    assert watchdog_wiring_violations_for(_rel(target), _read_text(target)) != []
