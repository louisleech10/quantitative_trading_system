"""數值政策、臂／算法 fingerprint 與 view 身分之單一實作（docs/NUMVIEW_SPEC.md Task 0.1／2.1／4.1／4.3）。

純函式、無狀態：讀契約 `momentum/FeatureEngineering/contracts/numeric_view.json`（SPEC §C 契約單一真相源）、
解析 post-IC 各入口之正式臂、於臂分派前驗證前處理數值政策（空 zscore 窗、縮尾 method 封閉值集、缺 `method` 鍵）、
自前處理設定＋環境＋能力旗標解析 run 之數值 fingerprint 與 `algorithm_id`、`config_hash` 鹽、事後路由身分、
IC 頁第三步之 view 身分。值集、鍵名與正規化規則一律取自契約，本模組不另列舉（SPEC §C、Task 0.1「不可做」）。
`api/` 只經本模組與 `momentum.factories` 取用，不自組身分、不自判臂（SPEC §C 解耦）。

本檔為 TODO 階段空殼：函式體一律 `raise NotImplementedError("<Task ID>")`，由對應 Task 實作。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

CONTRACT_PATH: Path = Path(__file__).resolve().parent / "contracts" / "numeric_view.json"


class NumericPolicyError(ValueError):
    """非法數值政策之具名拒收（SPEC §C D3；Task 0.1 契約缺段、Task 2.1 空窗／未知 method／缺鍵）。

    API 入口轉 422；Python 入口原樣上拋。契約檔缺段時 `load_contract` 亦拋此型別（不回預設；Task 0.1 邊界①）。"""


class NumericContextUnresolvedError(RuntimeError):
    """硬體自動解析之值不可解析（SPEC Task 4.1：`FFACT_MEMORY_TIER=auto` 而 psutil 不可用或查詢拋錯、slow-path
    自動判定或 n_jobs 取 tier 失敗）⇒ fingerprint 解析拒收，提示以環境明設 tier；不得以預設值代替。
    名稱登記於契約 `auto_resolutions`（Task 4.1）。"""


class ICViewIdentityMismatchError(RuntimeError):
    """IC 頁第三步之載入 run 身分與 IC 任務報告 metadata 之 `ff_run_identity` 逐鍵不等（run 已於 IC 後重生；
    SPEC Task 4.3）。"""


def load_contract() -> Dict[str, Any]:
    """讀契約 JSON（每次讀檔、不快取）；SPEC Task 0.1 所列必要段任一缺 ⇒ `NumericPolicyError`（邊界①，不回預設）。"""
    raise NotImplementedError("NUMVIEW Task 0.1")


def post_ic_arm(entry: str) -> str:
    """post-IC 入口（契約 `post_ic_entries` 之鍵，如 `ic_first`、`ic_page_apply_transforms`）之正式臂；
    `arm_ref` 型入口解析至被引用入口之臂（Task 3.4 起 IC 頁引用 `ic_first`）。未知入口 ⇒ `NumericPolicyError`。
    SPEC Task 0.1（`ic_first_context.POST_IC_ARM` 於 Task 2.2 起改讀本函式）。"""
    raise NotImplementedError("NUMVIEW Task 0.1")


def validate_preprocessing_policy(config: Mapping[str, Any]) -> None:
    """於臂分派前驗證前處理設定（dict 或 `model_dump()` 形）；規則全讀契約（SPEC Task 2.1）：
    zscore 啟用而窗清單為空或含非正整數 ⇒ 拒收；縮尾 method 不屬契約 `winsor_method_values`（區分大小寫）⇒ 拒收；
    縮尾啟用而缺 `method` 鍵 ⇒ 依契約 `winsor_method_missing_key` 處置。違反 ⇒ `NumericPolicyError`。
    `enabled=false` 之步驟不驗其窗或 method（邊界①）。"""
    raise NotImplementedError("NUMVIEW Task 2.1")


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
