#!/usr/bin/env python3
"""testreg.py — TESTREG 測試清冊：契約驗證、bootstrap、標記、產出端檢查、複查訊號、受影響測試挑選、成效報告。

規格：docs/TESTREG_SPEC.md；契約單一真相源：tests/registry/testreg_schema.json（格式、枚舉、規則 V01–V22、挑選規則、
閘收據欄皆只讀該檔；本檔不存任何枚舉值副本——Task 1.1 驗收以字面計數機檢）。

TODO 凍結之介面（docs/manifests/TESTREG.json）：本檔目前只含簽章，函式體一律 `raise NotImplementedError("<Task>")`，
由各批實作。簽章、具名縫（供 tests/registry/ 之 mutation 置換者）與 CLI 契約不得於實作期更改；需改者回 TODO 重審。

用法（`--repo` 預設＝本檔所在 repo 根；路徑一律 repo 相對 POSIX）：
  testreg.py [--repo R] validate [--require-executed]
  testreg.py [--repo R] bootstrap [--receipt P]
  testreg.py [--repo R] markers
  testreg.py [--repo R] check (--paths P [P ...] | --manifest M | --helpers H [H ...] | --staged)
  testreg.py [--repo R] review
  testreg.py [--repo R] impact --changed-from <git-range|worktree> --manifest M --phase N
  testreg.py [--repo R] effect (--out P [--scope PREFIX ...] | --recompute P)
  testreg.py [--repo R] run --manifest M --phase N --base <rev> --receipt P [--out D] [--max-seconds S]

結束碼：0＝通過；非 0＝不通過或無法判定。不通過之每一項於 stderr 單列輸出，列首為規則 id（`V01`…`V22`）或
`MARKER`／`CATALOG`／`SCHEMA`／`MANIFEST`／`EFFECT`，格式 `<ID> <主體>: <訊息>`；ledger 不在本機而無法驗證者訊息含
`unverifiable`。review／impact 之結果以 JSON 寫 stdout。

具名縫（呼叫端一律於呼叫當下以模組屬性取用，使 `monkeypatch.setattr(testreg, <名>, …)` 生效）：
  - 規則：`rule_v01`…`rule_v22`；`rule_v07` 由 `rule_v07_receipt_valid` 與 `rule_v07_change_requires_receipt` 組成。
  - 斷言多重集合比較：`multiset_decreased`；暫存區變更清單：`staged_changes`；形狀驗證（V17 共用實作）：`validate_shape`。
  - bootstrap 之票代號：`ticket_of`；產出端呼叫者反推：`helper_callers`。
  - 複查訊號：`signal_<名>`，名＝schema `enums.review_signal` 之各值。
  - 挑選：`combine_sources`、`domain_prefix`、`import_closure`、`shared_infra_scope`。
"""
from __future__ import annotations

import argparse
import collections
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

REPO = Path(__file__).resolve().parents[1]
SCHEMA_REL = "tests/registry/testreg_schema.json"
CATALOG_REL = "tests/registry/catalog.json"
RULE_IDS: Tuple[str, ...] = tuple(f"V{i:02d}" for i in range(1, 23))

SignalValue = Union[bool, str]  # True／False／字面 "unknown"


class TestregError(RuntimeError):
    """無法判定（catalog／schema 不存在或不可解析、用法錯誤等）；訊息具名原因與路徑。"""

    __test__ = False  # 名稱以 Test 開頭，防 pytest 誤收集


@dataclass(frozen=True)
class Finding:
    """一項不符。`rule` 為規則 id 或類別字（見模組說明）；`subject` 為 entry 路徑、nodeid、收據或 manifest 路徑。"""

    rule: str
    subject: str
    message: str
    unverifiable: bool = False

    def render(self) -> str:
        """stderr 單列：`<rule> <subject>: <message>`（unverifiable 者訊息含該字）。"""
        raise NotImplementedError("TESTREG Task 1.1")


@dataclass
class Context:
    """一次驗證之受驗之樹與輸入。`tree`＝"worktree"（hook、手動 validate）或 "staged"（pre-commit）；
    `head_catalog` 為 `git show HEAD:tests/registry/catalog.json`（HEAD 無此檔為 None）；`scope_paths` 為 check
    之受檢範圍（None＝全部）。其餘內部欄位由實作自訂。"""

    repo_root: Path
    tree: str
    schema: Dict[str, Any]
    catalog: Dict[str, Any]
    head_catalog: Optional[Dict[str, Any]]
    ledger_dir: Path
    require_executed: bool = False
    scope_paths: Optional[FrozenSet[str]] = None
    extra: Dict[str, Any] = field(default_factory=dict)


# ── Task 1.1：契約與 validate ─────────────────────────────────────────────────────────────────────────


def load_schema(repo_root: Path) -> Dict[str, Any]:
    """讀 `<repo_root>/tests/registry/testreg_schema.json`；不存在或不可解析 ⇒ TestregError。"""
    raise NotImplementedError("TESTREG Task 1.1")


def load_catalog(repo_root: Path, tree: str = "worktree") -> Dict[str, Any]:
    """讀受驗之樹之 catalog（worktree＝檔案；staged＝`git show :tests/registry/catalog.json`）；不存在 ⇒ TestregError。"""
    raise NotImplementedError("TESTREG Task 1.1")


def build_context(repo_root: Path, tree: str = "worktree", *, require_executed: bool = False,
                  scope_paths: Optional[Iterable[str]] = None) -> Context:
    """組 Context；ledger 目錄依 schema `ledger.dir`（相對 repo_root）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def validate(repo_root: Path, *, tree: str = "worktree", require_executed: bool = False) -> List[Finding]:
    """依 schema `validation_rules` 逐條呼叫 `rule_<id>`（呼叫當下以模組屬性取用）；V21 只於 require_executed=True 時
    執行。回傳全部不符（空＝通過）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def validate_shape(value: Any, type_spec: Mapping[str, Any], schema: Mapping[str, Any], where: str = "") -> List[str]:
    """V17 之單一實作：依 type／format／items／items_format／items_enum／min_items／max_items_ref／min／finite／const／
    key_format／additional_properties 與 types.* 遞迴驗形；catalog、summary、收據與閘收據共用。回傳錯誤訊息清單。"""
    raise NotImplementedError("TESTREG Task 1.1")


def multiset_decreased(old: "collections.Counter[str]", new: "collections.Counter[str]") -> List[str]:
    """V19：回傳 old 中計數大於 new 之元素（多重集合減少；非僅比總數）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def assertion_multiset(repo_root: Path, nodeid: str, tree: str = "worktree") -> "collections.Counter[str]":
    """某測試函式（函式層 nodeid）於受驗之樹（"HEAD"／"staged"／"worktree"）之斷言多重集合：依 schema
    `assertion_nodes`（kinds、assertion_helpers、inline_rule、normalize）由 AST 導出；元素帶 provenance 另由實作保存。"""
    raise NotImplementedError("TESTREG Task 1.1")


def e1_hashes(repo_root: Path, nodeid: str, tree: str = "worktree") -> Dict[str, str]:
    """E1 收據三雜湊之單一實作（validate 重算同用）：{"ast": FunctionDef 去名去屬性後 ast.dump 之 sha256,
    "fixture_closure": ..., "module_context": ...}，定義見 schema `receipts.E1.rule`；tree＝"HEAD"／"staged"／"worktree"。"""
    raise NotImplementedError("TESTREG Task 1.1")


def assertion_lines(repo_root: Path, nodeid: str, tree: str = "worktree") -> List[str]:
    """`assertion_multiset` 之 provenance 位置清單（file:line，排序；mutation 收據之 target_assertion_lines 由此導出）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def staged_changes(repo_root: Path) -> Dict[str, str]:
    """暫存區相對 HEAD 之變更：{repo 相對路徑: 狀態字（A／M／D；改名拆為 D＋A）}；pre-commit 之 V07／V19／V20 以此定範圍。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v01(ctx: Context) -> List[Finding]:
    """V01（規則本文見 schema validation_rules）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v02(ctx: Context) -> List[Finding]:
    """V02。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v03(ctx: Context) -> List[Finding]:
    """V03。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v04(ctx: Context) -> List[Finding]:
    """V04。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v05(ctx: Context) -> List[Finding]:
    """V05。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v06(ctx: Context) -> List[Finding]:
    """V06。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v07_receipt_valid(ctx: Context) -> List[Finding]:
    """V07 前半：rewrite_receipt 非 null ⇒ 依 receipts.mutation 全部 rule 與 binding_rule 驗過。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v07_change_requires_receipt(ctx: Context) -> List[Finding]:
    """V07 後半：暫存區中 disposition=rewrite 之檔有內容變更 ⇒ 同提交之 rewrite_receipt 非 null 且驗過。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v07(ctx: Context) -> List[Finding]:
    """V07＝`rule_v07_receipt_valid` ∪ `rule_v07_change_requires_receipt`（兩者皆於呼叫當下以模組屬性取用）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v08(ctx: Context) -> List[Finding]:
    """V08。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v09(ctx: Context) -> List[Finding]:
    """V09。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v10(ctx: Context) -> List[Finding]:
    """V10。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v11(ctx: Context) -> List[Finding]:
    """V11。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v12(ctx: Context) -> List[Finding]:
    """V12。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v13(ctx: Context) -> List[Finding]:
    """V13。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v14(ctx: Context) -> List[Finding]:
    """V14。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v15(ctx: Context) -> List[Finding]:
    """V15。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v16(ctx: Context) -> List[Finding]:
    """V16。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v17(ctx: Context) -> List[Finding]:
    """V17（以 `validate_shape` 對 catalog 全樹與 ledger 紀錄驗形）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v18(ctx: Context) -> List[Finding]:
    """V18。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v19(ctx: Context) -> List[Finding]:
    """V19（以 `assertion_multiset` 與 `multiset_decreased` 判定）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v20(ctx: Context) -> List[Finding]:
    """V20。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v21(ctx: Context) -> List[Finding]:
    """V21（只於 require_executed=True）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def rule_v22(ctx: Context) -> List[Finding]:
    """V22。"""
    raise NotImplementedError("TESTREG Task 1.1")


def manifest_closed(repo_root: Path, manifest: Mapping[str, Any]) -> bool:
    """schema `manifest_status.manifest_closed`。"""
    raise NotImplementedError("TESTREG Task 1.1")


def manifest_tombstone_aware(manifest: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    """schema `manifest_status.manifest_tombstone_aware`（含 gate_cmd_allowed_env／gate_cmd_allowed_options／gate_cmd_parse）。"""
    raise NotImplementedError("TESTREG Task 1.1")


def manifest_selection_strings(manifest: Mapping[str, Any], schema: Mapping[str, Any]) -> List[str]:
    """schema `manifest_selection_keys`：keys 所列鍵下之全部字串（gate_cmd 取 shlex token）＋ prefixed_strings 所定之列
    中之 token；其他欄位之字串不計。"""
    raise NotImplementedError("TESTREG Task 1.1")


# ── Task 1.2：bootstrap ──────────────────────────────────────────────────────────────────────────────


def ticket_of(repo_root: Path, path: str) -> str:
    """schema `bootstrap.ticket_rule`：以 `git log --follow --diff-filter=A` 取最早加入之提交導出票代號；導不出 ⇒ unknown。"""
    raise NotImplementedError("TESTREG Task 1.2")


def bootstrap(repo_root: Path, receipt: Optional[Path] = None) -> Dict[str, Any]:
    """寫 catalog（全部 git 追蹤之測試檔一筆 entry，其餘欄依 `bootstrap.defaults`）與 `bootstrap.paths_file`；冪等。
    回傳 {"entries": int, "unknown": int}；receipt 非 None 時另寫該 JSON（含 unknown 筆數與路徑清單）。"""
    raise NotImplementedError("TESTREG Task 1.2")


# ── Task 1.4：標記 ───────────────────────────────────────────────────────────────────────────────────


def unregistered_markers(repo_root: Path) -> List[Tuple[str, int, str]]:
    """AST 掃描 tests/ 下 `pytest.mark.<name>` 屬性存取（含清單形式 pytestmark；註解與字串不計），對照 pytest.ini
    註冊集合與 pytest 內建集合；回傳未註冊者 (路徑, 行號, 名稱)。"""
    raise NotImplementedError("TESTREG Task 1.4")


# ── Task 1.5：產出端檢查 ─────────────────────────────────────────────────────────────────────────────


def check(repo_root: Path, *, paths: Sequence[str] = (), manifest: Optional[str] = None,
          helpers: Sequence[str] = (), staged: bool = False) -> List[Finding]:
    """產出端檢查（SPEC Task 1.5 改法之規則子集）；只讀 catalog、schema、變更檔清單與其 AST，不呼叫 pytest、不讀 git 全史。"""
    raise NotImplementedError("TESTREG Task 1.5")


def helper_callers(repo_root: Path, helper_path: str, tree: str = "worktree") -> List[str]:
    """tests/ 下非測試檔（conftest、fixtures、helper 模組）變更時，依 `assertion_nodes.inline_rule` 受影響之全部呼叫者
    測試函式（函式層 nodeid，排序）。"""
    raise NotImplementedError("TESTREG Task 1.5")


# ── Task 2.1：複查訊號 ───────────────────────────────────────────────────────────────────────────────


def review(repo_root: Path) -> Dict[str, Dict[str, SignalValue]]:
    """逐 catalog entry 逐訊號：{path: {訊號名: True|False|"unknown"}}；訊號名依 schema `enums.review_signal`，
    每訊號以 `signal_<名>`（呼叫當下以模組屬性取用）判定；不寫回 catalog。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_prod_symbol_gone(ctx: Context, path: str) -> SignalValue:
    """測試檔 import 之生產符號於 HEAD AST 不存在。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_duration_regression(ctx: Context, path: str) -> SignalValue:
    """依 schema `derived.duration_regression_rule`；summary 不存在 ⇒ "unknown"。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_outcome_flip_same_fingerprint(ctx: Context, path: str) -> SignalValue:
    """summary 中同 fingerprint 不同 outcome；summary 不存在 ⇒ "unknown"。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_collect_error(ctx: Context, path: str) -> SignalValue:
    """最近一個收集過該檔之 session 有該檔之 ledger collect_record；ledger 不存在 ⇒ "unknown"。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_allowed_red_owner_closed(ctx: Context, path: str) -> SignalValue:
    """該檔之 allowed_red.json 列之 owner_ticket 於 scripts/fact_keys.json 已完成（查表規則見 SPEC Task 2.1）。"""
    raise NotImplementedError("TESTREG Task 2.1")


def signal_quarantine_expired(ctx: Context, path: str) -> SignalValue:
    """該 entry 有 quarantine 之 expires 早於今日（V11 反例）。"""
    raise NotImplementedError("TESTREG Task 2.1")


# ── Task 2.2：impact ─────────────────────────────────────────────────────────────────────────────────


def impact(repo_root: Path, changed_paths: List[str], must_resolved: List[str],
           previously_failed: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """schema `impact`＋`gate_wiring` 之簽名：catalog、schema、AST 與測試檔集合一律自 repo_root 讀取；
    回傳 {"selected": [{"path", "reasons"}], "excluded": [{"path", "excluded_reason"}]}；catalog validate 失敗 ⇒
    TestregError（不輸出）；不存在使 selected 為空之分支。"""
    raise NotImplementedError("TESTREG Task 2.2")


def combine_sources(sources: Mapping[str, Iterable[str]]) -> Dict[str, List[str]]:
    """{select_reason: 檔集合} → {檔: 排序後之理由清單}（聯集）。"""
    raise NotImplementedError("TESTREG Task 2.2")


def domain_prefix(path: str) -> str:
    """schema `impact.domain_rule` 之 prefix(f)：f 之前兩層路徑（不足兩層取一層）。"""
    raise NotImplementedError("TESTREG Task 2.2")


def import_closure(repo_root: Path, test_path: str) -> FrozenSet[str]:
    """schema `impact.domain_rule` 之 import_closure(t)：repo 內模組之遞移閉包（含函式內 import、星號匯入、
    套件 __init__ 之 re-export），以 repo 相對 .py 路徑表示。"""
    raise NotImplementedError("TESTREG Task 2.2")


def shared_infra_scope(repo_root: Path, changed_path: str, tests: Iterable[str]) -> Optional[FrozenSet[str]]:
    """schema `impact.shared_test_infra`：changed_path 屬共用基礎設施 ⇒ 其作用範圍內之測試檔集合；否則 None。"""
    raise NotImplementedError("TESTREG Task 2.2")


def must_from_manifest(repo_root: Path, manifest: Mapping[str, Any], phase: int) -> List[str]:
    """CLI impact 用：manifest 須含 `affected_tests phase=<phase> ` 列（否則 TestregError）；回傳 `affected_must
    phase=<phase> ` 列之 nodeid 經碑解析（schema `impact.gate_feed` 第一步）後之結果。"""
    raise NotImplementedError("TESTREG Task 2.2")


# ── Task 3.2／4.2：子批閘（SPEC v17 C3）──────────────────────────────────────────────────────────────


def run_subbatch(repo_root: Path, manifest_path: str, phase: int, base: str, *, out: Path, receipt: Path,
                 max_seconds: float = 3600.0) -> int:
    """子批閘：changed_paths＝`git diff --name-only <base>` ∪ 相對 HEAD 之 diff ∪ 未追蹤檔（扣閘之 FP_EXCLUDES）；
    選測＝`impact`（must＝`must_from_manifest`；previously_failed 取自 summary）之 selected，整檔執行；執行器＝
    `framepath_affected_gate.Runner`（分段、`max_seconds` 用盡於呼叫之間停下回 3、同指紋沿用、progress.json）；非綠
    nodeid 於 base 之 detached worktree 重跑同 nodeid，以 `framepath_affected_gate.classify` 歸屬（模組屬性取用）；
    收據寫 receipt；回傳 0＝本子批造成＝0 且無未完成檔、1＝否、3＝暫停。"""
    raise NotImplementedError("TESTREG Task 3.2")


# ── Task 3.3／4.3：成效報告 ──────────────────────────────────────────────────────────────────────────


def effect_report(repo_root: Path, scope: Sequence[str] = ()) -> Dict[str, Any]:
    """由 catalog 碑與 summary 重算（SPEC v17 C9 定義各欄）：retired_functions（碑數）、retired_files（工作樹已不存在
    且其 entry 之函式皆有碑之檔數）、evidence_levels（各等級碑數）、saved_seconds_per_full_run（每一被淘汰函式層 nodeid
    之全部參數化 nodeid 於 summary 中 outcome=passed 紀錄之 duration_s 中位數之和；任一被淘汰 nodeid 無此紀錄 ⇒ 字面
    "unknown"，不寫 0、不外插）；scope 為碑 nodeid 之路徑前綴（空＝全部），記於報告 scope 欄。"""
    raise NotImplementedError("TESTREG Task 3.3")


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口；回傳結束碼（見模組說明）。"""
    raise NotImplementedError("TESTREG Task 1.1")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
