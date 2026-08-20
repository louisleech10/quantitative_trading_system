# GAP-3 B1 review R2 — grok（closure／sentinel）

task-id: 20260821-GAP3-B1-REVIEW-R2
family: grok
brief-kind: closure
brief: handoffs/20260821-gap3-b1-review-r2-brief.md
patch: `git diff df45bc82..e0cecf7c -- momentum/ tests/`（commit e0cecf7c）
R1 裁決: handoffs/reconcile/20260821-gap3-b1-review-r1/synth.md

## Verdict：可蓋 RECONCILE-STAMP 進 B2（本輪無新 finding；sentinel 視角）

### 必答

1. **原提出方逐條 CLOSED？（codex 7、composer 1）**  
   本家族非該八條原提出方；CLOSED 正式判定以 codex／composer R2 交件為準。sentinel 碼證：兩家反例已入 `test_dedupe.py` 且通過；M1/M3/M5/M10 改生產 seam；T8–T10 nested／close_time／row_id／NaN fail-closed／manifest hash 皆有對應回歸；`pytest tests/momentum/event_samples/ -q` → **98 passed**。未見修補未落地之反例殘留。

2. **修補新引入問題？**  
   **無**（見 sentinel `GROK-R2-P3-00`）。全檔重掃 `dedupe`／`baseline`／`feature_materialization`／`alignment`／`import_contract`／mutation／對應測試後，未發現需列 P0–P2 的新矛盾。

3. **可蓋 RECONCILE-STAMP 進 B2 嗎？**  
   **可以（grok sentinel／本輪 APPROVED）**——前提為同輪 codex／composer 亦對其原 finding 標 CLOSED 且無新 BLOCKING。本檔戳記見文末。

### R1「相鄰鏈對等價」覆核（明文撤回）

R1 正文主張「interval 排序相鄰鏈對 overlap 連通分量等價」**不成立**，已被兩家反例＋本輪重跑推翻：

| 反例 | 排序後相鄰鏈（gap=0） | UF／區間聯集 | 本輪 |
|---|---|---|---|
| COMPOSER：A[0,100], C[30,35], B[40,50] | A–C 同簇、B 被拆（C⟂B） | 三者同簇（A⊃B） | `test_transitive_overlap_union_find_composer_counterexample` PASS；手跑同結果 |
| CODEX：a[0,100], b[50,60], c[90,120] | a–b 同簇、c 被拆（b⟂c） | 三者同簇（a∩c） | `test_transitive_overlap_union_find_codex_counterexample` PASS |

手跑舊鏈模擬（composer 輸入）→ `A:c0, C:c0, B:c1`；新 UF → 全 `c0`。與 synth X1「grok 等價主張被推翻、採較嚴」一致。**本輪正式撤回 R1 該判斷。**

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **X1** UF gap＝事件 i 自身答案窗 duration、對所有 j>i 檢查，與 TODO「cluster_gap 預設＝答案窗 duration」一致 | **成立（攻擊不推翻）** | TODO/SPEC 字面未指定對稱 gap；實作以排序後較早事件 i 之 duration 向前掃，與舊相鄰鏈「用前一事件 duration」同向；`cluster_gap_ms=None` 時 touch（start 差＝duration、無 overlap）會 union，短早＋遠晚分離——皆符合「UTC duration／config 可調」。O(n²) 對事件級 n 可接受（實作註解＋brief）。 |
| **X6** baseline 任一 NaN/inf fail-closed（嚴於 TODO「特徵全 NaN」字面）屬較嚴且與 B1.6 一致、非越權 | **成立（攻擊不推翻）** | B1.6 契約禁 NaN 混入特徵表；baseline 見非有限＝上游破缺。舊 pairwise 靜默刪列違反 §0「NaN/inf 不弱化」。`test_partial_nan_inf_fail_closed` 對單 cell NaN／inf 皆 `ValueError`。TODO 邊界仍寫「全 NaN」屬敘事較鬆；**SPEC/TODO 重審＝不受理**，不另開 finding。 |
| fact-verified: 98 passed | **本輪複驗成立** | 見下 TESTS_RUN |

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——R1 八條修補落地且未引入新矛盾；R1「相鄰鏈對等價」已撤回；X1／X6 兩條 assumed 攻擊不成立。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed rc=0；`git diff df45bc82..e0cecf7c --stat -- momentum/ tests/` → 13 files +254/-62；舊鏈模擬 composer 反例 A/C/B → B 入 c1，新 UF＋`test_dedupe` 兩反例 → 全 c0；X1 gap 探針 touch 同簇／短早遠晚異簇；X6 單 cell NaN/inf → ValueError；mutation 四 seam 皆 monkeypatch 生產路徑；truncate_mode 仍強制 ms[pos]==target。

**來源摘要**: handoffs/reconcile/20260821-gap3-b1-review-r1/synth.md#d680f3943116；handoffs/20260821-gap3-b1-review-r1-grok.md#60f4db270029；momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0；momentum/Analysis/event_samples/baseline.py#e13696f0eb59；tests/momentum/event_samples/test_dedupe.py#3290a1d85bf2；docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：adversarial 候選（gap 不對稱／TODO「全 NaN」字面／truncate_mode 繞過 row_id）逐項核對後不達可證偽 P0–P2 門檻或落在不受理之 SPEC/TODO 重審。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief 兩條 assumed 已攻擊（上表）。D-001 三條本輪不受理重審。

ASSUMPTIONS_VERIFIED: X1 gap＝事件自身 duration 向前掃與 TODO 一致；X6 任一非有限 fail-closed 與 B1.6／不弱化原則一致；相鄰鏈≠UF（反例＋舊鏈模擬）；98 passed；patch e0cecf7c 為 HEAD 祖先
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed rc=0；targeted dedupe/baseline/mutation/alignment/import/materialize → 73 passed rc=0；手跑 composer/codex 反例與舊鏈模擬
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b1-review-r2-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

## 戳記
RECONCILE-STAMP: grok APPROVED 2026-08-21 sha256:85151322543608a37660f900039446e63ac7d4689decd7d7a60c91e7727aaf82 task:20260821-GAP3-B1-REVIEW-R2

STATUS: DONE
