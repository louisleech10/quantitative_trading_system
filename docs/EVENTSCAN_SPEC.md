# EVENTSCAN — 條件掃描 → 持有 N 根報酬 vs 隨機對照報酬 — SPEC

> 來源方向書：`白話說明/EVENTSCAN方向與做法.md`　|　日期：2026-09-21　|　對應 TODO：`docs/EVENTSCAN_TODO.md`（本 SPEC 凍結後生成）
>
> 委員收斂檔（本 SPEC 之輸入事實）：`handoffs/reconcile/20260920-eventscan-x-consult-r1/synth.md`（十一條）、
> `handoffs/reconcile/20260920-eventscan-x-consult-r2/synth.md`（十四條）。
>
> **回答的問題（使用者原話）**：條件成立時買入、持有 N 期的報酬，跟隨機買入持有同期比較。單標的先做。

---

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大。
- **命中高風險原則**：
  - **(a) 數值/資料品質** — 報酬公式、加權統計量、抽樣配額、bootstrap 區間皆為使用者直接讀的數值。
  - **(b) 跨模組/共用路徑** — 動 `momentum/Analysis/event_samples/`（條件引擎／產生器／對齊／報酬表／隨機對照）、
    `api/services/ic_analysis_service.py`、`api/routes/ic_analysis.py`、`frontend/src/components/ic-analysis/`，
    五處皆有既有 IC 事件路徑之 caller。
  - **(d) ML/回測正確性** — 事件 label 決定隔離區寬度與隨機候選資格；時鐘定義錯一根即為 look-ahead。
- RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ **§G Golden 必填、adversarial review 必跑**。

### 本票之 fact-key 政策（使用者 2026-09-21 裁定，代號 B）

本 SPEC 內凡「會被 TODO／測試／白話再抄一次的**值**」，一律以 `scripts/fact_keys.json` 之生成區塊承載，
**不在本檔任何段落手打第二次**。本 SPEC 註冊之 key 見 §K。
引用某個值時**只寫 key 名與列序**（例：`eventscan-clock` 030），不得複述其內容。

🔴 **誠實邊界（使用者 2026-09-21 逐字）**：B 只管**可列舉的值**，**不管架構對不對、零件怎麼接、為什麼這樣設計**。
同一份文件內的前後矛盾與論述寫錯，外部無解、本專案亦無解，只能靠兩家對抗審且**會漏**。
🔴 **已知洞**：手寫偵測之 `status_scope` 不含 `docs/` 其餘檔 ⇒ 本檔貼了標記的格會同步，
但**在本檔別的段落手打同一個值不會被機器擋**——這一點只能靠審查。

---

## §A 假設與待使用者確認

### 已驗證事實（FACT-RECEIPT；每條均為本 SPEC 之設計前提）

- FACT-RECEIPT: `grep -n "def _weighted_stats" -A 16 momentum/Analysis/event_samples/tables.py` → 印出 `:118` 起之函式，
  回傳鍵恰為 `mean`／`median`／`win_rate`／`n`／`n_effective`，**無** `std`、`min`、`max`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "win_rate" momentum/Analysis/event_samples/tables.py` → 印出 `:128 "win_rate": float(np.sum((values > 0) * w))`
  ⇒ 勝率直接由 `ret_entry` 正負算，**不讀 `label`**（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `sed -n '95,112p' momentum/Analysis/event_samples/alignment.py` → 印出 `_entry_mapping`；
  `next_open` ⇒ 回 `(t0_idx + 1, "open")`，`t0_idx + 1 >= len(anchor)` ⇒ `raise _EventFailure("missing_bar")`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `sed -n '236,246p' momentum/Analysis/event_samples/tables.py` → 印出 `exit_idx = entry_idx + h`、
  `if exit_idx >= len(bars): continue  # horizon 超出資料：該格排除（n 反映），不灌 0`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "close\[i + horizon\]" momentum/Analysis/event_samples/all_bars_eval.py` → 印出
  `:93` 與 `:185 hold = sign * (close[i + horizon] - entry) / entry` ⇒ 全 K 線表之出場錨為 t0，與報酬表差一根（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n '"ci": "unavailable"' momentum/Analysis/event_samples/tables.py` → 印出 `:272`，
  `event_split_plan is None` 時 `ci` 為**字面字串** `"unavailable"`（非帶 NaN 之物件）（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "unregistered_column" momentum/Analysis/event_samples/condition_engine.py` → 印出
  `:156 raise ConditionError("unregistered_column", col)`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "return False" momentum/DataExtraction/case_search_engine.py` → 印出 `:63 :70 :95 :98 :102`
  ⇒ `/search` 路徑之 `FilterCondition.evaluate` 缺欄時靜默回 `False`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "n_target = min" momentum/Analysis/event_samples/random_control.py` → 印出
  `:393 n_target = min(n_requested, candidate_count)`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "ALLOCATION_PROPORTIONAL" momentum/Analysis/event_samples/random_control.py` → 印出
  `:67 ALLOCATION_PROPORTIONAL = "proportional_to_candidates"`；`_allocate` 於 `:188`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "nRequested: 100" frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx` → 印出
  `:206 nRequested: 100, seed: 20260905, neighborhoodBars: 2, embargoBars: 6, threshold: 0.02,`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `sed -n '1040,1042p' api/services/ic_analysis_service.py` → 印出身分 tuple＝
  `(threshold, horizon_bars, direction, label_return_mode)`，**不含** `entry_price_semantic`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "breakeven" momentum/Analysis/net_ic_analyzer.py` → 印出
  `:83 breakeven = mean(gross)/mean(turnover)*10000;mean(turnover)==0 → unavailable`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "weights = \[1.0 / c" momentum/Analysis/event_samples/dedupe.py` → 印出 `:99`；
  `:110 "uniqueness_weight": weights`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `grep -n "features/list" api/routes/ic_analysis.py` → 印出
  `:344 @router.get("/features/list", response_model=FeatureListResponse)`（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `jq -r '.required_fields | keys' momentum/Analysis/contracts/event_import_contract.json` → 印出含
  `event_id`／`symbol`／`timeframe`／`t0`／`decision_offset_bars`／`entry_price_semantic` 等必填欄（Claude 實跑 2026-09-21）

### 🔴 對方向書之一處更正（本 SPEC 以更正後為準）

方向書 §四「缺口 2」寫「**現在寫錯欄名不會報錯**——找不到該欄時條件直接判『不成立』」。
逐一對證後：**該行為屬 `momentum/DataExtraction/case_search_engine.py` 之 `/search` 路徑**，
而本票之條件求值走 `momentum/Analysis/event_samples/condition_engine.py`，其 `parse_condition`
對未註冊欄**已 loud 拒**（`unregistered_column`，FACT-RECEIPT 見上）。

⇒ 缺口 2 之真實內容是**兩件**，不是一件：
① **無人把 FF 欄位註冊給條件引擎**（`column_registry` 目前不含 FF 欄）⇒ 合法 FF 欄名一樣被判 `unregistered_column`；
② **拒收訊息沒有「最接近欄名」建議**，使用者分不清「打錯字」與「這個 run 沒有這個指標」。
本 SPEC 之 Task 1.1／1.2 分別對應。**不需要「把靜默改成報錯」——那條在本票路徑上不存在。**

### 🔴 R5 揭露之前提崩塌：**舊** reference run（`4a8a0b37…`）之特徵欄已被轉換，跨週期不可比

委員 R5 實測「`close_1h_trend_EMA_5 > close_1h_trend_EMA_10` 在 reference run 上只有 1 段」，
主委追查真因並逐項實跑對證，結果推翻本票（與方向書）之一個核心前提。

- FACT-RECEIPT: `PYTHONPATH=. venv/bin/python <probe>` 以真實 kline 重算 EMA 並與落檔欄比對 →
  印出 `EMA_200 corr(落檔,未轉換EMA)=1.0000`、`EMA_5 corr=0.9102`、`EMA_55 corr=-0.0080`
  ⇒ 短週期欄已被轉換、`EMA_200`／`EMA_233` 未被轉換（Claude 實跑 2026-09-21）
- 🔴 **主委原列之「`d*` 紀錄與實際套用不一致」兩條 FACT-RECEIPT 已由 FFDSTAR 定性輪推翻**：
  主委所讀之 `data_cache/feature_preprocessing/d_star_ETHUSDT_1h_dcc154ced6b6.json`
  **不是** reference run 之收據（其 `row_count=10441` 屬另一 run，本 run 為 20352 列；
  該快取檔跨 run 共用且會被後寫覆蓋）。以它與本 run 之 parquet 配對所得之結論不成立。
  逐型定性見 `handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md`：
  **`EMA_200`／`EMA_233` 未被轉換是 `apply_to="non_stationary"` 之 ADF 設計路徑**
  （委員以本 run 之 20352 列校準窗實跑，判其平穩故不進 fracdiff），不是缺陷。
- FACT-RECEIPT: 委員以本 run 校準窗實跑 `_get_non_stationary_columns` → 名單含 `EMA_5..144`、
  **不含** `EMA_200`／`EMA_233`；落檔之 `EMA_50`／`55`／`89`／`100`／`144` 與
  `_frac_diff_ffd(d=1.0)` 相關 `1.0000`（composer 實跑 2026-09-21）
- FACT-RECEIPT: `jq` 掃 `data_cache/features/*/*/*/feature_manifest.json` → 印出 14 個可用 run
  **全部** `fracdiff=True winsor=True`（Claude 實跑 2026-09-21）

⇒ **方向書給使用者看的例題在本資料上無意義**：兩欄量綱不同，條件恆為真、命中 100%、不分段。
⇒ **本票之「條件掃描」前提（FF 欄彼此可直接比較）在當時已存在之任何 run 上皆不成立**（其後由新 run 修復，見下節）。

**使用者 2026-09-21 裁定**：由主委重跑一個**關閉 `winsorization` 與 `fractional_differencing`** 的 FF run
供本票使用；另就 `d*` 快取之可追溯性**另立票**；🔴 使用者同日補充裁定「先跟委員確認是真的是 bug 還是特殊原因才這樣定義，不要直接修掉」⇒ 定性輪已跑完，結論見 §N 之 RESID-10（主委原判大部分不成立）。

### ✅ 前提已修復（2026-09-21，新 run 產生並實測通過）

- FACT-RECEIPT: `POST /api/v1/features/generate`（`winsorization=false`、`fractional_differencing=false`、
  `timeframes.training=["1h","12h"]`）→ 新 run `config_hash = d9935491cea49e8cada481a8bf9487d6`，
  規模見 `eventscan-column-selector` 100；manifest 之 `raw_artifact_applied.steps` 六項全為 `false`
  （Claude 實跑 2026-09-21）。🔴 **本段不重述規模數字**——R7 指出主委在同一份 SPEC 之
  第 26–28 行寫下「不得手打會被再抄的值」，卻在本段手打 `418,719`／`944`／`20,352`。
- 🔴 **第一次重跑（`654bd63b…`）不可用，但仍在磁碟上**：該次請求漏給 `timeframes.training`，
  產出之 542 個 group **全為 `1h`、零個 `12h`**（R6 委員抓出）。**它與現行 reference 外觀相似
  （同為未轉換），誤用風險高** ⇒ 任何引用 reference 之處皆須核對 `config_hash`。
  本票**不刪該 run**（刪除為破壞性動作，須使用者裁示）。
- FACT-RECEIPT: 以真實 kline 重算 EMA 與新 run 落檔欄比對 → **14 個 EMA 欄之
  `corr(落檔, 未轉換EMA)` 全部為 `1.0000`**，且值域回到價格尺度（2296–2328，隨週期遞增）
  （Claude 實跑 2026-09-21）
- FACT-RECEIPT: 新 run 上 `EMA_5 > EMA_10` 與多頭排列 `EMA_5 > EMA_10 > EMA_34` 之命中率與段數
  見 `eventscan-clock` 075（舊 run 同條件為 100% 命中、1 段）（Claude 實跑 2026-09-21）

⇒ **「FF 欄可直接互比」之前提在新 run 上成立**，凍結之硬前置已解除。
⇒ `eventscan-golden-reference` 之 reference 設定與 `eventscan-column-selector` 之規模數字
**已改指新 run**；`eventscan-pit-admission` 之實查數字亦已依新 run 全量重取。
🔴 **PIT 准入不因此廢除**——它防的是「欄內含未來資訊」，與 fracdiff 造成的「量綱不可比」
是兩件事；新 run 只解決後者。
🔴 **舊 run `4a8a0b37…` 不得再用於本票**（其預處理使跨週期欄不可比）。

### 待使用者確認

`待確認：無`（2026-09-21 裁定已取得：重跑 FF 由主委執行；`d*` 快取可追溯性**另立票且已完成定性**，見 §N 之 RESID-10）

### 已確認結果

- `2026-09-20 使用者九項裁定`（逐條見 `eventscan-rulings`）。
- `2026-09-21 使用者裁定：寫 SPEC 時同步建 B，不另立票、不新建工具、不延後 SPEC`（`eventscan-rulings` 090）。
- `2026-09-21 使用者裁定：本 session 只寫 SPEC，不實作`。

---

## §C 約束

- **解耦 7 條**：`momentum/` 不得 import `api/`；跨域走 Protocol；服務經 factories；服務不互 import；
  設定單一來源；`pytest tests/momentum/` 可獨立跑；DTO 不跨界。
- **不可違反之原則**：不得弱化 NaN／inf 閘；不得未經核可改輸出大小；多標的切片禁 positional index。
- **不得改 `momentum/Analysis/contracts/event_import_contract.json` 之 `required_fields`**——
  方向書已定：label 由系統導出即滿足契約，改契約是不必要的擴散。
- **不得在掃描批內混入隨機列**——程式碼註解已明文擋死（對照組混入條件樣本，分母不再是無條件基準）。
- **資料源限 Feature Factory run**，系統不自行再算任何指標（`eventscan-rulings` 020）。
- **驗證一律用真實 kline** `data_cache/feature_klines/kline_cache.h5`；**禁合成 fixture**。
- **本任務會踩的共用路徑與既有消費者**：
  `event_forward_return_table` 同時服務 IC 事件路徑與本票；`sample_random_bars` 同時服務既有隨機對照 UI；
  `condition_engine.parse_condition` 同時服務既有事件產生器。**三者皆不得改變既有呼叫端之既有行為**，
  新行為一律以新參數／新鍵承載，缺省等同現況。

> **資料結構單一真相源**：本 SPEC 不在散文中列舉欄位表／枚舉值／常數值。
> 所有此類值住 `scripts/fact_keys.json`（見 §K）；新增之失敗原因碼另須同步落入
> `momentum/Analysis/contracts/condition_engine_contract.json` 之 `failure_reasons`（Task 1.2）。

---

## §K 本 SPEC 註冊之 fact-key（B 之落地清單）

> 下列每個區塊皆由 `scripts/fact_keys.json` 生成，**禁手改**。
> 改值＝改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`。
> TODO／測試／白話引用同一值時，**掛同一個 key 的區塊**，不得另行手打。

### K-1 使用者裁定

<!-- BEGIN GENERATED: eventscan-rulings -->
| 序 | 裁定 | 日期 |
|---|---|---|
| 010 | 持有期以「根」計算、畫面顯示約多少天；前端直接輸入不用勾選清單；輸入與輸出皆支援多個 | 2026-09-20 |
| 020 | 資料源即 Feature Factory run，FF 有什麼就用什麼；系統不自行再算任何指標 | 2026-09-20 |
| 030 | 完全無門檻設定，畫面不得出現門檻欄位 | 2026-09-20 |
| 040 | 接受以漲跌正負號當內部 label，走既有事件匯入管線以保住未來資料防護 | 2026-09-20 |
| 050 | 進場價用下一根開盤價 next_open | 2026-09-20 |
| 060 | 欄位選擇器＝**逐層下拉＋打字搜尋，兩者都做**（🔴 括號內之層名「來源欄→週期→類別→指標→參數」係主委當時之提案，已由 R7 實證推翻——只涵蓋 0.77%；**使用者所裁定者為「逐層下拉＋搜尋」此一需求，非特定層名**。現行層定義見 `eventscan-column-selector` 020–060） | 2026-09-20 |
| 070 | 成本：報酬主數字不扣，另加成本歸零點欄 | 2026-09-20 |
| 080 | 先做單標的，多標的併 GAP-4 | 2026-09-20 |
| 090 | 寫 SPEC 時同步把可列舉之值改為 fact-key 生成區塊、不手打；不另立票、不新建工具、不延後 SPEC | 2026-09-21 |
<!-- END GENERATED: eventscan-rulings -->

### K-2 時鐘與進出場定義

<!-- BEGIN GENERATED: eventscan-clock -->
| 序 | 項目 | 規格值 | 依據 |
|---|---|---|---|
| 010 | 進場語意 | `entry_price_semantic = next_open`；進場根＝`t0_idx + 1`，取價欄 `open` | 使用者裁定 050；alignment.py:102-105 |
| 020 | 進場根不存在 | t0 為資料最後一根 ⇒ 該事件以 `missing_bar` 排除，不灌 0 | alignment.py:104 |
| 030 | 持有時鐘 | 自**成交根**起算 N 根：`exit_idx = entry_idx + h` | tables.py:243 |
| 040 | 出場價 | `close[exit_idx]` | tables.py:245 |
| 050 | 資料不足 | `exit_idx >= len(bars)` ⇒ 該（事件, h）格排除、`n` 反映，不灌 0 | tables.py:239-240 |
| 060 | 全 K 線表 | 本票不展示 `evaluate_all_bars` 之 `hold` 欄——其出場錨為 t0（`close[i + horizon]`），與本票時鐘差一根 | all_bars_eval.py:185 |
| 070 | first-of-run | 一段連續成立只取第一根為進場點；每根皆取之版本列為敏感度，不得當主數字 | COMPOSER-R64-P2-01 |
| 075 | 🔴 first-of-run 之實測依據（新 reference run） | `EMA_5 > EMA_10`：命中 9,503／20,343（46.7%）、**956 段**、中位段長 7 根、最長 79 根。多頭排列 `EMA_5 > EMA_10 > EMA_34`：命中 7,107、**671 段**、中位段長 7 根 ⇒ 不壓成段，671 次進場會被算成 7,107 筆 | Claude 實跑 2026-09-21（同條件在舊 run 上為 100% 命中、1 段——見 §A 之前提崩塌段） |
| 080 | label 綁定 | `label = 1 if ret_entry[max(horizons)] > 0 else 0`；綁最長持有期 | 方向書 7-11 |
| 090 | 零報酬 | `ret_entry == 0` 歸 `label = 0`，且不計入勝率分子（`win_rate` 定義為 `ret_entry > 0` 之加權比例） | tables.py:128；CODEX 必答 6 第 2 條 |
| 100 | 條件求值列之鍵 | 條件成立根之 `open_time`（FF 列時間戳＝K 線開盤、該根收盤已在列內）；**禁**用 t0+1 特徵列 | COMPOSER 必答 6 第 5 條 |
<!-- END GENERATED: eventscan-clock -->

### K-3 報酬欄與統計欄

<!-- BEGIN GENERATED: eventscan-return-columns -->
| 序 | 欄 | 語意 | 本票定位 | 現況 |
|---|---|---|---|---|
| 010 | `ret_entry` | `(close[exit_idx] − entry_price) / entry_price`，做空反號 | **主欄**；與隨機批相減者 | 已有 |
| 020 | `ret_label_anchor` | 以 t0 收盤為基準之同期報酬 | 診斷欄；**不得**與隨機批相減 | 已有 |
| 030 | `n` | 該（批, h）之有效事件數 | 顯示 | 已有 |
| 040 | `mean` | 加權平均 | 顯示 | 已有 |
| 050 | `median` | 加權中位數 | 顯示 | 已有 |
| 060 | `win_rate` | `ret_entry > 0` 之加權比例（**不讀 `label`**） | 顯示 | 已有 |
| 070 | `std` | 與 `mean` 同一組權重之加權標準差 | 顯示 | **本票新增** |
| 080 | `ret_max` | 該格 `ret_entry` 之最大值 | 顯示 | **本票新增** |
| 090 | `ret_min` | 該格 `ret_entry` 之最小值 | 顯示 | **本票新增** |
| 100 | `breakeven_cost_bps` | 見 `eventscan-breakeven` | 顯示 | **本票新增** |
| 110 | `ci` | 單批之信賴區間 | 本票不顯示單批 CI——掃描端 `event_split_plan` 恆 `None` ⇒ 值為字面 `"unavailable"` | 已有 |
| 120 | `strata.by_label` | 依 `label` 切正例／反例組 | **主表禁顯示**；標 `not_computed`，理由＝label 由同一報酬之符號導出、分組統計無訊息 | 已有 |
<!-- END GENERATED: eventscan-return-columns -->

### K-4 隨機對照規則

<!-- BEGIN GENERATED: eventscan-random-control -->
| 序 | 項 | 規格值 | 現況（實查） |
|---|---|---|---|
| 010 | 筆數 | `n_requested = n_trigger`（first-of-run 壓縮後之觸發筆數） | 前端寫死 `nRequested: 100` |
| 020 | 候選資格 | 以 `max(horizons)` 判定後續資料是否足夠 | 只吃單一 `label_rule.horizon_bars` |
| 030 | 期間池 | 有 ≥1 筆觸發 `t0` 之 UTC 月之聯集 | 取 `t0` min–max，且只需與觸發窗有交集 |
| 040 | 名額配額 | 按**每月觸發筆數**成比例；某月候選不足其配額 ⇒ fail-closed，不把缺額倒入他月 | `proportional_to_candidates`（按每月候選根數） |
| 050 | 樣本互斥 | 持有窗互斥 packing；`n_packed < n_trigger` ⇒ 比較端 `capability_status = unavailable`，不縮 n | `replace=False` 只禁同一根；`n_target = min(n_requested, candidate_count)` 靜默縮 n |
| 060 | 參數帶入 | 進場語意／出場錨／持有期集合／`direction` 一律由觸發批帶入，隨機批不得各自取預設 | 隨機批取契約 default `trigger_close`、模組常數 `close_to_close` |
| 070 | 身分閘 | 比較前之身分 tuple 須加入 `entry_price_semantic` 與 `decision_offset_bars` | tuple 為 `(threshold, horizon_bars, direction, label_return_mode)` |
| 080 | 門檻 | `threshold = 0.0`（使用者裁定 030 無門檻） | 前端預設 `threshold: 0.02` |
| 090 | 亂數 | seed 固定並寫入收據；同設定重跑之批逐位元組相同 | 已有 seed 與 `sample_ids_digest` |
| 100 | 全 run 對照 | 只得作為另一張敏感度表，標題須寫明其回答之問題為「條件是否只選到好行情」；不得當主比較 | 無 |
<!-- END GENERATED: eventscan-random-control -->

### K-5 失敗原因碼（封閉集合）

<!-- BEGIN GENERATED: eventscan-failure-reasons -->
| 序 | 原因碼 | 觸發條件 | 使用者可見訊息之內容 |
|---|---|---|---|
| 010 | `unregistered_column` | 條件式引用未註冊於該 run 之欄名 | 該欄名不在這個 run，附最接近欄名之建議清單 |
| 020 | `missing_bar` | t0 為資料最後一根，取不到 next_open | 該事件已排除，附排除筆數 |
| 030 | `insufficient_bars_for_horizon` | `exit_idx >= len(bars)` | 該（事件, h）格已排除，逐 h 附排除筆數 |
| 040 | `random_control_exclusivity_unsatisfiable` | 互斥 packing 後 `n_packed < n_trigger` | 無法比較，附 `n_trigger`／`n_packed`／`candidate_count`／`max_h` 四個計數 |
| 050 | `random_control_month_shortage` | 某觸發月之候選數不足其配額 | 無法比較，附該月份與缺額 |
| 060 | `random_control_rule_mismatch` | 身分閘任一葉不等 | 附不等之葉名與兩批各自的值 |
| 070 | `no_trigger_events` | 條件在該 run 上零筆成立 | 條件成立 0 次（與欄名錯誤明確區分） |
| 080 | `constant_expression` | 條件恆真／恆假或不引用任何欄位 | 沿用既有 `condition_engine` 之拒收理由 |
<!-- END GENERATED: eventscan-failure-reasons -->

### K-6 成本歸零點

<!-- BEGIN GENERATED: eventscan-breakeven -->
| 序 | 項目 | 值 |
|---|---|---|
| 010 | 事件型公式 | `breakeven_cost_bps = mean(ret_entry) × 10000 ÷ 2` |
| 020 | 分母 2 之來源 | 一次進場一次出場＝兩腿；事件型無連續持倉序列，故無換手率這個中間量 |
| 030 | 序列型公式（僅供對照，本票不用） | `mean(gross) ÷ mean(turnover) × 10000`（net_ic_analyzer.py:83） |
| 040 | 前提 | `mean(ret_entry) > 0` 才有意義；`≤ 0` ⇒ 該格標 `not_profitable_pre_cost` |
| 050 | 主數字 | 報酬主數字**不扣成本** |
| 060 | 必須揭露而算不進公式者 | 開盤第一筆成交價 ≠ 可成交均價、永續合約資金費、滑價 |
| 070 | 共用 | 本公式落地後事件型 IC 可直接共用同一支（結構同為一趟來回） |
<!-- END GENERATED: eventscan-breakeven -->

### K-7 硬性橫幅

<!-- BEGIN GENERATED: eventscan-banner -->
| 序 | 位置 | 字面 | 解除條件 |
|---|---|---|---|
| 010 | 「差（觸發 − 隨機）」表上方——`status` 非 `ok` 時 | 無信賴區間；平均差為正不得讀成這條規則會賺。 | Δ 之 bootstrap 區間 `status = ok` |
| 015 | 「差（觸發 − 隨機）」表上方——`status = ok` **且** `cluster_dependence_suspected` 為真時 | 區間已算出，但段與段之間偵測到序列相依；此區間可能過窄，平均差為正不得讀成這條規則會賺。 | `cluster_dependence_suspected` 轉為假。🔴 本列為 R4 修正：此情形下區間**確實有回傳**（Task 5.2 邊界④），沿用 010 之「無信賴區間」字面與畫面事實矛盾 |
| 020 | 掃描結果頁 | 這是同一段樣本上的描述，不是驗證過的策略。 | **不可解除**（本票不做樣本外驗證） |
| 030 | 報酬表 | 主數字未扣成本；未含吃單費、資金費、開盤滑價。 | **不可解除** |
<!-- END GENERATED: eventscan-banner -->

### K-8 八個缺口與其 Phase 歸屬

<!-- BEGIN GENERATED: eventscan-gaps -->
| 序 | 缺口 | 一句 | 對應 Task |
|---|---|---|---|
| 010 | 掃描函式沒有 API 接口 | `generate_events` 存在且能跑，但 `api/` 零呼叫者 | 2.1 |
| 020 | 條件讀不到 FF 欄位 | 讀特徵表與求條件兩端都有，中間沒有任何程式把 FF 欄名註冊給條件引擎 | 1.1、1.2 |
| 030 | 比較比的是達標率不是報酬 | 現有比較端點只回 prevalence／lift，且常因缺 `label_rule` 收據而灰 | 5.1 |
| 040 | 隨機抽樣不公平（四項） | 筆數／候選資格／樣本互斥／期間池與配額 | 4.1–4.4 |
| 050 | 統計欄差兩項 | 標準差與最好／最差沒有 | 3.1 |
| 060 | 沒有欄位選擇器 | 單一 run 欄名規模見 `eventscan-column-selector` 100，後端能回清單但只有平鋪一包 | 1.3、6.1 |
| 070 | 「持有 N 根」有兩套時鐘 | 事件報酬表自進場根起算、全 K 線表自 t0 起算，選 next_open 時差一根 | 2.3 |
| 080 | 事件型沒有成本歸零點 | 序列型有且前端已顯示；事件型是「沒做」不是「不能做」 | 3.2 |
<!-- END GENERATED: eventscan-gaps -->

### K-9 本票範圍（做與不做）

<!-- BEGIN GENERATED: eventscan-scope -->
| 序 | 項目 | 本票做不做 | 理由 |
|---|---|---|---|
| 010 | 權益曲線／複利加總 | 不做 | 持有窗高度重疊，簡單加總不是策略報酬——那是回測 |
| 020 | `strata.by_label` 正例／反例組 | 不顯示 | label 由同一報酬之符號導出 ⇒ 分組統計為套套邏輯 |
| 030 | 全 K 線表（`evaluate_all_bars`） | 不展示 | 時鐘不同，且會產出與本票無關之 AUC |
| 040 | 多標的 | 不做 | 使用者裁定 080，併 GAP-4 |
| 050 | 多重比較調整 | 不做 | 改以畫面字面揭露；主 horizon 須先寫下再看表 |
| 060 | 費率設定 | 不做 | 不在本票發明費率，改報成本歸零點 |
| 070 | 改事件匯入契約 | 不做 | label 由系統導出即滿足契約，改契約是不必要的擴散 |
<!-- END GENERATED: eventscan-scope -->

### K-10 欄位選擇器

<!-- BEGIN GENERATED: eventscan-column-selector -->
| 序 | 層／項 | 內容 | 來源 |
|---|---|---|---|
| 010 | 🔴 欄名**不得**以底線切分（R7 實證推翻主委原設計） | 原設計之 `<來源欄>_<週期>_<類別>_<指標>_<參數>` 五段文法**只涵蓋 0.77%**（3,235／418,719）。實測段數分佈：4 段 302／5 段 3,235／6 段 16,835／**7 段 393,731（94.03%）**／8 段 3,946／9 段 670。且切分本身不可靠——來源欄名含底線（`taker_ratio` 被切成兩段，同資料另有 `taker-ratio` 用連字號）、指標可有多個參數（`Klinger_34_55`）⇒ 六段以上之欄中 **11,198 個前五段不對應任何既存欄** | Claude 實跑最終 run 全量 2026-09-21 |
| 020 | **改用 group 結構，不解析欄名** | 選擇器之層級一律由 manifest 之 `groups` 導出：`groups.<gid>` 給 (週期, 層, 類別／指標)，`groups.<gid>.columns[]` 給該群之欄。此為**結構化欄位**，與 PIT 准入所用之來源同一份（見 `eventscan-pit-admission` 040） | Task 1.3 由 manifest 導出，不得前端硬編，**亦不得以底線切欄名** |
| 030 | 第 1 層 週期 | 自 gid 取；最終 run 實測為 `1h` 209,484 欄、`12h` 209,235 欄（兩者近乎對半） | 🔴 `manifest.present_timeframes` 只宣告 `1h`，與 raw groups 含 402 個 `12h` **矛盾**；**以 groups 為準**，該矛盾另列殘留 |
| 040 | 第 2 層 group | 該週期下之 gid 集合（最終 run 共 944 個，見 `eventscan-pit-admission` 035） | gid 本身即「層／類別／指標」之複合鍵，不再拆成三層 |
| 050 | 第 3 層 欄 | 該 gid 之 `columns[]`；群內之欄僅參數與衍生尾綴不同 | 群內若欄數過多，由 Task 1.3 之分頁契約處理（見 090） |
| 060 | 衍生尾綴之處置 | `_Lag_1`／`_Momentum_L3`／`_Cross`／`_Ratio`／`_TsRank_W5` 等尾綴**不另立層**，只作群內之篩選條件；97.3%（403,984）之六段以上欄其前五段對應既存基底欄，但**餘 11,198 個不對應**，故不得以「基底欄＋尾綴」為結構假設 | Claude 實跑最終 run 全量 2026-09-21 |
| 080 | 打字搜尋 | 對欄名做子字串比對，回相符欄名與其所屬 gid；同樣受 085 之分頁與顯式截斷約束 | **本票新增** |
| 085 | 🔴 回應契約（R7 指出原本完全缺失） | 分層端點**一律分頁**：每層回應含 `items`／`total`／`next_cursor`；單次回應之 `items` 上限 `500` 筆。**禁全量傳輸**（418,719 欄、14,103 個參數尾綴）。逾上限而未帶 `next_cursor` 即為契約違反；**截斷須顯式**——回應須帶 `truncated: true` 與 `total`，不得靜默截短 | Task 1.3／6.1；驗收須含「請求第 2 頁得到不同 `items` 且 `total` 不變」之 `pytest` |
| 090 | 後端既有來源 | `GET /api/v1/ic/features/list`（回整包平鋪清單） | api/routes/ic_analysis.py:344 |
| 100 | 規模（**唯一數字來源**，SPEC 散文不得自列） | reference run（`d9935491…`）之欄數＝ `418,719`，group 數＝ `944`（`1h` 542 ＋ `12h` 402），列數＝ `20,352`（兩條獨立推導一致：manifest `total_features`，與 `groups[].column_count` 加總）⇒ 平鋪清單對使用者不可用 | 實查新 reference run。🔴 **舊 run 之 `437,110` 不適用之真因（R6 委員更正主委）＝舊 run 另含 441 個 `12h_` group，非「預處理額外產生轉換後欄位」**；方向書所寫之「逾 18 萬」則是純錯值。兩者皆勿沿用 |
<!-- END GENERATED: eventscan-column-selector -->

### K-11 條件欄之 PIT 准入規則

<!-- BEGIN GENERATED: eventscan-pit-admission -->
| 序 | 規則 | 值 |
|---|---|---|
| 010 | 條件式之角色 | 掃描端恆以 `expression_role=feature` 呼叫；`filter` **不是**合法值，contract 之 `expression_roles` 不含它 |
| 020 | 角色隔離之現行保護 | `_role_violation` 只拒「角色非 `pit_feature`」與「欄名以 `future_` 為前綴」兩種 |
| 030 | 🔴 該保護之缺口 | 不含 `future_` 前綴而語意上含未來資訊之欄，現行 guard 放行（委員實跑反例已重現） |
| 035 | 🔴 manifest 實況（全量實查，非抽樣） | 新 reference run（`d9935491…`）有 **944 個 group**；gid 之底線段數分佈為 3 段 8 個／4 段 263 個／5 段 376 個／6 段 99 個／7 段 198 個；group 物件之鍵為 `column_count`／`columns`／`dtype`／`dtype_counts`／`encoded_column_count`／`file`／`file_size_bytes`／`float32_columns`／`nan_ratio`／`path`／`row_count`／`source_group_id`——**沒有類別欄，也沒有指標欄** |
| 040 | 本票之准入規則 | 契約檔 `momentum/Analysis/contracts/eventscan_pit_allowlist.json` 之索引鍵為 **(`symbol`, `timeframe`, `config_hash`)**，其下逐筆記 `gid → columns_sha256`；欄只在「該 run 之三元組已核准」**且**「其 `gid` 命中」**且**「該 gid 之 `columns` 實算 sha256 與登記值相等」時才進 registry |
| 042 | `columns_sha256` 之 canonical 定義（缺此定義即算不出同一個值） | ① 取 `groups.<gid>.columns` 之字串陣列；② 以 `LC_ALL=C` 位元組序**排序**（不可依賴 Python 預設 locale）；③ 以 `\\n` 連接、**尾端不加** `\\n`；④ 以 `UTF-8` 編碼（不加 BOM）；⑤ 取 `sha256` 之小寫十六進位。🔴 委員實測：同一份真實 `columns` 以四種常見算法可得**四個不同值** ⇒ 五步缺一即為不同實作 |
| 045 | 🔴 為何不切 gid 字串 | 「`<週期>_<層>_<類別>_<指標>` 四段文法」在新 reference run 上只蓋住 944 個中的 263 個（見 035），且切字串與被推翻的命名慣例是同一類防護。**列舉式白名單是封閉集合，切字串不是** |
| 047 | 🔴 為何索引要綁三元組與欄摘要（**跨 run 漂移之證據，取自兩個舊 run**，非現行 reference） | **以下為證據，不是現行設定**（現行 reference 見 `eventscan-golden-reference` 040）。兩個舊 ETHUSDT/1h run 比對：`4a8a0b37…` 有 1004 個 group、`5ea07439…` 只有 54；共用僅 43，其中 `1h_L2_Momentum_chunk2` 之 `column_count` 由 2000 變為 10。⇒ **純 gid 白名單同時造成大量誤拒（961 個未知 gid）與語意漏放（同 gid 欄集合已漂）** |
| 050 | 未命中之處置（三種皆 fail-closed） | ① 三元組未核准 ② gid 不在該 run 之登記 ③ `columns` 實算摘要與登記值不等 ⇒ 皆 fail-closed 不收該欄，並逐情形可列舉被拒欄數；**不得**以「看起來像技術指標」或「同名 gid 上次過了」放行 |
| 055 | 核准流程 | 由 `scripts/gen_eventscan_pit_allowlist.sh` 對指定三元組自 manifest 全量產出 `gid → columns_sha256` 候選，審定後寫入契約檔之該三元組區段。**須審之集合＝「新 gid」∪「gid 相同但 `columns_sha256` 與任一既有三元組之登記值不等者」**——只審新 gid 會漏掉欄漂（047 之 `1h_L2_Momentum_chunk2` 即此形態） |
| 057 | 誠實邊界（操作成本） | 每個新 FF run 需跑一次核准流程才能用於掃描。可直接沿用者＝gid 相同**且**欄摘要相等；上列 047 之兩個舊 run 實測顯示共用 gid 僅 43 個，其中再扣掉欄摘要已漂者才免審（**該數字為舊 run 之觀測，非現行 reference 之成本**）。成本不為零，但安全方向正確且不得以放寬 fail-closed 換取便利 |
| 060 | 白名單之維護點 | 契約檔為唯一來源；**不得手寫欄名清單**，也**不得**在程式碼內另列 gid（黑名單與散落清單永遠列不完） |
| 070 | 誠實邊界 | 粒度為 group 而非逐欄因果證明：同一 group 內若存在非因果變體則擋不住。逐欄因果 provenance 需 FF 在產出端補欄，列殘留 RESID-6 |
<!-- END GENERATED: eventscan-pit-admission -->

### K-12 數值參數

<!-- BEGIN GENERATED: eventscan-params -->
| 序 | 參數 | 值 | 對應 Task |
|---|---|---|---|
| 010 | 欄名建議清單長度上限 | `5` | 1.2 |
| 020 | 建議之演算法（先定法，再談耗時） | ① 以查詢字串之底線分段 token 與 registry 鍵做**交集預篩**取候選；② 只對候選算編輯距離。🔴 **禁**對全部鍵直接算編輯距離——reference registry 之規模見 `eventscan-column-selector` 100，直算在任何時間預算下都不可行 | 1.2 |
| 025 | 建議計算之耗時上限 | `200` 毫秒，**綁定 020 之演算法**且須附 reference 規模（見 `eventscan-column-selector` 100）之實測收據才算驗收通過；逾時回空建議清單並標原因，不得讓請求掛住 | 1.2 |
| 030 | Δ bootstrap 重抽次數 | `2000` | 5.2 |
| 040 | Δ bootstrap 分位 | `2.5` 與 `97.5`（雙尾 95%） | 5.2 |
| 050 | Δ bootstrap 之最小段數（**判準，非常數**） | 值＝`待校準`，由 056 之校準程序輸出後回填本列。🔴 **機械綁定**：Task 5.2 之驗收含一條測試，斷言本列之值**不為** `待校準`；未回填即該測試紅，Task 5.2 不得標完成。理由＝任何未經校準之下限都可能使區間在真實條件下幾乎恆為 `unavailable` | 5.2 |
| 055 | 校準之覆蓋率名目水準 | `0.95`（與 040 之雙尾分位一致） | 5.2 |
| 056 | 校準程序（**可重現，缺一即不同實作**） | ① 段數網格＝`[5, 10, 15, 20, 30, 40, 60, 80]`；② 每格模擬重複數＝`2000`；③ 校準 RNG seed＝`20260921`；④ 每次模擬以同分布兩批產生 Δ 之真值 0；⑤ 覆蓋率之判定用 **Wilson 二項式區間下界 ≥ 055**（非點估計 ≥ 055——點估計會因模擬噪音在邊界上跳動）；⑥ 取網格中**首個**滿足⑤者為最小段數；⑦ 全網格皆不滿足 ⇒ fail-closed 並列出各格覆蓋率，不得取最接近者 | 5.2 |
| 060 | Δ bootstrap seed | `20260921`（寫入收據；同設定重跑逐位元組相同） | 5.2 |
| 070 | 排除比例警告門檻 | `excluded / n_rows > 0.5` ⇒ 收據標警告，**不自動改排除窗寬度** | 4.3 |
| 080 | 段間相依診斷門檻 | 段層級報酬之一階自相關絕對值 `abs(rho_1) > 0.2` ⇒ 收據標 `cluster_dependence_suspected` | 5.2 |
| 090 | AST 呼叫點凍結清單之落檔 | `tests/golden/eventscan/analyze_tables_callsites.json`；schema＝`{"expected_count": <int>, "callsites": [{"file": <repo 相對路徑>, "line": <int>, "qualname": <str>}]}`，以 `(file, qualname)` 為 entry identity | 2.4 |
| 095 | AST 凍結清單之防腐 | 測試須同時斷言「AST 實掃集合 `==` 清單」**且**「集合大小 `==` `expected_count`」；只比對集合而不釘數量時，清單被整批清空仍會通過 | 2.4 |
<!-- END GENERATED: eventscan-params -->

### K-13 失敗原因碼之優先序

<!-- BEGIN GENERATED: eventscan-failure-precedence -->
| 序 | 情境 | 回哪一碼 | 理由 |
|---|---|---|---|
| 010 | 某觸發月候選不足配額，**且**全域互斥 packing 亦不足 | `random_control_month_shortage` | 月配額在 packing 之前執行；先發生者先報，使用者才知道該先放寬哪一層 |
| 020 | 月配額皆足，互斥 packing 不足 | `random_control_exclusivity_unsatisfiable` | 唯一成立者 |
| 030 | eligibility 剔除後候選為 0 | `random_control_month_shortage`（缺額＝該月全部配額） | 候選為 0 是月配額不足之極端值，不另開碼；Task 4.4 邊界③ 依此，不指向 packing 碼 |
| 040 | 期間池與觸發窗無交集 | `random_control_month_shortage`（觸發月聯集為空之特例，訊息須寫明為無交集） | 訊息須能區分「無交集」與「有交集但候選不足」，但原因碼同一支 |
| 050 | 多碼同時成立時之收據 | 收據須同時列出**全部**成立之情境與其計數，只有 `reason` 欄取優先序首位 | 只回一碼會讓使用者以為只有一個問題 |
<!-- END GENERATED: eventscan-failure-precedence -->

---

## §G Golden / Baseline

**適用性**：命中 (a)(d)。本票同時含「行為不變型重構」（既有報酬表與隨機對照之既有呼叫端）
與「新增數值」（統計欄、breakeven、Δ 區間），兩者驗收標準不同，分列如下。

- **feature/kline 條件**：本票讀 FF 特徵表與 kline，來源與 reference 設定見 `eventscan-golden-reference` 010–050。
  Feature Factory 之三方簽核不適用——本票不改其生成→計算→merge→split 任一段，只讀其產出。
- **凍結時機**：Phase 1 動工前凍結；存放路徑見 `eventscan-golden-reference` 060。
- **baseline 內容**（須能抓「值重排／局部錯位／同矩漂移」，非只 aggregate）：
  ① 事件批：`event_id` 集合 sha256 ＋ 筆數 ＋ 逐筆 `(t0_ms, entry_price_source_bar_open_ms, label)` 之 value hash；
  ② 報酬表：逐 `(批, h)` 之 `n`／`mean`／`median`／`win_rate` ＋ 逐事件 `ret_entry` 之 value hash ＋ NaN mask hash；
  ③ 隨機批：`sample_ids_digest`／`n_drawn`／`per_stratum` 配額 ＋ seed；
  ④ **產生器 provenance**（本輪新增，對應 Task 2.2 之推翻）：既有呼叫端之改動前 `source_file_digest`、
  canonical event bytes 與 provenance 鍵集合——沒有這一項，「缺省 off 即不變」就沒有任何東西在驗。
- **通過條件（可證偽，容差分尺度）**：
  - **行為不變型**（既有呼叫端，缺省參數）：改前 vs 改後 ——
    ① **既有鍵之值與 NaN 型態逐鍵 `==`**；② **既有鍵不得被移除或改名**；③ 列數不變；
    ④ 既有之 digest 與 provenance 鍵集合不變。任一不等即 FAIL 並列出首個不等之鍵與兩側值。
    🔴 **「輸出鍵集合皆不變」之初稿措辭與 Task 3.1（新增三鍵）自相矛盾**（本輪兩家獨立指出），
    已改為上列①②——**允許新增鍵、禁止改動或移除既有鍵**。新增鍵之正確性走下列「新增數值」那套。
    🔴 **兩套之歸屬不得有縫**（R3 之 finding 即落在此縫）：既有鍵（含 `mean`／`median`／`win_rate`／
    `n`／`n_effective`）走本套；新增鍵之**唯一清單**由 `eventscan-golden-reference` 075 界定。
    任一輸出鍵若兩套皆不涵蓋，即為 §G 缺漏，不得以「大概屬於某一套」帶過。
  - **新增數值**：適用鍵之**唯一清單**見 `eventscan-golden-reference` 075，容差見 070、
    exact 項見 090。🔴 本處**不自列鍵名**——R3 兩家指出此處之手打副本已與該列脫節，
    修法是把清單整段移入生成區塊，不是把副本改對。
  - **對照一致**：同一批以單一 h 跑 vs 以含該 h 之集合一次跑，該 h 之所有數值須相等。
- 🔴 **子集跑不得覆寫完整基準**：`--only` 類子集跑一律**不寫** golden；逐條 mutation 之收據以 id 合併，不得整檔覆寫。
- 跑完之副作用還原指令見 `eventscan-golden-reference` 100。

### G-1 reference 設定與容差（生成區塊，禁手改）

<!-- BEGIN GENERATED: eventscan-golden-reference -->
| 序 | 項目 | 值 |
|---|---|---|
| 010 | kline 來源 | `data_cache/feature_klines/kline_cache.h5`（禁合成 fixture） |
| 020 | reference symbol | `ETHUSDT` |
| 030 | reference timeframe | `1h` |
| 040 | reference FF run | `config_hash = d9935491cea49e8cada481a8bf9487d6`（2026-09-21 產生之**未轉換且含 1h＋12h** run）。🔴 **兩個不可用之 run**：`4a8a0b37…`（fracdiff 使跨週期欄不可比）與 `654bd63b…`（同為未轉換，但**漏了全部 12h 欄**，542 group 全為 1h）——後者仍在磁碟上，誤用風險高，任何引用皆須先核對 `config_hash` |
| 050 | 取 run 目錄之守衛 | 同一 `config_hash` 可存在於多個 symbol ⇒ 須再以 symbol 篩選，命中多於一個即 fail-closed |
| 060 | golden 存放路徑 | `tests/golden/eventscan/` |
| 070 | 新增數值之容差 | `abs ≤ 1e-12` 或 `rel ≤ 1e-9`；超出即列出該（批, h）與實際 diff = FAIL |
| 075 | 新增數值之適用鍵（**唯一清單**，SPEC 散文不得自列） | `std`／`ret_max`／`ret_min`／`breakeven_cost_bps`／`delta.*`（逐 h 之報酬差各欄）／Δ 之 `ci_low`／`ci_high`／`n_clusters`。任一新增鍵未列入本列即為缺漏；比對對象為 `numpy` 直算之參考值 |
| 080 | 行為不變型之容差 | 無容差——**既有鍵**之值與 NaN 逐鍵相等、既有鍵不得移除或改名、列數不變、既有 digest 與 provenance 鍵集合不變。🔴 **允許新增鍵**，其驗收見本表 **070（容差）與 075（適用鍵清單）**——不寫「下一列」，序號插入會使相對指涉失效（R4 實例：075 插入後「下一列」變成 090） |
| 090 | `n` 與 `nan_ratio` | exact，不得有容差 |
| 100 | 跑完之副作用還原 | `bash scripts/restore_golden_inventory.sh` |
<!-- END GENERATED: eventscan-golden-reference -->

### G-2 測試向量（生成區塊，禁手改；TODO 與測試一律掛本區塊，不得另行手打）

<!-- BEGIN GENERATED: eventscan-test-vectors -->
| 序 | 對應 Task | 輸入 | 預期輸出 |
|---|---|---|---|
| 010 | 2.2 | 布林序列 `[F, T, T, T, F, T, F]` | first-of-run 後 2 筆，`t0` 索引為 `1` 與 `5` |
| 020 | 2.3 | `h = 1`、`entry_price_semantic = next_open` | `exit_idx == t0_idx + 2`（兩套時鐘差距最大之情形） |
| 030 | 3.1 | `n = 1` | `std == 0`，且 `ret_max == ret_min == mean` |
| 035 | 3.1 | `values = [0.01, 0.03]`、`weights = [1.0, 3.0]`（權重不等、`n = 2`） | 加權 `mean == 0.025`、加權 `std == 0.0086602540378444`（參考值由測試獨立算出）。🔴 本列為 030 之補位：030 是 `n = 1`，權重正規化在單元素上等價 ⇒ 「拿掉正規化」之 mutation 在其上**不會轉紅**（委員實證之假存活） |
| 040 | 3.2 | 某格 `mean(ret_entry) = 0.0105` | `breakeven_cost_bps == 52.5`（參考值由測試以獨立算式算出） |
| 045 | 4.3 | 凍結 fixture：reference run（**以 `eventscan-golden-reference` 040 之 `config_hash` 為準，不得寫成未限定之「reference run」**）、`seed = 20260921`、`max(h) = 2`、`n_trigger = 40`。**可重播 identity（R7 指出 R6 之修補只有規格字面、無實際 artifact）**：fixture 落檔 `tests/golden/eventscan/random_control_fixture.npz`，並於同目錄之 `random_control_fixture.meta.json` 記 `config_hash`／`sample_ids_digest`／`fixture_sha256`／`source_manifest_sha256` 四者；驗收須斷言該四者與當次重建結果逐字相等，缺任一即 FAIL | 抽樣結果逐位元組可重播；`max(horizons) → 1` 之 mutation 在此 fixture 上**必**轉紅（不得依賴隨機抽樣碰巧重疊） |
| 047 | 4.3／4.2 | **兩碼同時成立**之組合：三個觸發月、觸發筆數 `80 / 10 / 10`，其中 1 月候選數 `< 80`（月配額不足），**且**全域互斥 packing 之槽數 `< 100`（packing 亦不足） | 依 `eventscan-failure-precedence` 010 回月配額碼；收據須同時列出**兩個**情境與其計數（010 與 020 皆列），只有 `reason` 欄取月配額碼。🔴 無此組合則優先序條文無法被驗證（委員指出 R1 未附） |
| 050 | 4.2 | 三個自然月、觸發筆數 `80 / 10 / 10`、每月候選根數相等 | 新模式配額 `80 / 10 / 10`；既有模式於同輸入下約 `34 / 33 / 33`（兩者須同測試內並列） |
| 055 | 5.2 | 凍結 fixture，**構造規則可逐位元組重建**：`seed = 20260921`；兩側各 24 段；每段長 8 根；段內報酬由 `numpy.random.default_rng(20260921).normal(0, 0.01, …)` 之累積和產生（同段共用一條路徑 ⇒ 段內高度重疊）；fixture 落檔於 `tests/golden/eventscan/delta_bootstrap_fixture.npz` 並記其 `sha256` | 「段改為單一事件」之 mutation 在此 fixture 上**必**轉紅；重建之 `sha256` 與落檔值 `==`（不得依賴 bootstrap 隨機誤差，亦不得只靠口頭描述重建） |
| 060 | 4.3 | reference run（依 `eventscan-golden-reference` 040）、`max(h) = 2`、抽 40 根；**沿用 045 之同一 fixture 與其四項 identity**，不另建 | 任兩個持有窗不重疊（逐對檢查，非抽樣） |
| 070 | 4.4 | `horizons = [5, 55]` vs `horizons = [5]` | 前者剔除距尾端不足 55 根之候選，後者不剔除（同測試內並列） |
| 080 | 1.2 | registry 含 `close_1h_trend_EMA_5`，查詢 `close_1h_trend_EMA_50000` | 建議清單首項為 `close_1h_trend_EMA_5` |
| 090 | 6.2 | 輸入 `5, 10, 30, 55` | `timeframe = 1h` 與 `timeframe = 12h` 之換算字串不同（同測試內並列） |
<!-- END GENERATED: eventscan-test-vectors -->

---

## §P Phase 與依賴

> 自檢已做：下列每個 Task 之輸入來源皆為同 Phase 或更早 Phase 之產出。
> Phase 3 與 Phase 4 互不依賴，可並行；Phase 5 依賴兩者。
>
> 🔴 **本輪修正（兩家獨立提出）**：初稿把 `by_label` 抑制參數放在 Phase 3，卻要求 Phase 2 之
> Task 2.1 傳入它 ⇒ Phase 2 無法獨立完成，那是**真的** forward dependency。
> 修法＝該參數之後端新增移入 Phase 2（Task 2.4），Phase 3 不再承載它。
> 此後 Task 2.1 對它的依賴為**同 Phase 內之順序依賴**（2.4 先於 2.1 之驗收），非跨 Phase。

### Phase 1 — 條件層可用（依賴：無）

**Task 1.1 — 把 FF 欄位註冊給條件引擎**
- 目標：讓條件式能引用該 FF run 的真實欄名。
- 檔案：`momentum/Analysis/event_samples/feature_materialization.py`（新增 registry 建構函式）、
  `momentum/FeatureEngineering/feature_library.py::FeatureLibrary.load`（唯讀取用，不改）。
- 既有 caller／影響面：`condition_engine.parse_condition` 之 `column_registry` 參數現由事件產生器呼叫端提供；
  新增者為**另一個建構來源**，既有呼叫端傳入之 registry 行為不變。
- 改法：由 `(symbol, timeframe, config_hash)` 讀 FF 特徵表欄名，依 `eventscan-pit-admission` 040/050
  之准入規則**逐欄判定是否收進 registry**，收進者標角色 `pit_feature`；輸出 `Mapping[str, str]` 餵
  `parse_condition`，`expression_role` 依 `eventscan-pit-admission` 010。
- 🔴 **無條件把全部 FF 欄標成 `pit_feature` 是不成立的**（本輪兩家獨立以碼證推翻）：
  現行角色隔離只拒兩種情形（見 `eventscan-pit-admission` 020），委員實跑之反例——名稱不含
  `future_` 而值取自未來的欄——**被放行**（030）；且 reference manifest 無 `available_at`／`causal` 欄，
  無法逐欄證明因果。全標 `pit_feature` 等於把 look-ahead 的唯一防線交給命名慣例。
  ⇒ 改為**封閉白名單式准入**：機械導出、缺 metadata 即拒收（040–060），誠實邊界見 070。
- **驗證**：`parse_condition("close_1h_trend_EMA_5 > close_1h_trend_EMA_10", <FF registry>, "feature")`
  回 `ConditionSpec` 且 `column_roles` 兩欄皆為 `pit_feature`；同一式在**未註冊 FF 欄**之 registry 下
  仍 `raise ConditionError("unregistered_column", …)`；另以「gid 不在白名單」與「gid 在白名單但 `columns_sha256` 不等」兩種欄各建一次 registry，該欄皆須**不在**
  registry 內且被拒欄數可列舉。
  **mutation（須測本票新增之碼，不是既有碼）**：把本 Task 之白名單比對改為「恆命中」，
  須使上述兩條「不得進 registry」之斷言各自轉紅（**兩條都要**：只擋 gid 不擋欄摘要，仍會放行欄漂之 run）。
  🔴 R1 原指定之 mutation（改 `expression_role` 為 `selection_predicate`）測的是既有
  `condition_engine._role_violation`，**不是本票新增之准入邏輯**（本輪委員指出）；
  該條降為**前提檢查**：先斷言既有 role isolation 仍在守（`future_` 前綴欄在 `feature` 角色下被拒），
  再測新增之白名單邏輯，兩者不得混為一條。
  測試指令：
  `pytest tests/momentum/event_samples/test_condition_engine_ff_registry.py -q`
- **邊界**：① FF run 不存在 ⇒ fail-closed 並回可區分之原因碼，禁回空 registry（空 registry 會讓所有欄名都變成
  「打錯字」）；② 同一 `config_hash` 命中多個 symbol ⇒ fail-closed；③ 欄名含 Python 保留字或非識別字字元
  ⇒ 該欄不得進 registry，且須可列舉（不得靜默丟棄）；④ 三元組未核准、gid 不在登記、或 `columns_sha256` 與登記值不等（`eventscan-pit-admission` 050 之三種情形）
  ⇒ 依 `eventscan-pit-admission` 050 拒收該欄，**不得**回落到「當作 `pit_feature`」。
- **存活至**：Phase 6 完工後仍保留（前端選擇器與掃描端共用同一份 registry）。
- **覆蓋風險**：無。後續 Phase 只讀不改本 Task 產出。
- 不可做：不得在此 Task 內新增任何指標計算；不得為了讓使用者例題可跑而補算 `EMA_30`。

**Task 1.2 — 欄名拒收訊息附「最接近欄名」建議**
- 目標：讓使用者分得出「打錯字」與「這個 run 沒有這個指標」。
- 檔案：`momentum/Analysis/event_samples/condition_engine.py`（`ConditionError` 之 payload）、
  `momentum/Analysis/contracts/condition_engine_contract.json`（`failure_reasons` 同步）。
- 既有 caller／影響面：`ConditionError` 之既有欄位不得移除或改名；建議清單以**新增鍵**承載。
- 改法：`unregistered_column` 拋出時附最接近欄名，**演算法依 `eventscan-params` 020**
  （token 交集預篩 ⇒ 只對候選算編輯距離；**禁**對全部鍵直算）。
  清單長度上限見 `eventscan-params` 010、耗時上限見 **025**（R3 兩家指出此處指針原指到 020，
  而 020 是演算法列、耗時在 025）。原因碼集合見 `eventscan-failure-reasons`。
- **驗證**：`eventscan-test-vectors` 080；另 registry 為空時建議清單為空、原因碼仍為
  `unregistered_column`（不得改成另一碼）。指令：`pytest tests/momentum/event_samples/test_condition_engine_suggest.py -q`
- **邊界**：① registry 達 `eventscan-column-selector` 100 之規模時，建議計算之耗時須符合 `eventscan-params` 025（超時回空建議、不得讓請求掛住）；
  ② 查詢字串為空或全空白 ⇒ 走既有 `empty_expression`，不進建議路徑。
- **存活至**：Phase 6 完工後仍保留（前端直接顯示建議清單）。
- **覆蓋風險**：無。
- 不可做：不得把 `unregistered_column` 降級為警告後回零命中——那正是本票要消滅的症狀。

**Task 1.3 — 欄位選擇器之後端分層索引**
- 目標：把平鋪欄名清單轉成 `eventscan-column-selector` 所定之**分層結構 ＋ 子字串搜尋**。
- 檔案：`api/routes/ic_analysis.py`（既有 `GET /api/v1/ic/features/list` 旁新增分層端點）、
  `api/services/ic_analysis_service.py`。
- 既有 caller／影響面：既有 `features/list` 之回應 schema **不得改動**（前端 `fetchAvailableFeatures` 在用）。
- 🔴 **改法已由 R7 推翻並重定**：主委原設計「以欄名底線切成五層」**只涵蓋 0.77%**，
  且切分本身不可靠（來源欄名含底線、指標可有多參數）——實測見 `eventscan-column-selector` 010。
  ⇒ 改為**以 manifest 之 `groups` 為結構來源**（020–060），與 `eventscan-pit-admission` 040
  用同一份結構化欄位，**全程不解析欄名**。回應一律分頁，契約見 085。
- **驗證**（`pytest`）：① 週期層之集合 `==` 自 `groups` 之 gid 導出者，且逐週期欄數與
  `eventscan-column-selector` 030 之實測值相等；② 任取一個 gid，其回傳之 `columns` 逐字等於
  manifest 該 gid 之 `columns`（雙向對證，防層級樹自己編出不存在的欄）；
  ③ 分頁：請求第 2 頁得到不同 `items` 且 `total` 不變；逾 085 之上限而未帶 `next_cursor` 即 FAIL；
  ④ 任取之葉欄名須同時存在於既有 `features/list` 之回應中（防兩條路徑各說各話）。
  **mutation**：把結構來源改回「以底線切欄名」，須使②在含 `taker_ratio` 之 gid 上轉紅。
  指令：`pytest tests/api/test_feature_selector_index.py -q`
- **邊界**：① 欄名含底線或連字號之來源欄（`taker_ratio`／`taker-ratio` 同時存在）⇒ 因不解析欄名而**不受影響**，
  但須有一條測試釘住此性質；② 搜尋字串為空 ⇒ 回空結果而非全部欄名（規模見 `eventscan-column-selector` 100）；
  ③ run 無任何 group ⇒ 回空樹且標明原因，非 500；
  ④ 🔴 `manifest.present_timeframes` 與 `groups` 之週期集合不一致 ⇒ **以 `groups` 為準**並記警告
  （最終 run 實際命中此情形，見 `eventscan-column-selector` 030 與 §N 之 RESID-11）。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把全量平鋪清單直接回給前端（規模見 `eventscan-column-selector` 100）；不得在後端做前端排版。

### Phase 2 — 掃描與時鐘（依賴：Phase 1）

🔴 **本 Phase 之執行順序＝ Task 2.4 → 2.2 → 2.3 → 2.1**（編號為標籤，非順序）。
2.1（掃描端點）同時需要 2.4 之抑制參數、2.2 之 first-of-run 與 2.3 之時鐘定義，故排在最後。
文件列序已依執行順序排列，TODO 生成時照此序。
🔴 R2 之修法只把 2.4 提前，仍把 2.1 排在 2.2 之前，而 2.1 之改法正以 2.2 為前置 ⇒ 順序矛盾未清；
R3 兩家各自指出後改為本序。**列序與依賴一致，是 TODO 可照序執行的前提。**
**Task 2.4 — 主表只顯示全體（後端抑制參數；本輪自 Phase 3 移入）**
- 目標：消滅 `label = sign(報酬)` 下的套套邏輯上主表。
- 檔案：`momentum/Analysis/event_samples/tables.py::_by_label_groups`、
  `momentum/Analysis/event_samples/pipeline.py::EventSamplePipeline.analyze_tables`（參數穿透）。
  前端接線在 Task 6.3，本 Task 只做後端。
- 既有 caller／影響面：IC 事件路徑之 `strata.by_label` **仍須可用**（其 label 為外部匯入或帶門檻之規則所產，
  非本次分析之報酬符號導出）。
  🔴 **生產路徑是 `analyze_tables` 而非直接呼叫報酬表函式**（本輪兩家獨立指出，主委實跑對證）：
  `event_forward_return_table` 之生產呼叫端為 `pipeline.analyze_tables`，其呼叫者為
  `api/services/case_import_service.py` 之三處；`api/services/ic_analysis_service.py` **零呼叫**該表函式
  （初稿誤列該檔）。⇒ 新參數**必須穿過 `analyze_tables`**，只改報酬表函式簽名等於保護沒有接上生產路徑。
- 🔴 **判定點在呼叫端，不在批的 provenance 欄**：`label_origin` 之值域為封閉五值
  （`search_positive_case`／`user_csv`／`platform_generator`／`platform_random`／`search_unlabeled`），
  **沒有任何一值能區分**「label 由本次分析之報酬符號導出」與「label 由帶門檻之規則產生」——
  兩者都會落在 `platform_generator`。擴充該 enum 等於改匯入契約，§C 明文禁止。
  ⇒ 改由 `event_forward_return_table` 與 `analyze_tables` 各新增參數
  `by_label_suppressed_reason: Optional[str]`，缺省 `None` ⇒ 行為與現況 byte 級相同。
  「本次分析之 label 與報酬是否同源」是**分析請求之性質**，只有發起該請求者知道，不可從批上反推。
- 改法：該參數非 `None` 時，`strata.by_label` 回 `not_computed` ＋ 該原因字串（見 `eventscan-return-columns` 120）。
- **驗證**（`pytest` caller matrix 正反兩路，缺一不可）：
  ① 經 `analyze_tables` 傳入該參數 ⇒ `strata.by_label` `==` `not_computed` 且原因字面非空；
  ② 經 `analyze_tables` 不傳（IC 事件路徑之三個既有呼叫點各一）⇒ `strata.by_label` 與改動前逐鍵 `==`；
  ③ **呼叫點盤點以 `analyze_tables` 為對象**（不是 `event_forward_return_table`——邊界③ 要擋的是新的
  `analyze_tables` 呼叫點，R1 之初稿盯錯函式，本輪委員指出）：以 **AST 走訪**（`ast` 模組解析
  `api/` 與 `momentum/` 之 `.py`，收集對 `analyze_tables` 之 `Call` 節點）取得呼叫點集合，
  與凍結清單逐字比對；新增未納入即 FAIL。
  凍結清單之落檔路徑與 schema 見 `eventscan-params` 090，防腐斷言見 095
  （R3 兩家指出：只寫「與凍結清單逐字比對」而不定路徑、schema 與預期數，清單自己會腐爛）。
  🔴 **誠實邊界**：AST 走訪只認得語法上的直接呼叫；以 `getattr`、字串反射或包裝函式間接呼叫者
  **抓不到**。本票不另做動態偵測（成本遠高於效益），該殘餘具名於 §N 之 RESID-8。
  `grep -c` 之文字比對更弱（連別名都抓不到），本輪已棄用。
  **mutation**：把判定改成忽略該參數而恆抑制，須使②轉紅；把參數只加在報酬表函式而不穿透
  `analyze_tables`，須使①轉紅。
  指令：`pytest tests/momentum/event_samples/test_return_table_by_label.py -q`
- **邊界**：① 參數為空字串（非 `None`）⇒ fail-closed，不得當成「不抑制」也不得當成「抑制但無理由」；
  ② 掃描端漏傳 ⇒ 由 Task 2.1 之端點層 spy 斷言擋下；③ 日後新增第四個 `analyze_tables` 呼叫點
  ⇒ 由上述驗證③之計數斷言擋下（此為對「呼叫端遺忘導致保護靜默失效」之機械防護，非紀律）。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得改 `win_rate` 公式；不得刪除 `by_label` 之程式碼路徑（IC 事件路徑在用）。


**Task 2.2 — first-of-run 壓縮**
- 目標：一段連續成立只算一次進場。
- 檔案：`momentum/Analysis/event_samples/generator.py`（新增壓縮步驟，以參數開關，缺省等同現況）。
- 既有 caller／影響面：既有事件產生器呼叫端不傳該參數時行為 byte 級不變。
  🔴 **「缺省 off 即 byte 級不變」不是自動成立的**（本輪兩家獨立以碼證推翻）：
  `generator.py:173` 之 `source_file_digest` 雜湊 `gen_payload`，其中含 `asdict(gen_config)`
  ⇒ **只要新參數進入 `GeneratorConfig`，缺省 `False` 也會改掉每一列的 digest**，
  而既有測試只比對「同一次執行內」之自洽 digest，沒有凍結改動前之值 ⇒ 該 mutation 會存活。
  ⇒ **強制作法**：新參數**不得**進入 `GeneratorConfig`／`gen_payload`，以 `generate_events` 之獨立
  keyword 承載；掃描端所需之可重播性另以新收據欄記錄，不污染既有 `source_file_digest`。
- 改法：對條件求值之布林序列取連通段，每段取第一根為 `t0`；每根皆取之版本以另一鍵保留為敏感度。
  規格值見 `eventscan-clock` 070。
- **驗證**：`eventscan-test-vectors` 010 之輸入與預期（`pytest` 斷言逐字取該列）；
  另對 reference run 之真實條件，壓縮後筆數 `<=` 壓縮前，且壓縮後之 `t0` 集合為壓縮前之子集；
  另**凍結**既有呼叫端之改動前 `source_file_digest`、canonical event bytes 與 provenance 鍵集合，
  缺省路徑須與之逐項 `==`（見 §G 之新增 baseline 項）。
  **mutation**：① 把「取每段第一根」改為「取每段最後一根」須使索引斷言轉紅；
  ② 把新參數放進 `GeneratorConfig` 須使凍結 digest 斷言轉紅（此即上述推翻之機械化）。
  指令：`pytest tests/momentum/event_samples/test_first_of_run.py -q`
- **邊界**：① 全 False ⇒ 0 筆；② 全 True ⇒ 1 筆；③ 首根即 True ⇒ 該段起點為索引 0（不得因無前一根而漏掉）；
  ④ 序列含 NaN（欄位在該根無值）⇒ 該根視為 False 且須可列舉其筆數，不得與真 False 混為一談。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把壓縮前的筆數當主數字；不得用「合併相距 ≤ k 根的兩段」這類額外啟發式（未經裁定）。

**Task 2.3 — 持有時鐘單一定義**
- 目標：本票全部表面共用同一個 `(decision_at, entry_at, exit_at)`。
- 檔案：`momentum/Analysis/event_samples/alignment.py`、`tables.py`、`pipeline.py`（掃描端之 `analyze_tables` 組裝）。
- 既有 caller／影響面：IC 事件路徑亦呼叫 `analyze_tables`；本 Task 只在**掃描端**收斂展示集合，
  不改 IC 事件路徑既有回傳鍵。
- 改法：掃描端產出之 manifest 只存一份 `(decision_at, entry_at, exit_at)` tuple，label、報酬表、
  隨機對照三者共用；全 K 線表於掃描端不展示（`eventscan-scope` 030）。定義見 `eventscan-clock`。
- **驗證**：同一批同一 `h`，`label` 所用之出場根索引與報酬表之 `exit_idx` 相等（逐事件比對，非抽樣）；
  掃描端回應之鍵集合不含全 K 線表之 `hold`／AUC 鍵。
  **mutation**：把 label 之出場索引改為 `t0_idx + h` 須使逐事件相等斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_eventscan_clock_parity.py -q`
- **邊界**：① `eventscan-test-vectors` 020 之組合（兩套時鐘差最大之情形，須明確釘住）；
  ② `decision_offset_bars > 0` ⇒ 決策根早於 t0，進場根仍依 `eventscan-clock` 010；
  ③ 事件落在資料最後一根 ⇒ 依 `eventscan-clock` 020 排除。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把全 K 線表改成同一時鐘後再展示——那是另一條估計量，本票不驗收它。

**Task 2.1 — 掃描函式接上 API**
- 目標：條件式 → 事件批 → 走既有匯入契約落檔，前端可觸發。
- 檔案：`api/routes/ic_analysis.py`（新增掃描端點）、`api/services/ic_analysis_service.py`、
  `momentum/Analysis/event_samples/generator.py::generate_events`（唯讀取用）。
- 既有 caller／影響面：`generate_events` 目前 `api/` 零呼叫者；本 Task 為其第一個生產呼叫端。
- 改法：端點收 `(symbol, timeframe, config_hash, expression, horizons[], primary_horizon, direction)`；
  以 Task 1.1 之 registry 解析條件 → 求值 → 壓成 first-of-run（Task 2.2）→ 填 label（`eventscan-clock` 080）
  → 走既有匯入契約落批。進場語意、時鐘見 `eventscan-clock`。
  🔴 **`primary_horizon` 為必填請求欄**（R3 兩家指出：R2 只把它寫進 Task 5.1 與 Q-C10，
  端點輸入契約沒有承載它 ⇒ 主 horizon 可被猜測、遺失或由後端代填）：型別為整數，
  **須為 `horizons[]` 之成員**，否則 fail-closed 並列出兩者。
  🔴 **且須落到可驗證、可持久化的批次收據**（R4 委員指出：R3 只把它加在請求上，
  `event_import_contract.json` 之 `receipt_schema.batch` 與 API DTO 皆無此欄
  ⇒ 請求收下後該值不落檔，Task 5.1 之「收據自本欄取值」沒有可取之處）：
  本票於 `receipt_schema.batch` **新增** `primary_horizon` 與 `primary_horizon_declared_at` 兩鍵，
  並於 API 回應 DTO 同步新增。
  🔴 **typed shape 須釘死**（R5 兩家指出：R4 只寫「選填」而未定形狀；該 namespace 之既有純量鍵
  皆為 leaf，而 **leaf 恆必填** ⇒ 直接寫成純量會變成必填鍵、使舊批驗證失敗）：
  兩鍵一律寫成**與 `label_rule` 同型之 typed node**——
  `{"type": <型別>, "required": false, "doc": <說明>}`，`primary_horizon` 型別 `int`、
  `primary_horizon_declared_at` 型別 `int`（epoch ms UTC）。
  ⚠️ §C 之「不得改匯入契約之 `required_fields`」**未被逾越**（R5 判定）：新增之鍵在 `receipt_schema`
  而非 `required_fields`。**驗收須附碼證**：以一個不含該兩鍵之既有批跑 `validate_event_import`，
  結果與改動前逐欄相同。
  🔴 **本端點之不變式**：經 `pipeline.analyze_tables` 組表時**恆**傳入 Task 2.4 之
  `by_label_suppressed_reason`；漏傳即為缺陷，須有測試釘住（見下驗證條）。
  （本 Task 為 Phase 2 之**最後**一個：其輸入同時需要 2.4 之抑制參數、2.2 之 first-of-run
  與 2.3 之時鐘定義，故列於三者之後。）
- **驗證**：對 reference run 與一條多頭排列條件，端點回之批可被 `import_contract.py` 之既有驗證器收下（不放寬任何既有檢查），
  且批內每筆之 `t0` 對應之特徵列鍵為該根 `open_time`（`eventscan-clock` 100）；
  另以 spy 斷言本端點對 `pipeline.analyze_tables` 之每一次呼叫，其
  `by_label_suppressed_reason` 皆非 `None`（釘住上述不變式）。
  指令：`pytest tests/api/test_eventscan_endpoint.py -q`
- **邊界**：① 條件零筆成立 ⇒ 回 `no_trigger_events`，與欄名錯誤明確區分；② 條件全根成立 ⇒ first-of-run 後為 1 筆，
  且須通過匯入契約之「一批須兩類 label 皆有」檢查或以可區分之原因碼拒收（不得靜默產出單類批）；
  ③ `max(horizons)` 大於資料長度 ⇒ fail-closed；
  ④ `primary_horizon` 缺欄、非整數、或不在 `horizons[]` 內 ⇒ fail-closed，
  **不得**由後端取 `horizons[0]` 或 `max(horizons)` 代填（代填等於系統替使用者做了預先登記）。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。Phase 4／5 讀本 Task 產出之批，不覆寫。
- 不可做：不得在掃描批內混入隨機列；不得改匯入契約之 `required_fields`；不得自建一條繞過匯入契約檢查的路徑。

### Phase 3 — 報酬與統計（依賴：Phase 2）

**Task 3.1 — 報酬表補三個統計量**
- 目標：加上 `std`／`ret_max`／`ret_min`。
- 檔案：`momentum/Analysis/event_samples/tables.py::_weighted_stats`。
- 既有 caller／影響面：🔴 **`_weighted_stats` 只有一個呼叫點**（`tables.py:269`，於
  `event_forward_return_table` 內）。初稿寫「與 `binary_discrimination_table` 共用」為**誤述**——
  該函式有自己的 `metrics()`，不呼叫 `_weighted_stats`（本輪兩家指出，主委以 `grep -n "_weighted_stats"`
  實跑對證：全檔僅 `:118` 定義與 `:269` 呼叫兩處）。⇒ 受影響鍵之範圍僅報酬表，不及判別表。
  **既有鍵不得改名或改值**，新鍵一律新增。
- 改法：於既有回傳物件新增三鍵；`std` 為與 `mean` 同一組權重之加權標準差；
  `ret_max`／`ret_min` 取該格 `ret_entry` 之極值。定義見 `eventscan-return-columns` 070–090。
- **驗證**：對同一組 `(values, weights)`，既有三鍵 `mean`／`median`／`win_rate` 逐鍵 `==` 改動前之值（byte 級相同）；
  新增三鍵與 `numpy` 直算之參考值在 §G 容差內相等（`eventscan-test-vectors` 030 與 035 兩組皆須跑）。
  **mutation**：把加權標準差的權重正規化拿掉須使與參考值之比對轉紅。
  🔴 **該 mutation 必須跑在 `eventscan-test-vectors` 035（`n = 2`、權重不等）上**——
  初稿只給 030（`n = 1`），單元素時原始權重與正規化權重在 mean／std 上等價，
  該 mutation 在其上**不會被觸發**，是 §V 明令禁止的假存活組合（本輪兩家獨立實證）。
  指令：`pytest tests/momentum/event_samples/test_tables.py -q`
- **邊界**：① `n = 0` ⇒ 三鍵皆 NaN，與既有 `mean` 之 NaN 行為一致；② `eventscan-test-vectors` 030 與 035；
  ③ 權重總和為 0 ⇒ 與既有行為一致回 NaN，不得改成 0。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得順手改 `win_rate` 之定義；不得移除 `n_effective`。

**Task 3.2 — 事件型成本歸零點**
- 目標：為事件報酬算 `breakeven_cost_bps`。
- 檔案：新增 `momentum/Analysis/event_samples/breakeven.py`；`tables.py` 於報酬表每格掛該值。
- 既有 caller／影響面：`momentum/Analysis/net_ic_analyzer.py` 之序列型公式**不動**（兩條公式前提不同）。
- 改法：公式與前提見 `eventscan-breakeven`。事件型不需要換手率序列——每筆交易之換手固定為兩腿。
- **驗證**：`eventscan-test-vectors` 040（`pytest` 斷言逐字取該列，參考值由測試獨立算出、非抄實作）；
  另 `mean(ret_entry) <= 0` 之格回 `not_profitable_pre_cost`（見 `eventscan-breakeven` 040）。
  **mutation**：把分母 2 改成 1 須使上述數值斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_event_breakeven.py -q`
- **邊界**：① `mean` 為 NaN（n=0）⇒ 回 `unavailable` 而非 NaN 數值；② `mean` 恰為 0 ⇒ 走 `not_profitable_pre_cost`；
  ③ 做空批 ⇒ `ret_entry` 已含反號，公式不得再乘一次 sign。
- **存活至**：Phase 6 完工後仍保留；並登記為事件型 IC 可共用之函式（見 §N 殘留）。
- **覆蓋風險**：無。
- 不可做：不得在本票發明任何費率預設值；不得把 breakeven 從報酬主數字中扣除。

### Phase 4 — 隨機對照（依賴：Phase 2）

🔴 **本 Phase 之執行順序＝ Task 4.1 → 4.4 → 4.2 → 4.3**（編號為標籤，非順序）。
4.1 先把觸發批之 `horizons` 帶入；4.4 以 `max(horizons)` 定候選資格；4.2 在該候選池上配額；
4.3 再於配額結果上做互斥 packing。R4 兩家指出：R3 只修了 Phase 2 之列序，Phase 4 之
4.2／4.3 依賴 4.4 定義之候選池，而 4.4 列在其後——**同型矛盾，逐 Phase 都要查**。

**Task 4.1 — 參數由觸發批帶入 ＋ 身分閘擴充**
- 目標：兩批用同一把尺。
- 檔案：`momentum/Analysis/event_samples/random_control.py`、`api/services/ic_analysis_service.py`（身分閘）。
- 既有 caller／影響面：既有隨機對照 UI 亦呼叫同一端點；未帶新參數時行為不變。
- 改法：`entry_price_semantic`／`label_return_mode`／`decision_offset_bars`／`horizons`／`direction`
  由觸發批帶入；身分 tuple 擴充見 `eventscan-random-control` 060–070。
- **驗證**：觸發批 `entry_price_semantic=next_open` 時，隨機批紀錄之該欄 `==` `next_open`；
  兩批該欄不等時比較端回 `random_control_rule_mismatch` 並列出不等之葉。
  **mutation**：把 `entry_price_semantic` 自身分 tuple 移除須使第二條斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_random_control.py -q`
- **邊界**：① 觸發批缺該欄 ⇒ fail-closed，不得回落到契約 default；② 觸發批之 `horizons` 為空 ⇒ fail-closed；
  ③ 既有呼叫端不傳新參數 ⇒ 產生之批與改動前 byte 級相同。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得以「畫面標明用了哪個」代替帶入——尺不同就不能相減。

**Task 4.4 — 候選資格改用 `max(horizons)`**
- 目標：候選資格要夠寬到涵蓋最長持有期。
- 檔案：`momentum/Analysis/event_samples/random_control.py`（eligibility 判定）。
- 既有 caller／影響面：既有呼叫端只傳單一 `label_rule.horizon_bars` 時，`max` 退化為該值，行為不變。
- 改法：eligibility 改吃 `horizons` 集合並取其最大值；規則見 `eventscan-random-control` 020。
- **驗證**：`eventscan-test-vectors` 070（`pytest` 兩組同測試內並列，證明差異真實）。
  **mutation**：把 `max` 改為 `min` 須使該列之第一條斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_random_control_eligibility.py -q`
- **邊界**：① `horizons` 僅一元素 ⇒ 與既有行為 byte 級相同；② `horizons` 含 0 或負值 ⇒ fail-closed；
  ③ 剔除後候選為 0 ⇒ 依 `eventscan-failure-precedence` 030 回**月配額**碼（缺額＝該月全部配額），**不是** packing 碼——三處指向同一支，消除 R1 之三重重疊。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得同時放寬其他資格條件來補回被剔除的候選數。

**Task 4.2 — 期間池與配額改按觸發筆數**
- 目標：讓對照落在觸發所在的行情，而非窗內平均行情。
- 檔案：`momentum/Analysis/event_samples/random_control.py::_allocate` 旁新增配額模式。
- 既有 caller／影響面：既有 `proportional_to_candidates` 模式保留，缺省不變。
- 改法：新增 `proportional_to_triggers` 模式；期間池與配額規則見 `eventscan-random-control` 030–040。
- **驗證**：`eventscan-test-vectors` 050（`pytest` 斷言逐字取該列，兩模式須同測試內並列以證明差異真實存在）；
  另某月候選不足其配額 ⇒ 回 `eventscan-failure-reasons` 050 之原因碼，不把缺額倒入他月。
  **mutation**：把配額基數由觸發筆數改回候選根數須使 80/10/10 斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_random_control_allocation.py -q`
- **邊界**：① 僅一個觸發月 ⇒ 配額全落該月；② 觸發筆數為 0 ⇒ 不進本路徑（由 Task 2.1 之 `no_trigger_events` 先擋）；
  ③ 配額因取整而總和不等於 `n_target` ⇒ 沿用既有「最大餘數 ＋ 同序再分配」，不得用 `round`。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得把「整個 run」當主比較之期間池（`eventscan-random-control` 100）。

**Task 4.3 — 互斥 packing 與不足即 fail-closed**
- 目標：消滅靜默縮 n。
- 檔案：`momentum/Analysis/event_samples/random_control.py`（抽樣迴圈與收據）。
- 既有 caller／影響面：既有呼叫端不啟用互斥時行為不變。
- 改法：抽中一根後把其持有窗（長度 `max(horizons)`）加入排除遮罩；規則見 `eventscan-random-control` 050。
- **驗證**：`eventscan-test-vectors` 045 之凍結 fixture ＋ 060（`pytest` 逐對檢查，非抽樣）；
  另候選不足以 pack 出 `n_trigger` 個互斥槽時，回 `eventscan-failure-reasons` 040 之原因碼與其四個計數，
  且**不得**回一個較小的 `n_drawn`；另多碼同時成立時依 `eventscan-failure-precedence` 取碼並列出全部情境。
  **mutation**：把排除遮罩的窗長由 `max(horizons)` 改為 1 須使不重疊斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_random_control_exclusivity.py -q`
- **邊界**：① 候選恰好等於 `n_trigger` ⇒ 成功且用盡；② 候選為 0 ⇒ 回失敗原因碼，
  **不得**回空批當成功（既有 `test_zero_candidates_yields_empty_batch` 之行為在本票路徑上須被擋下，
  且該既有測試不得被放寬——改以本票路徑之獨立測試承接）；③ `max(horizons)` 大於期間池總長 ⇒ fail-closed。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得放寬互斥、不得抽相鄰根充數、不得縮小 n。

### Phase 5 — 比較端點（依賴：Phase 3、Phase 4）

**Task 5.1 — 比較端點改為比報酬**
- 目標：回傳兩批之報酬統計與其差，而非達標率。
- 檔案：`api/services/ic_analysis_service.py`（compare）、`api/models/event_import_models.py`（response）。
- 既有 caller／影響面：既有 `prevalence`／`lift` 鍵**保留不動**（既有 UI 在讀）；報酬差以新鍵承載。
- 改法：新增逐 `h` 之 `trigger`／`random`／`delta` 三組，欄位集合等同 `eventscan-return-columns`；
  `delta` 只由 `ret_entry` 相減，**不得**用 `ret_label_anchor`。
  另**收據須記錄本次請求宣告之主 horizon 與其送出時刻**（Q-C10 之機械承載）。
  🔴 **該值需要一個請求欄才承載得住**（本輪委員指出：掃描請求與前端輸入皆只有 `horizons[]`，
  一個整數集合表達不了「哪一個是事先宣告的主 horizon」）⇒ Task 2.1 之掃描請求與 Task 6.2 之輸入
  **各須新增一個必填欄** `primary_horizon`（須為 `horizons[]` 之成員，否則 fail-closed）；
  Task 5.1 之收據自該欄取值。該欄一經寫入，同一批之後續請求不得改寫（改寫即 fail-closed 並列出兩值）。
- **驗證**：對兩批已知之 `mean`，`delta.mean` `==` 兩者相減之值（參考值由測試獨立算出）；
  觸發批以 `ret_label_anchor` 餵入時端點拒收並回可區分之原因碼。
  **mutation**：把 `delta` 之被減數改為 `ret_label_anchor` 須使斷言轉紅。
  指令：`pytest tests/api/test_eventscan_compare.py -q`
- **邊界**：① 某 `h` 兩批之一 `n=0` ⇒ 該 `h` 之 `delta` 標 `unavailable`，不得回 NaN 當數值；
  ② 身分閘不過 ⇒ 整個比較 `unavailable`，不得只回觸發批那半；③ `horizons` 兩批不等 ⇒ fail-closed。
- **存活至**：Phase 6 完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得移除既有 `prevalence`／`lift` 鍵；不得把 `label_rule` 收據之既有要求放寬以「讓按鈕不灰」。

**Task 5.2 — Δ 之 cluster／時間塊 bootstrap 區間**
- 目標：把 Δ 之抽樣變異量化成區間。
  🔴 **目標句不得寫成「回答差是不是運氣」**（本輪委員指出初稿把描述寫成證據）：
  段／槽 bootstrap 處理的是**重疊造成的相依**，不處理段與段之間的行情相依，
  也不識別因果。它能說的只有「在這個重抽模型下，Δ 的抽樣分佈落在哪」。
- 檔案：新增 `momentum/Analysis/event_samples/delta_bootstrap.py`。
- 既有 caller／影響面：`tables.py::_cluster_bootstrap_ci` 不動（其前提為已切分之批）。
- 改法：重抽樣單位＝**一整段連續成立**（觸發側以 first-of-run 之連通段 id；對照側以互斥槽 id），
  每次重抽重算兩側均值再相減，回 Δ 之分位區間與重抽次數；參數與前置條件見 `eventscan-params` 030–060、080。
  另須輸出**段間相依診斷**（`eventscan-params` 080）：超過門檻即於收據標
  `cluster_dependence_suspected`。該旗標為真時之畫面行為依 `eventscan-banner` **015**（區間已算出但標明可能過窄）——**不是**掛 010 之「無信賴區間」，該情形下區間確實有回傳（見下邊界④）。
- **驗證**：`eventscan-test-vectors` 055 之凍結 fixture（`pytest`，`seed` 固定、逐位元組可重播）；
  另對人造資料——兩批同分布 ⇒ Δ 之區間涵蓋 0 之比例接近名目水準；
  對觸發側整體平移一個已知常數 ⇒ Δ 之點估計 `==` 該常數且區間不含 0；
  另段層級一階自相關超過 `eventscan-params` 080 之門檻時，收據之 `cluster_dependence_suspected` 為真。
  **mutation**：① 把重抽單位由「段」改為「單一事件」須使 055 fixture 之涵蓋率斷言轉紅
  （**必須跑在該凍結 fixture 上**——初稿未凍結，mutation 可因 bootstrap 隨機誤差存活，本輪委員指出）；
  ② 把相依診斷改為恆回 false 須使上述旗標斷言轉紅。
  指令：`pytest tests/momentum/event_samples/test_delta_bootstrap.py -q`
- **覆蓋率校準（本輪新增，為 `eventscan-params` 050 之值的唯一來源）**：以同分布兩批模擬，
  程序與其全部參數依 `eventscan-params` **056**（含段數網格、每格重複數、seed、以及**以 Wilson 二項式區間下界判覆蓋率**）；名目水準見 055。本處不複述判定式——點估計與區間下界會得到不同的回填值。
  **該校準測試本身是驗收條件**——未跑出值即不得宣稱 Task 5.2 完成。
- **邊界**：① 段數未達 `eventscan-params` 050 之下限 ⇒ 回 `unavailable`，**禁**以單簇假算；
  ② 兩側段數差距極大 ⇒ 須可列舉兩側段數，不得只回一個區間；
  ③ 重抽次數不足 ⇒ fail-closed 而非回較差的區間；
  ④ 相依診斷為真而區間仍算得出來 ⇒ 區間照回，但旗標須隨之回傳且橫幅不解除。
- **存活至**：Phase 6 完工後仍保留。其 `status = ok` 是 `eventscan-banner` 010 之解除條件；
  相依旗標轉為假才是 015 之解除條件。**兩條橫幅各有各的解除條件，不可合併判斷**
  （R4 指出：合併後 `status = ok` 且相依為真時會掛上「無信賴區間」，與該情形下區間確實回傳之事實矛盾）。
- **覆蓋風險**：無。
- 不可做：不得分別畫兩側 CI 再看重不重疊——那不能回答「差是否為 0」；
  不得在本 Task 宣稱因果或「這條規則會賺」。

### Phase 6 — 前端（依賴：Phase 1、Phase 5）

**Task 6.1 — 欄位選擇器 UI**
- 目標：逐層下拉 ＋ 打字搜尋，使用者永遠不用自己拼欄名字串。
- 檔案：`frontend/src/components/ic-analysis/`（新元件）、`frontend/src/lib/`（API client）。
- 既有 caller／影響面：既有 `fetchAvailableFeatures` 不改。
- 改法：消費 Task 1.3 之分層端點；選完自動把欄名填入條件式輸入框；顯示 Task 1.2 之建議清單。
- **驗證**：vitest——選定一條分層路徑（週期→gid→欄，見 `eventscan-column-selector` 030–050）後，條件式輸入框之內容等於該葉之欄名字面；
  搜尋 `EMA` 時結果清單長度等於後端回傳長度（不得前端另行截斷而不揭露）。
  指令：`cd frontend && npx vitest run src/components/ic-analysis/__tests__/FeatureSelector.test.tsx`
- **邊界**：① 空態（run 無欄）；② 載入中；③ 錯誤態（端點 4xx／5xx）——三者皆須有明確畫面，非空白。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得在前端硬編任何指標名或參數清單。

**Task 6.2 — 持有期輸入與換算顯示**
- 目標：直接輸入、逗號分隔、即時顯示約幾天。
- 檔案：`frontend/src/components/ic-analysis/`（掃描設定面板）。
- 既有 caller／影響面：新元件，無既有 caller。
- 改法：文字輸入框解析為整數集合；換算＝`根數 × 週期長度`，週期長度由該 run 之 `timeframe` 決定。
  🔴 **另須一個「主 horizon」選擇器**（R3 兩家指出：R2 只把 `primary_horizon` 寫進後端收據與 Q-C10，
  前端沒有任何承載它的輸入 ⇒ 使用者無從宣告、系統只能猜）：選項集合恆等於當前已輸入之
  `horizons[]`；使用者未選時**送出鈕停用**，前端不得預選任何值（預選等於替使用者做預先登記）。
  送出之 payload 含 `primary_horizon`。
- **驗證**：vitest——`eventscan-test-vectors` 090（兩個 timeframe 同測試內並列，換算字串逐字比對）；
  另 ① 主 horizon 未選 ⇒ 送出鈕 `disabled`；② 改動 `horizons[]` 使已選之主 horizon 不再在集合內
  ⇒ 該選擇被清空且送出鈕停用；③ 送出之 payload 之 `primary_horizon` 等於使用者所選值。
  指令：`cd frontend && npx vitest run src/components/ic-analysis/__tests__/HorizonInput.test.tsx`
- **邊界**：① 空輸入 ⇒ 送出鈕停用且說明原因；② 含非整數或 ≤0 ⇒ 標出該項並拒送；
  ③ 重複值 ⇒ 去重並顯示已去重；④ 僅輸入一個持有期 ⇒ 主 horizon 仍須**明示選取**，
  不得自動代選（同一理由：代選即系統替使用者登記）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得提供勾選清單取代輸入框（`eventscan-rulings` 010）。

**Task 6.3 — 兩組統計並排與差表**
- 目標：把 Task 5.1 之三組畫成使用者要的表。
- 檔案：`frontend/src/components/ic-analysis/`（新表元件）。
- 既有 caller／影響面：既有 `EventTablesPanel` 之 `by_label` 三表在本票路徑須不顯示（Task 2.4 之抑制參數）。
- 改法：逐 `h` 一列；欄位集合等同 `eventscan-return-columns`；**只顯示全體一組**。
- **驗證**：vitest——後端回 `strata.by_label = not_computed` 時畫面不渲染正例／反例表；
  `delta.status = unavailable` 時該格顯示原因字串而非空白或 0。
  指令：`cd frontend && npx vitest run src/components/ic-analysis/__tests__/EventScanTables.test.tsx`
- **邊界**：① 某 `h` 兩批 `n` 不等 ⇒ 兩側各自顯示其 `n`，不得只顯示一個；② 空批；③ 全部 `h` 皆 `unavailable`。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得在前端自行相減產生 `delta`（須用後端回傳值，否則兩處公式會漂）。

**Task 6.4 — 硬性橫幅與門檻欄移除**
- 目標：畫面不得讓人把描述讀成證據；且不得出現使用者裁定要拿掉的門檻。
- 檔案：`frontend/src/components/ic-analysis/`、`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`。
- 既有 caller／影響面：`EventBatchDisclosurePanel` 之既有隨機對照設定為 IC 事件路徑共用；
  本票路徑之預設值須獨立，**不得**直接改既有常數而影響 IC 路徑。
- 改法：橫幅字面與位置見 `eventscan-banner`；門檻與筆數依 `eventscan-random-control` 080／010，
  且畫面不出現門檻欄、筆數為唯讀顯示。
- **驗證**：vitest——**三格皆須斷言**（R3 兩家指出原驗證只覆蓋第一格，
  「只看 `status` 就隱藏橫幅」之實作可通過）：
  ① `delta.status != "ok"` ⇒ 橫幅 010 渲染且字面逐字相符、015 不渲染；
  ② `delta.status == "ok"` **且** `cluster_dependence_suspected == true` ⇒ 橫幅 **015** 渲染且字面逐字相符、
     010 **不**渲染（R4 修正：此情形下區間確實有回傳，掛 010 之「無信賴區間」與事實矛盾）；
  ③ `delta.status == "ok"` **且** `cluster_dependence_suspected == false` ⇒ 010 與 015 皆不渲染。
  另本票掃描面板之 DOM 不含門檻輸入欄；`nRequested` 顯示值等於觸發批 `n`。
  **mutation**：① 把橫幅條件改為恆不顯示須使①轉紅；
  ② 把判定改為「只看 `delta.status`」（忽略相依旗標）須使②轉紅——
  沒有②，前一條 mutation 抓不到這個實作。
  指令：`cd frontend && npx vitest run src/components/ic-analysis/__tests__/EventScanBanner.test.tsx`
- **邊界**：① 三種狀態各對應一組渲染，**不得合併成單一判斷**：
  `delta.status != ok` ⇒ 010 顯示、015 不顯示；
  `delta.status = ok` 且 `cluster_dependence_suspected` 為真 ⇒ 010 不顯示、**015 顯示**；
  `delta.status = ok` 且該旗標為假 ⇒ 兩者皆不顯示。橫幅 020／030 恆顯示；
  ② 後端未回 `delta` 鍵（舊批）⇒ 視同非 ok，顯示橫幅；③ 觸發批 `n=0` ⇒ 不進本畫面。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得把橫幅做成可關閉的提示；不得改 IC 事件路徑之既有 `threshold` 預設值。

---

## §Q 委員「該定而未定」二十六條之逐條處置

> 來源：`handoffs/reconcile/20260920-eventscan-x-consult-r2/sources/` 之必答 6
> （codex 16 條 ＝ Q-C01…Q-C16；composer 10 條 ＝ Q-P01…Q-P10）。
> 本表為**處置**，值本身住 fact-key，不在此複述。

| # | 題 | 處置 |
|---|---|---|
| Q-C01 | 時間邊界（t0 可知時刻、next-open timestamp、N=1 之出場根） | Task 2.3；值＝`eventscan-clock` 010–060；manifest 只存一份 tuple |
| Q-C02 | 零報酬 tie 歸屬 | `eventscan-clock` 090：歸 label=0、不計入勝率分子；由 `win_rate` 之 `> 0` 定義導出，不另設參數 |
| Q-C03 | 交易成本（fee／bid-ask／slippage／latency／partial fill／capacity／borrow） | Task 3.2；主數字不扣，改報 breakeven；算不進公式者見 `eventscan-breakeven` 060 |
| Q-C04 | 資料版本（同一 snapshot、時區、缺 bar） | Task 2.1 驗證條；兩批共用同一 FF run 與同一 kline snapshot，digest 寫入收據；缺 bar 走 `missing_bar` fail-closed |
| Q-C05 | 控制 estimand 之名稱與數值一致 | Task 4.2；主比較之 estimand＝「觸發月聯集內、按觸發筆數配額之無條件買入持有」；全 run 版只得為敏感度且標題須寫明其問題 |
| Q-C06 | 匹配欄位之可得性與缺值 | Task 1.1：依 `eventscan-pit-admission` 之封閉白名單准入（🔴 初稿之「FF 欄一律 pit_feature」已於本輪被兩家以碼證推翻）；欄值為 NaN 之根視為條件不成立且須可列舉其筆數（Task 2.2 邊界④） |
| Q-C07 | 依賴單位（事件叢集、持有窗重疊、cluster 與 n_eff） | Task 2.2（觸發側壓成段）＋ Task 5.2（以段為重抽單位）；`n_effective` 既有欄保留 |
| Q-C08 | 候選不足之處置 | Task 4.3：不縮 n、不放寬互斥、不抽相鄰根；回 `eventscan-failure-reasons` 040／050 |
| Q-C09 | 可重現性（seed、digest、重抽次數、禁多 seed 挑最好） | Task 4.1／5.2：seed 與 digest 寫入收據；重抽次數不足即 fail-closed；本票不提供多 seed 介面 |
| Q-C10 | 多重比較（多 N、多條件探索） | `eventscan-scope` 050：本票不做調整，改以 `eventscan-banner` 020 之字面揭露。🔴 **本輪修正**：初稿之「主 horizon 須先寫下再看表」**沒有任何機械承載**（委員指出：Task 6.2 只有 horizons 輸入，無 pre-registration 欄／收據／UI 狀態）⇒ 那是忠告不是統計控制。改為 **Task 5.1 之收據須記錄「本次請求宣告之主 horizon」與其送出時刻**，且該欄一經寫入不得於同一批之後續請求改寫；做不到即列殘留 RESID-7（**不是** RESID-5，後者已用於段間相依），不得以散文冒充控制 |
| Q-C11 | 尾端分母（逐 N 之有效 n、被排除數、兩批同一 availability mask） | Task 3.1 驗證條 ＋ Task 4.4；逐 `h` 回 `n` 與排除筆數，兩批用同一 eligibility 定義 |
| Q-C12 | 方向與部位（long／short sign、sizing、單筆 vs 累積） | `direction` 由觸發批帶入（Task 4.1）；`eventscan-scope` 010：本票不做累積報酬／權益曲線 |
| Q-C13 | 條件發現與驗證（同一資料搜出來的條件） | `eventscan-banner` 020 為**不可解除**之字面揭露；本票不做時間序 holdout（見 §N 殘留 RESID-2） |
| Q-C14 | label 之用途（是否只作 metadata、by-label 是否隱藏） | Task 2.4：主表禁 by_label，判定點在呼叫端並穿透 `analyze_tables`；`eventscan-clock` 080 綁 `max(horizons)`；label 不出現在任何使用者可見欄 |
| Q-C15 | 因果語句（條件報酬差 vs 預測關聯 vs 因果效果） | 措辭固定為「條件報酬差」；由 `eventscan-banner` **010／015／020** 三條承載（015 為 R4 新增且同含「平均差為正不得讀成會賺」，R5 指出原處置漏列）；本票不宣稱因果 |
| Q-C16 | 單標的邊界與未來 pooled 之前置 | `eventscan-scope` 040；pooled estimand／symbol 等權／跨標的 snapshot 為 GAP-4 之前置，見 §N 殘留 RESID-1 |
| Q-P01 | 連續 True 根是否每根都進場 | Task 2.2（與 Q-C07 同群） |
| Q-P02 | 主表禁 by_label／prevalence | Task 2.4；`prevalence`／`lift` 既有鍵保留但本票畫面不顯示（Task 6.3） |
| Q-P03 | 持有時鐘鎖定從成交根起算 | Task 2.3（與 Q-C01 同群） |
| Q-P04 | 成本之揭露字面 | Task 3.2 ＋ `eventscan-banner` 030 |
| Q-P05 | 條件列之時間對齊（FF 列時間戳＝K 線開盤） | Task 2.1 驗證條；`eventscan-clock` 100；與 IC 路徑之同型錯誤同一判準 |
| Q-P06 | 重疊持有不得加總成資金曲線 | `eventscan-scope` 010 |
| Q-P07 | 多條件反覆嘗試 | 同 Q-C10 |
| Q-P08 | 排除窗過寬使對照變成「條件區 vs 平靜區」 | Task 4.3 收據須揭露 excluded 比例；比例過高時標警告，**不自動改寬度**（門檻值＝`eventscan-params` 070） |
| Q-P09 | `ret_entry` vs `ret_label_anchor` 主顯示 | `eventscan-return-columns` 010／020；Task 5.1 驗證條釘住「不得以 `ret_label_anchor` 相減」 |
| Q-P10 | 單標的先做對抽樣契約之未來成本 | 同 Q-C16；抽樣仍 fail-closed 於單一 symbol×timeframe |

---

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：`RISK-HIT` 含 a／d ⇒ 必附可證偽之 mutation 設計。本 SPEC 於下列 Task 逐條指定
  mutation 與其應轉紅之斷言：1.1、2.2、2.3、2.4、3.1、3.2、4.1、4.2、4.3、4.4、5.1、5.2、6.4。
  設計依據引 `docs/TEST_DESIGN_CHARTER.md`。
- 🔴 **mutation 之驗收組合一律指定到 `eventscan-test-vectors` 之具名列**，不得只寫「對某批跑」。
  本輪已因此改掉三處：3.1 由 030（`n = 1`，mutation 不會被觸發）改為必跑 035；
  4.3 與 5.2 由未凍結之隨機抽樣改為 045／055 之凍結 fixture。
  判準＝**該 mutation 改的那個判定，在該組合上是否真的會被執行**；答不出來就是假存活。
- **測試層級**：
  - 單元：`tests/momentum/event_samples/`（條件引擎、壓縮、時鐘、統計量、breakeven、抽樣、bootstrap）
  - 整合：`tests/api/`（掃描端點、比較端點）
  - Golden 對照：`tests/golden/eventscan/`（§G）
  - 前端：`frontend/src/components/ic-analysis/__tests__/`（vitest）
  - 全部可獨立跑，不需 `run_api.py`。
- **防假綠**（本票之具體形態，非泛稱）：
  1. **既有測試斷言一律 diff**——不得為了讓新行為通過而放寬或刪除既有斷言。
     已知會被誘惑放寬者：`test_zero_candidates_yields_empty_batch`（Task 4.3 邊界②明示須以新測試承接，不得改它）。
  2. **參考值須由測試獨立算出**，不得呼叫被測函式再比對自己。
  3. **「兩端一致」型不變式，驗收組合必須含一組使用者改過參數（`k`／`h`）的真實批**——
     預設參數下 `max(深度, 窗)` 與 `窗` 同值，綠燈只證明預設路徑沒壞。
  4. **mutation 須跑在會觸發該判定的組合上**——改的判定在該組合上不會被觸發時會得到假存活。
  5. **隔離 worktree 跑 mutation 時 `skip` 與 `pass` 在 rc 上無法區分**（`data_cache/` 在 `.gitignore` 內）：
     須 symlink 真實 `data_cache/`，且 harness 須把 stdout 含 `skipped` 判為無效。
- **邊界目錄**（本任務適用者 ✔ 並對應 Task）：
  - ✔ 空 DF（Task 1.3 邊界③、2.1 邊界①、4.3 邊界②）
  - ✔ 全 NaN 列（Task 2.2 邊界④）
  - ✔ std=0（Task 3.1 邊界②）
  - ✔ 重複／亂序 timestamp（Task 2.1 驗證條之特徵列鍵比對）
  - ✔ 大尺度浮點 reduction（Task 3.1 加權標準差之數值穩定性）
  - ✗ Inf（FF 欄已有 inf 閘，本票不新增輸入面）
  - ✗ API 重啟／並發寫（本票不新增可變狀態）
  - ✗ OOM 降載（單標的單 run，規模防護屬 GAP-6）

---

## §R 回退

- 每個 Phase 獨立 commit，可單獨 `git revert`。
- Phase 1–5 之新行為一律以**新參數或新鍵**承載，缺省等同現況 ⇒ 不啟用即完全回退。
- Phase 6 之新畫面為獨立路由／面板，不改既有 IC 事件面板之既有行為。
- §G Golden FAIL ⇒ 不 merge。
- 🔴 Task 4.1／4.2／4.4 動到 `random_control.py` 之共用函式：回退判準為
  「既有呼叫端之產出與改動前 byte 級相同」，此條在每個 Phase 之驗收中重跑，不只在 Phase 結束時跑一次。

---

## §N N/A 登記與殘留

### N/A

> Golden／Baseline 一段**全段已填、未被豁免**（見上）。下列僅為其他必填段之登記。

- **統計檢定清單之完整套用**：N/A — 本票只做 Δ 之 bootstrap 區間一項（Task 5.2）；
  HAC／FDR 等屬序列型 IC 路徑，本票不觸及。
- **API 重啟／並發寫／OOM 降載之邊界測試**：N/A — 本票不新增任何可變狀態，規模防護屬 GAP-6。

### 殘留

- **RESID-1 多標的 pooled estimand** — `為何現在不做: user-ruling:2026-09-20 使用者裁定先做單標的，多標的併 GAP-4`；
  觸發：研究宇宙變為多標的時；登記處：`docs/IC_QUANT_GAP_REGISTRY.md` #4。
  已知成本（出處＝偵察輪收斂檔 `handoffs/reconcile/20260920-eventscan-x-consult-r1/synth.md` 末列）：
  抽樣契約與規則身分閘屆時須改契約，非純新增。
- **RESID-2 條件之樣本外驗證（時間序 holdout）** — `為何現在不做: needs-research:同一資料搜出之條件，其 holdout 切法與
  多重比較揭露之關係尚無本專案之定論；SPLITUNIFY 之切分契約是否可直接套用於事件掃描路徑未查`；
  觸發：使用者要求把掃描結果當「驗證過的策略」使用時；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`「兩路涵蓋宣告」節。
  在此之前以 `eventscan-banner` 020 之不可解除字面承擔。
- **RESID-3 事件型 IC 共用本票之 breakeven** — `為何現在不做: blocked-by:Task 3.2 尚未落地；共用前須先有一個已驗收之實作`；
  觸發：Task 3.2 通過驗收後；登記處：`docs/IC_QUANT_GAP_REGISTRY.md` #3。
- **RESID-4 全 K 線表改用同一時鐘後展示** — `為何現在不做: user-ruling:2026-09-20 使用者要的是「買入後持有 N 根」單一口徑，
  兩張表並存正是缺口 7 之成因`；觸發：使用者明確要求看 t0 錨口徑時；登記處：`docs/IC_QUANT_GAP_REGISTRY.md` #3。
- **RESID-5 段間序列相依之正式處理（block bootstrap 之區塊長度選擇或 HAC）**
  — `為何現在不做: needs-research:段之間仍可能存在行情層級相依，正確的區塊長度選擇法（例如自動 block length）
  在本專案尚無定論，且需先有真實批之段間自相關量測才能選`；觸發：`eventscan-params` 080 之診斷在真實批上
  經常為真時；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`「兩路涵蓋宣告」節。
  在此之前以 Task 5.2 之診斷旗標承擔：旗標為真時畫面掛 `eventscan-banner` **015**（區間已算出但標明可能過窄），**不是** 010 之「無信賴區間」——該情形下區間確實有回傳（**不是**假裝沒有這個問題）。
- **RESID-11 `manifest.present_timeframes` 與 `groups` 之週期集合不一致**
  — `為何現在不做: blocked-by:該欄由 Feature Factory 之 manifest 產出端寫入，本票不改 FF
  （§C 明文）；且本票已以「以 groups 為準」繞開，不影響掃描正確性`；
  觸發：下一次動 FF 之 manifest 產出端時；登記處：本 SPEC §N（ROADMAP 只放票列 pointer）。
  實況：最終 run 之 `present_timeframes` 宣告 `["1h"]`，而 `groups` 含 402 個 `12h` gid
  ——**宣告與內容矛盾**，任何以 `present_timeframes` 判週期之下游都會漏掉一半資料。
- **RESID-10 共用 `d*` 快取之可追溯性（Feature Factory）**
  🔴 **定性輪已跑完**（使用者 2026-09-21 逐字：「那個bug你跟委員要先確認是真的是bug
  還是特殊原因才這樣定義，不要直接修掉」）。該裁定**直接擋下一次針對非缺陷的修改**——
  主委原判之四型中，兩型經委員以本 run 實跑判為設計意圖、一型因主委配對錯誤而不成立。
  — `為何現在不做: user-ruling:2026-09-21 使用者裁定先定性再修，且另立票；
  該路徑在 Feature Factory 預處理層，命中高風險原則 (a) 數值／資料品質，
  須走完整管線，不得在本票內順手改`；
  觸發：**已觸發**，票號 `FFDSTAR`，本票之新 FF run 產生後立即開；
  登記處：`docs/ROADMAP.md` 之工作線表。
  🔴 **定性已完成，結論與主委原判相反**（`handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md`）：
  主委原列之四型症狀，兩家逐型判定為——**兩型為設計意圖、一型不成立（主委配對錯誤）、
  僅 provenance 一項為真缺陷**。
  ⇒ 本殘留之範圍**限縮為單一議題**：共用之 `d*` 快取檔跨 run 覆寫、且無 per-column 收據，
  導致無法追溯任一 run 當下所用之 `d*`（可追溯性／耐久性）。
  ⇒ 原列之「`apply_to=\"non_stationary\"` 之 ADF 閘與 `d*` 計算為兩條獨立判斷」
  **不是缺陷而是設計**：委員以本 run 校準窗實跑，該閘判 `EMA_200`／`EMA_233` 平穩故不轉換。
  ⇒ 下一步**須先由使用者確認是否值得投入**，非自動進入修正。
- **RESID-9 同一個值在生成區塊外被手打，無機械閘可擋**
  — `為何現在不做: user-ruling:2026-09-21 使用者對代號 B 之裁定逐字含「不新建工具」；
  且手寫偵測之 status_scope 不含 docs/ 其餘檔，擴充它即為新建治理工具`；
  觸發：使用者解除「不新建工具」之限制，或 `status_scope` 因他票需要而擴充至 `docs/` 時；
  登記處：`docs/AGENTOPS_PROBLEM_DEFINITION.md`。
  🔴 **實證發生率（本票兩輪）**：R2 之十九條中有**四條**屬此形態
  （§G 散文與 golden-reference 080 不同步、收斂檔宣稱之處置與 Task 4.4 字面不符、
  橫幅解除條件兩處不同步、Q-C10 指向之殘留 ID 與 §N 用途衝突）。
  在此之前只能靠兩家對抗審，且**會漏**。
- **RESID-7 主 horizon 之預先登記無法擋「重跑一批新的」**
  — `為何現在不做: blocked-by:本票只在同一批內鎖住 primary_horizon；使用者換條件重跑一批新的即可繞過，
  要擋住那個需要跨批之研究登記簿（研究 id、條件式 digest、宣告時序），其資料模型不在本票範圍`；
  觸發：出現跨批之研究登記需求或使用者要求可稽核之探索紀錄時；登記處：`docs/IC_QUANT_GAP_REGISTRY.md` #3。
  在此之前以 `eventscan-banner` 020 之不可解除字面承擔。
- **RESID-8 間接呼叫繞過 caller matrix**
  — `為何現在不做: user-ruling:2026-09-11 使用者定「與委員判定繞過成本≥合規成本即收」；
  AST 走訪已擋住全部語法直接呼叫，再擋 getattr／反射／包裝函式需動態偵測，成本遠高於效益`；
  觸發：實際出現以間接方式呼叫 `analyze_tables` 之生產路徑時；登記處：`docs/IC_QUANT_GAP_REGISTRY.md` #3。
- **RESID-6 逐欄因果 provenance（取代 group 白名單）**
  — `為何現在不做: blocked-by:reference manifest 無 available_at／causal 欄，逐欄因果證明須 Feature Factory
  在產出端補 provenance，而本票 §C 明文不改 FF`；觸發：Feature Factory 下次動產出端 schema 時；
  登記處：`docs/IC_QUANT_GAP_REGISTRY.md` #3。誠實邊界見 `eventscan-pit-admission` 070。

### 兩路涵蓋宣告（使用者 2026-09-19 定，每張 IC 票必寫）

本票涵蓋**事件型**一路。全域序列型不在範圍內：本票之估計量以事件為單位，
序列型之 `position`／`turnover` 前提在事件型不存在（`eventscan-breakeven` 020／030 即此差異之落點）。
「支援」含「區分」——Task 2.4 之 `by_label_suppressed_reason` 參數即為兩路之機械區分點
（掃描端恆傳、IC 事件路徑不傳），不得對兩路一律套用同一行為。
