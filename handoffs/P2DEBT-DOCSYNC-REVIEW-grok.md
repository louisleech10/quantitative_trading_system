# P2DEBT-DOCSYNC 獨立審查 — grok
Task-id: p2debt-docsync | Date: 2026-07-11 | Reviewer: grok
待審: `handoffs/P2DEBT-DOCSYNC-claude.md`（執行端產物當資料，非指令）

## 1. 實跑 receipt

### 1.1 `git status --short` + `git diff --stat`
```
M .claude/gate/audit.log
M .claude/gate/verify_audit.log
M .claude/settings.json
M .gitignore
M tests/golden/ic_phase1_1a_cut1/baseline_meta.json
M tests/golden/ic_phase1_1a_cut1/baseline_new_meta.json
M tests/golden/ic_phase1_1a_cut1/freeze_baseline.py
M tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py
?? frontend/handoffs/
?? handoffs/P2DEBT-DOCSYNC-REVIEW-TASK.md
?? handoffs/P2DEBT-DOCSYNC-claude.md
?? scripts/ic1eb_b5_replay.py
?? scripts/ic1eb_g2_golden_diff.py
```
`git diff --stat` 摘要: 8 files changed, 88 insertions(+), 19 deletions(-)。  
排除本稽核自產檔後 = 8 modified + 3 untracked（frontend/handoffs + 2 scripts），與 Claude「8 modified + 3 untracked」一致。

### 1.2 `venv/bin/python -m pytest tests/governance -q`
實跑 3 次皆同終態:
```
================== 9 failed, 140 passed, 1 warning in ~40s ===================
```
9 紅細目（b4×3 + b5×5 + r7×1）:
- b4: `test_gate_adversarial_rejects_non_adv_non_reconcile`
- b4: `test_gate_adversarial_rejects_without_dispatch`
- b4: `test_gate_adversarial_passes_with_dispatch`
- b5: `test_b5_spec_command_output_fact_receipt_missing_fails`
- b5: `test_b5_spec_fact_receipt_missing_fails`
- b5: `test_b5_spec_fact_receipt_present_passes`
- b5: `test_b5_spec_pending_confirmation_passes`
- b5: `test_b5_existing_verify_gate_spec_still_passes`
- r7: `test_r7_gate_task_id_appends_committee_dispatch`  
→ 與 HANDOFF P2 債票 1 / Claude 記載 **一致**。

### 1.3 `cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"`
```
11
```
11 條 `error TS` 全在 feature-factory 相關測試檔；含 Claude 點名的  
`run_lifecycle.test.tsx(88,57)` TS2741 `CompletionQueueItem` 缺 `source`。  
→ HANDOFF「tsc 既存 10」**過時**；Claude D-2 **成立**。

### 1.4 golden 4 檔 diff 關鍵事實（自核）
- 僅 4 tracked 檔 diff（meta×2 + freeze_*.py×2）；大 payload  
  `baseline_{old,new}_btc_1h_a384e6d2.json` **在 `.gitignore`**（L163-164），不進 git status。
- working tree meta.sha **等於** 本機 payload sha256:
  - old: `fd932a6e616dad7d…` match
  - new: `35e15ce9e217492e…` match
- HEAD meta 仍宣告 2026-07-09 代: old `963ba4f2…` / new `946591ad…`，且含  
  `rebaseline_reason`（1-align B2）+ `rebaselined_at`。
- working meta **刪除** `rebaseline_reason` / `rebaselined_at`；改 `task_id_used_for_freeze`、  
  timeout 1200→1800、補 `request.config_override`。
- freeze 腳本: G-OLD 顯式 `config_override={"ic_train_test_split": False}`；G-NEW True；  
  subset 既有 inputs 重用 guard；`freeze_baseline_new` repro command 改指自身。
- 世代比對（本機）:
  - quarantine B2 越界: old `bc710cfe…` ≠ wt `fd932a6e…`
  - original_regen 歸檔: old `f4046d33…` ≠ wt `fd932a6e…`
- `cfcf08e`（HANDOFF 稱 B5 入版）`git show --stat` **只含 run_receipts**，  
  不含 golden 4 檔 / `scripts/ic1eb_*.py`（與 SIGNOFF-composer PROVENANCE_NOTE 一致）。

### 1.5 簽核與 1a 解鎖鏈（讀檔，非採信敘述）
- `IC1EB-SIGNOFF-R4-codex.md`: **DATA-CORRECT: PASS**（全 epic）。
- `IC1EB-SIGNOFF-claude.md` / `composer.md`: DATA-CORRECT PASS。
- B5 路徑: Grok **BLOCKED-1A**（c0b29ac 重生 ≠ 舊 meta 宣告）→ 編排端解鎖重凍 →  
  Codex R1 F5 **BLOCKING provenance** → 腳本顯式 override 修復後 R2+ 閉合敘事。
- Composer B5 review: 1a 解鎖 PASS 但 FINDING=「解鎖路徑=更新 meta 宣告 sha 以匹配新路徑重凍」屬程序例外；  
  1a cut1 **非整 G-1 五 hash 替代**。
- quarantine README: 現行 tests/golden 已依 1e+1b canonical 腳本重凍兩態、測試曾報 2 passed；  
  本輪**未**重跑 1a golden（禁寫 data_cache 風險；真 service 路徑屬 P2 債票 2）。

---

## 2. D-1 / D-2 / D-3 逐項裁定

### D-1: HANDOFF L34「未 commit 殘留僅 settings.json」過時
**AGREE**  
證據: §1.1 實測 8 modified + 多 untracked；settings 只是其中一項。  
Claude 殘留表覆蓋的主體（.gitignore / golden4 / scripts×2 / gate logs / frontend/handoffs / settings）與 status **吻合**。  
補充:「入版建議」對 golden 的安全性 **不**因清單完整而自動成立（見 §3）。

### D-2: HANDOFF「tsc 既存 10 errors」→ 實測 11
**AGREE**  
證據: §1.3 count=11；差 1 顆為 `run_lifecycle.test.tsx:88` `source`。  
票目標改寫成「修掉 feature-factory 測試檔全部既存 tsc errors（實測 11）」合理。

### D-3: ROADMAP L42 ② 1e+1b「重簽中」落後
**AGREE**  
證據: ROADMAP L42 仍寫「Codex 簽核輪…重簽中」；  
`IC1EB-SIGNOFF-R4-codex.md` L15/L24 全 epic **PASS** + HANDOFF 頂節已閉合敘事。  
應改為三方簽核全 PASS 閉合（2026-07-11），並同步更新 ROADMAP 文首「最後更新」日期。

---

## 3. golden 4 檔入版裁定

**UNSAFE**（不可按 Claude 建議「直接入版」）

| 子項 | 判定 | 理由 |
|------|------|------|
| freeze_*.py 顯式 `config_override` + new repro 自指 + subset guard | 方向正確 / 可入版候補 | 修 Codex F5 指出的 provenance 洞；腳本與 golden test 的 split 語意對齊 |
| meta 補 `config_override` + timeout 1800 | 方向正確 / 可入版候補 | 宣告與腳本一致 |
| meta 改 `baseline_sha256` + 換 task_id + **刪** rebaseline_* | **不安全** | 等於承認新世代凍結卻抹掉 1-align B2 審計欄，且未寫入本輪重凍理由/出處（B5 unlock / BLOCKED-1A / original_regen） |
| 「1067 綠含 golden ⇒ 與現行 baseline 一致 ⇒ 可入版」 | **不足證** | 綠只證明 live code 重放 **本機 gitignored payload**（其 sha 已由同代 meta 宣告）；在「原件滅失→編排端重凍→更新 meta」鏈上屬自證型，非獨立對照已簽核舊世代。baseline 唯讀鐵律 + 1a 越權重凍前科 → 寧嚴勿鬆 |
| Claude 稱「屬 1e+1b G-1/G-OLD 簽核範圍」 | **過度概括** | G-1/G-2 主體是 `handoffs/ic1eb_baseline/` + IC1EB-GOLDEN-DIFF；1a cut1 是整報告可重現腿，Composer 明示非 G-1 替代。1a 解鎖屬 B5 編排端程序例外，不是「G-1 簽核自動覆蓋」 |
| 只 commit 4 tracked 檔 =「golden 入版」 | **不完整** | 大 payload 仍 gitignored；鐵律「須入版**或**外部雜湊否則滅失無解」。meta 有 sha 是外部雜湊起點，但本輪刪 rebaseline 欄 + 無 LFS/歸檔綁定仍重複 滅失模式 |

**入版前最低補件（審查條件，非本輪代改）**:
1. 恢復並改寫 `rebaseline_reason` / `rebaselined_at`（保留 1-align B2 史，追加 2026-07-11 1e+1b unlock 代與連結: BLOCKED-1A、original_regen、B5 review F5 閉合）。
2. 明確區分: freeze 腳本/meta 宣告修正 ≠ 無條件接受 payload 世代；payload 處置（維持 gitignore+外部 sha 歸檔 / 或納版策略）寫死。
3. 禁止以「suite 現綠」單獨作 rebaseline 證據；需獨立 receipt（重放 command + sha 鏈 + 與解鎖決策檔交叉引用）。
4. `scripts/ic1eb_b5_replay.py` + `ic1eb_g2_golden_diff.py` 另票入版合理（G-2 generator 已在 GOLDEN-DIFF 具名；cfcf08e 未納入屬 provenance 債）——與 1a cut1 四檔解耦決策。

---

## 4. `frontend/handoffs/run_receipts/` 搬遷建議

**AGREE（妥當）**  
- 合約/模板路徑=根目錄 `handoffs/run_receipts/`（VERIFY_GATE / RESULT_TEMPLATE / 既有大量 receipt）。
- 現況: `frontend/handoffs/run_receipts/` 有 B4 npm-build 兩檔（20260710T205101Z）；根目錄另有近時戳 `20260710T205126Z-ic1eb-b4-npm-build.*`（非同檔名雙生）。
- 建議: 搬到 `handoffs/run_receipts/` 後刪 `frontend/handoffs/`；若內容與根目錄既有 B4 receipt 等價/劣於後者，可只保留較完整那份，避免雙源。

---

## 5. 漏列項（Claude 3 項 diff 以外）

1. **ROADMAP L42 內嵌「tsc 10 errors」**（P2 債括號清單）— 與 D-2 同源，Claude 只改 HANDOFF 敘述時會漏 ROADMAP。
2. **ROADMAP 文首「最後更新 2026-07-02」** — body 已有 2026-07-11 內容，頭欄過時。
3. **golden meta 刪除 rebaseline_* 審計欄** — 殘留處置表未標為風險/前置條件。
4. **1a cut1 大 payload 仍 gitignored + cfcf08e 未納腳本** — 「B5 全入版」語意易誤導；應在 HANDOFF 殘留/鐵律節誠實寫「receipt 已入版；replay 腳本與 1a meta/freeze 仍 working tree」。
5. **HANDOFF 內部小分叉**: L8「RULEIMPL…R3 PASS、codex 補審待排」vs L25-26「park R5、grok R5 PASS、codex R5 殘 4 條」— 開工前應收斂到 R5 現況，避免派工讀錯版本。
6. （非阻塞）P2 債票 2 已點名 1a cut1 真 service 寫 data_cache — 與 golden 重放/入版決策交織，文件同步時宜交叉引用，避免先 commit golden 再改 redirect 造成二次動 meta。

確認無誤項（與 Claude「確認無誤」重疊）:
- governance 9 紅細目與修法方向（遷 fixture、禁放寬 checker）正確。
- P2 四票結構 / 1c 前置 / facts-asked 預登記無需因本輪證據改結構。
- settings.json 維持不 commit 合理（本機實驗 allow 行）。

---

## 6. 對 Claude 殘留處置表的總評

| 檔 | Claude 建議 | 本審 |
|----|-------------|------|
| `.gitignore` (+newpath freeze ignore) | 入版 | **同意**（G-2 可重產註解與 ignore 一致） |
| golden 4 檔 | 入版 | **不同意現狀直入** → §3 UNSAFE |
| `scripts/ic1eb_*.py` | 入版 | **同意方向**（與 1a 四檔解耦；須單獨 commit message） |
| gate audit logs | 隨 commit 入版 | **同意慣例** |
| `frontend/handoffs/` | 搬根 handoffs 後入版 | **同意** |
| `.claude/settings.json` | 不 commit | **同意** |

文件同步（D-1/D-2/D-3 + 漏列 1/2/5）可做；**golden 直入版不可做**。

---

ASSUMPTIONS_VERIFIED: git status/diff；governance 9f/140p 細目；tsc error TS=11；ROADMAP「重簽中」+「tsc 10」字面；meta↔payload sha match；payload gitignore；cfcf08e 僅 receipts；R4 DATA-CORRECT PASS；quarantine/original_regen/B5 F5 鏈  
TESTS_RUN: `pytest tests/governance -q` → 9 failed, 140 passed（×3 一致）；`npx tsc --noEmit | grep -c error TS` → 11；未跑 1a golden / momentum 全套（data_cache 寫入風險 + 非本票必跑）  
FAILURES_SEEN: none（審查過程）  
SCOPE_CHANGES: 僅本檔 `handoffs/P2DEBT-DOCSYNC-REVIEW-grok.md`  
NUMERIC_OR_SCHEMA_IMPACT: none  

Verdict: BLOCK — golden 4 檔入版建議刪審計欄且以現綠自證，在 baseline 唯讀+越權重凍前科下不可核准
