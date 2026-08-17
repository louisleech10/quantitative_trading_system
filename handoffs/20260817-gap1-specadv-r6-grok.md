# GAP-1 SPEC R6 複審 — GROK（R4 findings / G1–G3 closure 複驗 vs SPEC R5）

**task-id**: `20260817-GAP1-X-REVIEW-R6` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-r6-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`e0e426ca5389`（commit `2482de77`／訊息含「SPEC R5」）
**上一輪本家**：`handoffs/20260817-gap1-specadv-r5-grok.md`（finding ID＝GROK-R4-P1-01／P1-02）
**上一輪收斂**：`handoffs/reconcile/20260817-gap1-x-review-r5/synth.md`（G1–G3；body sha256 前 12＝`6fb40fafe2f0` 之 full-file 前 12；本輪不蓋戳記）
**禁改碼／禁改 SPEC／禁蓋戳記**（僅 closure + assumed 攻擊 + FATAL／RESIDUAL-OK 二分）
**本輪 finding 輪次**：R5（brief 範本「本輪輪次=R5」；產出檔名 r6＝第 6 次 SPEC 複審）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `e0e426ca5389…`
- R4 六條 ID `grep -c`：GROK-R4-P1-01=1、GROK-R4-P1-02=1、CODEX-R4-P0-01=1、CODEX-R4-P1-01=2、CODEX-R4-P1-02=3、CODEX-R4-P1-03=1（皆 ≥1）
- 頂層鍵：改法列名 **14** 個且含 `reason_conditions`；`reasons` 字面 **11** 值（含 `ledger_row_invalid`／`all_paths_degenerate`）
- `ledger_record_keys` ＝物件＋`type`/`required`/`additional_properties:false`＋非法列 `ledger_row_invalid`
- DSR：`N` 恆取 `ledger_result.n_for_dsr` 且 `n_for_dsr == n_candidates_considered`；驗收⑤ 已改 `valid_sharpe_values`（`cross_trial_sr_values` 僅出現於「前版誤引用」說明句）
- PBO 3b：`n_path_exclusions`／`n_paths_skipped`／`n_paths_used`／`all_paths_degenerate`＋驗收⑦⑧
- universe：唯一成功＝`ledger_all_candidates`；`full_grid`／`external_declared` 一律 `universe_provenance_unverifiable`（驗收④／④b／⑤）
- 殘字：`grep -n '13 個頂層'` → **L278 驗收⑤仍寫「13 個頂層鍵齊備」**（改法已 14；見 §3 RESIDUAL-OK）

---

## Verdict：可進 TODO 生成

本家 R4 兩條 **CLOSED**。R5 synth G1–G3（契約 14 鍵＋row 型別＋`n_for_dsr`／`snapshot_hash`＋PBO path 退化＋universe 僅 ledger）**主幹 CLOSED**，足以生成 B1–B4 TODO。

**BLOCKING 清單（僅 FATAL）：無。**

殘留皆判定 **RESIDUAL-OK**（§3）——規格細節／可在對應 TODO Task 一句釘死，**不**使 B1–B4 在正確實作下產出錯誤統計量；依最終 SPEC 輪收斂紀律不重開修訂輪。

---

## 1. Closure 表（本家 R4 → SPEC R5）

| R4 ID | 狀態 | 證據摘要 | FATAL／RESIDUAL-OK（若未全關） |
|---|---|---|---|
| GROK-R4-P1-01 | **CLOSED** | L230-235：僅含 **14** 頂層鍵，`reason_conditions` 為第 14 鍵；L266-268 物件 schema＋與 `reasons` **雙向相等**；L237-243 `ledger_record_keys` 物件化＋`ledger_row_invalid`。原「13 鍵 vs 必須提供 reason_conditions」互斥已消。 | —（驗收⑤殘「13」字面 → §3 RESIDUAL-OK-1，非原缺陷重開） |
| GROK-R4-P1-02 | **CLOSED** | L290-301：`n_for_dsr` 契約＝`n_candidates_considered`；L376-377 DSR 之 N **恆取** `n_for_dsr`、`n_trials` 在場必 `None`；L391-395 驗收⑤改 `valid_sharpe_values`、⑤b snapshot／雙傳 raise。 | — |

---

## 1b. Closure 表（R5 synth G1–G3／codex 四條 BLOCKING — 複驗）

| 群集／ID | 狀態 | 證據摘要 | 二分 |
|---|---|---|---|
| G1 CODEX-R4-P1-01／GROK-R4-P1-01 | **CLOSED**（契約可唯一實作主幹） | 14 鍵＋`reason_conditions` 雙向相等＋`ledger_record_keys` 物件＋reasons **11** 值（`ledger_row_invalid`／`all_paths_degenerate`）。 | 驗收⑤「13」字面＝RESIDUAL-OK-1 |
| G2 CODEX-R4-P1-02／GROK-R4-P1-02 | **CLOSED**（N 取值＋驗收 dataflow） | `n_for_dsr` 釘死；`snapshot_hash` 定義於 Task 2.2⑦；DSR 綁定＋⑤／⑤b。 | snapshot **成員檢查**僅有聚合 hash、無集合欄位＝RESIDUAL-OK-2（守衛可實作細節，非 SR0 公式歧義） |
| G3 CODEX-R4-P0-01 | **CLOSED**（禁 NaN 排序主幹） | 步驟 3b path 剔除／跳過／`all_paths_degenerate`；分母 `n_paths_used`；驗收⑦⑧。 | path 上 `r=rank/(N_valid+1)` 之 `N_valid` 是否 path-local＝RESIDUAL-OK-3（TODO 一句＋golden 可鎖） |
| G3 CODEX-R4-P1-03 | **CLOSED**（top-K 自洽通關） | 唯一成功 `ledger_all_candidates`＋ledger 重算 hash＋三方 count；`full_grid`／`external_declared` 一律非成功（④b）。 | `ledger_result` 未進 Task 4.2 簽名欄位表、hash canonical 序列化未寫死＝RESIDUAL-OK-4 |

---

## 2. 挑戰 brief assumed

| assumed | 本輪 |
|---|---|
| G1：14 鍵＋`reason_conditions` 雙向相等＋`ledger_record_keys` 物件化 ⇒ 契約可唯一實作 | **成立（攻後仍立）**。改法鍵集合、row schema、reason 枚舉與雙向相等測試義務已寫死。殘：驗收⑤ 字面「13」與改法 14 不一致——測試作者若只抄驗收句會寫錯斷言，但**實作鍵集合以改法 14 名為準**已無互斥；RESIDUAL-OK-1。 |
| G2：`n_for_dsr == n_candidates_considered`＋`snapshot_hash` ⇒ 兩獨立實作同 DSR | **主幹成立**。N 無從自選欄位；同一 `valid_sharpe_values`／`n_for_dsr`／per-period 矩 ⇒ 同 SR0／DSR 公式。殘：`period_returns` artifact「屬於 `snapshot_hash` 所涵蓋集合」在**僅有聚合 hash、無 `input_artifact_hashes` 欄**時無法做集合成員測試——兩實作可能用（A）額外保留 hash 集合（B）誤比對單 hash——影響 **status/mismatch 守衛**，不改已接受輸入下之 DSR 數值；RESIDUAL-OK-2，TODO Task 2.2／3.2 釘 `artifact_hashes: frozenset` 或等價。 |
| G3：path 級剔除消除 NaN 排序；universe 僅 `ledger_all_candidates` 封閉 top-K | **成立（攻後仍立）**。3b 明確剔除非有限 metric、&lt;2 跳過、全跳過 fail-closed；`full_grid` 自洽 hash 反例已封（④b）。殘：3③ 之 `N_valid` 與 3b path 剩餘集合之關係未重寫——極端 path 部分剔除時 `r` 分母可歧義（見 §3 反例量級）；**不重開為 FATAL**（主幹已禁 NaN 排序；TODO／golden 鎖 path-local `N_eff` 一行即可）＝RESIDUAL-OK-3。 |
| SPEC 已足以生成 TODO 並開始 B1；剩餘皆 RESIDUAL-OK | **成立（攻後仍立）**。無 FATAL；§3 殘留均可在 Task 2.1／2.2／3.2／4.2／4.3 動工前於 TODO 釘死，不需重做 phase 或公式族。 |

---

## 3. 未關／殘留項二分（brief 必答 3）

| 項 | 二分 | 一句理由 |
|---|---|---|
| RESIDUAL-OK-1：Task 2.1 驗收⑤「13 個頂層鍵齊備」vs 改法 14 | **RESIDUAL-OK** | 改法已列死 14 名；殘字不改 B1–B4 統計；TODO 斷言 `len(top_keys)==14` 即可。 |
| RESIDUAL-OK-2：`snapshot_hash` 成員檢查缺集合欄位／canonical 序列化細節 | **RESIDUAL-OK** | 影響 mismatch 守衛可實作性，不影響已接受輸入之 DSR 公式；TODO 補 `artifact_hashes` 或等價＋sha 序列化一句。 |
| RESIDUAL-OK-3：PBO 3b 後 `N_valid` path-local vs global | **RESIDUAL-OK** | 部分 path 剔除時 `r=rank/(N+1)` 分母可歧義（例：path 剩 3、名次 2 → N=3⇒r=0.5,ω=0；N=5⇒r=1/3,ω&lt;0）→ PBO 可比對分叉；**主幹 NaN 排序已封**；TODO Task 4.2 寫死 `N_eff=path 剩餘有效數`＋fixture 即可，不擋 TODO 生成。 |
| RESIDUAL-OK-4：`ledger_result` 傳入位置／`candidate_set_hash` canonical 算法 | **RESIDUAL-OK** | 成功路徑語意已封；簽名欄位 nested vs kwarg 與 hash 字節格式屬 API 釘死，不改 PBO 統計定義。 |
| `reason_conditions` 表體未在 SPEC 預填 11 條 condition 原文 | **RESIDUAL-OK** | 結構＋雙向相等＋各 Task 觸發句已足夠；表體為契約檔產物。 |
| §N 既有接線／adaptive／MinBTL 上界語意等 | **RESIDUAL-OK** | 使用者裁決與 brief 不受理範圍；不進本輪 BLOCKING。 |

**無 FATAL 未關項。**

---

## 4. Findings（本輪）

本輪無達 **FATAL**（亦無須再修 SPEC 才准生成 TODO 之 MAJOR）之新缺陷；殘留僅 §3 RESIDUAL-OK 表。依零 finding 契約寫 sentinel（不捏造實質 finding）。

## GROK-R5-P3-00

**斷言**: 本輪逐項核對 R4 本家 2 條、R5 收斂 G1–G3（含 codex 四條 BLOCKING 之 SPEC R5 修補）與 brief 四條 assumed 攻擊後，**無 FATAL finding**；剩餘不一致皆為可在 TODO 釘死之 RESIDUAL-OK（見 §3），不阻擋 TODO 生成與 B1 開工。

**碼證**: (1) `template_check` PASS；(2) SPEC sha `e0e426ca5389`；(3) 六 ID grep-c 皆 ≥1；(4) L230-268 十四鍵＋reason 雙向＋ledger 物件＋11 reasons；(5) L290-304／L375-395 `n_for_dsr`／`snapshot_hash`／驗收⑤更名；(6) L475-495／L509-527 path 3b＋universe 唯一 ledger 成功；(7) 殘字僅 L278「13 個頂層」與 snapshot 成員語意／N_eff 分母——均未達「不修則數值錯誤或不可重現且無法於 TODO 鎖定」之 FATAL 門檻。RECHECK：`grep -n '14 個頂層\|n_for_dsr\|all_paths_degenerate\|ledger_all_candidates\|13 個頂層' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`；重讀 Task 2.1／2.2／3.2／4.2／4.3。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[P3] 信心度=High。核對依據＝§1／§1b closure 表＋§2 assumed 表＋§3 二分；刻意不捏造實質 finding 湊數。本輪核對後無 finding（sentinel）。

---

## BLOCKING 清單（進 TODO 前；僅 FATAL）

**無。**

建議 TODO 起草時吸收（非阻擋，對應 §3）：
1. Task 2.1 驗收⑤：`14` 頂層鍵（非 13）
2. Task 2.2／3.2：`artifact_hashes`（或等價）供 snapshot 成員檢查＋canonical sha 序列化
3. Task 4.2：path 剩餘集合上 `N_eff` 與 `r=rank/(N_eff+1)`；3b 後再選 champion
4. Task 4.2／4.3：`ledger_result` 簽名位置＋`candidate_set_hash` 字節級 canonical

---

## 必答對照

1. **closure**：本家 2/2 **CLOSED**；G1／G2／G3 主幹 **CLOSED**；細節殘留見 §3 皆 **RESIDUAL-OK**。
2. **可否進 TODO**：**是** — FATAL／BLOCKING 空。
3. **未關項二分**：無 FATAL；§3 列 6 項皆 **RESIDUAL-OK**。

---

## 被當成事實的未驗證假設（§0）

| 陳述位置 | fact / assumed | 本輪 |
|---|---|---|
| brief：G1 契約可唯一實作 | assumed | 攻後**成立**（主幹；驗收⑤字面殘） |
| brief：G2 兩實作同 DSR | assumed | 攻後**主幹成立**（N 釘死；snapshot 成員守衛細節殘） |
| brief：G3 path/universe 封閉 | assumed | 攻後**成立**（N_eff 分母殘） |
| brief：足以 TODO 且剩餘 RESIDUAL-OK | assumed | 攻後**成立** |
| 主委未採納 grok「具名殘留」、改當輪修完 | fact-verified（synth 未採納節） | 接受；本輪複驗修補已落地 |

---

ASSUMPTIONS_VERIFIED: 本家 R4 兩條 closure；G1–G3 段落對照；14 鍵／11 reasons 計數；n_for_dsr 契約；PBO 3b／universe 封閉；template PASS；六 ID grep；L278 殘「13」；snapshot 成員語意與 N_eff 殘留定位
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS；`shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → e0e426ca5389…；6× `grep -c` R4 ID；鍵／reason 計數 python；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r6-grok.md --family grok`（交件前自跑）
FAILURES_SEEN: none（本輪無改碼）
SCOPE_CHANGES: none（只讀審查＋本 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC／碼）；殘留建議僅 TODO 斷言與 API 釘死
OUTPUT_ARTIFACT: handoffs/20260817-gap1-specadv-r6-grok.md
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留未動

STATUS: DONE
