# Reconcile — 20260926-ffstat-b6-consult-r1

**來源** 20260926-ffstat-b6-consult-r1-codex.md, 20260926-ffstat-b6-consult-r1-composer.md, 20260926-ffstat-b6-consult-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

三家一致：截斷 MR 之 NaN mask 分層（任一側 fill_rate < 0.95 只印 informational）使 L3 置中窗洩漏（full 有限、trunc 尾端 NaN）整段未被擋下，屬未來洩漏漏測，須修。修法分歧：codex 主「比較窗內共同欄雙方向全等、不論 fill_rate」（秒級探針：tail6、reverse6 改前放行、改後拒收；同位置稀疏 50% 改前改後皆放行）；composer 主「單側高密度、trunc 尾端單向 NaN 必抓，雙側稀疏 churn 仍可豁免」。依分歧規則採較嚴版（codex）：反方向（full 缺、trunc 有限）同樣違反共同前綴不變，稀疏不構成豁免；正常基線（全跑第 1 段）informational 0 行為不致假紅之證據，多週期正常基線之同類證據由第 3 段 log 補（舊規則只在 mask 不同時印此行）。其餘一致：`POST_WARMUP_BARS`＝20 維持（加長不是修法，且任何更長置中窗仍可繞過分層）；置中 mutant 之 `min_periods=window` 保留（min_periods=1 版值 gate 本會紅，不需另開慢生成）；尾擾動版 fracdiff 長度耦合控制撤除（mutant 只於值 gate 現形、基線本即 codec 值 gate 失敗 ⇒ 無可辨認出口；截斷版、並行版承接），不新增 xfail；assumed ⑤ 為條件成立之因果不變式（codex：封閉原因集合宜含資料前綴不等價、錯位等，但皆不支持 PASS）。fracdiff `_assert_values_gate` 與 warmup gate 本即無條件要求 mask 全等，無同類盲點（codex 讀碼＋探針）。重跑範圍：修正後之 L3 置中 mutant（單週期）以新 gate 重跑；多週期第 4–6 段以新 gate 跑；已通過之正常基線與無關控制不重跑。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| mask 盲點：主截斷MR允許低fill-rate共同欄 | P1 | CODEX-R1-P1-01 | 採納（雙方向全等、不論 fill_rate；秒級邊界測試＋舊規則 mutant 兩例紅） | code-contract |
| mask 盲點：主MR之`_assert_nan_mas | P0 | COMPOSER-R1-P0-01 | 採納（同上） | code-contract |
| mask 盲點：`_assert_nan_mask_la | P0 | GROK-R1-P0-01 | 採納（同上） | code-contract |
| 豁免範圍：B2reconcile（`handoff | P1 | COMPOSER-R1-P1-01 | 部分採納（單側尾端 NaN 必抓採納；雙側稀疏 churn 豁免不採，依較嚴版雙方向全等；同位置稀疏照常通過） | doc-sync |
| 比較窗：`POST_WARMUP_BARS=20 | P2 | COMPOSER-R1-P2-01 | 採納（維持 20；根因為 gate 規則） | other |
| 置中寫法：L3centermutant以`min_ | P2 | COMPOSER-R1-P2-02 | 採納（保留 min_periods=window） | other |
| 尾擾動長度耦合：`test_small_mutation | P2 | COMPOSER-R1-P2-03 | 採納（撤除，既有檔同撤；不新增 xfail） | code-contract |
| 尾擾動長度耦合：尾擾動版fracdiff長度耦合控制在c | P2 | GROK-R1-P2-01 | 採納（同上） | code-contract |
| 前提⑤：assumed⑤（比較窗內full有限／ | P2 | COMPOSER-R1-P2-04 | 採納（多週期正常基線 informational 行數補證） | other |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01

**斷言**: 主截斷 MR 允許低 fill-rate 共同欄之 NaN mask 不對稱，會放過需要未來六根的 L3 置中均值；其覆蓋率守衛不能阻止這種漏測。

**碼證**: `tests/feature_engineering/ff_truncation_mr_helpers.py:797-821` 在任一側 fill_rate < 0.95 時只列印；`:771-794` 只比 both-non-NaN；`:975-977` 每欄只要有一格共同非 NaN 即增加 comparable_columns，並非逐格完整性守衛。`:1573-1593` 既有 mutant 把 mean 改成 center=True、min_periods=window。既有 `handoffs/run_receipts/20261002-ffstat-small-mr-s2.log:5331-5334` 有 DID NOT RAISE 與 full=1.000、trunc=0.700；`:7128-7129` 摘要為該控制失敗、其餘五項通過。

CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:807
MUTATION: `_assert_values_gate_main` 比較一個共同欄 full=`np.arange(20.)`、trunc=`np.r_[np.arange(14.), [np.nan]*6]` 的小 parquet，warmup=0、n_trunc=20；原 gate PASS。既有端到端操作是 `run_control_numba_rolling_center_true(SMALL_SCOPE, monkeypatch, tmp_path, kline_df_module)`（本輪依禁令未重跑生成）。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#aba8dc92e20b

**類別**: code-contract

修法：原 `_assert_nan_mask_layered` 中移除高 fill-rate 判斷與 informational 旁路，對相同比較段直接 `assert np.array_equal(np.isnan(left), np.isnan(right))`，沿用 context 訊息；both-non-NaN 值比較在 mask 已相等後仍可維持，容差、抽樣、coverage 分母不變。不採只擋 full 有限／trunc NaN 的單方向規則：反方向同樣違反共同前綴不變，秒級探針也重現反方向存活。這是替換既有 gate，不增加額外生成流程。

可行性證據：`venv/bin/python /tmp/ffstat-mask-Ql4gVt/probe.py` → rc=0，約 0.68 秒。AST 取 `/tmp` helper 複本的原始函式，在小 parquet 上實跑；抽樣與分層覆蓋準備用單欄 stub 隔離，本探針不代表完整抽樣設計已驗。原主 gate 放過 tail6、reverse6，替換後主 gate 兩者 REJECT；相同 50% 填充率之稀疏 mask 在改前／改後均 PASS。覆蓋率守衛未改，故修法可在原比較流程內完成。新 assertion 的 traceback 仍經 `_assert_values_gate_main`，與 `_expect_causal_gate_failure` 的既有允許函式集合相容（碼證 `:1511-1533`；捕獲流程整體未於本輪實跑）。

### 必答 1：Q1–Q6 結論與依據（1a／1b）

| 問題 | (1a) 結論 | (1b) 依據與限制 |
|---|---|---|
| Q1 | 比較窗內共同抽樣欄 mask 雙方向全等，不依 fill_rate；稀疏不構成豁免。 | P1 的秒級探針与 s2 log；舊收斂 §二把低 fill-rate、near-empty、僅一側欄合併視為列數依賴良性，但未提供「共同欄共同時間格合法 mask 不對稱」的實證。掉整欄是 schema 問題，不能支持保留下來之共同欄值位置豁免。 |
| Q2 | 縮小單週期已有支持證據；全設定 13 項與正式多週期尚不能保證無假紅。 | s1 沒有任何 `NaN mask informational`；s2 有 236 行，均為 center mutant 失敗報告。舊 helper 只在 mask 不同時印 informational，故正常主 MR 之已抽樣比較位置有直接證據；這不涵蓋未抽樣欄。多週期 probe JSON 的 `status=pass` 只證舊 gate，沒有 informational 計數；本輪未取得第 3 段完成結果。 |
| Q3 | 維持 POST_WARMUP_BARS=20；加長不是本缺陷修法。 | W13 的六格差異在 20 列即充分可見，漏測來自放行。探針長度 20 原主 gate PASS，120／121 則 REJECT，因 114/120=0.95 跨過門檻。任何更長置中窗／更稀疏欄仍可繞過分層。`_required_window_bars:140-155` 將 min_post_warmup 加入生成窗，故加 N 會加 full／trunc 公開域列數及計算／儲存量；總時間增幅未量測，不虛報線性秒數。 |
| Q4 | 保留 min_periods=window 的既有控制；它是合理且必須抓到的完整窗置中洩漏。min_periods=1 可作秒級值 gate 補充，無需另開一對慢生成。 | `:1582-1587` 只改 mean、其餘統計沿用原輸出，足以代表缺陷。秒級平方序列長 50／40、W13、warmup=20：minp13 原主 gate PASS、strict mask REJECT；minp1 mask 相等但原主 gate 因值差 REJECT。minp1 不能取代 minp13，否則會掩蓋本輪 mask-only 攻擊面。該值 gate 結果只證此序列，不保證所有真實欄都超過既有容差。 |
| Q5 | 不新增 strict xfail；本家支持撤除／合併這支無鑑別力之尾擾動長度耦合慢控制，保留尾擾動正常基線既有 strict xfail、截斷與並行長度耦合控制。 | s1:5553-5555：被拒收的錯誤來源是 `_assert_values_gate`，不在只允許 columns／d* 的集合；`:1701-1703,1748-1749` 明確設了此前值 gate 邊界。無 mutant 尾擾動基線已因 codec 值精度失敗，因此放行該錯誤不構成成功偵測 mutant。SPEC §Task 4.2:203 禁新增 xfail；若委員採撤除，SPEC／manifest 及 node 對應、數量與收據之差異需要由主委具名同步，本輪未改任何測試或文件。 |
| Q6 | 正在跑的正常多週期基線可先完成，取得 mask 證據與可重播產物；第 4–6 段之 mutant 驗收採修正後共用 gate。 | 不必為純 gate 修改重生成相同正常 full／trunc。若第 3 段保留 raw parquet 與 pair 的 warmup／n_trunc／metadata／時間軸，可對同產物重放新 gate。若產物未保留，舊 log 的零 informational 可證舊抽樣格 mask 已同，不能冒稱新碼整條已跑。修補捕獲邊界先秒級驗，再繼續受影響尚未跑的 node。已跑的獨立 fracdiff／校準等控制不因無關 mask gate 修改而全部重跑。 |

Q5 的理由是該操作沒有可辨認的新失敗出口，而非既有測試紅就刪掉。缺陷 max_lag 長度依賴之威脅未放棄，仍由兩個相同 mutant 本體之截斷／並行控制承接；尾擾动基線之 codec 問題仍可見。SPEC 現行「具名全部 mutant」要求與這個建議有差异，主委尚未核可之前不能把當前紅改報綠。另一條可行方向是先修 codec 再驗正常基線和尾擾動 mutant，但那會擴大生產數值／儲存 scope，並非本輪 NaN gate 的必要修法。

### 必答 2：assumed ⑤（2a／2b）

(2a) ⑤是**條件成立的因果不變式**，不是本輪已證實的生產全稱事實。前提包括同一欄、同一時間戳、相同起始資料／校準與設定、trunc 確為 full 的資料前綴、比較點之前可取用的跨週期來源集合相同。具備這些前提，因果函式連「是否缺值」也不能依後綴而變；雙方共同的真實缺值、稀疏、warmup 或未滿 trailing 窗只會造成相同 mask。

(2b) `TimeframeAligner.build_asof_index_map` (`momentum/FeatureEngineering/timeframe/tf_aligner.py:158-169`) 用 source close ≤ decision 的 backward map。在 open_minus（正規化為 open_time）下，新增加於共同決策時間之後才收盤的粗週期 bar 不會合法改变共同過去列；若實際資料讀取／完成 bar 過濾移除了 trunc 端原本已閉合的來源，應區分輸入對不等價與對齊缺陷，不能直接給低 fill_rate 豁免。此生成資料端前提本輪僅讀碼，未跑完整多週期來源快照。

`FeatureStorage._select_parquet_storage_array` (`momentum/FeatureEngineering/feature_storage.py:2867-2893`) 的 float16／float32 轉換保留 NaN，且有限值轉成非有限會退回 float32；rank／zscore codec 的 `:1951-1963` 也驗 mask 原值全等。因此既有 codec **值捨入**問題不能支持 mask informational。dead-drop 移除欄是欄集合問題，主 MR 配置已關 L7 dead-drop；本輪不改使用者允許之整史選欄，也不宣稱 columns gate 容許範圍已完全不存在洩漏。

換言之，⑤列的「只可能洩漏或非決定論」作為錯誤原因封閉集合過強，還可能是資料前綴不等價、錯位或其他管線缺陷；但那些原因同樣不能支持因果 MR 的 PASS。第 3 段若出現無 mutant 不對稱，足以否證「現行正常管線從無這種情況」；是否假紅需要該格時間與來源證據，單靠稀疏標籤不能定性。

### 未查面的核對

fracdiff `_assert_values_gate(atol=...)` 在 `ff_truncation_mr_helpers.py:1033-1036` 無條件驗 mask 全等，再以 rtol=0、既有 atol 比值；沒有同類 fill-rate 旁路。`_assert_warmup_nan_masks_equal:897-903,919-924` 呼叫 `_assert_arrays_values_close`，其 `:754-756` 也要求 mask 全等。秒級探針 tail6／reverse6 被 fracdiff gate 拒絕，warmup 段單格 NaN 差異被拒絕。這些檢查仍只涵蓋自己選取或交集之欄，並非全欄存在性證明。

多週期 align oracle `:1308-1313` 只在雙方均 NaN 時略過，`np.isclose(..., equal_nan=True)` 會把單側 NaN 視為不相等，故 oracle **能看到** mask-only 差異。然而它的角色是正向證明 mutant 有差異，真正收件仍經共用主 MR；舊主 MR 有可能把已由 oracle 見到的低 fill-rate 不對稱放過。修共用 gate 同時封住這條消費路徑，無需改 oracle 或另加生成。

### 必答 3：修法與重跑範圍（3a／3b）

(3a) 本家供收斂之方案是原 NaN gate 雙方向 exact、保留既有值容差与覆蓋率、維持 20 列及 minp=window 控制、不新增 xfail、尾擾動長度耦合控制去重。驗證順序與最小範圍為：秒級 gate 正反 mask／同 mask 稀疏與值差；現有 capture boundary 與共用 gate 之捕獲相容；已保留正常產物以新 gate 重放；單週期 L3 center 控制由修正後 gate 取得真實被拒原因；多週期正常與尚未跑的共用主 gate mutant 依原分段完成。若已有保存的 center mutant 產物，也可重放並核對 seam、準備證據和新 gate traceback，避免重生成。完整 13 項的本機资源限制与 RM-FULLSCALE 不变，沒有把它們算成本輪通過。

(3b) 本輪未讀他家交件，沒有三家共識之已驗聲明；可能分歧點是 Q5 的撤除／codec 修復及⑤的無條件表述。碼證分別為 `:1748-1749` 的前值 gate 限制、SPEC `:195,199,203` 與對齊 map 的 `:158-169`。假設新多週期基線提出合法例外，需有具體共同時間格／來源比較才能改本家判斷；不支持為讓測試綠而放寬 mask。

### 秒級實跑紀錄與重現邊界

探針先 `cp tests/feature_engineering/ff_truncation_mr_helpers.py /tmp/ffstat-mask-Ql4gVt/helpers.py`，AST 編譯 `_fill_rate`、兩個 array 值 gate、mask gate、主值 gate、fracdiff 值 gate、warmup gate；未 import 專案生成器。單欄 parquet 的抽樣／覆蓋准备 stub 僅用以讓原函式執行至被研究出口，coverage 計數仍為原碼。修法試算僅替換同名 mask 函式：

```python
def _assert_nan_mask_layered(left, right, *, context, fill_rate_left, fill_rate_right):
    assert np.array_equal(np.isnan(left), np.isnan(right)), context + ' NaN mask mismatch'
```

實跑 `venv/bin/python /tmp/ffstat-mask-Ql4gVt/probe.py`，探針 sha256=`cc50d840c2ac61ee3e2c1dc84f42379e045fbbe4abc19a8c8355f97edd7b9703`，rc=0，输出摘要：

```text
tail6 main=PASS strict-mask=REJECT frac-mask=REJECT
reverse6 main=PASS strict-mask=REJECT frac-mask=REJECT
sparse-equal main=PASS strict-mask=PASS frac-mask=PASS
length20 main=PASS strict-mask=REJECT frac-mask=REJECT
length120 main=REJECT strict-mask=REJECT frac-mask=REJECT
length121 main=REJECT strict-mask=REJECT frac-mask=REJECT
center-minp13 main=PASS strict-mask=REJECT frac-mask=REJECT
center-minp1 main=REJECT strict-mask=PASS frac-mask=REJECT
warmup-mask REJECT
patched-tail6 main=REJECT strict-mask=REJECT frac-mask=REJECT
patched-reverse6 main=REJECT strict-mask=REJECT frac-mask=REJECT
patched-sparse-equal main=PASS strict-mask=PASS frac-mask=PASS
```

center 案輸入為 `pd.Series(np.arange(50.)**2)` 及其 40 列前綴，`rolling(13, center=True, min_periods=13或1).mean()`，比较 `[20:40)`。sparse 案为 `np.where(np.arange(20)%2, np.nan, np.arange(20.))`，雙方同值。每案 parquet 均由这些明示合成数组構成，僅驗 gate，未作为 Feature Factory 真實資料替代物。

`rg -c 'NaN mask informational' handoffs/run_receipts/20261002-ffstat-small-mr-s1.log handoffs/run_receipts/20261002-ffstat-small-mr-s2.log` → 只输出 s2:236，s1 零匹配。`tail -8 ...s1.log` → 1 failed／5 passed／1 xfailed，失敗項為尾擾動長度耦合；這是既有收據讀取，非本輪重跑。Arrow 顯示 sandbox sysctl CPU cache 資訊 warnings，探針仍 rc=0。

ASSUMPTIONS_VERIFIED: 秒級小 parquet 證實原 gate 漏 mask、exact 修法拒兩方向且接受同 mask 稀疏；全設定與正式多週期未驗證。
TESTS_RUN: `venv/bin/python /tmp/ffstat-mask-Ql4gVt/probe.py` rc=0；`cmp /tmp/ffstat-mask-Ql4gVt/status-before.txt /tmp/ffstat-mask-Ql4gVt/status-after.txt` rc=0、無輸出（兩檔均由 `git status --short -- momentum api frontend tests templates config` 產生）。
FAILURES_SEEN: 探針第二次執行因已有 full／trunc 暫存目錄發生 FileExistsError；mkdir 改 exist_ok=True 後 rc=0。最初搜尋不存在之 ff_fracdiff_mr_helpers.py，後由 rg 確認函式實在共用 helper；無生產改碼。
SCOPE_CHANGES: none；僅交件檔與本次 /tmp 工作目錄。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪未改生產數值、schema、輸出大小或測試。提案收緊測試 gate、去重一支慢控制，尚未實作。
HANDOFF_NOT_UPDATED: 本輪唯讀 brief；根 HANDOFF 與另份狀態交接均未改寫，交件落點為本檔。

交件自驗：`bash scripts/completeness_check.sh --single handoffs/20260926-ffstat-b6-consult-r1-codex.md --family codex --round-id 88499789-aa56-4222-a4ac-ebf4dd6f8f92` → rc=0，`COMPLETENESS PASS(single)`、1 個 canonical ID。收尾 `git status --short -- momentum api frontend tests templates config` 另存 status-final.txt，再 `cmp .../status-before.txt .../status-final.txt` → rc=0、無輸出。`rm -r /tmp/ffstat-mask-Ql4gVt` → rc=0；`test ! -e /tmp/ffstat-mask-Ql4gVt && test -d /tmp/claude-501` → rc=0，本次暫存已清、claude-501 保留。探針檔已隨清理移除，明示輸入與實跑摘要留存於上文。

VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01
CLOSED:
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

