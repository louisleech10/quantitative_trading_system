# SPLITUNIFY b9 — Task 9.2＋9.2a（B9B）之三家審碼

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 🔴 本批是第 9 批的**核心**
`Task 9.2` 之前，producer 只挑一個 feature TF、其餘整批丟掉；本批改為**全量輸出**，
行粒度升為 `(event_id, feature_timeframe)`。**沒有這一批，下游全改完 `SU-RESID-2` 仍不會解決。**
請用審碼方式打——**構造反例、實跑、看值**。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **本輪 diff**：`git show 9e87386f`
- **current block**：
  - `momentum/Analysis/event_samples/split_projection.py`：`build_event_keys` 全函式、`EVENT_KEY_COLUMNS`、`_derive_single_symbol` 之 guard 與兩表組裝、`derive_event_split_from_plans` 多 symbol 分支、`_build_summary`
  - `momentum/Analysis/event_samples/pipeline.py`：投影分支之三參數閘與 caller
  - `scripts/freeze_splitunify_golden.py`：`_event_keys()`
  - `docs/SPLITUNIFY_TODO.md` 之 `§C-9 Task 9.2` 與 `Task 9.2a`（契約來源）
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 正文（v18 三家戳記 rc=0、本輪未動）、`HISTORY-BEGIN..END`、「## 沿革與追溯索引」節。
- 🔴 **不得重開**：`Task 9.2b`–`9.5` 之設計（尚未實作）、`Task 9.1` 已閉合之十三條、r17 共識決。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 回歸全綠 → `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/ tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` 實跑得 **705 passed**（receipt `20260913T165740Z-splitunify-b9b-task92-92a`）。派工後預期值: 不變（唯讀審查）。VERIFY:20260913T165740Z-splitunify-b9b-task92-92a
fact-verified: 五種破壞各自轉紅並還原 → `M-SU-D2-20`（producer 保留預設單選）紅；`M-SU-D2-21`（門檻改回四鍵）2 紅；`M-SU-D2-23`（`validate` 改回 `1:1`）2 紅；`M-SU-D2-26`（以 `event_level.timeframe` 冒充）紅；`M-SU-D2-36`（`purged` 不寫該欄）紅。VERIFY-EXEMPT:doc-example:brief-dispatch-time-premise
fact-verified: golden 既有值未動 → `scripts/freeze_splitunify_golden.py` 之 fixture **刻意維持單一 feature TF**，`tests/momentum/Analysis/test_splitunify_golden.py` 三條全綠。VERIFY-EXEMPT:doc-example:brief-dispatch-time-premise
fact-verified: summary 由 13 鍵增為 16 鍵 → `test_summary_has_all_sixteen_keys` 之 exact-set 斷言（多一鍵少一鍵都紅）。VERIFY-EXEMPT:doc-example:brief-dispatch-time-premise

assumed: 多 feature TF 之 `purged` 列**目前不會**出現「同事件一列 purged、另一列 assign」之混態。**我的否證觀測（已先跑）**：現行判側仍逐列用 `feature_cutoff_ms`，而本批之 fixture 讓同事件兩列的 cutoff **相同**（刻意——側別錨定是 `Task 9.2b`），故兩列必同側。**我沒查**：若 cutoff 不同（真實資料的常態），現行碼會不會產生混態、以及那是否屬 `Task 9.2b` 才處理的範圍。← **請直接攻這條**，構造 cutoff 不同的多 TF 反例實跑，並判「現在就該擋」還是「屬 9.2b」。
assumed: `n_events`／`n_event_tf_rows` 兩個新計數在**多 symbol 分支**也正確。**我的否證觀測（已先跑）**：兩者皆以整批 `event_keys` 算（`nunique()` 與 `len()`），與 symbol 無關。**我沒查**：多 symbol 分支之 `n_event_tf_rows_purged` 取 `len(purged)`，而 `purged` 是逐 symbol `concat` 而來——若某 symbol 之子批為空，`concat` 之欄集是否仍正確。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| 四層是否都真的改了 | 五種破壞各自轉紅（上列 fact-verified 第 2 條） | 是否有**第六種**破壞會讓全量失效但測試全綠 |
| `EVENT_KEY_COLUMNS` 新增欄 | `derive_*` 入口有缺欄檢查 | 全 repo 是否還有別處**建構** `event_keys` 而未加該欄（請掃，含 `scripts/`／`handoffs/*.py`／`api/`） |
| 空批欄集 | 多 symbol 空批已明寫欄集 | 單標的空批（`assign_rows`／`purge_rows` 皆空）之欄集是否也一致 |
| 計數三鍵 | 單標的有具名測試 | 多 symbol 分支之三鍵**無具名測試**（見 assumed 2） |
| golden | 單 TF、三條全綠、值未動 | `splitunify_golden.json` 之 11 個頂層鍵是否**逐值**未變（請實際比對，不要只看測試綠） |
| NaN fail-closed | `Task 9.1` 之檢查已提前到**全欄** | 提前後是否誤殺——`per_tf` 有缺值但**被選中側沒有**時，單選模式現在也會 raise；判這是否為預期 |

## 必答（逐條 verdict；成對，不得只答一半）
1. **(1a)** cutoff 不同的多 feature TF 反例：現行碼會不會產生「同事件一列 purged、另一列 assign」之混態？**請實跑**。
   **(1b)** 若會，判「現在就該擋」還是「屬 `Task 9.2b`」；若判現在就該擋，給最小修法。
2. **(2a)** 多 symbol 分支之 `n_events`／`n_event_tf_rows`／`n_event_tf_rows_purged` 是否正確？**請構造反例實跑**。
   **(2b)** 是否該補具名測試？若該補，給測試名與斷言。
3. **(3a)** 全 repo 是否還有別處建構 `event_keys` 而未加 `feature_timeframe`？逐處列出。
   **(3b)** 若有，判是否阻擋。
4. **(4a)** `splitunify_golden.json` 之 11 個頂層鍵是否逐值未變？**請實際比對**（不要只看測試綠）。
   **(4b)** 若有變動，逐鍵列出。
5. **(5a)** NaN fail-closed 提前到全欄後，是否會誤殺「缺值只在未選中側」之單選批？**請實跑**。
   **(5b)** 若會，判這是否為預期；若非預期，給最小修法。
6. **(6a)** 是否還有**第六種**破壞會讓全量失效但所有測試仍綠？
   **(6b)** 可以進 `Task 9.2b` 嗎，還是有 BLOCKING 必須先修？

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**。

## 產出
canonical 四欄 findings + **Verdict**。**禁改碼、禁改 SPEC、禁改 TODO**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
