# GAP-1 G1-R11 修補 code review（R21）— GROK

**task-id**: `20260818-GAP1-X-REVIEW-R21` | **family**: grok | **brief**: `handoffs/20260818-gap1-r11-review-BRIEF.md`
**審查標的**: commit `16e5971c`（`ptp==0` 常數退化；consult r20 O1）
**禁改碼／禁 commit／禁 push**（本輪唯讀）

**VERIFY（本輪實跑）**:
- 專測＋golden：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_sharpe.py::test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe tests/momentum/Analysis/strategy_validation/test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_noise_band tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_detectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_undetectable -q` → **5 passed** rc=0
- 段 A② 逐欄等價探針（同 fixture 結構）：9 欄 `got == ref` 全 True（欄 7 雙 NaN；欄 8 雙巨大有限且位元相同）
- 段 B 邊界：`-0/+0` 混合 ⇒ degenerate；`[0.5,0.5]` ⇒ degenerate；含 `inf` ⇒ 先被 `isfinite` 擋；`ptp==0` ⇔ `all_eq` 於 6 組有限案例一致
- 段 B④：924×50 欄、len=80 之逐欄 `np.ptp` 迴圈 ≈0.11s；向量化 `np.ptp(...,axis=0)` ≈0.002s（相對既有 per-col std／mean 可忽略）
- §V-16：唯讀 receipt `handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log`（brief：探針互斥鎖，本家族不重跑）→ §V-16 1 FAILED rc=1；21／21 轉紅；baseline／post-restore 278 passed；總 rc=0

---

## Verdict：可合併

段 A①–④ 忠於 consult r20 O1；段 B①–⑤ 攻擊未揭回歸或需改謂詞之事實；段 C §V-16 mutant 對應 O1。無 ε／相對容差；兩路徑判定式同構且測試以 `==` 鎖住。

**BLOCKING**：0。**MAJOR**：0。**MINOR**：0。

---

## 段 A — 是否忠於 consult 結論

| # | 結論 | 要點 |
|---|------|------|
| **A①** | **符合** | `sharpe.py:92` 與 `pbo.py:152` 皆為 `std == 0.0 or not np.isfinite(std) or float(np.ptp(values)) == 0.0`。條件列無 `atol`／`rtol`／`eps`／`1e-` 容差字面；`float(...)` 僅將 numpy 標量收成 Python float，不改變 `== 0.0` 精確比對。 |
| **A②** | **符合** | 兩函式同序：`n<2`／`isfinite` → `std` → `ptp`。本輪對 9 欄重跑 `compute_sharpe(...).value_per_period` vs `_sharpe_pp_1d`：全數 `match=True`（含 NaN 對 NaN）。`test_vectorized_sharpe_matches_compute_sharpe` 以 `got[j] == ref` 鎖住 → **passed**。 |
| **A③** | **符合** | CODEX-R20-P2-01 scope 已入 `sharpe.py:89-91` 註解（「位元全等…不保證跨異源浮點表達式之數學相等」）與 `test_sharpe.py` 新測 docstring／`test_pbo.py` 欄 7 註解。觀察（不升格 finding）：`compute_sharpe` Returns 列仍只寫 `std(ddof=1)==0`；`_sharpe_pp_1d` docstring L145 同漏 `ptp`——但 brief A③ 準據為「註解／測試 docstring」，已滿足；行為由 `==` 測試與行內註解鎖住。 |
| **A④** | **符合** | golden 三案例本輪全綠；與 consult GROK-R20-P2-02「golden 不受 ptp 影響」一致。 |

---

## 段 B — 攻

| # | 結論 | 要點 |
|---|------|------|
| **B①** | **合理** | `[-0.0, 0.0, -0.0, 0.0]`：`ptp=0.0`、`std=0.0`、`all_eq=True`（IEEE `-0.0==+0.0`），bits 雖異號零仍判定常數 ⇒ `status=not_computed`／`degenerate_returns`。與「編碼值相等（比較語意）」一致，非漏判。 |
| **B②** | **無回歸** | `[0.5, 0.5]`：`std==0` 已涵蓋；`ptp==0` 冗餘保險，行為不變。 |
| **B③** | **順序正確** | `sharpe.py:85-86`／`pbo.py:149-150` 先擋非有限；含 `inf` 之序列本輪得 `degenerate_returns`，不會執行到 `np.ptp`。 |
| **B④** | **可忽略（assumed→verified）** | 既有路徑已是 Python 逐欄 `_sharpe_pp_1d`；每欄多一次 len≈80 的 `ptp` 相對 `std`／`mean` 可忽略。本輪 46200 欄迴圈 ptp≈0.11s、向量化≈0.002s。receipt baseline 12.24s vs 歷史 ~11s 屬秒級噪音，遠低於若改回逐欄 `compute_sharpe`（含 scipy 矩）之 ~30s／案例。 |
| **B⑤** | **維持 `ptp`（assumed 等價→verified）** | 有限、已過 `isfinite` 閘後：`ptp==0` ⇔ `all(values==values[0])`（本輪 6 案例含 `-0/+0`、ULP 混合、微擾皆 `equal_predicates=True`）。`all_eq` 較直白（codex 建議），但語意等價、§V-16 已鎖 `ptp` 字面；換寫法無數值收益，僅風格——**不要求改**。 |

---

## 段 C — 探針

§V-16 mutant 字面＝拿掉 `or float(np.ptp(values)) == 0.0`（與 live `sharpe.py:92` 字串對齊），對應 consult O1「併判 ptp」。receipt：該條 **1 FAILED＝斷言失敗**（即 `test_non_binary_exact_constant_series_is_degenerate_not_huge_sharpe` 轉紅），非 collection error；全套 21 條皆 rc=1；baseline／post-restore 綠。本家族依 brief **未**重跑互斥探針；自建邊界／等價探針已於上列 VERIFY（無長跑、已結束）。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| 281 passed（全套 strategy_validation＋api 橋） | fact-verified | 本輪未重跑全套；專測＋golden **5 passed** 覆核核心路徑 |
| 探針 21 條全 rc=1、baseline/post-restore 綠 | fact-verified | **覆核 receipt**（未重跑探針） |
| `strategy_wiring_check.sh` rc=0 | fact-verified | 與本修補無直接耦合；本輪未重跑 |
| `np.ptp` 效能可忽略 | assumed→**verified** | 段 B④ |
| `ptp==0` 與 `all_eq` 有限值域等價 | assumed→**verified** | 段 B⑤（含 `-0/+0`） |

---

## Findings（canonical）

## GROK-R21-P3-00

**斷言**: 本輪逐項核對後無 finding——段 A①–④ 忠於 consult r20 O1（精確 `std==0 or not finite or ptp==0`、兩路徑逐位等價、編碼值相等 scope 已入註解／測試 docstring、golden 三案例綠）；段 B①–⑤ 與段 C §V-16 receipt 未揭須修補之回歸或容差漏洞。

**碼證**: `sharpe.py:85-93`／`pbo.py:149-153` 判定同構且無 ε；`test_sharpe.py:105-117` 80×0.01⇒NaN＋微擾仍巨大有限；`test_pbo.py:120-138` 欄 7 NaN／欄 8 巨大有限＋`==` 鎖；本輪 pytest 5 passed rc=0；receipt §V-16 → 1 FAILED；B 探針 `-0/+0`／`[0.5,0.5]`／`inf` 順序／ptp↔all_eq 等價見上。RECHECK：同 VERIFY 專測命令＋讀 `handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log` 之 §V-16 行。

**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#11fda76fba6b

[P3] 信心度=High。核對依據＝段 A–C＋本輪邊界／等價探針；`compute_sharpe` Returns 與 `_sharpe_pp_1d` docstring 未列 `ptp` 為文檔輕微缺口（註解＋測試 docstring 已披露 scope），不升格 finding。

---

## §1 必查（11 類摘要）

1. 矛盾：無（與 consult O1 一致）。2. 漏項：無（兩路徑＋測試＋§V-16 齊）。3. 不可測：無（pytest＋mutation 可證偽）。4. quant：無相對容差；近常數巨大 SR 保留。5. 過度工程：無。6. OOM：無新增。7. Cache：無。8. API／型別：無跨域。9. 測試：新測＋翻轉欄 7＋mutation 到位。10. Agent 可執行：N/A（已落地修補）。11. 短命工：無。

---

ASSUMPTIONS_VERIFIED: A①–④ 碼與測試；B①–⑤ 邊界／效能／等價探針；§V-16 receipt；CODEX-R20-P2-01 scope 在註解＋測試 docstring
TESTS_RUN: `venv/bin/python -m pytest …test_non_binary… …test_vectorized_sharpe… …test_golden_{noise_band,alpha_detectable,alpha_undetectable} -q` → 5 passed rc=0；本地等價／邊界探針見 VERIFY；mutation 唯讀 receipt（未重跑）
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀 review；未改產品碼）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；標的 commit 之數值影響已由 consult／測試覆蓋）
OUTPUT_ARTIFACT: handoffs/20260818-gap1-r11-review-grok.md
TMP_CLEANUP: 刪除本輪 `/tmp/grok-gap1-r21`；保留 `/tmp/claude-501`
STATUS: DONE
