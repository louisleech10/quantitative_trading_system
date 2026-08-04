# GOVB0-R2-STAMP2 — Composer 戳記輪（第二輪）

**家族**：composer | **task-id**：GOVB0-R2-STAMP2 | **日期**：2026-08-05  
**標的**：`handoffs/reconcile/20260805-govb0-spec-r2/synth.md`

## 決定

**蓋章 APPROVED** — 已 append 一行 `RECONCILE-STAMP` 至 `## 戳記` 區段。

## synth.md 變更（diff）

```diff
 ## 戳記
 
+RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:GOVB0-R2-STAMP2
```

## 檢查器

### `reconcile_stamps_check.sh`（完整 stdout + rc）

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r2/synth.md 未獲全數委員核可:
  · codex: provenance 不符 — ERROR: task:GOVB0-R2-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · composer: provenance 不符 — ERROR: task:GOVB0-R2-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: provenance 不符 — ERROR: task:GOVB0-R2-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（預期：僅 composer 已蓋章；codex／grok 待蓋；provenance pending 待 Claude register-output）

### `completeness_check.sh --lock`（完整 stdout + rc）

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r2/sources/20260805-govb0-spec-r2-codex.md — 10/10 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r2/sources/20260805-govb0-spec-r2-composer.md — 7/7 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

rc=0

## Composer R2 findings 歸戶（7/7）

| ID | 群 | 處置 | 一致？ |
|---|---|---|---|
| `COMPOSER-R2-P0-01` | E-3 | ACCEPT-BLOCKING + 原型③ | ✓ |
| `COMPOSER-R2-P1-01` | E-13 | ACCEPT — 禁止照抄原型 | ✓（首輪漏列已修） |
| `COMPOSER-R2-P1-02` | E-4 | ACCEPT — 併入 E-3 契約 | ✓ |
| `COMPOSER-R2-P1-03` | E-11 | ACCEPT（明文化）— 本批不解 | ✓ |
| `COMPOSER-R2-P1-04` | E-10 | ACCEPT — 樣本門檻 + 定稿公式 | ✓ |
| `COMPOSER-R2-P2-01` | E-2 | ACCEPT-BLOCKING（§V 客觀錯誤） | ✓ |
| `COMPOSER-R2-P2-02` | E-12 + E-SCOPE③ | ACCEPT — TODO §0 標部分完成；機械面 defer | ✓ |

## 主委 17/17 群集表自檢複核

逐條核對附錄 17 ID 皆在群集表（含 codex 10 條）⇒ **自檢可靠**（E-13 修復後無漏項）。

## E-3 獨立重跑（b15probe4／b15probe5）

- **b15probe4**：四向量 `eval`／`$()`／反引號／子 shell 在**現行 gate** 皆 `ALLOW`（want=BLOCK）⇒ fail-open 屬實。
- **b15probe5**：16 TP + 10 TN = **26/26** proto3 全 `ok` ⇒ 原型③宣稱屬實。

## E-6 序列化裁決

同意。同一 `<out>` 並發派工本不應發生；拒絕第二 attempt 比仲裁兩份 payload 簡單且不丟資料。

## E-10 暫定值取捨

接受主委裁決：定稿門檻採 codex 較嚴者（≥50 + ≥3 session／日期）；未達前可上線暫定 timeout 但標 `PROVISIONAL`、Task 3.3 不得宣稱完工。理由（無 timeout 致 B-14 空等）合理，優於嚴格禁止暫定值。  
備註：群集表 E-10 列「採 composer Q4 門檻」與正文（定稿 ≥50）用語略不一致，屬標籤精度問題，不影響處置實質。

## E-SCOPE 四項不受理立場

| 項 | 立場 | 失效路徑？ |
|---|---|---|
| ① 產出完整性 oracle | **接受** | 否 — attempt-scoped publish 已解 B-14 主病；截斷未實際致害 |
| ② `B-34` 語意閉合 | **接受** | 否 — 權宜 stamp 可過機檢，獨立票追蹤 |
| ③ `B-24` 機械強制 | **接受** | 否 — R1 SPLIT 已裁；E-12 補紀律面 |
| ④ `B-15` FP-2 | **接受** | 否 — 補查條件已寫，不阻塞本批 |

## /tmp 清理

已刪除本輪 workdir 檔案；**保留** `claude-501/`。

---

ASSUMPTIONS_VERIFIED: body-hash `8b8d0a94…` 與 `reconcile_body_hash.sh` 一致；b15probe4 四向量 fail-open；b15probe5 26/26
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh …` rc=1；`bash scripts/completeness_check.sh --lock …` rc=0；`bash handoffs/govb0_probes/b15probe4.sh` rc=0；`bash handoffs/govb0_probes/b15probe5.sh` rc=0
FAILURES_SEEN: stamps_check rc=1 為單家族蓋章預期狀態
SCOPE_CHANGES: none（僅 `## 戳記` 區段 append 一行）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
