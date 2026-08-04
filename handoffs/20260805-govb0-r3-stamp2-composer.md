# GOVB0-R3-STAMP2 — Composer 戳記輪產出

**家族**：composer | **task-id**：GOVB0-R3-STAMP2 | **日期**：2026-08-05  
**標的**：`handoffs/reconcile/20260805-govb0-spec-r3/synth.md`

---

## 戳記決定

**APPROVED** — 群集表 ID 歸戶已修正（F-4←P1-01、F-6←P1-02）；處置與本人 R3 findings 一致；主委三組裁決同意。

已 append 至 `synth.md` `## 戳記` 區段：

```
RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:2949edaacb5f7a35a3e4cfadd143a4b48962d1534fd73eeec3ba162b2ccf696b task:GOVB0-R3-STAMP2
```

---

## Diff（僅 `## 戳記` 區段）

```diff
 ## 戳記
 
+RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:2949edaacb5f7a35a3e4cfadd143a4b48962d1534fd73eeec3ba162b2ccf696b task:GOVB0-R3-STAMP2
```

---

## 逐條 findings 歸戶核對

### CODEX（5 條）— 全數 ID 正確

| ID | 應歸 F | 群集表實際 | 處置一致？ |
|---|---|---|---|
| `CODEX-R3-P0-01` | F-1 | F-1 | ✓ ACCEPT-BLOCKING |
| `CODEX-R3-P0-02` | F-2 | F-2 | ✓ ACCEPT-BLOCKING |
| `CODEX-R3-P0-03` | F-3 | F-3 | ✓ ACCEPT-BLOCKING |
| `CODEX-R3-P1-04` | F-4 | F-4 | ✓ ACCEPT-BLOCKING |
| `CODEX-R3-P1-05` | F-7 | F-7 | ✓ ACCEPT |

### COMPOSER（6 條）— 全數 ID 正確（本輪修正後複核）

| ID | 附錄主旨 | 應歸 F | 群集表實際 | 處置一致？ |
|---|---|---|---|---|
| `COMPOSER-R3-P0-01` | Task 0.1 JSON diff 互斥 | F-1 | F-1 | ✓ |
| `COMPOSER-R3-P1-01` | E-10 ≥50＋≥3 session 未落 SPEC | F-4 | F-4 | ✓ |
| `COMPOSER-R3-P1-02` | Task 2.1 缺 b15probe6 四條語料 | F-6 | F-6 | ✓ |
| `COMPOSER-R3-P1-03` | lock 逾時後同 `<out>` 重派 | F-3 | F-3 | ✓ |
| `COMPOSER-R3-P2-01` | 契約 10 項 vs 11 編號點 | F-5 | F-5 | ✓ |
| `COMPOSER-R3-P2-02` | B-36 併 B-13 產出端預列 | F-7 | F-7 | ✓ |

**本輪 ID 錯位複核**：上一輪拒章點（P1-01↔P1-02 在 F-4／F-6 對調）已修正；逐條比對附錄 `## COMPOSER-R3-P1-01`（E-10 門檻）與 `## COMPOSER-R3-P1-02`（1b 語料）主旨，與群集表 F-4／F-6 列一致。

**F-2 僅列 codex ID**：本人 R3 未獨立開 F-2 finding（契約四項未定結果僅 codex P0-02）；本人 1b 相關訴求在 P1-02→F-6，與群集拆分一致。

---

## 主委三組裁決表態

### F-2 契約四項判定 — **同意**

| 契約項 | 主委裁決 | 本人立場 |
|---|---|---|
| unquoted `-c` | BLOCK | 同意 |
| 遞迴深度 | 上限 3 層，逾限 fail-closed | 同意 |
| 跳脫引號 | 不終止 span；不確定邊界 fail-closed | 同意 |
| heredoc | 本體視為引號 span，外部照常判定 | 同意（對齊 R2 P1-02 誤擋根因） |

### F-2 放寬至 `awk` — **同意**

R3 Q3 已建議 awk 單進程掃描；brief 引用 receipt `awk_hotpath_bench.sh` → +5 ms／次（~6%）可接受。維持禁 python 合理。

### F-3 lock 生命週期 — **同意（含被拒不寫 result_state）**

| 項目 | 主委裁決 | 本人立場 |
|---|---|---|
| ownership | attempt id（pid＋UTC 起始戳） | 同意 |
| release | `_emit_family_result` 後必定釋放 | 同意（對齊 P1-03） |
| stale | pid 已死 **或** 逾 timeout＋外層安全閥 | 同意 |
| 逾時重派 | `failed` 後同 `<out>` 正常放行 | 同意（P1-03 核心訴求） |
| 被拒 attempt | 不寫 `result_state`，只記 audit 拒絕 | **同意** — 「每 attempt 恰一筆 result_state」須排除未啟動 CLI 者；否則污染 Task 3.1 duration → 影響 3.3 定稿 |

---

## E-SCOPE — 維持 R2 接受

四項不受理範圍不變；本輪未改變立場。

---

## 對「accretion 已中止」的攻擊

**部分同意，但有保留。**

**支持中止的證據**：
- 計數 19→17→11；P0 5→7→3；R3 無 OUT-OF-SCOPE 項被重新列為 BLOCKING。
- F-1／F-4／F-5 為主委交叉引用漏改（票 B-17 同型），非新機制缺口。
- F-6／F-7 為驗收語料／治理工具債，severity 偏低。

**保留（R4 仍可能 2–4 條，但難再現 R2 量級 7 P0）**：
- F-2／F-3 是 R2 underspec 在 R3 升格 P0；R4 寫入 SPEC 後應閉合，但若再增契約項而忘同步計數／驗收，B-17 可再現。
- 群集 ID **錯位**仍無機械防線（`completeness --lock` rc=0 無感）；B-13／B-36 產出端修法落地前，人工複核仍是必要防線。
- **結論**：不必開 R5；R4 預期剩餘為 F-2／F-3 定稿實作＋交叉引用紀律。若 R4 >5 條且含 ≥2 新 P0 機制缺口，再評估 R5。

---

## 檢查器輸出

### `reconcile_stamps_check.sh`

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r3/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: provenance 不符 — ERROR: task:GOVB0-R3-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:2949edaacb5f7a35a3e4cfadd143a4b48962d1534fd73eeec3ba162b2ccf696b task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（預期：codex／grok 尚未蓋章；composer provenance 待 Claude `register-output GOVB0-R3-STAMP2 handoffs/20260805-govb0-r3-stamp2-composer.md`）

### `completeness_check.sh --lock`

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r3/sources/20260805-govb0-spec-r3-codex.md — 5/5 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r3/sources/20260805-govb0-spec-r3-composer.md — 6/6 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

rc=0

---

## /tmp 清理

已刪：`agent_dc_snapshot.txt`、暫存檢查輸出檔  
保留：`claude-501`  
無 `govb0*` 工作目錄

---

ASSUMPTIONS_VERIFIED: body hash=`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-spec-r3/synth.md` → 2949edaacb5f7a35a3e4cfadd143a4b48962d1534fd73eeec3ba162b2ccf696b；附錄 COMPOSER ID 與群集表逐條比對
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r3/synth.md` rc=1；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r3/sources.lock` rc=0
FAILURES_SEEN: none（stamps rc=1 為三家未全 APPROVED／provenance pending，屬預期）
SCOPE_CHANGES: 僅 append `synth.md` `## 戳記` 一行
NUMERIC_OR_SCHEMA_IMPACT: none

產出檔: handoffs/20260805-govb0-r3-stamp2-composer.md

STATUS: DONE
