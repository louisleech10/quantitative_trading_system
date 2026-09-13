# SPLITUNIFY b9 Task 9.1（B9A）審碼：codex

審查邊界：0bd91069 本輪 diff、brief 指定 current block；未改碼、SPEC、TODO。

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
