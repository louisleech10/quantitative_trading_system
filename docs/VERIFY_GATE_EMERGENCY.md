# 驗收防偽閘 — 緊急逃生程序

當 `verification_claim_check.py` 缺失、crash，或 PreToolUse / git hook 導致 **operational HANDOFF 編輯被 fail-closed 鎖死** 時，依下列步驟暫時解除閘門、修復後復原。

> **誠實邊界**：此程序僅供修復 checker/hook 本身；不得用來繞過正常驗收聲稱檢查。`gate_check.sh` 對 parse 失敗為 fail-open，通常不會鎖死 session。

## 1. 解除 git pre-commit / commit-msg hook

若 `git commit` 因 claim checker 失敗：

```bash
# 查看目前 hooks 路徑
git config --get core.hooksPath

# 暫時還原為預設（不再指向 scripts/git_hooks）
git config --unset core.hooksPath
```

修復完成後重新安裝：

```bash
bash scripts/install_verify_hooks.sh
```

## 2. 暫移 Cursor PreToolUse hook

編輯 `.claude/settings.json`，將 `verify_pretooluse` 相關 PreToolUse 項目**暫時移除或註解**（勿刪其他 hooks）。

修復 `scripts/verification_claim_check.py` / `scripts/verify_pretooluse.sh` 後，把 hook 條目加回。

驗證健康狀態：

```bash
bash scripts/verify_hooks_health.sh
```

## 3. 修復後必做回歸

```bash
pytest tests/governance/ -q
bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md   # 若動到 SPEC
bash scripts/reconcile_stamps_check.sh handoffs/<reconcile>.md # 若動到戳記流程
```

## 4. 已知邊界（非本程序能解）

- `git commit --no-verify` 可繞本地 hook；遠端 CI `Verify Claim` workflow 為後盾。
- checker 缺失時 PreToolUse **fail-closed（exit 2）** 為設計行為，需先修復或暫移 hook。
- `gate_check.sh` 無 jq 或 JSON parse 失敗時 **fail-open（exit 0）**，與 PreToolUse 不同。
