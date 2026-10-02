# FF-STAT 第 6 批 諮詢 r1 — COMPOSER

task-id: 20260926-FFSTAT-B6-CONSULT-R1  
family: COMPOSER  
findings-round: R1  
brief-kind: consult  
brief: handoffs/20261002-FFSTAT-B6-CONSULT-R1-BRIEF.md  
template: templates/COMMITTEE_FINDING_TEMPLATE.md

本輪唯讀。讀碼＋收據 log＋`/tmp/ffstat_b6_probe/mask_probe.py` 秒級探針（未跑生成型 node）。

## §0 前提對照

| 項目 | 判定 |
|---|---|
| brief ① center mutant DID NOT RAISE | **與** `handoffs/run_receipts/20261002-ffstat-small-mr-s2.log` **一致** |
| brief ② 236 行 informational、`fill_rate full=1.000 trunc=0.700` | **與 log 一致**（`grep -c` → 236） |
| brief ③ 第 1 段基線 0 行 informational | **與** `20261002-ffstat-small-mr-s1.log` **一致**（0 匹配） |
| brief ④ 其餘 mutant 紅、尾擾動 fracdiff 耦合僅值 gate | **讀碼與 brief 一致**（`run_control_fracdiff_maxlag_len_coupling` + `tail_perturb` 路徑） |

---

## COMPOSER-R1-P0-01

**斷言**: 主 MR 之 `_assert_nan_mask_layered` 在比較窗 `[warmup:n_trunc)` 內，當 **full 全有限而 trunc 尾端因置中窗缺未來 bar 而出現 NaN** 時，因 `fill_rate_right < 0.95` 僅印 informational；`_assert_values_both_non_nan_close` 又只比 both-non-NaN ⇒ **`run_control_numba_rolling_center_true` 可全綠**，屬未來洩漏漏測（與使用者「絕對修掉不得列殘留」衝突）。

**碼證**: `tests/feature_engineering/ff_truncation_mr_helpers.py:797-821` 僅在 **兩側** fill≥0.95 時 mask 不等才 `AssertionError`；`:771-794` both-non-NaN 值比對。`run_control_numba_rolling_center_true` `:1573-1593` 以 `min_periods=window` 置中 mean 覆寫 L3 mean 槽。收據：`20261002-ffstat-small-mr-s2.log` 末段 `test_small_mutation_numba_rolling_center_true_fails` **未** `pytest.raises`。秒級探針（2026-10-02）：`venv/bin/python /tmp/ffstat_b6_probe/mask_probe.py` → `fill_l=1.000 fill_r=0.700`、`mask_layered_raised=False values_gate_raised=False`、`PROBE_OK`。CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:797  
MUTATION: `pytest tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py::test_small_mutation_numba_rolling_center_true_fails -q`（已實跑於 s2 log）⇒ 預期 **綠**（現況）；修正 gate 後同命令須 **紅** 且失敗訊息經 `_assert_nan_mask_layered` 或新定向規則、**不**經 coverage/sampling 守衛。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b

**類別**: code-contract

正文：**修法（單點收緊 gate，非再加一層機制）**：在 `_assert_nan_mask_layered`（或等價唯一呼叫點 `:980-986`）對比較窗 segment 增加 **定向失敗**：任一索引滿足 `np.isfinite(segment_full) & np.isnan(segment_trunc)` 即 `AssertionError`（trunc 較短時「full 看見未來、trunc 同索引無值」之 look-ahead 簽名）。保留 B2 對 **雙側皆低 fill** 之 bilateral mask 不對稱僅 informational（列數依賴）。**可行性**：探針已證現規則不紅、定向規則在 20×6 合成窗可紅；實作後須附 unit 探針於 `tests/feature_engineering/`（秒級）＋原 mutant 必紅。**重跑範圍**：縮小版全檔＋日後 RM-FULLSCALE 13 項（同一 helper）；第 1 段基線 s1 log 0 informational ⇒ **定向規則下預期仍綠**（待 impl 後實跑確認）。

---

## COMPOSER-R1-P1-01

**斷言**: B2 reconcile（`handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md` §二-3）之「低 fill 僅 informational」**仍成立**於 near-empty／雙側稀疏 churn，**不**涵蓋「單側仍高密度、trunc 尾端單向 NaN」——後者屬截斷因果 MR 必抓之洩漏型，不能以原條款豁免。

**碼證**: Reconcile §二-3 明文低 fill「列數依賴良性」。現況 mutant 欄 `fill_rate full=1.000 trunc=0.700`（log）——trunc 側 **非** near-empty，而是 W13 置中窗在 trunc 末端缺 6 根未來（`(13-1)//2`）所致，與 dead_drop 稀疏良性案例不同。CODE-ANCHOR: handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md:25  
MUTATION: 若僅把 `HIGH_FILL_RATE_THRESHOLD` 從 0.95 降到 0.65 而不加定向規則 ⇒ 仍可能漏「雙側 0.9 fill 但 mask 不對稱」；若改為比較窗 mask 全等（不論 fill）⇒ 須用 s1 基線與多週期基線（進行中）驗證 assumed ⑤。

**來源摘要**: handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md#58798e0b568c

**類別**: doc-sync

正文：**Q1 結論**：不建議無條件「不論 fill_rate mask 全等」作唯一方案；**最低限度**採 P0-01 定向規則；若多週期基線出現 **雙側低 fill** 合法不對稱，再保留現分層作 **補充** 而非取代定向規則。**修法可行性**：定向規則與 B2 稀疏豁免可並存（先檢定向失敗，再走現 informational 分支）。

---

## COMPOSER-R1-P2-01

**斷言**: `POST_WARMUP_BARS=20`（`:41`）使置中窗 W13 之尾端 NaN 佔比較窗 6/20，放大 values gate 盲區，但 **根因仍是 gate 規則**；加長至 ≥`2×max(L3窗)`（例 26–40）可提高 both-non-NaN 覆蓋率，**不能替代** P0-01，且每對生成僅增加 `window_bars` 內之 kline 切片（`_required_window_bars` `:146-155`），成本為 **O(加長根數×既有欄寬)**，非 13 項全量重設。

**碼證**: `POST_WARMUP_BARS=20`；縮小版 L3 窗含 13（`test_ff_fullchain_truncation_small_mr.py:6`）。加長 `min_post_warmup` 只影響 `_required_window_bars` 返回值。CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:41  
MUTATION: 僅把 `POST_WARMUP_BARS` 改 40 而不改 mask 規則 ⇒ center mutant 仍可能僅 informational（trunc fill 仍可 <0.95）。

**來源摘要**: handoffs/20261002-FFSTAT-B6-CONSULT-R1-BRIEF.md#333afa150740

**類別**: other

正文：**Q3**：可選加長比較窗作 **輔助**；優先序 P0-01 > 可選加長。

---

## COMPOSER-R1-P2-02

**斷言**: L3 center mutant 以 `min_periods=window`（`:1587`）合理，對應生產禁用之 `center=True`+完整窗；另增 `min_periods=1` 變體 **非本輪必須**，因尾端以部分未來算出有限值時 values gate 通常仍會紅，且會混淆「嚴格因果窗」與「寬鬆 pandas 預設」兩種失敗模式。

**碼證**: `series.rolling(window, center=True, min_periods=window).mean()`。其餘 mutant（winsor、L4、fracdiff）在 s2 段已紅。CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:1587  
MUTATION: 改 `min_periods=1` 後若 values 在 trunc 尾端 both-non-NaN 仍可能數值接近 ⇒ 鑑別力不優於現 mutant；建議 **gate 修復後**再評估是否需第二 mutant。

**來源摘要**: handoffs/run_receipts/20261002-ffstat-small-mr-s2.log#ff5498e42586

**類別**: other

正文：**Q4**：維持現 `min_periods=window` 為 P0 探針；`min_periods=1` 列為可選增補（impl 票），非 consult 阻塞項。

---

## COMPOSER-R1-P2-03

**斷言**: `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails`（`:100-101`）與 `…_truncation_fails`／`…_parallel_fails` 測同一 `run_control_fracdiff_maxlag_len_coupling` seam；尾擾動版在 codec 既有 xfail 基線下 **僅能在值 gate 區分**，鑑別力重疊 ⇒ 應 **撤除尾擾動版**（保留 truncation＋parallel），勿為 SPEC「不得新增 xfail」再疊 strict xfail 綁 codec。

**碼證**: `ff_truncation_mr_helpers.py:1701-1703` 尾擾動 fracdiff 基線 codec 問題說明；`run_control_fracdiff_maxlag_len_coupling` `:1710-1744` `tail_perturb` 收緊 `allowed_gates` 為 `_FRACDIFF_PRE_VALUES_GATES`。small 檔 `:100-105` 三測試。CODE-ANCHOR: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py:100  
MUTATION: 刪除 `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails` 後跑縮小版 mutant 子集 ⇒ 仍應紅 truncation＋parallel；全鏈 13 項對應項同步檢視（若存在 tail 版）。

**來源摘要**: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#1fe4a24c8a23

**類別**: code-contract

正文：**Q5**：撤除尾擾動耦合項；`test_small_fracdiff_tail_perturbation_invariant` 維持既有 strict xfail（codec），與 mutant 鑑別無關。

---

## COMPOSER-R1-P2-04

**斷言**: assumed ⑤（比較窗內 full 有限／trunc NaN 僅來自洩漏或非決定論）在 **單週期無 mutant 基線** 下目前 **未被否證**（s1：0 informational）；多週期正常基線主委進行中——若出現 **雙側低 fill** 之粗週期對齊尾端 NaN，應歸入 B2 稀疏豁免而非推翻定向規則。

**碼證**: `grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-s1.log` → 0。brief assumed／否證觀測。`_COARSE_TF_TAG`（`:64`）與 multi-TF align 控制見 `run_control_align_*`（`:1668+`）。CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:64  
MUTATION: 多週期基線若出現 `full=0.4 trunc=0.35` 級 bilateral 不對稱且無 full-finite/trunc-NaN 格 ⇒ 支持保留稀疏 informational；若出現 `full=1.0 trunc=0.7` 級 ⇒ 與 center 案例同型，定向規則應抓。

**來源摘要**: handoffs/run_receipts/20261002-ffstat-small-mr-s1.log#ff5498e42586

**類別**: other

正文：**Q2**：P0-01 後縮小版基線預期不假紅（s1 證據）；全設定 13 項 **未驗**（RM-FULLSCALE）。**Q6**：多週期第 3–6 段 **可先跑基線** 取 informational 計數驗 ⑤，**不必**等 gate 修復才跑；但 **center mutant 驗收** 須 gate 修復後重跑第 2 段（否則持續假綠）。

---

### 必答（成對）

**(1a) Q1–Q6**  
- **Q1**：收緊為 P0-01 定向 mask 失敗＋保留稀疏 bilateral informational；原 B2 分層理由對稀疏仍成立、對 trunc 尾端高密度單向 NaN 不成立。  
- **Q2**：s1 基線 0 informational ⇒ 定向規則下假紅風險低；13 項全設定未跑。  
- **Q3**：可加長 `POST_WARMUP_BARS` 輔助，非替代；成本＝每對多幾十根 kline 窗。  
- **Q4**：維持 `min_periods=window`；`min_periods=1` 可選後補。  
- **Q5**：撤 `…_tail_fails` 耦合測試。  
- **Q6**：多週期基線可先跑；mutant 段須 gate 修後重跑。

**(1b)** `ff_truncation_mr_helpers.py:797-821,771-794`；s1/s2 log；`/tmp/ffstat_b6_probe/mask_probe.py` 實跑。

**(2a) assumed ⑤**  
- 單週期無 mutant：**暫成立**（無反例）。  
- 多週期：**待定**（主委跑完前不宣稱）。

**(2b)** s1 零 informational；brief 否證觀測；B2 §二-3 稀疏例外語意。

**(3a) 共識修法與重跑**  
1. 實作 P0-01 定向 mask 規則＋秒級 unit 探針。  
2. 撤除 `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails`（及全鏈對應項若有）。  
3. 重跑：縮小版全檔（尤其 center mutant）；可選加長 `POST_WARMUP_BARS` 後再跑一輪。  
4. RM-FULLSCALE 13 項於換機與 gate 合併後跑。

**(3b) 分歧**  
- 無三家輸入；若他族主張「比較窗 mask 全等、無豁免」，以多週期 s3+ log 計數仲裁（見 P2-04）。

### 驗證留痕

```bash
grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-s1.log
grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-s2.log
/Users/louis/Desktop/quantitative_trading_system/venv/bin/python /tmp/ffstat_b6_probe/mask_probe.py 2>&1 | tail -3
git status --short -- momentum api frontend tests templates config | head -5
```

s1→0、s2→236（2026-10-02）；probe→`PROBE_OK`；git status 與開跑前同型（僅既有 pycache/golden 等）。

ASSUMPTIONS_VERIFIED: brief fact ①–④ 與 log／讀碼一致。  
TESTS_RUN: `/tmp/ffstat_b6_probe/mask_probe.py` → PROBE_OK；未跑 pytest 生成。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT: handoffs/20260926-ffstat-b6-consult-r1-composer.md

VERDICT: proceed
BLOCKED-BY:
CLOSED:
