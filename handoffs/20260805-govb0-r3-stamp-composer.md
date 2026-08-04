# GOVB0-R3-STAMP — Composer 戳記輪產出

**家族**：composer | **task-id**：GOVB0-R3-STAMP | **日期**：2026-08-05  
**標的**：`handoffs/reconcile/20260805-govb0-spec-r3/synth.md`

---

## 戳記決定

**REJECTED** — F-4／F-6 的 COMPOSER ID 仍對調（主委自稱已修，實測未閉合）。

已 append 至 `synth.md` `## 戳記` 區段：

```
RECONCILE-STAMP: composer REJECTED 2026-08-05 — F-4/F-6 將 COMPOSER-R3-P1-01 與 P1-02 對調：P1-01(E-10≥50)應歸 F-4、P1-02(1b語料)應歸 F-6；處置語意正確但 ID 歸戶錯
```

---

## Diff（僅 `## 戳記` 區段）

```diff
 ## 戳記
 
+RECONCILE-STAMP: composer REJECTED 2026-08-05 — F-4/F-6 將 COMPOSER-R3-P1-01 與 P1-02 對調：P1-01(E-10≥50)應歸 F-4、P1-02(1b語料)應歸 F-6；處置語意正確但 ID 歸戶錯
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

### COMPOSER（6 條）— 2 條 ID 對調

| ID | 附錄主旨 | 應歸 F | 群集表實際 | 處置一致？ |
|---|---|---|---|---|
| `COMPOSER-R3-P0-01` | Task 0.1 JSON diff 互斥 | F-1 | F-1 | ✓ |
| `COMPOSER-R3-P1-01` | E-10 ≥50＋≥3 session 未落 SPEC | **F-4** | **F-6** | ✗ ID 錯（F-6 語意是 1b 語料） |
| `COMPOSER-R3-P1-02` | Task 2.1 缺 b15probe6 四條語料 | **F-6** | **F-4** | ✗ ID 錯（F-4 語意是 E-10） |
| `COMPOSER-R3-P1-03` | lock 逾時後同 `<out>` 重派 | F-3 | F-3 | ✓ |
| `COMPOSER-R3-P2-01` | 契約 10 項 vs 11 編號點 | F-5 | F-5 | ✓ |
| `COMPOSER-R3-P2-02` | B-36 併 B-13 產出端預列 | F-7 | F-7 | ✓ |

**根因**：主委第一版把 P1-02 誤寫 P0-02、P2-01 誤寫 P1-04、P2-02 誤寫 P2-01；現行表已修正 P2-01→F-5、P2-02→F-7，但修正 P0-02→P1-02 時把 P1-02 放進 F-4、P1-01 放進 F-6——**P1-01／P1-02 仍互換**。兩 ID 皆有引用（非漏引），但歸戶錯。

---

## 主委三組裁決表態

### F-2 契約四項判定 — **同意**

| 契約項 | 主委裁決 | 本人立場 |
|---|---|---|
| unquoted `-c` | BLOCK | 同意（與帶引號等價） |
| 遞迴深度 | 上限 3 層，逾限 fail-closed | 同意 |
| 跳脫引號 | 不終止 span；不確定邊界 fail-closed | 同意 |
| heredoc | 本體視為引號 span，外部照常判定 | 同意（對齊 R2 P1-02 誤擋根因） |

### F-2 放寬至 `awk` — **同意**

R3 Q3 已建議「awk 或等價單進程掃描」；receipt `bash handoffs/govb0_probes/awk_hotpath_bench.sh` → +5 ms／次（~6%）可接受。維持禁 python 合理。

### F-3 lock 生命週期 — **同意（含被拒不寫 result_state）**

| 項目 | 主委裁決 | 本人立場 |
|---|---|---|
| ownership | attempt id（pid＋UTC 起始戳） | 同意 |
| release | `_emit_family_result` 後必定釋放 | 同意（對齊 P1-03） |
| stale | pid 已死 **或** 逾 timeout＋外層安全閥 | 同意 |
| 逾時重派 | `failed` 後同 `<out>` 正常放行 | 同意（P1-03 核心訴求） |
| 被拒 attempt | 不寫 `result_state`，只記 audit 拒絕 | **同意** — 自洽：「每 attempt 恰一筆 result_state」須排除未啟動 CLI 者；否則污染 Task 3.1 duration → 影響 3.3 定稿 |

---

## E-SCOPE — 維持 R2 接受

四項不受理範圍不變；本輪未改變立場。

---

## 對「accretion 已中止」的攻擊

**部分同意，但有保留。**

**支持中止的證據**：
- 計數 19→17→11；P0 5→7→3；R3 無新 OUT-OF-SCOPE 項被重新列為 BLOCKING。
- F-1／F-4／F-5 確為主委交叉引用漏改（與 memory「6 次同型」、票 B-17 一致），非新機制設計缺口。
- F-6／F-7 為驗收語料／治理工具債，severity 偏低。

**保留（R4 仍可能 2–4 條，但難再現 R2 量級 7 P0）**：
- F-2／F-3 是 R2 未閉合的**機制 underspec**在 R3 升格 P0，非純漏改；R4 寫入 SPEC 後應閉合，但若 R4 又增契約項而忘同步計數／驗收，B-17 病型可再現（主委本輪又犯 ID 對調即例證）。
- `completeness_check --lock` 對群集 ID 歸戶錯誤仍無感（rc=0）；在 B-13／B-36 產出端修法落地前，人工自檢仍是唯一防線。
- **結論**：不必開 R5；R4 預期剩餘為 F-2／F-3 定稿實作＋交叉引用紀律，非新一輪機制發明。若 R4 >5 條且含 ≥2 新 P0 機制缺口，再評估 R5。

---

## 檢查器輸出

### `reconcile_stamps_check.sh`

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r3/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: REJECTED(reconcile 未獲核可,須修後重審)
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:edda2ccd9f1cbc38622f564826fbec654a29ac23135f634ad9feaa3153c91be7 task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（預期：composer REJECTED）

### `completeness_check.sh --lock`

```
COMPLETENESS PASS: .../20260805-govb0-spec-r3-codex.md — 5/5 個 ID 全在綜合檔。
COMPLETENESS PASS: .../20260805-govb0-spec-r3-composer.md — 6/6 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

rc=0

---

## /tmp 清理

已刪：`govb0-r3-stamp-check.out`、`govb0-r3-completeness.out`、`govb0_r3_stamps_check_grok.out`、`govb0_r3_completeness_grok.out`  
保留：`claude-501`

---

ASSUMPTIONS_VERIFIED: 附錄 COMPOSER-R3-P1-01/P1-02 主旨與群集表 F-4/F-6 逐字比對；body hash=edda2ccd9f1cbc38622f564826fbec654a29ac23135f634ad9feaa3153c91be7
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r3/synth.md` rc=1；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r3/sources.lock` rc=0
FAILURES_SEEN: none（REJECT 為刻意決定）
SCOPE_CHANGES: 僅 append `synth.md` `## 戳記` 一行
NUMERIC_OR_SCHEMA_IMPACT: none

產出檔: handoffs/20260805-govb0-r3-stamp-composer.md

STATUS: DONE
