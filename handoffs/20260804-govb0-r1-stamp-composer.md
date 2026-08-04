# GOVB0-R1-STAMP — Composer 收斂戳記

**家族**：composer | **task-id**：GOVB0-R1-STAMP | **日期**：2026-08-04  
**標的**：`handoffs/reconcile/20260804-govb0-spec-r1/synth.md`

## 決定

**蓋章 APPROVED** — 群集／處置段忠實反映 composer R1 findings；D-6／D-7 主委裁決可接受。

## synth.md 變更（僅 `## 戳記` 區段）

```diff
 ## 戳記
 
+RECONCILE-STAMP: composer APPROVED 2026-08-04 sha256:1088062c7da80a7ea23978675f6a19d433b90d7523c21d5b75eb72470b581d7d task:GOVB0-R1-STAMP
```

## findings 逐條歸戶確認（composer 10 條）

| ID | 群 | 處置 | 與本人主張一致？ |
|---|---|---|---|
| `COMPOSER-R1-P0-01` | D-1 | ACCEPT-BLOCKING | 是 — `bash -c` fail-open，須原型②遞迴 |
| `COMPOSER-R1-P0-02` | D-2 | ACCEPT-BLOCKING | 是 — prompt 路徑須對齊 `.part` |
| `COMPOSER-R1-P1-01` | D-4 | ACCEPT-BLOCKING | 是 — 差集改必要子集＋附加堆 |
| `COMPOSER-R1-P1-02` | D-6 | SPLIT（主委裁） | 接受 — 本人原「不建議拆票」為條件式；主委拆出 Phase 4 機械面、保留 B-24 紀律面，符合「95% 解法」與降臨界路徑風險 |
| `COMPOSER-R1-P1-03` | D-8 | ACCEPT — 開 B-33 | 是 — OPEN-2 不納本批、標 MAJOR |
| `COMPOSER-R1-P1-04` | D-10 | ACCEPT — 隨 D-6 移出 | 是 — owner／UTC 到期／到期後狀態，與本人修法一致 |
| `COMPOSER-R1-P1-05` | D-1 | ACCEPT-BLOCKING | 是 — 疊加風險在 quote-strip 範圍，併入 D-1 |
| `COMPOSER-R1-P2-01` | D-12 | ACCEPT（明文化） | 是 — `grep -Eo` 僅在判定後、失敗不改 rc |
| `COMPOSER-R1-P2-02` | D-11 | ACCEPT（收窄） | 是 — Task 1.1 只保 harness 端 |
| `COMPOSER-R1-P2-03` | D-9 | ACCEPT — 補條件 | 是 — OPEN-3 Phase 0 後補查、不除役 |

**Q1（OPEN-1 timeout）** → D-7 PARTIAL：區間＝CLI process-group launch→return/kill（與 Q1 一致）；暫定值 composer **75m**、grok **70m**（聯集取大）、外層 **90m** — 接受暫定，Task 3.1 定稿。

**Q6（forward dep）** → D-13 ACCEPT：Phase 1→3.2、3.1→3.3、OPEN-1→3.3 補 §P — 與本人建議一致。

## D-1 主委獨立驗證（本機重跑）

```bash
bash .claude/tmp/b15probe3.sh
```

輸出摘要：`bash -c "codex exec x"` proto1=ALLOW（fail-open）、proto2=BLOCK；`sh -c 'grok …'` 同型；其餘 7 條 TN/TP 兩原型皆 ok。與 synth D-1 表一致 ⇒ 採原型②。

## D-6／D-7 主委裁決

- **D-6 SPLIT**：本人 R1 立場為「限縮可交付、不建議拆票除非再膨脹」；主委裁決拆出機械強制、保留紀律面 — **不反對**，理由充分。
- **D-7 暫定值**：本人建議 codex 50m／grok 65m／composer 75m；暫定表 grok 採 70m（聯集）— 更保守，可接受。

## 驗收

### `reconcile_stamps_check.sh`（完整 stdout）

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260804-govb0-spec-r1/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:1088062c7da80a7ea23978675f6a19d433b90d7523c21d5b75eb72470b581d7d task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（預期：codex 尚未蓋章；composer provenance 已通過 synth.md register-output）

**register-output**（stamp-target）：
```bash
bash scripts/gate.sh register-output GOVB0-R1-STAMP handoffs/reconcile/20260804-govb0-spec-r1/synth.md
# GATE PASS sha256:2ad434f3e70adb3b0238a41529b8ed4c6cc68700d7c2b55f81192f144fb08055
```

### `completeness_check.sh --lock`

```
COMPLETENESS PASS: .../20260804-govb0-spec-r1-codex.md — 9/9 個 ID 全在綜合檔。
COMPLETENESS PASS: .../20260804-govb0-spec-r1-composer.md — 10/10 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

rc=0

## /tmp 清帳

`/tmp` 與 `/private/tmp` 僅 `claude-501`（保留）與系統 `powerlog`；無 composer workdir 需刪。

---

STATUS: DONE
