# SPLITUNIFY b8 — `M-SU-D1-01`～`23` mutation 自證收據

日期：2026-09-12｜票：`20260911-SPLITUNIFY/b8`｜執行者：主委（Claude）

## 方法

逐條：改壞生產碼 → 只跑該條指定的測試群 → **期望 rc != 0** → `git checkout --` 還原。
腳本為一次性檔（放 session scratchpad，不進 repo），紀律寫死在腳本內：

- 錨點字串找不到 ⇒ 記 `ANCHOR-MISS` 並列入未通過，**不得**靜默當成通過；
- 替換後內容若未改變 ⇒ 記 `NO-CHANGE`，同樣列入未通過；
- `try/finally` 確保任何情況都還原；
- 執行前檢查生產碼工作區乾淨，否則拒絕執行（避免還原吃掉未提交的改動）。

## 結果：22 條執行、22 條 CAUGHT；1 條（23）在現行 fixture 下不可觸發

| ID | 改壞什麼 | 結果 |
|---|---|---|
| 01 | per-symbol 合併只取第一個 symbol | CAUGHT |
| 02 | 把「跨 symbol hash 必互異」加成閘 | CAUGHT |
| 03 | `single_symbol` 解除條件改為無條件解除 | CAUGHT |
| 04 | 指紋比對只比首尾 | CAUGHT |
| 05 | 缺指紋欄時放行 | CAUGHT |
| 06 | 門檻判定退回整批 `n_test` | CAUGHT |
| 07 | 跨 symbol 混用 `feature_index` | CAUGHT |
| 08 | 指紋列改用 `list[dict]` | CAUGHT（驗收＝`freeze_splitunify_golden.py`，見下） |
| 09 | 映不到就丟棄（不 fail-closed） | CAUGHT（**補測試後**，見下） |
| 10 | 成員判定改回以全框 `row_index` 索引 | CAUGHT |
| 11 | attest 不等就以寫入值為準 | CAUGHT |
| 12 | `derive` 缺 `row_index_local` 時回退 | CAUGHT |
| 13 | 建構時不複製 row 陣列 | CAUGHT |
| 14 | 不設唯讀（允許原地改寫） | CAUGHT |
| 15 | attest 判準改 frame 序 | CAUGHT |
| 16 | 投影入口略過指紋重算 | CAUGHT |
| 17 | 以 `setflags(write=False)` 取代不可變 buffer | CAUGHT |
| 18 | attest 略過負值前置閘 | CAUGHT |
| 19 | 投影入口把 `require_sorted` 關掉 | CAUGHT（**修正斷言後**，見下） |
| 20 | 移除遞增閘（改 `assert_positional_rows` 預設值） | CAUGHT（同上） |
| 21 | 往返比對省略等長前置（zip 語意） | CAUGHT |
| 22 | 接受非整數型序號 | CAUGHT |
| 23 | oracle 改用 `row_index` 重算 | **不可觸發**，見下 |

## 首輪 4 條未被抓到，逐條處置（全部是真問題，沒有一條靠改 mutation 定義蒙混）

**08**：`-k fingerprint` 永遠抓不到它。producer 與 consumer 共用同一支
`build_row_time_fingerprint`，兩端同時改形狀 ⇒ 兩邊仍相等。這是**我的驗收命令給錯**：
真正能抓的是 `scripts/freeze_splitunify_golden.py`，它拿凍結的 digest 比對重算值。改用它之後 CAUGHT。

**09**：`feature_index_by_symbol` 缺某個 symbol 時把 `raise` 改成 `continue`（該標的事件靜默消失），
**整批測試一條都不會紅**——真的沒有任何測試覆蓋。已補
`test_per_symbol_missing_feature_index_entry_is_fail_closed`，補後 CAUGHT。

**19／20**：暴露出我自己寫的
`test_fingerprint_reordered_rows_are_caught_by_monotonic_gate` **沒有鑑別力**。
重排會讓首列時刻跟著變，於是 `time_bounds` 同源閘先擋下並丟出同一種 `ValueError`，
而我只寫了 `pytest.raises(ValueError)` 沒限定訊息 ⇒ 把遞增閘整個拿掉它照樣通過。
已改為 `match="非嚴格遞增"`，指名是哪一道閘擋的，補後 CAUGHT。
🔴 這條與該測試檔開頭寫的紀律同源（`CrossSymbolLeakageError` 繼承 `ValueError`，
不限定就分不出是哪道閘）——我寫下紀律，卻在另一個檔案犯了同一個病。

## 23 的誠實邊界（具名殘留，不是通過）

`M-SU-D1-23` 要求「golden 的獨立 oracle 改用 `row_index` 重算 ⇒ 應永遠不等 ⇒ 應紅」。
但 golden fixture 是**單標的**，其 `row_index_local` 由 `b["test_row_index"]` 直接指派、
與 `row_index` **逐值相同**（碼證：`scripts/freeze_splitunify_golden.py` 的 `_plans`），
所以這條 mutation 改了等於沒改，**在現行 fixture 下不可觸發**。

處置：不宣稱通過。要讓它有鑑別力，golden fixture 必須改成兩標的交錯（那會移動既有
golden digest，屬於重凍範圍）。歸類＝`needs-research`（是否值得為單一 mutation 重凍 golden，
交 b8 審碼三家裁定）。

## 可複現

腳本路徑（session scratchpad，非 repo 檔）：`mutate.py`，用法 `venv/bin/python mutate.py [ID…]`。
不帶參數＝全跑；帶 ID＝只跑指定條目。
