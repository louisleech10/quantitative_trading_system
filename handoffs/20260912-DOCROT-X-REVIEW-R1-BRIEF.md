# DOCROT R2 五項落地之審碼——主委自實作、無人審過

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷／輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 本輪審的是**已 commit 的實作**，不是規格。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`scripts/brief_conformance_check.sh`（佔位偵測段）、`scripts/spec_count_audit.py`（`_RE_TOTAL_ITEMS` 與 `dupes()`）、`scripts/spec_xref_hook.sh`（③ warn-only 段）、`scripts/gov_check.sh`（段 1b 內新增呼叫）、`scripts/new_brief.sh`（審查標的骨架）、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:16` 區段、`templates/TODO_GENERATION_PROMPT.md:41` 區段、`tests/governance/test_docrot_e3_brief_placeholder.py`、`tests/governance/test_docrot_f2_total_items_count.py`
- **本輪 diff**：`git diff 44bbd8d3..HEAD -- scripts/ templates/ tests/governance/ docs/SPLITUNIFY_SPEC.D-002.md`
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 之修訂沿革段（`HISTORY-BEGIN`～`HISTORY-END`）。finding 之 source anchor 落在歷史段者不受理。

## 本輪的由來（請先讀，這是你們要判的核心）
R2 三家共同結論含一條程序修正，主委當場接受：**凡主委產出「非任一家原文」之折衷，自動開一輪 consult，不得由主委單方生效**。
主委在本輪實作中**至少自創五項、一輪 consult 都沒開**：
1. `brief_conformance_check.sh` 的「骨架佔位偵測」——三家談的是 E3 審查輸入隔離與 E2 派工邊界掛載，**沒有任何一家提過用佔位字面當判準**。
2. `spec_count_audit.py --dupes`（同一字面出現在多行）——三家的窄 F2 逐字是「只數『共 N 條』形態」，**多行重複偵測是主委自行擴張的形態**。
3. `dupes()` 在 `HISTORY-BEGIN` 處停止掃描——**主委自訂**，無任何委員文字支持。
4. 產出端警告層併進既有 `spec_xref_hook.sh` 而非在 `.claude/settings.json` 新增條目——E2 原文是「PostToolUse 警告」，**併入既有 hook 是主委的成本考量**。
5. F1 活文收縮**只做 `docs/SPLITUNIFY_SPEC.D-002.md` 一份**就宣告到收斂點——三家未限定範圍。
使用者當面指控：「你自己做完，然後還持續讓人以為這些都經過委員審查，涵蓋範圍和閘門也只做部分就說做了」。本輪即為補審。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: 本輪實作 commit 範圍為 `44bbd8d3..HEAD` → 實跑 `git log --oneline 44bbd8d3..HEAD`，8 筆。
fact-verified: 兩支 DOCROT 測試檔共 15 passed → 實跑 `venv/bin/python -m pytest tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_f2_total_items_count.py -q`。
fact-verified: `docs/` 下 200 個 `.md`，其中 132 個命中 `spec_xref_hook` 之觸發集合（`SPEC|TODO|PLAN|RECON`），68 個不命中 → 實跑 `ls docs/ | grep -cE`。
fact-verified: 治理回歸（19 檔）30 failed／523 passed；同組檔在乾淨 HEAD worktree 為 35 failed／512 passed，逐檔失敗數相同 → 兩次實跑比對。
assumed: 「併進既有 hook 所以一般寫檔零成本」——主委**只有** codex R2 對既有八支鏈的 4.39–4.97 秒量測，**沒有實測自己新增這一支的延遲**。請直接攻這條。
assumed: 「沿革段略過不會漏掉真缺陷」——主委沒有任何反例證明沿革內的重複字面一定無害。請直接攻這條。
assumed: 「F1 只做 D-002 一份，足以在下一張中大票驗成效」——若下一票不是 D-002 系列，成效判準可能根本測不到。請直接攻這條。
assumed: 「骨架佔位偵測對手寫 brief 零誤擋」——僅以封閉字面集推論，未跑既有 651 份 brief 的 replay。請直接攻這條。

## 必答（逐條 verdict）
1. 上列自創五項逐項判定：是否屬「非任一家原文之折衷」？主委跳過 consult 是否構成違反 R2 程序修正？哪幾項應被**推翻或改寫**？
2. 現行配置對主因 D1（同一決定手寫進多個無索引落點）的**實際覆蓋率**：唯一硬擋是派工當下的佔位檢查，而主委可以不派工、直接自己寫文檔就完全繞過。請給可證偽的評估，不要只給定性判斷。
3. R2 第 4 項遷移序定「第一期只 warn」。但主委在本輪已示範「警告擋不住自己」。該條是否仍成立？若否，**最小可行的擋門形態**是什麼（限制：不得要求新 epic、不得要求新腳本檔）？
4. D3（三閘 rc=0 不代表無語意互斥）、D4（停輪判準機械化）、R2 E8 Phase B（單檔決定表＋`narrow_check_router` 一列）三項完全沒做。以「下一張中大票」為期，哪一項**應該先做**？請排序並各給一條可驗收判準。
5. 主委的 commit 訊息以「三家共同結論」「依 `CODEX-R1-P1-02`」為標題，但實作無任何委員審過。這種表述是否構成 `verification_claim_check` 同型的不實宣稱？是否需要、且**能否**做成機械閘？
6. 可以進下一步嗎，還是有 BLOCKING 必須先修？

## 產出
canonical 四欄 findings ＋ **Verdict**。**禁改碼**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
