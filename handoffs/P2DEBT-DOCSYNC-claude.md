# P2 債開工前文件同步稽核 — Claude 自產版
Task-id: p2debt-docsync | Date: 2026-07-11 | Author: Claude

## 目的
P2 債 session 開工前,確認 HANDOFF.md / docs/ROADMAP.md 與 repo 實況一致;列出需更新項與未入版殘留處置建議,交 Grok+Composer 雙審。

## 實測 receipt(Claude 本機實跑,2026-07-11)
- `git status --short`:8 modified + 3 untracked(見下)。
- `venv/bin/python -m pytest tests/governance -q` → **9 failed, 140 passed**(b4×3 + b5×5 + redteam r7×1)——與 HANDOFF P2 債票 1 記載一致。
- `cd frontend && npx tsc --noEmit | grep -c "error TS"` → **11**(HANDOFF 記 10;全在 feature-factory 測試檔不變)。

## 發現的文件差異(3 項)

### D-1: HANDOFF L34「未 commit 殘留:.claude/settings.json(使用者本機)」過時
實際殘留:
| 檔 | 內容 | 建議處置 |
|---|---|---|
| `.gitignore` | +3 行(B5 newpath freeze reports ignore,G-2 可重產) | 入版(1e+1b 收尾漏 commit) |
| `tests/golden/ic_phase1_1a_cut1/` 4 檔 | G-OLD `config_override={"ic_train_test_split": False}` 顯式化+meta sha 重算+timeout 1200→1800+subset 重用 guard;freeze_baseline.py 內註記 dated 2026-07-11 | 入版(屬 1e+1b G-1/G-OLD 簽核內容;1067 綠含 golden 測試可證與現行 baseline 一致)——**請委員特別確認此判定**,golden 區敏感(baseline 唯讀鐵律+1a 越權重凍前科) |
| `scripts/ic1eb_b5_replay.py` + `scripts/ic1eb_g2_golden_diff.py` | G-1/G-2 重放/凍結腳本(未追蹤) | 入版(鐵律:golden 產物須入版否則滅失無解;.gitignore 註解明說「G-2 腳本可重產」預設腳本存在) |
| `.claude/gate/audit.log` / `verify_audit.log` | gate 稽核尾錄 | 隨本次 commit 入版(慣例) |
| `frontend/handoffs/run_receipts/` 2 檔 | B4 npm build receipt(20260710)——執行端寫錯位置(合約=根目錄 handoffs/) | 搬到 `handoffs/run_receipts/` 後入版;frontend/handoffs/ 刪除 |
| `.claude/settings.json` | 使用者本機(鍵序重排+2 條實驗 allow 行) | 維持不 commit(HANDOFF 既有記載,保留) |

### D-2: HANDOFF P2 債票 3「tsc 既存 10 errors」→ 實測 11
差 1 顆:`run_lifecycle.test.tsx(88,57)` TS2741 `CompletionQueueItem` 缺 `source`。無論 10/11,票目標改寫成「修掉 frontend feature-factory 測試檔全部既存 tsc errors(實測 11)」。

### D-3: ROADMAP L42 ② 1e+1b 狀態落後
現文寫「Codex 簽核輪抓 fail-open 洞修復後**重簽中**」;HANDOFF 記 R4 已全 PASS 且 epic 閉合 SIGNOFF:IC1EB-SIGNOFF-R4-codex.md。應更新為「三方簽核全 PASS 閉合(2026-07-11)」。

## 確認無誤項
- governance 9 紅細目(b4×3/b5×5/r7×1)與修法方向記載正確。
- P2 債四票結構、1c 前置與 facts-asked 預登記無需改。
- ROADMAP P2 各節(preset 盤點/統計嚴謹度/Agent-readable)無新差異。

## 委員審查請求
1. 驗證上表 receipt(可自跑 git status/pytest tests/governance/tsc)。
2. **裁定 golden 4 檔入版判定是否成立**(vs 應退回/隔離)。
3. 檢查我是否漏列殘留或漏更新文件(HANDOFF/ROADMAP 以外若有牽連檔請點名)。
4. Verdict: APPROVE / BLOCK(附反例)。
