# GOVB0-R2-STAMP — Composer 複核

**家族**：composer | **task-id**：GOVB0-R2-STAMP | **日期**：2026-08-05  
**標的**：`handoffs/reconcile/20260805-govb0-spec-r2/synth.md` 群集／處置段  
**決定**：**不蓋章**（見下）

---

## 逐條 findings 歸戶核對（composer 7 條）

| Finding ID | 群集表行 | 處置與原主張一致？ | 備註 |
|---|---|---|---|
| `COMPOSER-R2-P0-01` | E-3（`COMPOSER-R2-P0-01`／`CODEX-R2-P0-04`） | ✅ | eval／`$()`／反引號／子 shell fail-open → ACCEPT-BLOCKING＋原型③；與 P0-01 一致 |
| `COMPOSER-R2-P1-01` | **未出現在群集表** | ❌ | 見下 |
| `COMPOSER-R2-P1-02` | E-4（`CODEX-R2-P0-04`／`COMPOSER-R2-P1-02`） | ✅ | heredoc 假陽性 → ACCEPT 併入 E-3 契約 |
| `COMPOSER-R2-P1-03` | E-11（`CODEX-R2-P0-06`／`COMPOSER-R2-P1-03`） | ✅ | B-34 roster 衝突 → ACCEPT 明文化、本批不解；與 Q6「不納第 0 批」一致 |
| `COMPOSER-R2-P1-04` | E-10（`CODEX-R2-P1-07`／`COMPOSER-R2-P1-04`） | ✅ | duration 樣本門檻 → 採 composer Q4 五條（≥20／P99×1.25 等） |
| `COMPOSER-R2-P2-01` | E-2（`CODEX-R2-P1-09`／`COMPOSER-R2-P2-01`） | ✅ | §V rc 宣稱過度 → ACCEPT-BLOCKING；嚴重度自 MINOR 升為客觀錯誤，主張未改寫 |
| `COMPOSER-R2-P2-02` | E-12（`COMPOSER-R2-P2-02`） | ✅ | B-24 機械面缺 → ACCEPT，TODO §0 強制標註 |

### 不蓋章理由：`COMPOSER-R2-P1-01` 未歸戶

群集表第 21–35 行列出 12 個 E 群與對應 finding ID，**不含 `COMPOSER-R2-P1-01`**。  
第 10 行宣稱「17 條全部歸戶，**無未分群 ID**」與附錄 17 條 ID 表面一致，但 **composer 7 條中 P1-01 在表上缺席**。

P1-01 主張（附錄 `:245-254`）：契約第 3–5 項（**引號路徑、路徑正規化、未閉合引號**）要求測試，原型② **未實作多數項**；探針證 `bash scripts/../scripts/cx_run.sh`、`"./my dir/codex" exec` 等皆 ALLOW。  
處置建議：Task 2.0 驗證列出具名語料；Task 2.1 不得只寫「參考原型②」。

**與 E-4 的語意重疊不足以代替 ID 歸戶**：E-4 僅列 `CODEX-R2-P0-04`／`COMPOSER-R2-P1-02`，主張為 unquoted `-c`、遞迴上限、escape、heredoc——**未涵蓋 P1-01 的引號路徑／路徑正規化**。上一輪 codex 即在 ID 對應步驟抓到主委歸錯 ID；本條屬同類：**finding 存在於附錄但未進群集表**。

**修法建議**（供主委）：將 `COMPOSER-R2-P1-01` 併入 E-4（或新建 E 行），處置建議 ACCEPT——Task 2.0 驗收增契約 3–5 項具名 TP/TN，與 B2 修法方向一致。

---

## E-3 主委驗證重跑

`bash handoffs/govb0_probes/b15probe4.sh`（rc=0）：

```
===== composer R2-P0-01 指出的四個向量（皆為真派工，want=BLOCK）=====
  CURRENT=XX ALLOW | proto2=XX ALLOW | want=BLOCK | eval 包住
  CURRENT=XX ALLOW | proto2=XX ALLOW | want=BLOCK | 命令替換 $()
  CURRENT=XX ALLOW | proto2=XX ALLOW | want=BLOCK | 反引號
  CURRENT=XX ALLOW | proto2=XX ALLOW | want=BLOCK | 子 shell 括號
  CURRENT=XX ALLOW | proto2=XX ALLOW | want=BLOCK | eval 單引號
  CURRENT=ok BLOCK | proto2=XX ALLOW | want=BLOCK | 命令替換嵌 claude
```

四向量（eval／`$()`／反引號／子 shell）在 **現行 gate 與 proto2 皆 ALLOW** → 與 synth E-3 段及 P0-01 一致。

`bash handoffs/govb0_probes/b15probe5.sh`（rc=0）：16 TP + 10 TN，**proto3 欄全 ok**（26/26）→ 與 synth「26/26 全對」一致。

---

## E-6 改設計（並發→序列化）

主委裁決：同一 `<out>` 僅允許一 attempt，第二個直接拒絕。  
**同意**——與「委員不應對同產出路徑並發」及單一 final path 資料模型一致；非本家族 finding，無異議。

---

## E-SCOPE 四項不受理 — 立場

| 不受理項 | 本批交付物會失效？ | 立場 |
|---|---|---|
| 產出完整性 oracle（`CODEX-R2-P0-01`） | 否 | attempt-scoped publish 已覆蓋 stale／覆蓋／未完成；截斷為第四類且未實際致害；開票合理 |
| `B-34` 語意閉合 | 否 | 與 Q6 一致：權宜 stamp 可過機檢，TODO §0 登記已知債 |
| `B-24` 機械強制面 | 否 | R1 D-6 SPLIT 已裁；E-12＋TODO 標「部分完成」足夠 |
| `B-15` FP-2 定位（R1 OPEN-3） | 否 | Phase 0 累積後補查，不阻塞本批 SPEC |

四項皆屬「不夠完美」而非「不做則交付物失效」→ 若 P1-01 歸戶修正後，其餘可接受。

---

## synth.md 變更

**無**（未蓋章，未 append `RECONCILE-STAMP`）。

---

## 檢查器輸出

### `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r2/synth.md`

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r2/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: composer APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:4f659b945c6c7df23814f5c4ad80611f7e32bfea4645ea418838c39ba34428e3 task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（預期：尚無任何戳記）

### `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r2/sources.lock`

```
COMPLETENESS PASS: .../sources/20260805-govb0-spec-r2-codex.md — 10/10 個 ID 全在綜合檔。
COMPLETENESS PASS: .../sources/20260805-govb0-spec-r2-composer.md — 7/7 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

rc=0

### body-hash 核對

`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-spec-r2/synth.md` →  
`4f659b945c6c7df23814f5c4ad80611f7e32bfea4645ea418838c39ba34428e3`（與 brief 一致）

---

ASSUMPTIONS_VERIFIED: 群集表 ID 逐條對照附錄 17 條；b15probe4/5 重跑；body-hash 與 brief 一致  
TESTS_RUN: `bash handoffs/govb0_probes/b15probe4.sh` rc=0；`bash handoffs/govb0_probes/b15probe5.sh` rc=0；`bash scripts/reconcile_stamps_check.sh …` rc=1；`bash scripts/completeness_check.sh --lock …` rc=0  
FAILURES_SEEN: P1-01 未歸戶（阻擋蓋章）  
SCOPE_CHANGES: none（未改 synth.md）  
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE — 不蓋章（`COMPOSER-R2-P1-01` 未出現在群集表）
