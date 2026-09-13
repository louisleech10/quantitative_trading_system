# SPLITUNIFY b9 — review-r18 A1-A6 閉合再驗證

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 本輪要做什麼（一句話）
**逐條重跑你自己在 review-r18 提出的反例**，確認修補真的關閉了該 finding（章程 §B8：閉合須由**原提出方**重跑同一反例，不憑「已修」信任）。

| finding | 提出方 | 修補摘要 |
|---|---|---|
| `GROK-R18-P1-01` | grok | 新增 `tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_discarded_rows_reaches_summary`——斷言掛在 `EventSamplePipeline.run`，fixture 用兩個 feature TF（`4h`＋`12h`）之真實 kline 使記帳非空 |
| `CODEX-R18-P1-01`／`COMPOSER-R18-P2-02`／`GROK-R18-P3-01` | 三家 | `handoffs/20260911-splitunify-b9-probe-multitf.py` 改為 `out, discarded = build_event_keys(...)` 並印出 `discarded` |
| `CODEX-R18-P1-02`／`COMPOSER-R18-P3-01` | codex／composer | `build_event_keys` 在計數前對 `dropped.isna().any()` fail-closed raise；配 `test_build_event_keys_rejects_nan_timeframe_in_dropped_rows` |
| `CODEX-R18-P1-03`／`GROK-R18-P2-01` | codex／grok | TODO `Task 9.1` 實作要點 2 改為「**原樣傳遞、不得相加**」並載明理由與鎖住它的測試 |
| `CODEX-R18-P2-01`／`COMPOSER-R18-P2-01`／`GROK-R18-P2-02` | 三家 | 新增 `test_multi_symbol_branch_carries_discarded_rows_verbatim`（值相等＋**防放大**） |
| `CODEX-R18-P3-02`／`GROK-R18-P3-02` | codex／grok | `_build_summary` docstring 改 13 鍵、刪掉 `pipeline.py:696` 失效引用、明寫鍵數權威是 exact-set 斷言 |

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **本輪 diff**：`git show 7943abe3`
- **current block**：
  - `momentum/Analysis/event_samples/split_projection.py`：`build_event_keys` 之 `discarded` 計算段、`_build_summary` docstring 與第 13 鍵
  - `tests/momentum/event_samples/test_splitunify_wiring.py`：檔末之 `bars_multi_tf` fixture 與 `test_splitunify_wiring_discarded_rows_reaches_summary`
  - `tests/momentum/Analysis/test_splitunify_derive.py`：檔末兩條新測試
  - `handoffs/20260911-splitunify-b9-probe-multitf.py`：`case()` 之 unpack
  - `docs/SPLITUNIFY_TODO.md` 之 `§C-9 Task 9.1`
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 正文（三家戳記 rc=0、本輪未動）、`HISTORY-BEGIN..END`、「## 沿革與追溯索引」節。
- 🔴 **不得重開**：`Task 9.2`–`9.5` 之設計（尚未實作）、register 之 mutation 欄對應、r17 共識決。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 六群皆已落地 → `git show 7943abe3 --stat` 含 `split_projection.py`／`test_splitunify_wiring.py`／`test_splitunify_derive.py`／`20260911-splitunify-b9-probe-multitf.py`／`docs/SPLITUNIFY_TODO.md`。派工後預期值: 不變（唯讀審查）。
fact-verified: 三條新測試各自實跑破壞驗過鑑別力 → 拿掉 `pipeline.py` 之 `discarded_rows_by_feature_tf=` ⇒ wiring 那條轉紅；多 symbol 分派器改傳 `{}` ⇒ 多 symbol 那條轉紅；兩者皆已還原。
fact-verified: 探針四案可重跑 → `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` 印出 A／B／C／D 四行，其中 C 之 `discarded` 記到 `4h` 兩列。
fact-verified: 回歸筆數見收斂檔 → `handoffs/reconcile/20260911-splitunify-b9-review-r18/synth.md` 裁定第 2 點（VERIFY:20260913T161341Z-splitunify-b9-t91-r18-fixes）。

assumed: NaN fail-closed **只擋壞資料、不會誤殺合法批**。**我的否證觀測（已先跑）**：該檢查只對**被丟棄的那一側**（`dropped`）做 `isna`，被選中側不受影響；既有全部測試仍綠。**我沒查**：`per_tf` 若整欄為 `Categorical` 且含未使用類別，`isna()` 與後續 `astype(str).value_counts()` 的互動——`Categorical` 之 `value_counts()` 會列出**未出現的類別且計數為 0**，我在字串化之後才計數，理論上已規避，但**沒有實跑驗過**。← **請直接攻這條**：構造 `Categorical` fixture 實跑，看 `discarded` 是否混入值為 0 的偽項。

assumed: wiring 測試之 `bars_multi_tf` fixture **真的讓兩個 feature TF 都進到 `per_tf`**。**我的否證觀測（已先跑）**：該測試斷言 `set(discarded) == {"4h"}` 且值為正整數，若只有一個 TF 進來則 `discarded` 為空、斷言會紅。**我沒查**：`EventPipelineConfig(timeframes=("4h", TF))` 之順序是否影響 `selected_timeframe=TF` 的過濾（例如某處以第一個 TF 為預設）。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| 生產接線 | 已有掛 `EventSamplePipeline.run` 之測試並實跑驗紅 | 是否還有**第二條**生產路徑會呼叫 `derive_event_split_from_plans` 而繞過該測試（請全 repo 掃該函式之呼叫點） |
| 多 symbol 分支 | 已有值相等＋防放大測試並實跑驗紅 | 防放大斷言只檢查 `4h` 一鍵——若實作改成「只對部分鍵相加」是否仍會紅 |
| NaN fail-closed | 只對 dropped 側、既有測試全綠 | 見 assumed 1 之 `Categorical` 互動 |
| 探針檔 | 四案可重跑 | 探針之輸出是否與 TODO／FACT-RECEIPT 引用它的字面一致（請比對） |
| TODO 條文 | 已改「原樣傳遞、不得相加」 | 該條文與 SPEC `D-002` §P `Task 9.1` 之字面是否仍一致（SPEC 未動，請確認 SPEC 那側沒有相衝突的「相加」字樣） |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 逐條重跑你在 review-r18 提出的反例，給 `CLOSED` 或 `STILL-OPEN`。
   **(1b)** 判 `CLOSED` 者，寫出你重跑的命令與觀測到的輸出特徵。
2. **(2a)** 是否還有**第二條**生產路徑會繞過新的 wiring 測試？
   **(2b)** 若有，逐一列出並判是否阻擋。
3. **(3a)** `Categorical` dtype 下 `discarded` 是否會混入值為 0 的偽項？**請實跑**。
   **(3b)** 若會，給最小修法；若不會，說明你試了哪幾種 dtype。
4. **(4a)** 可以進 `Task 9.2`（批次 `B9B`＝`9.2`＋`9.2a`）了嗎，還是有 BLOCKING 必須先修？
   **(4b)** 若可以，說明你檢查了什麼；若不可以，列**最小**閉合集合。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**。

## 產出
canonical 四欄 findings + **Verdict**。**禁改碼、禁改 SPEC、禁改 TODO**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。
