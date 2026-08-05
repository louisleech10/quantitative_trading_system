# GOVB0-R4-STAMP — Composer 戳記輪產出

**家族**：composer | **task-id**：GOVB0-R4-STAMP | **日期**：2026-08-05  
**標的**：`handoffs/reconcile/20260805-govb0-spec-r4/synth.md`  
**裁決**：**APPROVED**（已 append RECONCILE-STAMP）

---

## 改動 diff

```diff
diff --git a/handoffs/reconcile/20260805-govb0-spec-r4/synth.md b/handoffs/reconcile/20260805-govb0-spec-r4/synth.md
@@ -149,3 +149,5 @@ STATUS: DONE
 
 ## 戳記
 
+RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-R4-STAMP
+
```

---

## 三支檢查器（完整 stdout + rc）

### 1. `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md`

**rc=1**（預期：本輪僅 composer 一家蓋章，codex／grok 待戳；composer provenance 待 register-output）

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r4/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: provenance 不符 — ERROR: task:GOVB0-R4-STAMP 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

### 2. `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock`

**rc=0**

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r4/sources/20260805-govb0-spec-r4-codex.md — 3/3 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r4/sources/20260805-govb0-spec-r4-composer.md — 5/5 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

### 3. `python3 scripts/verification_claim_check.py --files handoffs/reconcile/20260805-govb0-spec-r4/synth.md`

**rc=0**（stdout 空）

---

## 逐條 findings 歸戶（composer 5 條 + codex 交叉核對）

以 `awk` 自附錄抽出「ID → 斷言首句」對照群集表（機械表 + 語意複核）：

| Finding ID | 群集 | 附錄斷言首句 vs 群集主張 | 處置 vs 原主張 |
|---|---|---|---|
| `COMPOSER-R4-P1-01` | G-4 | Task 2.1／3.3 交叉引用對调 ↔ 群集「兩處 composer ID 對调」 | **一致**；ACCEPT → 已修 + VERIFY:govb0-r4-g4-composer-ids |
| `COMPOSER-R4-P1-02` | G-5 | F-7 要求 B-36 具名殘留入 SPEC ↔ 群集「SPEC 漏記 B-36」 | **一致**；ACCEPT → 已修（待 R5 複核） |
| `COMPOSER-R4-P1-03` | G-1 | heredoc 缺 delimiter／body 規則 ↔ 群集「heredoc 無可執行契約」 | **一致**；ACCEPT-BLOCKING → 已修（待 R5 複核）；與 `CODEX-R4-P0-01` 同群合理 |
| `COMPOSER-R4-P2-01` | G-6 | Task 3.3 驗證段無 PROVISIONAL 狀態斷言 ↔ 群集「E-10 不可證偽」 | **一致**；ACCEPT → 已修（待 R5 複核） |
| `COMPOSER-R4-P2-02` | G-2 | lock 被外部刪除路徑未覆蓋 ↔ 群集「lock 生命週期四路徑」 | **一致**；ACCEPT-BLOCKING → 已修（待 R5 複核）；與 `CODEX-R4-P0-02` 同群合理 |
| `CODEX-R4-P0-01` | G-1 | heredoc 邊界契約 ↔ 同上 | **一致** |
| `CODEX-R4-P0-02` | G-2 | owner-safe release 等 ↔ 同上 | **一致** |
| `CODEX-R4-P2-01` | G-3 | §A 計數 9 vs 10 ↔ 群集「FACT-RECEIPT 不一致」 | **一致**；VERIFY:govb0-r4-g3-factcount → 10 |

**錯位檢查**：8/8 ID 歸入正確 G 群；**未發現** R1–R3 戳記輪那類「ID 掛錯列」錯位。`completeness_check --lock` rc=0 僅證「ID 出現」，語意複核本輪通過。

**主委 awk 填表法**：自附錄機械抽表後填群集，本輪未再現錯位；附錄仍保留易腐行號（byte-faithful 要求）但群集段已改 Task 定位——作法有效。

---

## 三類修改攻擊

### 修改 1：移除假豁免 `VERIFY-EXEMPT:doc-summary:*`

**屬實**。已讀 `scripts/verification_claim_check.py:97-99`，`EXEMPT_RE` 僅六類（`typo`／`doc-example`／`migration-note`／`template-drift`／`tooling-blocked`／`spec-ambiguity`），**不含** `doc-summary` ⇒ token 自始零效力。移除後改寫「待 R5 逐条複核／本檔不自證」**誠實**，無掩飾成分。

### 修改 2：G-3／G-4 真 receipt；G-1／G-2／G-5／G-6 標「不自證」

**獨立複驗 G-3／G-4**：
- `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → **10** rc=0（== §A）
- `grep -n 'COMPOSER-R3-P1-0' docs/GOVB0_FRICTION_SPEC.md` → `:239` 為 `P1-02`（Task 2.1）、`:417` 為 `P1-01`（Task 3.3）rc=0

**G-1／G-2／G-5／G-6**：非「無人驗」——SPEC R5 版已含修補文本（heredoc 五規則 `:194-199`、owner-safe `:360+`、B-36 殘留 `:492-497`、PROVISIONAL 驗收 `:436`）。標「待 R5 逐条複核」是把**收斂檔層**的 receipt 責任推到確認輪，**可接受**；若硬要現在出 receipt，G-5／G-6 其實可用 `rg` 機械驗（本輪 spot-check 已過），但**不構成拒章理由**——R5 確認輪正是為此設計。

### 修改 3：行號 → Task 定位

群集／VERIFY 區已改 Task 編號；附錄保留 `:230`／`:387` 等**符合 byte-faithful**。**殘留易腐引用**：附錄內行號（不可改）、VERIFY 區 `:239`／`:417` 為 receipt 紀錄（可接受）。群集表本體無未鎖定計數漂移。

---

## E-SCOPE 立場

**維持 R2 接受，不重新開放**。四項（截斷 oracle／B-34 語意閉合／B-24 機械強制面／B-15 FP-2 定位）仍 OUT-OF-SCOPE；本輪無失效路徑。

---

## R5 表態：**(a) R5 確認輪有必要**

**理由**（修正 R4 審查時 composer 的「可省 R5」立場）：

1. **全批 8 條含 codex 2 P0**（非 composer 單家 ≤5／0 P0）；主委已裁以 codex 較嚴出場判準 ⇒ 需確認輪關閉。
2. **G-1／G-2／G-5／G-6 四條**收斂檔誠實標「待 R5 逐条複核」——確認輪是唯一指定關卡，非推責無人驗。
3. **不預期 R5 再冒新 P0 機制缺口**；預期僅 adversarial 逐條確認 SPEC 修補是否完整關閉 R4 八條。

若選 (b) 須把四條併入 TODO 審查輪，但現行 SPEC 憲法＋主委裁決已定 R5 確認輪，與 (a) 等價且更清晰。

---

ASSUMPTIONS_VERIFIED: EXEMPT_RE 六類無 doc-summary（讀 verification_claim_check.py:97-99）；body-hash=ae304eeb…（reconcile_body_hash.sh）；G-3 count=10；G-4 Task 2.1→P1-02／Task 3.3→P1-01；8/8 ID 歸戶語意複核通過
TESTS_RUN: reconcile_stamps_check rc=1（缺 codex/grok + provenance pending）；completeness_check --lock rc=0；verification_claim_check rc=0
FAILURES_SEEN: reconcile_stamps_check rc=1 屬預期（單家戳記輪進行中）
SCOPE_CHANGES: 僅 synth.md `## 戳記` 區 append 一行
NUMERIC_OR_SCHEMA_IMPACT: none

產出檔: handoffs/20260805-govb0-r4-stamp-composer.md

STATUS: DONE
