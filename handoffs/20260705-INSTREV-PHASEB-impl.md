# INSTREV-PHASEB-impl（Composer 2026-07-06）

## 正在做
- Phase B 四 Task 實作完成，待 Claude 驗收/commit

## 產出檔
- scripts/check_agent_contract_sync.sh（B1.1 兩層 token+反向檢查）
- scripts/gate_check.sh（B2.1 DENY audit append）
- scripts/git_hooks/pre-commit（B3.1 index-only 尾隨空白 strip）
- scripts/verification_claim_check.py（B3.1 VERIFY-EXEMPT 提示）
- scripts/gate.sh（B4.1 _print_usage）
- scripts/dispatch.sh（B4.1 新建 wrapper）
- tests/governance/test_{sync_check,gate_deny_audit,precommit_autofix,dispatch_wrapper}.py

## TESTS_RUN
```bash
bash scripts/check_agent_contract_sync.sh  # exit 0, stdout 含 ✅
pytest tests/governance/ -q              # 137 passed, 9 failed (pre-existing)
```
- sync check: ✅ 四源關鍵不變式一致
- 新增 22 測全綠；既有 test_verify_gate*.py diff 斷言=0
- **9 FAIL 為 pre-existing**（stash 還原腳本後 b4/b5/r7 同紅，非本批引入）

## 本次決策
- gate_check 保留 `GATE_DIR=".claude/gate"` 行供 redteam 隔離替換，再加 OVERRIDE
- pre-commit 用 pipe 餵 python（避免 `$(git show)` 吞尾隨換行）
- hard-break 判定：剛好兩空白保留，三空白以上 strip

STATUS: DONE
