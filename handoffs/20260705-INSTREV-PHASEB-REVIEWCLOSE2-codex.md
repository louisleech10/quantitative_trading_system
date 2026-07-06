# REVIEWCLOSE2 — Phase B REVIEW-1

正在做: Phase B 原 reviewer Codex 閉合重驗 REVIEW-1（checker 對非 UTF-8 staged markdown traceback crash）。
結論: REVIEW-1 CLOSED；Composer 修法以 binary-safe git blob read 將非 UTF-8 staged blob 轉為 FileReadError，main 回 exit 2 並印清楚訊息。
條件①: PASS；手工 tmp repo staged `docs/bad.md` bytes `616263ff2020200a` 後跑 `python scripts/verification_claim_check.py --staged` → `EXIT=2`，stderr `verification_claim_check.py: cannot read docs/bad.md: not valid UTF-8 (staged blob)`，`TRACEBACK_COUNT=0`。
條件②: PASS with known pre-existing red；`pytest tests/governance/test_precommit_autofix.py -q` → 7 passed；`pytest tests/governance/test_verify_gate*.py -q` → 9 failed, 115 passed，失敗組與 HANDOFF 記錄 pre-existing governance 9 failed 一致；`git diff --exit-code -- tests/governance/test_verify_gate*.py` → `DIFF_EXIT=0`。
條件③: PASS；新測 `test_staged_non_utf8_md_checker_exit_2_graceful` 斷言 returncode 2、stderr 含 `cannot read docs/bad.md`/`not valid UTF-8 (staged blob)`、不含 `UnicodeDecodeError`/`Traceback`；還原 binary-safe staged read 會回到 subprocess/text decode crash 形態而 FAIL。
全 governance: `pytest tests/governance/ -q` → 9 failed, 140 passed；新增 Phase B 測試皆在 failure 前後顯示 passed，9 紅為既有 b4/b5/r7 類治理債，非 REVIEW-1 closure 新紅。
未改: 未 git checkout；未改根 `HANDOFF.md`；未改 `.claude/gate/audit.log`；測試使用 tmp repo，gate 測試由 pytest tmp/GATE_DIR 隔離。
待辦: Claude 可接續處理既有 governance 9 紅；本 REVIEW-1 無待修。
阻塞: none。
本次決策: 對 REVIEW-1 給 CLOSED；整體 VERDICT: APPROVE。
踩坑提醒: `VAR=... source venv/bin/activate && pytest ...` 不等同全程 export env；本次關鍵非 UTF-8 closure 使用手工 tmp repo receipt，不依賴該 env 寫法。

ASSUMPTIONS_VERIFIED: 非 UTF-8 staged md 不再 traceback；UTF-8 gate 測試檔斷言未被改；新測能證偽舊 crash 路徑。
TESTS_RUN: 見上列命令與摘要。
FAILURES_SEEN: `test_verify_gate*.py`/全 governance 既有 9 紅，未在本 review 中修。
SCOPE_CHANGES: none；只寫本 output 檔。
NUMERIC_OR_SCHEMA_IMPACT: none。
STATUS: DONE
