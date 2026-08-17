# GAP-1 SPEC R6 複審 — COMPOSER（最終 SPEC 輪：R5 closure 複驗）

**task-id**: `20260817-GAP1-X-REVIEW-R6` | **family**: composer | **brief**: `handoffs/20260817-gap1-specadv-r6-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`e0e426ca5389`（commit `2482de77`）
**R5 本家**：`handoffs/20260817-gap1-specadv-r5-composer.md`（zero-findings sentinel `COMPOSER-R4-P3-00`）
**R5 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r5/synth.md`（群集 G1–G3；7/7 具名引用）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `e0e426ca5389…`
- μ 重算：`0.01/math.sqrt(8760)=1.068434607926721e-04` 與 §G:108-109 bit-match（`atol<1e-18`）
- R5 六條新 finding ID `grep -c`：CODEX P0-01=1、P1-01=2、P1-02=3、P1-03=1、GROK P1-01=1、P1-02=1（皆 ≥1）
- `cross_trial_sr_values` 僅殘留於 R4 更正註解（`SPEC:393`），主路徑已改 `ledger_result.valid_sharpe_values`
- reasons 計數：`ledger_row_invalid`＋`all_paths_degenerate` 等共 **11** 值（`SPEC:258-261`）

---

## Verdict：可進 TODO 生成

R5 reconcile G1–G3 修補經本輪逐條複驗**全部 CLOSED**；brief 四條 assumed 攻擊後無 **FATAL**。**BLOCKING 清單：無。**

---

## 1. Closure 表（COMPOSER R5 本家）

| R5 ID | 狀態 | 證據摘要 |
|---|---|---|
| COMPOSER-R4-P3-00 | **CLOSED**（維持零實質 finding） | R5 結論＝R4 closure（μ、F1–F4）與 assumed 攻擊後無 BLOCKING。本輪對 R5→SPEC R5 修補重跑同一探針：template PASS、μ bit-match、G1–G3 段落對照（見 §2）仍成立；無新可證偽缺陷。 |

---

## 2. Closure 表（reconcile G1–G3 — R5 修補複驗）

| 群集 | 引用 ID | 狀態 | 證據摘要 |
|---|---|---|---|
| G1 契約＋row 型別 | CODEX-R4-P1-01, GROK-R4-P1-01 | **CLOSED** | `SPEC:230-235` 頂層鍵 **14**（含 `reason_conditions`）；`ledger_record_keys` 物件化＋逐鍵 type/required＋`additional_properties:false`（`SPEC:237-243`）；reasons **11** 值含 `ledger_row_invalid`（`SPEC:258-261`）；`reason_conditions` key 集合與 `reasons` 雙向相等（`SPEC:266-268`）。 |
| G2 DSR N＋snapshot | CODEX-R4-P1-02, GROK-R4-P1-02 | **CLOSED** | Task 2.2 新增 `n_for_dsr`＋`snapshot_hash`（`SPEC:290-303`）；斷言⑥ `n_for_dsr == n_candidates_considered`；Task 3.2 釘死 `N := ledger_result.n_for_dsr`、`n_trials` 互斥（`SPEC:376-377`）；snapshot 比對＋`ledger_snapshot_mismatch`（`SPEC:378-380,394-395`）；驗收⑤ 改 `ledger_result.valid_sharpe_values`（`SPEC:391-393`）。 |
| G3 PBO path 退化＋universe | CODEX-R4-P0-01, CODEX-R4-P1-03, COMPOSER-R4-P3-00 | **CLOSED** | 步驟 3b path 級剔除／跳過／`all_paths_degenerate`（`SPEC:475-479`）；分母 `n_paths_used`；驗收⑦⑧（`SPEC:493-495`）。universe 唯一成功路徑＝`ledger_all_candidates`＋`ledger_result`＋hash 重算（`SPEC:509-527`）；`full_grid`／`external_declared` 一律 `universe_provenance_unverifiable`。 |

---

## 3. 是否可進 TODO 生成

**是。** 本輪無 **FATAL**；R5 四條 codex BLOCKING 修補均已關閉。

**BLOCKING 清單（僅 FATAL）：無。**

---

## 4. 未關項二分（本輪無 OPEN；下列為掃到的字面殘留）

| 殘留項 | 二分 | 理由 |
|---|---|---|
| Task 2.1 驗收⑤仍寫「13 個頂層鍵齊備」（`SPEC:278`）而正文已改 14 鍵 | **RESIDUAL-OK** | 契約正文與鍵名列（`SPEC:230-235`）已一致定義 14 鍵；實作／測試依正文即可，TODO Task 2.1 驗收字面改「14」不影響 B1–B4 數值正確性。 |
| `candidate_set_hash` canonical 演算法未逐字（僅「由 ledger candidate_id 集合重算」） | **RESIDUAL-OK** | G3 已封閉 top-K 成功路徑；hash 函式與 canonical ordering 在 contract 測試一次鎖定即可（R4–R5 延續殘留）。 |
| OOS「平均排名」partial tie 未寫代數式 | **RESIDUAL-OK** | 驗收④/④b 已釘全平手與 IS tie-break；`scipy.stats.rankdata(method='average')` 等價一句可在 TODO 釘死。 |
| `universe_provenance` dataclass 欄位列舉未明示 `ledger_result` 型別欄 | **RESIDUAL-OK** | Task 4.3 文字與驗收⑤（`SPEC:526-527`）已要求 `ledger_all_candidates` 必傳 `ledger_result`；TODO 起草時補 dataclass 欄位即可。 |

---

## 5. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| G1 之 14 鍵＋`reason_conditions` 雙向相等＋`ledger_record_keys` 物件化已使契約可唯一實作 | **成立**（`SPEC:230-268`；非法 row→`ledger_row_invalid`） |
| G2 之 `n_for_dsr == n_candidates_considered` 與 `snapshot_hash` 已使兩實作得相同 DSR | **成立**（`SPEC:300-303,376-380`；`n_trials` 互斥 raise） |
| G3 path 級剔除已消除 NaN 排序決定結果，universe 僅 `ledger_all_candidates` 可通過 | **成立**（3b＋`n_paths_used`；`full_grid` 驗收④b 封閉） |
| SPEC 已足以生成 TODO 並開始 B1；剩餘皆 RESIDUAL-OK | **成立**（見 §4；無 FATAL） |

---

## Findings（本輪新 finding：sentinel）

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對 R5 closure（本家 sentinel、reconcile G1–G3 共 7 條引用修補）與 brief 四條 assumed 攻擊後，無達 **FATAL** 門檻之新缺陷。

**碼證**: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS；μ 重算與 §G:108-109 一致；6 條 R4 finding ID grep≥1；G1 `SPEC:230-268`、G2 `SPEC:290-303,376-395`、G3 `SPEC:475-527` 對照；`cross_trial_sr_values` 僅註解殘留。RECHECK：同上命令＋`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '230,278p;290,303p;375,395p;475,527p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#e0e426ca5389

[P3] 信心度=High。核對依據＝closure 表 §1–§2 逐條狀態＋§5 assumed 表＋§4 RESIDUAL-OK 二分；刻意不捏造 finding 湊數。

---

ASSUMPTIONS_VERIFIED: template_check PASS；μ bit-match；6 ID grep≥1；G1–G3 段落對照；§4 殘留皆 RESIDUAL-OK
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；`venv/bin/python -c "import math; ..."` μ 重算；6× `grep -c`；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r6-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r6-composer.md`
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留未動
STATUS: DONE
