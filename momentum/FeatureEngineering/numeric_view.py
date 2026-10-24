"""數值政策、臂／算法 fingerprint 與 view 身分之單一實作（docs/NUMVIEW_SPEC.md Task 0.1／2.1／4.1／4.3）。

純函式、無狀態：讀契約 `momentum/FeatureEngineering/contracts/numeric_view.json`（SPEC §C 契約單一真相源）、
解析 post-IC 各入口之正式臂、於臂分派前驗證前處理數值政策（空 zscore 窗、縮尾 method 封閉值集、缺 `method` 鍵）、
自前處理設定＋環境＋能力旗標解析 run 之數值 fingerprint 與 `algorithm_id`、`config_hash` 鹽、事後路由身分、
IC 頁第三步之 view 身分。值集、鍵名與正規化規則一律取自契約，本模組不另列舉（SPEC §C、Task 0.1「不可做」）。
`api/` 只經本模組與 `momentum.factories` 取用，不自組身分、不自判臂（SPEC §C 解耦）。

已實作：`load_contract`、`post_ic_arm`（Task 0.1，NUMVIEW b1）。其餘函式體仍 `raise NotImplementedError("<Task ID>")`，由對應 Task 實作。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

CONTRACT_PATH: Path = Path(__file__).resolve().parent / "contracts" / "numeric_view.json"

#: 契約之必要段名（SPEC Task 0.1「改法」所列段落之結構名，非值集；值一律讀契約）
REQUIRED_SECTIONS = (
    "version", "value_pattern",
    "post_ic_entries", "post_ic_arm_values", "post_ic_arm_reachability", "processed_codec_mapping",
    "cgsa_work_identity", "auto_resolutions", "research_arms", "zscore_windows_policy", "winsor_method_values",
    "winsor_method_missing_key", "selectors", "selector_classes", "capability_flags", "library_versions",
    "algorithm_versions", "fingerprint_sections", "config_hash_salt", "run_identity_new_keys", "manifest_keys",
    "ic_page_output_attrs", "ic_page_response_keys", "ic_page_view_identity",
)
#: 入口之臂政策欄（恰一；SPEC Task 0.1／3.4）
_ENTRY_ARM = "arm"
_ENTRY_ARM_REF = "arm_ref"
_ENTRY_ARM_POLICY = "arm_policy"
#: IC 頁第三步記錄之槽（SPEC Task 2.2；契約 `ic_page_output_attrs`／`ic_page_response_keys` 之鍵；Task 4.3 另增）
_IC_PAGE_RECORD_SLOTS: Tuple[str, ...] = ("arm", "ff_run_identity")


class NumericPolicyError(ValueError):
    """非法數值政策之具名拒收（SPEC §C D3；Task 0.1 契約缺段、Task 2.1 空窗／未知 method／缺鍵）。

    API 入口轉 422；Python 入口原樣上拋。契約檔缺段時 `load_contract` 亦拋此型別（不回預設；Task 0.1 邊界①）。"""


class NumericContextUnresolvedError(RuntimeError):
    """硬體自動解析之值不可解析（SPEC Task 4.1：`FFACT_MEMORY_TIER=auto` 而 psutil 不可用或查詢拋錯、slow-path
    自動判定或 n_jobs 取 tier 失敗）⇒ fingerprint 解析拒收，提示以環境明設 tier；不得以預設值代替。
    名稱登記於契約 `auto_resolutions`（Task 4.1）。"""


class PostICOutputDtypeError(ValueError):
    """post-IC 擇定核心之原生輸出欄 dtype 非 float16／float32（轉 float32 會失真）⇒ 具名拒收、不靜默轉型
    （SPEC Task 3.4 v41；使用者 2026-10-24「legacy＋一律 float32」，前提為數字不變）。"""


class ICViewIdentityMismatchError(RuntimeError):
    """IC 頁第三步之載入 run 身分與 IC 任務報告 metadata 之 `ff_run_identity` 逐鍵不等（run 已於 IC 後重生；
    SPEC Task 4.3）。"""


def load_contract() -> Dict[str, Any]:
    """讀契約 JSON（每次讀檔、不快取）；SPEC Task 0.1 所列必要段任一缺 ⇒ `NumericPolicyError`（邊界①，不回預設）。

    路徑於呼叫時讀模組屬性 `CONTRACT_PATH`（測試接縫）。檔不存在、非 JSON 或頂層非物件亦拋 `NumericPolicyError`。"""
    path = Path(CONTRACT_PATH)
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise NumericPolicyError(f"NUMVIEW 契約不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise NumericPolicyError(f"NUMVIEW 契約非合法 JSON：{path}：{exc}") from exc
    if not isinstance(contract, dict):
        raise NumericPolicyError(f"NUMVIEW 契約頂層須為物件：{path}")
    missing = [section for section in REQUIRED_SECTIONS if section not in contract]
    if missing:
        raise NumericPolicyError(f"NUMVIEW 契約缺必要段 {missing}：{path}")
    return contract


def post_ic_arm(entry: str) -> str:
    """post-IC 入口（契約 `post_ic_entries` 之鍵，如 `ic_first`、`ic_page_apply_transforms`）之正式臂；
    `arm_ref` 型入口解析至被引用入口之臂（Task 3.4 起 IC 頁引用 `ic_first`）。未知入口 ⇒ `NumericPolicyError`。
    SPEC Task 0.1（`ic_first_context.POST_IC_ARM` 於 Task 2.2 起改讀本函式）。

    `arm_policy` 型入口（依環境解析、無固定正式臂；Task 3.4 前之 IC 頁）⇒ `NumericPolicyError`（不以政策值冒充臂）。
    臂值不屬契約 `post_ic_arm_values`、入口臂政策欄非恰一、或 `arm_ref` 循環 ⇒ `NumericPolicyError`。"""
    contract = load_contract()
    entries = {k: v for k, v in contract["post_ic_entries"].items() if not str(k).startswith("_")}
    arms = list(contract["post_ic_arm_values"].get("values") or [])
    seen: list = []
    name = str(entry)
    while True:
        if name not in entries:
            raise NumericPolicyError(f"post-IC 入口未登記於契約 post_ic_entries：{name!r}")
        if name in seen:
            raise NumericPolicyError(f"post-IC 入口 arm_ref 循環：{seen + [name]}")
        seen.append(name)
        node = entries[name]
        fields = [f for f in (_ENTRY_ARM, _ENTRY_ARM_REF, _ENTRY_ARM_POLICY) if isinstance(node, Mapping) and f in node]
        if len(fields) != 1:
            raise NumericPolicyError(f"post_ic_entries.{name} 之臂政策欄須恰一，實得 {fields}")
        field = fields[0]
        if field == _ENTRY_ARM_REF:
            name = str(node[_ENTRY_ARM_REF])
            continue
        if field == _ENTRY_ARM_POLICY:
            raise NumericPolicyError(
                f"post_ic_entries.{name} 為依環境解析之政策（{node[_ENTRY_ARM_POLICY]!r}），無固定正式臂")
        arm = str(node[_ENTRY_ARM])
        if arm not in arms:
            raise NumericPolicyError(f"post_ic_entries.{name}.arm={arm!r} 不屬契約 post_ic_arm_values")
        return arm


def validate_preprocessing_policy(config: Mapping[str, Any]) -> None:
    """於臂分派前驗證前處理設定（dict 或 `model_dump()` 形）；規則全讀契約（SPEC Task 2.1）：
    zscore 啟用而窗清單為空或含非正整數 ⇒ 拒收；縮尾 method 不屬契約 `winsor_method_values`（區分大小寫）⇒ 拒收；
    縮尾啟用而缺 `method` 鍵 ⇒ 依契約 `winsor_method_missing_key` 處置。違反 ⇒ `NumericPolicyError`。
    `enabled=false` 之步驟不驗其窗或 method（邊界①）。

    步驟之啟用預設同 `FeaturePreprocessor` 之讀法：zscore 缺 `enabled` ⇒ 關；縮尾缺 `enabled` ⇒ 開（含整段缺）。
    zscore 啟用而缺 `windows` 鍵 ⇒ 依契約 `non_empty_when_enabled` 拒收（未給即非「非空清單」；審碼 b3 r1——各臂不得再以
    預設窗補值；pydantic 路徑由 `AdaptiveZScoreConfig` 之欄位預設填值，故 model_dump 必帶此鍵）。"""
    if not isinstance(config, Mapping):
        raise NumericPolicyError(f"前處理設定須為 Mapping，實得 {type(config).__name__}")
    contract = load_contract()
    zscore = config.get("adaptive_zscore") or {}
    if not isinstance(zscore, Mapping):
        raise NumericPolicyError("adaptive_zscore 須為物件")
    if zscore.get("enabled", False):
        rules = set(contract["zscore_windows_policy"]["rules"])
        if "windows" not in zscore:
            if "non_empty_when_enabled" in rules:
                raise NumericPolicyError("adaptive_zscore 啟用而缺 windows 鍵（不得以預設窗代替）")
        windows = zscore.get("windows", [])
        if not isinstance(windows, (list, tuple)):
            raise NumericPolicyError(f"adaptive_zscore.windows 須為清單，實得 {windows!r}")
        if "non_empty_when_enabled" in rules and not windows:
            raise NumericPolicyError("adaptive_zscore 啟用而 windows 為空清單（不得以預設窗代替）")
        if "each_positive_int" in rules:
            bad = [w for w in windows if isinstance(w, bool) or not isinstance(w, int) or w <= 0]
            if bad:
                raise NumericPolicyError(f"adaptive_zscore.windows 須皆為正整數，違反者 {bad!r}")
    winsor = config.get("winsorization") or {}
    if not isinstance(winsor, Mapping):
        raise NumericPolicyError("winsorization 須為物件")
    if winsor.get("enabled", True):
        if "method" not in winsor:
            policy = contract["winsor_method_missing_key"]["value"]
            if policy == "reject":
                raise NumericPolicyError("winsorization 啟用而缺 method 鍵（契約 winsor_method_missing_key=reject）")
            raise NumericPolicyError(f"契約 winsor_method_missing_key.value 未知：{policy!r}")
        values = [str(v) for v in contract["winsor_method_values"]["values"]]
        method = winsor["method"]
        if not isinstance(method, str) or method not in values:
            raise NumericPolicyError(f"winsorization.method={method!r} 不屬契約 winsor_method_values {values}")


def reject_bool_items(values: Any, field: str) -> Any:
    """窗清單之型別轉換前檢查（SPEC Task 2.1；審碼 b3 r2–r3，供 pydantic 入口 `AdaptiveZScoreConfig` 與 API
    `ApplyTransformsRequest` 共用）：任何非字串之可迭代容器（list／tuple／set／frozenset／產生器等）先展開為 list，元素含
    bool ⇒ ValueError（pydantic 會把 True 轉成 1；dict 入口之 `validate_preprocessing_policy` 同拒）；非可迭代之值原樣
    回傳交 pydantic 判型別。"""
    if isinstance(values, (str, bytes)) or values is None:
        return values
    try:
        items = list(values)
    except TypeError:
        return values
    if any(isinstance(v, bool) for v in items):
        raise ValueError(f"{field} 須皆為正整數（不得為 bool），實得 {items!r}")
    return items


def ic_page_record_keys() -> Tuple[Dict[str, str], Dict[str, str]]:
    """IC 頁第三步之記錄鍵名（SPEC Task 2.2）：（h5 屬性鍵 `ic_page_output_attrs`, 回應鍵 `ic_page_response_keys`），
    各為 {槽: 鍵名}；本 Task 之槽＝`arm`、`ff_run_identity`。任一槽未填或非非空字串 ⇒ `NumericPolicyError`。"""
    contract = load_contract()
    out = []
    for section in ("ic_page_output_attrs", "ic_page_response_keys"):
        keys = {k: v for k, v in contract[section].items() if not str(k).startswith("_")}
        for slot in _IC_PAGE_RECORD_SLOTS:
            if not isinstance(keys.get(slot), str) or not keys[slot]:
                raise NumericPolicyError(f"契約 {section}.{slot} 未填")
        out.append({slot: keys[slot] for slot in _IC_PAGE_RECORD_SLOTS})
    return out[0], out[1]


def require_post_ic_core(arm: Any) -> str:
    """post-IC 呼叫所傳之 `arm`（SPEC Task 3.4）：須屬契約 `post_ic_arm_values` 且等於擇定核心
    （`post_ic_arm("ic_first")`；IC 頁經 `arm_ref` 引用之）；否則 `NumericPolicyError`（不退回他臂）。"""
    values = list(load_contract()["post_ic_arm_values"].get("values") or [])
    if not isinstance(arm, str) or arm not in values:
        raise NumericPolicyError(f"post-IC arm={arm!r} 不屬契約 post_ic_arm_values {values}")
    core = post_ic_arm("ic_first")
    if arm != core:
        raise NumericPolicyError(f"post-IC arm={arm!r} 非擇定核心 {core!r}（契約 post_ic_entries.ic_first）")
    return arm


def post_ic_output_float32(frame: Any) -> Any:
    """post-IC 輸出一律 float32（SPEC Task 3.4 v41）：只允許原生 float16／float32 欄（轉 float32 無損、值逐位元不變），
    任一欄為其他 dtype ⇒ `PostICOutputDtypeError`（列欄名與 dtype；不靜默轉型）。回新表，不改輸入。"""
    import numpy as np

    allowed = (np.dtype(np.float16), np.dtype(np.float32))
    bad = {str(col): str(dtype) for col, dtype in frame.dtypes.items() if dtype not in allowed}
    if bad:
        raise PostICOutputDtypeError(f"post-IC 原生輸出含非 float16／float32 欄（轉 float32 會失真）：{bad}")
    return frame.astype(np.float32, copy=True)


def executed_post_ic_arm(groups: Mapping[str, Mapping[str, Any]]) -> str:
    """post-IC 一次 `transform_selected` 實際執行之臂（SPEC Task 2.2）：取執行紀錄（`last_post_ic_execution()[1]`）
    各群組之 `arm`，須恰一且屬契約 `post_ic_arm_values`；無群組、多臂或值不屬值集 ⇒ `NumericPolicyError`
    （不以契約政策值或環境推算代替）。"""
    arms = {str(info.get("arm")) for info in groups.values()}
    if len(arms) != 1:
        raise NumericPolicyError(f"post-IC 執行紀錄之臂須恰一，實得 {sorted(arms)}")
    arm = arms.pop()
    if arm not in list(load_contract()["post_ic_arm_values"].get("values") or []):
        raise NumericPolicyError(f"post-IC 執行紀錄之臂 {arm!r} 不屬契約 post_ic_arm_values")
    return arm


def detect_capabilities() -> Dict[str, bool]:
    """能力旗標（契約 `capability_flags`：Polars、numba、scipy、statsmodels 可用性）之實測值（SPEC Task 0.2／4.1；
    供 Task 4.2 寫入端傳入 `resolve_numeric_fingerprint(capabilities=...)`）。"""
    raise NotImplementedError("NUMVIEW Task 4.1")


def resolve_numeric_fingerprint(
    *,
    preprocessing_config: Mapping[str, Any],
    environ: Mapping[str, str],
    capabilities: Mapping[str, bool],
) -> Dict[str, Any]:
    """run 之數值 fingerprint（段之鍵見契約 `fingerprint_sections`；SPEC Task 4.1）：契約政策（各入口臂）、
    `value_affecting` 選擇子之**解析後有效值**（非原始字串；非法值記退回後之有效值並帶 `invalid_env` 標記）、
    能力旗標、函式庫版本、算法版本常數、表示層（codec 開關、float16 判定常數）、硬體自動解析之有效值
    （契約 `auto_resolutions`）。只讀 `environ` 中契約登記之鍵。不可解析之 auto 情境 ⇒ `NumericContextUnresolvedError`。
    執行後觀測之實際臂（`observed_arms`）不入本 fingerprint。"""
    raise NotImplementedError("NUMVIEW Task 4.1")


def algorithm_id(fingerprint: Mapping[str, Any]) -> str:
    """fingerprint 正規 JSON（`sort_keys`、無空白）之 sha256 hex（SPEC Task 4.1）。"""
    raise NotImplementedError("NUMVIEW Task 4.1")


def config_hash_salt(fingerprint: Mapping[str, Any]) -> Dict[str, Any]:
    """`config_hash` 鹽＝fingerprint 去除函式庫版本段（設計選擇①；鹽鍵名與排除段見契約 `config_hash_salt`；
    SPEC Task 4.1／4.2）。"""
    raise NotImplementedError("NUMVIEW Task 4.1")


def route_identity(route_records: Sequence[Mapping[str, Any]]) -> str:
    """run 之事後路由身分（SPEC Task 4.1 ⑨）：全部**未認證**換臂點之〔換臂點、群組、所選臂〕排序後正規 JSON 之
    sha256；只含已認證換臂點（`FeatureFactory.L2_ROUTE_CERTIFIED` 機制所登錄者）之紀錄不入；無未認證換臂 ⇒
    契約 `auto_resolutions` 所定之空值摘要。同一換臂點多次觸發逐次逐群組計入、不去重（邊界⑤）。"""
    raise NotImplementedError("NUMVIEW Task 4.1")


def ic_page_view_id(
    *,
    run_identity: Optional[Mapping[str, Any]],
    transform_config: Mapping[str, Any],
    arm: str,
    algorithm_id: str,
    kept_cols: Sequence[str],
) -> str:
    """IC 頁第三步 view 身分 `view_id`＝sha256(正規 JSON：run 身分、轉換設定、臂、`algorithm_id`、有序 `kept_cols`)；
    組成與正規化規則見契約 `ic_page_view_identity`。`kept_cols` 以原順序入身分（不排序；SPEC Task 4.3、R7-A）。"""
    raise NotImplementedError("NUMVIEW Task 4.3")
