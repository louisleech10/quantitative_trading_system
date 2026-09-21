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
（技術類選擇不問使用者，依既有裁定交委員會——見下「交委員會決定」）。
⇒ 因此順序為：Task 1.1／1.2 實作 → Task 1.3 量出絕對位元組與佔比 → **帶數字請使用者核可** → 交付。
**未取得核可前不得宣告本票完工**；使用者否決即整票回退（§R）。

`待確認：無`（實作前無待決；輸出增量之核可屬**交付前**關卡，非實作前關卡）

### 交委員會決定（技術選擇，依 2026-07 既有裁定不問使用者）

1. **落點**：收據寫進 run 目錄（例 `<run>/d_star_receipt.json`），或寫進
   `data_cache/feature_preprocessing/` 但檔名加入 `config_hash`？
   （前者使 run 自我描述、搬移 run 即帶著收據；後者不動 run 目錄之檔案集合。）
2. **覆蓋率**：只記「本次實際進入 fracdiff 且完成套用」之欄，
   或連「被 ADF 判為平穩而未轉換」之欄也記一筆（`applied: false`）？
   後者才答得出「這欄到底有沒有被轉換」，但檔會大很多——**此選擇直接決定上述輸出增量**。
3. **既有 7 個共用檔**：保留原狀（只面向未來），或一併標記為「來源 run 不明」？
   🔴 本票預設**保留原狀不動**（面向未來不溯及既往，2026-08-05 使用者定死）。

### 已確認結果（2026-09-21 使用者裁定，逐條見下）
- `2026-09-21 使用者裁定：先確認是真的是 bug 還是特殊原因才這樣定義，不要直接修掉` → 定性輪已跑完
- `2026-09-21 使用者裁定：同意做「每個 run 自帶 d* 收據」`

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

### Phase 1 — 收據落檔（依賴：使用者對 §A 三項否決點之裁示）

**Task 1.1 — 在預處理層收集「本次實際套用之 `d`」**
- 目標：讓一次 run 結束時，手上有一份「欄 → 實際用的 `d` ／ 未套用及其原因」。
- 檔案：`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
  （`_apply_fractional_differencing_serial` 與 `_apply_fractional_differencing_parallel` 兩條路徑，
  以及 `_apply_fractional_differencing` 之 eligible／skip 分支）。
- 既有 caller／影響面：三條路徑之既有回傳值與副作用**不得改變**；收集僅為累加至一個實例屬性
  （比照既有之 `self._fracdiff_processed_columns`）。
- 改法：於既有 `_fracdiff_processed_columns` 旁新增一個 `dict`，
  在**已存在**的四個分支各記一筆：`applied`（含 `d` 與來源＝cache hit 或 search）／
  `skipped_not_selected`（ADF 判平穩）／`skipped_high_nan`／`skipped_filtered`（layer／safe-skip）。
  **不新增任何判斷分支**——只在既有分支上記錄。
- **驗證**（`pytest`）：對 reference run 之一個小 group，收集所得之
  `applied` 欄集合 `==` 既有 `_fracdiff_processed_columns`（兩者必須一致，否則記錄漏了）；
  且 `applied ∪ skipped_*` `==` 進入該函式之全部欄（無欄落在四類之外）。
  **mutation**：拿掉任一 `skipped_*` 分支之記錄，須使第二條斷言轉紅。
  指令：`pytest tests/momentum/feature_engineering/test_dstar_receipt.py -q`
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
- 既有 caller／影響面：落檔為**新增副作用**；落點與覆蓋率依 §A 之使用者裁示，
  **裁示未到前本 Task 不得開工**。
- 改法：以既有 `DStarCache.flush_atomic` 之同型原子寫入（temp ＋ `os.replace`），
  內容含 `symbol`／`timeframe`／`config_hash`／`row_count`／`time_range`／
  `fracdiff_hash`／逐欄記錄。**欄名一律用落檔當下之欄名**（不做任何正規化——
  共用快取之鍵不帶週期前綴正是本票要解的可追溯性問題之一部分）。
- **驗證**（`pytest`）：跑一個小 run 後，收據之 `config_hash` `==` 該 run 目錄之 `config_hash`；
  收據逐欄之 `d` 與同次執行之 `_fracdiff_processed_columns` 對應值相等；
  同一 run 連跑兩次，收據 byte 級相同。
  **mutation**：把 `config_hash` 改為寫入 `symbol`，須使第一條斷言轉紅。
  指令：`pytest tests/momentum/feature_engineering/test_dstar_receipt.py -q`
- **邊界**：① 落點目錄不存在 ⇒ 建立而非失敗；② 寫入失敗 ⇒ **不得**讓整個 run 失敗
  （收據是診斷物，不是產物），但須 `logger.warning` 且可由測試斷言該警告；
  ③ 同一 run 重跑 ⇒ 覆寫自己的收據（同 `config_hash`，不涉跨 run 覆蓋）。
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
  可獨立 `pytest tests/momentum/...` 跑，不需 `run_api.py`。
- **防假綠**：
  1. 「收據與實際一致」不得以「讀自己剛寫的檔」自證——須與 `_fracdiff_processed_columns`
     這個**既有**、非本票新增的來源比對。
  2. 既有測試斷言一律 diff，不得放寬。
  3. 用真實 run，禁合成 fixture。
- **邊界目錄**：✔ 空輸入（eligible 為空）／✔ 並行合併重複鍵／✔ 寫入失敗降級；
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
  觸發：使用者要求回溯查證某個既有 run 之 `d*` 時；登記處：`docs/ROADMAP.md`。
  🔴 **誠實邊界**：本票**救不回過去**。reference run（特徵落檔 `Jul 4 15:35`）當時之 `d*`
  已被 `Sep 9 20:45` 之另一 run 覆寫，除重跑外無法取得。
- **FFDSTAR-R2 `/api/v1/features/generate` 回之 `task_id` 於 `/task/{task_id}` 查不到**
  — `為何現在不做: blocked-by:本票範圍限於預處理層之可追溯性，該缺陷在 api/ 之任務登記路徑，
  屬不同模組且需獨立定性（是否為已知設計）`；
  觸發：**已觸發**，2026-09-21 主委跑 FF 重跑時實遇（三個候選狀態端點皆 404，生成本身正常）；
  登記處：`docs/ROADMAP.md`。
- **FFDSTAR-R3 收據覆蓋率與欄數之落差**
  — `為何現在不做: needs-research:現存共用快取僅 148 entries 而 run 有 437,110 欄，
  該落差是「只有少數欄進 fracdiff」還是「記錄本身不全」尚未區分；須待 Task 1.1 之收集上線後，
  以真實 run 之四類計數回答`；
  觸發：Task 1.1 完工並跑過一次真實 run 後；登記處：`docs/ROADMAP.md`。
