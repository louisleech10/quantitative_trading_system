# GAP-1 G1-R11 修補 code review（R21）— COMPOSER

**task-id**: `20260818-GAP1-X-REVIEW-R21` | **family**: composer | **brief**: `handoffs/20260818-gap1-r11-review-BRIEF.md`
**審查標的**: commit `16e5971c`（`ptp==0` 常數退化判定；consult r20 O1 落地）
**禁改碼／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → **281 passed** rc=0
- golden 三案例＋G1-R11 專測：`test_golden_noise_band`／`test_golden_alpha_detectable`／`test_golden_alpha_undetectable`／`test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe`／`test_vectorized_sharpe_matches_compute_sharpe` → **5 passed** rc=0
- 段 B 邊界探針（本地）：`-0.0/+0.0` 混合 ⇒ `ptp=0` `std=0` ⇒ `degenerate_returns`；`[0.5,0.5]` ⇒ 退化；含 `inf` ⇒ `isfinite` 先擋、未觸 `ptp`；`ptp==0` 與 `all(values==values[0])` 於 `80×0.01`／`zeros`／ULP 混合列結果一致
- §V-16 探針：唯讀 receipt `handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log` → baseline 278 passed 12.24s；§V-16 拿掉 `ptp` ⇒ 1 failed rc=1；21 條全轉紅；post-restore 278 passed 12.08s；總 rc=0

---

## Verdict：可合併

段 A 四項與 consult r20 O1 一致；段 B 五項攻擊未發現回歸或數值風險；段 C 探針 receipt 對應 consult 建議。實作忠於「`std==0 or not finite or ptp==0`、無 ε、兩路徑逐位等價」之主委方案。

**BLOCKING**：0。**MAJOR**：0。**MINOR**：0。

---

## 段 A — 是否忠於 consult 結論

| # | 結論 | 要點 |
|---|------|------|
| **A①** | **符合** | `sharpe.py:92` 與 `pbo.py:152` 退化條件為 `std == 0.0 or not np.isfinite(std) or float(np.ptp(values)) == 0.0`；皆為精確 `== 0.0`，無相對容差／ε 常數。`float()` 包裝與 `std` 分支對稱，語意不變。 |
| **A②** | **符合** | 兩處判定式結構相同（先 `n<2`／`isfinite`，再 `std`＋`ptp`）。`test_vectorized_sharpe_matches_compute_sharpe` 對 9 欄以 `got[j] == ref` 逐位鎖定（含欄 7 `0.01`⇒NaN、欄 8 微擾⇒巨大有限）→ 本輪 **passed**。 |
| **A③** | **符合** | CODEX-R20-P2-01 scope 已寫入：`sharpe.py:89-91` 註解「輸入元素**位元全等**…不保證跨異源浮點表達式之數學相等」；`test_sharpe.py:106-107` docstring 同旨；`test_pbo.py:126` 欄 7 註解。`pbo._sharpe_pp_1d` docstring L145 仍只列 `std==0`，但 L152 行內註解已補「常數＝位元全等」，行為由 `==` 測試鎖住——文檔輕微不完整，不構成實作偏差。 |
| **A④** | **符合** | golden 三案例（noise band／alpha_detectable／alpha_undetectable）本輪全 **passed**；與 consult grok P2-02「golden 不受 ptp 影響」一致。 |

---

## 段 B — 攻（邊界／效能／替代寫法）

| # | 結論 | 要點 |
|---|------|------|
| **B①** | **合理** | `[0.0, -0.0, 0.0, -0.0]`：`ptp=0.0`、`std(ddof=1)=0.0`、`all_eq=True` ⇒ `compute_sharpe` → `status=not_computed` `reason=degenerate_returns`。IEEE 下 `-0.0==+0.0`，與「常數序列」語意一致。 |
| **B②** | **無回歸** | `[0.5, 0.5]`（len=2）：`std=0`、`ptp=0` ⇒ 退化；既有 `std==0` 已涵蓋，`ptp` 為冗餘保險、不改行為。 |
| **B③** | **順序正確** | `sharpe.py:85-86`／`pbo.py:149-150` 先 `not np.all(np.isfinite(values))` ⇒ `_degenerate`／NaN；含 `inf` 時**不會**執行到 `np.ptp`。本輪 `[0.01, 0.02, inf]` 探針確認。 |
| **B④** | **可忽略** | receipt baseline **278 passed in 12.24s**（HANDOFF 前次 ~11s）；+~1s 於 924 path×50 候選之 PBO 路徑可接受，遠低於 scipy 矩計算若逐欄 `compute_sharpe` 之 ~30s／案例（`pbo.py:161-162` 註解）。brief assumed「ptp 開銷可忽略」→ **本輪坐實**。 |
| **B⑤** | **維持 `ptp`** | 有限值域上 `float(np.ptp(values))==0.0` ⇔ `np.all(values==values[0])`（本輪 `80×0.01`／`zeros`／ULP 混合列皆一致）。codex 建議 `all_eq` 更直白，但 `ptp` 已落地、探針 §V-16 已鎖、兩者語意等價；換寫法無實質收益，僅風格差異。 |

---

## 段 C — 探針（唯讀 receipt）

§V-16 mutant 精確對應 consult O1：移除 `float(np.ptp(values)) == 0.0` 後 `test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe` **1 failed** rc=1，其餘 20 條仍轉紅；baseline／post-restore 全綠。與「拿掉 ptp 判定 ⇒ 80×0.01 回巨大 SR」之設計意圖一致。**本家族未自建探針**（brief 互斥鎖；codex 已跑）。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| 281 passed | fact-verified | **覆核 rc=0** |
| 探針 21 條全 rc=1、baseline/post-restore 綠 | fact-verified | **覆核 receipt** |
| `strategy_wiring_check.sh` rc=0 | fact-verified | brief 標記；本輪未重跑（與 R11 無直接耦合） |
| `np.ptp` 效能可忽略 | assumed→**verified** | 段 B④；+~1s／278 tests |
| `ptp==0` 與 `all_eq` 有限值域等價 | assumed→**verified** | 段 B⑤ 探針 |

---

## Findings（canonical）

## COMPOSER-R21-P3-00

**斷言**: 本輪逐項核對段 A①–④、段 B①–⑤、段 C 探針 receipt 與 §0 前提後，修補忠於 consult r20 O1、無需額外 blocking／major finding。

**碼證**: `sharpe.py:88-93` 退化三條件無 ε；`pbo.py:149-153` 同構；`test_sharpe.py:105-117` 80×0.01⇒NaN＋微擾仍巨大有限；`test_pbo.py:120-138` 欄 7/8 與 `==` 鎖；receipt §V-16 1 failed；golden 三案例 pytest 全綠。RECHECK：`pytest tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_noise_band tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_detectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_undetectable tests/momentum/Analysis/strategy_validation/test_sharpe.py::test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe tests/momentum/Analysis/strategy_validation/test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe -q`

**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#11fda76fba6b

[P3] 信心度=High。核對依據＝段 A–C 表＋本輪邊界探針；`_sharpe_pp_1d` docstring L145 未列 `ptp` 為輕微文檔缺口（L152 行內註解已補），不升格 finding。

---

## §1 必查（11 類摘要）

1. 矛盾：無。2. 漏項：無。3. 不可測：驗收可執行（pytest＋§V-16）。4. quant 假設：無容差洩漏；ULP 邊界已文件化。5–11：無阻擋項。

---

ASSUMPTIONS_VERIFIED: sharpe.py/pbo.py 退化條件逐字比對；golden+G1-R11 五測；段 B 邊界探針（±0、inf、ptp vs all_eq）；receipt §V-16  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → 281 passed rc=0；golden+專測 5 passed rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 review）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼；審查標的已讓 80×0.01 由巨大 SR→NaN，屬 G1-R11 意圖）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap1-r11-review-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap1-r20`、`/tmp/grok-gap1-r21`；保留 `/tmp/claude-501`  
STATUS: DONE
