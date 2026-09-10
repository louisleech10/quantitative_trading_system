# SPLITUNIFY B2b code review（R1）

brief-kind: review
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`，結尾附 **Verdict**。
**禁改碼**；碼證以檔案:行號指名。

## 審查對象（commit `864efeb9`）

- `momentum/Analysis/event_samples/split_projection.py`（**新**）——
  `derive_event_split_from_plans`、`build_event_keys`、`_index_as_ms`、`_build_summary`。
- `momentum/Analysis/event_samples/event_split.py`——抽出
  `time_cluster_bucket_ms` ＋ `build_time_clusters`，`split_events` 改呼叫（行為應不變）。
- `tests/momentum/Analysis/test_splitunify_derive.py`（**新**，24 條）。
- `handoffs/20260911-splitunify-b2b-mutate.py`（**新**，mutation 自證）。

規格：`docs/SPLITUNIFY_SPEC.md`（v5）C-2／C-3／C-4／C-5＋Task 2.2；
凍結鏈：`docs/GAP3_EVENT_SPEC_AMENDMENTS.md` A-2（答案窗 purge 之條件式）。

## 主委已跑的驗收（請複驗，別照抄）

- `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py` → **24 passed**。
- `venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → **UNCOVERED=0**
  （9 條 mutation 全 rc=1、對照組 C0 rc=0）。
- 回歸：`tests/momentum/event_samples` ＋ `tests/momentum/core` ＋ 兩支 splitunify 測試
  → **652 passed**。
- `bash scripts/check_decoupling.sh` → `R2=1 R3=17 R4=3`，逐值等於 `scripts/decouple_baseline.txt`。
- 跑完已 `bash scripts/restore_golden_inventory.sh`。

## 🔴 主委自承的兩件事（請當作**已知起點**，不必重新發現，但請驗我修對了沒）

1. **`build_time_clusters` 第一版是「複製」不是「抽出」**——我在 `split_projection.py` 又寫了
   一份分簇邏輯，那就是兩份算術（正是本票要消滅的形態）。自查後改成從 `event_split.py`
   抽出、兩邊**共同呼叫**。請驗：`split_events` 的行為真的逐值不變嗎？
2. **mutation 第一輪有 3 條沒抓到**（`M-SU-4`／`M-SU-6`／`M-SU-7`），是**我的測試設計不夠**：
   連續 rows 上「區間 vs 集合」等價、防呆分支在正常輸入下走不到、每事件各自成簇時權重恆 1。
   三個 fixture 改過才全紅。請驗：改後的 fixture 是不是真的能分辨，還是我只是換了一個
   剛好會紅的寫法？

## 🔴 必答

1. **兩段式判定的實作是否忠實於契約**？逐行對 `GAP3_EVENT_SPEC_AMENDMENTS.md` A-2 的
   code fence 與 SPEC C-4。特別是：`>=` 有沒有被寫成 `>`？第一段是不是**只**作用在
   train 側？`test_rows` 為空是不是在**比較之前**就 raise？
2. **有沒有第二份算術漏網**？`split_projection.py` 裡還有哪一段是「自己算」而不是
   「呼叫既有唯一實作」？（`_index_as_ms` vs `split_preview._as_ms` 是兩支——這算不算？
   請給立場。）
3. **`build_event_keys` 的 keyed join 真的擋得住 positional 錯位嗎**？
   `merge(..., validate="1:1")` 夠不夠？`event_level` 若本身有重複 `event_id` 會怎樣？
4. **`_build_summary` 的 12 鍵語意對不對**？特別是
   `insufficient_events_in_test`（我用「投影後 test 數 < tier_min_test_events 就把所有
   symbol 都列進去」，這對嗎？舊實作是逐 symbol 判定）與 `avg_cluster_size` 的分母。
5. **`event_split.py` 的抽出有沒有改到行為**？`bucket` 這個區域變數現在算了兩次
   （`time_cluster_bucket_ms` 在 `split_events` 與 `build_time_clusters` 內各一次），
   有沒有可能不一致？有沒有效能疑慮（10k 事件級）？
6. **mutation 表夠不夠**？現有 9 條（`M-SU-1`..`7`、`12`、`13`）。
   請補你認為缺的，每條寫「改壞哪一行 → 哪個測試會紅」。
   特別想聽：有沒有哪一種改壞法會讓**答案窗 purge 只在 fixture 上失效、在真實資料上仍紅**？
7. **可否進 B2c**（golden 五組）？直接回「可以」或「不可以＋ID」。

## 停輪條件

① 必答 1–7 皆有明確立場；② 必答 1／3／5 有具體檔案:行號；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭）；
④ 禁以「三家零 finding」當停輪——零 finding 須走 sentinel 契約。

## 本 brief 之前提（逐條標）

fact-verified: 上方所有數字皆為主委實跑，命令逐字如上。

fact-verified: 舊 purge 條件式為 `label_end_ms > test_start - embargo` → `momentum/Analysis/event_samples/event_split.py:144`（抽出後行號已位移）。

fact-verified: `split_events` 抽出 clusters 後行為逐值不變 → VERIFY:20260910T182032Z-splitunify-clusters-ab
（派工後主委補跑之 A/B 探針 `handoffs/20260911-probe-splitunify-clusters-ab.py`：以 `git show 1be5be3f:`
取出抽出**前**的邏輯，對四種未被既有測試涵蓋的形狀——單 TF 各自成簇／共桶／三筆同時刻／跨標的同桶——
`assert_frame_equal` 全過；混 TF 兩版皆 raise 且訊息相符。`A/B FAILURES=0`。
🔴 本條**原為 assumed**，派工當下我確實沒跑；派工後補跑並升級為 fact-verified，必答 5 因此只剩
「`bucket` 算兩次是否可能不一致」與效能兩問。）

assumed: `_index_as_ms` 與 `split_preview._as_ms` 兩支秒守衛的門檻一致（皆 1e11）不會漂
← 否證觀測：改其中一支的門檻，另一支不會紅。／我跑了：**沒跑**。請正面打（必答 2）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| 10k 事件級的效能（逐 row `to_dict("records")` 迴圈） | 投影成為瓶頸 | cost |
| `event_level` 有重複 `event_id` 時 `validate="1:1"` 的錯誤訊息是否可讀 | 使用者看到 pandas 內部訊息 | cost |
| `insufficient_events_in_test` 之下游消費者是否假設逐 symbol 語意 | 多 symbol 支援後行為改變 | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth。
- 不得跑 `pytest tests/governance`（小時級）；`tests/momentum/Analysis` 全套 17 分鐘，
  非必要別跑。
- 跑完測試請 `bash scripts/restore_golden_inventory.sh`。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句必須是「可進 B2c」或「不可進 B2c：<ID>」）。
