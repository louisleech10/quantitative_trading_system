# P2DEBT-T5 golden provenance reconcile(SPEC R2 定稿,派實作前)
Task-id: p2debt-t5 | Date: 2026-07-12 | Chair: Claude(Opus 4.8)

## 審查鏈
- 起草:Claude R1。雙家族 adversarial:**codex=BLOCK(6 findings)**、**grok=BLOCK(4 獵點+3 CE,實測)**,高度收斂+實證。
- 兩腿一致:重凍方向對(KEEP flag-off,不 revert),但 R1 有真問題:理由不誠實/reuse 無守衛/replay 定義錯/unlock 是發明。

## 主委裁決:全數採納,R2 定稿(兩腿實跑反例,adversarial 勝)
### R2-1 方向=KEEP flag-off + 修 guard + 誠實補史,**不 revert**(兩腿一致)
revert 會重開「freeze 腳本語意≠G-OLD」洞;滅失的 963ba payload 無法 git restore。保留 flag-off 寫死。

### R2-2 誠實 provenance——**恢復非刪除**(codex#1+grok#4)
- **寫回** rebaseline_reason/rebaselined_at(禁刪史);記**三個獨立事由**分開陳述:
  (a) B2 rolling-oracle 對齊修(feature-epoch-index vs label-RangeIndex rolling join→0列全None,RCA 854d444;不可 revert);
  (b) flag-off config_override 顯式化(關閉「原凍用未入腳本 override 產 full-sample」隱形參數債);
  (c) **post-B2 碼漂移新 oracle**(WT norm 85f65830 有 full selection_scope/FDR 結構 vs 854 regen 2f3617b9 selection_scope=None)。
- **移除 float64**(RCA 後已修,非現 baseline 重凍理由);不得把新 sha 話術成「只補 override」。

### R2-3 reuse guard=content-addressed manifest fail-closed(codex#2#3+grok CE1)
- 光比 meta config_hash 不夠(抓不到同 meta 髒 H5)。要 manifest 綁 **H5 SHA256 + meta SHA256**,並驗 H5 內
  symbol/tf/schema/row-index/feature-order + selected_features == 當前 registry sorted top-N;任一不符 → **raise,禁自動覆寫 canonical inputs**。
- mutation 測(可證偽,兩腿 CE1):(a) 只改 H5 值 meta 不改 → raise;(b) meta selected_features 與 registry top-N 分歧 → raise;(c) 改內嵌 config_hash → raise。

### R2-4 replay 拆 A/B + canonical projection(codex#5+grok CE2)
- **禁 file-byte 級 == fd932a6e**(payload 含 generated_at/task_id 天生不穩)。
- **Gate A(input-fixed→output)**:pinned input SHA → 跑 service → 輸出 **normalized sha**(exempt generated_at/task_id 等易變欄,沿用現 regen receipt 的 normalized 比較)== 工作樹 baseline normalized sha。
  grok 已提供語意 receipt:`pytest test_ic_1a_cut1_golden.py → 2 passed`(service 路徑+顯式 flag,等同重放)。
- **Gate B(source→input)**:移除 inputs → 由 canonical registry 重建 → 驗重建 input 的 SHA == pinned;證 source→input 可重建(reuse 只證 input→output,不能兼證)。
- 定 **canonical projection**:明列 exempt fields(generated_at/task_id_used_for_freeze 等);baseline 比對用 normalized sha 或 golden deep-equal。

### R2-5 unlock 制度化 or append-only events(codex#4+grok#4)
- `unlock_*` **非既有 schema**(grep 僅 R1;ic_phase1_contract golden 無此欄)。二選一:
  (a) 建 schema:先定精確欄名/語義/authority/source-receipt;或 (b) 改 **append-only provenance events**(較可稽核)。**R2 採 (b)**(不硬造必填欄,用 append-only event log 記重凍鏈)。

### R2-6 執行環境(codex#6+grok)
freeze 若需實跑:用獨立 worktree / 複製 golden+inputs 到 /tmp + redirect persist + data_cache 前後快照;禁在髒工作樹跑覆寫。但**語意 replay(pytest golden)已足**當主 receipt,freeze 全跑非必要(除非 Gate B 需要)。

## 驗收(R2)
1. baseline_meta/new_meta 稽核欄齊+三事由分述+移除 float64+append-only provenance events;禁刪史。
2. reuse guard content-addressed fail-closed;3 個 mutation 各 raise(receipt)。
3. Gate A normalized-sha replay == 工作樹(pytest golden 2 passed 已為初步 receipt);Gate B source→input 重建驗 SHA。
4. golden 比對測試全綠未弱化。
5. **三方 golden 資料正確性簽核**(Claude+grok+composer):flag-off 語意正確、無 look-ahead、值守恆、provenance 誠實完整。

## Verdict
Verdict: APPROVE(條件式)— codex+grok 雙 BLOCK 全數以 R2-1~R2-6 納入;兩腿反例皆實跑;每項對應可證偽 gate。
待 codex+grok append RECONCILE-STAMP 確認 BLOCK 化解後派實作。

## 戳記
(待 codex / grok append)
RECONCILE-STAMP: codex APPROVED 2026-07-12 sha256:be05054f47de4d4b8142a986947d8b6bf124601d58d44d320b8d9b2dc3fb8ec2 task:t5-recon-codex
RECONCILE-STAMP: grok APPROVED 2026-07-12 sha256:be05054f47de4d4b8142a986947d8b6bf124601d58d44d320b8d9b2dc3fb8ec2 task:t5-recon-grok
