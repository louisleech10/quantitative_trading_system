# FF 產出端兩缺陷 — 定性與修法決策紀錄

**狀態**：定性完成（2026-09-21），**未實作**。
**由來**：使用者逐字「那個bug你跟委員要先確認是真的是bug還是特殊原因才這樣定義，不要直接修掉」
與「那命名缺陷和timeframe缺陷，應該是要修吧 你跟委員先研究是真缺陷看是要怎麼修」。
**收斂檔**：`handoffs/reconcile/20260921-ffdefect-x-consult-r1/synth.md`（codex＋composer 各 5 條，零駁回）。
**本檔性質**：決策紀錄，非 SPEC。兩張實作票各自走完整管線。

---

## 一、缺陷 A — 衍生層欄名未經來源／指標正規化

### A-1 定性：**是真缺陷**（兩家獨立同判）

命名規則明文於 `momentum/FeatureEngineering/atomic/talib_wrapper.py:36-37`：

> `'_' separates major segments, while '-' separates values inside Params.`

`normalize_source_label` 與 `normalize_indicator_name` 皆為 `replace("_", "-")`。

**同一 run、同一指標、同一週期出現兩種名字**（reference run `d9935491…` 實查）：

```
close_12h_statistics_LINEARREG_SLOPE_10_144_Cross    ← L2 pair-op
close_12h_statistics_LINEARREG-SLOPE_10_Lag_1        ← L4 lag
```

**反證條件**（不成立）：需存在版本化契約宣告 raw 與 normalized 是兩個有意義且不需相等之 identity。
實查不存在；且 L4 用正規化名這件事本身否證「衍生層刻意保留 raw」。

### A-2 根因：metadata-hit 分支與 fallback 分支的分叉

**不是**「L2 一律從 raw 重建」（此為主委原判，已被推翻）。實測 taker 族各家族之來源形式：

| 家族 | 連字號來源 | 底線來源 |
|---|---|---|
| Distance | 272 | 0 |
| Momentum | 8,700 | 0 |
| Abs | 870 | 0 |
| TsRank | 2,610 | 0 |
| **Cross** | **0** | **1,194** |
| **Ratio** | **0** | **1,194** |
| Lag | 6,960 | 16 |

鏈：
1. `momentum/FeatureEngineering/atomic/momentum_indicators.py:85-97`（其餘五個 atomic 同形）——
   **欄名用 normalized、metadata 存 raw**。
2. `momentum/FeatureEngineering/feature_factory.py:4020-4024`——把 metadata 之 raw 抄進 `indicator_specs`。
3. `momentum/FeatureEngineering/operators/derived_operators.py:816-831`——
   **metadata-hit 分支**取 raw；**fallback 分支** `:833-851` 從已正規化欄名 parse ⇒ 分叉點在此。
4. `momentum/FeatureEngineering/operators/derived_operators.py:303-306` 與 pandas 路徑 `:549-552`——
   以 raw 組出 `col_name`。

**週期標記器不是缺陷**：本 run 走 CGSA，標記器為
`momentum/FeatureEngineering/feature_storage.py:862-873`（註解逐字「CGSA mode skips `_apply_timeframe_tag`」），
它對合規名之行為正確；歪掉的是它收到的輸入。
`momentum/FeatureEngineering/feature_factory.py:3803-3808` 與
`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1645-1651` 為 legacy 路徑，
**本 run 不走**——修它對本 run 零效果且測不出來。

### A-3 影響範圍（reference run 全量實跑）

| 段 | 欄數 |
|---|---|
| 來源段（`taker_ratio` 之 raw 名含底線） | 2,404 |
| 指標段（14 個指標，如 `LINEARREG-SLOPE`／`BBANDS-Upper`／`MINUS-DM`） | 1,604 |
| 交集 | 412 |
| **聯集** | **3,596 / 418,719 ＝ 0.859%** |

落點 group：`{1h,12h}_L2_Cross`、`{1h,12h}_L2_Ratio`、`12h_L4_lag_{1,2,3}`。

### A-4 修法：只改衍生層造名邊界

在 `momentum/FeatureEngineering/operators/derived_operators.py:303-306` 與 `:549-552` 之造名處，
對來源與指標套既有之 `normalize_source_label`／`normalize_indicator_name`。

**不得改 `FeatureInfo.source` 本身，也不得改 atomic metadata。** 三條獨立證據：

1. `info.source` 是查 kline 欄名之鍵。kline dataset 實查欄名為
   `timestamp/open/high/low/close/volume/taker_buy_volume/taker_ratio/quote_volume/number_of_trades`
   ——只有 `taker_ratio`（底線），**無** `taker-ratio` ⇒ 正規化後查不到，Distance 272 欄整族消失。
2. entropy 之來源含 `close_return` 字面，正規化會變成 `close-return` 而走錯分支。
3. `api/services/ic_analysis_service.py:2472` 之
   `meta_item.get("data_source") or meta_item.get("source")` 把 raw source 當 `data_source` **回給前端**。

### A-5 相容性：**只對新 run 生效**（採 A）

兩家皆建議此選項。主委判定此題**已由使用者既有裁定涵蓋**——2026-08-05 定死之
「面向未來不溯及既往：修正只考慮以後，不把舊錯誤／不合規／麻煩包回來，不管舊文件與舊資料格式」。

| 選項 | 與該裁定 | 實測成本 |
|---|---|---|
| **A 只對新 run** | **正是它** | 改造名 ＋ 以既有 `scripts/freeze_batch2d_baseline.py` 重簽 baseline |
| B 對照表 | 「把舊麻煩包回來」；且對照表本身成為第三份要同步的事實（即本缺陷之病根） | 須維護 3,596 筆映射並讓所有消費端接別名 |
| C 全部重跑 | 「溯及既往」 | 41 GB、18 個 run；單次 run 實測約 2 小時 |
| D 雙寫兩套欄名 | 撞 CLAUDE.md「未經批准不得改輸出大小」 | — |

**機械防護**：manifest 記 `naming_version`，跨世代比較 fail-closed。
先例＝現有 `schema_version: "raw_v2"` 與 `version: "l7_v2"` 之字串版本標記。

**須重簽之 golden**（皆在 git 追蹤內，共 146 MB）：
`tests/_golden/batch2d/control.json`（3,096 處）、`cgsa_baseline.json`（3,096）、`provenance.json`（2,872）。

---

## 二、缺陷 B — 同一 run 之 `present_timeframes` 兩個值

### B-1 定性：**是真缺陷**（兩家獨立同判）

reference run 實查：

```
feature_manifest.json → present_timeframes = ["1h"]，expected_timeframes = ["1h"]，
                        failed_timeframes = []，quality_status = "complete"
task_record.json      → metadata.present_timeframes = ["1h","12h"]
                        metadata.config_used.timeframes.training = ["1h","12h"]
                        metadata.skipped_timeframes = []
groups                → gid 前綴 1h 542 個 / 12h 402 個（209,235 欄）
```

**系統性而非個案**：全掃 18 個 run，4 個多週期 run（`4a8a0b37…` 於 BCH／BTC／ETH 三 symbol、
加 reference）之 manifest 皆只宣告主週期；單週期 run 之 manifest 正確。

**反證條件**（不成立）：需版本化 schema 明訂 manifest 該欄僅代表 primary artifact row grid、
而 task-record 同名欄代表 training inputs。實查反面證據——
`docs/FF_FAILOPEN_FROZEN_TESTS.md` 逐字記載 `result.metadata["actual_timeframes"]` **改名**為
`present_timeframes`「對齊 manifest 語彙」⇒ 是刻意對齊，不是碰巧同名。

### B-2 根因：整條 completeness 鏈型別上只接一個週期

`momentum/FeatureEngineering/feature_storage.py:556-600` 之
`build_completeness_meta_from_layer_results(layer_results, *, timeframe: str)` 只收純量並硬寫
`expected_timeframes: [timeframe]`／`present_timeframes: [timeframe]`。

writer chain：`feature_storage.py:1171-1195`（registry-stream 路徑）與 `:1298-1301`（一般 L7 writer）
→ `:1810-1812` 放入 artifact → `:1842-1847` 複製到 manifest root。
呼叫端 `feature_factory.py:3226-3240` 與 `:3271-3274` 皆傳 primary `timeframe`。

多週期之正確值只存在於 `momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1409-1412`
之 `_present_timeframes()`，經 `result.metadata` 流向
`api/services/feature_factory_service.py:4264-4279` 寫入 `task_record.json`，**從未進入 manifest**。

🔴 **`_apply_failed_timeframe_metadata`（`multi_tf_generator.py:1474-1481`）開頭即
`if not failed_timeframes: return`** ⇒ 週期資訊只有在**有週期失敗時**才寫得完整；
全部成功時反而是錯的。這解釋了為何 reference run 同時標 `complete` 卻漏掉一半資料。

### B-3 嚴重度：**latent**（已寫錯但尚未害到人）

三方獨立 grep 一致：`momentum/` 與 `api/` 生產碼對該三個鍵**零消費者**；
命中全在 FF 自己的測試與 profile 腳本，且**無任何** `present_timeframes[0]` 或 `len==1` 之假設。
EVENTSCAN 會是第一個真實消費者——這正是它被挖出來的原因。
⇒ 修法風險低：沒有生產端依賴現值。

### B-4 修法：由 MultiTF producer 形成 canonical completeness object

契約：
- `expected = ordered(training_tfs)`
- `present = expected − skipped/failed`
- `failed ⊆ expected`
- `expected = present ∪ failed`
- complete 時 `failed = []` 且 `present == expected`

同一個 object 同時餵 manifest 與 task record；**不得**在 storage 端由 primary `tf` 猜多週期集合，
**不得**在 manifest 寫完後只 patch metadata。
`expected_timeframes` **必須一併改**，否則 present 變多元素而 expected 仍單元素即為新的自相矛盾。

🔴 **產出端不變式之權威來源（codex 修正，已採納；它同時修正主委與 composer）**：
canonical 來源＝**ordered training config 與 skip／failure 集合**。
`groups` 之 gid 前綴**只作 diagnostic cross-check**（不等即報警／fail-closed），
**不得**成為 canonical authority——group id 是不透明鍵、不是可靠的 timeframe schema 欄位，
把它當語義欄位即重蹈本專案已被推翻兩次的「靠解析名字」形態。
`task_record` 同名欄在有該檔時亦須相等。

驗收須覆蓋健康多 TF／skip／failed／單 TF 四種情況。

**相容性**：只對新 run 生效；舊 artifact 依既有 task-record authority 使用，**不回填**。

---

## 三、分票與優先序

**兩張票，不併入 FFDSTAR**（兩家獨立同判）：

| 票 | 內容 | 順序 | 理由 |
|---|---|---|---|
| **FF-TFMETA** | 缺陷 B | **先** | 不改欄名、無生產端消費者、風險低；EVENTSCAN 可立刻少一個 workaround |
| **FF-NAME** | 缺陷 A | 後 | 改欄名、相容成本高，須先完成 B 之驗收面 |

不併入 `FFDSTAR`：其 §RISK 明文「不改任何數值」且升級訊號①＝改 `feature_manifest.json` schema；
A 改欄名索引鍵、B 改 completeness 值，皆與 FFDSTAR「只加 d\* 收據、run 目錄檔案集合不變」正交。
FFDSTAR 只 cross-link 追蹤。

🔴 **主委原主張「A 與 B 同源故應一併加產出端不變式」被兩家部分推翻**：
檢查可同層掛（persist 邊界），但實作票不該綁——producer、identity、rollback 與驗收面皆不同。

---

## 四、實作時的兩條保留意見（codex 提、已採納）

1. **不宜為修命名讓 `derived_operators` 直接 import atomic TALib wrapper**（跨層耦合）。
   應把 canonical formatter 放在既有共用層，或由 caller 傳入已正規化之 identity。
2. **`close_..._Cross` 對 `close_..._Lag_1` 之例子不足以單獨證明「數值是同一特徵」**——
   兩字面帶不同 operator 與參數。**定性不依賴該等同**：同一 canonical source/indicator
   在已明定 normalization 之規則下跨分支混用，本身即足以證明 identity contract 破壞。
   主委之 `corr = 0.999994` 屬另一組配對（`taker-ratio` 之 CMO_13／CMO_144 之 Cross），
   codex 本輪未重跑，視為主委新增佐證而非其獨立驗證。

## 五、本輪之流程事故（主委端）

主委在 codex 進程仍存活時讀取其稿並據以建 `sources.lock`，鎖到尚未寫完必答 8 的骨架版，
因而在收斂檔寫下一條不成立的斷言。處置＝依 `HANDOFF.md` 坑段之機械流程
移開整個 session 目錄、以最終交件重建；現行收斂檔為重建後版本，codex 之必答 8 完整。

**判準**：委員進程仍存活時**不得**視為交件完成；`committee_run` 之收尾才是交件信號，
**檔案存在不是**。

## 六、FF-TFMETA 收案殘留（2026-09-24 收批，實作 `cb53ff19`＋審碼修補 `afa1f4bd`）

- 殘留：既有 18 個 run 之 manifest 不回填 — `為何現在不做: user-ruling:2026-08-05 面向未來不溯及既往`；觸發：無（舊 run 依 task-record authority 使用）。
- 殘留：CGSA 路徑之 L6.5 預處理失敗未進 completeness — `為何現在不做: needs-research:CGSA 串流於 manifest 合併前，哪一個已產生之 run 級信號代表 preprocessing 失敗（_preprocessing_applied 只於 frame 路徑設定，CGSA 兩路徑不經 _execute_l65_with_degradation）`；觸發：研究得出信號後另立票。
- 待辦：grok 復役後自行重驗其 SPEC 審查第 3 輪所提兩條 P1（本期由 codex 同等重跑閉合）— `為何現在不做: blocked-by:grok 帳戶額度用完（402），委員名冊 active_stampers 暫無 grok`。
