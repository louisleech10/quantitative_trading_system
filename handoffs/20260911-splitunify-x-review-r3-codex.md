# SPLITUNIFY SPEC v3 / TODO v3 adversarial review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R3
family: codex
findings-round: R3

## Verdict：不可進 B1：CODEX-R3-P1-01、CODEX-R3-P1-02

## CODEX-R3-P1-01

**斷言**: B2b 沒有可執行的事件身份／plan provenance 對位契約，會把正確的 feature cutoff 配到錯的 event_id，或無法由 B2a 產物建立 `SplitPlan`。

**碼證**: SPEC C-4 `event_index: pd.Index` 僅是時間、無 event_id/timeframe；TODO 2.1 輸出只有 `(train_row_index,test_row_index,train_end_ms,test_start_ms)`，但 TODO 2.2 輸入是完整 `train_plan,test_plan`。`dedupe.py:46` 實際將 manifest 依 `(label_start_ms,event_id)` 重排；`alignment.py:197-213` 的 feature cutoff 則按輸入事件且可有多個 `per_tf`。VERIFY：`nl -ba ...` stdout 顯示上述行；`shasum` 已核對來源。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf, docs/SPLITUNIFY_TODO.md#a9ec9e1559a, momentum/Analysis/event_samples/dedupe.py#5962ba9c8f2e, momentum/Analysis/event_samples/alignment.py#0da3c48b2668

[BLOCKING] 信心度=High。B2b/B2c 無法在不猜順序、TF 或 hash provenance 的情況下執行；一旦 positional zip，投影會靜默錯分而 G-3b 也可能對錯 event。修法：把 `event_id→feature_cutoff_ms(+timeframe)` 作為明確輸入並規定與 manifest 的鍵對位；同時讓 B2a 輸出完整 `SplitPlan` pair，或在 B2a/B2b 間新增明名、可驗證的 adapter。

## CODEX-R3-P1-02

**斷言**: G-5 的 answer-window／leakage oracle 與 Task 2.2 的實作介面仍互斥；只把 train 事件的 `label_end_ms` 推進 test 區，按現行集合規則不會改變其 train assignment。

**碼證**: SPEC C-4／TODO 2.2 明定成員判定只看 `event_index` 是否落在 `feature_index[train/test_plan.row_index]`，且投影簽名沒有 source bars；SPEC G-5.3-4 卻要求缺 endpoint／跨界與僅修改 `label_end_ms` 時必 purge。RECHECK：以相同 `event_index`、`feature_index`、plans 只改 manifest 的 `label_end_ms`，集合判定輸入不變，故無法滿足 G-5-4。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf, docs/SPLITUNIFY_TODO.md#a9ec9e1559a

[BLOCKING] 信心度=High。這會讓答案窗跨界的 train 事件留在 assignments，直接造成 OOS leakage；G-5 也無法成為可執行的 containment gate。修法：明定事件 keyed answer-window/source-bar 輸入與 purge precedence（先驗 endpoint／跨界，再落 assignments），並讓 G-5.3/4 的 nodeid 驗證同一條規則。

## CODEX-R3-P2-03

**斷言**: Task 3.3 的前端驗收命令指向不存在且未列入修改範圍的測試檔。

**碼證**: TODO:320-335 列 `EventTablesPanel.test.tsx` 驗收，但修改檔清單沒有它；`test -e frontend/src/components/ic-analysis/EventTablesPanel.test.tsx` → rc=1；在 `frontend` 執行 `node_modules/.bin/vitest run src/components/ic-analysis/EventTablesPanel.test.tsx` → rc=1、`No test files found`。既有 `test_gap3_split_blocked.py` 實跑 → `9 passed`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#a9ec9e1559a, frontend/src/components/ic-analysis/EventTablesPanel.tsx#979163953945

[MAJOR] 信心度=High；不擋 B1，但 B3 交件會因驗收目標缺檔而失敗。修法：把該 vitest 檔納入 Task 3.3 scope，或改用實際存在的測試檔並保留兩 reason／不顯示計數列斷言。

## CODEX-R3-P2-04

**斷言**: §N R-4 的「無任何 caller、grep 只命中自身與 `__all__`」不是目前 repo 事實。

**碼證**: SPEC:595-597 的 claim；VERIFY `rg -n 'extract_event_patterns' momentum api tests` → `tests/momentum/event_samples/test_pattern_bridge.py:47,63,66,71,89,...` 多個測試 caller，rc=0。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf, tests/momentum/event_samples/test_pattern_bridge.py#ebe6d74f9965

[MAJOR] 信心度=High；不擋 B1。若 R-4 意指「無 production caller」，應改寫 claim 並保留 `blocked-by`；目前文字把測試 caller 一併否認，會污染殘留盤點與後續收斂。

## CODEX-R3-P3-05

**斷言**: G-4 被排在 B2c，但多 symbol projection 的 fail-closed 行為要到 B3 Task 3.2 才定義，G-4 的輸入／預期結果未閉合。

**碼證**: SPEC §G G-4 要「多 symbol 批逐標的計數」；§P 將 G-4 放 B2c；TODO Task 3.2（B3）則要求多 symbol → `ValueError`。未說明 G-4 是獨立 oracle／舊 producer，或應預期 raise。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf, docs/SPLITUNIFY_TODO.md#a9ec9e1559a

[MINOR] 信心度=High；不擋 B1。修法：明定 G-4 使用獨立 `split_per_symbol` oracle，或將其移到 per-symbol projection 支援之後；不得讓 B2c gate 自行猜「計數」與「fail-closed」哪個才是綠。

### 必答回覆

1. 可否進 B1：不可以；未閉合 `CODEX-R3-P1-01`、`CODEX-R3-P1-02`。
2. D1：可接受，是針對主目標「同次 UAT 不再出現兩個矛盾驗證段數字」的 95% 解法，不是偷偷把事件掃描結果冒稱 OOS；IC 報告保留 canonical 驗證段，事件掃描明示 `event-study-only`，R-5 誠實具名殘留。
3. D2：既有 L3 回歸 `venv/bin/python -m pytest tests/momentum/event_samples/test_gap3_split_blocked.py -q --tb=short` → 9 passed，沒有斷言 run-only 的三鍵；但現有 `EventTablesPanel.tsx:352` 無條件讀三鍵，刪鍵後必須靠 Task 3.3 UI 修改隱藏，且指定 vitest 檔目前不存在。
4. G-5：①不夠（未定 IC 輸出 key／對位來源，受 P1-01 影響）；②結構上夠；③不夠（無 source-bars 輸入／路徑與 purge precedence）；④不夠（P1-02，僅改 `label_end_ms` 不影響目前 membership）。
5. 介面掃描：`index_kind`、dual membership、毫秒歸一、`bucket_ms` 都有輸入或可檢查；D7 禁用秒 normalizer、D8 把 embargo 檢查移呼叫端已閉合。仍有 P1-01 的 event identity/provenance 與 P1-02 的 answer-window 檢查不在可執行簽名上。
6. 批次鏈：B2a→B2b→B2c→B3 的拓撲順序正確；B2b 需要 B2a 的完整 plans、事件 keyed cutoff 與 universe provenance，現行 B2a 只交 tuple；B2c 另有 G-4／B3 fail-closed 的 P3 歧義，沒有整個 Task 應前移。
7. 殘留：R-1 needs-research、R-2 blocked-by、R-3 user-ruling、R-5 needs-research（含 R2 裁定）均有具體理由；R-4 的 production 未接線意圖可保留但現行「無任何 caller」需改正；SU-RESID-1 needs-research 合理。沒有把可做工作偽裝成 blocked-by 的額外偷懶，但 R-4 需修正文案。

### 被當成事實的未驗證假設（§0）

- v3 隱含假設 `event_index` positional order 與重排後 manifest 永遠一致、且一個事件只有一個 feature cutoff；碼證未成立，見 CODEX-R3-P1-01。
- v3 隱含假設 changing `label_end_ms` 會被投影觀察；按現行 membership contract 不成立，見 CODEX-R3-P1-02。

STATUS: DONE
