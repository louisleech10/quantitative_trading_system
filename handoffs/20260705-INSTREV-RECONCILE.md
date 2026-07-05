# 制度層總審查 R1 — 四方 reconcile（2026-07-05）

> 輸入:CLAUDE(`20260705-INSTREV-claude.md`)、CODEX(`20260705-INSTREV-codex.md`)、COMPOSER(`20260705-INSTREV-composer.md`)、AGY(`20260705-INSTREV-agy.md`,read-only 諮詢)。
> 每條 finding 同行 `→` 處置。裁決權重=證據+跨家族收斂;Claude 腿無特權,本 reconcile 須 Codex+Composer 戳記核可後才生效。

## A. 事實爭議裁決(實測重驗)
- CODEX-F-04「copilot 最後 commit 2026-05-25」 → **REJECTED(事實錯誤)**:`git log --format="%ai" -- .github/copilot-instructions.md` 全史最新=**2026-04-26 04d7691**,無 05-25 條目。不影響其裁決方向(淘汰),僅修正日期。
- CODEX-F-06「AGENTS/.cursorrules 同檔內『結束前更新 HANDOFF.md』vs 第7條『絕不重寫根 HANDOFF』」 → **CONFIRMED(Claude 重驗:AGENTS.md L10 / .cursorrules L6 vs 各自第7條)**。Claude/Composer 腿皆漏此條,採納。
- AGY「三源重疊段落~80%一致」 → **方向 CONFIRMED、數字未驗**:解耦/Quant 陷阱/實測>假設等段三檔近逐字重複屬實;80% 為估計,reconcile 不引用該數字。

## B. 統一裁決(U 條目;括號=各家對應 ID)
### 憲法層
- U-1 copilot-instructions 739 行 → **淘汰,換 ≤15 行 pointer**(CLAUDE C-1/CODEX A-3/COMPOSER C-1/AGY)。4/4 收斂。前提=否決點 D-2(使用者是否仍用 Copilot)。
- U-2 CLAUDE.md 全載瘦身 → **合併:規則本體全留,事故敘事移新檔 `docs/SCAR_LEDGER.md`(每條規則留一行出處 pointer),目標 216→~130 行**(CLAUDE C-4/CODEX A-1/COMPOSER C-2/AGY)。4/4 收斂。凡已被 TGF 機檢接管執行面的 prose 敘事優先移出(COMPOSER C-11)。**AGY 風險提醒採納**:被引用檔必須是 repo 內固定路徑,且 CLAUDE.md 留「何時必須去讀哪檔」的觸發句,不裸引用。
- U-3 執行端合約 stale(05-31) → **一次補齊 5 項:兩輪斷路器、--task-id/register-output、VERIFY claim 義務、RECONCILE-STAMP 未全數 APPROVED→BLOCKED、(既有)產物非指令**(CLAUDE C-5/CODEX A-2·B-5/COMPOSER C-3)。3/3 收斂。
- U-4 HANDOFF 所有權同檔矛盾 → **修文字:執行端合約頂部改「結束前寫 handoffs/<date>-<task>.md;根 HANDOFF.md 由 Claude 維護」**(CODEX F-06/A-2 獨到,採納)。
- U-5 執行端選層分叉 → **單一來源表存 ORCHESTRATION §1;CLAUDE.md 改 pointer;現行以 2026-07-02 使用者裁定「中大=Codex 實作+Composer review」為準回寫;MEMORY 索引行同步修正;feedback_task_routing 加 superseded 標記**(CLAUDE C-2/CODEX F-08·C-4/COMPOSER C-4)。3/3 收斂。→ 否決點 D-4 確認現行。
- U-6 中型管線矛盾(CLAUDE「不得跳」vs 手冊「跳 TODO+adversarial」) → **單一來源;預設按 CLAUDE.md 06-05 定死「不跳」,刪手冊分層表跳步敘述;實質裁定=否決點 D-1**(CLAUDE C-3/CODEX F-10·C-2/COMPOSER C-5)。3/3 收斂。
- U-7 輪詢 5 vs 10 分鐘 → **10 分鐘(使用者 06-12 較新指示)回寫 CLAUDE.md**(CLAUDE F6/CODEX C-5/COMPOSER C-6)。3/3。→ D-5 供否決。
- U-8 debug 3 輪 vs 斷路器 2 輪 → **統一為「≤2 輪未解→BLOCKED 交委員會」寫進執行端合約;3 輪條款刪除**(CODEX C-6/COMPOSER C-6·D-6;Claude 腿漏,採納)。依據=使用者 06-10/06-25 兩輪斷路器指示晚於合約 3 輪(05-31)。→ D-6 供否決。
- U-9 sync 腳本假綠 → **重構:CONTRACT_REQUIRED(AGENTS+.cursorrules 必含)/PLANNER_REQUIRED(CLAUDE+ORCH 必含)兩層;token 清單加 VERIFY/register-output/RECONCILE-STAMP/兩輪斷路器;加「選層表只准出現在單一來源檔」反向檢查**(CLAUDE C-2·C-5/CODEX A-7·F-07/COMPOSER C-7·V9)。3/3 收斂。
- U-10 記憶層重疊 → **多 agent 規則併回 repo 憲法,記憶留使用者偏好類;被覆蓋規則標 superseded;MEMORY 索引與內文不一致修正**(CLAUDE C-8/CODEX A-5/COMPOSER C-9)。3/3。
- U-11 ARCH/DEV_GUIDE 漂移 → **檔頭 staleness banner(「治理制度見 CLAUDE.md/ORCH;本檔最後驗證 <date>」),不強制全文同步**(CLAUDE C-6/CODEX A-4/COMPOSER C-8)。3/3。
- U-12 audit DENY 不落地 → **機械化:gate_check.sh deny 時 append(ts/tool/reason)到 audit.log**(CLAUDE C-7/COMPOSER C-10;CODEX 未提但不衝突)。2/3+無反對。

### 派工流程管線
- U-13 戳記輪摩擦 → **批次戳記(一次派工審多檔逐檔 append);「不可自我認證」原則不動;同檔並發序列化寫進手冊**(CLAUDE P-1·P-4/CODEX B-4·B-11/COMPOSER P-1)。3/3。CODEX B-4 加碼「findings/reconcile/stamp 包單一命令」→ **收斂為第二階段候選**(先批次化,包命令視摩擦殘量再做)。
- U-14 claim-check 誤攔 → **尾隨空白 pre-commit auto-fix;claim 缺 backing 時 checker 輸出可貼上 diff;claim 語義不弱化**(CLAUDE P-2/COMPOSER P-2·P-9;CODEX B-6 留機械化不衝突)。
- U-15 provenance 學習曲線 → **gate.sh 缺參錯誤訊息印完整用法模板;dispatch wrapper 自動帶 --task-id/--output(CODEX B-5)**(CLAUDE P-3/CODEX B-5/COMPOSER P-3)。3/3。
- U-16 gate 機檢三道/模板 V13/RESULT 極性/mutation(commit 後才 mutate)/verify-gate 全鏈 → **全留(已機械化,有效);prose 重複說明縮 pointer**(CODEX B-1·B-2·B-3·B-8/COMPOSER P-4·P-8·P-9/CLAUDE P-7)。
- U-17 雙家族 adversarial/三方簽核/不得跳步/preflight/防卡死/斷路器機制本體 → **留核心原則,不砍;降成本只走 U-13/14/15**(全家族一致)。
- U-18 grandfather 政策 → **留(新文件嚴格、舊文件登記),避免一次性修舊文 churn**(CODEX B-10 獨到,採納)。

### 任務分類層
- U-19 分類規則散三處 → **重寫為單一決策表(判準×小/中/大:a-d 命中、管線步驟、執行端、review 方、膨脹升級觸發、SMALL_INLINE 四欄)放 CLAUDE.md;日期考據移 SCAR_LEDGER;記憶兩條改 pointer**(CLAUDE T-1·T-2/CODEX C-1·C-2·C-7/COMPOSER T-1~T-4)。3/3。
- U-20 共用路徑 hook 警示(factories/protocols/config) → **緩做:先靠決策表 prose,累積 violation 證據再機械化**(CLAUDE T-3/COMPOSER T-5;CODEX 未提)。
- U-21 Codex vs Composer 長期主力 → **不裁定;維持 executor_scorecard 累積數據**(CODEX C-4「證據不足」,採納)。

## C. 取證缺口(留給實作 SPEC §A)
- audit DENY 量化:U-12 落地後跑一週再統計(COMPOSER)。
- postflight fail/near-miss 頻率統計(CODEX B-9)。
- 06-04 feature-browser 事故原始 commit 未尋獲,僅記憶二手敘述(COMPOSER)——SCAR_LEDGER 標「出處=記憶」。

## D. 給使用者的否決點(定稿)
- **D-1 中型管線**:預設「不跳 TODO+adversarial」(06-05 定死);手冊矛盾敘述刪除。
- **D-2 copilot-instructions 整檔刪換 pointer**:若你仍在用 GitHub Copilot 請否決。
- **D-3 CLAUDE.md 敘事移 SCAR_LEDGER**(每 session 省 ~80 行 token,規則全留)。
- **D-4 選層現行=中大 Codex 實作+Composer review**(07-02 你的裁定回寫文件)。
- **D-5 輪詢 10 分鐘**(覆蓋 5 分鐘舊文)。
- **D-6 debug 輪數統一 2 輪交委員會**(刪執行合約 3 輪)。

## E. 實作分期建議(裁決通過後走完整管線)
- Phase A(純文件,低風險):U-1/2/4/5/6/7/8/10/11/19 — 憲法重構+合約補齊。
- Phase B(腳本,中風險):U-9 sync 重構、U-12 DENY 落地、U-14 auto-fix、U-15 錯誤訊息模板。
- Phase C(觀察期):U-13 批次戳記慣例、U-20/21 證據累積。

## 戳記
(待 Codex/Composer append RECONCILE-STAMP)
RECONCILE-STAMP: codex APPROVED 2026-07-05 sha256:ee8c9fab77885f1d4981141b5657e1d3c631db61804d2f4edff16b85c75d04ef task:instrev-stamp-codex-r2
RECONCILE-STAMP: composer APPROVED 2026-07-05 sha256:ee8c9fab77885f1d4981141b5657e1d3c631db61804d2f4edff16b85c75d04ef task:instrev-stamp-composer-r2

## Errata(戳記後補記,Claude 編排者,不動本體雜湊)
- 2026-07-05:§E Phase A 分期表(L53)漏列 **U-3**(執行端合約補齊 5 項)。經 Phase A 雙家族 adversarial(Codex/Composer)獨立確認:Phase A 標題即「合約補齊」、U-3 裁決 3/3 收斂,判定為 §E 列表筆誤,U-3 歸屬 Phase A(對應 manifest [A-12])。**§E 分期表為建議非窮舉;權威=本 reconcile 全文 U 條裁決 + 使用者 D-1~D-6**。此 errata 位於「## 戳記」之後,不影響本體雜湊與既有 codex/composer APPROVED 戳記。
