"""NUMVIEW 重型跑之機械前置（docs/NUMVIEW_SPEC.md §C「重型跑紀律」、Task 0.4，R2-B）。

`scripts/numview_freeze_baseline.py` 與本目錄每個呼叫生成入口之探針，於主入口內、任何生成呼叫之前呼叫
`require(run_kind, cells)`：估時收據（`handoffs/run_receipts/<date>-numview-estimate.json`）不存在、無
`reported_at`（主委白話報使用者後寫入）、或所請格不在收據該跑別之格清單（`cells` 格 id ∪ `preprov_cells` PRE-PROV 格名）
⇒ 拋 `EstimateGateError`（不只 log）。Phase 2–4 驗收重產（R15-A）同受此閘：`numview_freeze_baseline.generate_cell`／
`freeze_cell` 以 `regen_*` 跑別呼叫。測試直接經 `preprov_helpers` 生成之 PRE-PROV 格只由估時收據之 `preprov_cells`
涵蓋檢查（Task 0.4 ①）約束，執行期不經本閘（見 manifest not_executable）。

已實作（NUMVIEW b1，Task 0.4）。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


REPO: Path = Path(__file__).resolve().parents[3]
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"
#: 估時收據檔名樣式（恰一份；多份或零份 ⇒ 拒跑）
ESTIMATE_RECEIPT_GLOB = "*-numview-estimate.json"


class EstimateGateError(RuntimeError):
    """估時前置不成立（收據缺、`reported_at` 缺、格不在收據該跑別之格清單）⇒ 拒跑（SPEC Task 0.4 ②）。"""


def load_estimate_receipt(receipts_dir: Optional[Path] = None) -> Dict[str, Any]:
    """讀估時收據（`receipts_dir` 預設 `RECEIPTS_DIR`；恰一份符合 `ESTIMATE_RECEIPT_GLOB`）；缺或多份 ⇒ `EstimateGateError`。"""
    directory = Path(receipts_dir) if receipts_dir is not None else Path(RECEIPTS_DIR)
    paths = sorted(p for p in directory.glob(ESTIMATE_RECEIPT_GLOB) if p.is_file())
    if len(paths) != 1:
        raise EstimateGateError(
            f"估時收據須恰一份（{directory}/{ESTIMATE_RECEIPT_GLOB}），實得 {[p.name for p in paths]}；"
            "先跑 handoffs/run_receipts/numview_probes/estimate.py 並由主委白話報告後寫入 reported_at")
    try:
        receipt = json.loads(paths[0].read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EstimateGateError(f"估時收據非合法 JSON：{paths[0]}：{exc}") from exc
    if not isinstance(receipt, dict):
        raise EstimateGateError(f"估時收據頂層須為物件：{paths[0]}")
    return receipt


def _reported_at(receipt: Mapping[str, Any]) -> datetime:
    raw = receipt.get("reported_at")
    if not isinstance(raw, str) or not raw.strip():
        raise EstimateGateError("估時收據缺 reported_at（主委白話報告使用者後寫入）；拒跑")
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise EstimateGateError(f"估時收據 reported_at 非 ISO-8601：{raw!r}") from exc


#: 事前登記判準檔（Task 0.3）；估時收據之 `criteria_sha256` 須等於其現行位元組之 sha256
CRITERIA_PATH: Path = REPO / "tests" / "_golden" / "numview" / "preregistered_criteria.json"


def _require_current_criteria(receipt: Mapping[str, Any]) -> None:
    """估時收據須綁現行判準檔（格定義與 RUN_PLAN 皆由判準導出）：`criteria_sha256` 缺或不等 ⇒ 拒跑。
    不綁 HEAD：收據為 Phase 0–4 總成本之事前白話報，綁 HEAD 會使每次提交皆須重跑估時（違使用者 2026-10-16「跑過的結果不准全部重跑」）。"""
    import hashlib

    recorded = receipt.get("criteria_sha256")
    if not isinstance(recorded, str) or not recorded:
        raise EstimateGateError("估時收據缺 criteria_sha256；拒跑")
    try:
        current = hashlib.sha256(Path(CRITERIA_PATH).read_bytes()).hexdigest()
    except OSError as exc:
        raise EstimateGateError(f"判準檔不可讀：{CRITERIA_PATH}：{exc}") from exc
    if recorded != current:
        raise EstimateGateError(f"估時收據之 criteria_sha256 {recorded[:12]}… ≠ 現行判準檔 {current[:12]}…；拒跑（判準變動須重估）")


def require(run_kind: str, cells: Sequence[str], *, receipts_dir: Optional[Path] = None) -> None:
    """重型跑前置（SPEC Task 0.4）：收據存在、含 `reported_at`、且 `cells` 全屬收據 `run_kind` 跑別之格清單，否則拋錯。

    格清單＝該跑別之 `cells`（格 id）∪ `preprov_cells`（PRE-PROV 格名）。未指定任何格亦拒跑（無從核對涵蓋）。
    只拋 `EstimateGateError`，不以 log 代替（mutation：改只 log ⇒ 驗收紅）。"""
    receipt = load_estimate_receipt(receipts_dir)
    _reported_at(receipt)
    _require_current_criteria(receipt)
    requested = [str(c) for c in cells]
    if not requested:
        raise EstimateGateError(f"跑別 {run_kind!r} 未指定任何格；拒跑")
    run_kinds = receipt.get("run_kinds")
    node = run_kinds.get(run_kind) if isinstance(run_kinds, Mapping) else None
    if not isinstance(node, Mapping):
        raise EstimateGateError(f"估時收據無跑別 {run_kind!r}；拒跑")
    listed = {str(c) for c in (node.get("cells") or [])} | {str(c) for c in (node.get("preprov_cells") or [])}
    missing = [c for c in requested if c not in listed]
    if missing:
        raise EstimateGateError(f"跑別 {run_kind!r} 之格不在估時收據之格清單：{missing[:10]}（共 {len(missing)} 格）；拒跑")
