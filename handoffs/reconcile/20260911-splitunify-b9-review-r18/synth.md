# Reconcile — 20260911-splitunify-b9-review-r18

**來源** 20260911-splitunify-b9-review-r18-codex.md, 20260911-splitunify-b9-review-r18-composer.md, 20260911-splitunify-b9-review-r18-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **A1 生產接線可靜默失效——四條具名測試全在 `derive_*` 層，caller 省略 kwarg 仍全綠**——「生產接線`pipeline.py`若省略」 | P1 | GROK-R18-P1-01 | 採納（🔴 **這正是主委在 brief 必答 5b 問「有沒有第三種破壞方式讓記帳失效但測試全綠」的答案，由該家找出**。修法：新增 `tests/momentum/event_samples/test_splitunify_wiring.py::test_splitunify_wiring_discarded_rows_reaches_summary`，斷言掛在 **`EventSamplePipeline.run`** 上，並以兩個 feature TF 之真實 kline fixture 使 `discarded` 非空（單 TF 下恆為 `{}`、無鑑別力）。**主委實跑驗鑑別力**：把 `pipeline.py` 之 `discarded_rows_by_feature_tf=` 拿掉 ⇒ 該測試轉紅（斷言到空 dict），還原後綠；修補後回歸見本檔裁定第 2 點，VERIFY:20260913T161341Z-splitunify-b9-t91-r18-fixes） |
| **A2 多 symbol（Mapping）分支無具名測試，改傳 `{}` 時全綠（三家撞題）**——「多symbolMapping分支之`di」「多symbolMapping分支目前確實」「`derive_event_split_」 | P2 | COMPOSER-R18-P2-01, CODEX-R18-P2-01, GROK-R18-P2-02 | 採納（composer 實證「僅破壞分派器為 `{}` 時 692 passed 全綠」。修法：新增 `test_multi_symbol_branch_carries_discarded_rows_verbatim`，含**值相等**斷言與**防放大**斷言（值被乘倍即紅）。**主委實跑驗鑑別力**：分派器改傳 `{}` ⇒ 該測試轉紅，還原後綠；修補後回歸見本檔裁定第 2 點，VERIFY:20260913T161341Z-splitunify-b9-t91-r18-fixes） |
| **A3 `timeframe` 缺值會產生名為 `nan` 的假 feature TF（兩家撞題）**——「build_event_keys先把ti」「`per_tf["timeframe"]」 | P1 | CODEX-R18-P1-02, COMPOSER-R18-P3-01 | 採納（🔴 **主委在 brief assumed 第 2 條已自標此疑慮並請三家攻，兩家各自證實**。字串化 把 `NaN`／`pd.NA` 變成字面 `"nan"`／"<NA>"，`discarded` 於是長出**看起來合法、實際不是 TF** 的鍵。修法：**缺 TF 是壞資料、不是一種 TF** ⇒ 在計數前以 isna 檢查 fail-closed raise，並配 `test_build_event_keys_rejects_nan_timeframe_in_dropped_rows`） |
| **A4 探針檔未隨二值回傳更新，case A 直接 TypeError（三家撞題）**——「build_event_keys改成二值」「`handoffs/20260911-s」 | P1 | CODEX-R18-P1-01, COMPOSER-R18-P2-02, GROK-R18-P3-01 | 採納（🔴 **根因是主委自己造成的**：consult-r2 裁定 REVERT 時把該探針一併還原到 HEAD 的單值形態，Task 9.1 改簽章後就壞了——回退與前進之間漏了這一步。修法：改為兩值 unpack 並一併印出 `discarded`。**主委實跑四案**：A discarded 為空／B raise 多列 per_tf／C discarded 記到 4h 兩列／D raise 缺 cutoff，全部如文件所述） |
| **A5 TODO 條文「多 symbol 逐 symbol 相加」與實際資料流互斥（兩家撞題）**——「TODOTask9.1的「多symbol」「TODO`Task9.1`實作要點2寫「」 | P2 | CODEX-R18-P1-03, GROK-R18-P2-01 | 採納（🔴 **主委在 brief assumed 第 1 條已自標並請三家裁，兩家一致判「實作對、TODO 條文錯」**：`build_event_keys` 對整批 `receipts.per_tf` 只呼叫一次，`discarded` 為批次級、無逐 symbol 分量，照字面相加會按 symbol **重複放大**。修法：TODO 實作要點 2 改寫為「原樣傳遞、不得相加」並載明理由與鎖住它的測試） |
| **A6 `_build_summary` docstring 仍寫 12 鍵且引用不存在的行號（兩家撞題）**——「_build_summary的現行doc」「`_build_summary`docs」 | P3 | CODEX-R18-P3-02, GROK-R18-P3-02 | 採納（鍵數已為 13、pipeline 的 696 行 之行號早已不存在。修法：docstring 改為 13 鍵、刪掉失效行號引用，並明寫「鍵數之權威是 test_summary_has_all_thirteen_keys 之 exact-set 斷言，不是這段散文」——避免同一個數字再長出第二份真相源） |

### 本輪裁定
1. **六群全數採納並修完**；`Task 9.1` 之實作面新增三條具名測試（生產接線／多 symbol 分支／NaN fail-closed），每條皆經**主委實跑破壞驗鑑別力**後還原。
2. **回歸**：`tests/momentum/Analysis/test_splitunify_derive.py` ＋ `tests/momentum/event_samples/` ＋ golden ＋ contract ＋ `tests/api/test_splitunify_disclosure.py` ＋ `..._event_study_only.py` 合計 **695 passed**（較 R18 當時之 692 多 3 條新測試）、0 failed。
3. 🔴 **本輪最值得記的一件事**：主委在 brief 裡自標的兩條 assumed（多 symbol 相加、`value_counts` 之 dtype 陷阱）**兩條都被證實為真問題**，而 A1 之「第三種破壞」也正是主委自己問出來的。⇒ **把自己沒把握的面寫進 brief 交出去攻，比自己再讀一遍有效**。
4. **下一步**：派 `review-r19` 做 A1–A6 之閉合再驗證；三家確認後進 `Task 9.2`（批次 `B9B`＝`Task 9.2` ＋ `9.2a`，不得拆批）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R18-P1-01

**斷言**: build_event_keys 改成二值回傳後，repo 內被 TODO／FACT-RECEIPT 當作可重跑探針的 handoffs/20260911-splitunify-b9-probe-multitf.py 仍以單一 DataFrame 接收，現行 Case A 即失敗；因此 Task 9.1 的 caller closure 尚未完成。

**碼證**: VERIFY: venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py → rc=1，TypeError: tuple indices must be integers or slices, not str（line 47 的 out = ...，line 52 的 out["event_id"]）。
CODE-ANCHOR: handoffs/20260911-splitunify-b9-probe-multitf.py:47
MUTATION: 對 tuple-returning build_event_keys 保持 out = build_event_keys(...) 單值接收，重跑上述命令即重現 TypeError。

**來源摘要**: handoffs/20260911-splitunify-b9-probe-multitf.py#ec28dd11cf01

[BLOCKING] 信心度=High。rg -n --glob '*.py' 'build_event_keys' . 顯示 production caller pipeline.py:747 與測試已改為二值形狀，但該 tracked probe 是唯一未改的實際 caller；其 docstring 明示它是可重跑探針，TODO :425-426 也宣稱其 tuple unpack 已還原，兩者與工作樹事實不符。最小修法是讓 probe 同批 unpack (out, _discarded)，再以 out 做列數與 event_id 觀測；可行性已由 production caller pipeline.py:747-754 的同型 unpack 實證。此項需在進 Task 9.2 前閉合，否則既有 FACT-RECEIPT 不可重跑。

## CODEX-R18-P1-02

**斷言**: build_event_keys 先把 timeframe .astype(str) 再計數，遇到缺失 timeframe 時會把 NaN／pd.NA 記成偽 feature-TF 鍵，而不是 fail-closed 或保留為無效輸入；這會讓 discarded_rows_by_feature_tf 產生看似合法但非 TF 的數字。

**碼證**: VERIFY: 實跑 build_event_keys，Categorical(['1h','4h', NaN]) → {'4h': 1, 'nan': 1}；object 同樣 → {'4h': 1, 'nan': 1}；string + pd.NA → {'4h': 1, '<NA>': 1}；Categorical 未使用類別則不產生 0 項，因為計數前已轉成字串。
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:294
MUTATION: 將 per_tf.timeframe fixture 設為 ['1h', '4h', np.nan]（保留一列有效 selected 1h）後重跑 build_event_keys(..., selected_timeframe='1h')，現行輸出含 {'nan': 1}。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[BLOCKING] 信心度=High。現行 :286-296 同時用字串化欄位做 selected filter 與 discarded counter，故缺失值在 value_counts() 前已不再是缺失。最小修法是於字串化前對 per_tf['timeframe'].isna() 做具名 ValueError fail-closed 閘，再沿現有字串計數；不應直接 drop，因那會重新隱藏未被記帳的列。可行性：pandas Series.isna() 已可直接對上述三種 dtype 產生布林 mask，且 valid string／Categorical（無缺失）路徑的現有測試輸出不變。這是資料品質與揭露正確性問題，需在進 Task 9.2 前閉合。

## CODEX-R18-P1-03

**斷言**: TODO Task 9.1 的「多 symbol 分派器逐 symbol 相加」與實際資料流互斥：build_event_keys 對整批 receipts.per_tf 只呼叫一次，discarded 是批次級字典；照 TODO 字面相加會把同一批計數按 symbol 重複放大。

**碼證**: VERIFY: 兩 symbol Mapping 反例以 discarded_rows_by_feature_tf={'4h': 7, '12h': 2} 呼叫 derive_event_split_from_plans，stdout 摘要為 summary == input 且 summary != {'4h': 14, '12h': 4}；rg -n 'build_event_keys' momentum/Analysis/event_samples/pipeline.py 只有單一 production call site pipeline.py:747-749。
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:685
MUTATION: 在 Mapping summary call 將 discarded_rows_by_feature_tf=discarded_rows_by_feature_tf 改成逐 symbol 累加同一輸入字典；兩 symbol 輸入 {'4h': 7, '12h': 2} 即得到錯誤 {'4h': 14, '12h': 4}。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a3afd566fc1d

[BLOCKING] 信心度=High。現行實作 :685-688 明確採 producer 對整批 receipt 一次計數後原樣傳遞，這個選擇在實跑反例中保留正確數值；不存在可供逐 symbol 相加的分量。最小閉合是把 TODO :448 改成「多 symbol 分派器將整批 producer 字典原樣傳遞，不逐 symbol 相加」；若要保留相加語意，則必須另行把 producer 改造成逐 symbol 計數，已超出本 Task 的輸入／輸出與現行唯一 caller。進 Task 9.2 前需消除此契約歧義，避免下一輪照字面引入 double-count。

## CODEX-R18-P2-01

**斷言**: 多 symbol Mapping 分支目前確實把非空 discarded 帶到 summary，但沒有具名測試鎖定這條新資料流；現有多 symbol 測試只驗 assignments／symbol／門檻等舊欄，未驗 discarded_rows_by_feature_tf 的值相等。

**碼證**: VERIFY: 兩 symbol 反例實跑 result.summary['discarded_rows_by_feature_tf'] == {'4h': 7, '12h': 2}；tests/momentum/Analysis/test_splitunify_derive.py 的新具名 summary 測試只走舊式單 symbol，Mapping 測試區 :1073-1195 沒有非空 discarded assertion。MUTATION: 將 Mapping 分支 :688 的參數改為 {}；以 runtime-equivalent mutation 跑 brief 指定完整命令，結果仍為 692 passed in 69.23s、rc=0（MAPPING_MUTATION_RC=0）。
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:677

**來源摘要**: tests/momentum/Analysis/test_splitunify_derive.py#6107794020e5

[MINOR] 信心度=High。現行分支的值傳遞不是已發現的邏輯錯誤，所以不是 P1 行為 finding；但它的回歸防護不足，且上述可執行破壞在完整指定測試集仍綠。最小修法是補一條具名 Mapping 測試：傳入非空 producer 字典，逐值斷言 summary 相等且不按 symbol 倍增。此項不單獨阻擋 Task 9.2，但應與 P1-03 一起收斂。

## CODEX-R18-P3-02

**斷言**: _build_summary 的現行 docstring 仍寫 EventSplitPlan.summary 有 12 個必填鍵，且引用已不存在的 pipeline.py:696；本輪實作已將實際鍵集改為 13，測試也改成 exact 13-key assertion。

**碼證**: VERIFY: rg -n '12 個必填鍵|pipeline\\.py:696|test_summary_has_all_twelve_keys' ... → 唯一 current-code 命中為 split_projection.py:719-722；test_splitunify_derive.py:594-614 實際斷言 13 鍵，pipeline 現行 summary 更新在 pipeline.py:763-765。
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:719

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[MINOR] 信心度=High；doc-literal-only。這不改執行結果，也沒有在 pipeline／下游發現寫死 12 的 executable gate；但會誤導下一位維護者判斷 summary 契約。修法是把 docstring 更新為 13 並指向現行 summary propagation 行。

### 假設攻擊與必答

1. **(1a)** 裁定「批次級原樣傳遞」正確；現行唯一 production producer call 在 pipeline.py:747-749 吃整批 receipts，Mapping 分支只切 event_keys。逐 symbol 相加會重複同一批數字。
   **(1b)** TODO Task 9.1 :448 應改為：「多 symbol 分派器將 producer 對整批 receipts.per_tf 產出的 discarded 原樣傳到最終 summary，不逐 symbol 相加。」若要相加，必須先有逐 symbol producer 分量；現行呼叫圖沒有該來源。
2. **(2a)** 是，Mapping 分支帶到 summary。實跑兩 symbol interleaved fixture，輸入 {'4h': 7, '12h': 2}，輸出同值且非 {'4h': 14, '12h': 4}。
   **(2b)** 是，應補具名測試；目前實作正確但 P2-01 的 Mapping mutation 以指定 692 測試全綠，證明沒有鑑別力。
3. **(3a)** 未使用 Categorical 類別不會形成值 0 偽項，因為 code 先 .astype(str)；但缺失值會形成 "nan" 或 "<NA>" 偽項。上述三種 dtype 已實跑。
   **(3b)** 最小修法是加 missing-timeframe fail-closed dtype-independent 閘，再做字串化與計數；不是只加 Categorical dtype 閘，也不是 drop 缺失列。
4. **(4a)** production caller pipeline.py:747 已改；測試 caller 已改為接收 tuple 或只在 raises case 呼叫；唯一未改的 executable caller 是 handoffs/20260911-splitunify-b9-probe-multitf.py:47。handoffs/20260911-splitunify-b2b-mutate.py:93 只是 mutation 描述字串，不是 call site。
   **(4b)** probe 阻擋，因為它是 tracked、可重跑 FACT-RECEIPT，現行命令 rc=1；b2b mutation 描述不阻擋。
5. **(5a)** M-SU-D2-01 的 runtime-equivalent deletion 使 3 條具名測試失敗：test_summary_has_all_thirteen_keys、test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer、test_discarded_layer_is_independently_revertible。M-SU-D2-02 的 runtime-equivalent {} 傳遞使 producer-value equality 測試失敗 1 條；兩條都有鑑別力。
   **(5b)** 有。將 Mapping 分支的 summary forwarding 改成 {} 是第三種破壞；它使多 symbol 記帳失效，但完整 brief 測試集仍實跑 692 passed in 69.23s、rc=0。pipeline canonical integration 目前只以單一 TF fixture 走到非空 discarded 以外的路徑，不能補上這個缺口。
6. **(6a)** 不能進 Task 9.2。最小 blocking closure 是 P1-01 修 probe caller、P1-02 對缺失 timeframe fail-closed、P1-03 修正 TODO 的批次級契約字面；P2-01 與 P3-02 非單獨 blocking，但 P2-01 應一併補測。
   **(6b)** 上述三項是最小閉合集合；未重開 Task 9.2–9.5 設計，也未改 SPEC／TODO。

### 收尾稽核

ASSUMPTIONS_VERIFIED: SPEC stamp gate bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md rc=0；指定 692-test baseline venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/ tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py → 692 passed、0 failed；probe rc=1 已重現；Categorical／object NaN／StringDtype NA、multi-symbol summary、兩條既有 mutation 與第三 mutation 均已實跑。
TESTS_RUN: baseline rc=0、692 passed in 69.14s；runtime-equivalent M-SU-D2-01=3 failures、M-SU-D2-02=1 failure；runtime-equivalent Mapping forwarding mutation rc=0、692 passed in 69.23s；venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py rc=1 TypeError；bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md rc=0。
FAILURES_SEEN: probe stale caller TypeError；NaN／pd.NA 偽 TF 計數；TODO multi-symbol 相加字面與 batch-level 實作衝突；P2 Mapping mutation 692-test 全綠；以上均保留為本輪 findings，未就地改碼。
SCOPE_CHANGES: none；只新增本交件檔，未改 production code、測試、SPEC、TODO、HANDOFF.md 或 data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: 審查未改輸出；確認本輪 tuple return 與 summary 第 13 鍵已存在，並記錄 invalid-null 輸入會產生偽鍵。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-b9-review-r18-codex.md

VERDICT: blocked
BLOCKED-BY: CODEX-R18-P1-01,CODEX-R18-P1-02,CODEX-R18-P1-03
CLOSED:
## COMPOSER-R18-P2-01

**斷言**: 多 symbol Mapping 分支之 `discarded_rows_by_feature_tf` 無具名測試；僅破壞 `split_projection.py:688` 為 `{}` 時 **692 passed 全綠**，記帳可在多 symbol 路徑靜默失效。

**碼證**: `split_projection.py:677-688` 多 symbol `_build_summary` 傳遞 discarded；per-symbol 迴圈 L654-658 不傳。`test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 只用 `_basic_case()` 單 symbol。第三 mutation 實跑：`awk 'NR==688{sub(/discarded_rows_by_feature_tf=discarded_rows_by_feature_tf/,"discarded_rows_by_feature_tf={}")}1' split_projection.py` → 全套 692 passed。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d9674adea08c

[P2] 修法：在 `test_splitunify_derive.py` 增 `test_per_symbol_summary_carries_discarded_rows_by_feature_tf`——用 `_interleaved_case()` + 非空 `discarded_rows_by_feature_tf` 斷言 summary 值相等。可行性：沿用既有 `_interleaved_case` fixture，無新腳本；加後第三 mutation 必紅。信心度=High。

---

## COMPOSER-R18-P2-02

**斷言**: `handoffs/20260911-splitunify-b9-probe-multitf.py` 未隨 Task 9.1 tuple 回傳更新，實跑 case A 即 `TypeError`，§A FACT-RECEIPT 不可複驗。

**碼證**: `handoffs/20260911-splitunify-b9-probe-multitf.py:47-52` 仍 `out = build_event_keys(...); len(out)`；`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → `TypeError: tuple indices must be integers or slices, not str`。

**來源摘要**: handoffs/20260911-splitunify-b9-probe-multitf.py#probe-broken

[P2] 修法：`keys, discarded = build_event_keys(...)` 並在 case C 印出 `discarded`。可行性：單檔兩行；不動生產碼。信心度=High。不阻 9.2。

---

## COMPOSER-R18-P3-01

**斷言**: `per_tf["timeframe"]` 為 NaN 之 dropped 列會產生 `discarded` 鍵 `'nan'`，可能誤導呼叫端。

**碼證**: `/tmp/r18-composer-probes.py` 插入 NaN timeframe 列 ⇒ `discarded={'4h': 2, '12h': 1, 'nan': 1}`；`split_projection.py:294-296` 無 `dropna`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d9674adea08c

[P3] doc-literal-only 邊界。修法：計數前 `dropna()` 或排除 `str(tf)=='nan'`。現行對齊路徑未見 NaN 為合法輸入；不阻 9.2。信心度=Medium。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: 692 passed；M-SU-D2-01 三紅／M-SU-D2-02 一紅；多 symbol discarded 反例；value_counts 三 dtype；全 repo build_event_keys 掃描；第三 mutation 692 綠  
TESTS_RUN: 全套 692 pytest rc=0；M-SU-D2-01/02 mutation 重跑；`/tmp/r18-composer-probes.py`；第三 mutation（僅 L688）692 綠；`handoffs/...-probe-multitf.py` TypeError  
FAILURES_SEEN: none（mutation 預期失敗已還原）  
SCOPE_CHANGES: none（review-only；/tmp 探針已清）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）

STATUS: DONE
## GROK-R18-P1-01

**斷言**: 生產接線 `pipeline.py` 若省略 `discarded_rows_by_feature_tf=discarded_rows`，Task 9.1 全部具名測試與既有 wiring 測試仍全綠——記帳在唯一生產呼叫點可靜默失效。

**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:754  
MUTATION: 刪除 `discarded_rows_by_feature_tf=discarded_rows,` 一行後執行 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'discarded or thirteen_keys'` → 全綠；`venv/bin/python -m pytest -q tests/momentum/event_samples/test_splitunify_wiring.py` → 9 passed。對照：同檔 `tier_min_test_events` 已有 `test_splitunify_wiring_tier_min_test_events_reaches_projection`（:146）防 H6 回歸，discarded 無對等探針。單 TF fixture 下 `discarded=={}`，summary 鍵存在／等於 `{}` **無法**區分「有傳空 dict」與「沒傳（None→{}）」。

**來源摘要**: momentum/Analysis/event_samples/pipeline.py#db6753fd6161

[P1] 信心度=High。會怎麼失敗：實作正確時看似完工；之後任一重構若漏傳 kwarg，summary 永遠 `{}`，靜默丟棄再次對呼叫端不可見，且 CI 不紅。  
**修法**：在 `tests/momentum/event_samples/test_splitunify_wiring.py` 新增一條（對齊既有執行期探針風格）——`monkeypatch` `build_event_keys` 令其回傳具名非空 `discarded`（例如 `{"4h": 3}`），跑投影路徑 `EventSamplePipeline().run(...)`，斷言 `res.split_plan.summary["discarded_rows_by_feature_tf"] == {"4h": 3}`。  
**可行性證據**：同檔已用 runtime probe（非原始碼形狀）抓 H6；`build_event_keys` 已從 `pipeline` 模組 import，monkeypatch 點與 `spy_split` 同型；不需多 TF bars 即可令「漏傳」轉紅。

---

## GROK-R18-P2-01

**斷言**: TODO `Task 9.1` 實作要點 2 寫「多 symbol 分派器逐 symbol 相加」，與現行呼叫圖／實作（批次級原樣傳遞）互斥；照字面實作會重複計數。

**碼證**: `docs/SPLITUNIFY_TODO.md` Task 9.1 要點 2 原文「逐 symbol **相加**」；對照 `split_projection.py:685-688` 具名「不得再相加」＋ `pipeline.py:747` 單一呼叫點。doc-literal-only（行為以實作為準且正確）。RECHECK：`grep -n "build_event_keys" momentum/Analysis/event_samples/pipeline.py` 僅 import＋一呼叫。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a3afd566fc1d

[P2] 信心度=High。修法：將要點 2 末句改為「原樣傳遞（批次級；不得逐 symbol 相加）」。不擋產品行為，但會誤導下一輪 Agent。

---

## GROK-R18-P2-02

**斷言**: `derive_event_split_from_plans` 之 Mapping（多 symbol）分支目前無具名測試覆蓋 `discarded_rows_by_feature_tf` 傳遞，回歸只能靠讀碼。

**碼證**: `test_summary_carries_discarded_rows_by_feature_tf_equal_to_producer` 只走單標的 wrapper；`test_per_symbol_*` 皆未傳 discarded。本輪反例實跑確認 Mapping 路徑**行為正確**（手注與 producer e2e 值相等）。CODE 落點：`split_projection.py:688`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[P2] 信心度=High。修法：`_interleaved_case()` + `discarded_rows_by_feature_tf={"4h":7}` 值相等斷言一條即可。非 BLOCKING（行為已證）。

---

## GROK-R18-P3-01

**斷言**: `handoffs/20260911-splitunify-b9-probe-multitf.py` 仍把 `build_event_keys` 回傳值當單一 DataFrame，簽章改 tuple 後探針語意損壞。

**碼證**: `handoffs/20260911-splitunify-b9-probe-multitf.py:47` `out = build_event_keys(...)`；`len(out)` 對 tuple 為 2。doc-literal／探針維護，非生產 caller。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[P3] 信心度=High。修法：unpack `(keyed, discarded)` 並印 discarded。不阻擋 9.2。

---

## GROK-R18-P3-02

**斷言**: `_build_summary` docstring 仍寫「12 個必填鍵」，與實作 13 鍵／測試 `thirteen_keys` 漂移。

**碼證**: `split_projection.py:719` docstring「12 個必填鍵」；同函式 :762 已寫入第 13 鍵。doc-literal-only。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#d3c9d0208d59

[P3] 信心度=High。修法：docstring 改「13 個必填鍵」。

---

