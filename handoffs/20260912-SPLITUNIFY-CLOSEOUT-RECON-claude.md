# SPLITUNIFY 收尾（B8）偵察 — Claude 自產版

日期：2026-09-12｜主委：Claude Opus 5｜目的：把 SPLITUNIFY 未收票之殘留一次做完，並實測 VERDICTGATE 四閘之摩擦。

## 0. 範圍：要補的到底有哪幾條

`docs/SPLITUNIFY_TODO.md` §E ＋ `docs/SPLITUNIFY_SPEC.md` §N，扣掉已處置者：

| ID | 一句話 | 現行理由類別 | 我的初判 |
|---|---|---|---|
| `R-1` | per-symbol 投影未支援；多標的批一律 fail-closed | needs-research | **做**（研究問題可解，見 §2） |
| `R-5` | 事件掃描端拿不到 post-trim feature universe | needs-research | **做但收窄**（見 §4；不做全跨棧參數） |
| `SU-RESID-2` | 多 TF 之 `(event_id, timeframe)` 複合鍵 | needs-research | **做**（見 §5） |
| `SU-RESID-3` | 同源對證只比首尾，中間間距不同仍可過 | needs-research | **做**（見 §6） |
| `D1 範圍裁定` | 事件掃描端恆走 event-study-only | 曾以已廢止之「95% 就收」接受 | **重審**（見 §3） |
| `R-3` UAT | 使用者裁定最後 | user-ruling | 不動 |
| `R-4` | `extract_event_patterns` 無 production caller | blocked-by | 不動（屬 GAP-3） |
| `SU-RESID-1` | attribution checker 擋不住歸屬錯置 | 已由 VERDICTGATE Task 4.1 實作 | **已完成**（`_synth_attr.py`：ID 必列表＋逐字引用斷言前 20 字＋處置 token） |

## 1. 碼證（file:line；取得方式＝我自己跑 grep／讀碼，非實跑測試）

- 多標的 fail-closed 四處：`momentum/Analysis/event_samples/split_projection.py:385`（symbol 空）、`:402`（plan 未帶 symbol）、`:406`（train/test plan symbol 不同）、`:426`（事件 symbol ≠ plan symbol）。reason 字面 `multi_symbol_projection_unsupported` 住 `momentum/Analysis/contracts/split_unify.json::fail_closed_reasons`。
- **per-symbol 切分本體已存在**：`momentum/core/contracts.py:625 split_per_symbol()` 逐 symbol 產 `(train_plan, test_plan)` 對、每個 plan 帶 `symbol` 欄、且逐對跑 `validate_split_pair_integrity`。⇒ R-1 缺的**不是切分**，是**投影端接受多對 plan** 的語意。
- `base_universe_hash` 產生器：`momentum/Analysis/ic_filter_orchestrator.py:517 _base_universe_hash(index, symbol)`＝`sha256(hash_pandas_object({symbol, timestamp, _split_row_pos}))`。**已含 symbol** ⇒ 多標的下每 symbol 一個 hash，唯一性語意其實已定義；`split_per_symbol` 對所有 symbol 傳**同一個** `base_universe_hash`（:635 參數）才是語意衝突點。
- 同源對證現況：`split_projection.py:474-486`，以 `plan.time_bounds` 對 `feature_index` 之**首尾列**逐值比對（`_plan_bounds_as_ms` 型別分派、不猜單位）。殘留＝中間間距不同且首尾相同者仍會被放行。
- 單位歧異（SU-RESID-3 之所以難）：`contracts._coerce_timestamp_array` 對純數字一律 `unit="s"`；事件側時鐘是**毫秒**。改 hash 輸入會移動既有 IC golden digest。
- `build_event_keys`（`split_projection.py:255-302`）：以 `selected_timeframe` 過濾 `per_tf`，重複 `event_id` ⇒ raise（SU-RESID-2）。下游 `EventSplitPlan.assignments`（`momentum/Analysis/event_samples/types.py:87-93`）為 DataFrame，欄位由投影端決定 ⇒ 複合鍵是**加欄**而非改型別。
- R-5 之跨棧面（實際比 SPEC 描述小）：請求模型 `api/models/event_import_models.py:295-303 EventAnalyzeRequest`（已有 `test_fraction`／`embargo_ms`／`tier_min_test_events` 三個**當前未被使用**之欄）、路由 `api/routes/case.py:488 analyze_event_import`、前端唯一呼叫點 `frontend/src/lib/api.ts:1123`。IC 側識別一個 FF run 用 `(symbol, config_hash)`＋`features_path`（`api/services/ic_analysis_service.py:650,699`）⇒ **`features_run_id` 不必新造**，可用既有 `(features_path, config_hash)` 對。
- 現有測試面：`test_splitunify_derive.py` 55、`test_splitunify_disclosure.py` 22、`test_splitunify_golden.py` 9、`test_splitunify_contract.py` 8；golden `tests/golden/splitunify/splitunify_golden.json`（`g1_membership`／`g3b_oracle`／`g4_per_symbol_n`／`g5_row_fingerprint_*`）。

## 2. R-1（per-symbol 投影）——我的提案

**研究問題原文**：「per-symbol `SplitPlan` 之 `base_universe_hash` 語意在多標的下是否仍唯一」。

**我的答案：唯一性已經有定義，問題在傳遞不在語意。** `_base_universe_hash` 的輸入含 symbol ⇒ 每 symbol 一份 hash 天然唯一。真正的洞是 `split_per_symbol(base_universe_hash=…)` 對全部 symbol 灌同一個字面 ⇒ 投影端若照現行「兩 plan hash 必須相同」的檢查放行，就會用 A 標的的邊界投影 B 標的的事件。

**修法形狀**：投影端改收 `plans: Mapping[symbol, (train_plan, test_plan)]`＋`feature_index_by_symbol`，逐 symbol 走現行單標的路徑後**縱向合併** assignments／purged／clusters；每 symbol 各自跑既有四道 fail-closed 與同源對證；跨 symbol **禁**共用 row_index 數字。`multi_symbol_projection_unsupported` 保留為「呼叫端沒給 per-symbol 結構」時的 reason，不刪。

**攻擊面（我已想到的，請委員補）**：①兩 symbol 之 `feature_index` 長度相同 ⇒ row_index 可互換而不被長度閘抓到（對策：每 symbol 獨立做首尾＋逐列對證）②summary 的 `single_symbol` 欄語意要改（B4 已把它當恆亮）③golden `g4_per_symbol_n` 只有一個 symbol，需新增多標的 golden。

## 3. D1 重審（事件掃描端恆走 event-study-only）

D1 之成立理由在 R3 synth 已被更正為「三家逐輪複查後一致無異議」（非 95%），但 `b7-review-r1` synth 明寫**未重審**。我的立場：**D1 本身仍成立**（沒有 canonical universe 就不得宣稱 OOS，這是主目標），但它的**前提**在 R-5 做完後會改變——若事件掃描端能拿到 universe，D1 的「恆走」就該降為「拿不到才走」。⇒ D1 不推翻，改寫為條件式；這正是 R-5 的驗收條件。

## 4. R-5（universe 供給路徑）——我的提案：收窄做

SPEC 說要「新增 `features_run_id` 跨棧參數（請求模型／前端／契約／UAT 全動）」。**碼證顯示不必**：`EventAnalyzeRequest` 已有三個未使用欄位，加一個 `features_ref: {features_path, config_hash} | None`（選填、預設 None）即可；前端不改也能跑（None ⇒ 維持現行 event-study-only），UAT 不動。⇒ **新增對照路徑、不刪 Task 3.3 分支**（SPEC §N 明令）。

**誠實邊界**：此法讓「能不能拿到 universe」變成呼叫端的選擇；若呼叫端亂傳一個不屬於該批的 run，投影端必須擋——靠的就是 R-1 的每 symbol 同源對證＋SU-RESID-3 的逐列指紋。⇒ **R-5 依賴 R-1 與 SU-RESID-3**，排序不能反。

## 5. SU-RESID-2（多 TF 複合鍵）

現行：每事件在 selected TF 下恰一列，否則 raise。修法：`build_event_keys` 改以 `(event_id, timeframe)` 為鍵輸出，投影端 assignments 加 `timeframe` 欄；`ic_feed.py:109` 之消費端（已在做 `per_tf[per_tf.timeframe==tf]`）語意不變。**風險**：golden 之 `g1_membership` 以 event_id 列舉 ⇒ 多 TF 下同一 event_id 會出現兩次，golden 結構要加 TF 維度（改 golden 須經 review，SPEC §G）。

## 6. SU-RESID-3（逐列時刻指紋）

現行只比首尾。修法：plan 隨身帶 `row_time_fingerprint`（該 plan 全部 row 之時刻 sha256），投影端比對。**衝突**：新增欄位動 IC 契約與既有 golden digest。折衷案（我偏好）：**不改 plan 結構**，改由投影端對 `feature_index` 在 plan 之**全部 row_index** 上取指紋，與 `time_bounds` 首尾一起驗——但這只證明「傳入的 index 自洽」，不證明「plan 當初建在同一份」。⇒ 真解仍需 producer 側帶指紋。**請委員裁**：是接受「加欄＋接受 golden 位移」，還是維持首尾＋把中間間距列為永久誠實邊界。

## 6b. 主委自查補充（brief 標「我沒查」者，2026-09-12 已查完）

**已排除兩項**：
- `lightgbm_analyzer.py:377`／`xgboost_analyzer.py:1162` 之 `"lgb_cv_universe"`／`"xgb_cv_universe"` 假 hash **不會**流進投影路徑——兩支 analyzer 對 `split_projection`／`derive_event_split_from_plans` 零引用。
- golden `g5_row_fingerprint_*` **不受** SU-RESID-2 影響：`test_splitunify_golden.py:73-88` 由凍結明文重算，payload 四欄為 `[pos, ms, "ETHUSDT", "splitunify-golden"]`，與 timeframe 無關。會被動到的只有 `g1_membership`／`g3b_oracle`（以 `event_id` 列舉）。

**新發現三條（我自己找到，不是委員提的；三條都必須進 SPEC）**：

1. 🔴 **SU-RESID-2 與 dedupe policy 衝突（真風險，非理論）**：`dedupe.py:124-127` 之 `retained("cluster_first")` 以 `dedupe_cluster_id` 分組、取 `observation_interval_start_ms` 最早的**一列**。多 TF 複合鍵下，同一 `event_id` 的不同 timeframe 列若落在同一 cluster，會被**只留一列** ⇒ 複合鍵在投影端成立、卻在 dedupe 端被折疊。⇒ SU-RESID-2 不是只改 `build_event_keys`，必須同時裁定 dedupe 的分組鍵是否納入 timeframe。
2. 🔴 **`insufficient_events_in_test` 之 per-symbol 判定其實是壞的**：`split_projection.py:571` 寫 `insufficient = [s for s in per_symbol_n if n_test < int(tier_min_test_events)]`——條件**與迴圈變數 `s` 無關**，用的是**全批** `n_test`。單標的下 `n_symbols == 1` 故行為看起來正確；**R-1 一旦支援多標的，它會變成「要嘛全部標不足、要嘛全部不標」**。⇒ R-1 必須連修此條，且 mutation 要釘「只有該 symbol 的 test 數低於下限時才列入」。
3. 🔴 **既有斷言在 R-1 後變成假前提**：`test_splitunify_derive.py:537` 明文寫「`single_symbol` 恆亮是**預期的**……**不得**為了讓 `formal_pooled_inference_allowed` 變 True 而清空 `degraded`」。R-1 支援多標的後，`n_symbols > 1` 時該旗標本來就不該亮——**修這條測試的方向，與它警告的方向字面相同**。⇒ SPEC 必須把解除條件寫死為「**只有 `n_symbols > 1` 才解除**，且解除後 `formal_pooled_inference_allowed` 之其餘前提（cluster 調整等）不得連帶放寬」，並配 mutation：把解除條件改成無條件 ⇒ 必紅。旗標唯一產生點在 `event_split.py:20-30 _degraded_flags`（已是 M11 mutation seam），改動面收斂。

## 7. 我要問委員的（也是本輪必答）

1. R-1 之研究問題我判為「已有定義、問題在傳遞」——碼證是否支持？有無反例（兩 symbol 同 hash 之合法情形）？
2. R-5 收窄成選填 `features_ref` 是否真的避開跨棧改動？前端 None 路徑是否仍會顯示正確 capability 字面？
3. SU-RESID-3：加欄（動 golden）vs 維持首尾（留邊界）——給立場與碼證。
4. SU-RESID-2 之 golden 結構改法：加 TF 維度是否會讓既有 5 組 golden 全部重算（＝失去「改壞會紅」的基準）？
5. D1 改寫為條件式是否等於推翻 D1？若是，須走凍結文件修訂程序哪一條路？
6. 批次切法：我初擬 b8＝R-1、b9＝SU-RESID-2＋SU-RESID-3、b10＝R-5＋D1 條件化。依賴對不對？
