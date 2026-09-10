# SPLITUNIFY B2b — Claude 自產獨立審查（與三家平行）

依 `feedback_claude_own_version`。審查對象＝我自己寫的 B2b（commit `864efeb9`）。
🔴 **本檔之修法一律等三家收斂後才動檔**——他們正在讀這些行號。

---

## CLAUDE-R1-P2-01

**斷言**: 秒守衛的門檻在兩支函式裡是**兩份寫法**——`split_preview` 用具名常數 `_MS_MAGNITUDE_FLOOR = 1e11`、`split_projection._index_as_ms` 用**字面量 `1e11`**。兩者現在數值相同，但沒有任何機制保證它們一起變；改其中一支另一支不會紅。

**碼證**: `momentum/core/split_preview.py:51` `_MS_MAGNITUDE_FLOOR = 1e11`、`:76` 使用之；
`momentum/Analysis/event_samples/split_projection.py:87`
`if values.size and np.all(np.abs(values) < 1e11):`（字面量）。
兩檔各有一條秒守衛測試，但**沒有**任何測試把兩個門檻綁在一起。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#864efeb9c0de

判定：**這是我自己在同一批裡製造的第二份真相源**，形態與本票要消滅的「兩份算術」相同，
只是規模小。修法（三家收斂後套用）：`split_projection` 改
`from momentum.core.split_preview import _MS_MAGNITUDE_FLOOR`（或把它提成公開常數
`MS_MAGNITUDE_FLOOR`），並加一條測試斷言兩支共用同一個值。
這正是我在 brief 必答 2 自己列出來問三家的那條——派工後自查即確認成立。

---

## CLAUDE-R1-P3-02

**斷言**: brief 之 assumed 第 1 條（`split_events` 抽出 clusters 後行為逐值不變）**已由主委實跑證實**，不需三家再花時間；四種 manifest 形狀＋混 TF raise 全數前後一致。

**碼證**: 探針 `handoffs/20260911-probe-splitunify-clusters-ab.py`（以 `git show 1be5be3f:` 取出
抽出**前**的 `_cluster_weight` 與那段逐字邏輯做 A/B），
receipt `handoffs/run_receipts/20260910T181812Z-splitunify-clusters-ab.log`：
單 TF 各自成簇（權重 1.0）／共桶（0.5）／三筆同時刻（1/3）／跨標的同桶（0.5）
四種形狀 `pd.testing.assert_frame_equal` 全過；混 TF 兩版皆 raise `ValueError`
且訊息含「bucket_ms 須顯式指定」。`A/B FAILURES=0`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#864efeb9c0de

⇒ 本條記為**已自證**。既有測試只證明「被測到的形狀」不變，本探針補的是
**沒被既有測試涵蓋**的四種形狀與 raise 路徑——這是「行為不變型重構須 byte 級一致」
（三方數據正確性簽核鐵律）的實作。

---

## 我對必答 4 的自評（先寫下來，之後與三家對照）

`insufficient_events_in_test` 我寫成「投影後 test 總數 < `tier_min_test_events` 就把**所有**
symbol 列進去」，而**舊實作是逐 symbol 判定**（`event_split.py` 之
`n_test = sum(... if r["symbol"] == symbol ...)`）。

我的立場：**在本票的單 symbol fail-closed 前提下兩者等價**（存活路徑恆一個 symbol），
但**語意不同**——日後 per-symbol 支援（殘留 `R-1`）落地時，我這個寫法會變成錯的。
⇒ 傾向現在就改成逐 symbol（即使目前不可觀測），理由是「不要留一個會在未來靜默變錯的實作」。
但這也可能是過早一般化。**請三家給立場**（brief 必答 4）。

---

## Verdict

**可進 B2c**，但 `CLAUDE-R1-P2-01`（兩份門檻）須在本輪收斂時一併修掉——
它現在不會出錯，但它是我在「消滅兩份真相源」的票裡自己種下的第二份真相源。
必答 4 之語意分歧待三家裁定。
