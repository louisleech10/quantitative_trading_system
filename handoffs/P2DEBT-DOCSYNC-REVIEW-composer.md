# P2 債開工前文件同步稽核 — Composer 獨立審查
Task-id: p2debt-docsync | Date: 2026-07-11 | Author: Composer

## 方法
依 `handoffs/P2DEBT-DOCSYNC-REVIEW-TASK.md` 自跑全部必做驗證；Claude 產物僅作線索，結論以本人 receipt 為準。

---

## 實跑 receipt

### 1. `git status --short` + `git diff --stat`
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
`git diff --stat`: 8 files changed, 88 insertions(+), 19 deletions(-)（與 Claude 一致）。

### 2. `venv/bin/python -m pytest tests/governance -q 2>&1 | tail -5`
```
FAILED tests/governance/test_verify_gate_b5.py::test_b5_spec_fact_receipt_present_passes
FAILED tests/governance/test_verify_gate_b5.py::test_b5_spec_pending_confirmation_passes
FAILED tests/governance/test_verify_gate_b5.py::test_b5_existing_verify_gate_spec_still_passes
FAILED tests/governance/test_verify_gate_redteam.py::test_r7_gate_task_id_appends_committee_dispatch
======================== 9 failed, 140 passed in 37.96s ========================
```
完整 FAILED 清單（`grep FAILED`）：b4×3 + b5×5 + r7×1 = **9 failed**。與 HANDOFF P2 債票 1 及 Claude 記載一致。

### 3. `cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"`
```
11
```
11 顆全在 feature-factory 測試檔（`run_lifecycle.test.tsx`×2、`RunManagerPanel.batchDeleteWhole.test.tsx`×2、`useFeatureFactory.batchDate.test.ts`×4、`runExplorer.test.ts`×1、`featureFactoryStore.test.ts`×2）。新增 1 顆為 `run_lifecycle.test.tsx(88,57)` `CompletionQueueItem` 缺 `source`（Claude D-2 所指）。

### 4. Golden 測試（裁定用）
```
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py tests/momentum/Analysis/test_ic_1eb_b5_golden.py -q
→ 20 passed in 471.54s
```
（cut1 2 + B5 golden 18）

### 5. Golden meta SHA 鏈（本人實算）
```
shasum baseline_old → fd932a6e…
shasum baseline_new → 35e15ce9…
working-tree baseline_meta.json baseline_sha256 → fd932a6e…（與檔案一致）
HEAD baseline_meta.json baseline_sha256 → 963ba4f210f…（與現行 baseline 檔 **不一致**）
```
結論：4 檔 diff **未改 baseline JSON 本體**；meta 是在把 SHA 校正到磁碟上既有 baseline，並補 `config_override` / repro 字串。

---

## D-1 / D-2 / D-3 裁定

### D-1: HANDOFF L34「未 commit 殘留」過時
**AGREE**（附一處小誤）

| 項目 | 本人核對 | 裁定 |
|------|----------|------|
| `.gitignore` +3 行 | `git diff` 確認 `ic1eb_newpath_freeze/` 與 `.bak.*/` | 應入版（1e+1b B5 收尾漏 commit） |
| golden 4 檔 | 見下節 golden 裁定 | 應入版（條件見下） |
| `scripts/ic1eb_b5_replay.py` / `ic1eb_g2_golden_diff.py` | untracked；`IC1EB-SIGNOFF-composer.md` PROVENANCE_NOTE 已標須入庫 | 應入版 |
| `.claude/gate/*.log` | modified | 慣例入版可接受 |
| `frontend/handoffs/run_receipts/` | **僅 1 檔** `20260710T205101Z-ic1eb-b4-npm-build.json`（Claude 表寫「2 檔」不精確） | 搬遷建議仍成立 |
| `.claude/settings.json` | modified | 維持不 commit |

HANDOFF L34 確實不完整；Claude 殘留表實質正確。

### D-2: tsc 10 → 11
**AGREE**

- HANDOFF P2 債票 3 寫「10 errors」；實測 **11**。
- 根因合理：B4 審查期（`IC1EB-B4-REVIEW-codex.md`）記 10；其後型別或測試檔新增 1 顆 `source` 缺欄。
- 票目標應改寫為「修掉 feature-factory 測試檔全部既存 tsc errors（實測 11）」。

### D-3: ROADMAP L42 ①e+1b「重簽中」落後
**AGREE**

- ROADMAP L42 現文：「Codex 簽核輪抓 fail-open 洞修復後**重簽中**」。
- `handoffs/IC1EB-SIGNOFF-R4-codex.md` 存在；HANDOFF 頂部記三方全 PASS、epic 閉合。
- 應更新為「三方簽核全 PASS 閉合(2026-07-11)」。

---

## Golden 4 檔入版裁定

**SAFE**（附一項 provenance 建議，不構成 BLOCK）

### 理由
1. **baseline 本體未動**：`baseline_old_*.json` / `baseline_new_*.json` 不在 `git diff`；深比測試 `test_ic_1a_cut1_golden.py` **2 passed**。
2. **屬 1e+1b B5/F5 簽核範圍**：`IC1EB-B5-REVIEW-R2-codex.md` F5a/F5b 已 CLOSED（顯式 `ic_train_test_split` False/True、meta SHA 實算相符、golden 2p）。`IC1EB-GOLDEN-DIFF.md` 涵蓋 G-2（1e+1b HAC/FDR 腿），與 cut1 1a golden 為不同腿但同 epic 收尾。
3. **改動語意正確**：
   - `config_override` 顯式化 → 回應 SCAR「凍結腳本隱形參數」；測試本來就 `split_on=False/True` 顯式傳入。
   - meta `baseline_sha256` 校正 → 修正 HEAD meta（963ba…）與磁碟 baseline（fd932a…）長期不一致的 provenance 債，非重凍內容。
   - subset 重用 guard → 防意外重 materialize。
   - timeout 1200→1800 → 與 `ic1a_cut1_original_regen` receipt 一致，屬操作參數。
4. **B5 golden 18 passed** → 1e+1b 回歸鏈在相鄰腿仍綠。

### 保留意見（不翻轉 SAFE）
- diff **刪除** `rebaseline_reason` / `rebaselined_at`（HEAD 有、working tree 無）。建議入版 commit 時**恢復**這兩欄或改寫進 `notes`，避免 1-align B2 重凍脈絡滅失；這是 meta 文檔品質問題，不是 baseline byte 變更。

### 與「baseline 唯讀 / 越權重凍前科」對照
- 本次 diff 是 **meta+freeze 腳本誠實化**，不是第三次無簽核重凍 baseline JSON。
- 前科（`ic1a_cut1_refreeze_quarantine`）已由 `original_regen/` 歸檔；現行改動與 R4 F5c「顯式 override + 正確 repro」方向一致。

---

## `frontend/handoffs/` 搬遷建議

**妥當**

- 合約：receipt 應在根目錄 `handoffs/run_receipts/`（見 misplaced 檔 `log_path` 已指向該路徑但 json 落在 `frontend/handoffs/`）。
- 根目錄已有同 claim 較晚一輪 `20260710T205126Z-ic1eb-b4-npm-build.json`（不同 receipt_id、不同 command_sha）；205101Z 為獨立早輪，**應搬入而非覆蓋**。
- 搬遷後刪除 `frontend/handoffs/` 空殼，避免再誤放。

---

## 漏列項（Claude 未點名）

1. **ROADMAP L42 內嵌 P2 債 session 字串仍寫「tsc 10 errors」**——與 HANDOFF D-2 同源，ROADMAP 亦需同步改 11（或「全部既存 tsc errors」）。
2. **Claude D-1 表「frontend/handoffs 2 檔」**——實測僅 1 個 json；若預期含 `.log`，該 log 不在 `frontend/handoffs/`（可能在根 `handoffs/run_receipts/` 或未產）。
3. **審查任務產物本身 untracked**：`P2DEBT-DOCSYNC-REVIEW-TASK.md`、`P2DEBT-DOCSYNC-claude.md`——屬本輪工作檔，P2 開工 commit 時一併入版即可（非文件過時，但殘留清單可選列）。

其餘 HANDOFF P2 四票結構、governance 細目、1c facts-asked、RULEIMPL park 狀態——本人核對無新差異。

---

## 對 Claude 自產版總評
三項主差異（D-1/D-2/D-3）本人獨立驗證後均成立；殘留處置方向合理。golden 入版判定可接受；建議 commit 時恢復 meta 的 `rebaseline_reason`/`rebaselined_at` 並修正 ROADMAP 內嵌 tsc 計數。

Verdict: APPROVE
