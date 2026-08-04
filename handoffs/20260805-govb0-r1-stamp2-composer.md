# GOVB0-R1-STAMP2 — composer 戳記產出

**task-id**: GOVB0-R1-STAMP2 | **家族**: composer | **日期**: 2026-08-05

## 決定

**蓋章** — append 一行 `RECONCILE-STAMP` 至 `synth.md ## 戳記`。

## 改動 diff

```diff
--- a/handoffs/reconcile/20260804-govb0-spec-r1/synth.md
+++ b/handoffs/reconcile/20260804-govb0-spec-r1/synth.md
@@ -298,5 +298,7 @@ STATUS: DONE
 
 ## 戳記
 
+RECONCILE-STAMP: composer APPROVED 2026-08-04 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2
```

（同區段內 codex／grok 戳記由並行委員 append；本產出僅負責 composer 行。）

## composer findings 歸戶逐條確認

| ID | 群 | 處置 | 一致？ |
|---|---|---|---|
| COMPOSER-R1-P0-01 | D-1 | ACCEPT-BLOCKING | ✓ bash -c fail-open 主張忠實 |
| COMPOSER-R1-P0-02 | D-2 | ACCEPT-BLOCKING | ✓ .part／prompt 未對齊 |
| COMPOSER-R1-P1-01 | D-4 | ACCEPT-BLOCKING | ✓ §V 不可證偽／immutable corpus |
| COMPOSER-R1-P1-02 | D-6 | SPLIT（主委裁） | ✓ 忠實呈現「不建議拆 unless 膨脹」；接受 SPLIT 裁決 |
| COMPOSER-R1-P1-03 | D-8 | ACCEPT — 開 B-33 | ✓ locale fail-open MAJOR、本批不併 |
| COMPOSER-R1-P1-04 | D-6／D-10 | SPLIT／ACCEPT 隨 D-6 移出 | ✓ owner／到期日未弱化 |
| COMPOSER-R1-P1-05 | D-1 | ACCEPT-BLOCKING | ✓ 與 P0-01 同群、疊加洞歸 D-1 |
| COMPOSER-R1-P2-01 | D-12 | ACCEPT（明文化） | ✓ grep -Eo 先判後記 |
| COMPOSER-R1-P2-02 | D-11 | ACCEPT（收窄） | ✓ harness 字串非委員行為 |
| COMPOSER-R1-P2-03 | D-9 | ACCEPT — 補條件 | ✓ Phase 0 後補查、不除役 |
| composer Q1（timeout） | D-7 | PARTIAL — 暫定值 | ✓ 75m composer 採用；區間定義一致 |
| composer Q6（依賴） | D-13 | ACCEPT — §P 補宣告 | ✓ forward dependency 未弱化 |

**D-6／D-7 主委裁決**：接受。D-6 SPLIT 與我 P1-02 條件立場（膨脹 5 訊號）相容；D-7 暫定值取保守聯集（composer 75m）與我 Q1 建議一致。

**D-1 獨立驗證**（重跑 `bash .claude/tmp/b15probe3.sh`）：proto1 對 `bash -c`／`sh -c` 為 ALLOW（fail-open）；proto2 全 9 條 ok。與 synth 主委表一致。

**body hash**：`bash scripts/reconcile_body_hash.sh …` → `25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c` ✓

## reconcile_stamps_check.sh 完整 stdout 與 rc

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260804-govb0-spec-r1/synth.md 未獲全數委員核可:
  · codex: provenance 不符 — ERROR: task:GOVB0-R1-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · composer: provenance 不符 — ERROR: task:GOVB0-R1-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: provenance 不符 — ERROR: task:GOVB0-R1-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（戳記行已齊；FAIL 因 register-output pending，待 Claude `register-output`）

## completeness_check --lock rc

`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260804-govb0-spec-r1/sources.lock` → rc=0

## /tmp 收尾

已刪本輪 workdir 檔（govb0-* logs／out）。保留 `claude-501`。`frtest.67076`／`sessions` 目錄因 sandbox 權限未刪（非本輪產物）。

---

ASSUMPTIONS_VERIFIED: body hash 25e1241f…；b15probe3 原型①②對照；10 條 composer findings 全歸戶
TESTS_RUN: reconcile_body_hash.sh PASS；b15probe3.sh PASS；completeness_check --lock rc=0；reconcile_stamps_check rc=1（provenance pending）
FAILURES_SEEN: reconcile_stamps_check provenance pending（預期，待 register-output）
SCOPE_CHANGES: none（僅 synth.md ## 戳記 append 一行）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
