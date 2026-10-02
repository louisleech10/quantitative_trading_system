# FFSTAT 第 6 批 consult R1 — codex

task-id: 20260926-FFSTAT-B6-CONSULT-R1
brief-kind: consult
round-id: 88499789-aa56-4222-a4ac-ebf4dd6f8f92

本輪唯讀研究；一條 P1，六問與三組成對必答如下。結論是主 MR 的低 fill-rate mask 豁免有可重現漏測，建議以原 gate 內無條件 mask 全等取代分層。這是測試缺陷，並非本輪發現生產 L3 使用 center=True。本報告不宣稱三家已形成共識。

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
