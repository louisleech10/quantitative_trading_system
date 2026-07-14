# IC1C SPEC r5 delta concur (Composer)

Task-id: IC1C-SPECREV-R5 | Reviewer: composer | Date: 2026-07-14  
SPEC: `docs/IC1C_NETIC_SPEC.md` **v0.5 r5** | 基線: r2 APPROVE+STAMP `handoffs/20260714-IC1C-SPECREV-R2-composer.md`  
輸入: codex r3/r4/r5 `handoffs/20260714-IC1C-SPECREV-R{3,4,5}-codex.md`；RECONCILE `handoffs/20260714-IC1C-SPECREV-RECONCILE.md`

---

## 1. r3–r5 delta 與 r2 APPROVE 相容性 (a)

| delta 項 | r2 已裁內容 | v0.5 落點 | 相容判定 |
|----------|-------------|-----------|----------|
| §U 統一佔位 union | R2 允許 unavailable+reason，但 Task 1.1/1.2 三形分裂(R2-1) | §U:33-34 凍 `{status,value,reason}`；presence 與 shape 分離(r4 F21) | **相容且收緊** |
| 三 profile 鍵集合 | §G 要求全鍵 equality，r2 未列精確集合 | §U:35-39 SKIPPED/GROSS_ONLY/COST_ENABLED + §G:70 綁定 | **相容且補 oracle** |
| finite validator | R2 §G 禁 JSON NaN/inf，未凍輸入域 | §U:41 三層 `0<cost_bps≤1000`+turnover 非有限→SKIPPED；M10/T1/T2/T5 | **相容_additive** |
| 階梯移 Phase 1 | R2 Task 3.1 掃 cost_drag；codex R2-1 指 phase 倒置 | §T:30 算法；Task 1.1:84/113；Phase 3 零 schema(G-NEW2 byte 等值) | **相容，修倒置** |
| M9-M10 / T4-T5 probe | R2 §V M1–M8；R2-2 422 探針缺口 | M9 union shape；M10 三層 test+probe；T4 vitest 同檔 probe；T5=config 層 | **相容且補證偽** |
| cost_bps=0 非法 | R2 未裁定 0；邊界寫 turnover=0 drag=0 | §U:41 域拒 0；Task 1.1:89 三層拒；§V:141 邊界目錄同步；無成本=`cost_enabled=False` | **相容，新裁不衝突** |

**RULING-FINAL B-strict / 1c-FR 拆票 / fail-closed**：§A:22、Task 1.2:92-94、拆票 1c-FR:116 均未改寫或弱化。r3–r5 僅在輸出契約(§U)、驗證(§V)、phase 分工上收緊，**無與 r2 APPROVE 相矛盾的裁決**。

---

## 2. r2 六項 BLOCKING 回歸 (b)

| ID | r2 閉合要點 | v0.5 對應 | 回歸 |
|----|-------------|-----------|------|
| COMPOSER-1 | 不傳 factor_returns；禁混減 e2e；unavailable | Task 1.2:92-94；Task 1.1:84-90；§A:22 | **未破** |
| COMPOSER-2 | net_factor_return 顯式 unavailable+reason | §U:34/37-38；Task 1.2:93；M3 | **未破** |
| COMPOSER-3 | §C 16 項 consumer manifest | §C:47-62 清單完整 | **未破** |
| COMPOSER-4 | 禁 5bps 三層；typed request；422；override reject | Task 2.1:101-106；§U:40 Phase1 schema；M5/M7 | **未破**（schema 提前 Phase1 為強化） |
| COMPOSER-5 | §G 全鍵 equality+canonical 重算 | §G:69-75 綁 §U 三 profile；G-NEW/G-NEW2 分層 | **未破**（profile 化為原 intent 落地） |
| COMPOSER-6 | 禁 `net_ic` 鍵；軸改 cost_drag | Task 1.1:86-88；Task 2.2:108；M1 | **未破** |

**6/6 BLOCKING 維持 CLOSED，r3–r5 未復開任一 r2 反例。**

---

## 3. R2-1/2/3 NON-BLOCKING 與 §U 收斂 (c)

| ID | r2 訴求 | v0.5 收斂 | 狀態 |
|----|---------|-----------|------|
| COMPOSER-R2-1 | 統一 MetricUnavailable 形狀 | §U:33-34 union；Task 1.2:93 具體物件；M9 `test_unavailable_union_shape` | **已收**（RECONCILE F14） |
| COMPOSER-R2-2 | route 層 422 須可驗 | Task 2.1:103「422 在 HTTP 邊界…route…同步路徑」；M7 override 422 | **已收**（併 F17） |
| COMPOSER-R2-3 | summary 恒 0 勿誤讀為全虧 | §U profile 將 profitable 限 COST_ENABLED 且 1c 恒 unavailable；Task 1.1:87 evaluable 恒 0；Task 2.2 文案 | **邊際已收**（無 `evaluation_status` 欄，與 r2 PARTIALLY 同級；RECONCILE 已裁併入 profile+文案，非 r5 新缺口） |

---

## 4. r5 delta 新洞掃描

- 逐條重跑 codex R4-1/R4-2 反例：`cost_bps=0` 三處一致非法；M10 T1/T2/T5 各有 test+同檔 probe — **與 codex R5 結論一致，無殘留矛盾**。
- §A:22「三者一律 unavailable」與 GROSS_ONLY 缺 breakeven/profitable 鍵：屬 profile 語意（無成本子樹則鍵不存在），r4 F21 已釐清 presence/shape 分工 — **非新洞**。
- 其餘：未見新 BLOCKING；未見曲解 r2 RECONCILE 17 筆或 r3–r5 F14–F26 裁決。

**本輪新 finding：0 BLOCKING / 0 NON-BLOCKING。**

---

## 5. 摘要

| 類別 | 計數 |
|------|------|
| (a) r2 相容 | 6/6 delta 項相容或收緊 |
| (b) BLOCKING 回歸 | 0/6 |
| (c) R2-1/2/3 收斂 | 3/3（R2-3 邊際與 r2 同級，未惡化） |
| r5 新 finding | 0 |

```
ASSUMPTIONS_VERIFIED: SPEC v0.5 全文；R2-composer/R3-R5-codex/RECONCILE 對照；rg §U/Task/§V 關鍵落點
TESTS_RUN: shasum -a 256 handoffs/20260714-IC1C-SPECREV-RECONCILE.md → d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d；review-only 未跑 pytest/vitest
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審+本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: review-only；確認 v0.5 schema/邊界裁決與 r2 intent 一致
```

DELTA-CONCUR: APPROVE
RECONCILE-STAMP APPROVED — composer 2026-07-14 sha256:d71c4ee1b5a55a993a92c3ff5de1d9c36d411b969d0dbf9f7fd68ed33a26096d
