# GAP3_EVENT_UX_TODO — D 延伸 005（Task 7.0b 之 `label_value` 符號通道）

> ## 🔴 本檔已因 R 重開而失效（SUPERSEDED-BY-R，2026-09-02）
>
> **失效依據**：`docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1（R ⇒ 所有延伸檔失效；安全閥①全量作廢）。
> 觸發：`docs/GAP3_EVENT_UX_SPEC.md` R35-R（§D **D-8**）。
> **處置**：A-023（`PreparedAnalysisWindows.direction_sign`）**併回本體**（Task 7.0b；與 2.1b 無關，內容不變）。
> 本檔不得再作為任何派工之授權來源。

BASE: docs/GAP3_EVENT_UX_TODO.md @ afa70967
PREDECESSOR: docs/GAP3_EVENT_UX_TODO.D-004.md

改什麼: 一條——**A-023** 為 `PreparedAnalysisWindows` 增 `direction_sign: int` 欄，
使 Task 7.0b 之階段 5 產出 **signed** `label_value`，同時**維持** `WindowRow` 恰七鍵
與 `event_label_spec` 恰四鍵不變。

為什麼: 這是**凍結後才發現的契約互斥**，不是操作清單不足。SPEC Task 7.0b 之四條 FROZEN
字面兩兩相容、四者不相容：
① 驗收 ②（L2668）「同上 short ⇒ 值為①之相反數（`== -x`，`atol=0`）」＝要求 stage 5 產 signed 值；
② stage 5 簽章（L2422–2427，R32 定死）為 `resolve_label_value_at_analyze(prepared, bars_by_tf, *, event_label_spec)`
　——**無 `records`、無 `direction`**；
③ `WindowRow` 欄集（L2380–2390，R13 (β)／R18）「恰七鍵」——**無 `direction`**；
④ `event_label_spec` normalizer（L2415–2421，R13）「鍵集恰四鍵，多一鍵 fail-closed」。
⇒ 照字面實作，stage 5 **在結構上**取不到方向，只能回 unsigned，驗收 ② 必紅。

🔴 **為什麼不能放著不管**（這不是形式問題，是數值正確性問題）：
consumer 側**沒有**第二次乘 direction——主委實跑
`sed -n '2894,2908p' momentum/Analysis/ic_filter_orchestrator.py`：該段只做 `missing` 檢查 →
`float()` → `np.isfinite` gate → 建 `pd.Series` → 標 `label_source`，**無任何 direction／sign 分支**；
`momentum/Analysis/event_samples/ic_feed.py:80` 為 `ts_map[ts] = float(ev.loc[eid, "label_value"])`，純複製。
⇒ producer 若回 unsigned，**short 批次的條件 IC 符號整個反轉**，而且沿路沒有任何一層會補救。
三家（codex／composer／grok）獨立實查同結論。

裁定來源: `handoffs/reconcile/20260828-gap3ux-b10-consult-r2/synth.md`
（三家 P0／BLOCKING 一致判「必須開延伸檔」：`CODEX-R2-P0-01`／`COMPOSER-R2-P0-01`／`GROK-R2-P0-01`）。
檔名依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.2（`*.D-NNN.md` 機讀規約）。

## 觸及面宣告

新增: `momentum/Analysis/event_samples/label_value_from_case.py` 之
`PreparedAnalysisWindows.direction_sign: int`；`momentum/Analysis/event_samples/keys.py` 之
`event_direction_sign(record) -> int`（第三個 accessor，同檔同紀律）
不動: `WindowRow` 欄集（**維持恰七鍵**）；`event_label_spec` normalizer 鍵集（**維持恰四鍵**）；
`resolve_label_value_at_analyze` 與 `prepare_analysis_windows` 之**簽章**（兩者皆不變）；
`PerTfRow`／`SymbolPurgeRow` 欄集；`ic_filter_orchestrator`／`ic_feed`（**不加第二次乘號**）
覆寫: SPEC Task 7.0b ① 之 `PreparedAnalysisWindows` 欄集（由九欄增為**十欄**）
依賴: docs/GAP3_EVENT_UX_TODO.D-001.md、D-002.md、D-003.md、D-004.md

---

## 內容

本延伸檔兩條修訂：**A-023**（`direction_sign`）與 **A-024**（`⑧(a)` 前綴保留判準之改形）。

- **對 TODO Task 7.0b 之效力**：實作要點 2 所列之 `PreparedAnalysisWindows` 欄集
  由九欄增為**十欄**（增 `direction_sign: int`）；其餘欄集與兩個階段函式之**簽章不變**。
- **對 SPEC 之效力**：SPEC 為 FROZEN，本檔**不就地改 SPEC**；SPEC Task 7.0b ① 之
  「`PreparedAnalysisWindows` 欄集恰如 SPEC L2378–2396」一句，自本檔核可起
  讀為「恰如 SPEC L2378–2396 **＋ 本檔 A-023 之 `direction_sign`**」。
- **對驗收之效力**：SPEC 驗收 ①② 之字面**完全不改**（本檔正是為了讓那兩條能通過而存在）；
  另增三條驗收與四條 mutation，全文在 A-023 之「驗證」節。

## A-023 — `PreparedAnalysisWindows` 增 `direction_sign`

### 判準（本節為 A-023 之唯一權威字面）

1. **欄位**：`PreparedAnalysisWindows` 增
   ```
   direction_sign: int      # 恰 +1 或 -1；無第三個合法值
   ```
   置於欄集內，**不得**為 `Optional`、**不得**有預設值——沒有方向就不該有 prepared 物件。

2. **取值（唯一路徑）**：由 `prepare_analysis_windows` 自 `records` 導出，
   經 `momentum/Analysis/event_samples/keys.py::event_direction_sign(record) -> int`。
   該 accessor 之判準：
   - `record["direction"]`（**key access**，禁 attribute access；同 `event_scope_key` 之紀律）
   - `"long"` ⇒ `+1`；`"short"` ⇒ `-1`；**其餘任何值 ⇒ raise**（含缺鍵、`None`、大小寫變體）
   - 🔴 **不得**以 `record.get("direction", "long")` 之形式補預設——
     「沒宣告方向」與「宣告為 long」是兩件事，後者是使用者的選擇，前者是資料缺失。

3. **批內一致性**：`prepare_analysis_windows` 對 `records` 逐列取 sign，
   得到之集合**大小須為 1**，否則 raise。
   🔴 這**不是**重做匯入層的檢查而是**第二道**：匯入層之
   `import_contract.py:694-696` 已對混方向 fail-closed（`direction_mixed_in_batch`），
   但 prepare 也吃「分析用副本」這條路徑，而副本是本模組自己組的
   ——只信上游等於把不變式的維護責任交給一個本模組管不到的地方。

4. **產出**：`resolve_label_value_at_analyze` 之每個值為
   ```
   direction_sign * (close[label_end_ms] - close[label_start_ms]) / close[label_start_ms]
   ```
   🔴 **乘號在 producer，不在編排層**。理由（兩家獨立提出，`COMPOSER-R2-P2-01`／`GROK-R2-P2-01`）：
   ① SPEC 已寫死 **producer 級** mutation「short 不取負 ⇒ ②」，乘號挪走則該 mutation 打不到東西；
   ② 任何直接呼叫 `resolve_label_value_at_analyze` 的路徑都會拿到 unsigned，而下游不補救。

5. **hash 綁定**：`direction_sign` **須進** `analysis_alignment_receipt_hash` 之輸入。
   🔴 否則同一批以 long 與 short 各 prepare 一次會得到**相同 hash**，
   而兩者的 `label_values` 正負相反 ⇒ 驗收 ⑩「三處讀到同一 hash」會在錯誤的前提下全綠。

6. **`apply_event_coverage` 原樣攜帶**：`dataclasses.replace` 不動本欄
   （與 `prepared_token`／`analysis_alignment_receipt_hash` 同待遇）。

### 驗證（A-023 之可證偽性）

- `pytest tests/momentum/event_samples/ -q -k analysis_label_producer` 之
  **①②即為本條之驗收**（SPEC L2666–2668 原字面，**不改寫**）：
  ① long ⇒ `label_values[eid] ==` 手算之 `(close[t0+h]-close[t0])/close[t0]`（`atol=0`）；
  ② 同上 short ⇒ `== -x`（`atol=0`）。
  🔴 ①② 之 fixture 須為**同一組價格序列**，只改 `direction`
  ——兩組不同 fixture 各自手算會使「相反數」這件事無從證偽（那正是本 brief 之 `丁` 選項的錯法）。
- **新增一條**：`direction_sign` 進 hash 之對證——同一批之 long 與 short 兩次 prepare
  ⇒ `analysis_alignment_receipt_hash` **不相等**。
- **新增一條**：`records` 混方向 ⇒ `prepare_analysis_windows` raise。
- **新增一條**：`record` 之 `direction` 缺鍵／為 `None`／為 `"Long"`（大小寫變體）⇒ raise
  （**over 向對照**：`"long"`／`"short"` 兩個合法值須成功，證明不是恆 raise）。

**mutation（四條，皆須紅）**：
1. `event_direction_sign` 對 `"short"` 回 `+1` ⇒ ② 紅；
2. 乘號從 `resolve` 移到 caller（模擬選項甲）⇒ ② 紅（producer 級測試看不到 caller）；
3. `direction_sign` 自 hash 輸入移除 ⇒ 「long/short 兩次 prepare 之 hash 不相等」紅；
4. 批內一致性檢查移除 ⇒ 混方向 fixture 之 raise 斷言紅。

### 🔴 擇取理由（兩份互斥提案之裁決；依使用者工作方法把理由寫進文件）

三家皆提出「第五案」，但形狀分兩種：

| 提案 | 內容 | 家 |
|---|---|---|
| **批次 scalar** | `direction_sign` 掛 `PreparedAnalysisWindows`，`WindowRow` 維持七鍵 | codex（`CODEX-R2-P1-02`）／composer（`COMPOSER-R2-P1-01`） |
| **逐列欄** | `direction` 加進 `WindowRow` 成第八鍵 | grok（`GROK-R2-P1-01`，其 Verdict 之「乙」） |

**採批次 scalar。三個理由皆為碼證，不是數人頭**（本專案定「分歧看碼證不數人頭」）：

1. **SPEC 自己的分類**：L3073–3076 之封閉分類表把 `direction` 列在**批次事實欄**
   （與「批次宣告種子」「分析參數」並列），且 L3075 逐字寫
   「`direction` 歸批次事實（**它決定 short 取負**、是 §G G-3 之 golden input）」。
2. **契約使非法狀態不可表達**：`import_contract.py:694-696` 已對混方向 fail-closed
   ⇒ 做成逐列欄就**造出一個可表達但非法的狀態**（各列方向不同的 `WindowRow` tuple）；
   批次 scalar 讓它連表達都表達不出來。§C0「只能更嚴」偏向後者。
3. **爆炸半徑**：`WindowRow` 之七鍵被 §G G-3 之 `inspect.signature` 對證引用，
   改它須同步動 G-3；加一個 scalar 只動一處欄集宣告。

🔴 **grok 之異議具名保留**：grok 主張「`direction` 是事件列屬性，批內單值只是匯入約束，
不是把它做成批次維度的理由」。此點在抽象語意上成立——本裁定不是說 grok 講錯，
而是說**在本 epic 現行的 SPEC 分類與契約約束下**，批次 scalar 是較嚴且爆炸半徑較小的形狀。

🔴 **本裁定之失效觸發條件（寫死，不靠記得）**：
**若日後解除 `direction_mixed_in_batch` 之 fail-closed**（即允許批內混方向），
理由 2 立即消失、理由 1 之分類亦須重議 ⇒ **本 A-023 失效，須改為 grok 之逐列欄版**。
屆時 `WindowRow` 增第八鍵並同步 §G G-3 之 signature 對證。

### 具名殘留

| 代號 | 內容 | 三值理由 |
|---|---|---|
| `R-D005-1` | 「`direction` 之所有讀取皆須經 `event_direction_sign`」為**規範陳述**，與 `keys.py` 之另兩個 accessor 同屬 SPEC R21 已降為「待裁定」之範疇——**沒有機械閘**，靠紀律 | `user-ruling`（R20 已刪除「consumer 恰三處」之枚舉、R21 已判 AST 掃描不作 active acceptance；本專案定治理不擴建） |

---

## A-024 — `⑧(a)` 前綴保留判準改為**逐 namespace**（因 A-023 之契約加欄而觸發）

### 這條為什麼存在（不是為了讓測試變綠）

SPEC Task 7.0b R18 要求「`alignment.py:21` 之 `_EVENT_COLS` 須擴充 `symbol`／`timeframe`
（**先改契約，D-6**）」⇒ `event_import_contract.json` 之 `receipt_schema.event_level` 須加兩鍵。

但既有測試 `tests/api/test_gap3_contract_reason_registry.py::…_08a_flatten_prefix_preserved`
斷言 `now_names[:len(pre_names)] == pre_names`，其中 `flatten_receipt_schema` 是**跨 namespace
攤平**（`event_level.*` → `per_tf.*` → `batch.*` → `mapping_provenance.*`）。
⇒ 該斷言實際編碼的是「**全域 append-only**」：任何新鍵只能加在**最後一個 namespace 的最後面**。

**主委實跑確認這不是可繞過的**：先把兩鍵插在 `event_level` 中間 → 紅（`index 10` 起分歧）；
再改為 append 在 `event_level` **尾端** → **仍紅**，因為 `per_tf.event_id` 原本就在全域 index 10。
⇒ 在該判準下，`event_level` 這個非末端 namespace **永遠不能加欄**。
這與 D-6「先改契約」的成長路徑直接互斥。

🔴 **這不是「放寬既有斷言換綠」**。原斷言的**目的**寫在它自己的節標題上：
「既有欄名與順序一個不差且排在新欄之前」——前半（既有欄名與順序一個不差）是真正要守的，
後半（排在新欄之前）是**實作前綴比對時順帶產生的副作用**，不是獨立的品質要求：
把新欄放在哪個 namespace 內，並不改變任何既有欄的名字或相對順序。

### 判準（改形後；本節為唯一權威字面）

`⑧(a)` 改為**四條並列**，全部須成立：

1. **逐 namespace 前綴保留**：對 `pre` 之每個 namespace `ns`，
   `now` 之該 ns 攤平名單須以 `pre` 之該 ns 攤平名單為**前綴**
   （擋重新命名／重新排序／刪欄，與原斷言在**同一 namespace 內**等強）。
2. **namespace 順序保留**：`now` 之 namespace 出現序須以 `pre` 之 namespace 序為前綴
   （原斷言**沒有**這一條；本次新增，擋「把整個 namespace 搬位置」）。
3. **無遺漏**：`set(pre_names) <= set(now_names)`（擋任何既有欄被拿掉）。
4. **確有成長**：`len(now_names) > len(pre_names)`（原斷言即有，保留）。

🔴 **改形後之淨效果**：能抓到的壞法**多一種**（namespace 重排），
少限制的只有「新欄必須全域排最後」這一件與品質無關的事。

### 驗證（A-024 之可證偽性）

`pytest tests/api -q -k gap3_contract_reason_registry` rc=0，且下列 **mutation 皆須紅**：
1. 把 `receipt_schema.event_level` 之任一既有鍵**改名** ⇒ 條 1 紅；
2. 把 `event_level` 內任兩個既有鍵**對調** ⇒ 條 1 紅；
3. 把 `per_tf` 整個 namespace 移到 `event_level` **之前** ⇒ 條 2 紅；
4. 刪掉 `receipt_schema` 之任一既有鍵 ⇒ 條 3 紅（且條 1 亦紅）。

🔴 **over 向對照（本批雙向矩陣之一格）**：在 `event_level` **尾端**加新鍵
⇒ 四條**皆須綠**（那正是 A-023 要做的事；若它紅，代表改形沒生效）。

### 具名邊界

本條只改 `⑧(a)`。`⑧(a2)`（baseline 側之獨立 oracle，`CODEX-R3-P2-06`）**原樣不動**
——那條是防「共用 traversal 壞掉時兩側一起變形而自我配對」，與本條無關。

---

## 戳記

（待三家 append `RECONCILE-STAMP APPROVED`／`REJECTED`）

RECONCILE-STAMP: grok APPROVED 2026-08-28 sha256:1994fdfa5f3ca723408f34d42b94c21bb15a312d0f487254cc579aa94418b6b7 task:20260828-GAP3UXTODOD305-X-STAMP-R1 — D-005

RECONCILE-STAMP: composer APPROVED 2026-08-28 sha256:1994fdfa5f3ca723408f34d42b94c21bb15a312d0f487254cc579aa94418b6b7 task:20260828-GAP3UXTODOD305-X-STAMP-R1 — D-005
RECONCILE-STAMP: codex APPROVED 2026-08-28 sha256:1994fdfa5f3ca723408f34d42b94c21bb15a312d0f487254cc579aa94418b6b7 task:20260828-GAP3UXTODOD305-X-STAMP-R1 — D-005
