# GAP-1 SPEC R7 受限閉合複驗 — GROK

**task-id**: `20260817-GAP1-X-REVIEW-R7` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-r7-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（SPEC R6，commit `56cfb961`）@ sha256 前 12＝`503fd8a184f2`
**上一輪收斂**：`handoffs/reconcile/20260817-gap1-x-review-r6/synth.md`（H1 四條 FATAL 全採；body sha 前 12＝`846c47f79b32`）
**上一輪 FATAL 來源**：`handoffs/20260817-gap1-specadv-r6-codex.md`（`CODEX-R5-P0-01`～`04`；sha 前 12＝`54c294897f19`）
**本輪 finding 輪次**：R6（brief「本輪輪次=R6」；產出檔名 r7＝第 7 次 SPEC 複審／受限閉合輪）
**禁改碼／禁改 SPEC／禁蓋戳記**；範圍＝**僅**四條 FATAL 閉合複驗＋必答 2/3；不受理新一般性 SPEC 議題（除非達數值錯誤／不可重現＋可執行反例門檻）。

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `503fd8a184f2…`
- 四條 FATAL ID `grep -c`：`CODEX-R5-P0-01`=1、`P0-02`=2、`P0-03`=1、`P0-04`=2（皆 ≥1）
- `grep -c "13 個頂層"` → **0**（殘字已清；驗收⑤改 **15**）
- 頂層鍵名列＝**15** 且互異（含 `metric_unit_values`＋`reason_conditions`）
- 關鍵修補字面皆在場：`N_valid_on_path`、`artifact_hashes`、`source_artifact_hash`、`candidate_ids`、`ledger_result`、`metric_unit`、`rankdata(method="average")`、驗收 ④c／⑤b

---

## Verdict：可進 TODO 生成

四條 `CODEX-R5-P0-01`～`04` 於 SPEC R6 **全部 CLOSED**。重跑 codex 原始數值／集合反例後，修補寫死之定義已消除原分歧路徑。  
**BLOCKING 清單（僅達受限門檻之 FATAL）：無。**

---

## 1. Closure 表（四條 FATAL → SPEC R6）

| 上一輪 FATAL | 狀態 | 重跑同一反例／碼證 |
|---|---|---|
| `CODEX-R5-P0-01`（PBO rank 分母） | **CLOSED** | **SPEC**：`r = rank/(N_valid_on_path + 1)`、`rank ∈ [1, N_valid_on_path]`；平均排名＝`scipy.stats.rankdata(method="average")` 等價；驗收 ④c（path A 分母 6／path B 分母 4）。**反例重跑**：rank=2、全域 N=3 → `r=0.5, ω=0.0`；path-local N=2 → `r=0.666…, ω=0.693…`（與 codex 原 probe 一致）。④c 量級：N=5 rank=2 → `r=1/3, ω=-0.693`；N=3 rank=2 → `r=0.5, ω=0`——分母生效可證偽。兩合規實作若皆依 path-local 則同 ω。 |
| `CODEX-R5-P0-02`（snapshot membership 不可實作） | **CLOSED** | **SPEC**：`PeriodReturns.source_artifact_hash`（必填）；`LedgerReadResult.artifact_hashes: frozenset[str]`；DSR 綁定＝`source_artifact_hash ∈ artifact_hashes`（**集合成員**，非 digest 反推）。原「單一 snapshot_hash digest 無法做 membership」路徑已關閉。RECHECK：`grep -n 'source_artifact_hash\|artifact_hashes\|∈' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。 |
| `CODEX-R5-P0-03`（universe 守衛缺輸入） | **CLOSED** | **SPEC**：PBO 簽名新增必填 `candidate_ids`＋`ledger_result`；成功路徑僅 `ledger_all_candidates` 且三條件：① `set(candidate_ids)==ledger candidate_id 集合` ② count 三方相等 ③ `candidate_set_hash == sha256(",".join(sorted(candidate_ids)))`。**反例重跑（⑤b）**：50 vs top-10，`set(topk)!=set(full)` 且自算 top-10 hash 正確仍因集合相等失敗 → 必 `universe_provenance_unverifiable`。`full_grid`／`external_declared` 一律非成功。 |
| `CODEX-R5-P0-04`（ledger Sharpe 單位） | **CLOSED** | **SPEC**：`ledger_record_keys.metric_unit` 必填；值集合 `metric_unit_values=["per_period","annualized"]`；`valid_sharpe_values` 只收 `metric_name=sharpe` ∧ `metric_unit=per_period` ∧ `metric_valid=True`；混入 annualized → `ledger_row_invalid` 且不進樣本；頂層鍵 **15**。**尺度反例**：`periods_per_year=730` 時 annualized SR 放大 `√730≈27.02`、跨 trial variance 放大 **730**——單位混入會改 SR0/DSR；現由契約＋⑥b 鎖 per_period。 |

---

## 2. 可否進 TODO 生成？（brief 必答 2）

**是。** BLOCKING（FATAL）清單：**無**。

理由：四條修補皆為 SPEC 內可執行、可測的唯一定義（分母／集合成員／集合相等＋canonical hash／單位過濾），且附驗收 ④c／⑤b／⑥b；不存在「不修則 B1–B4 數值錯誤或不可重現」之未關 FATAL。

---

## 3. 未關項二分（brief 必答 3；含 6 項具名殘留攻擊）

| 項 | 二分 | 理由 |
|---|---|---|
| 四條 FATAL 本體 | **CLOSED** | 見 §1；無 OPEN／PARTIAL。 |
| §N 五項待接線（Optuna 生產者／output 矩陣／ml_pipeline／前端／wiring 閘門） | **RESIDUAL-OK** | 使用者裁決之範圍外接線；不改純統計 B1–B4 公式與契約正確性。 |
| C1 六條生產 bypass | **RESIDUAL-OK** | 生產者未接線前無法機器阻止；契約層已 fail-closed（`n_unknown`／`n_is_lower_bound`）。 |
| `ml_pipeline` 可消費不合格冠軍 | **RESIDUAL-OK** | 使用者「降級展示不硬擋」裁決；非 B1–B4 統計錯誤。 |
| adaptive `n_independence="unverified"` | **RESIDUAL-OK** | 誠實不換算；不引入假獨立 N。 |
| MinBTL 上界近似誤差未量化 | **RESIDUAL-OK** | 函式／欄位帶 `upper_bound` 語意；禁稱精確值。 |
| `universe_provenance` 欄位逐字／`LedgerReadResult` 未具名 `candidate_ids` 集合欄 | **RESIDUAL-OK** | 守衛語意（集合相等＋count＋hash）與 ⑤b 反例已寫死；TODO Task 2.2／4.3 具名 `candidate_ids: frozenset` 一行即可。**不**達「不修則數值錯誤」——兩實作依同一三條件得同一拒收／放行。 |
| DSR 驗收⑤b 字面仍寫「`snapshot_hash` 不涵蓋」而改法已是 `∈ artifact_hashes` | **RESIDUAL-OK** | 測法可等價為 hash ∉ 集合；不改 membership 語意。 |
| `valid_sharpe_values` 改法首句（299–301）未並排寫 `metric_unit`，⑥b／245–247 已鎖 | **RESIDUAL-OK** | 測試義務 ⑥b 強制 per_period；TODO 對齊首句即可。 |

**無 FATAL 未關項。** 6 項具名殘留攻擊後仍**不**推翻「不影響 B1–B4 正確性」——皆屬接線／展示／誠實降級／TODO 欄位釘名，非統計公式歧義。

---

## 4. 挑戰 brief assumed

| assumed | 本輪 |
|---|---|
| 四條修補皆已使兩個獨立實作得到相同數值，且 top-K 污染路徑已封閉 | **成立（攻後仍立）**。P0-01 path-local 分母＋④c；P0-02 集合成員；P0-03 集合相等＋⑤b 擋 top-K 自洽 hash；P0-04 單位＋⑥b。重跑數值／集合 probe 與 SPEC 一致。 |
| 6 項具名殘留皆不影響 B1–B4 正確性 | **成立（攻後仍立）**。見 §3；無一滿足「數值錯誤或不可重現＋可執行反例」之再開門檻。 |

---

## 5. Findings（本輪）

本輪對四條 FATAL 逐條重跑反例並核對 SPEC R6 寫死定義後，**無達受限門檻之新 FATAL／實質 finding**。依零 finding 契約寫 sentinel（不捏造湊數）。

## GROK-R6-P3-00

**斷言**: 本輪逐項核對 `CODEX-R5-P0-01`～`04` 於 SPEC R6 之修補後，四條皆 **CLOSED**；重跑 path-local rank 分母、snapshot 集合成員、top-K 50→10 集合相等、Sharpe 單位尺度四類反例後，無剩餘會使 B1–B4 產出數值錯誤或不可重現之 finding；6 項具名殘留仍為 RESIDUAL-OK。

**碼證**: (1) `template_check` PASS；(2) SPEC sha `503fd8a184f2`（commit `56cfb961`）；(3) 四 ID grep-c ≥1；(4) `13 個頂層` count=0、頂層鍵 15；(5) `SPEC:489-510` `N_valid_on_path`＋④c；(6) `SPEC:165-166,297-298,391-393` `source_artifact_hash`／`artifact_hashes` 集合成員；(7) `SPEC:471-473,530-554` `candidate_ids`＋`ledger_result`＋⑤b；(8) `SPEC:243-247,309-311` `metric_unit`／`valid_sharpe_values` 只收 `per_period`；(9) 數值 probe：path N=2 rank=2 → ω≈0.693 vs 全域 N=3 → ω=0；50≠10 set equality False。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '160,175p;230,315p;370,410p;469,555p'`；`python3` 重跑 rank／hash／set probe。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#503fd8a184f2

[P3] 信心度=High。核對依據＝§1 closure 表＋§3 殘留二分＋§4 assumed 攻擊＋上列實跑命令；本輪逐項核對後無 finding（sentinel）。刻意不捏造實質 finding 湊數。

---

## BLOCKING 清單（進 TODO 前；僅 FATAL）

**無。**

建議 TODO 起草時吸收（**非**阻擋，對應 §3 RESIDUAL-OK）：
1. Task 2.2：`LedgerReadResult` 具名 `candidate_ids: frozenset[str]`（或等價）供 4.3 集合相等直讀。
2. Task 3.2 驗收⑤b 字面改為 `source_artifact_hash ∉ artifact_hashes`。
3. Task 2.2 改法首句對齊 ⑥b：`valid_sharpe_values` 並寫 `metric_unit="per_period"`。

---

## 被當成事實的未驗證假設（§0）

- brief fact-verified（四 ID 命中、`13 個頂層`=0、template PASS）：**本輪實跑確認成立**。
- brief assumed（四修補使兩實作同值＋top-K 封閉）：**攻後仍立**（§4）。
- brief assumed（6 殘留不影響 B1–B4）：**攻後仍立**（§3）。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、R7 brief、R6 codex findings、R6 synth、SPEC R6；四 FATAL 修補字面與驗收在場；template_check PASS；四 ID grep≥1；13 殘字=0；path-local rank／top-K set／unit scale 數值 probe 已實跑。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；`shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `503fd8a184f2…`；4× `grep -c CODEX-R5-P0-0{1,2,3,4}` ≥1；`grep -c "13 個頂層"` → 0；python3 rank/hash/set probe rc=0（ω_old=0 vs ω_new≈0.693；set(top10)!=set(50)）。
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查；僅新增本檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC／碼）；結論＝四 FATAL 數值／守衛缺口於 R6 已關閉
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r7-grok.md`
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪 brief 只要求寫指定 review 產出
TMP_CLEANUP: 見收尾步驟
STATUS: DONE
