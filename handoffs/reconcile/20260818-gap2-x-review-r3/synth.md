# Reconcile — 20260818-gap2-x-review-r3

**來源** 20260818-gap2-specadv-r3-codex.md, 20260818-gap2-specadv-r3-composer.md, 20260818-gap2-specadv-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **5 條** findings（codex 1／composer 2／grok 2），下列三個群集**引用全部 5 條，0 掉項**。收斂趨勢：R1 14 → R2 12 → R3 4 條內容 finding（皆為 R2 修訂後之**文字對齊**缺陷，修復 ≤4 行）＋1 條流程 finding（戳記步驟漏跑）。composer／grok 判 L1／L4／L5 閉合、L2／L3 各殘一處字面矛盾；codex 因流程闔門未複核內容。

Verdict：需修補後派工——M1／M2 已寫回 SPEC；M3（戳記）由主委補齊 c1／r1／r2／r3 四份 synth 之三家 RECONCILE-STAMP 後重派 R4（codex 內容複核＋三家確認收斂）。

### M1 — §G-4 之 `case_id` 對照來源與 Task 3.1 ⑮ 不一致（composer／grok；grok 判 BLOCKING）
**引用**: COMPOSER-R3-P1-01, GROK-R3-P0-01

**處置＝接受**：§G-4 改為「`symbol`／`timeframe` ↔ 報告 metadata（缺欄 raise）；`case_id` ↔ `report_ref` 檔名段 `ic_report_{case_id}.json`（不比 metadata）」，與 Task 3.1 ⑮／Task 4.2 同一規則；V-19 之「§G-4 轉紅」語意隨之。實跑 receipt（`metadata.case_id=None`、`symbol=ETHUSDT`、`timeframe=12h`）入 §A。

### M2 — §C 白名單第 3 項／Task 1.0 既有 caller 句／§C ref 句仍寫「report 契約加 reasons」（composer／grok）
**引用**: COMPOSER-R3-P2-01, GROK-R3-P1-01

**處置＝接受**：三處字面統一為「report 契約只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；不加 reasons；reasons 不 ref」，與 Task 1.0／Task 4.1 一字對齊；`grep -n 'reasons 加\|reasons 增鍵' SPEC` → 0。

### M3 — 流程：R1／R2（及 consult）reconcile synth 未經三家 RECONCILE-STAMP（codex；AGENTS Rule 12）
**引用**: CODEX-R3-P0-01

**處置＝接受（主委漏跑戳記步驟；同 GAP-1 R3 之出生事故再犯）**：對 `20260818-gap2-x-consult-r1`／`x-review-r1`／`x-review-r2`／`x-review-r3` 四份 synth 逐份加 `## 戳記` 區段並派三家 stamp 輪（單一 stamp-target／輪，序列執行）；全數 APPROVED 後重派 R4；R4 起每輪 review 後**必**接 stamp 輪。教訓登記於 HANDOFF／白話摩擦記錄。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P0-01

**斷言**: 依 AGENTS Rule 12，本輪所依 R1／R2 reconcile synth 未具全數 `RECONCILE-STAMP: ... APPROVED`，故 R3 adversarial review 不得開始。

**碼證**: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260818-gap2-x-review-r2/synth.md; rc=$?; echo RC=$rc` → `RECONCILE-STAMP FAIL: .../synth.md 缺『## 戳記』區段標題(無法界定本體雜湊範圍)`、`RC=1`；R1 synth 同命令結果亦為相同 fail 與 `RC=1`。`rg -n '^RECONCILE-STAMP:' docs/GAP2_MARGINAL_IC_SPEC.md handoffs/reconcile/20260818-gap2-x-review-r1/synth.md handoffs/reconcile/20260818-gap2-x-review-r2/synth.md` → 無輸出。RECHECK：補齊三方 APPROVED 戳記後重跑兩個 `reconcile_stamps_check.sh` 命令，確認各自 `RC=0`，再重派 R3。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-review-r2/synth.md#f4d34b65ba51；handoffs/reconcile/20260818-gap2-x-review-r1/synth.md#c0786915b314；docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[BLOCKING] 信心度=High。這是開工前的流程闔門，不是對 L1–L5 內容的重議；在戳記未核可前，若繼續審查會違反 Rule 12。修復條件是由授權流程完成 R1／R2 reconcile 的 `## 戳記` 區段與全數 APPROVED stamps，之後重新執行本輪審查。

### 必答 1：L1–L5

未判定。Rule 12 在內容複核前阻塞；本檔不宣稱 L1、L2、L3、L4 或 L5 已閉合，也不提出新的 SPEC finding。

### 必答 2：新引入風險

未評估。除上述可重現的 reconcile 前置阻塞外，本輪沒有在未核可前提下對 SPEC 內容宣稱新風險。

### 必答 3：預算預設 200 vs 真實 fixture

未執行 `run_analyze()` 或真實 fixture 預算探針；沒有可誠實貼出的 survivors／removed 數值，避免在 blocked 狀態下捏造或誤宣稱驗證完成。

### 必答 4：可進 TODO？BLOCKING 清單

不可進 TODO。BLOCKING 清單只有 `CODEX-R3-P0-01`：R1／R2 reconcile stamps 未核可。解除前不進行 SPEC 內容收斂判定。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、指定 R3 brief、review template、R1/R2 synth、R2 codex review；R1/R2 `reconcile_stamps_check.sh` 均實跑 `RC=1`，且三個審查標的未找到 APPROVED stamp。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260818-gap2-x-review-r2/synth.md; rc=$?; echo RC=$rc` → fail／RC=1；R1 synth 同命令 → fail／RC=1；`bash scripts/gate.sh dispatch; rc=$?; echo RC=$rc` → fail／RC=1（OPEN debt）；指定 `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r3-codex.md --family codex` 在 PreToolUse 啟動前被 gate 攔截，未取得 completeness script rc。
FAILURES_SEEN: reconcile 前置檢查兩次 fail，原因均為缺少 `## 戳記` 區段；completeness 命令被 PreToolUse 以 OPEN debt 攔截，未進行內容修訂或實作測試。
SCOPE_CHANGES: 僅新增本指定 review／handoff 產出檔；未改 SPEC、TODO、程式碼、測試或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none；未執行或修改產品數值、schema、輸出大小。
TMP_CLEANUP: 實查 `/tmp`（`/tmp -> /private/tmp`）後不存在 `/tmp/workdir`，亦無需刪除的 workdir 項目；未觸碰或刪除 `claude-501`。
OUTPUT_FILE: handoffs/20260818-gap2-specadv-r3-codex.md
TASK_ID: 20260818-GAP2-X-REVIEW-R3
STATUS: BLOCKED — reconcile 未核可
## COMPOSER-R3-P1-01

**斷言**: L3 已將 `case_id` 對照改為 `report_ref` 檔名段（Task 3.1 ⑮／Task 4.2 L212），但 §G-4 契約 oracle（L96）仍要求 `case_id` 與**報告 metadata** exact 相等——與 R2 COMPOSER-R2-P1-02 修法矛盾，實作者依 §G 寫測試會再度要求 `metadata.case_id`（現況恒為 `None`）。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:96`（「`symbol`／`timeframe`／`case_id` 與報告 metadata exact 相等」）vs `:178` ⑮（「`case_id` 與 `report_ref` 檔名段…相等（**不**改 report metadata）」）／`:212`；VERIFY `venv/bin/python /tmp/composer-gap2-specadv-r3/budget_probe.py` → `metadata.case_id=None`，`symbol=ETHUSDT`，`timeframe=12h`；`data_cache/reports/ic_report_ic_gatekeeper.json` → `case_id=None`。RECHECK: 對照 L96 與 Task 3.1 ⑮ 是否同指一來源。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[MAJOR] 信心度=High。§G-4 是 B3 契約 oracle 的驗收入口；L96 未同步會讓 Task 3.1 ⑮ 與 §G-4 測試雙標——一邊比檔名、一邊比 metadata。修法：L96 改為「`symbol`／`timeframe` 與報告 metadata exact 相等；`case_id` 與 `report_ref` 檔名段 `ic_report_{case_id}.json` 相等（不比 metadata）」，與 L178 ⑮ 對齊。

---

## COMPOSER-R3-P2-01

**斷言**: L2 已裁定 reason 字面唯一住 `ic_survivor_contract.json#reasons`、Task 4.1 **不加** `ic_report_contract.json#reasons`（L105／L199），但 §C 白名單 L62 仍要求 report 契約「`reasons` 加 `marginal_ic`／`marginal_ic_feature` 兩組」——與 L2 處置及 Task 1.0「report 契約本 Task 不動」衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:62` vs `:105`（「`ic_report_contract.json` 不加 reasons」）／`:199`（「**不加 reasons**——R2 L2」）；`rg marginal_ic momentum/Analysis/contracts/ic_report_contract.json` → 0（2026-08-18）。RECHECK: 搜尋 SPEC 內「reasons 加」與「不加 reasons」是否僅剩 L62 矛盾。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[MAJOR] 信心度=High。實作者若先讀 §C 白名單會在 B4 提前改 report reasons，重開 R2 forward dependency／`test_r6` 風險。修法：L62 刪除 reasons 增鍵，改為「僅 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`」，與 L199 一字對齊。

---

## GROK-R3-P0-01

**斷言**: R2 L3 已把 `case_id` 對照改為 `report_ref` 檔名段（且不改 report metadata），但 §G-4 仍要求 `symbol`／`timeframe`／`case_id` **皆**與報告 metadata exact 相等；在 `run_analyze()` 真路徑 `metadata.case_id=None`、`_resolve_case_id`→`ic_gatekeeper` 下，依 Task 3.1⑮ 實作的正確 validator 會被 §G-4／V-19 假紅。

**碼證**: SPEC L96（§G-4「與報告 metadata exact 相等」）；對照 L178 Task 3.1⑮（`case_id`＝`ic_report_{case_id}.json` 檔名段，**不**改 report metadata）與 R2 synth L3。VERIFY：`run_analyze()` → `metadata.case_id is None`、`symbol=ETHUSDT`、`timeframe=12h`；`sed -n 3856,3859p momentum/Analysis/ic_filter_orchestrator.py` → 缺 case_id 時回 `"ic_gatekeeper"`。RECHECK: 重跑 `run_analyze()` 印三欄；對照 L96 vs L178。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[BLOCKING] 信心度=High。會怎麼失敗：B3／B4 依⑮做檔名對照 → §G-4 要 `payload.case_id == metadata.case_id`（None）失敗；或為過 §G-4 把 case_id 鏡進 report metadata＝直接違反 L3「不改 report metadata」。  
修法：§G-4 改寫為與 Task 3.1⑮ 同一對照規則（symbol／timeframe↔metadata；case_id↔`report_ref` 檔名段）；V-19「§G-4 轉紅」同步該語意。

---

## GROK-R3-P1-01

**斷言**: R2 L2 已裁定 reason 字面唯一住 `ic_survivor_contract.json#reasons`、B4 **不加** `ic_report_contract.json#reasons`，但 §C 允許改動白名單第 3 項與 Task 1.0「既有 caller」句仍寫 B4 對 report 契約 **加 reasons 兩組／reasons 增鍵**，與 Task 4.1 正文「不加 reasons」及 Task 1.0 reasons「唯一列舉處」互斥。

**碼證**: SPEC L62（`reasons` 加 `marginal_ic`／`marginal_ic_feature`）；L106（`report_sections`／`reasons`／`metadata` 增鍵全部移至 Task 4.1）；對照 L105（reasons 唯一列舉、不設 `reasons_ref`、report 不加 reasons）與 L199（**不加 reasons**）。另 L68「既有 … reasons 以 `*_ref` 指向 `ic_report_contract.json`」仍暗示舊 ref 設計。VERIFY：`jq -r '.reasons|keys[]' momentum/Analysis/contracts/ic_report_contract.json` → 僅既有三鍵、無 marginal_*。RECHECK: `grep -n 'reasons 加\\|不加 reasons\\|reasons 增鍵' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[MAJOR] 信心度=High。會怎麼失敗：實作者依 §C／L106 於 B4 寫入 report `reasons.marginal_ic*` → 兩處列舉回潮、`test_r6` 要求 orchestrator 對新 reason 鍵有字面、或與「 survivor 契約唯一 SoT」漂移；依 Task 4.1 不加則與 §C 白名單字面衝突、審查／實作各執一段。  
修法：L62 改為只加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；L106 刪「reasons 增鍵」；L68 改為僅 `capability_status_ref`（reasons 不再 ref 到 report 契約）。

---


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:d2c73b8b2e165ca177cf9dd33485f5dc5a852745673195fd75fb976fa97b849e task:20260818-GAP2-X-STAMP-R4
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:d2c73b8b2e165ca177cf9dd33485f5dc5a852745673195fd75fb976fa97b849e task:20260818-GAP2-X-STAMP-R4
RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:d2c73b8b2e165ca177cf9dd33485f5dc5a852745673195fd75fb976fa97b849e task:20260818-GAP2-X-STAMP-R4
