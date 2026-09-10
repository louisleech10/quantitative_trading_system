# EVTLABEL B4（Phase 3 第二批：Task 3.4–3.7 mode 決策／統計／門檻／置換與負對照）code review R1

brief-kind: review
task-id: 20260910-EVTLABEL-B4-REVIEW-R1
findings-round: R1
標的 diff：`git diff 34381156..06ccb917 -- momentum tests handoffs`
規格：`docs/EVTLABEL_SPEC.md` Task 3.4／3.5／3.6／3.7（v4，三家已 RECONCILE-STAMP APPROVED）

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0／§1（十一類）；審查對象是**碼**。
findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。實作者（Claude）不自審。

## 使用者主目標（SPEC §A 逐字，任何把它延後的建議＝否決點）
> 「我在外面標好正反例（標的＋t₀＋0/1 標籤）匯入，平台找出 t₀ 之前哪些特徵能把正反例分開，再把這些特徵餵 ML。」

本批是「找出哪些特徵能分開」這一段的**數值核心**。錯了不會拋例外，只會給出一份看起來
很漂亮的倖存者名單。

## 這批改了什麼

1. **Task 3.4（stage3 決策與綁定）**
   - `_resolve_label_mode_and_bind_binary`：effective mode 之**唯一**決策點。
   - selection scope＝`split_context["test_mask"]`（無切分 ⇒ full_sample）；
     四種 reason：`no_label_column`／`label_invalid_domain`（取 staging hint）／`one_class`／
     `class_below_min_selection`／`conditional_ic_abandoned`。
   - 明示 `imported_binary` 不足 ⇒ raise；`metadata.label_mode` 揭露整批與驗證段兩組計數。
   - 0/1 走 `validate_consumed_label`（event_given 分派），封 frozen `ValidatedBinaryLabel`，
     `series.to_numpy().flags.writeable = False`。
   - `validate_event_given` 回傳新增 `consumed_event_rows={event_id:(ts_ms,value)}`（additive）。

2. **Task 3.5（`momentum/Analysis/binary_discrimination.py`）**
   - `mann_whitney_table`：一次呼叫 `mannwhitneyu(axis=0, nan_policy="omit")`；
     `auc=U/(n_pos·n_neg)`、`rank_biserial=2·auc−1`；三種 unavailable（all_nan／
     class_below_min／constant）回值＋status，不拋例外；`weights` 非 None ⇒ `NotImplementedError`。

3. **Task 3.6（stage5）**
   - `_merge_binary_statistics`：消費前三守衛（index 對齊／長度／`rows_frozenset` 逐列子集），
     **無** digest 相等比對；對證後直接餵 `mann_whitney_table`。
   - `_apply_thresholds(..., binary_mode=True)`：報酬版六道記錄到 `*_skipped_binary_mode`
     不剔除；效應量閘 `abs(rank_biserial) >= rank_biserial_min`；p 閘讀 `mw_p_value_adj`；
     `binary_status != ok` ⇒ `removed["binary_unavailable"]`；排序改 `(-abs(rb), name)`。

4. **Task 3.7（置換與負對照）**
   - `block_ids_for_events`：`L = max(1, ceil(W/min_gap), ceil(W/median_gap))`。
   - `_permute_blocks`（獨立小函式供 mutation）、`block_permutation_oracle`
     （沿用三道硬檢與雙尾經驗 p；`n_blocks < 10` ⇒ `unavailable:insufficient_blocks`）。
   - `_run_binary_permutation_and_negative_control`：逐倖存者置換自檢
     ⇒ `permutation_oracle_disagree`／`permutation_unavailable`；
     整批負對照 `negative_control_n` 次、`q95 = quantile(..., method="higher")`（整數）；
     `n_observed <= q95` ⇒ `self._survivor_suppressed_reason="negative_control_failed"`；
     `n_observed == 0` ⇒ `skipped:no_survivors`、不設 suppressed。

## 🔴 請優先攻的八點

1. **`_binary_feature_bar_ms` 用「相鄰事件之最小正間距」推特徵 K 線長度**——
   這是我自己想的啟發式，SPEC 沒有規定。事件稀疏時最小間距**不一定**等於一根
   （例如所有事件都相隔 3 根以上 ⇒ 推出 3 根，於是 `block_len` 被低估三倍 ⇒ 區塊保護不足）。
   請正面打：這是不是真的洞？正確做法應該是什麼（由 `timeframe_seconds` 傳進來？）。
2. **`_binary_label_window_bars` 是 instance 狀態**，在 `analyze` 的切分段設定、
   在 stage5 才讀。掃描格每格重用同一個 orchestrator 嗎？refilter 路徑會不會讀到上一次的殘值？
   （B1 review 抓過我「計時沒歸零」的同型錯。）
3. **負對照的計數規則與主篩選是否真的同一套**：我在負對照裡重寫了一遍
   「`status==ok` 且 `q<=alpha` 且 `abs(rb)>=min`」，而主路徑走的是 `_apply_thresholds`。
   兩份判準若分歧，`q95` 就不是同一個尺度上的數字 ⇒ 比較無意義。請確認。
4. **置換自檢對「已被門檻擋掉的特徵」不跑**（我只對 `passed` 跑）。
   這是否讓 `negative_control` 的 `n_observed` 與 shuffled counts 不同義？
   （shuffled counts 是對**全表**重算門檻後的數量。）
5. **`block_permutation_oracle` 的 `n_perm` 由預算除以 K**，但負對照又跑 `negative_control_n`
   次**全表** `mann_whitney_table`。39,373 欄 × 50 次的實際耗時我**只在 165 列的小 fixture 上跑過**。
   請估算或實跑真實規模，判斷是否會讓一次分析從分鐘級變成小時級。
6. **stage5 之 `features_for_stats` 是否恆等於 selection scope**：我用它同時當
   「統計輸入」與「守衛比對對象」。若 stage5 在此之前對欄或列做過任何過濾，兩者就不同。
7. **`_merge_binary_statistics` 在 `summary_table` 之列名對不上時 `continue`**（靜默略過）。
   對不上代表什麼？該不該 raise？
8. **既有紅之歸因**：本批未新增既有紅；`tests/momentum/Analysis` 之 20 條既有紅已具名於
   `HANDOFF.md`。請確認本批沒有讓其中任何一條變得更嚴重。

## ⚠️ 前置說明
- **禁改碼、禁改文件**。不得跑 `pytest tests/governance`（小時級）。
- 既有紅基準見 `HANDOFF.md`「既有紅盤點」節（20 failed / 1615 passed），不要算進本批。
- 前端本批未動。

## 本 brief 之前提（逐條標）

fact-verified: B4 測試批 236 passed → 實跑（stage3／stage5／oracle／binary_discrimination
  ＋ isolation_channel／contract／cut1_split／core／staging／scan_cube）。
fact-verified: `--phase 3b` **8/8 RED**、對照組綠、UNCOVERED=0；`gate 3b` rc=0。
fact-verified: `--phase 2`／`3a` 未回歸（各 6/6、3/3 RED）。
fact-verified: G-6 survivor golden 逐項相等（`return_rule` 與全域皆未漂移）。
fact-verified: decoupling 對 baseline rc=0。
fact-verified: [A-2] 39,373×165 clean 0.49s／10% NaN 4.02s；植入 oracle auc=1.0000。
fact-verified: [A-3] `validate_event_given` 對 0/1 可重用；且**不驗值域**（label=7.0 照收）。
fact-verified: 我兩條斷言原本太鬆（mutation 首跑 `M-P3-3`／`M-P3-5b` GREEN），
  收緊後 8/8 全紅——其中 `M-P3-3` 原本挑的反例在該路徑上**結構上不可達**。

assumed: **最小正間距＝一根特徵 K 線**（`_binary_feature_bar_ms`）
← 否證觀測：一批事件彼此皆相隔 ≥2 根 ⇒ 推出的 bar_ms 是實際的 ≥2 倍 ⇒ `block_len` 被低估。
／我跑了：**沒跑**。只在「每根一個事件」的 fixture 上驗過。請正面打（必答 1）。

assumed: 負對照之計數判準與主篩選同義
← 否證觀測：同一份資料，`_apply_thresholds` 與負對照內聯判準給出不同的通過集合。
／我跑了：讀碼比對，**沒有**寫一條測試釘住兩者相等。請正面打（必答 3）。

assumed: 真實規模（39,373 欄 × 50 次負對照）不會讓分析變成小時級
← 否證觀測：實跑 > 120 秒。／我跑了：**沒跑**。只在 21 欄 × 120 列的 fixture 上跑過。
  Task 3.7 之 TODO 明列 benchmark 兩道，我尚未執行。請正面打（必答 5）。

assumed: `_binary_label_window_bars` 之 instance 狀態不會跨 run 殘留
← 否證觀測：掃描格或 refilter 讀到上一次的值。／我跑了：只在 `__init__` 設了預設 0，
  **沒查**掃描格是否重用同一個 orchestrator 實例。

## 🔴 我沒查的
| claim | observable_if_false | reason_code |
|---|---|---|
| binary 模式下 stage6（冗餘）之分數是否該改用 `abs(rank_biserial)` | 冗餘挑選仍用報酬版 ICIR／ic_mean ⇒ 與主統計不一致 | cost（TODO 要點 5 有寫，本批**未實作**——具名殘留給下一批） |
| stage6b（邊際 IC）在 binary 模式是否該標 `role="diagnostic"` | 使用者把報酬版邊際 IC 當成 binary 結論 | cost（TODO 要點 5，本批未實作） |
| `metadata.event_label_rule` 之 `primary_statistic`／`effect_gate` 揭露 | 報告沒說主統計是哪一個 | cost（Task 3.6 輸出欄，本批未實作——service 端揭露留給下一批） |
| 端到端（真實 kline）跑一次 binary 全流程 | 某處接不上而單元測試皆過 | needs-research（Task 3.10 之範圍） |

## 必答（成對）
1a. `_binary_feature_bar_ms` 之啟發式是否為真洞？ 1b. 正確做法（含應由誰傳入）。
2a. `_binary_label_window_bars` 之 instance 狀態會不會跨 run／跨格殘留？ 2b. 若會，最小修法。
3a. 負對照之判準與 `_apply_thresholds` 是否同義？ 3b. 若否，最小修法（能否直接複用同一函式）。
4a. 置換自檢只跑 `passed` 是否讓 `n_observed` 與 shuffled counts 不同義？ 4b. 正確做法。
5a. 真實規模之負對照耗時（估算或實跑）？ 5b. 若超 120 秒，該降階還是改設計。
6a. `features_for_stats` 是否恆等於 selection scope？ 6b. 若否，守衛比對的是不是錯的對象。
7a. 列名對不上時 `continue` 是否該改 raise？ 7b. 你的判斷與理由。
8. 有無 ≥10× 不必要複雜？本批可否進第三批（Task 3.8／3.9 倖存者輸出與前端）？

## 停輪條件
① 必答 1a–8 皆有 verdict；② 必答 5a 有數字（估算須寫出算式，實跑須附秒數）；
③ 必答 3a 有具體比對結果；④ P0／P1 皆指出修訂位置與最小修法。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
