"""防上限 checker（ICPERF SPEC v5.85 Task 0.6 (g)，L3；施工前空殼）。

只檢產品路徑（momentum/、api/、frontend/src/、config/）之新增或修改行，高信心規則：Field／Query 無依據之上界、
逾欄列數即拒、依資料維度降低精度、資料切片直接入統計或持久結果。固定秒數中止計算由既有 NOCAP
`timeout_write_guard` 負責，本 checker 不重複。行內豁免 `# limit-lint: allow=<rule> reason=<理由>`。
兩態：`--mode warn`（只提示）與 `--mode block`（未豁免之 high 命中或 parse_error ⇒ rc 2）。
"""
from __future__ import annotations

from typing import Any, Dict, List


def lint_text(path: str, text: str) -> List[Dict[str, Any]]:
    """回命中清單，每筆 `{"rule", "line", "symbol", "confidence"}`（confidence ∈ {"high", "hint"}）。"""
    raise NotImplementedError("Task 0.6")


def lint_changed(path: str, old_text: str, new_text: str) -> List[Dict[str, Any]]:
    """只回新增或修改行（含既有常數改值）之命中；未修改之舊違例不回。"""
    raise NotImplementedError("Task 0.6")


def main(argv: Any = None) -> int:
    """CLI：`limit_lint.py --mode warn|block [--receipt <語料收據>] [--root <repo 根>] <檔>...`；`--staged` 檢 git 暫存區內容
    （pre-commit 用）。block 模式只阻擋收據（預設 tests/_golden/icperf/limit_lint_corpus_receipt.json）中 status＝block 之規則。"""
    raise NotImplementedError("Task 0.6")


if __name__ == "__main__":
    raise SystemExit(main())
