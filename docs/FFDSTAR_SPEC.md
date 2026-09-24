# FFDSTAR — 每個 FF run 自帶 `d*` 收據（可追溯性） — SPEC

> 來源診斷：`handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md`（定性輪）　|　日期：2026-09-21　|　對應 TODO：`docs/FFDSTAR_TODO.md`（本 SPEC 凍結後生成）
>
> **要解的問題（一句話）**：事後查不到某個 FF run 當時用了什麼 `d*`。

---

## §RISK 風險分級

- **大小**：中。動單一模組（Feature Factory 預處理層）＋其既有 caller。
- **命中高風險原則**：無。
  - 不命中 (a)：**不改任何數值**。本票只新增一份「這次實際用了什麼」的收據，
    特徵值、欄集合、`d*` 的選法與套用邏輯皆不動。
  - 不命中 (b)：改動限於 `momentum/FeatureEngineering/preprocessing/`；不跨 `api/`／`frontend/`。
  - 不命中 (c)：單一 Phase 可獨立回退。
  - 不命中 (d)：不影響 ML／回測路徑之任何輸入值。
- RISK-HIT: none
- 🔴 **膨脹升級訊號（命中任一即當場升級為大任務、退回重走）**：
  ① 需要改 `feature_manifest.json` 之 schema（那是契約改動）；
  ② 需要改 `_find_min_d`／`_frac_diff_ffd`／`_get_non_stationary_columns` 任一之行為；
  ③ 新增之檔使既有 golden 或輸出大小斷言轉紅。

---

## §A 假設與待使用者確認

### 已驗證事實

- FACT-RECEIPT: `sed -n '327,331p' momentum/FeatureEngineering/preprocessing/_d_star_cache.py` → 印出
  `return cache_dir / f"d_star_{symbol}_{timeframe}_{fhash}.json"`
  ⇒ **檔名只含 symbol／timeframe／fracdiff 參數雜湊，不含 run 識別碼**（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `ls -la data_cache/feature_preprocessing/d_star_*.json` → 印出 7 個檔，
  `ETHUSDT/1h` **僅一個**（`d_star_ETHUSDT_1h_dcc154ced6b6.json`，最後寫入 `Sep 9 20:45`）
  ⇒ 同一 symbol×timeframe 之全部 run 共用一檔，後寫覆蓋（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `jq -r '.row_count'` 該檔 → 印出 `10441`；而 run `4a8a0b37…` 之列數為 `20352`
  ⇒ 現存內容屬另一 run，reference run 當時之 `d*` **已不可得**（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `find data_cache -name "d_star_*.json"` 之結果全部位於
  `data_cache/feature_preprocessing/`，**run 目錄內 0 個**（Claude 實跑 2026-09-21）
- FACT-RECEIPT: `jq -r '.entries | length'` 該檔 → 印出 `148`，而 reference run 之欄數為 `437,110`
  ⇒ 收據之覆蓋率遠低於欄數（Claude 實跑 2026-09-21）

### 定性輪之結論（本票範圍之唯一依據）

`handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md`：兩家逐型判定——
**① 有紀錄且有套用＝設計意圖；② 有紀錄但 `d` 不符＝不成立（主委配對錯誤）；
③ 無紀錄但有套用＝缺陷（provenance）；④ 有紀錄但未套用＝設計意圖；
⑤ `row_count` 與 run 列數不同＝缺陷（provenance）。**

⇒ **本票只處理 ③⑤ 這一件事：可追溯性。** 不碰 ①④ 之設計、不重開 ②。

🔴 **數值正確性不在本票範圍且未被質疑**：快取有數值指紋校驗
（`_d_star_cache.py::get_by_value_fingerprint`），值對不上即 miss 重算 ⇒
一個 run 不會誤用另一 run 的 `d*`。**壞的是紀錄，不是計算。**

### 🔴 待使用者確認（否決點，未確認前不得**交付**）

**本票會讓每個 FF run 多產出一個檔**，而 CLAUDE.md 明訂
「**Never** … change output size without user approval」。

⇒ **唯一需要使用者裁示的是輸出增量本身，且必須帶著實測數字去問**
（技術類選擇不問使用者，依既有裁定交委員會——結果見下「委員會已裁定之技術選擇」）。
⇒ 因此順序為：Task 1.1／1.2 實作 → Task 1.3 量出絕對位元組與佔比 → **帶數字請使用者核可** → 交付。
**未取得核可前不得宣告本票完工**；使用者否決即整票回退（§R）。

`待確認：無`（實作前無待決；輸出增量之核可屬**交付前**關卡，非實作前關卡）

### 委員會已裁定之技術選擇（R1 收斂，不再是待決）

1. **落點＝`data_cache/feature_preprocessing/`，檔名含 `config_hash`。**
   🔴 **決定性理由（composer 實查）**：若落在 run 目錄，既有
   `tests/feature_engineering/test_failopen_correctness.py:348::test_v3_multi_tf_btc_matches_frozen_baseline`
   會把新 JSON 當資料檔而使檔案集合比對轉紅 ⇒ **直接命中 §RISK 升級訊號③**。
   選共用目錄則 run 目錄之檔案集合**逐位元組不變**，該測試維持綠。
2. **覆蓋率＝全部進入判定之欄，各帶 `applied` 與 `reason`／`source`。**
   理由（codex）：只記已套用者**解決不了型③**——不在收據內的欄有兩種可能
   （未進 fracdiff／進了但沒記），無法區分等於沒做。
3. **既有 7 個共用檔＝保留原狀不動**（面向未來不溯及既往，2026-08-05 使用者定死）。
4. **本票套用 `fact_keys` 生成區塊**（codex `P2-07`）：主委原判「值很少故不套用」不成立——
   可觀測之值已含四類原因碼、`source` 值集、收據頂層欄位、落點路徑、三條升級訊號。

### 🔴 唯一之閘序（本 SPEC 內先前三處互斥宣告，以本段為準）

R1 兩家各自指出 §A／Phase 1／Task 1.2 對「何時可開工」給了互斥條件。**統一為**：

```
Task 1.1（收集，不落檔）  → 可立即開工，不需任何裁示
Task 1.2（落檔）          → 可立即開工（落點與覆蓋率已由上述裁定確定）
Task 1.3（量測輸出增量）  → 依賴 1.2
使用者核可輸出增量        → 交付前關卡，非實作前關卡
```

**沒有任何 Task 以「等使用者裁示」為開工條件。** 使用者之核可只擋**交付**。

### 已確認結果（2026-09-21 使用者裁定，逐條見下）
- `2026-09-21 使用者裁定：先確認是真的是 bug 還是特殊原因才這樣定義，不要直接修掉` → 定性輪已跑完
- `2026-09-21 使用者裁定：同意做「每個 run 自帶 d* 收據」`

---

## §K 本 SPEC 註冊之 fact-key

> 下列區塊由 `scripts/fact_keys.json` 生成，**禁手改**。改值＝改該檔後跑
> `bash scripts/gen_fact_key_blocks.sh --write`。TODO 與測試引用同一值時掛同一區塊，不得手打。
> （採用理由：R1 之 codex `P2-07` 推翻主委「值很少故不套用」之判斷。）

### K-1 收據 schema

<!-- BEGIN GENERATED: ffdstar-receipt-schema -->
| 序 | 欄 | 型別／值集 | 說明 |
|---|---|---|---|
| 010 | `applied` | 布林 | 本次 run 該欄是否實際套用 fracdiff |
| 020 | `d` | 浮點；`applied` 為真時**必填**，為假時**必須缺席** | 本次實際使用之分數階；缺席與 `null` 語意不同，須以缺席表達 |
| 030 | `source` | `cache_hit` ｜ `search` ｜ `search_error_default`；`applied` 為真時必填 | `d` 之來源＝命中既有快取、本次重新搜尋，或**搜尋拋例外後現行碼以 `d=1.0` 套用**（`feature_preprocessor.py:3035-3060` 之 `except Exception` 分支；R3 codex P1-02）——本票只如實記錄此分支，不改其行為；該分支是否應 fail-closed 屬平穩化處理之數值正確性，交另案研究 |
| 040 | `reason` | 封閉集合，見 `ffdstar-skip-reasons`；`applied` 為假時必填 | 未套用之原因 |
| 050 | 頂層 `symbol`／`timeframe`／`config_hash` | 字串 | run 之身分；`config_hash` 為本票解決 owner mismatch 之關鍵欄 |
| 060 | 頂層 `row_count`／`time_range` | 整數／物件 | 與 run 對齊；與既有共用快取之同名欄語意相同 |
| 070 | 頂層 `fracdiff_hash` | 字串 | fracdiff 參數雜湊；與既有快取檔名所用者同源 |
| 072 | 頂層 `execution_outcome` | `ran` ｜ `skipped_no_statsmodels` ｜ `skipped_disabled` ｜ `skipped_no_target_columns` | 🔴 **空 `entries` 有多種成因**，只看 entries 無法區分「沒跑」與「跑了但零欄」；本欄為唯一區分點（R2 委員指出 K-1 原無此欄） |
| 074 | `source` 與「重跑 byte 級相同」之相容性 | 重跑之 byte 級比對**排除 `source` 欄**；其餘欄須逐位元組相同 | 🔴 首次 `search`、次次 `cache_hit` 時 `source` 本來就會變（R2 委員指出兩條規定互斥）；`source` 記的是「這次怎麼取得」，不是 run 之身分 |
| 080 | 落點 | `data_cache/feature_preprocessing/`，檔名為 `dstar_receipt_<symbol>_<timeframe>_<config_hash>.json`。🔴 **不得**以 `d_star_` 為前綴——`tests/feature_engineering/test_batch2d_dstar_align.py:59` 與 `:104` 對該目錄之 `d_star_*.json` glob 斷言**恰一檔**，同前綴即打破它（R2 委員實查、主委複核） | 🔴 **不得**落在 run 目錄——會使既有 failopen 檔案集合比對轉紅（見 SPEC §A 裁定 1） |
<!-- END GENERATED: ffdstar-receipt-schema -->

### K-2 未套用原因碼（待實作以碼證回填）

<!-- BEGIN GENERATED: ffdstar-skip-reasons -->
| 序 | 值 | 語意 |
|---|---|---|
| 010 | （待實作時以碼證補齊） | 🔴 本表之值集合**不得由主委憑印象填寫**——SPEC 初稿曾杜撰四個不存在的分支名，經 R1 兩家以碼證推翻。實作 Task 1.1 之第一步即為列出 `_apply_fractional_differencing` 之實際離開路徑，逐一對應後回填本表；回填前本表僅此一列 |
| 020 | 回填之機械約束 | 🔴 **只有值符合 `^[a-z][a-z0-9_]*$` 之列才是原因碼**（R3 codex P1-01：原寫法使本表之說明列〔如本列之值〕亦可被當成合法 reason 寫入而通過）。Task 1.1 驗證③：收據中每筆 `applied=false` 之 `reason` 須逐字命中本表中**值合此樣式之列**；回填前本表無任何此樣式之值 ⇒ 任何 `applied=false` 之筆皆使驗證③轉紅，**回填前實作不可能通過驗收** |
| 030 | 🔴 唯一之 column universe（R2 委員指出原文未定義） | 「進入 `_apply_fractional_differencing` 之欄」歧義（df input／numeric columns／layer-filtered targets／selected columns 四者不同）。**定義為**：該函式**實際迭代過**之欄，亦即 `columns` 變數在 `_select_columns` 與 `_filter_fracdiff_target_columns` 之後、`nan_rates` 過濾之前的內容；其後之 `eligible_columns` 與 `skipped_high_nan` 皆為其子集 |
<!-- END GENERATED: ffdstar-skip-reasons -->

---

## §C 約束

- 解耦 7 條：本票改動全在 `momentum/`，不得 import `api/`。
- **不得改變任何特徵數值**、欄集合、欄順序、dtype。
- **不得改 `feature_manifest.json` 之 schema**（命中即升級為大任務，見 §RISK）。
- 不得改 `_find_min_d`／`_frac_diff_ffd`／`_get_non_stationary_columns` 之行為。
- 既有共用快取之讀寫行為**保持不變**——本票只**額外**寫一份收據，不取代快取。
- 驗證一律用真實 run（以 `data_cache/features/ETHUSDT/1h/<config_hash>/feature_manifest.json` 定位）；禁合成 fixture。

---

## §P Phase 與依賴

> 🔴 **本 Phase 表之執行順序＝ Task 1.1 → 1.2 → 1.3**（列序即執行序）。
> 自檢已做：無 forward dependency。

### Phase 1 — 收據落檔（依賴：**FF-NAME 實作完成**——收據之 `config_hash` 與逐欄鍵皆依 FF-NAME 之命名世代與欄名；於 FF-NAME 前實作即鎖在舊世代、須重做驗收〔R3 codex P2-03／composer P2-02〕。三項技術選擇已由 R1 收斂裁定，見 §A）

**Task 1.1 — 在預處理層收集「本次實際套用之 `d`」**
- 目標：讓一次 run 結束時，手上有一份「欄 → 實際用的 `d` ／ 未套用及其原因」。
- 檔案：`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
  （`_apply_fractional_differencing_serial` 與 `_apply_fractional_differencing_parallel` 兩條路徑，
  以及 `_apply_fractional_differencing` 之 eligible／skip 分支）。
- 既有 caller／影響面：三條路徑之既有回傳值與副作用**不得改變**。
  🔴 **不得比照 `self._fracdiff_processed_columns` 之生命週期**（R1 兩家指出）：該屬性於
  `feature_preprocessor.py:2471` 與 `:2484` 被重設，**其內容是最後一次 transform 的殘局**，
  不是整個 run 的清單；且其型別為 `set[str]`（`:150`），**不帶 `d` 值**。
  ⇒ 收據容器須為 **run 層級、不被 per-transform 重設**之累加結構。
  🔴 **「掛在 parent 實例上」不夠**（R2 兩家指出，主委實跑對證）：生產路徑對 compact-aligned group
  會另建 **sibling `FeaturePreprocessor`**（`feature_preprocessor.py:813` 與 `:979` 之 `native_pp`），
  於其上跑 `_transform_single` 後**丟棄該實例**。只累加在 parent 上會**漏記這些欄**。
  ⇒ 本 Task 須定義**明確之 owner／merge 契約**：sibling 之累加結果須在丟棄前併回 owner；
  併入時鍵衝突即 fail-closed（不得後寫覆蓋——那正是本票要消滅的形態）。
  **驗證須含一條走 sibling 路徑（`feature_preprocessor.py:813`）之 `pytest` 案例**，
  斷言該路徑之欄亦出現在收據中；否則該契約無人守。
- 改法：**第一步是盤出實際分支**——R1 兩家指出本 SPEC 初稿所列之「四個既有分支」
  （`applied`／`skipped_not_selected`／`skipped_high_nan`／`skipped_filtered`）**在碼上不存在**，
  是主委未經查證的杜撰。
  ⇒ 本 SPEC **只定義收據必須涵蓋之語意**，不指定分支名：
  **每一個進入 `_apply_fractional_differencing` 之欄，收據須有且恰有一筆**，
  含 `applied`（布林）、`d`（`applied` 為真時必填）、`source`（`d` 從何而來）、
  `reason`（`applied` 為假時必填）。值集合見 §K 之生成區塊。
  實作時須先以碼證列出實際的離開路徑，再逐一對應到上述語意；**新增任何判斷分支即為違規**。
- **驗證**（`pytest`，兩層）：
  ① **窮盡性**：收據之欄集合 `==` 進入該函式之欄集合（逐欄，非計數）；
  任一欄缺席或重複即 FAIL。此條不依賴任何既有屬性，只依賴函式之輸入。
  ② **`d` 值正確性**：🔴 **不得**以 `_fracdiff_processed_columns` 核對——它沒有 `d` 值（見上）。
  改用**獨立重算**：取收據之 `d`，以 `_frac_diff_ffd` 重跑該欄，與落檔值比對
  （相關性 `>= 0.9999`；此即主委 2026-09-21 追查時實際用過的 oracle）。
  ③ **原因碼封閉**（R3 composer P2-01：原只寫在 K-2 表，Task 段漏列）：每筆 `applied=false` 之 `reason` 須逐字命中 `ffdstar-skip-reasons` 中值符合 `^[a-z][a-z0-9_]*$` 之列；`applied=true` 之 `source` 須屬 `ffdstar-receipt-schema` 030 之三值。
  **mutation**：把任一離開路徑之記錄拿掉，須使①轉紅；把收據之 `d` 改寫成固定值，須使②轉紅；把某筆 `reason` 寫成 K-2 表之說明文字，須使③轉紅。
  指令：`pytest tests/feature_engineering/preprocessing/test_d_star_receipt.py -q`
  （🔴 測試樹依既有 `test_d_star_*.py` 之所在，非主委初稿所寫之 `tests/momentum/...`）
- **邊界**：① fracdiff 整段被 early return（`HAS_STATSMODELS` 為 false）⇒ 收據為空且須可區分
  「沒跑」與「跑了但零欄」；② `eligible_columns` 為空；③ parallel 路徑之多 worker 結果合併後
  不得有重複鍵，重複即 fail-closed。
- **存活至**：Phase 1 完工後保留（Task 1.2 消費它）。
- **覆蓋風險**：無。
- 不可做：不得改動任何既有分支之條件；不得在此 Task 落檔。

**Task 1.2 — 落檔為收據**
- 目標：把 Task 1.1 收集到的東西寫成一份檔。
- 檔案：`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`（落檔呼叫點）；
  新增 `momentum/FeatureEngineering/preprocessing/_dstar_receipt.py`（序列化）。
- 既有 caller／影響面：落檔為**新增副作用**。落點與覆蓋率**已由 R1 收斂裁定**（見 §A），
  本 Task **無待決、可立即開工**。
- 改法：以既有 `DStarCache.flush_atomic` 之同型原子寫入（temp ＋ `os.replace`），
  落於 `data_cache/feature_preprocessing/`，檔名含 `config_hash`。
  內容含 `symbol`／`timeframe`／`config_hash`／`row_count`／`time_range`／
  `fracdiff_hash`／逐欄記錄。**欄名一律用落檔當下之欄名**（不做任何正規化——
  共用快取之鍵不帶週期前綴正是本票要解的可追溯性問題之一部分）。
- **驗證**（`pytest`）：跑一個小 run 後，收據之 `config_hash` `==` 該 run 之 `config_hash`；
  收據逐欄之 `d` 以 Task 1.1 驗證② 之獨立重算 oracle 核對（**不得**用
  `_fracdiff_processed_columns`，它沒有 `d` 值）；同一 run 連跑兩次，收據 byte 級相同。
  另**斷言 run 目錄之檔案集合與改動前逐項相同**——此條直接對應 `§RISK` 升級訊號③。
  **mutation**：把 `config_hash` 改為寫入 `symbol`，須使第一條斷言轉紅；
  把落點改回 run 目錄，須使「run 目錄檔案集合不變」之斷言轉紅。
  指令：`pytest tests/feature_engineering/preprocessing/test_d_star_receipt.py -q`
- **邊界**：① 落點目錄不存在 ⇒ 建立而非失敗；
  ② 🔴 **寫入失敗 ⇒ 整個 run 判失敗（fail-closed）**。
  R1 兩家一致指出：降級為 `logger.warning` 會再產出一個「成功但沒有 per-run `d*` 紀錄」的 run，
  **正是本票要消滅的型③**，且與 CLAUDE.md「擬合參數（逐字含 `d*`）必須持久化才能上線」鐵律衝突。
  主委初稿之「收據是診斷物不是產物」不成立——它是本票要新增之 provenance 產物。
  🔴 **fail-closed 不會從既有之原子寫入接縫自然得到**（R2 委員指出）：既有 cache flush 會吞例外，
  L6.5 之 wrapper 亦可能把新 writer 之例外吃掉。⇒ 本 Task 須**明確指定一個會把例外往上傳的接縫**
  （實作時以碼證指出該位置與其例外傳播行為），並加一條 `pytest`：注入寫入失敗（例如唯讀目錄）
  後，**該 run 之對外結果為失敗**；若僅記 log 而 run 仍成功即 FAIL。
  ③ 同一 run 重跑 ⇒ 覆寫自己的收據（同 `config_hash`，不涉跨 run 覆蓋）；
  byte 級比對之範圍見 `ffdstar-receipt-schema` 074（排除 `source` 欄）。
- **存活至**：本票交付後保留。
- **覆蓋風險**：無。
- 不可做：不得改既有共用快取之讀寫；不得因寫收據而改變 run 之任何既有輸出。

**Task 1.3 — 輸出面影響之量測與揭露**
- 目標：把「多產一個檔」這件事量出來，交使用者驗收。
- 檔案：無產品碼改動；新增量測腳本與收據。
- 既有 caller／影響面：無。
- 改法：對一個真實 run 量測收據檔之位元組大小與其佔該 run 總輸出之比例，寫入 run receipt。
- **驗證**（`pytest` 或腳本 rc=0）：量測輸出含絕對位元組數與百分比兩者；
  既有 golden 與輸出大小斷言**全部維持綠**（若有任一轉紅，即命中 §RISK 之升級訊號③）。
  指令：`bash scripts/restore_golden_inventory.sh` 後跑既有 FF golden 測試逐檔明列路徑。
- **邊界**：① run 目錄本身很小時百分比失真 ⇒ 須同時報絕對值；② 多 symbol 時逐 symbol 報。
- **存活至**：本票交付後保留為收據。
- **覆蓋風險**：無。
- 不可做：不得以「檔很小所以不用問」略過 §A 之否決點。

---

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：`RISK-HIT: none` ⇒ 不強制。但本 SPEC 仍於 Task 1.1／1.2 各指定一條
  可證偽之 mutation，因為兩者皆宣稱「記錄與實際一致」，該宣稱若無 mutation 即為空殼。
- **測試層級**：單元（收集與序列化）＋ 整合（跑一個小 run 後讀收據）；
  可獨立 `pytest tests/feature_engineering/preprocessing/` 跑，不需 `run_api.py`。
- **防假綠**：
  1. 「收據與實際一致」不得以「讀自己剛寫的檔」自證——須以 **Task 1.1 驗證② 之獨立重算 oracle**
     （取收據之 `d`、以 `_frac_diff_ffd` 重跑該欄、與落檔值比對）核對。
     🔴 **不得**以 `_fracdiff_processed_columns` 為 oracle——它是不帶值之 `set[str]`，核對不了 `d`
     （R1 指出；R2 指出本節仍留著該錯誤指涉，屬「只修被點名處」之復發）。
  2. 既有測試斷言一律 diff，不得放寬。**特別列名**：
     `tests/feature_engineering/test_batch2d_dstar_align.py`（該目錄 `d_star_*.json` 恰一檔）與
     `tests/feature_engineering/test_failopen_correctness.py`（run 目錄檔案集合）**皆須維持綠**。
  3. 用真實 run，禁合成 fixture。
- **邊界目錄**：✔ 空輸入（`columns` 為空）／✔ 並行與 sibling 實例之合併重複鍵／
  ✔ **寫入失敗 fail-closed**（🔴 非「降級」——R1 已推翻降級寫法，本節字面同步更正）；
  ✗ 大尺度浮點（本票不算任何數值）／✗ 並發寫（單 run 單寫者）。

---

## §R 回退

- 單一 Phase，可整體 `git revert`。
- 收據落檔為純新增副作用：不啟用即完全回退，既有 run 之輸出逐位元組不變。
- 若 Task 1.3 量出之輸出增幅使使用者否決 ⇒ 整票回退，不留半套。

---

## §N N/A 登記與殘留

### N/A

- **§G Golden／Baseline**：N/A — 本票不改任何數值、不碰特徵計算路徑；
  「行為不變」由**既有** FF golden 測試承接（Task 1.3 明列其須維持綠）。
  🔴 若實作中發現任何既有 golden 轉紅，即為命中 §RISK 升級訊號③，當場停工重新分類。

### 殘留

- **FFDSTAR-R1 既有 7 個共用快取檔之來源 run 不明**
  — `為何現在不做: user-ruling:2026-08-05 使用者定死「修正只考慮以後，不把舊錯誤包回來」`；
  觸發：使用者要求回溯查證某個既有 run 之 `d*` 時；登記處：本 SPEC §N（ROADMAP 只放票列 `RM-FFDSTAR` 之 pointer，不重複列殘留識別碼）。
  🔴 **誠實邊界**：本票**救不回過去**。reference run（特徵落檔 `Jul 4 15:35`）當時之 `d*`
  已被 `Sep 9 20:45` 之另一 run 覆寫，除重跑外無法取得。
- **FFDSTAR-R2 `/api/v1/features/generate` 回之 `task_id` 於 `/task/{task_id}` 查不到**
  — `為何現在不做: blocked-by:本票範圍限於預處理層之可追溯性，該缺陷在 api/ 之任務登記路徑，
  屬不同模組且需獨立定性（是否為已知設計）`；
  觸發：**已觸發**，2026-09-21 主委跑 FF 重跑時實遇（三個候選狀態端點皆 404，生成本身正常）；
  登記處：本 SPEC §N（ROADMAP 只放票列 `RM-FFDSTAR` 之 pointer，不重複列殘留識別碼）。
- **FFDSTAR-R3 收據覆蓋率與欄數之落差**
  🔴 **本輪已先拆掉一半**（R1 composer 指出「不實作也能拆」，主委照做）：
  FACT-RECEIPT: FF 重跑之 L6.5 日誌逐字印出
  `fracdiff_apply_to=non_stationary fracdiff_layers=['L1', 'L2']`（Claude 實跑 2026-09-21）
  ⇒ **L3 以上之欄從不進入 fracdiff**，437,110 不是候選母體；候選僅 L1＋L2
  （同次 run 之 L2 完成量為 44,827 欄）。
  ⇒ 剩下待答的只有「L1＋L2 候選中，被 ADF 判為非平穩者是否恰為 148」。
  — `為何現在不做: needs-research:上述剩餘問題須以真實 run 之逐欄判定計數回答，
  而該計數正是 Task 1.1 之產出；在其上線前無獨立來源`；
  觸發：Task 1.1 完工並跑過一次真實 run 後；登記處：本 SPEC §N（ROADMAP 只放票列 `RM-FFDSTAR` 之 pointer，不重複列殘留識別碼）。
