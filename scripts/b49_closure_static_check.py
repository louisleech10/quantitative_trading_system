#!/usr/bin/env python3
"""票 B-49 閉合證據之**靜態可判定子集**（產出端可跑的那一半）。

── 為何存在 ────────────────────────────────────────────────────────────
`docs/GOV_ENFORCEMENT_REGISTRY.md` 之 `E-007`：B-49 由收案退回，重新收案的前置是
「把閉合證據的**靜態可判定部分**前移至產出端」。三家 r1 一致認定該部分
（`CODEX-R1-P1-05`／`COMPOSER-R1-P1-02`／`GROK-R1-P2-01`）**無需 commit 亦可於寫檔當下驗**，
主委原本「單次 Edit 無等價判定」的豁免理由因此被否決。

閉合證據原本整包只掛 pre-push（`_assert_b49_closure_evidence`：逐格於實體隔離副本實跑）。
那一包的**動態部分**（隔離重放、rc／passed／skipped 比對）確實需要可重放標的，掛不上產出端；
但**靜態部分**只需要讀原始碼：

  ① selector 清單本身完整（六格、無重複、與 receipt 契約鍵集合相等）
  ② 每一格都有**實質斷言**（≥1 個可達的 `assert` 或 `pytest.raises`）

這兩條在寫檔當下就判得出來 ⇒ 本檔把它們抽出來，掛 `PostToolUse`。

── 單一來源 ────────────────────────────────────────────────────────────
🔴 `tests/governance/test_govb1_contract_matrix.py` **從本檔 import** 這些定義，
   不另抄一份。改判準只改這裡；兩邊分岔的風險由 import 消滅。

── 誠實邊界（逐條，不誇大）────────────────────────────────────────────
1. 本檔**不取代** `_assert_b49_closure_evidence`。隔離重放仍在 pre-push，
   兩者是 defense-in-depth，不得因本檔存在而放寬那一層。
2. `assert True` 仍會通過。只防**意外掏空與重構失手**，不防蓄意
   （SPEC §C-6 已具名排除；與整套 B-49 機制同一邊界）。
3. 靜態可達性是**近似**：判不出者一律**計入**（保守方向＝當作可達）。
4. 本檔只看 selector 函式**自身可達 body**；巢狀函式／類別／lambda 內的 assert
   與 `if False:`／`while False:`／`for _ in []:` 的 body 皆為死碼，不計。

用法：
  python3 scripts/b49_closure_static_check.py          # rc=0 通過／1 不通過
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# 票 B-49 之閉合證據：六格具名 selector（SPEC/TODO Task 2.3）。
# 🔴 **逐字列出**——改名或刪除任一格即紅（`CODEX-R1-P1-02`：不得以整檔 exit 0 充當證據）。
_B49_CLOSURE_FILE = "tests/governance/test_govb49_path_grant.py"
_B49_CLOSURE_SELECTORS = (
    "test_v12_body_has_no_skip_escape",
    "test_v12_four_kinds_all_visited",
    "test_stamp_path_invalid_implementer_turns_red",
    "test_impl_path_works_for_every_cli_family",
    "test_dispatch_set_equals_review_families",
    "test_review_families_subset_of_eligible",
)
# 每格的**固定** receipt 契約（六格皆非參數化 ⇒ 各恰 1）。寫字面，不由集合長度導出。
_B49_CLOSURE_EXPECTED = {
    "test_v12_body_has_no_skip_escape": 1,
    "test_v12_four_kinds_all_visited": 1,
    "test_stamp_path_invalid_implementer_turns_red": 1,
    "test_impl_path_works_for_every_cli_family": 1,
    "test_dispatch_set_equals_review_families": 1,
    "test_review_families_subset_of_eligible": 1,
}


def _b49_selector_is_substantive(src: str, fn: str) -> bool:
    """具名 selector 是否**有實質斷言**（≥1 個 `assert` 或 `pytest.raises`）。

    〔`CODEX-R2-P0-01` 第二病；主委反向驗證實測命中〕
    把 selector 的 body 換成只剩 docstring，它照樣 `1 passed` ⇒ 只驗 rc/passed
    擋不住「掏空」。本函式以 AST 檢查該函式**自身**的 body。

    🔴 **誠實邊界**：`assert True` 仍會通過。本檢查只防**意外掏空與重構失手**，
    不防蓄意（SPEC §C-6 已具名排除；與整套 B-49 機制同一誠實邊界）。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False

    # 🔴 只認**模組層**同名定義，且須恰好一個〔`CODEX-R3-P0-01` 探針 2〕：
    #    `ast.walk` 取到的是**第一個**，而 Python 實際生效的是**最後一個**
    #    ⇒ 「前面放真的、後面放空的」可騙過檢查。數量不等於 1 一律 fail-closed。
    defs = [
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn
    ]
    if len(defs) != 1:
        return False

    def _static_truth(node: ast.AST):
        """靜態可判定之真假值；判不出回 None（**不猜**）。"""
        if isinstance(node, ast.Constant):
            return bool(node.value)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and not node.elts:
            return False
        if isinstance(node, ast.Dict) and not node.keys:
            return False
        return None

    # 🔴 只看**自身可達 body**〔`CODEX-R3-P0-01` 探針 1、`CODEX-R4-P0-01` 探針 1–3〕：
    #    ① 巢狀函式／類別／lambda 內的 assert 是死碼
    #    ② `if False:` / `while False:` / `for _ in []:` 的 body 靜態不可達，同樣是死碼
    #    判準是「**靜態可證不會執行**者不計」——封閉可導出，不是關鍵字黑名單。
    #    誠實邊界：靜態可達性是**近似**；判不出者一律**計入**（保守方向＝當作可達）。
    def _own_nodes(node: ast.AST):
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
            ):
                continue
            if isinstance(child, ast.If):
                truth = _static_truth(child.test)
                branches = (
                    child.body + child.orelse
                    if truth is None
                    else (child.body if truth else child.orelse)
                )
                for stmt in branches:
                    yield stmt
                    yield from _own_nodes(stmt)
                continue
            if isinstance(child, ast.While) and _static_truth(child.test) is False:
                for stmt in child.orelse:
                    yield stmt
                    yield from _own_nodes(stmt)
                continue
            if isinstance(child, ast.For) and _static_truth(child.iter) is False:
                for stmt in child.orelse:
                    yield stmt
                    yield from _own_nodes(stmt)
                continue
            yield child
            yield from _own_nodes(child)

    for sub in _own_nodes(defs[0]):
        if isinstance(sub, ast.Assert):
            return True
        if isinstance(sub, ast.With):
            for item in sub.items:
                call = item.context_expr
                if isinstance(call, ast.Call):
                    name = getattr(call.func, "attr", None) or getattr(
                        call.func, "id", None
                    )
                    if name == "raises":
                        return True
    return False


def check_static(repo: Path | None = None) -> list[str]:
    """回傳問題清單（空 list ＝ 通過）。純靜態，不跑任何測試、不碰 git。"""
    root = repo or REPO
    problems: list[str] = []

    # ① 清單自身完整性〔`CODEX-R4-P1-02`：只斷言長度會被「同一格重複六次」騙過〕
    if len(_B49_CLOSURE_SELECTORS) != 6:
        problems.append(f"selector 數量應為 6，實為 {len(_B49_CLOSURE_SELECTORS)}")
    if len(set(_B49_CLOSURE_SELECTORS)) != len(_B49_CLOSURE_SELECTORS):
        dup = sorted(
            {s for s in _B49_CLOSURE_SELECTORS if _B49_CLOSURE_SELECTORS.count(s) > 1}
        )
        problems.append(f"selector 清單有**重複**（漏驗其餘格）：{dup}")
    if set(_B49_CLOSURE_EXPECTED) != set(_B49_CLOSURE_SELECTORS):
        problems.append(
            "selector 清單與 receipt 契約鍵集合漂移："
            f"多={sorted(set(_B49_CLOSURE_EXPECTED) - set(_B49_CLOSURE_SELECTORS))} "
            f"少={sorted(set(_B49_CLOSURE_SELECTORS) - set(_B49_CLOSURE_EXPECTED))}"
        )

    # ② 每格須有實質斷言
    path = root / _B49_CLOSURE_FILE
    if not path.is_file():
        problems.append(f"閉合證據檔不存在: {_B49_CLOSURE_FILE}（缺檔 fail-closed）")
        return problems
    src = path.read_text(encoding="utf-8")
    for fn in _B49_CLOSURE_SELECTORS:
        if not _b49_selector_is_substantive(src, fn):
            problems.append(
                f"閉合證據 selector 無實質斷言或定義不唯一: {_B49_CLOSURE_FILE}::{fn}"
            )
    return problems


def main() -> int:
    problems = check_static()
    if problems:
        print("B49 CLOSURE STATIC CHECK FAIL:", file=sys.stderr)
        for p in problems:
            print(f"  · {p}", file=sys.stderr)
        print(
            "  修：閉合證據是票 B-49 的關票前提，掏空或改名等於把關票證據抽掉。"
            "  完整（含隔離重放）之檢查仍在 pre-push。",
            file=sys.stderr,
        )
        return 1
    print(f"B49 CLOSURE STATIC OK: {len(_B49_CLOSURE_SELECTORS)} 格 selector 皆有實質斷言")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
