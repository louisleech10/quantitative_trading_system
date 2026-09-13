# SPLITUNIFY b9 — Task 9.1（B9A）實作之三家審碼

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 🔴 本輪標的變了：**這是第一輪審「程式碼」，不是審規格**
r13–r17 都在審 SPEC／TODO 文字。本輪標的是 `Task 9.1` 的**實際實作**（commit `0bd91069`）。
請用審碼的方式打——**構造反例、實跑、看值**，不要只讀條文對字面。

## 這次實作解決的缺陷（一句話）
單選 `selected_timeframe` 會把其餘 feature TF 的 `per_tf` 列**靜默丟掉**，呼叫端與使用者看不到丟了多少。
Task 9.1 只做**記帳**：producer 回傳 `(keyed, discarded)`，`discarded` 原樣沿 summary 帶出。
🔴 **刻意不做**：`selected_timeframe` 仍必填、單選行為未動（改可選全量是 `Task 9.2`）。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **本輪 diff**：`git show 0bd91069 -- momentum/Analysis/event_samples/split_projection.py momentum/Analysis/event_samples/pipeline.py tests/momentum/Analysis/test_splitunify_derive.py`
- **current block**：
  - `momentum/Analysis/event_samples/split_projection.py`：`build_event_keys`、`_derive_single_symbol` 之簽章與 summary 呼叫、`derive_event_split_from_plans` 之多 symbol 分支、`_build_summary`
  - `momentum/Analysis/event_samples/pipeline.py`：投影分支之 caller
  - `docs/SPLITUNIFY_TODO.md` 之 `§C-9 Task 9.1`（契約來源）
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 正文（已三家戳記 rc=0，本輪未動）、`HISTORY-BEGIN..END`、「## 沿革與追溯索引」節。
- 🔴 **不得重開**：`Task 9.2`–`9.5` 之設計（尚未實作）、register 之 mutation 欄對應（r14 窮舉、r15/r16/r17 零復發）、停輪判準與 r17 共識決。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 測試全綠 → `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/ tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` 實跑得 **692 passed**。派工後預期值: 不變（唯讀審查）。VERIFY-EXEMPT:doc-example:brief-dispatch-time-premise（本行記錄的是**派工當下**之狀態，供委員對照；修補後之最新回歸見該輪收斂檔）
fact-verified: 兩條 mutation 實跑轉紅 → 刪掉 `_build_summary` 之 `discarded_rows_by_feature_tf` 鍵 ⇒ **3 failed**（`test_summary_has_all_thirteen_keys`／`test_summary_carries_..._equal_to_producer`／`test_discarded_layer_is_independently_revertible`）；`_derive_single_symbol` 改傳 `{}` ⇒ **1 failed**（`test_summary_carries_..._equal_to_producer`）。兩者皆已還原。
fact-verified: summary 由 12 鍵增為 13 鍵 → 既有 `test_summary_has_all_twelve_keys` 已更名為 `..._thirteen_keys` 並改為 exact-set 斷言（多一鍵少一鍵都紅）。
fact-verified: 單選行為未動 → `build_event_keys` 之 `selected_timeframe` 仍為必填 keyword-only `str`，過濾與 `1:1` merge 邏輯一字未改。

assumed: `discarded` 是**批次級**、不需逐 symbol 相加。**我的否證觀測（已先跑）**：`grep -n "build_event_keys" momentum/Analysis/event_samples/pipeline.py` 只有 import 與**單一呼叫點**，且該呼叫吃的是整批 `receipts`；多 symbol 分支只切 `event_keys`，不重呼 producer。**但這與 TODO 條文字面衝突**——`Task 9.1` 實作要點 2 寫「多 symbol 分派器逐 symbol **相加**（同鍵值相加，非後者覆蓋前者）」。我判斷照字面相加會**重複計數**，故採原樣傳遞並於碼中具名。← **請直接裁這條**：是實作對、還是 TODO 條文對？若 TODO 對，請指出逐 symbol 分量從哪裡來。
assumed: `discarded` 用 `value_counts()` 計數**對所有 dtype 都正確**。**我的否證觀測（已先跑）**：測試 fixture 之 `timeframe` 為 `str`，`astype(str)` 後比較。**我沒查**：`per_tf["timeframe"]` 若為 `Categorical` 或含 `NaN`，`value_counts()` 的行為（`Categorical` 會列出**未出現的類別**且計數為 0；`NaN` 預設被丟掉）⇒ 可能產生鍵為 `"nan"` 或值為 0 的偽項。← **請直接攻這條**，並判是否該加 dtype 閘。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| 契約形狀 | `discarded` 無丟棄時為 `{}`、非 `None`；有具名測試 | `discarded` 之值型別是否恆為 Python `int`（`value_counts()` 回 `np.int64`，我有 `int(n)` 轉換——請驗轉換是否覆蓋所有路徑） |
| 跨邊界傳遞 | producer → `_derive_single_symbol` → summary 三層有值相等測試 | 多 symbol 分支（`plans` 為 Mapping）之 summary 是否真的帶到——**該分支目前無具名測試**，請構造多 symbol 反例實跑 |
| 未動面 | 單選過濾與 `1:1` merge 未改；692 passed | 是否有**未被上述 692 條覆蓋**的 caller 受簽章改動影響（請 `grep -rn "build_event_keys" --include='*.py' .` 全 repo 掃，含 `handoffs/*.py` 探針） |
| summary 鍵集 | exact-set 斷言、13 鍵 | `pipeline.py` 或下游是否有「summary 鍵數寫死為 12」的地方（請掃） |
| 預設可變物件 | 參數預設用 `None` 不用 `{}` | `_build_summary` 內 `(discarded_rows_by_feature_tf or {})` 之 falsy 陷阱——傳入**空 dict** 與傳入 `None` 在此不可分；請判是否有語意差需要區分 |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 「逐 symbol 相加」vs「批次級原樣傳遞」——哪個對？給裁定。
   **(1b)** 若判 TODO 條文對，指出逐 symbol 分量的來源；若判實作對，給出應如何修改 TODO 條文的字面。
2. **(2a)** 多 symbol 分支（`plans` 為 Mapping）之 `discarded` 是否真的帶到 summary？**請構造反例實跑**。
   **(2b)** 若帶到了，該分支是否該補具名測試？若沒帶到，給最小修法。
3. **(3a)** `value_counts()` 在 `Categorical`／含 `NaN` 之 `timeframe` 欄上會不會產生偽項（鍵 `"nan"`、值 0）？**請實跑**。
   **(3b)** 若會，給最小修法（加 dtype 閘還是改計數方式）；若不會，說明你試了哪幾種 dtype。
4. **(4a)** 全 repo 是否還有未改的 `build_event_keys` 呼叫端（含 `handoffs/*.py` 探針）？
   **(4b)** 若有，逐一列出並判是否阻擋。
5. **(5a)** 兩條 mutation（`M-SU-D2-01`／`M-SU-D2-02`）之應紅測試是否**真的有鑑別力**？請自行重跑那兩個破壞。
   **(5b)** 是否還有**第三種**破壞方式會讓記帳失效但所有測試仍綠？若有，給出來。
6. **(6a)** 可以進 `Task 9.2` 嗎，還是有 BLOCKING 必須先修？
   **(6b)** 若可以，說明你檢查了什麼；若不可以，列**最小**閉合集合。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**。

## 產出
canonical 四欄 findings + **Verdict**。**禁改碼、禁改 SPEC、禁改 TODO**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
