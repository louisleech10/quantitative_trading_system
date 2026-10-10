"""TESTREG §G 記錄器不變性基準（docs/TESTREG_SPEC.md §G、Task 1.3）：凍結與比對收據之產生器。

用法（主工作樹、repo 根；單組串行；跑完 `bash scripts/restore_golden_inventory.sh`）：
  venv/bin/python handoffs/run_receipts/testreg_probes/recorder_invariance.py freeze   # Task 1.3 動工前、記錄器未掛載之 HEAD
  venv/bin/python handoffs/run_receipts/testreg_probes/recorder_invariance.py verify   # 記錄器掛載後之同命令
收據：freeze ⇒ handoffs/run_receipts/testreg-recorder-baseline.json；verify ⇒ handoffs/run_receipts/testreg-recorder-verify.json。

收據欄（tests/registry/test_testreg_recorder.py::test_g_recorder_invariance_receipts 讀之）：
  sample（凍結清單：test_framepath_disposition.py、test_mutation_scope_extension.py、tests/api 依路徑字典序前 10 檔）、
  sample_rule（字面「tests/api 依路徑字典序前 10 檔（凍結時之 git ls-files）」）、command（argv 陣列：
  `venv/bin/python -m pytest -p no:cacheprovider -v <sample…>`）、head、recorder_loaded（本次 session 是否載入記錄器：
  以執行前後 `.testreg/ledger` 檔數差判定）、ledger_sessions_written、outcomes_sha256（排序後之「nodeid outcome」列之
  sha256）、order_sha256（-v 輸出之 nodeid 序列之 sha256）、rc、porcelain_sha256_without_testreg（`git status
  --porcelain --ignored` 去除 `.testreg/` 開頭之列後之 sha256）。執行前一律以 restore_golden_inventory.sh 還原清冊副作用。

TODO 凍結之介面（docs/manifests/TESTREG.json）：本檔目前只含介面；第 1 批實作（freeze 須於記錄器掛載之提交之前執行）。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[3]
BASELINE_REL = "handoffs/run_receipts/testreg-recorder-baseline.json"
VERIFY_REL = "handoffs/run_receipts/testreg-recorder-verify.json"
FIXED = ["tests/feature_engineering/test_framepath_disposition.py", "tests/governance/test_mutation_scope_extension.py"]


def sample() -> List[str]:
    """FIXED ＋ `git ls-files 'tests/api/test_*.py'` 依路徑字典序前 10 檔。"""
    raise NotImplementedError("TESTREG Task 1.3 §G")


def run_once(files: List[str]) -> Dict[str, object]:
    """執行一次並回傳收據欄（見模組說明）。"""
    raise NotImplementedError("TESTREG Task 1.3 §G")


def main(argv: List[str]) -> int:
    raise NotImplementedError("TESTREG Task 1.3 §G")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
