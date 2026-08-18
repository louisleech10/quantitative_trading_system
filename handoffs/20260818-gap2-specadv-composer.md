brief-kind: review

# GAP-2a／2b SPEC adversarial 審查 R1 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R1`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-specadv-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| D1 van der Waerden 秩空間投影最合適 | assumed | **部分成立**：SPEC 已鎖 D1＋O1 raw 反向斷言；train/test 各自 `normal_scores` 是刻意 OOS 設計（非 leakage），O7 可證偽 test-fit |
| O1 0.02／O4 [0.85,1.15] 足夠嚴且不假紅 | assumed | **O4 成立**（探針 3 trial ratio∈[0.96,1.02]）；O1 雙通過條（`residual_degenerate` OR ≤0.02）略寬但可接受 |
| 五批無 forward dependency | assumed | **成立**；1.2→2.1 bootstrap 搬移已標覆蓋風險 |
| `MarginalICConfig.enabled` 預設 True 不弄壞既有測試 | assumed | **成立**（`grep marginal_ic tests/` → 0；§G-1 剝 `marginal_ic` 後比 sha；既有測試無全報告鍵集相等斷言） |
| §N R1–R5 三值理由成立 | assumed | **成立**（R1 user-ruling／R2 needs-research／R3 blocked-by #4／R5 blocked-by holdout；R4 預設納入＋白話閘否決合規） |
| Task 3.1 契約欄位對 ML 防 stale 足夠 | assumed | **不成立**：收斂 C4 要求之 `symbol`／`timeframe` 未入 Task 3.1 鍵集（見 P1-02） |
| `deny_factor_in_ok_oos` 不誤傷新節 | fact-verified | **成立**（`contracts.py:2005-2012` 僅拒 `module∈{orthogonalization,exposure}`） |
| B3→B4 `test_r6` 順序可過 | fact-verified | **成立**（SPEC Task 3.1 L156 明寫 B3 只加鍵、reason 值 B4 同 commit；`test_ichc_contract_sync.py:43-62` 掃 orchestrator 字面） |

---

## COMPOSER-R1-P1-01

**斷言**: §G O5 標籤置亂門檻（L82 `2/√n_test`）與同節 Oracle 矩陣（L248「多重比較＝Bonferroni 於同測試內多因子」）自相矛盾，實作者無法同時滿足兩處，且按 L82 實作會對多 survivor 場景偏寬（假綠風險）。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:82` vs `:248`；`docs/TEST_DESIGN_CHARTER.md` F-IC-6 要求標籤置亂檢定。RECHECK: `rg -n 'O5|Bonferroni|2/√n' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=High。多因子（k>1）時未 Bonferroni 調整，O5 可能放過非零邊際 IC。修法：統一 O5 為 `|marginal_ic| < (2/√n_test)·α_adj`（`α_adj=0.05/k_features` 或契約寫死 Bonferroni 公式），並刪除 L248 與 L82 之一致性衝突。

---

## COMPOSER-R1-P1-02

**斷言**: 收斂檔 C4 明定倖存者契約須含 `symbol`／`timeframe`（`synth.md` C4-2 欄位聯集），但 SPEC Task 3.1 之 `provenance_keys`／語意描述（L157）與 `build_survivor_output` 參數均未要求兩欄，亦無 §G-4 契約 oracle 驗證——C4 義務被靜默弱化，未來 ML 消費端無法 fail-closed 拒 cross-symbol stale 檔。

**碼證**: `handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md` C4「symbol／timeframe／…」；`docs/GAP2_MARGINAL_IC_SPEC.md:155-157` provenance 列舉無 symbol/timeframe；`rg symbol\|timeframe docs/GAP2_MARGINAL_IC_SPEC.md` 僅 L26 `allowed_symbols` receipt。RECHECK: 對照 synth C4 與 Task 3.1 鍵集。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md#7c72c0aa258d

[MAJOR] 信心度=High。2b 契約無單標的身份欄，僅 `base_universe_hash` 不足以讓消費端區分同 hash 不同 symbol 的誤載。修法：Task 3.1 契約加 `symbol`／`timeframe`（required）＋ validator ⑭ 與 §G-4 tamper（錯 symbol 必 raise）。

---

## COMPOSER-R1-P2-01

**斷言**: §V 17 條 mutation 未覆蓋收斂 C7／CODEX-R1-P1-06 要求之 `shuffle-S`（條件集列順序／歸屬錯誤）與 `hash/symbol mismatch`（倖存者檔 identity 錯配），存在「改壞條件集或 identity 仍綠」的假綠窗。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:225-242` 列 V-1..V-17 無 shuffle-S／symbol-hash mismatch；`synth.md` C7「shuffle-S／hash mismatch 之 mutation」；`docs/TEST_DESIGN_CHARTER.md` A2 洩漏 MR 要求可證偽 mutation。RECHECK: `rg 'shuffle|symbol mismatch|V-1[0-9]' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=Medium。V-4（loo 含 f）不涵蓋「S 列順序錯誤但集合相同」；契約 oracle ⑫ 只驗 `feature_set_hash`，不驗 symbol。修法：增 §V-18（shuffle `Z_S` 列⇒loo 不變、sequential 變⇒紅）與 §V-19（`symbol` tamper⇒validator 紅）。

---

## COMPOSER-R1-P2-02

**斷言**: Task 4.1 邊界 ④「cache-hit `refilter`」列為邊界卻無可量化驗收，Agent 可能讓 refilter 在 cache 命中時跳過 stage6b 或沿用過期 `stage6b_results`，與 D7「三入口一致」衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:183` 邊界 ④ 無對應「驗證」子句；現行 `refilter()` 僅 stage5→6→7（`ic_filter_orchestrator.py:1736-1765`），stage6b 尚未存在；deep cache-hit 先例見 `:1850-1855`（降級而非靜默 ok）。RECHECK: 讀 Task 4.1 邊界 vs 驗證清單是否成對。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MINOR] 信心度=Medium。refilter 後 `per_feature` 鍵集與 survivors 不一致風險。修法：Task 4.1 驗證增 ⑩「cache 命中後 `refilter()` ⇒ `marginal_ic.per_feature` 鍵 == 新 `filtered_df.columns` 且 `stage6b_results` 已刷新」。

---

## 必答 1–9（逐條 verdict）

### 1. 統計定義正確性

**Verdict: 可接受，一處修補（O5）**。D1 semi-partial 秩 IC、train/test 分段 `normal_scores`、`|train_ic|` sequential 排序與 D4「不改選擇」一致。`ic_retained_ratio` 僅處理 `|gross|<1e-12`（負 gross 時比值語意未文件化，屬 MINOR 文件缺口）。O1–O9 中 O7／O1 raw 反向斷言可防「跑得綠但不正確」；**O5 因 Bonferroni 矛盾可能假綠**（P1-01）。O4 容差本輪探針 3/3 落在 [0.85,1.15] 內（`/tmp/composer-gap2-specadv-r1/o4_probe.txt`）。

### 2. OOS 與揭露誠實度

**Verdict: 足夠且較嚴**。D3′ 機器欄 `independent_oos_validation=false`＋`selection_sample="test"`＋train/test 並列（F-IC-8）直接回應 C1。`oos_guarantees` 沿用 root（preprocessing＋投影不在 test 擬合）與 `independent_oos_validation` 分離，不與 root 契約矛盾且較嚴於靜默宣稱獨立 OOS。`marginal_ic_train_insample` 命名含 `train_insample`，配合 D3′(d) 禁文案，誤讀風險低。

### 3. 可證偽驗收

**Verdict: 整體強，缺 2 條 mutation（P2-01）**。各 Task「驗證」含 rc=0／數值門檻／契約 raise，改壞即 FAIL 意圖明確。§V 17 條覆蓋 train-fit、秩空間、符號／權重來源、契約 fail-closed、§G-1 既有鍵；**缺 shuffle-S、symbol-hash mismatch**。

### 4. forward dependency 與存活性

**Verdict: 無白工**。B1→B2→B3→B4→B5 依賴方向正確；1.2 內部 bootstrap→2.1 搬移標為同批合併（L137）。B3 契約鍵集與 B1/B2 `to_dict()` 對照在 Task 3.1 驗證 ⑨，方向為契約釘死→實作對齊，無反向依賴。

### 5. 義務覆蓋（C1–C7）

| 群集 | SPEC 對應 | 缺口 |
|---|---|---|
| C1 test 已被 selection 消費 | D3′、§N R5 | 無 |
| C2 semi-partial 秩 IC | D1/D2、§G O1/O7 | 無 |
| C3 禁第二次選擇＋組合 CI | D4/D5、§N R2 | 無 |
| C4 sample_scope＋欄位聯集 | Task 3.1 | **缺 symbol/timeframe（P1-02）** |
| C5 stage 6b 三入口 | D7、Task 4.1 | 無 |
| C6 契約／wiring／types | Task 4.3、B5 | 無 |
| C7 oracle＋mutation | §G、§V | **mutation 未全（P2-01）** |

### 6. 契約設計（2b）

**Verdict: 可行，一處欄位缺口**。ref 機制、`additional_properties:false`、`sample_scope` 結構、AST sync `RowMaskPlan.source`（Task 3.1 ⑦）設計完整。Task 3.1 L157 語意描述標「鍵名以契約檔為準」，屬同一 Task 內輔助說明，**不構成第二處機械列舉**（§C 禁的是跨章節複列）。載入：`resolve_ref` fail-closed，無循環風險。

### 7. 接線影響面

**Verdict: 白名單完整，一處邊界待寫**。7 處白名單與三入口／fallback／xsec／`_suppress_persist`（Task 4.2）均有對應。`ic_wiring_check` 改讀契約（Task 4.3）**擴大** R3 覆蓋至六節，語意變嚴不變鬆。B5 `npm run build`／`tsc` 已列驗證。cache-hit refilter 驗收缺口見 P2-02。

### 8. 殘留誠實度（§N R1–R5）

| 殘留 | 三值 | Verdict |
|---|---|---|
| R1 ML 橋 | user-ruling | **成立** — 成熟度地圖＋使用者裁定 |
| R2 forward 選擇 | needs-research | **成立** — post-FDR 政策未定 |
| R3 xsec | blocked-by #4 | **成立** — xsec IC 未重建 |
| R4 前端表格 | 預設納入 | **合規** — 白話閘可否決 |
| R5 nested OOS | blocked-by holdout | **成立** — 主線無 nested test |

### 9. 可否進 TODO

**Verdict: 需修補後派工**。無根本缺陷需重作 SPEC；**BLOCKING 清單（修 SPEC 後可進 TODO）**：
1. 統一 O5 Bonferroni 門檻（P1-01）
2. Task 3.1 補 `symbol`／`timeframe`＋validator／§G oracle（P1-02）
3. §V 補 shuffle-S、symbol-hash mutation（P2-01）

非 BLOCKING：P2-02 cache-hit refilter 驗收可併入 Task 4.1 驗證清單。

---

## Verdict：需修補後派工

SPEC 統計核心、OOS 揭露（D3′）、分批與 §G oracle 整體可證偽且回應偵察收斂；**3 項 MAJOR 修補**（O5 矛盾、C4 symbol/timeframe、§V mutation 缺口）應在 TODO 生成前寫回 SPEC，無需重作架構。

---

ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → TEMPLATE PASS；`deny_factor_in_ok_oos` `contracts.py:2005-2012`；`test_r6` `test_ichc_contract_sync.py:43-62`；O4 探針 `/tmp/composer-gap2-specadv-r1/o4_probe.txt`；`grep marginal_ic tests/` → 0  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS；O4 合成探針 3 trials；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-composer.md --family composer`（收尾）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 SPEC 審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼；建議修 SPEC 契約欄位與 O5 門檻）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-specadv-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap2-specadv-r1`；保留 `/tmp/claude-501`  
STATUS: DONE
