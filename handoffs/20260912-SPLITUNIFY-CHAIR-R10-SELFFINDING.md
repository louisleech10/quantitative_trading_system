# 主委自產發現（待併入 R10 收斂）

task-id: 20260911-SPLITUNIFY-X-REVIEW-R10；family: chair(claude)；findings-round: R10
性質：**主委自查**，非委員交件；不進 `reconcile_build` 之 sources，僅供 R10 收斂時併入群集表。
產生時點：R10 派工後、兩家交件前。**未改動 `docs/SPLITUNIFY_SPEC.D-001.md`**（避免審查中途變更標的）。

## CLAUDE-R10-P2-01

🔴 **本條已由主委自行降級（P1 → P2）**：初判斷言「會弄紅現行活路徑」，經主委二次實跑**不成立**，見下方「自我更正」。保留本條是因為其**修法建議仍成立且更優**，而非因為原斷言成立。

**斷言**: （本條已由主委自行修正並降級，原斷言之影響面不成立，見下方「自我更正」）R9 寫入 D-001-C2 第 4 點的 attest 判準（以 `_local_ordinals_for_symbol` 之 frame 序結果逐值相等，否則 fail-closed）雖不誤傷現行面板形狀，但**判準本身選錯了不變式**：正確且與面板順序無關的判準是「時間序往返」——`sorted_positions[row_index_local]` 逐值等於 `row_index`。改用它可同時消除潛在誤擋與那條前提條款。

**碼證**: 實跑 `venv/bin/python`，以刻意非時間序之面板呼叫 `split_per_symbol`：

```
frame 順序: [('A', 2), ('B', 1), ('A', 0), ('B', 3)]        # A 之兩列在 frame 內為 t2 在前、t0 在後
A train row_index(全框) = [2]   train_local(時間序) = [0]
  helper(frame 序) 給的 local = [1]                          # 與 train_local 不等
  時間序位置 = [2 0]   往返 sorted_pos[[0]] = [2] == row_index? True
```

三項判定：
1. **現行行為**：`split_per_symbol` 在該面板下**正常完成、不報錯**（`purge_semantic="timedelta"`）。故此形狀是現行綠徑，不是既有錯誤。
2. **helper 不適用**：`momentum/core/contracts.py:504-519` 之 `_local_ordinals_for_symbol` 以 `np.flatnonzero(symbol_arr == symbol)` 取位置，該序為 **frame 序**；而 `split_per_symbol`（`:656`）先 `sort_values(ts_col)` 才呼叫 splitter，故 `train_local` 為 **時間序**。兩者只在「該標的之 frame 序等同時間序」時相等。
3. **面板順序無保證**：`momentum/Analysis/ic_filter_orchestrator.py` 全檔未對面板做 `sort_index`／`sort_values`（僅 `:865` 取唯一時刻排序）；`_cross_sectional_to_split_frame`（`:836-849`）原樣複製索引層；`_with_row_positions`（`ic_split_adapter.py`）以 `np.arange(len(frame))` 標號、不排序；`working_df = features.copy()`（`:2006`／`:2012`）順序由呼叫端給。⇒ 未排序面板在契約上可達。

**來源摘要**: momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；momentum/Analysis/ic_split_adapter.py#c2dd93482826；momentum/Analysis/event_samples/split_projection.py#98ee62905643

4. 🔴 **第二次探針修正了第一次的盲點**（第一次只用單列，剛好躲過順序檢查）：以**單標的、frame 內時間完全反序**之面板重跑——
   ```
   frame 時序: [3, 2, 1, 0]
   producer 建計畫: 成功；train row_index = [3 2]   test row_index = [1 0]
   投影端長度閘: 擋下 => row_index 非嚴格遞增——下游以 row_index[0] 取『最早的列』，反序即算錯
   ```
   `momentum/core/split_preview.py:161-165` 之 `assert_positional_rows(..., require_sorted=True)`（預設值）要求嚴格遞增，而 `split_projection.py:453-458` 未關閉它。⇒ **反序面板之計畫從來就進不了投影端**；但**計畫本身建得出來**，且 IC 自己的消費端（`ic_filter_orchestrator.py:1318`／`:1335`／`:1359-1360`）今日即在使用這類計畫。

**影響／修法判定**: 若照 R9 現行文字實作，見下方「自我更正」。原判之「弄紅既有路徑」**不成立**。修法：把 attest 定義改為與面板順序無關之往返——取該標的之列、**依時刻排序**後得 `sorted_positions`，驗 `sorted_positions[row_index_local]` 逐值等於 `row_index`；`row_index_local` 之語意即「該標的**時間序**內之序號」（與投影端所用之時間序 `feature_index` 同序，故正確）。`_local_ordinals_for_symbol` 僅在「frame 序等同時間序」時可用作等價檢查，**不得**當作 attest 之唯一判準。R9 所寫之「frame 序非時間序 ⇒ fail-closed」應刪除，改為上述往返。

**與 R9 之關係**: 本條**不推翻** `CODEX-R9-P1-01`（深層不可變性）之採納，僅更正我自己對其配套前提條件之處置寫法；亦不推翻該輪第二家所揭露之「排序前提」觀察本身——那個觀察是對的，是我把它的處置寫錯了。

## 🔴 自我更正（主委二次實跑，R10 一家交件後）

初判假設「面板順序無保證 ⇒ 未排序面板可達 ⇒ 新 fail-closed 會誤擋活路徑」。**第三次探針推翻了這個推論鏈的最後一環**：

```
from_product(時間,標的): 標的內 frame 序是否時間遞增 = True    helper == train_local ? [True, True]
打亂:                     標的內 frame 序是否時間遞增 = False   helper == train_local ? [False, False]
```

生產與測試慣例之面板為 `MultiIndex.from_product([timestamps, symbols])`（時間在外層），故**標的內 frame 序必然時間遞增**，helper 與 `train_local` 相等 ⇒ 新 fail-closed **不會**誤擋。只有人為打亂索引才分歧，而該形狀非現行任何綠徑。R10 第一家之必答三獨立得出同一結論，主委實跑複驗一致。

**故原斷言之「影響」面不成立，降級 P2。** 但**修法建議仍成立且更優**，理由與原斷言無關：

1. `_local_ordinals_for_symbol` 驗的是 **frame 序**，而 `row_index_local` 之語意是**時間序**內之序號（`split_per_symbol:657` 先 `sort_values(ts_col)` 才呼叫 splitter）。以 frame 序判準驗時間序語意，是**用錯不變式**——它在今日碰巧相等，不代表判準正確。
2. 時間序往返 `sorted_positions[row_index_local] == row_index` 在**兩種面板形狀下皆正確**：排序面板下與 helper 等價，未排序面板下仍能驗出真正的寫入錯誤，且不誤擋。
3. 改用它之後，R9 那條「frame 序非時間序 ⇒ fail-closed」前提條款**可整條刪除**，規格更短且少一個實作者必須記住的例外。

**處置建議**: R10 收斂時把 C2 第 4 點之 attest 判準改為時間序往返，刪除前提條款與 `M-SU-D1-15`，改立「往返不成立時應紅」之變異。

**待辦**: 待第二家交件後一併收斂；若其必答三另有反證，以碼證為準。
