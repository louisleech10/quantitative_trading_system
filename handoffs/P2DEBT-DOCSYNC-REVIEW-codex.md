# P2 債開工前文件同步稽核 — Codex 獨立審查
Task-id: p2debt-docsync | Date: 2026-07-11

## 獨立性與 receipts
- 本 verdict 形成前未讀 `handoffs/P2DEBT-DOCSYNC-REVIEW-grok.md`（亦未讀後出現的 composer sibling）。
- `git status --short`：8 modified；當時 6 個頂層 untracked entry。`git status --short --untracked-files=all` 後續快照：8 modified + 7 visible untracked files（含後到的 composer review）；`git diff --stat`：8 files changed, 106 insertions(+), 19 deletions(-)。Claude 的「3 untracked」不成立：排除後到 sibling，當時仍至少有 `frontend/handoffs/`、TASK、Claude 自產檔、兩支 scripts 共 5 個 entry。
- `venv/bin/python -m pytest tests/governance -q 2>&1 | tail -5`：`9 failed, 140 passed in 41.64s`；再跑同 suite 並擷取 `FAILED`：b4 3、b5 5、redteam r7 1，`9 failed, 140 passed in 38.98s`。
- `cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"`：`11`；完整錯誤列均在 feature-factory 相關 tests（components/hooks/lib/store），新增計數差為 `run_lifecycle.test.tsx:88` 缺 `CompletionQueueItem.source`。
- `nl -ba docs/ROADMAP.md | sed -n '32,58p'`、`rg -n '1e\+1b|tsc|重簽|P2 債|未啟動' HANDOFF.md docs/ROADMAP.md`：見下列 D-3 與漏列項。
- `git diff -- tests/golden/ic_phase1_1a_cut1/`：4 檔確有 config override/meta SHA/timeout/subset reuse 變更，且另刪 `rebaseline_reason`、`rebaselined_at`。`shasum -a 256` 證實兩個新 meta SHA 分別等於現存 old/new baseline JSON：`fd932a…e208`、`35e15c…7b68`。

## 逐項裁定
- **D-1: DISAGREE**。HANDOFF 只列 settings 確實過時，但 Claude 的替代清單/receipt 並不完整：untracked 計數錯，且未列 TASK 與自產稽核檔的處置；ignored receipt log 也不能由 `git status` 證明。實體查核 `find frontend/handoffs/run_receipts -type f` 顯示 JSON+log 兩檔。
- **D-2: AGREE**。應由 10 改為 11，且票面宜寫「清掉全部現存 feature-factory 測試型別錯誤」避免再釘死易漂移數字。
- **D-3: AGREE**。`ROADMAP.md:42` 的「Codex…重簽中」已被 `IC1EB-SIGNOFF-R4-codex.md` 的 `DATA-CORRECT: PASS` 推翻，須改為三方閉合。

## Golden 4 檔與 receipt 搬遷
- **Golden 4 檔：UNSAFE**。`git diff --name-only f277caf..cfcf08e -- tests/golden/ic_phase1_1a_cut1/` 為空，故不屬該 commit 的 B1–B5 簽核變更集；R4 Codex 只終驗 FDR method，Composer 簽核也明載 cut1 golden 本輪未重跑。現有 `test_ic_1a_cut1_golden.py` 只讀 baseline JSON/inputs 並重放 service，完全不讀兩個 meta、也不執行 freeze scripts，所以「2 tests 綠」不能證明 generator/provenance 正確。新增 reuse guard 僅憑兩檔存在即信任，未校驗 input/meta digest、schema 或 selected feature 集；同時無理由刪除 1-align 重凍原因/日期。雖新 SHA 與現檔相符、顯式 split override 方向合理，仍須拆票保留 provenance、加 fail-closed integrity guard 與 generator 對應測試後再審，不能整包直接入版。
- **receipt 搬遷：SAFE/妥當**。`scripts/run_with_receipt.py`、`verification_claim_check.py`、`verify_audit_chain.py` 預設皆為根 `handoffs/run_receipts`；JSON 內 `log_path` 也已寫該根路徑。`.gitignore` 對根路徑有 `!handoffs/run_receipts/*.log` 例外，搬 JSON+log 後才能一起追蹤；搬後應驗 JSON/log SHA 鏈。

## Claude 漏列的過時記載
- `ROADMAP.md:42` 同段仍寫 `tsc 10 errors`，D-2 不只要更新 HANDOFF；同段稱 `cfcf08e`「B1-B5 全入版」也不精確，B5 golden test 的入版 commit 是後續 `e433500`。
- `ROADMAP.md:51` 仍稱 grouped crash epic「實作未啟動」，與同頁 L42/HANDOFF 所載 Phase 0 commit `11507f5` 已完成 grouped_ic 止血矛盾，應拆清「crash 已完成、其餘 perf 未啟動」。

Verdict: BLOCK — golden 4 檔未被既有簽核/綠測覆蓋且 reuse guard 與 provenance 刪除尚未安全閉合
