"""NUMVIEW Task 4.1／4.2（docs/NUMVIEW_SPEC.md §C D1／D2／D6／D9、§V oracle ⑤⑪⑭）：數值 fingerprint 解析（純函式）
與寫入端、身分、續跑閘之驗收。

命名分界（SPEC Task 4.1 命令為 `-k resolve`）：Task 4.1 之一切驗證、邊界、mutation 名稱皆含 `resolve`；Task 4.2 之
名稱一律不含該字串（含 `unresolved`、`resolved` 等衍生字）。

Task 4.1 驗證：①契約每個 `value_affecting` 選擇子改值 ⇒ `algorithm_id` 與 `config_hash_salt` 皆變（參數化自契約；
契約空即紅）；②契約無 `non_value` 鍵（另驗 `output_only` 五鍵改值兩者皆不變）；③函式庫版本 monkeypatch ⇒
`algorithm_id` 變、鹽不變（另以 `importlib.metadata` 獨立比對版本段）；④能力旗標變 ⇒ 兩者皆變；⑤同輸入同結果；
⑥跨硬體：`FFACT_MEMORY_TIER` 未設、monkeypatch `psutil.virtual_memory().total` 落於 `hardware_utils.TIER_THRESHOLDS`
每一級及各門檻兩側 ⇒ `get_tier_config` 導出值或 slow-path 自動判定不同之兩點身分必不同、相同者必相同；環境明設
各 tier 與同級 auto 一致；⑦psutil 不可用或查詢拋錯而 tier 為 auto ⇒ `NumericContextUnresolvedError`；
⑧AST：三檔中讀 psutil 或 tier 之函式 ⊆ 契約 `auto_resolutions.items` 登記之解析函式；⑨路由身分純函式與換臂點
AST 集合＝契約登記；⑩標記寫入失敗自 `route()` 拋出、換臂後 branch 零次、檔案集合不變；量測失敗照舊容錯且標記已寫；
另：`FFACT_USE_POLARS=1` 而 Polars 不可用 ⇒ 記有效值（與 `=0` 同身分）。
Task 4.1 邊界（全域編號）：40 環境未設＝契約預設＝`memory_budget.SELECTOR_DEFAULTS`；41 非法環境值記退回後有效值
＋`invalid_env` 標記；42 實體 RAM 恰等於門檻；43 未認證換臂照舊換臂並入路由身分；44 同一換臂點多次觸發逐次記錄；
45 未認證換臂後崩潰 ⇒ 標記已在、下一 run 不續跑；46 標記寫入失敗（唯讀目錄）⇒ `route()` 拋出、branch 未執行；
47 量測失敗容錯、照常換臂並寫標記。
Task 4.1 mutation：鹽刪一個 value_affecting 鍵；有效值記原始字串；fingerprint 不反映解析後 tier；psutil 不可用
靜默 8gb；新增讀 psutil 函式未登記；路由身分刪所選臂；略過未認證點；未登記之新換臂點；標記回呼例外被吞；
量測失敗亦拋出。

Task 4.2 驗證（⑦ 另見 `test_numview_cgsa_workdir.py`、⑤ 屬重凍收據）：①真實短窗 manifest 頂層與 artifact 節點帶
fingerprint、`algorithm_id`，fingerprint 等於以 Task 4.1 函式依該 run 之設定／環境／能力重算者，`algorithm_id`
等於測試端獨立計算之正規 JSON sha256；②`FFACT_USE_POLARS` 0／1 ⇒ 不同 `config_hash` 目錄、不互相覆寫；
③函式庫版本 monkeypatch ⇒ 同 `config_hash`、續跑被拒（葉不同；葉同而 L7 manifest `algorithm_id` 不同亦拒）、
IC ingest 快取重建；④§G 值指紋逐位元（一格，`h1_stat_off` 對沿用基準；全格在 `test_numview_acceptance.py`）；
⑥倖存者契約升版且 `ff_run_identity` 內層遞迴驗證（`{}`／缺 `algorithm_id`／多未知鍵拒收、null 通過、舊版 3 拒收）；
⑧路由身分整合（未認證換臂照常完成且身分不同、IC ingest 快取不沿用；已認證換臂身分同未換臂；未認證換臂後崩潰
重跑不續跑且新 registry 建立前零讀；只已認證換臂崩潰後續跑；續跑後換臂等同未中斷且 §G 逐位元相等）；
另驗 RunIdentity 欄＝契約鍵、`CACHE_IDENTITY_FIELDS` 擴充不放寬。
Task 4.2 邊界：48 舊 run（無新鍵）讀特徵不受影響、IC 快取不沿用；49 IC-first 已刪 raw 之 processed 節點身分。
Task 4.2 mutation：路由身分刪所選臂；未認證換臂點改拋錯；含標記目錄被續跑；標記延至完成才寫；續跑閘先讀 manifest
再查標記；已認證換臂亦寫標記；IC 快取比對略過路由身分；續跑後換臂漏記本 run 換臂；續跑閘不比 `algorithm_id`；
RunIdentity 漏新鍵；`_check_object` 不遞迴；倖存者契約版本不升。
（`tests/momentum/Analysis/test_survivor_contract.py:56`、`:176`、`:190` 之 `version == 3` 字面須於實作時改讀契約常數，
依 2026-10-17 裁定同提交登記審清單；本檔不改該檔。）

測試接縫（實作須提供；名稱為本檔所定，見報告）：
- `numeric_view.library_version(name: str) -> str`：函式庫版本之唯一讀取點（內部讀 `importlib.metadata.version`），
  `resolve_numeric_fingerprint` 經模組屬性呼叫之（測試以 monkeypatch 改版本字串）。
- `numeric_view.resolve_numeric_fingerprint`：硬體自動解析一律於呼叫時經 `hardware_utils._psutil`／`import psutil`
  （不得於模組載入時自持 psutil 參照；若有 `_psutil` 屬性測試一併置換）；有效 Polars 取 `capabilities` 之 Polars 旗標
  與 `polars_adapter._polars_available`；選擇子有效值於 fingerprint 中以環境鍵名（如 `FFACT_LAYER1_PARALLEL`）為鍵。
- `memory_budget.set_route_switch_marker(callback)`：context manager；作用期間 `route()` 於未認證換臂點選定換臂後、
  `return` 前呼叫 `callback(entry)`（例外原樣上拋）；認證與否讀 `numeric_view.load_contract()` 之
  `auto_resolutions.route_switch_points[<點>]["certified"]`（未登記之點視同未認證）；登記以 contextvar 為之。
- `memory_budget.route(point, candidates, *, label=None, scale_key=None, group=None)`：`group` 記入紀錄之 `group` 鍵。
- `run_paths.write_route_switch_marker(work_dir: Path, entry: Mapping) -> Path`：原子寫契約 `cgsa_work_identity.marker_file`
  （JSON，含 `marker_keys`）。
- `run_paths.cgsa_config_layer_dir(root, symbol, timeframe, config_hash) -> Path`、
  `run_paths.cgsa_work_dir(root, symbol, timeframe, config_hash, algorithm_id) -> Path`；
  `FeatureFactory._prepare_cgsa_registry(symbol, timeframe, config_hash="", algorithm_id="")`（續跑閘：身分檔、標記檔、
  L7 manifest `algorithm_id`）。
- 契約鍵（本檔讀取）：`selectors[*].{class,default,domain}`、`selector_classes.output_only_keys`、`capability_flags`、
  `library_versions`、`fingerprint_sections`、`config_hash_salt.exclude_sections`、`auto_resolutions.{items[*].function
  (格式 `<repo 相對路徑>::<qualname>`), route_switch_points[*].certified, route_identity_key, route_identity_empty,
  unresolved_error}`、`cgsa_work_identity.{identity_file, identity_keys, marker_file, marker_keys}`、
  `manifest_keys.{fingerprint, algorithm_id, observed_arms}`（角色→鍵名；頂層與 artifact 節點同名）、`run_identity_new_keys`。

資料：Task 4.1 為純函式（秒級；不讀特徵資料）；Task 4.2 一律真實 kline 短窗（`preprov_helpers`，格 `h1_stat_off`、
`ic_first`），每個生成於模組範圍只做一次；本檔各隔離根共用同一 registry 路徑（`FFACT_FEATURE_REGISTRY_PATH` 於 SPEC
v44 前屬 value_affecting 時所需；v44 起屬 output_only，共用無害）。重型：單行程串行。
實作前應為紅（契約未填、`numeric_view` 為 NotImplementedError、接縫未建）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import builtins
import contextvars
import copy
import dataclasses
import errno
import hashlib
import importlib.metadata
import io
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Set, Tuple
from unittest.mock import Mock

import h5py
import pytest

from momentum.Analysis import ic_engine as ice
from momentum.Analysis import survivor_contract as sc
from momentum.Analysis.ic_config_schema import ContractValidationError
from momentum.core import config as core_config
from momentum.FeatureEngineering import memory_budget as mb
from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering import polars_adapter
from momentum.FeatureEngineering import run_paths
from momentum.FeatureEngineering import run_provenance as rp
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import PreprocessingConfig
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.utils import hardware_utils as hw
from tests.feature_engineering import numview_helpers as nh
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(3600)

REPO = Path(__file__).resolve().parents[2]
#: 契約（唯一真相源）直接讀 JSON 供收集期參數化；值一律取自此，不另列值集
RAW: Dict[str, Any] = json.loads(nv.CONTRACT_PATH.read_text(encoding="utf-8"))
RUN_PROV: Dict[str, Any] = json.loads(rp.CONTRACT_PATH.read_text(encoding="utf-8"))
GiB = 1 << 30
EMPTY = "<契約未填>"

#: SPEC 正文點名之環境鍵（使用前一律斷言屬契約 value_affecting）
MEMORY_TIER_KEY = "FFACT_MEMORY_TIER"            # Task 4.1 ⑥
SLOWPATH_KEY = "FFACT_L65_SLOWPATH_PARALLEL"     # Task 4.1 改法（core/config.py:192-232）
USE_POLARS_KEY = "FFACT_USE_POLARS"              # Task 4.1 改法（有效值例）
INVALID_FALLBACK_KEY = "FFACT_L65_OPTIMIZATION_PROFILE"  # Task 4.1 邊界②（core/config.py:24-35）
SALT_PROBE_KEY = "FFACT_LAYER1_PARALLEL"         # mutation 用：memory_budget.SELECTORS 之布林鍵，只屬選擇子段
#: Task 4.1 ⑧ 之掃描範圍（SPEC 點名三檔）
AUTO_FILES: Tuple[str, ...] = (
    "momentum/FeatureEngineering/utils/hardware_utils.py",
    "momentum/core/config.py",
    "momentum/FeatureEngineering/memory_budget.py",
)
MEMORY_BUDGET_FILE = "momentum/FeatureEngineering/memory_budget.py"
FACTORY_FILE = "momentum/FeatureEngineering/feature_factory.py"
#: route 單元案之分支（memory_budget.BRANCH_TABLE 既有 ID；估算以 setitem 注入，同 test_icfirstalign_memory）
ORIG_BRANCH, ALT_BRANCH, ALT2_BRANCH = "L2.polars", "L2.pandas_serial", "L2.pandas_parallel"
#: 單元案暫登於契約之未認證換臂點（只存在於 monkeypatch 之契約副本）
TEST_UNCERT_POINT = "numview_test_uncertified_point"
CELL = "h1_stat_off"
IC_FIRST_CELL = "ic_first"
CACHE_REL = Path("data_cache/reports/ic_ingest_cache")
OLD_NS = 1_600_000_000_000_000_000
#: 改前之 IC-first JSON 快取身分欄（ic_engine.py:39-53）；本票只增不減
HEAD_CACHE_FIELDS = ("symbol", "tf", "config_hash", "method", "label_horizon", "selection_window_start",
                     "selection_window_end", "split_id", "feature_axis_sha256", "label_sha256", "content_sha256")
#: 舊倖存者契約版本（SPEC Task 4.2「現值 3」）
OLD_SURVIVOR_VERSION = 3


class SimulatedCrash(BaseException):
    """模擬行程崩潰：非 `Exception` 子類，不被層執行器之 `except Exception` 吞（Task 4.2 ⑧ 崩潰案）。"""


# ============================================================================================== 契約讀取（fail-closed）

def _real(key: Any) -> bool:
    return not str(key).startswith("_")


def _selectors() -> Dict[str, Mapping[str, Any]]:
    return {k: v for k, v in RAW["selectors"].items() if _real(k) and isinstance(v, Mapping)}


def _value_affecting() -> List[str]:
    return sorted(k for k, v in _selectors().items() if v.get("class") == "value_affecting")


def _output_only() -> List[str]:
    return list(RAW["selector_classes"].get("output_only_keys") or [])


VALUE_AFFECTING_PARAMS: List[str] = _value_affecting() or [EMPTY]
OUTPUT_ONLY_PARAMS: List[str] = _output_only() or [EMPTY]


def _library_section() -> str:
    excluded = list(RAW["config_hash_salt"].get("exclude_sections") or [])
    assert len(excluded) == 1, f"契約 config_hash_salt.exclude_sections 須恰為函式庫版本段一段（設計選擇①），實得 {excluded}"
    assert excluded[0] in RAW["fingerprint_sections"]["values"], "鹽排除段不屬 fingerprint_sections"
    return str(excluded[0])


def _polars_flag() -> str:
    flags = [f for f in RAW["capability_flags"]["values"] if "polars" in f]
    assert len(flags) == 1, f"契約 capability_flags 須恰有一個 Polars 可用性旗標，實得 {flags}"
    return flags[0]


def _route_points_contract() -> Dict[str, Mapping[str, Any]]:
    points = {k: v for k, v in (RAW["auto_resolutions"].get("route_switch_points") or {}).items() if _real(k)}
    assert points, "契約 auto_resolutions.route_switch_points 為空（Task 4.1 未填）"
    return points


def _certified_points() -> List[str]:
    return sorted(p for p, v in _route_points_contract().items() if isinstance(v, Mapping) and v.get("certified") is True)


def _route_key() -> str:
    key = RAW["auto_resolutions"].get("route_identity_key")
    assert isinstance(key, str) and key, "契約 auto_resolutions.route_identity_key 未填（Task 4.1）"
    return key


def _route_empty() -> Any:
    value = RAW["auto_resolutions"].get("route_identity_empty")
    assert value, "契約 auto_resolutions.route_identity_empty 未填（Task 4.1）"
    return value


def _cgsa_identity() -> Mapping[str, Any]:
    section = RAW["cgsa_work_identity"]
    for key in ("identity_file", "marker_file"):
        assert isinstance(section.get(key), str) and section[key], f"契約 cgsa_work_identity.{key} 未填（Task 4.2）"
    return section


def _identity_name() -> str:
    return str(_cgsa_identity()["identity_file"])


def _marker_name() -> str:
    return str(_cgsa_identity()["marker_file"])


def _identity_payload(symbol: str, tf: str, config_hash: str, algorithm_id: str) -> Dict[str, str]:
    """身分檔內容（SPEC D7：symbol、tf、完整 config_hash、完整 algorithm_id）；鍵集須等於契約 identity_keys。"""
    payload = {"symbol": symbol, "tf": tf, "config_hash": config_hash, "algorithm_id": algorithm_id}
    keys = list(_cgsa_identity().get("identity_keys") or [])
    assert set(keys) == set(payload), f"契約 cgsa_work_identity.identity_keys {keys} ≠ SPEC D7 四鍵"
    return payload


def _manifest_keys() -> Dict[str, str]:
    mk = {k: v for k, v in RAW["manifest_keys"].items() if _real(k)}
    for role in ("fingerprint", "algorithm_id", "observed_arms"):
        assert isinstance(mk.get(role), str) and mk[role], f"契約 manifest_keys.{role} 未填（Task 4.2）"
    return mk


def _contract_with(monkeypatch: pytest.MonkeyPatch, mutate: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
    """`numeric_view.load_contract` 改回傳契約副本（套 `mutate`）；回傳該副本。"""
    contract = copy.deepcopy(RAW)
    mutate(contract)
    monkeypatch.setattr(nv, "load_contract", lambda: copy.deepcopy(contract))
    return contract


def _register_point(monkeypatch: pytest.MonkeyPatch, point: str, certified: bool) -> None:
    def mutate(c: Dict[str, Any]) -> None:
        c["auto_resolutions"].setdefault("route_switch_points", {})[point] = {
            "certified": certified, "_doc": "測試暫登（monkeypatch 之契約副本）"}
    _contract_with(monkeypatch, mutate)


# ============================================================================================== 一般工具

def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _independent_algorithm_id(fp: Mapping[str, Any]) -> str:
    """測試端獨立 oracle：fingerprint 正規 JSON（sort_keys、無空白）之 sha256（不經 numeric_view）。"""
    return hashlib.sha256(json.dumps(fp, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _drop_key(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return {k: _drop_key(v, name) for k, v in obj.items() if k != name}
    if isinstance(obj, list):
        return [_drop_key(v, name) for v in obj]
    return obj


def _set_key(obj: Any, name: str, value: Any) -> Any:
    if isinstance(obj, Mapping):
        return {k: (value if k == name else _set_key(v, name, value)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_set_key(v, name, value) for v in obj]
    return obj


def _find_key(obj: Any, name: str) -> List[Any]:
    out: List[Any] = []
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            if k == name:
                out.append(v)
            out.extend(_find_key(v, name))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_find_key(v, name))
    return out


def _files(root: Path) -> Set[str]:
    return {str(p.relative_to(root)) for p in Path(root).rglob("*")}


def _md5(tag: str) -> str:
    return hashlib.md5(tag.encode("utf-8")).hexdigest()


def _sha(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def _kline_cell() -> Tuple[str, str]:
    """真實 kline 之第一個 symbol×tf（自 kline_cache.h5 列舉，不寫死）。"""
    with h5py.File(ph.KLINE_FILE, "r") as f:
        symbols = sorted(f.keys())
        assert symbols, "kline_cache.h5 無 symbol"
        tfs = sorted(f[symbols[0]].keys())
    assert tfs, f"{symbols[0]} 無週期"
    return symbols[0], tfs[0]


def _isolated(fn: Callable[[], Any]) -> Any:
    """於 context 副本內執行（工廠註冊之換臂標記回呼等 contextvar 不外洩至其他測試）。"""
    return contextvars.copy_context().run(fn)


# ============================================================================================== Task 4.1 fixture

PRE: Dict[str, Any] = PreprocessingConfig().model_dump()


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Dict[str, str]]:
    """清空 os.environ 之全部 FFACT_* 後套用 overrides（同時寫 os.environ，因登記之解析函式讀之）；回傳 environ 副本。"""
    def apply(overrides: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        for key in [k for k in os.environ if k.startswith("FFACT_")]:
            monkeypatch.delenv(key)
        for key, value in dict(overrides or {}).items():
            monkeypatch.setenv(key, value)
        return dict(os.environ)
    return apply


def _fake_vm(total: int) -> Callable[[], Any]:
    return lambda: types.SimpleNamespace(total=int(total), available=int(total))


@pytest.fixture()
def ram(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """把 `psutil.virtual_memory().total` 釘為指定位元組（psutil 模組本身之屬性；hardware_utils 與 core.config 皆經之）。"""
    import psutil

    def pin(total: int) -> None:
        monkeypatch.setattr(psutil, "virtual_memory", _fake_vm(total))
        monkeypatch.setattr(hw, "_psutil", psutil)
    return pin


def _psutil_unavailable(mp: pytest.MonkeyPatch) -> None:
    mp.setattr(hw, "_psutil", None)
    mp.setitem(sys.modules, "psutil", None)  # `import psutil` ⇒ ImportError
    if hasattr(nv, "_psutil"):
        mp.setattr(nv, "_psutil", None)


def _psutil_raising(mp: pytest.MonkeyPatch) -> None:
    import psutil

    def boom() -> Any:
        raise OSError(errno.EIO, "numview 注入：virtual_memory 查詢失敗")
    mp.setattr(psutil, "virtual_memory", boom)
    mp.setattr(hw, "_psutil", psutil)


def _caps(**over: bool) -> Dict[str, bool]:
    caps = dict(nv.detect_capabilities())
    caps.update(over)
    return caps


def _fp(environ: Mapping[str, str], caps: Optional[Mapping[str, bool]] = None, *,
        fn: Optional[Callable[..., Dict[str, Any]]] = None) -> Dict[str, Any]:
    resolver = fn or nv.resolve_numeric_fingerprint
    return resolver(preprocessing_config=copy.deepcopy(PRE), environ=dict(environ),
                    capabilities=dict(caps if caps is not None else _caps()))


def _ids(fp: Mapping[str, Any]) -> Tuple[str, str]:
    return nv.algorithm_id(fp), _canon(nv.config_hash_salt(fp))


def _moves(a: Mapping[str, Any], b: Mapping[str, Any]) -> Tuple[bool, bool]:
    """(algorithm_id 是否變, config_hash_salt 是否變)。"""
    ia, ib = _ids(a), _ids(b)
    return ia[0] != ib[0], ia[1] != ib[1]


#: 非 memory_budget.SELECTORS 之鍵：依契約 `domain` 之語彙取一個合法替代值（語彙同 memory_budget.SELECTORS 之
#: "auto|positive_int" 寫法；未知語彙 ⇒ 斷言紅，要求契約補值域）
_DOMAIN_TOKEN_VALUES: Tuple[Tuple[str, str], ...] = (
    ("positive_int", "3"), ("non_negative_int", "3"), ("int", "3"), ("size_bytes", "64MiB"),
    ("ratio", "0.5"), ("float", "0.5"), ("bool", "1"), ("str", "numview_alt"),
)


def _alternative_value(key: str, tmp: Path) -> str:
    """合法且有效值異於預設之替代值。值域優先取碼證（memory_budget.SELECTORS／SELECTOR_DEFAULTS），否則取契約
    `selectors[key].domain`／`default`。清單值域取「≠ 預設且 ≠ auto」之最後一個（RAM 釘 8 GiB 時避開 auto 之解析值）。"""
    entry = _selectors()[key]
    if key in mb.SELECTORS:
        domain: Any = mb.SELECTORS[key]
        default = mb.SELECTOR_DEFAULTS[key]
    else:
        domain, default = entry.get("domain"), entry.get("default")
    assert domain is not None, f"契約 selectors.{key} 無 domain（無從選合法替代值）"
    if isinstance(domain, (list, tuple)):
        cands = [str(v) for v in domain if str(v) != str(default) and str(v) != "auto"]
        assert cands, f"{key} 之值域 {domain} 無異於預設 {default!r} 之合法值"
        return cands[-1]
    tokens = [t.strip() for t in str(domain).split("|")]
    if "path" in tokens:
        return str(tmp / "numview_alt_path")
    for token, value in _DOMAIN_TOKEN_VALUES:
        if token in tokens and value != str(default):
            return value
    raise AssertionError(f"{key} 之 domain {domain!r} 無已知語彙（契約須登記可導出合法值之值域）")


# ============================================================================================== Task 4.1 ①②③④⑤

@pytest.mark.parametrize("key", VALUE_AFFECTING_PARAMS)
def test_resolve_selector_change_moves_algorithm_id_and_salt(key: str, env: Any, ram: Any, tmp_path: Path) -> None:
    """①：契約每個 value_affecting 選擇子改為合法替代值 ⇒ `algorithm_id` 與 `config_hash_salt` 皆變。"""
    assert key in _value_affecting(), "契約 selectors 無 value_affecting 鍵（Task 0.2／4.1 未填）"
    ram(8 * GiB)
    base = _fp(env({}))
    alt = _fp(env({key: _alternative_value(key, tmp_path)}))
    assert _moves(base, alt) == (True, True)


def test_resolve_contract_has_no_non_value_selector() -> None:
    """②：契約中無 `non_value` 鍵（本票不排除）；全部類別屬契約 selector_classes。"""
    sels = _selectors()
    assert sels, "契約 selectors 為空（Task 0.2 未填）"
    assert sorted(k for k, v in sels.items() if v.get("class") == "non_value") == []
    assert {v.get("class") for v in sels.values()} <= set(RAW["selector_classes"]["values"])


@pytest.mark.parametrize("key", OUTPUT_ONLY_PARAMS)
def test_resolve_output_only_key_does_not_move_ids(key: str, env: Any, ram: Any) -> None:
    """②之對照：封閉清單之 output_only 鍵不入鹽與 `algorithm_id`（改值兩者皆不變）。"""
    assert key in _output_only() and _selectors()[key].get("class") == "output_only", \
        "契約 output_only_keys 為空或其類別不符（Task 0.2 未填）"
    ram(8 * GiB)
    assert _moves(_fp(env({})), _fp(env({key: "numview_output_only_alt"}))) == (False, False)


def test_resolve_library_version_moves_algorithm_id_only(env: Any, ram: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """③：函式庫版本段＝`importlib.metadata` 獨立讀得之版本；改版本字串 ⇒ `algorithm_id` 變、鹽不變。"""
    libs = list(RAW["library_versions"]["values"])
    assert libs, "契約 library_versions 為空（Task 4.1 未填）"
    ram(8 * GiB)
    environ = env({})
    base = _fp(environ)
    assert base[_library_section()] == {name: importlib.metadata.version(name) for name in libs}
    real = nv.library_version
    monkeypatch.setattr(nv, "library_version", lambda name: real(name) + ("+numview" if name == libs[0] else ""))
    assert _moves(base, _fp(environ)) == (True, False)


def test_resolve_capability_flag_moves_both(env: Any, ram: Any) -> None:
    """④：任一能力旗標翻轉 ⇒ `algorithm_id` 與鹽皆變。"""
    flags = list(RAW["capability_flags"]["values"])
    assert flags, "契約 capability_flags 為空"
    ram(8 * GiB)
    environ = env({})
    caps = _caps()
    assert set(caps) == set(flags), f"detect_capabilities 之鍵 {sorted(caps)} ≠ 契約 {flags}"
    base = _fp(environ, caps)
    moved = {f: _moves(base, _fp(environ, {**caps, f: not caps[f]})) for f in flags}
    assert moved == {f: (True, True) for f in flags}


def test_resolve_is_deterministic(env: Any, ram: Any) -> None:
    """⑤：同輸入兩次呼叫 ⇒ fingerprint、`algorithm_id`、鹽皆相同；`algorithm_id`＝獨立正規 JSON sha256。"""
    ram(8 * GiB)
    environ = env({})
    a, b = _fp(environ), _fp(environ)
    assert a == b and _ids(a) == _ids(b)
    assert nv.algorithm_id(a) == _independent_algorithm_id(a)


# ---------------------------------------------------------------------------------------------- Polars 有效值

def _polars_effective_case(env: Any, ram: Any, fn: Optional[Callable[..., Any]] = None) -> Dict[bool, bool]:
    """Polars 可用／不可用下，`FFACT_USE_POLARS=1` 與 `=0` 是否同身分（有效值相同 ⇒ True）。"""
    flag = _polars_flag()
    ram(8 * GiB)
    out: Dict[bool, bool] = {}
    for available in (True, False):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(polars_adapter, "_polars_available", available)
            caps = {**_caps(), flag: available}
            on = _ids(_fp(env({USE_POLARS_KEY: "1"}), caps, fn=fn))
            off = _ids(_fp(env({USE_POLARS_KEY: "0"}), caps, fn=fn))
        out[available] = on == off
    return out


def test_resolve_records_effective_polars_when_unavailable(env: Any, ram: Any) -> None:
    """改法（有效值）：Polars 不可用時 `FFACT_USE_POLARS=1` 之有效值＝不用 Polars ⇒ 與 `=0` 同身分；可用時兩者不同。"""
    assert USE_POLARS_KEY in _value_affecting()
    assert _polars_effective_case(env, ram) == {True: False, False: True}


# ---------------------------------------------------------------------------------------------- ⑥ 跨硬體

def _ram_points() -> List[int]:
    positive = [t for t, _tier in hw.TIER_THRESHOLDS if t > 0]
    points = {min(positive) * GiB // 2, max(positive) * GiB * 2}
    for t in positive:
        points.update({t * GiB - 1, t * GiB, t * GiB + 1})
    return sorted(points)


def _expected_tier(total: int) -> str:
    for threshold, tier in hw.TIER_THRESHOLDS:
        if total / GiB >= threshold:
            return tier
    raise AssertionError(f"{total} 不落於任何 tier（TIER_THRESHOLDS 末級須為 0）")


def _tier_partition_violations(ram: Any, env: Any, fn: Optional[Callable[..., Any]] = None) -> List[str]:
    """⑥ 之 oracle：導出值（`get_tier_config(期望 tier)`＋`get_slowpath_parallel_enabled()`）相同之 RAM 點身分必同、
    不同者 `algorithm_id` 與鹽皆須不同。期望 tier 由 `TIER_THRESHOLDS` 獨立判定（`>=`）。"""
    rows: List[Tuple[int, Tuple[str, bool], Tuple[str, str]]] = []
    for total in _ram_points():
        ram(total)
        environ = env({})
        derived = (_canon(hw.get_tier_config(_expected_tier(total))), bool(core_config.get_slowpath_parallel_enabled()))
        rows.append((total, derived, _ids(_fp(environ, fn=fn))))
    out: List[str] = []
    if len({d for _t, d, _i in rows}) < 2:
        out.append("前提不成立：RAM 點之導出值全同")
    for i, (t1, d1, id1) in enumerate(rows):
        for t2, d2, id2 in rows[i + 1:]:
            if d1 == d2 and id1 != id2:
                out.append(f"導出值同而身分不同：{t1} vs {t2}")
            if d1 != d2 and (id1[0] == id2[0] or id1[1] == id2[1]):
                out.append(f"導出值不同而身分（algorithm_id 或鹽）相同：{t1} vs {t2}")
    return out


def test_resolve_cross_hardware_tiers_partition_identity(env: Any, ram: Any) -> None:
    """⑥：`FFACT_MEMORY_TIER` 未設，RAM 落於每一級及每個門檻兩側（12 GB 兩側同時切換 slow-path）⇒ 依導出值分群。"""
    assert MEMORY_TIER_KEY in _value_affecting() and SLOWPATH_KEY in _value_affecting()
    assert _tier_partition_violations(ram, env) == []


def test_resolve_explicit_tier_equals_same_tier_auto(env: Any, ram: Any) -> None:
    """⑥：環境明設每個 tier ＝ 同級 auto 解析（RAM 釘於該級內，slow-path auto 一致）。"""
    positive = [t for t, _tier in hw.TIER_THRESHOLDS if t > 0]
    mismatched: List[str] = []
    for threshold, tier in hw.TIER_THRESHOLDS:
        assert tier in mb.SELECTORS[MEMORY_TIER_KEY]
        ram(threshold * GiB if threshold > 0 else min(positive) * GiB // 2)
        if _ids(_fp(env({}))) != _ids(_fp(env({MEMORY_TIER_KEY: tier}))):
            mismatched.append(tier)
    assert mismatched == []


# ---------------------------------------------------------------------------------------------- ⑦ 不可解析之 auto

def _unresolved_outcomes(env: Any, fn: Optional[Callable[..., Any]] = None) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, inject in (("psutil_unavailable", _psutil_unavailable), ("psutil_raises", _psutil_raising)):
        with pytest.MonkeyPatch.context() as mp:
            inject(mp)
            environ = env({})
            try:
                _fp(environ, fn=fn)
            except nv.NumericContextUnresolvedError:
                out[name] = "rejected"
            else:
                out[name] = "accepted"
    return out


def test_resolve_unresolvable_auto_tier_rejected(env: Any) -> None:
    """⑦：tier 為 auto 而 psutil 不可用或查詢拋錯 ⇒ `NumericContextUnresolvedError`（不以 8gb 代替）；錯誤名登記於契約。"""
    assert RAW["auto_resolutions"].get("unresolved_error") == nv.NumericContextUnresolvedError.__name__
    assert _unresolved_outcomes(env) == {"psutil_unavailable": "rejected", "psutil_raises": "rejected"}


def test_resolve_explicit_tier_without_psutil_accepted(env: Any, ram: Any) -> None:
    """⑦ 之對照（SPEC「提示以環境明設 tier」）：明設 tier 與 slow-path 時 psutil 不可用仍可解析，且身分與 psutil 可用時同。"""
    explicit = {MEMORY_TIER_KEY: hw.TIER_THRESHOLDS[-1][1], SLOWPATH_KEY: "0"}
    ram(8 * GiB)
    with_psutil = _ids(_fp(env(explicit)))
    with pytest.MonkeyPatch.context() as mp:
        _psutil_unavailable(mp)
        without = _ids(_fp(env(explicit)))
    assert without == with_psutil


# ---------------------------------------------------------------------------------------------- ⑧ AST 登記

_PSUTIL_NAMES = frozenset({"psutil", "_psutil", "_psutil_cfg"})
_TIER_NAMES = frozenset({"get_memory_tier", "get_current_tier_gb", "get_tier_config", "get_tier_concurrent_symbols",
                         "TIER_THRESHOLDS"})


def _reads_hardware(fn: ast.AST) -> bool:
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and (n.id in _PSUTIL_NAMES or n.id in _TIER_NAMES or "_BY_TIER" in n.id):
            return True
        if isinstance(n, ast.Attribute) and (n.attr in _TIER_NAMES or n.attr == "virtual_memory"):
            return True
        if isinstance(n, ast.Import) and any("psutil" in a.name for a in n.names):
            return True
        if isinstance(n, ast.ImportFrom) and ("psutil" in (n.module or "") or any("psutil" in a.name for a in n.names)):
            return True
        if isinstance(n, ast.Constant) and n.value == MEMORY_TIER_KEY:
            return True
    return False


def _hardware_reader_functions(sources: Mapping[str, str]) -> Set[str]:
    """讀 psutil 或 tier 之函式（`<path>::<qualname>`；巢狀以 `.` 連接）。"""
    found: Set[str] = set()
    for path, src in sources.items():
        def visit(node: ast.AST, prefix: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qual = prefix + child.name
                    if _reads_hardware(child):
                        found.add(f"{path}::{qual}")
                    visit(child, qual + ".")
                elif isinstance(child, ast.ClassDef):
                    visit(child, prefix + child.name + ".")
                else:
                    visit(child, prefix)
        visit(ast.parse(src), "")
    return found


def _registered_resolvers() -> Set[str]:
    items = RAW["auto_resolutions"].get("items") or {}
    return {str(v["function"]) for k, v in items.items() if _real(k) and isinstance(v, Mapping) and "function" in v}


def _auto_sources() -> Dict[str, str]:
    return {p: (REPO / p).read_text(encoding="utf-8") for p in AUTO_FILES}


def test_resolve_hardware_readers_registered_in_contract() -> None:
    """⑧：三檔中讀 psutil 或 tier 之函式集合 ⊆ 契約 `auto_resolutions.items[*].function`。"""
    found = _hardware_reader_functions(_auto_sources())
    assert f"{AUTO_FILES[0]}::get_memory_tier" in found, "前提不成立：AST 掃描未見 get_memory_tier"
    registered = _registered_resolvers()
    assert registered, "契約 auto_resolutions.items 為空（Task 4.1 未填）"
    assert sorted(found - registered) == []


# ---------------------------------------------------------------------------------------------- ⑨ 路由身分

def _momentum_api_sources() -> Dict[str, str]:
    out = subprocess.run(["git", "ls-files", "-z", "--", "momentum", "api"], cwd=REPO, capture_output=True, check=True)
    paths = [p for p in out.stdout.decode("utf-8").split("\0") if p.endswith(".py")]
    return {p: (REPO / p).read_text(encoding="utf-8") for p in paths if (REPO / p).is_file()}


def _route_points_from_source(sources: Mapping[str, str]) -> Tuple[Set[str], List[str]]:
    """全部 `<memory_budget 模組>.route(<點>, …)` 呼叫之第一引數（須為字面；否則列問題）。"""
    points: Set[str] = set()
    problems: List[str] = []
    for path, src in sources.items():
        for node in ast.walk(ast.parse(src)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "route"):
                continue
            if "memory_budget" not in ast.unparse(node.func.value):
                continue
            first = node.args[0] if node.args else None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                points.add(first.value)
            else:
                problems.append(f"{path}:{node.lineno} 換臂點非字面")
    return points, problems


def _record_switch_callers(src: str) -> Set[str]:
    callers: Set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(node):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_record_route_switch":
                    callers.add(node.name)
    return callers


def _layer2_point() -> str:
    points, problems = _route_points_from_source({FACTORY_FILE: (REPO / FACTORY_FILE).read_text(encoding="utf-8")})
    assert problems == [] and len(points) == 1, f"前提不成立：feature_factory 之換臂點 {points}／{problems}"
    return next(iter(points))


def _rec(point: str, group: str, to: str, frm: str = ORIG_BRANCH) -> Dict[str, Any]:
    return {"event": "memory_route", "point": point, "group": group, "from": frm, "to": to, "reason": "capacity"}


def _route_distinguishes(fn: Callable[[Sequence[Mapping[str, Any]]], Any]) -> Dict[str, bool]:
    """⑨「不同」案：一筆未認證換臂 ≠ 無換臂；兩筆只差所選臂 ⇒ 不同。"""
    switched = [_rec(TEST_UNCERT_POINT, "g1", ALT_BRANCH)]
    other_arm = [_rec(TEST_UNCERT_POINT, "g1", ALT2_BRANCH)]
    return {"switch_vs_none": fn(switched) != fn([]), "arm_only": fn(switched) != fn(other_arm)}


def test_resolve_route_identity_pure_function(monkeypatch: pytest.MonkeyPatch) -> None:
    """⑨：同紀錄同身分（亦與順序無關）；未認證換臂與無換臂不同、只差所選臂亦不同；只含已認證者＝無換臂＝契約空值摘要。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    certified = _certified_points()
    assert certified, "契約無已認證換臂點（L2_ROUTE_CERTIFIED 機制所登錄者）"
    empty = nv.route_identity([])
    assert empty == _route_empty()
    one = [_rec(TEST_UNCERT_POINT, "g1", ALT_BRANCH)]
    assert nv.route_identity(one) == nv.route_identity(copy.deepcopy(one))
    assert _route_distinguishes(nv.route_identity) == {"switch_vs_none": True, "arm_only": True}
    cert = [_rec(certified[0], "g1", ALT_BRANCH)]
    assert nv.route_identity(cert) == empty
    assert nv.route_identity(cert + one) == nv.route_identity(one)
    two = one + [_rec(TEST_UNCERT_POINT, "g2", ALT_BRANCH)]
    assert nv.route_identity(two) == nv.route_identity(list(reversed(two)))


def test_resolve_route_switch_points_ast_equal_contract() -> None:
    """⑨ AST：`_record_route_switch` 只由 `route` 呼叫；全部 `memory_budget.route(<點>)` 之點集合＝契約登記之換臂點。"""
    sources = _momentum_api_sources()
    assert _record_switch_callers(sources[MEMORY_BUDGET_FILE]) == {"route"}
    points, problems = _route_points_from_source(sources)
    assert problems == [] and points, f"換臂點掃描：{points}／{problems}"
    assert points == set(_route_points_contract())


# ---------------------------------------------------------------------------------------------- ⑩ 標記回呼控制流

def _snapshot(available: int) -> Any:
    return mb.VMSnapshot(free_bytes=int(available), file_backed_bytes=0, swap_free_bytes=0, pressure_level=1,
                         swap_volume_free_bytes=75 * GiB, swap_volume_capacity_bytes=228 * GiB)


@pytest.fixture()
def switching(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """route 單元案：原臂估算 6 GiB、候選 1 GiB、可用 4 GiB ⇒ 容量換臂；受保護 run 情境使 `route_records` 有效。"""
    monkeypatch.delenv(mb.CHECK_LOG_ENV, raising=False)
    monkeypatch.setitem(mb.BRANCH_TABLE, ORIG_BRANCH, lambda p: [mb.Component("orig", "anon", 6 * GiB)])
    monkeypatch.setitem(mb.BRANCH_TABLE, ALT_BRANCH, lambda p: [mb.Component("alt", "anon", GiB)])
    token = mb._ACTIVE.set(mb._RunContext(mode="run", stop_dir=None))
    try:
        with mb.vm_snapshot_override(_snapshot(4 * GiB)):
            yield
    finally:
        mb._ACTIVE.reset(token)


def _run_route(point: str, work: Path, executed: Dict[str, int], group: str = "g1") -> str:
    """模擬分派點呼叫端：`route()` 回傳之 branch 才執行並於工作目錄留產物。"""
    branch = mb.route(point, [(ORIG_BRANCH, {}), (ALT_BRANCH, {})], label=point, group=group)
    executed[branch] = executed.get(branch, 0) + 1
    (Path(work) / f"{branch}.out").write_bytes(b"numview")
    return branch


def _writer(work: Path) -> Callable[[Mapping[str, Any]], Any]:
    return lambda entry: run_paths.write_route_switch_marker(Path(work), entry)


def _marker_failure_outcome(work: Path) -> Dict[str, Any]:
    """⑩ 拋出案：註冊之標記回呼注入 OSError，強制未認證換臂。"""
    injected = OSError(errno.ENOSPC, "numview 注入：標記寫入失敗（磁碟已滿）")

    def failing(entry: Mapping[str, Any]) -> None:
        raise injected

    executed: Dict[str, int] = {}
    before = _files(work)
    raised: Optional[BaseException] = None
    with mb.set_route_switch_marker(failing):
        try:
            _run_route(TEST_UNCERT_POINT, work, executed)
        except OSError as exc:
            raised = exc
    return {"raised_injected": raised is injected, "post_switch_runs": executed.get(ALT_BRANCH, 0),
            "files_unchanged": _files(work) == before}


def _measurement_failure_outcome(work: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """⑩ 容錯案：換臂紀錄之量測（`_current_usage_bytes`）拋 `MemoryMeasurementUnavailable`。"""
    def unavailable(*_a: Any, **_k: Any) -> int:
        raise mb.MemoryMeasurementUnavailable("numview 注入：量測失敗")

    monkeypatch.setattr(mb, "_current_usage_bytes", unavailable)
    executed: Dict[str, int] = {}
    branch: Optional[str] = None
    with mb.set_route_switch_marker(_writer(work)):
        try:
            branch = _run_route(TEST_UNCERT_POINT, work, executed)
        except mb.MemoryMeasurementUnavailable:
            branch = None
    return {"branch": branch, "marker": (Path(work) / _marker_name()).is_file()}


def test_resolve_marker_write_failure_raises_from_route(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                        tmp_path: Path) -> None:
    """⑩：標記回呼 OSError ⇒ `route()` 原樣拋出、換臂後 branch 零次、工作目錄檔案集合不變。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    (tmp_path / "pre_switch.out").write_bytes(b"orig")
    assert _marker_failure_outcome(tmp_path) == {"raised_injected": True, "post_switch_runs": 0,
                                                 "files_unchanged": True}


def test_resolve_measurement_failure_tolerated_and_marker_written(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                                  tmp_path: Path) -> None:
    """⑩：量測失敗照舊容錯——`route()` 回傳換臂後 branch，且標記已寫。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    assert _measurement_failure_outcome(tmp_path, monkeypatch) == {"branch": ALT_BRANCH, "marker": True}


# ============================================================================================== Task 4.1 邊界 40–47

def test_boundary_40_resolve_unset_env_uses_contract_default(env: Any, ram: Any) -> None:
    """邊界①（Task 4.1）：環境未設 ⇒ 契約登記之預設（＝`memory_budget.SELECTOR_DEFAULTS`）；明設全部預設值與未設同身分。"""
    sels = _selectors()
    assert sels, "契約 selectors 為空"
    assert {k: sels[k].get("default") for k in mb.SELECTOR_DEFAULTS if k in sels} == dict(mb.SELECTOR_DEFAULTS)
    ram(8 * GiB)
    assert _ids(_fp(env({}))) == _ids(_fp(env(dict(mb.SELECTOR_DEFAULTS))))


def test_boundary_41_resolve_invalid_env_records_fallback_with_marker(env: Any, ram: Any) -> None:
    """邊界②（Task 4.1）：非法環境值（現行 warning 後退回預設，core/config.py:24-35）⇒ fingerprint 該鍵記退回後之有效值
    （以生產函式於同環境之回傳為 oracle）並帶 `invalid_env` 標記；身分異於未設者（標記入身分）。"""
    assert INVALID_FALLBACK_KEY in _value_affecting()
    ram(8 * GiB)
    unset = _fp(env({}))
    bogus_env = env({INVALID_FALLBACK_KEY: "numview_bogus"})
    fallback = core_config.get_l65_optimization_profile()
    bogus = _fp(bogus_env)
    entries = _find_key(bogus, INVALID_FALLBACK_KEY)
    assert entries, f"fingerprint 無 {INVALID_FALLBACK_KEY} 之紀錄"
    text = _canon(entries)
    assert json.dumps(fallback) in text and "invalid_env" in text
    unset_entries = _find_key(unset, INVALID_FALLBACK_KEY)
    assert unset_entries and not any(_find_key(unset_entries, "invalid_env")), "未設之鍵不得帶真值 invalid_env 標記"
    assert _moves(unset, bogus) == (True, True)


def test_boundary_42_resolve_ram_equal_to_tier_threshold(env: Any, ram: Any) -> None:
    """邊界③（Task 4.1）：RAM 恰等於門檻（`>=`）⇒ 屬上一級：身分＝明設該級者，且≠門檻下一位元組之身分（導出值不同時）。"""
    bad: List[str] = []
    for threshold, tier in hw.TIER_THRESHOLDS:
        if threshold <= 0:
            continue
        ram(threshold * GiB)
        at = _ids(_fp(env({})))
        if at != _ids(_fp(env({MEMORY_TIER_KEY: tier}))):
            bad.append(f"{threshold} GiB ≠ 明設 {tier}")
        ram(threshold * GiB - 1)
        below = _ids(_fp(env({})))
        below_tier = _expected_tier(threshold * GiB - 1)
        if hw.get_tier_config(below_tier) != hw.get_tier_config(tier) and below == at:
            bad.append(f"{threshold} GiB 與其下一位元組身分相同")
    assert bad == []


def test_boundary_43_resolve_uncertified_switch_enters_route_identity(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                                      tmp_path: Path) -> None:
    """邊界④（Task 4.1）：未認證之執行期換臂點觸發 ⇒ 照舊換臂、呼叫端完成，所選臂入事後路由身分。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    executed: Dict[str, int] = {}
    with mb.set_route_switch_marker(_writer(tmp_path)):
        branch = _run_route(TEST_UNCERT_POINT, tmp_path, executed)
    records = mb.route_records()
    assert branch == ALT_BRANCH and executed == {ALT_BRANCH: 1}
    assert [(r["point"], r["group"], r["to"]) for r in records] == [(TEST_UNCERT_POINT, "g1", ALT_BRANCH)]
    assert nv.route_identity(records) != nv.route_identity([])


def test_boundary_44_resolve_repeated_switch_recorded_each_time(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                                tmp_path: Path) -> None:
    """邊界⑤（Task 4.1）：同一換臂點同一 run 多次觸發 ⇒ 逐次逐群組記錄、不去重；路由身分異於單次。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    executed: Dict[str, int] = {}
    with mb.set_route_switch_marker(_writer(tmp_path)):
        for group in ("g1", "g1", "g2"):
            _run_route(TEST_UNCERT_POINT, tmp_path, executed, group=group)
    records = mb.route_records()
    assert [(r["point"], r["group"], r["to"]) for r in records] == [
        (TEST_UNCERT_POINT, "g1", ALT_BRANCH), (TEST_UNCERT_POINT, "g1", ALT_BRANCH), (TEST_UNCERT_POINT, "g2", ALT_BRANCH)]
    assert nv.route_identity(records[:2]) != nv.route_identity(records[:1])
    assert nv.route_identity(records) != nv.route_identity(records[1:])


# ---------------------------------------------------------------------------------------------- 單元工廠（不生成）

def bare_factory(tmp: Path) -> FeatureFactory:
    """最小 FeatureFactory（同 tests/test_cgsa_resume.py 之 fixture）；特徵根＝`tmp/features`。"""
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()
    factory._adapter_registry = Mock()
    factory._progress_callback = None
    factory._storage = FeatureStorage(str(Path(tmp) / "features"))
    factory._registry = FeatureRegistry(Path(tmp) / "registry.json")
    factory._validator = Mock()
    factory._current_symbol = None
    factory._current_timeframe = None
    factory._current_config_hash = None
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._cgsa_registry = None
    factory._cgsa_force_fresh = False
    factory.layer_results = {}
    return factory


def write_complete_l7_manifest(storage: FeatureStorage, symbol: str, tf: str, config_hash: str,
                               algorithm_id: str) -> Path:
    """完整 L7 manifest（續跑閘放行之前提；同 test_cgsa_resume）＋頂層與 raw 節點之 `algorithm_id`（D6 比對對象）。"""
    run_dir = storage.feature_run_dir(symbol, tf, config_hash)
    run_dir.mkdir(parents=True, exist_ok=True)
    alg_key = _manifest_keys()["algorithm_id"]
    node = {"schema_version": "raw_v2", "expected_layers": ["L1"], "present_layers": ["L1"], "failed_layers": [],
            "expected_timeframes": [tf], "present_timeframes": [tf], "failed_timeframes": [],
            "quality_status": "complete", alg_key: algorithm_id}
    path = run_dir / storage.L7_V2_MANIFEST_NAME
    path.write_text(json.dumps({"artifacts": {"raw": node}, alg_key: algorithm_id}), encoding="utf-8")
    return path


def _stale_dirs(leaf: Path) -> List[Path]:
    return sorted(p for p in Path(leaf).parent.iterdir() if p.name.startswith(Path(leaf).name + ".stale-"))


def test_boundary_45_resolve_crash_after_uncertified_switch_blocks_resume(
        switching: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """邊界⑥（Task 4.1）：未認證換臂當下標記已寫；run 完成前崩潰 ⇒ 下一 run 不續跑（舊葉移為 `.stale-*`、新葉無舊檔）。
    對照：同設定而無標記之葉 ⇒ 續跑（證續跑閘可達）。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    symbol, tf = _kline_cell()
    resume = Mock(return_value="resumed")
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", resume)

    def body() -> Dict[str, Any]:
        factory = bare_factory(tmp_path)
        control_ch, ch, aid = _md5("numview-b45-control"), _md5("numview-b45"), _sha("numview-b45")
        control = factory._prepare_cgsa_registry(symbol, tf, control_ch, algorithm_id=aid)
        (Path(control.work_dir) / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
        write_complete_l7_manifest(factory._storage, symbol, tf, control_ch, aid)
        control_again = bare_factory(tmp_path)._prepare_cgsa_registry(symbol, tf, control_ch, algorithm_id=aid)
        control_calls = resume.call_count

        leaf = Path(factory._prepare_cgsa_registry(symbol, tf, ch, algorithm_id=aid).work_dir)
        (leaf / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
        write_complete_l7_manifest(factory._storage, symbol, tf, ch, aid)
        marker_at_switch = False
        with pytest.raises(SimulatedCrash):
            with mb.set_route_switch_marker(_writer(leaf)):
                _run_route(TEST_UNCERT_POINT, leaf, {})
                marker_at_switch = (leaf / _marker_name()).is_file()
                raise SimulatedCrash()
        rerun = bare_factory(tmp_path)._prepare_cgsa_registry(symbol, tf, ch, algorithm_id=aid)
        stale = _stale_dirs(leaf)
        return {"control_resumed": control_again == "resumed" and control_calls == 1,
                "marker_at_switch": marker_at_switch, "rerun_resumed": resume.call_count != control_calls,
                "stale_with_marker": len(stale) == 1 and (stale[0] / _marker_name()).is_file(),
                "new_leaf_same_path": Path(rerun.work_dir) == leaf,
                "new_leaf_has_manifest": (leaf / "manifest.json").exists()}

    assert _isolated(body) == {"control_resumed": True, "marker_at_switch": True, "rerun_resumed": False,
                               "stale_with_marker": True, "new_leaf_same_path": True, "new_leaf_has_manifest": False}


def test_boundary_46_resolve_marker_write_failure_aborts_before_branch(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                                       tmp_path: Path) -> None:
    """邊界⑦（Task 4.1）：工作目錄唯讀致標記寫入 OSError ⇒ `route()` 拋出、run 失敗、換臂後 branch 未執行、目錄不變。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    leaf = tmp_path / "leaf"
    leaf.mkdir()
    (leaf / "pre_switch.out").write_bytes(b"orig")
    before = _files(leaf)
    executed: Dict[str, int] = {}
    os.chmod(leaf, 0o555)
    try:
        with mb.set_route_switch_marker(_writer(leaf)):
            with pytest.raises(OSError):
                _run_route(TEST_UNCERT_POINT, leaf, executed)
    finally:
        os.chmod(leaf, 0o755)
    assert executed.get(ALT_BRANCH, 0) == 0
    assert _files(leaf) == before and not (leaf / _marker_name()).exists()


def test_boundary_47_resolve_measurement_failure_tolerated_marker_written(switching: None,
                                                                          monkeypatch: pytest.MonkeyPatch,
                                                                          tmp_path: Path) -> None:
    """邊界⑧（Task 4.1）：換臂量測失敗（`MemoryMeasurementUnavailable`）⇒ 照舊容錯、照常換臂並寫標記；紀錄之 F 為 None、
    標記內容含契約 marker_keys。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    outcome = _measurement_failure_outcome(tmp_path, monkeypatch)
    records = mb.route_records()
    assert outcome == {"branch": ALT_BRANCH, "marker": True}
    assert [(r["point"], r["to"], r["F"]) for r in records] == [(TEST_UNCERT_POINT, ALT_BRANCH, None)]
    marker = json.loads((tmp_path / _marker_name()).read_text(encoding="utf-8"))
    keys = list(_cgsa_identity().get("marker_keys") or [])
    assert keys and set(keys) <= set(marker)


# ============================================================================================== Task 4.1 mutation

def test_mutation_resolve_salt_drops_selector_key(env: Any, ram: Any, monkeypatch: pytest.MonkeyPatch,
                                                  tmp_path: Path) -> None:
    """mutant：鹽組成刪去一個 value_affecting 鍵 ⇒ ①該參數案之「鹽變」翻紅。"""
    assert SALT_PROBE_KEY in _value_affecting()
    real = nv.config_hash_salt
    monkeypatch.setattr(nv, "config_hash_salt", lambda fp: real(_drop_key(fp, SALT_PROBE_KEY)))
    ram(8 * GiB)
    base = _fp(env({}))
    alt = _fp(env({SALT_PROBE_KEY: _alternative_value(SALT_PROBE_KEY, tmp_path)}))
    assert _moves(base, alt)[1] is False


def test_mutation_resolve_records_raw_string_turns_polars_case_red(env: Any, ram: Any,
                                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：選擇子改記原始字串（非有效值）⇒ Polars 不可用案（=1 與 =0 同身分）翻紅。"""
    real = nv.resolve_numeric_fingerprint

    def raw_string(**kw: Any) -> Dict[str, Any]:
        return _set_key(real(**kw), USE_POLARS_KEY, kw["environ"].get(USE_POLARS_KEY, ""))

    monkeypatch.setattr(nv, "resolve_numeric_fingerprint", raw_string)
    assert _polars_effective_case(env, ram)[False] is False


def test_mutation_resolve_tier_not_recorded_turns_cross_hardware_red(env: Any, ram: Any,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：fingerprint 不反映解析後之 tier（以固定硬體解析，等同刪 tier 或記 `auto`）⇒ ⑥ 翻紅。"""
    import psutil

    real = nv.resolve_numeric_fingerprint

    def constant_hardware(**kw: Any) -> Dict[str, Any]:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(psutil, "virtual_memory", _fake_vm(8 * GiB))
            return real(**kw)

    monkeypatch.setattr(nv, "resolve_numeric_fingerprint", constant_hardware)
    assert _tier_partition_violations(ram, env) != []


def test_mutation_resolve_silent_8gb_turns_unresolved_case_red(env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：psutil 不可用時改回靜默 8gb（＋slow-path 關）⇒ ⑦ 翻紅。"""
    real = nv.resolve_numeric_fingerprint

    def silent(**kw: Any) -> Dict[str, Any]:
        try:
            return real(**kw)
        except nv.NumericContextUnresolvedError:
            fallback = {MEMORY_TIER_KEY: "8gb", SLOWPATH_KEY: "0"}
            with pytest.MonkeyPatch.context() as mp:
                for key, value in fallback.items():
                    mp.setenv(key, value)
                return real(**{**kw, "environ": {**kw["environ"], **fallback}})

    monkeypatch.setattr(nv, "resolve_numeric_fingerprint", silent)
    assert _unresolved_outcomes(env)["psutil_unavailable"] == "accepted"


def test_mutation_resolve_unregistered_psutil_reader_turns_ast_red() -> None:
    """mutant：hardware_utils 新增一個讀 psutil 之函式而未登記 ⇒ ⑧ 翻紅（餵改過之原始碼）。"""
    assert Path(hw.__file__).resolve().relative_to(REPO).as_posix() == AUTO_FILES[0]
    sources = _auto_sources()
    sources[AUTO_FILES[0]] += "\n\ndef numview_mutant_reads_psutil():\n    return _psutil.virtual_memory().total\n"
    missing = _hardware_reader_functions(sources) - _registered_resolvers()
    assert f"{AUTO_FILES[0]}::numview_mutant_reads_psutil" in missing


def test_mutation_resolve_route_identity_without_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：路由身分組成刪去所選臂 ⇒ ⑨「只差所選臂」之不同案翻紅。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    real = nv.route_identity
    monkeypatch.setattr(nv, "route_identity", lambda records: real([{**r, "to": "numview_dropped"} for r in records]))
    assert _route_distinguishes(nv.route_identity)["arm_only"] is False


def test_mutation_resolve_route_identity_skips_uncertified(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：路由身分整個略過未認證點 ⇒ ⑨「換臂≠無換臂」翻紅。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    real = nv.route_identity
    monkeypatch.setattr(nv, "route_identity",
                        lambda records: real([r for r in records if r.get("point") != TEST_UNCERT_POINT]))
    assert _route_distinguishes(nv.route_identity)["switch_vs_none"] is False


def test_mutation_resolve_unregistered_switch_point_turns_ast_red() -> None:
    """mutant：feature_factory 新增一個未登記之換臂點 ⇒ ⑨ AST 案翻紅。"""
    assert Path(sys.modules[FeatureFactory.__module__].__file__).resolve().relative_to(REPO).as_posix() == FACTORY_FILE
    sources = _momentum_api_sources()
    sources[FACTORY_FILE] += "\n\ndef _numview_mutant(candidates):\n    return _memory_budget.route(\"numview_mutant_point\", candidates)\n"
    points, _problems = _route_points_from_source(sources)
    assert points != set(_route_points_contract()) and "numview_mutant_point" in points


def test_mutation_resolve_marker_exception_swallowed(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                     tmp_path: Path) -> None:
    """mutant：標記回呼例外被吞（try/except 包住）⇒ ⑩ 拋出案翻紅。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    real = mb.set_route_switch_marker

    def swallowing(callback: Callable[[Mapping[str, Any]], Any]) -> Any:
        def wrapped(entry: Mapping[str, Any]) -> None:
            try:
                callback(entry)
            except Exception:  # noqa: BLE001 — mutant 本身即吞例外
                pass
        return real(wrapped)

    monkeypatch.setattr(mb, "set_route_switch_marker", swallowing)
    assert _marker_failure_outcome(tmp_path)["raised_injected"] is False


def test_mutation_resolve_measurement_failure_raises(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                     tmp_path: Path) -> None:
    """mutant：換臂紀錄之量測失敗亦拋出 ⇒ ⑩ 容錯案翻紅。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    real = mb._record_route_switch

    def strict(*args: Any, **kwargs: Any) -> Any:
        mb._current_usage_bytes()
        return real(*args, **kwargs)

    monkeypatch.setattr(mb, "_record_route_switch", strict)
    assert _measurement_failure_outcome(tmp_path, monkeypatch) != {"branch": ALT_BRANCH, "marker": True}


# ============================================================================================== Task 4.2 生成基礎

@dataclasses.dataclass
class GenRun:
    """一次真實短窗生成之紀錄（生成期間之事實，皆非紀錄檔自述）。"""

    root: Path
    work: Path
    handle: Optional[ph.RunHandle]
    env: Dict[str, str]
    switches: List[Dict[str, Any]]
    resumes: int
    events: List[Tuple[str, str]]
    crashed: bool

    @property
    def cgsa_root(self) -> Path:
        return self.work / "cgsa_work"

    @property
    def features_root(self) -> Path:
        return self.work / "features"


def _work_dir(root: Path, cell: str) -> Path:
    return Path(root) / cell / ph.cell_symbols(cell)[0]


def _crash(*_a: Any, **_k: Any) -> Any:
    raise SimulatedCrash("numview 模擬崩潰")


def _crash_after_leaf(real: Callable[..., Any]) -> Callable[..., Any]:
    """只於正式生成（CGSA 葉已定）崩潰；公開域預熱探測（定葉前以 `_calibration_domain` 獨立實例、暫存 registry 算
    L1–L6）照常執行——崩潰案之對象是已有部分落盤之葉。"""
    def wrapped(self: Any, *a: Any, **k: Any) -> Any:
        if getattr(self, "_cgsa_registry", None) is not None and not getattr(self, "_calibration_domain", False):
            _crash()
        return real(self, *a, **k)
    return wrapped


def _force_l2_switch(mp: pytest.MonkeyPatch, *, certified: bool) -> None:
    """強制 Layer 2 換臂（模擬可用記憶體不足）：暫登 L2 設定指紋於 `L2_ROUTE_CERTIFIED` 使分派點經 `route`，且原臂
    `check` 回容量拒絕。`certified=False` ⇒ 契約副本把該點標為未認證（HEAD 唯一之換臂點即 Layer 2；見報告之 SPEC 歧義）。"""
    assert ORIG_BRANCH in mb.BRANCH_TABLE
    mp.setattr(FeatureFactory, "_l2_route_fingerprint", lambda self, layer1, config: "numview_forced_fp")
    mp.setattr(FeatureFactory, "L2_ROUTE_CERTIFIED", frozenset({"numview_forced_fp"}))
    real_check = mb.check

    def check(branch_id: str, components: Any, **kwargs: Any) -> Any:
        if branch_id == ORIG_BRANCH:
            raise mb.GenerationMemoryBudgetExceeded(str(kwargs.get("label") or branch_id), 0, 1, 0,
                                                    mb.MSG_MACHINE_INSUFFICIENT)
        return real_check(branch_id, components, **kwargs)

    mp.setattr(mb, "check", check)
    if not certified:
        point = _layer2_point()

        def mutate(c: Dict[str, Any]) -> None:
            c["auto_resolutions"]["route_switch_points"][point] = {
                **dict(c["auto_resolutions"]["route_switch_points"].get(point) or {}), "certified": False}
        _contract_with(mp, mutate)


def _install_open_spy(mp: pytest.MonkeyPatch, watch: Path, events: List[Tuple[str, str]]) -> None:
    """記錄對 `watch`（含其 `.stale-*` 兄弟）之開檔，與 ColumnGroupRegistry 之建立／續跑時點（同一有序串列）。"""
    watch_s = os.path.realpath(watch)

    def hit(target: Any) -> Optional[str]:
        try:
            path = os.path.realpath(os.fspath(target))
        except TypeError:
            return None
        if path == watch_s or path.startswith(watch_s + os.sep) or path.startswith(watch_s + ".stale-"):
            return path
        return None

    real_builtin, real_io, real_os = builtins.open, io.open, os.open

    def b_open(file: Any, *a: Any, **k: Any) -> Any:
        h = hit(file)
        if h:
            events.append(("open", h))
        return real_builtin(file, *a, **k)

    def i_open(file: Any, *a: Any, **k: Any) -> Any:
        h = hit(file)
        if h:
            events.append(("open", h))
        return real_io(file, *a, **k)

    def o_open(path: Any, *a: Any, **k: Any) -> Any:
        h = hit(path)
        if h:
            events.append(("open", h))
        return real_os(path, *a, **k)

    mp.setattr(builtins, "open", b_open)
    mp.setattr(io, "open", i_open)
    mp.setattr(os, "open", o_open)
    real_init = ColumnGroupRegistry.__init__

    def init(self: Any, work_dir: Any, *a: Any, **k: Any) -> None:
        events.append(("registry", os.path.realpath(work_dir)))
        real_init(self, work_dir, *a, **k)

    mp.setattr(ColumnGroupRegistry, "__init__", init)


def _gen(root: Path, registry_path: Path, *, cell: str = CELL, fresh: bool = True, switch: Optional[str] = None,
         crash: Optional[str] = None, use_polars: Optional[str] = None, watch: Optional[Path] = None) -> GenRun:
    """真實短窗生成（`preprov_helpers.generate_short_run`）＋本檔之觀測與注入（外層 MonkeyPatch，生成後全數還原）。"""
    env_log: List[Dict[str, str]] = []
    switches: List[Dict[str, Any]] = []
    resumes = [0]
    events: List[Tuple[str, str]] = []
    handle: Optional[ph.RunHandle] = None
    crashed = False
    with pytest.MonkeyPatch.context() as mp:
        real_iso = ph._isolate

        def iso(inner: pytest.MonkeyPatch, work: Path, spec: Mapping[str, Any]) -> Path:
            out = real_iso(inner, work, spec)
            inner.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_path))  # 各根共用同一 registry 路徑（v44 前此鍵屬 value_affecting）
            return out

        mp.setattr(ph, "_isolate", iso)
        if use_polars is not None:
            mp.setitem(ph.FIXED_ENV, USE_POLARS_KEY, use_polars)
        real_hash = FeatureFactory._compute_config_hash

        def hash_spy(self: Any, *a: Any, **k: Any) -> str:
            env_log.append({key: v for key, v in os.environ.items() if key.startswith("FFACT_")})
            return real_hash(self, *a, **k)

        mp.setattr(FeatureFactory, "_compute_config_hash", hash_spy)
        if not fresh:
            real_generate = FeatureFactory.generate_features
            mp.setattr(FeatureFactory, "generate_features",
                       lambda self, *a, **k: real_generate(self, *a, **{**k, "force_regenerate": False}))
        real_switch = mb._record_route_switch

        def switch_spy(point: str, original: str, original_params: Any, branch: str, *a: Any, **k: Any) -> Any:
            switches.append({"point": point, "from": original, "to": branch})
            return real_switch(point, original, original_params, branch, *a, **k)

        mp.setattr(mb, "_record_route_switch", switch_spy)
        real_resume = ColumnGroupRegistry.resume_from_manifest.__func__

        def resume_spy(cls: Any, work_dir: Any) -> Any:
            resumes[0] += 1
            events.append(("resume", os.path.realpath(work_dir)))
            return real_resume(cls, work_dir)

        mp.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(resume_spy))
        if switch is not None:
            _force_l2_switch(mp, certified=(switch == "certified"))
        if crash == "after_switch":
            mp.setattr(FeatureFactory, "_layer2_derived_pandas", _crash_after_leaf(FeatureFactory._layer2_derived_pandas))
        elif crash == "before_l2":
            mp.setattr(FeatureFactory, "_budget_check_l2", _crash_after_leaf(FeatureFactory._budget_check_l2))
        if watch is not None:
            _install_open_spy(mp, watch, events)
        try:
            handle = ph.generate_short_run(root, cell)
        except SimulatedCrash:
            if crash is None:
                raise
            crashed = True
    assert crash is None or crashed, f"前提不成立：注入之崩潰（{crash}）未發生"
    assert env_log and all(e == env_log[-1] for e in env_log), "生成期間環境不一致（config_hash 計算多次而環境不同）"
    return GenRun(Path(root), _work_dir(root, cell), handle, env_log[-1], switches, resumes[0], events, crashed)


def _copy_root(src: Path, dst_parent: Path) -> Path:
    dst = Path(dst_parent) / "root"
    shutil.copytree(src, dst, symlinks=True)
    return dst


def _manifest(run: GenRun) -> Dict[str, Any]:
    assert run.handle is not None, "前提不成立：run 未完成"
    return ph.load_manifest(run.handle.run_dir)


def _single_leaf(run: GenRun, config_hash: str) -> Path:
    layer = run_paths.cgsa_config_layer_dir(run.cgsa_root, ph.cell_symbols(CELL)[0], ph.cell_spec(CELL)["primary"],
                                            config_hash)
    leaves = [p for p in layer.iterdir() if p.is_dir() and ".stale-" not in p.name]
    assert len(leaves) == 1, f"前提不成立：{layer} 下葉目錄 {leaves}"
    return leaves[0]


def _layer2_switches(run: GenRun) -> List[Dict[str, Any]]:
    point = _layer2_point()
    return [s for s in run.switches if s["point"] == point and s["to"] != s["from"]]


# ---------------------------------------------------------------------------------------------- 模組範圍之生成

@pytest.fixture(scope="module")
def registry_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("numview_identity_registry") / "registry.json"


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory, registry_path: Path) -> GenRun:
    """未換臂之基準 run（格 h1_stat_off）。"""
    return _gen(tmp_path_factory.mktemp("numview_base"), registry_path)


@pytest.fixture(scope="module")
def polars0(tmp_path_factory: pytest.TempPathFactory, registry_path: Path, base: GenRun) -> Dict[str, Any]:
    """基準根之複本內再以 `FFACT_USE_POLARS=0` 生成（同一特徵根，驗不互相覆寫）。"""
    root = _copy_root(base.root, tmp_path_factory.mktemp("numview_polars0"))
    base_dir = root / base.handle.run_dir.relative_to(base.root)
    before = hashlib.sha256((base_dir / ph.MANIFEST_NAME).read_bytes()).hexdigest()
    run = _gen(root, registry_path, use_polars="0")
    return {"run": run, "base_dir": base_dir, "before": before}


@pytest.fixture(scope="module")
def unc(tmp_path_factory: pytest.TempPathFactory, registry_path: Path) -> GenRun:
    """強制未認證換臂之 run（Task 4.2 ⑧）。"""
    run = _gen(tmp_path_factory.mktemp("numview_unc"), registry_path, switch="uncertified")
    assert _layer2_switches(run), "前提不成立：未認證換臂未發生"
    return run


@pytest.fixture(scope="module")
def cert(tmp_path_factory: pytest.TempPathFactory, registry_path: Path) -> GenRun:
    """強制已認證換臂之 run（Task 4.2 ⑧）。"""
    run = _gen(tmp_path_factory.mktemp("numview_cert"), registry_path, switch="certified")
    assert _layer2_switches(run), "前提不成立：已認證換臂未發生"
    return run


@pytest.fixture(scope="module")
def scen_uncertified_crash(tmp_path_factory: pytest.TempPathFactory, registry_path: Path, base: GenRun) -> Dict[str, Any]:
    """未認證換臂後崩潰 → 同設定重跑（不 force）：基準根複本（含完整 L7 manifest）上進行。"""
    root = _copy_root(base.root, tmp_path_factory.mktemp("numview_scen_unc_crash"))
    crash = _gen(root, registry_path, switch="uncertified", crash="after_switch")
    leaf = _single_leaf(crash, base.handle.config_hash)
    pre = {"switched": bool(_layer2_switches(crash)), "marker": (leaf / _marker_name()).is_file(),
           "manifest": (leaf / "manifest.json").is_file(),
           "l7": (crash.features_root / base.handle.run_dir.relative_to(base.features_root) / ph.MANIFEST_NAME).is_file()}
    rerun = _gen(root, registry_path, fresh=False, watch=leaf)
    return {"pre": pre, "leaf": leaf, "rerun": rerun}


@pytest.fixture(scope="module")
def scen_certified_crash(tmp_path_factory: pytest.TempPathFactory, registry_path: Path, base: GenRun) -> Dict[str, Any]:
    """只發生已認證換臂後崩潰 → 同設定重跑（不 force、同樣強制已認證換臂）。"""
    root = _copy_root(base.root, tmp_path_factory.mktemp("numview_scen_cert_crash"))
    crash = _gen(root, registry_path, switch="certified", crash="after_switch")
    leaf = _single_leaf(crash, base.handle.config_hash)
    pre = {"switched": bool(_layer2_switches(crash)), "marker": (leaf / _marker_name()).is_file(),
           "manifest": (leaf / "manifest.json").is_file()}
    rerun = _gen(root, registry_path, fresh=False, switch="certified")
    return {"pre": pre, "leaf": leaf, "rerun": rerun}


@pytest.fixture(scope="module")
def scen_resume_then_switch(tmp_path_factory: pytest.TempPathFactory, registry_path: Path,
                            base: GenRun) -> Dict[str, Any]:
    """未換臂而於 L2 前崩潰 → 續跑並於後續群組（L2）強制未認證換臂。"""
    root = _copy_root(base.root, tmp_path_factory.mktemp("numview_scen_resume_switch"))
    crash = _gen(root, registry_path, crash="before_l2")
    leaf = _single_leaf(crash, base.handle.config_hash)
    pre = {"switched": bool(_layer2_switches(crash)), "marker": (leaf / _marker_name()).is_file(),
           "manifest": (leaf / "manifest.json").is_file()}
    rerun = _gen(root, registry_path, fresh=False, switch="uncertified")
    return {"pre": pre, "leaf": leaf, "rerun": rerun}


@pytest.fixture(scope="module")
def ic_first_run(tmp_path_factory: pytest.TempPathFactory, registry_path: Path) -> GenRun:
    """IC-first 格（cleanup_raw ⇒ raw 已刪）。"""
    return _gen(tmp_path_factory.mktemp("numview_ic_first"), registry_path, cell=IC_FIRST_CELL)


# ---------------------------------------------------------------------------------------------- IC ingest 快取工具

def library_for(run_dir_root: Path, registry_path: Path) -> FeatureLibrary:
    root = Path(run_dir_root)
    return FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(root)),
                          feature_reader=FeatureReader(str(root)))


def _cache_paths(symbol: str, tf: str, config_hash: str) -> Dict[str, Path]:
    key = f"{symbol}_{tf}_{config_hash}".replace("/", "_")
    return {"h5": CACHE_REL / f"{key}.h5", "meta": CACHE_REL / f"{key}_meta.json"}


def _age(*paths: Path) -> None:
    for p in paths:
        os.utime(p, ns=(OLD_NS, OLD_NS))


def _ingest_pair_case(first_root: Path, second_root: Path, handle: ph.RunHandle, registry_path: Path,
                      writes: List[str]) -> Dict[str, bool]:
    """同 (symbol, tf, config_hash) 先以 first 物化，再換 second 物化；回傳第二次是否重寫 h5／meta。"""
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    service._feature_library = library_for(first_root, registry_path)  # noqa: SLF001
    service._materialize_features_for_ic(handle.symbol, handle.tf, handle.config_hash)
    paths = _cache_paths(handle.symbol, handle.tf, handle.config_hash)
    assert paths["h5"].is_file() and paths["meta"].is_file(), "前提不成立：首次物化未落快取"
    _age(paths["h5"], paths["meta"])
    writes.clear()
    service._feature_library = library_for(second_root, registry_path)  # noqa: SLF001
    service._materialize_features_for_ic(handle.symbol, handle.tf, handle.config_hash)
    return {"h5_rewritten": paths["h5"].stat().st_mtime_ns != OLD_NS and len(writes) == 1,
            "meta_rewritten": paths["meta"].stat().st_mtime_ns != OLD_NS}


@pytest.fixture()
def h5_writes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> List[str]:
    """cwd 移到 tmp（快取相對路徑落 tmp）＋`_write_features_h5` 呼叫計數（照實寫入）。"""
    from api.services.ic_analysis_service import ICAnalysisService

    monkeypatch.chdir(tmp_path)
    real = ICAnalysisService._write_features_h5
    calls: List[str] = []

    def counting(path: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append(str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(ICAnalysisService, "_write_features_h5", staticmethod(counting))
    return calls


def patch_everywhere(monkeypatch: pytest.MonkeyPatch, name: str, original: Any, replacement: Any) -> int:
    """把 momentum／api 已載入模組中綁定到 `original` 之 `name` 一律換成 `replacement`（同 test_preprov_ingest_cache）。"""
    hits = 0
    for module in list(sys.modules.values()):
        modname = getattr(module, "__name__", "") or ""
        if modname.startswith(("momentum", "api")) and getattr(module, name, None) is original:
            monkeypatch.setattr(module, name, replacement)
            hits += 1
    return hits


def _rewrite_manifest(run_dir: Path, *, values: Optional[Mapping[str, Any]] = None, strip: bool = False) -> None:
    """改寫 manifest 頂層與各 artifact 節點之本票新鍵：`values`（鍵→值）逐一覆寫（表同 config_hash 之另一身分，內容不變）；
    `strip=True` ⇒ 刪除本票全部新鍵（表舊 run）。"""
    path = Path(run_dir) / ph.MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    mk = _manifest_keys()
    new_keys = [mk["fingerprint"], mk["algorithm_id"], mk["observed_arms"], _route_key()]
    nodes = [manifest] + [n for n in (manifest.get("artifacts") or {}).values() if isinstance(n, dict)]
    for node in nodes:
        if strip:
            for key in new_keys:
                node.pop(key, None)
        for key, value in dict(values or {}).items():
            if node is manifest or key != mk["observed_arms"]:
                node[key] = value
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _copied_run(run: GenRun, parent: Path) -> Tuple[Path, Path]:
    """run 所在根之複本；回傳（複本之特徵根, 複本之 run 目錄）。"""
    root = _copy_root(run.root, parent)
    features = root / run.features_root.relative_to(run.root)
    return features, features / run.handle.run_dir.relative_to(run.features_root)


def _route_variant(base: GenRun, unc: GenRun, parent: Path) -> Path:
    """基準 run 之複本，只把 manifest 之路由身分改為未認證換臂 run 實得之值（特徵內容逐位元不變）⇒ IC 快取比對兩者只差
    路由身分（換臂臂之值未經認證等價，直接比兩 run 可能因內容不同而重寫，不足以證路由身分入比對）。回傳複本特徵根。"""
    rk = _route_key()
    value = _manifest(unc)[rk]
    assert value != _manifest(base)[rk], "前提不成立：未認證換臂 run 之路由身分等於未換臂者"
    features, run_dir = _copied_run(base, parent)
    _rewrite_manifest(run_dir, values={rk: value})
    return features


def _run_config(run: GenRun) -> Any:
    assert run.handle is not None
    return ph.observation(run.handle).config


def _fingerprint_for(run: GenRun, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """以 Task 4.1 函式依該 run 生成時之設定、環境、能力重算 fingerprint（環境同時寫入 os.environ）。"""
    for key in [k for k in os.environ if k.startswith("FFACT_")]:
        monkeypatch.delenv(key)
    for key, value in run.env.items():
        monkeypatch.setenv(key, value)
    return nv.resolve_numeric_fingerprint(preprocessing_config=_run_config(run).preprocessing.model_dump(),
                                          environ=dict(os.environ), capabilities=dict(nv.detect_capabilities()))


# ============================================================================================== Task 4.2 驗證

def test_manifest_carries_fingerprint_and_algorithm_id(base: GenRun, monkeypatch: pytest.MonkeyPatch) -> None:
    """①：manifest 頂層與 raw 節點帶 fingerprint、`algorithm_id`；fingerprint＝依該 run 設定／環境／能力以 Task 4.1 函式
    重算者；`algorithm_id`＝測試端獨立正規 JSON sha256＝`numeric_view.algorithm_id`；RunIdentity 之 `algorithm_id` 同值。"""
    mk = _manifest_keys()
    manifest = _manifest(base)
    raw_node = manifest["artifacts"]["raw"]
    fp = manifest[mk["fingerprint"]]
    assert raw_node[mk["fingerprint"]] == fp and raw_node[mk["algorithm_id"]] == manifest[mk["algorithm_id"]]
    assert fp == _fingerprint_for(base, monkeypatch)
    assert manifest[mk["algorithm_id"]] == _independent_algorithm_id(fp) == nv.algorithm_id(fp)
    assert mk["observed_arms"] in manifest
    assert rp.resolve_run_identity(manifest, "raw").algorithm_id == manifest[mk["algorithm_id"]]


def test_use_polars_toggle_lands_in_distinct_config_hash_dirs(polars0: Dict[str, Any], base: GenRun) -> None:
    """②：`FFACT_USE_POLARS` 0／1 兩次生成（同一特徵根）⇒ 不同 `config_hash` 目錄，先生成者之 manifest 不被覆寫。"""
    run: GenRun = polars0["run"]
    assert run.env.get(USE_POLARS_KEY) == "0" and base.env.get(USE_POLARS_KEY) == "1"
    assert run.handle.config_hash != base.handle.config_hash
    assert run.handle.run_dir != polars0["base_dir"] and run.handle.run_dir.is_dir() and polars0["base_dir"].is_dir()
    after = hashlib.sha256((polars0["base_dir"] / ph.MANIFEST_NAME).read_bytes()).hexdigest()
    assert after == polars0["before"]


def _library_bump(monkeypatch: pytest.MonkeyPatch) -> None:
    libs = list(RAW["library_versions"]["values"])
    assert libs, "契約 library_versions 為空"
    real = nv.library_version
    monkeypatch.setattr(nv, "library_version", lambda name: real(name) + ("+numview" if name == libs[0] else ""))


def _d6_case(root: Path, run: GenRun, *, requested_aid: str, l7_aid: str,
             monkeypatch: pytest.MonkeyPatch) -> int:
    """葉身分相符（同 config_hash、同 algorithm_id 之葉）而 L7 manifest 之 `algorithm_id` 為 `l7_aid` 時，
    `_prepare_cgsa_registry(…, algorithm_id=requested_aid)` 之續跑次數。"""
    copy_work = root / run.work.relative_to(run.root)
    run_dir = copy_work / "features" / run.handle.run_dir.relative_to(run.features_root)
    mk = _manifest_keys()
    l7 = json.loads((run_dir / ph.MANIFEST_NAME).read_text(encoding="utf-8"))
    l7[mk["algorithm_id"]] = l7_aid
    for node in (l7.get("artifacts") or {}).values():
        if isinstance(node, dict):
            node[mk["algorithm_id"]] = l7_aid
    (run_dir / ph.MANIFEST_NAME).write_text(json.dumps(l7, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(copy_work / "cgsa_work"))
    resume = Mock(return_value="resumed")
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", resume)
    factory = bare_factory(copy_work)
    _isolated(lambda: factory._prepare_cgsa_registry(run.handle.symbol, run.handle.tf, run.handle.config_hash,
                                                     algorithm_id=requested_aid))
    return resume.call_count


def test_library_version_change_same_config_hash_resume_refused_cache_rebuilt(
        base: GenRun, registry_path: Path, monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory,
        h5_writes: List[str]) -> None:
    """③：函式庫版本改變 ⇒ 同 `config_hash`（鹽不含版本）、`algorithm_id` 不同；續跑被拒（新 `algorithm_id` 之葉不同；
    葉同而 L7 manifest 記另一 `algorithm_id` 亦拒——D6）；IC ingest 快取重建。對照：原版本下續跑可達。"""
    from momentum.factories import create_feature_factory

    handle = base.handle
    config = _run_config(base)
    start, end = ph.cell_spec(CELL)["window"]
    factory = create_feature_factory(cache_dir=str(ph.KLINE_FILE.parent), validate_continuity=False)
    fp0 = _fingerprint_for(base, monkeypatch)
    aid0 = nv.algorithm_id(fp0)
    ch0 = factory._compute_config_hash(config, handle.symbol, handle.tf, start_date=start, end_date=end)
    assert ch0 == handle.config_hash and aid0 == _manifest(base)[_manifest_keys()["algorithm_id"]], \
        "前提不成立：以生成時環境重算之 config_hash／algorithm_id 不等於該 run"
    with pytest.MonkeyPatch.context() as mp:
        _library_bump(mp)
        fp1 = _fingerprint_for(base, mp)
        aid1 = nv.algorithm_id(fp1)
        ch1 = factory._compute_config_hash(config, handle.symbol, handle.tf, start_date=start, end_date=end)
    assert ch1 == ch0 and aid1 != aid0

    copy_root = _copy_root(base.root, tmp_path_factory.mktemp("numview_lib_resume"))
    assert _d6_case(copy_root, base, requested_aid=aid0, l7_aid=aid0, monkeypatch=monkeypatch) == 1  # 對照：可續跑
    assert _d6_case(copy_root, base, requested_aid=aid1, l7_aid=aid1, monkeypatch=monkeypatch) == 0  # 葉不同
    assert _d6_case(copy_root, base, requested_aid=aid0, l7_aid=aid1, monkeypatch=monkeypatch) == 0  # D6

    ingest_features, ingest_run_dir = _copied_run(base, tmp_path_factory.mktemp("numview_lib_ingest"))
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    service._feature_library = library_for(ingest_features, registry_path)  # noqa: SLF001
    service._materialize_features_for_ic(handle.symbol, handle.tf, handle.config_hash)
    paths = _cache_paths(handle.symbol, handle.tf, handle.config_hash)
    _age(paths["h5"], paths["meta"])
    h5_writes.clear()
    mk = _manifest_keys()
    _rewrite_manifest(ingest_run_dir, values={mk["algorithm_id"]: aid1, mk["fingerprint"]: fp1})
    service._feature_library = library_for(ingest_features, registry_path)  # noqa: SLF001
    service._materialize_features_for_ic(handle.symbol, handle.tf, handle.config_hash)
    assert len(h5_writes) == 1 and paths["h5"].stat().st_mtime_ns != OLD_NS
    assert paths["meta"].stat().st_mtime_ns != OLD_NS


def test_section_g_fingerprints_bitwise_one_cell(base: GenRun) -> None:
    """④：§G 值指紋逐位元（一格：h1_stat_off 對沿用基準 `tests/_golden/preprov/pre_change_fingerprints.json`）。"""
    legacy = json.loads(nh.LEGACY_BASELINE_PATH.read_text(encoding="utf-8"))["cells"][CELL][base.handle.symbol]["raw"]
    assert nh.bitwise_diff(legacy, nh.fingerprints(base.handle.run_dir, "raw"), legacy=True) == []


# ---------------------------------------------------------------------------------------------- ⑥ 倖存者契約

def _inner_identity_schema() -> Mapping[str, Any]:
    spec = sc.load_survivor_contract()["provenance_keys"]["keys"]["ff_run_identity"]
    assert spec.get("type") == "object" and isinstance(spec.get("keys"), Mapping), \
        "倖存者契約 provenance_keys.keys.ff_run_identity 無內層 keys schema（Task 4.2 未改）"
    return spec


_SAMPLE_BY_TYPE: Dict[str, Any] = {"str": "numview", "int": 1, "float": 1.0, "bool": True, "list": [], "object": {}}


def _full_identity() -> Dict[str, Any]:
    inner = _inner_identity_schema()
    keys = list(RUN_PROV["run_identity_keys"])
    assert set(inner["keys"]) == set(keys), "倖存者 ff_run_identity 內層鍵集 ≠ run_provenance.run_identity_keys"
    assert inner.get("additional_properties") is False
    return {k: _SAMPLE_BY_TYPE[inner["keys"][k]["type"]] for k in keys}


def _survivor_payload(identity: Any) -> Dict[str, Any]:
    from tests.momentum.Analysis.test_survivor_contract import _build_kwargs

    kwargs, _plan = _build_kwargs()
    payload = sc.build_survivor_output(**kwargs)
    payload["provenance"]["ff_run_identity"] = copy.deepcopy(identity)
    return payload


def _survivor_cases() -> Dict[str, str]:
    full = _full_identity()
    cases = {"null": None, "full": full, "empty": {},
             "missing_algorithm_id": {k: v for k, v in full.items() if k != "algorithm_id"},
             "extra_key": {**full, "numview_unknown_key": "x"}}
    out: Dict[str, str] = {}
    for name, identity in cases.items():
        try:
            sc.validate_survivor_output(_survivor_payload(identity))
            out[name] = "accepted"
        except ContractValidationError:
            out[name] = "rejected"
    return out


def _old_version_rejected() -> bool:
    payload = _survivor_payload(None)
    payload["schema_version"] = OLD_SURVIVOR_VERSION
    payload["provenance"]["contract_version"] = OLD_SURVIVOR_VERSION
    try:
        sc.validate_survivor_output(payload)
    except ContractValidationError:
        return True
    return False


def test_survivor_identity_inner_schema_validated() -> None:
    """⑥：`ff_run_identity` 為 `{}`、缺 `algorithm_id`、多一未知鍵 ⇒ 拒收；null 與完整身分 ⇒ 通過。"""
    assert "algorithm_id" in RUN_PROV["run_identity_keys"]
    assert _survivor_cases() == {"null": "accepted", "full": "accepted", "empty": "rejected",
                                 "missing_algorithm_id": "rejected", "extra_key": "rejected"}


def test_survivor_contract_version_bumped_old_rejected() -> None:
    """⑥：倖存者契約 `version` 無條件 +1（> 3）；舊版本（3）倖存者檔拒收。"""
    assert sc.load_survivor_contract()["version"] > OLD_SURVIVOR_VERSION
    assert _old_version_rejected() is True


# ---------------------------------------------------------------------------------------------- 身分欄（D2）

def test_run_identity_and_cache_fields_extended() -> None:
    """D2：RunIdentity 新鍵（含 `algorithm_id` 與路由身分鍵）⊆ run_provenance `run_identity_keys`＝RunIdentity 欄位；
    IC-first JSON 快取身分欄只增不減且含兩新鍵。"""
    new = list(RAW["run_identity_new_keys"])
    assert new, "契約 run_identity_new_keys 為空（Task 4.2 未填）"
    assert {"algorithm_id", _route_key()} <= set(new) <= set(RUN_PROV["run_identity_keys"])
    assert {f.name for f in dataclasses.fields(rp.RunIdentity)} == set(RUN_PROV["run_identity_keys"])
    assert set(HEAD_CACHE_FIELDS) | {"algorithm_id", _route_key()} <= set(ice.CACHE_IDENTITY_FIELDS)


# ---------------------------------------------------------------------------------------------- ⑧ 路由身分整合

def _route_values(manifest: Mapping[str, Any]) -> Tuple[Any, Any, Any]:
    rk = _route_key()
    return manifest[rk], manifest["artifacts"]["raw"][rk], getattr(rp.resolve_run_identity(manifest, "raw"), rk)


def test_uncertified_switch_run_completes_with_distinct_route_identity(base: GenRun, unc: GenRun) -> None:
    """⑧：強制未認證換臂（模擬可用記憶體不足）⇒ run 照常完成；事前身分（config_hash、algorithm_id）同未換臂者，
    manifest 頂層、raw 節點與 RunIdentity 之路由身分皆異於未換臂者；未換臂者＝契約空值摘要。"""
    alg = _manifest_keys()["algorithm_id"]
    m0, m1 = _manifest(base), _manifest(unc)
    assert unc.handle.config_hash == base.handle.config_hash and m1[alg] == m0[alg]
    top0, node0, ident0 = _route_values(m0)
    top1, node1, ident1 = _route_values(m1)
    assert top0 == node0 == ident0 == _route_empty()
    assert top1 == node1 == ident1 and top1 != top0


def test_uncertified_switch_ic_ingest_cache_not_reused(base: GenRun, unc: GenRun, registry_path: Path,
                                                       h5_writes: List[str],
                                                       tmp_path_factory: pytest.TempPathFactory) -> None:
    """⑧：同 (symbol, tf, config_hash)、特徵內容相同而路由身分＝未認證換臂 run 實得之值 ⇒ IC ingest 快取不沿用
    未換臂者（h5 與 meta 重寫）；另直接以兩 run 物化亦不沿用。"""
    assert unc.handle.config_hash == base.handle.config_hash
    variant = _route_variant(base, unc, tmp_path_factory.mktemp("numview_route_variant"))
    assert _ingest_pair_case(base.features_root, variant, base.handle, registry_path, h5_writes) == {
        "h5_rewritten": True, "meta_rewritten": True}
    assert _ingest_pair_case(base.features_root, unc.features_root, base.handle, registry_path, h5_writes) == {
        "h5_rewritten": True, "meta_rewritten": True}


def test_certified_switch_route_identity_equals_unswitched(base: GenRun, cert: GenRun) -> None:
    """⑧：強制已認證換臂點（`L2_ROUTE_CERTIFIED` 暫登一筆）換臂 ⇒ 路由身分與未換臂者相同。"""
    assert _route_values(_manifest(cert)) == _route_values(_manifest(base))


def _reads_before_registry(events: Sequence[Tuple[str, str]], leaf: Path) -> List[str]:
    """新 registry 建立（`ColumnGroupRegistry.__init__` 於該葉）之前，對舊葉（含 `.stale-*`）之開檔；身分檔除外。"""
    leaf_s = os.path.realpath(leaf)
    allowed = os.path.join(leaf_s, _identity_name())
    out: List[str] = []
    for kind, path in events:
        if kind == "registry" and path == leaf_s:
            return out
        if kind in ("open", "resume") and path != allowed:
            out.append(f"{kind}:{path}")
    out.append("未見新 registry 於該葉建立")
    return out


def test_crash_after_uncertified_switch_rerun_not_continued(scen_uncertified_crash: Dict[str, Any]) -> None:
    """⑧：已發生未認證換臂之 run 於換臂後立即崩潰（標記檔當下即在）⇒ 同設定重跑不續跑、舊目錄移為 `.stale-*`（內含標記）、
    新 registry 建立前對舊目錄除身分檔外零開檔。"""
    s = scen_uncertified_crash
    assert s["pre"] == {"switched": True, "marker": True, "manifest": True, "l7": True}
    rerun: GenRun = s["rerun"]
    assert rerun.handle is not None and rerun.resumes == 0
    assert [p.name for p in _stale_dirs(s["leaf"]) if (p / _marker_name()).is_file()], "含標記之舊葉未移為 .stale-*"
    assert not (s["leaf"] / _marker_name()).exists(), "新葉不得帶舊標記"
    assert _reads_before_registry(rerun.events, s["leaf"]) == []


def test_crash_after_certified_switch_rerun_continues(scen_certified_crash: Dict[str, Any], cert: GenRun,
                                                      base: GenRun) -> None:
    """⑧：只發生已認證換臂之 run 崩潰後重跑 ⇒ 續跑；最終路由身分＝未中斷之已認證換臂 run＝未換臂 run。"""
    s = scen_certified_crash
    assert s["pre"] == {"switched": True, "marker": False, "manifest": True}
    rerun: GenRun = s["rerun"]
    assert rerun.resumes >= 1 and not (s["leaf"] / _marker_name()).exists()
    assert _route_values(_manifest(rerun)) == _route_values(_manifest(cert)) == _route_values(_manifest(base))


def _switch_projection(run: GenRun) -> List[Tuple[str, str, str]]:
    return [(s["point"], s["from"], s["to"]) for s in _layer2_switches(run)]


def test_resume_then_uncertified_switch_equals_uninterrupted(scen_resume_then_switch: Dict[str, Any],
                                                             unc: GenRun) -> None:
    """⑧：未換臂之 run 中止後續跑，並於本 run 之後續群組強制未認證換臂 ⇒ 完成、標記寫入；逐群組換臂與最終路由身分
    等於同設定未中斷而於同群組換臂之 run，且兩者 §G 值指紋逐位元相等。"""
    s = scen_resume_then_switch
    assert s["pre"] == {"switched": False, "marker": False, "manifest": True}
    rerun: GenRun = s["rerun"]
    assert rerun.resumes >= 1 and (s["leaf"] / _marker_name()).is_file()
    assert _switch_projection(rerun) == _switch_projection(unc)
    assert _route_values(_manifest(rerun)) == _route_values(_manifest(unc))
    assert nh.bitwise_diff(nh.fingerprints(unc.handle.run_dir, "raw"),
                           nh.fingerprints(rerun.handle.run_dir, "raw")) == []


# ============================================================================================== Task 4.2 邊界

def test_boundary_48_legacy_run_reads_but_cache_not_reused(base: GenRun, registry_path: Path, h5_writes: List[str],
                                                          tmp_path_factory: pytest.TempPathFactory) -> None:
    """邊界①（Task 4.2）：舊 run（manifest 無本票新鍵）⇒ 讀特徵與原 run 逐值相同、RunIdentity `algorithm_id` 為 None
    （legacy）；IC ingest 快取不沿用（同一舊 run 第二次物化仍重寫）。"""
    legacy_features, legacy_run_dir = _copied_run(base, tmp_path_factory.mktemp("numview_legacy"))
    _rewrite_manifest(legacy_run_dir, strip=True)
    h = base.handle
    original = library_for(base.features_root, registry_path).load(h.symbol, h.tf, config_hash=h.config_hash)
    frame, identity = library_for(legacy_features, registry_path).load_with_identity(h.symbol, h.tf,
                                                                                     config_hash=h.config_hash)
    assert frame.equals(original)
    assert identity.algorithm_id is None and identity.legacy is True
    assert _ingest_pair_case(legacy_features, legacy_features, h, registry_path, h5_writes) == {
        "h5_rewritten": True, "meta_rewritten": True}


def test_boundary_49_ic_first_processed_node_carries_identity(ic_first_run: GenRun) -> None:
    """邊界②（Task 4.2）：IC-first 已刪 raw 之 run ⇒ processed 節點帶 fingerprint、`algorithm_id`、路由身分（＝頂層），
    processed 之 RunIdentity 同值。"""
    mk = _manifest_keys()
    rk = _route_key()
    run = ic_first_run
    assert not (run.handle.run_dir / "raw").exists(), "前提不成立：cleanup_raw 後 raw 仍在"
    manifest = _manifest(run)
    node = manifest["artifacts"]["processed"]
    for key in (mk["fingerprint"], mk["algorithm_id"], rk):
        assert node[key] == manifest[key], key
    identity = rp.resolve_run_identity(manifest, "processed")
    assert identity.algorithm_id == manifest[mk["algorithm_id"]] and getattr(identity, rk) == manifest[rk]


def test_scheduling_only_keys_change_parallelism_not_values(registry_path: Path,
                                                             tmp_path_factory: pytest.TempPathFactory) -> None:
    """SPEC v44 ⑥（使用者 2026-10-25 選「分工設定不算進指紋」）：批次分工兩鍵（契約 `scheduling_only_keys`）只改 L6.5
    slow-path 之 n_jobs、不改值——同一真實短窗（`h1_stat_on`：fracdiff／ADF 走 slow-path）於強制 slow-path 平行下，不設兩鍵與
    設兩鍵（批次情境）各生成一次：前提＝實際觀測之 n_jobs 不同（平行 ≥2、批次 1）；斷言＝config_hash 相同（兩鍵不入身分）、
    raw 值指紋逐位元相同。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    keys = list(RAW["selector_classes"].get("scheduling_only_keys") or [])
    assert sorted(keys) == ["FFACT_BATCH_NESTED", "FFACT_BATCH_SYMBOL_CONCURRENCY"], keys
    real = FeaturePreprocessor._resolve_slowpath_n_jobs
    seen: Dict[str, List[int]] = {}
    runs: Dict[str, GenRun] = {}
    for tag, extra in (("parallel", {}), ("batch", {"FFACT_BATCH_NESTED": "1", "FFACT_BATCH_SYMBOL_CONCURRENCY": "2"})):
        def spy(self: Any, _tag: str = tag) -> int:
            n = real(self)
            seen.setdefault(_tag, []).append(int(n))
            return n

        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(ph.FIXED_ENV, SLOWPATH_KEY, "1")
            for key, value in extra.items():
                mp.setitem(ph.FIXED_ENV, key, value)
            mp.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", spy)
            runs[tag] = _gen(tmp_path_factory.mktemp(f"numview_sched_{tag}"), registry_path, cell="h1_stat_on")
    assert seen.get("parallel") and min(seen["parallel"]) >= 2, f"前提不成立：平行情境之 n_jobs {seen.get('parallel')}"
    assert seen.get("batch") and set(seen["batch"]) == {1}, f"前提不成立：批次情境之 n_jobs {seen.get('batch')}"
    assert runs["parallel"].handle.config_hash == runs["batch"].handle.config_hash
    assert nh.bitwise_diff(nh.fingerprints(runs["parallel"].handle.run_dir, "raw"),
                           nh.fingerprints(runs["batch"].handle.run_dir, "raw")) == []


# ============================================================================================== Task 4.2 mutation

def test_mutation_route_identity_without_arm_breaks_distinct_case(unc: GenRun, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：路由身分組成刪去所選臂 ⇒ ⑧「不同」案之 oracle（真實換臂紀錄 vs 同點同群組改選他臂）翻紅。"""
    point = _layer2_point()

    def mutate(c: Dict[str, Any]) -> None:
        c["auto_resolutions"]["route_switch_points"][point] = {"certified": False}
    _contract_with(monkeypatch, mutate)
    switched = [_rec(s["point"], "numview_group", s["to"], s["from"]) for s in _layer2_switches(unc)]
    assert switched, "前提不成立：無真實換臂紀錄"
    other = [{**r, "to": r["from"]} for r in switched]
    assert nv.route_identity(switched) != nv.route_identity(other)
    real = nv.route_identity
    monkeypatch.setattr(nv, "route_identity", lambda records: real([{**r, "to": "numview_dropped"} for r in records]))
    assert nv.route_identity(switched) == nv.route_identity(other)


def _uncertified_switch_completes() -> bool:
    executed: Dict[str, int] = {}
    try:
        with mb.set_route_switch_marker(lambda entry: None):
            return _run_route(TEST_UNCERT_POINT, Path(os.getcwd()), executed) == ALT_BRANCH
    except RuntimeError:
        return False


def test_mutation_uncertified_point_raising_breaks_completion(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                              tmp_path: Path) -> None:
    """mutant：未認證換臂點改為拋錯 ⇒ ⑧「照常完成」之 oracle 翻紅。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    monkeypatch.chdir(tmp_path)
    assert _uncertified_switch_completes() is True

    def refuse(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("numview mutant：未認證換臂改為拋錯")

    monkeypatch.setattr(mb, "_record_route_switch", refuse)
    assert _uncertified_switch_completes() is False


def _marker_leaf(tmp: Path, symbol: str, tf: str, ch: str, aid: str) -> Tuple[FeatureFactory, Path]:
    """建葉（身分檔由工廠寫）＋registry manifest＋完整 L7 manifest＋未認證換臂標記檔。"""
    factory = bare_factory(tmp)
    leaf = Path(_isolated(lambda: factory._prepare_cgsa_registry(symbol, tf, ch, algorithm_id=aid)).work_dir)
    (leaf / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
    write_complete_l7_manifest(factory._storage, symbol, tf, ch, aid)
    run_paths.write_route_switch_marker(leaf, {"point": TEST_UNCERT_POINT, "group": "g1", "to": ALT_BRANCH})
    return factory, leaf


def test_mutation_marker_dir_resumed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutant：續跑閘無視標記（契約標記檔名改指不存在之檔）⇒ ⑧ 未認證續跑案（含標記不得續跑）翻紅。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    symbol, tf = _kline_cell()
    ch, aid = _md5("numview-m-marker"), _sha("numview-m-marker")
    resume = Mock(return_value="resumed")
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", resume)
    _factory, _leaf = _marker_leaf(tmp_path, symbol, tf, ch, aid)
    _isolated(lambda: bare_factory(tmp_path)._prepare_cgsa_registry(symbol, tf, ch, algorithm_id=aid))
    assert resume.call_count == 0
    _factory2, _leaf2 = _marker_leaf(tmp_path, symbol, tf, ch, aid)

    def mutate(c: Dict[str, Any]) -> None:
        c["cgsa_work_identity"]["marker_file"] = "numview_mutant_absent_marker"
    _contract_with(monkeypatch, mutate)
    _isolated(lambda: bare_factory(tmp_path)._prepare_cgsa_registry(symbol, tf, ch, algorithm_id=aid))
    assert resume.call_count == 1


def test_mutation_marker_written_at_completion(switching: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutant：標記檔延至 run 完成才寫（換臂當下只暫存）⇒ ⑧ 崩潰案（換臂當下標記已在）翻紅。"""
    _register_point(monkeypatch, TEST_UNCERT_POINT, False)
    pending: List[Mapping[str, Any]] = []
    monkeypatch.setattr(run_paths, "write_route_switch_marker", lambda work, entry: pending.append(entry))
    with mb.set_route_switch_marker(_writer(tmp_path)):
        _run_route(TEST_UNCERT_POINT, tmp_path, {})
        marker_at_switch = (tmp_path / _marker_name()).is_file()
    assert pending and marker_at_switch is False


def test_mutation_gate_reads_manifest_before_marker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """mutant：續跑閘先讀 registry manifest 再查標記 ⇒ ⑧ 零讀取斷言翻紅（新 registry 建立前見 manifest.json 開檔）。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    symbol, tf = _kline_cell()
    ch, aid = _md5("numview-m-order"), _sha("numview-m-order")
    _factory, leaf = _marker_leaf(tmp_path, symbol, tf, ch, aid)
    real = FeatureFactory._prepare_cgsa_registry

    def manifest_first(self: Any, symbol_: str, tf_: str, config_hash: str = "", algorithm_id: str = "") -> Any:
        with open(leaf / "manifest.json", encoding="utf-8") as handle:
            json.load(handle)
        return real(self, symbol_, tf_, config_hash, algorithm_id=algorithm_id)

    monkeypatch.setattr(FeatureFactory, "_prepare_cgsa_registry", manifest_first)
    events: List[Tuple[str, str]] = []
    with pytest.MonkeyPatch.context() as mp:
        _install_open_spy(mp, leaf, events)
        _isolated(lambda: bare_factory(tmp_path)._prepare_cgsa_registry(symbol, tf, ch, algorithm_id=aid))
    assert any(path.endswith("manifest.json") for path in _reads_before_registry(events, leaf))


def test_mutation_certified_switch_writes_marker(switching: None, monkeypatch: pytest.MonkeyPatch,
                                                 tmp_path: Path) -> None:
    """mutant：已認證換臂亦寫標記 ⇒ ⑧ 已認證續跑案（不得有標記）翻紅。"""
    certified = _certified_points()
    assert certified, "契約無已認證換臂點"
    with mb.set_route_switch_marker(_writer(tmp_path)):
        mb.route(certified[0], [(ORIG_BRANCH, {}), (ALT_BRANCH, {})], label=certified[0], group="g1")
    assert not (tmp_path / _marker_name()).exists()
    real = mb._record_route_switch

    def also_marker(point: str, original: str, original_params: Any, branch: str, *a: Any, **k: Any) -> Any:
        out = real(point, original, original_params, branch, *a, **k)
        run_paths.write_route_switch_marker(tmp_path, {"point": point, "group": "g1", "to": branch})
        return out

    monkeypatch.setattr(mb, "_record_route_switch", also_marker)
    with mb.set_route_switch_marker(_writer(tmp_path)):
        mb.route(certified[0], [(ORIG_BRANCH, {}), (ALT_BRANCH, {})], label=certified[0], group="g1")
    assert (tmp_path / _marker_name()).is_file()


def test_mutation_ic_cache_ignores_route_identity(base: GenRun, unc: GenRun, registry_path: Path,
                                                  h5_writes: List[str], monkeypatch: pytest.MonkeyPatch,
                                                  tmp_path_factory: pytest.TempPathFactory) -> None:
    """mutant：IC 快取比對略過路由身分（身分解析之路由鍵改為常數）⇒ ⑧ 快取案（只差路由身分之複本不沿用）翻紅。"""
    rk = _route_key()
    variant = _route_variant(base, unc, tmp_path_factory.mktemp("numview_m_route_variant"))
    real = rp.resolve_run_identity
    empty = _route_empty()

    def no_route(manifest: Mapping[str, Any], artifact_kind: str) -> Any:
        return dataclasses.replace(real(manifest, artifact_kind), **{rk: empty})

    assert patch_everywhere(monkeypatch, "resolve_run_identity", real, no_route) >= 1
    case = _ingest_pair_case(base.features_root, variant, base.handle, registry_path, h5_writes)
    assert case["h5_rewritten"] is False


def test_mutation_resume_then_switch_omits_own_switch(scen_resume_then_switch: Dict[str, Any], unc: GenRun,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：續跑後換臂之 run 漏記本 run 之換臂（路由身分只由沿用群組組成＝無換臂之空值摘要）⇒ ⑧ 續跑後換臂案翻紅。"""
    rerun: GenRun = scen_resume_then_switch["rerun"]
    assert _route_values(_manifest(rerun)) == _route_values(_manifest(unc))
    real = nv.route_identity
    monkeypatch.setattr(nv, "route_identity", lambda records: real([]))
    omitted = nv.route_identity([_rec(s["point"], "numview_group", s["to"], s["from"]) for s in _layer2_switches(rerun)])
    assert omitted != _route_values(_manifest(unc))[0]


def _d6_refuses(base: GenRun, tmp_root: Path, monkeypatch: pytest.MonkeyPatch) -> bool:
    """D6 oracle：葉身分相符而 L7 manifest 記另一 algorithm_id ⇒ 不續跑。"""
    aid0 = _manifest(base)[_manifest_keys()["algorithm_id"]]
    return _d6_case(tmp_root, base, requested_aid=aid0, l7_aid=_sha("numview-other-algorithm"),
                    monkeypatch=monkeypatch) == 0


def test_mutation_resume_gate_ignores_algorithm_id(base: GenRun, monkeypatch: pytest.MonkeyPatch,
                                                   tmp_path_factory: pytest.TempPathFactory) -> None:
    """mutant：續跑閘不比 `algorithm_id`（以包裝使閘所讀之 L7 manifest `algorithm_id` 恆等於本次）⇒ ③ 之 D6 案翻紅。"""
    root = _copy_root(base.root, tmp_path_factory.mktemp("numview_m_d6"))
    real = FeatureFactory._prepare_cgsa_registry
    mk = _manifest_keys()

    def ignore_algorithm(self: Any, symbol: str, tf: str, config_hash: str = "", algorithm_id: str = "") -> Any:
        path = self._storage.feature_run_dir(symbol, tf, config_hash) / ph.MANIFEST_NAME
        l7 = json.loads(path.read_text(encoding="utf-8"))
        l7[mk["algorithm_id"]] = algorithm_id
        for node in (l7.get("artifacts") or {}).values():
            if isinstance(node, dict):
                node[mk["algorithm_id"]] = algorithm_id
        path.write_text(json.dumps(l7), encoding="utf-8")
        return real(self, symbol, tf, config_hash, algorithm_id=algorithm_id)

    monkeypatch.setattr(FeatureFactory, "_prepare_cgsa_registry", ignore_algorithm)
    assert _d6_refuses(base, root, monkeypatch) is False


def test_mutation_run_identity_missing_new_key_rejected_by_to_dict() -> None:
    """mutant：RunIdentity 漏本票新鍵 ⇒ `to_dict` 之契約比對拋 `ProvenanceError`（既有機制）。"""
    new = set(RAW["run_identity_new_keys"])
    assert new, "契約 run_identity_new_keys 為空"
    fields = [(f.name, Any) for f in dataclasses.fields(rp.RunIdentity) if f.name not in new]
    mutant_cls = dataclasses.make_dataclass("RunIdentityMissingNewKey", fields, frozen=True)
    instance = mutant_cls(**{name: None for name, _t in fields})
    with pytest.raises(rp.ProvenanceError):
        rp.RunIdentity.to_dict(instance)


def _head_check_object(obj: Any, schema: Dict[str, Any], label: str) -> None:
    """改前（不遞迴）之 `_check_object`（survivor_contract.py:252-273 語意），且不對 ff_run_identity 內層另驗。"""
    if "ff_run_identity" in label:
        return
    if not isinstance(obj, dict):
        raise ContractValidationError(f"{label}: expected object, got {type(obj).__name__}")
    keys = schema["keys"]
    if schema.get("additional_properties") is False:
        unknown = sorted(set(obj.keys()) - set(keys.keys()))
        if unknown:
            raise ContractValidationError(f"{label}: unknown keys {unknown}")
    for key, spec in keys.items():
        if key not in obj:
            if spec.get("required", True):
                raise ContractValidationError(f"{label}: missing required key {key!r}")
            continue
        value = obj[key]
        if value is None:
            if not spec.get("nullable", False):
                raise ContractValidationError(f"{label}.{key}: null not allowed")
            continue
        if not sc._TYPE_CHECKS[spec["type"]](value):
            raise ContractValidationError(f"{label}.{key}: type mismatch")


def test_mutation_check_object_not_recursive(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`_check_object` 改回不遞迴（並移除內層驗證呼叫）⇒ ⑥ 缺 `algorithm_id` 案被收（翻紅）。"""
    monkeypatch.setattr(sc, "_check_object", _head_check_object)
    assert _survivor_cases()["missing_algorithm_id"] == "accepted"


def test_mutation_survivor_contract_version_not_bumped(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：倖存者契約版本不升（仍為 3）⇒ ⑥ 舊版拒收案翻紅。"""
    contract = copy.deepcopy(sc.load_survivor_contract())
    contract["version"] = OLD_SURVIVOR_VERSION
    monkeypatch.setattr(sc, "load_survivor_contract", lambda *a, **k: copy.deepcopy(contract))
    assert _old_version_rejected() is False
