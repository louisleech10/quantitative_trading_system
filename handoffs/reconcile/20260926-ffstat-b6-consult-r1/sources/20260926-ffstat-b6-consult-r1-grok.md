# FF-STAT 第 6 批 諮詢 r1 — grok

task-id: 20260926-FFSTAT-B6-CONSULT-R1
family: grok
findings-round: R1
brief-kind: consult
brief: handoffs/20261002-FFSTAT-B6-CONSULT-R1-BRIEF.md
template: templates/COMMITTEE_FINDING_TEMPLATE.md
round-id: 88499789-aa56-4222-a4ac-ebf4dd6f8f92

本輪唯讀。未改碼、未改文檔、未 git 寫入。未跑生成型 node。秒級探針在 `/tmp/ffstat_b6_maskp`（先 `isolate()`／`isolate_dstar_cache()`，再 import 真實 helpers）。指令列與暫存路徑無家族名。

## §0 前提宣告

fact-verified: ① 縮小版第 2 段 `test_small_mutation_numba_rolling_center_true_fails` DID NOT RAISE → `handoffs/run_receipts/20261002-ffstat-small-mr-s2.log` `Failed: DID NOT RAISE` at helpers.py:1520。
fact-verified: ② 該 mutant 下 236 行 `NaN mask informational`、W13 `full=1.000 trunc=0.700` → `grep -c 'NaN mask informational'` s2＝236（155× trunc=0.700、81× trunc=0.900）。
fact-verified: ③ 第 1 段正常基線 0 行 informational → `grep -c` s1＝0。
fact-verified: ④ 同段其餘 mutant 被抓到；尾擾動 fracdiff 長度耦合只於值 gate 失敗而被拒收 → s1 `失敗不由允許之 gate 拋出`，允許 columns／d_star，路徑含 `_assert_values_gate`；Max abs 2.901256e-05、Max rel 0.00042215。
assumed: ⑤ 因果管線比較窗 [warmup, n_trunc) 內「一側有限、一側 NaN」只可能來自洩漏或非決定論（見必答 2a／2b；單週期 s1 未否證，多週期待第 3 段）。

---

## 必答（成對）

### (1a) Q1–Q6 結論

**Q1**：應把現有 `_assert_nan_mask_layered` 收成比較窗 `[warmup, n_trunc)` 內 **mask 全等**（不論 fill_rate）。這是改既有 gate，不是再加一層。最低可落地、且已能殺死本輪存活 mutant 的寫法：`full` 有限且 `trunc` NaN 一律失敗。B2 分層原由（L7 dead_drop 造成 near-empty／單側欄／列數依賴）在現行 MR 不成立：`_mr_nan_strategy` 關閉 `l7_dead_feature_drop`；值 gate 已走欄交集（單側欄根本不比）；同 mask 的稀疏欄在 exact 下仍通過（探針 `equal_sparse` fill=0.25）。分層現在是 mask-only 洩漏的洞。

**Q2**：縮小版第 1 段基線 7 項 log 0 行 informational ⇒ 比較窗沒有 mask 不對稱可被 promote，收緊不會把那些基線假紅。全設定 13 項本機不可跑，未驗。用加長 `POST_WARMUP_BARS` 把 fill 拉到 ≥0.95 當修法：W13 需 N≥120、W21≥200、W55≥540、W233≥2320。生產 L3 窗含 W3，N=20 時 fill=0.95，**現規則會抓**；縮小版 L3 只留 (5, 13)，所以本 mutant 在小窗設定下存活。加長比較窗不是本洞的修法。

**Q3**：20 相對 W13 確實短（尾 6／20 被置中窗污染），但加長是輔助、成本落在 full＋trunc 各多生成 N 根。1h 探針窗 3594 根、隱含 warmup 3564；+100 根約 2.8%。用 0.95 規則去抓 W233 要再加 2320 根，幾乎再造一段窗。主修法是 gate。

**Q4**：`min_periods=window` 是正確的 mask-only 洩漏 mutant（正是現在存活的那一種）。`min_periods=1` 是另一類：尾端用部分未來算出有限值，mask 仍全等，值 gate 已抓得到（探針 `w13_mp_1`：`values_both` 紅，`rel_err=1.034e-01` at index 19；layered／exact／directional 皆不紅）。可在 mask 收緊後當互補 mutant 評估，不是本輪必須，也不是修法。

**Q5**：撤除 `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails`。截斷版與並行版已打同一 seam。尾擾動版只在值 gate 現形，與 codec 既有 xfail 基線不可分；SPEC Task 4.2 不得新增 skip／xfail。codec epic 之後若要再加，另票。

**Q6**：讓正在跑的多週期第 3 段基線跑完，用 informational 計數當 ⑤ 的否證觀測。第 4–6 段 mutant **等 mask gate 收緊後再跑**。收緊後必重跑 s2 center mutant（須改紅）。s1 0 informational，不必為本洞重跑第 1 段基線。多週期 mutant 同樣在 gate 收緊後跑。

### (1b) 依據

- helpers `_assert_nan_mask_layered` L797–821：mask 不等且兩側 fill 皆 ≥0.95 才 raise；否則 print informational。呼叫點 `_assert_values_gate_main` L980–986，隨後 `_assert_values_both_non_nan_close` 只比 both-non-NaN。
- s2 log：seam 被呼叫（`assert calls[0] > 0` 已過），`_expect_causal_gate_failure` 在 L1520 `check()` DID NOT RAISE；236 informational。
- 秒級探針 `TMPDIR=/tmp/ffstat_b6_maskp PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat_b6_maskp/probe.py` → 寫 `/tmp/ffstat_b6_maskp/probe_result.json` rc=0。W13 `min_periods=window`：layered／values_both 不紅，exact／directional 紅。`_assert_values_gate_main` 三層小樹 W13 洩漏：DID NOT RAISE。短序列探針 fill 0.70／0.40（置中窗亦 NaN 序列頭）；實跑 s2 長序列 fill 1.000／0.700，洞的方向相同。
- s1 log 0 informational；尾擾動耦合：允許 gate 只有 columns／d\*，實際 `_assert_values_gate` atol 失敗。
- fracdiff `_assert_values_gate` L1035–1037 已 exact mask（探針 `values_gate_atol_tail_nan` 紅 `fracdiff NaN mask`）。warmup exact mask 只蓋 `[0:warmup)`（探針 `warmup_ignores_tail` 不紅）。align oracle L1307–1315 用 `np.isclose(..., equal_nan=True)`，不走分層。

### (2a) assumed ⑤ 是否成立

單週期無 mutant：**成立**（s1 比較窗 0 行 mask 不對稱）。多週期：**待第 3 段基線**，本輪不宣稱。⑤ 的內容是「比較窗內一側有限、一側 NaN 只可能是洩漏或非決定論」——這正好是 exact mask 所禁止的狀態。codec 不會把一側有限變成另一側 NaN（尾擾動 fracdiff 的既有問題是 **兩側皆有限、值差 atol**）。

### (2b) 依據

- s1 `grep -c 'NaN mask informational'` = 0。
- `_mr_nan_strategy` L167–169 關閉 dead_drop。
- 探針 `equal_sparse`：兩側同一 25% mask，exact／layered／directional 皆不紅。
- 探針 `reverse_trunc_finite`：layered 不紅、directional 不紅、exact 紅——⑤ 把這個也算洩漏／非決定論。
- 多週期粗週期 as-of 若在比較窗製造 mask 不對稱，會以 informational 出現在第 3 段；本輪未跑生成，不預先當已發生。

### (3a) 修法與須重跑範圍

1. **改既有** `_assert_nan_mask_layered`：比較窗 mask 不等即 `AssertionError`（可保留 print 再 raise）。與 fracdiff `_assert_values_gate` 的 exact mask 對齊。不得新加平行 gate 層、不得放寬 rtol／atol、不得把 mutant 移出分母。
2. 若主委要先落地、等 s3 再決定是否全等：同一函式內先做定向 `full` 有限 ∧ `trunc` NaN 失敗（已能殺死本 mutant），再視 s3 決定是否刪 fill-rate skip。
3. 撤 `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails`（既有全鏈檔若有對應 tail 耦合控制一併撤）。`test_small_fracdiff_tail_perturbation_invariant` 維持既有 codec strict xfail。
4. 維持 `min_periods=window` 之 L3 center mutant。
5. **重跑**：gate 改後必跑 `test_small_mutation_numba_rolling_center_true_fails`（須紅，失敗須來自 `_assert_nan_mask_layered` 或其所屬 `_assert_values_gate_main`，不得靠 coverage／sampling）。縮小版其餘已紅 mutant 不必為本洞重跑。第 3 段基線可繼續跑完取 informational。第 4–6 段等 gate 收緊後跑。13 項全設定仍屬 RM-FULLSCALE。
6. 秒級：在 `tests/feature_engineering/` 加對 `_assert_nan_mask_layered` 的小陣列用例（W13 尾 NaN 必紅；同 mask 稀疏必綠；高 fill 單 NaN 必紅——現規則在 fill_r=0.95 已紅，探針 `high_fill_one_nan`）。

### (3b) 與「只定向、保留分層」之碼證分歧

本家主張 **exact 為終態**。碼證：探針 `reverse_trunc_finite` 在定向規則下通過、exact 失敗；⑤ 把反向不對稱也算洩漏／非決定論；s1 0 informational 表示單週期因果基線沒有「合法的低 fill 不對稱」要靠分層放行。若第 3 段出現 informational，先分類那些列（`full=1.0 trunc=0.7` 型 vs 雙側稀疏），再決定定向是否當過渡。加長 `POST_WARMUP_BARS` 與 `min_periods=1` mutant 都不是本洞修法。

---

## GROK-R1-P0-01

**斷言**: `_assert_nan_mask_layered` 在比較窗 fill_rate 未雙達 0.95 時只印 informational，加上值 gate 只比 both-non-NaN，使 L3 `center=True`＋`min_periods=window` mutant 的「full 有限、trunc 尾端 NaN」洩漏整段通過截斷 MR。

**碼證**: s2 log `test_small_mutation_numba_rolling_center_true_fails`：helpers.py:1593 呼叫 `_expect_causal_gate_failure`，L1520 `check()` 得 `Failed: DID NOT RAISE`；stdout 236 行 `NaN mask informational`（155× `full=1.000 trunc=0.700` W13，81× `trunc=0.900` W5）。函式 L808 若 mask 已等則 return；L810–821 兩側 fill 皆 ≥ `HIGH_FILL_RATE_THRESHOLD=0.95` 才 raise，否則 print。`_assert_values_gate_main` L980–991 先 layered 再 both-non-NaN。mutant L1587 只覆寫 mean 槽 `output[:, widx, 0]`。探針 `w13_mp_window`：layered.raised=false、values_both.raised=false、exact.raised=true、directional.raised=true；`values_gate_main_w13` raised=false。探針 `equal_sparse` fill=0.25 三規則皆不紅。`l7_dead_feature_drop` 於 `_mr_nan_strategy` 關閉。
CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:811
MUTATION: venv/bin/python -m pytest tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py::test_small_mutation_numba_rolling_center_true_fails -q --tb=line

**類別**: code-contract

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b; tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#12b74d75885b; handoffs/run_receipts/20261002-ffstat-small-mr-s2.log#ff5498e42586; handoffs/20261002-FFSTAT-B6-CONSULT-R1-BRIEF.md#333afa150740; handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-RECONCILE.md#58798e0b568c

修法：在 `_assert_nan_mask_layered` 內，比較窗 mask 不等即 raise（刪或短路 L810–821 的 fill-rate skip）。可先 print 再 raise，不另建 gate。可行性：探針 exact 已在 W13／W5 合成洩漏上 raise，且在 equal_high／equal_sparse／`min_periods=1` 值洩漏上不 raise；s1 0 informational 表示縮小版因果基線沒有 mask 不對稱會被這條 promote。最低過渡：同一函式加定向 `np.isfinite(full) & np.isnan(trunc)` 失敗——探針 directional 在 W13／W5 已 raise。B2 §二-3 分層原為 dead_drop 列數依賴；現行 MR 關 dead_drop，該豁免不再覆蓋「full=1.0 trunc=0.7」的置中窗尾。使用者：「未來洩漏絕對修掉不得列殘留」。影響：主 MR 與縮小版共用 helpers；fracdiff atol 路徑本就 exact mask，不受本改。

---

## GROK-R1-P2-01

**斷言**: 尾擾動版 fracdiff 長度耦合控制在 codec 值差下只於 `_assert_values_gate` 失敗，而該 gate 不在 `_FRACDIFF_PRE_VALUES_GATES`，測試紅但抓不到 mutant；截斷版與並行版已打同一 seam，本項應撤，不得再疊 xfail。

**碼證**: s1 log：`test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails` 於 helpers.py:1744 以 `allowed=_FRACDIFF_PRE_VALUES_GATES`（`_assert_columns_gate`、`_assert_d_star_gate`）呼叫 `_expect_causal_gate_failure`；實際路徑含 `_assert_values_gate`，訊息 `Not equal to tolerance rtol=0, atol=1e-08`、`volume_1h_trend_EMA_144_Momentum_L55_fracdiff`、Max abs 2.901256e-05、Max rel 0.00042215。small_mr.py:100–101 為該 node；:96–97 截斷版、:104–105 並行版同一 `run_control_fracdiff_maxlag_len_coupling`。SPEC Task 4.2：不得新增 skip／xfail；尾擾動為底之長度耦合只承認值 gate 之前的失敗。探針 `values_gate_atol_tail_nan` 證明 fracdiff 值 gate 對 tail-NaN 走 exact mask（與主 MR 分層洞不同），本項失敗是 **兩側有限值差**，與 codec xfail 同類。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py#12b74d75885b; tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b; handoffs/run_receipts/20261002-ffstat-small-mr-s1.log#ed70376e5a31; docs/FFSTAT_SPEC.md#f8a327dafd6a

處置：刪 `test_small_mutation_fracdiff_maxlag_len_coupling_tail_fails`（既有全鏈檔對應項一併刪）。保留 truncation＋parallel 兩控制與 `test_small_fracdiff_tail_perturbation_invariant` 既有 codec strict xfail。本條為套件鑑別力問題，不是生產特徵洩漏。

---

## 「我沒查」三面

1. **fracdiff `_assert_values_gate`（atol）**：比較窗 exact mask（L1035–1037），無 fill-rate skip。探針 `values_gate_atol_tail_nan` raise `fracdiff NaN mask`；`values_gate_atol_value_diff` raise numpy atol。與主 MR 分層洞不同。
2. **`_assert_warmup_nan_masks_equal`**：warmup 段 exact mask，範圍只 `[0:warmup)`。探針在 trunc 尾植入 full-finite／trunc-NaN 後 warmup gate 不 raise。尾端洩漏本應由比較窗值／mask gate 負責；洞在 layered，不在 warmup。
3. **align oracle**：`_assert_align_coarse_boundary_lookahead_detected` L1307–1315 對 12h 邊界做 `np.isclose(..., equal_nan=True)`；雙 NaN continue；一側有限一側 NaN 計入 mismatch。不走 `_assert_nan_mask_layered`。Oracle 是正向「必須看到差異」；MR 本體失敗仍走值 gate。多週期第 3 段 informational 計數仍是 ⑤ 的否證觀測。

---

## 驗證留痕

```
grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-s1.log
grep -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-s2.log
TMPDIR=/tmp/ffstat_b6_maskp PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat_b6_maskp/probe.py
git status --short -- momentum api frontend tests templates config
```

s1→0；s2→236；probe rc=0 寫 `probe_result.json`；scoped git status 與開跑前同型（既有 `__pycache__`／golden／`.DS_Store` 噪音）。

ASSUMPTIONS_VERIFIED: brief ①–④ 與 s1／s2 log 及 helpers 行號一致；⑤ 單週期成立、多週期待 s3
TESTS_RUN: `/tmp/ffstat_b6_maskp/probe.py` rc=0（未跑生成型 pytest node）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT: handoffs/20260926-ffstat-b6-consult-r1-grok.md

VERDICT: blocked
BLOCKED-BY: GROK-R1-P0-01
CLOSED:
