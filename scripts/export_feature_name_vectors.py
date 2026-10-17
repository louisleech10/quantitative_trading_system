#!/usr/bin/env python3
"""FF-NAME 欄名描述向量匯出腳本空殼（docs/FFNAME_SPEC.md Task 1.2）。

用法（實作後）：
  venv/bin/python scripts/export_feature_name_vectors.py --check            # 重產並與 tests/_golden/ffname/name_vectors.json 逐位元比對；rc 0＝相同
  venv/bin/python scripts/export_feature_name_vectors.py --out <path>       # 產生向量檔至 <path>（不覆寫正式檔）

產生規則（契約落點 `tests/_golden/ffname/contract.json` 之 `descriptor` 段）：
- 合法名：§G reference 全部新名（由 Task 0.1 baseline 之零件以新 formatter 推導）＋契約 `spec_valid_names`；
  每筆描述由 `feature_naming.parse_feature_name` 之身分**重新計算**（不得讀回既有向量檔）。
- 拒收名：契約 `descriptor.rejection_cases` 之每一類至少一筆；描述之錯誤鍵＝`parse_feature_name` 實際拋出之例外類別名。
- 版面：`{version, valid: [{name, descriptor}], rejected: [{name, case, descriptor}]}`；輸出為 canonical JSON（鍵排序）。

本檔為 TODO 落點（介面凍結）；函式體由 FFNAME Phase 1 實作。不得手寫向量。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
VECTORS_PATH = REPO / "tests" / "_golden" / "ffname" / "name_vectors.json"
CONTRACT_PATH = REPO / "tests" / "_golden" / "ffname" / "contract.json"


def build_vectors() -> Dict[str, Any]:
    """依契約與 parser 重新計算向量（不讀既有向量檔）。"""
    raise NotImplementedError("FFNAME Task 1.2")


def write_vectors(out_path: Path) -> int:
    """寫 canonical JSON 至 `out_path`；rc 0 成功。"""
    raise NotImplementedError("FFNAME Task 1.2")


def check(path: Path = VECTORS_PATH) -> int:
    """重產向量並與 `path` 逐位元比對；相同 rc 0，否則列差異 rc 1。"""
    raise NotImplementedError("FFNAME Task 1.2")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="重產並與正式向量檔比對")
    group.add_argument("--out", help="輸出路徑")
    args = parser.parse_args(argv)
    if args.check:
        return check()
    return write_vectors(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
