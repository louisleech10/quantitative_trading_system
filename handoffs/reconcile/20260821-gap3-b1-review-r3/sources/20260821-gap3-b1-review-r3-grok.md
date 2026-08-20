# GAP-3 B1 review R3 — grok（closure／sentinel）

task-id: 20260821-GAP3-B1-REVIEW-R3
family: grok
brief-kind: closure
brief: handoffs/20260821-gap3-b1-review-r3-brief.md
patch: `git diff e0cecf7c..HEAD -- momentum/ tests/`（HEAD=`bc4477df`：R2 三條寫回）
R2 裁決: handoffs/reconcile/20260821-gap3-b1-review-r2/synth.md

## Verdict：可蓋 RECONCILE-STAMP 進 B2（本輪無新 finding；sentinel 視角）

### 必答

1. **codex 三條 CLOSED？**  
   本家族非 CODEX-R2-P{1,2}-0{1,2} 原提出方；CLOSED 正式判定以同輪 codex 交件為準。sentinel 重跑三行為碼證：**皆已落地**——(Y1) uint64 降序 → `unsorted_bar`；(Y2) one-class＋NaN → `ValueError` 含「非有限值」（非 `unavailable`）；(Y3) 省略／`None`／短字串 hash → `TypeError`／`ValueError` fail-closed。`pytest tests/momentum/event_samples/ -q` → **100 passed**。

2. **修補新引入問題？**  
   **無**（見 sentinel `GROK-R3-P3-00`）。重點攻擊兩條：hash 必填未破壞既有呼叫端；合法 uint64（≤ int64 max）轉 int64 後與同值 int64 行為對等，超界拒。

3. **可蓋 RECONCILE-STAMP 進 B2 嗎？**  
   **可以（grok sentinel／本輪 APPROVED）**——前提為同輪 codex／composer 亦無新 BLOCKING 且其 CLOSED／sentinel 收斂。本檔戳記見文末。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**: uint64 timestamp 合法輸入（值 ≤ int64 max）轉 int64 後行為不變、超界拒 | **成立（攻擊不推翻）** | 升序 uint64 與同值 int64 皆回 `''` 且 `parity=True`；降序 uint64 → `unsorted_bar`；`max>int64.max` → `invalid_timestamp_unit`（先以 Python `int(arr.max())` 比對再 `astype`，無 wrap 後誤放行） |
| fact-verified: 修補後 suite 100 passed | **本輪複驗成立** | 見下 TESTS_RUN |
| hash 必填是否破壞既有呼叫 | **不破壞** | `grep` 呼叫端僅 `tests/momentum/event_samples/{test_baseline_oracle,test_mutation_guard}.py`（無 `api/`／其他 `momentum/` 生產呼叫）；全部已傳 64-char hash；省略關鍵字 → `TypeError`，`None`/短字串 → `ValueError` |

殘餘觀察（未達 P0–P2 finding）：實作以 `len==64` 閘門，`"x"*64` 非 hex 仍被接受寫入 receipts；與 commit／synth「64-hex」字面略寬。原 R2-P2-02 核心是「不可省略」；正式 hex charset 非本輪 sentinel 必答範圍，且 B1.6 實產 `sha256.hexdigest()` 恒為 hex——**不另開 finding、不捏造湊數**。

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——R2 三條寫回落地且未引入新矛盾；合法 uint64→int64 行為不變／超界拒；hash 必填未破壞既有呼叫端。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed rc=0；`git diff e0cecf7c..HEAD --stat -- momentum/ tests/` → 5 files +56/-24；uint64 probe A升序/`''`、B降序/`unsorted_bar`、C超界/`invalid_timestamp_unit`、D int64/`''`、E parity True；baseline omit→TypeError、None→ValueError、one-class+NaN→loud「非有限值」；呼叫端僅兩測試檔且皆已傳 hash。

**來源摘要**: handoffs/reconcile/20260821-gap3-b1-review-r2/synth.md#42996e573afa；momentum/Analysis/event_samples/alignment.py#0a7cf0773cc4；momentum/Analysis/event_samples/baseline.py#5ebe4e2fe875；tests/momentum/event_samples/test_alignment.py#acf9b8f1b45a；tests/momentum/event_samples/test_baseline_oracle.py#de818fd70529；handoffs/20260821-gap3-b1-review-r3-brief.md#fca26740b988

正文：sentinel 義務（hash 呼叫端／uint64 轉型）與 brief assumed 攻擊完成；adversarial 候選「非 hex 64 字元仍接受」低於可證偽 P0–P2 門檻（見上殘餘觀察）。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief assumed（uint64≤int64 max 行為不變、超界拒）已攻擊且成立。SPEC/TODO 重審／B2–B5／R1·R2 已 CLOSED 再議＝不受理。

ASSUMPTIONS_VERIFIED: uint64 合法升序≡int64；超界拒；降序 unsorted；hash 省略／None fail-closed；one-class+NaN loud；呼叫端僅測試且已更新；100 passed；patch range e0cecf7c..bc4477df
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed in 10.76s rc=0；手跑 alignment uint64 五探針＋baseline omit/None/one-class+NaN/legal hash
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b1-review-r3-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

## 戳記
RECONCILE-STAMP: grok APPROVED 2026-08-21 sha256:5cf1775a590e58186c1ecc3a04f79748b67f58e384932af3a3fe55dcf610c2dd task:20260821-GAP3-B1-REVIEW-R3

STATUS: DONE
