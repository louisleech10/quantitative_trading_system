# Reconcile — 20260911-splitunify-x-review-r3

**來源** 20260911-splitunify-x-review-r3-codex.md, 20260911-splitunify-x-review-r3-composer.md, 20260911-splitunify-x-review-r3-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——**不可進 B1**，改 v4 後再收。

🔴 **本輪三家分歧，主委採 codex（少數方）**：composer「可進 B1」（零 findings sentinel）、
grok「可進 B1」（只有 P2／P3），codex「不可進 B1：`CODEX-R3-P1-01`、`CODEX-R3-P1-02`」。
依 `feedback_offline_committee_decides`「分歧看碼證不數人頭，不決則採較嚴版」——
**codex 兩條 P1 皆有碼證且經主委實跑複驗成立**，故採 codex。

🔴 **本輪最重要的發現（`CODEX-R3-P1-02`）：我的投影設計把既有的 purge 規則整個弄丟了。**
`event_split.py:114` 現行以 **`label_end_ms > test_start - embargo`** 判 purge——這是事件側
**唯一**擋標籤窗跨界洩漏的閘。而我 v3 的 C-4 只用「`event_index` 是否 ∈
`feature_index[row_index]`」做判定，**簽名裡根本沒有 `label_end_ms`**
⇒ 答案窗跨進測試段的 train 事件會**留在 train**，直接造成 OOS leakage。
更糟的是 C-1 附帶約束①逐字寫著「未證明 containment 前**不得刪除任一既有 guard**」——
**我自己違反了自己寫的約束**，而且是在 R1／R2 兩輪審查都沒被抓到的情況下寫進 v3 的。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **E1 投影丟失答案窗 purge ⇒ OOS leakage** | **P1（實質 P0）** | CODEX-R3-P1-02 | **採納，v4 必修**。C-4 之成員判定改為**兩段式且有先後**：①**先**驗答案窗——`label_end_ms` 跨進測試段（或 source bars 上缺 endpoint）⇒ **purged**（reason 沿用 `interval_crosses_split_boundary`）；②**再**做集合成員判定決定 train／test。簽名須帶事件的答案窗（見 E2 之 keyed 輸入）。G-5.3／G-5.4 因此才變成可執行的 gate。主委實跑複驗：`sed -n '112,118p' momentum/Analysis/event_samples/event_split.py` 逐行確認 codex 所述屬實。 |
| **E2 事件身份／provenance 對位契約缺失** | **P1** | CODEX-R3-P1-01 | **採納**。C-4 之 `event_index: pd.Index` 只是時間、無 `event_id`／`timeframe`，而 `dedupe.py:46` 會依 `(label_start_ms, event_id)` **重排** manifest、`alignment.py:197-213` 之 feature cutoff 按輸入事件且可有多個 `per_tf` ⇒ 用 positional zip 對位會**靜默錯分**，連 G-3b 都可能對錯 event。v4 改為 **keyed 輸入**：`event_keys: pd.DataFrame`（欄 `event_id`／`feature_cutoff_ms`／`label_start_ms`／`label_end_ms`／`symbol`／`timeframe`），與 manifest 之鍵對位規則寫死；另明訂 B2a→B2b 之 adapter（B2a 輸出完整 `SplitPlan` pair，或新增具名可驗證 adapter）。 |
| **E3 前端測試檔不存在** | P2 | CODEX-R3-P2-03（主委補 CLAUDE-R3-P1-01） | **採納**。`test -e frontend/src/components/ic-analysis/EventTablesPanel.test.tsx` rc=1，codex 實跑 vitest 得 `No test files found`。v4 改為**新增** `eventTablesPanelCapability.test.tsx`（與既有 `eventTablesPanelByLabel.test.tsx` 命名慣例一致）並列進 Task 3.3 之修改檔案。 |
| **E4 §N R-4 之 claim 不是事實** | P2 | CODEX-R3-P2-04 | **採納**。我寫「`extract_event_patterns` 無任何 caller、grep 只命中自身與 `__all__`」——**錯的**。實跑 `grep -rn extract_event_patterns momentum api tests \| grep -v pattern_bridge.py` 命中 `tests/momentum/event_samples/test_pattern_bridge.py` 之 8 處。根因是我當時的 grep 加了 `head -15` 而前 15 行剛好全在 `pattern_bridge.py`——正是 `project_decoupling_scanner_partial` 記的「驗 scanner 勿 tail 截斷」。v4 改寫為「**無 production caller**（測試 caller 有 8 處）」並保留 `blocked-by`。 |
| **E5 embargo None 檢查未落進 Task 3.1** | P2 | GROK-R3-P2-01 | **採納**。C-5／Task 2.2 要點 7 說該檢查「住呼叫端（Task 3.1）」，但 Task 3.1 之實作要點 1–3 與驗證 (A)–(D) **都沒有它** ⇒ B3 實作端只讀 Task 3.1 會漏做。v4 於 Task 3.1 補要點與 `-k embargo_must_be_none` 驗證。 |
| **E6 `estimand_note` 之行號引用指錯檔** | P3 | GROK-R3-P3-01 | **採納**。`tables.py` 只有 371 行；該模式實際在 `pipeline.py:598-599`，且 `common` 來自 `tables.py:130-151` 之 `_common_constraint_block`（`:279` 掛上）。v4 改為「沿用 `pipeline.py:598-599` 之揭露欄位模式，欄位寫入 `_common_constraint_block`」。 |
| **E7 codex P3-05 與 composer／grok 之其餘意見** | P3 | CODEX-R3-P3-05、COMPOSER-R3-P3-00、GROK-R3-P3-01 | **記錄**。composer 為零 findings sentinel（判可進 B1）；grok 除 P2-01／P3-01 外無異議。兩家之「可進 B1」被 codex 之 E1／E2 覆蓋——**這不表示兩家審得不夠**，而是 E1 需要把 SPEC 的 C-4 與 §G 對照著讀才看得出互斥，codex 正是用「介面可執行性」那條必答 5 的掃法抓到的。 |

### 主委之自我記帳（不淡化）

- 我在 R3 brief 的必答 5 明確要求三家「掃一遍 v3 的介面可執行性」——**codex 照做並抓到 E1／E2**，
  另兩家沒抓到。這條必答是 R2 學到的（D7／D8 兩條介面自相矛盾），**寫進 brief 有用**。
- 但 E1 本身是我在 v3 造成的：把「投影＝集合成員判定」寫得太乾淨，把 interval-aware purge
  當成「舊實作的細節」而不是「必須保留的 guard」。C-1 附帶約束①是我自己寫的，我自己違反。
- E4 是我引用 truncated grep 的結果。這是 `CLAUDE.md` Gotchas 已具名的坑，我又踩一次。

### 收斂趨勢

R1 13 群集（3 P0）→ R2 11 群集（3 P0）→ R3 **7 群集（0 P0、2 P1、3 P2、2 P3）**。
P0 已清零、P1 集中在**同一個設計缺口**（投影的輸入不足以做答案窗判定）。
⇒ v4 修完 E1／E2 即為收斂；**不需 R5**，改走一輪針對 E1／E2 的定向確認即可
（brief 只問「E1／E2 是否閉合」）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
2. D1：可接受，是針對主目標「同次 UAT 不再出現兩個矛盾驗證段數字」的範圍裁定（🔴 2026-09-11 更正：原文寫「95% 解法」，那是治理票原則，量化主線禁用；本項之所以成立是因為**三家逐輪複查後一致無異議**，不是因為「差不多」），不是偷偷把事件掃描結果冒稱 OOS；IC 報告保留 canonical 驗證段，事件掃描明示 `event-study-only`，R-5 誠實具名殘留。
3. D2：既有 L3 回歸 `venv/bin/python -m pytest tests/momentum/event_samples/test_gap3_split_blocked.py -q --tb=short` → 9 passed，沒有斷言 run-only 的三鍵；但現有 `EventTablesPanel.tsx:352` 無條件讀三鍵，刪鍵後必須靠 Task 3.3 UI 修改隱藏，且指定 vitest 檔目前不存在。
4. G-5：①不夠（未定 IC 輸出 key／對位來源，受 P1-01 影響）；②結構上夠；③不夠（無 source-bars 輸入／路徑與 purge precedence）；④不夠（P1-02，僅改 `label_end_ms` 不影響目前 membership）。
5. 介面掃描：`index_kind`、dual membership、毫秒歸一、`bucket_ms` 都有輸入或可檢查；D7 禁用秒 normalizer、D8 把 embargo 檢查移呼叫端已閉合。仍有 P1-01 的 event identity/provenance 與 P1-02 的 answer-window 檢查不在可執行簽名上。
6. 批次鏈：B2a→B2b→B2c→B3 的拓撲順序正確；B2b 需要 B2a 的完整 plans、事件 keyed cutoff 與 universe provenance，現行 B2a 只交 tuple；B2c 另有 G-4／B3 fail-closed 的 P3 歧義，沒有整個 Task 應前移。
7. 殘留：R-1 needs-research、R-2 blocked-by、R-3 user-ruling、R-5 needs-research（含 R2 裁定）均有具體理由；R-4 的 production 未接線意圖可保留但現行「無任何 caller」需改正；SU-RESID-1 needs-research 合理。沒有把可做工作偽裝成 blocked-by 的額外偷懶，但 R-4 需修正文案。

### 被當成事實的未驗證假設（§0）

- v3 隱含假設 `event_index` positional order 與重排後 manifest 永遠一致、且一個事件只有一個 feature cutoff；碼證未成立，見 CODEX-R3-P1-01。
- v3 隱含假設 changing `label_end_ms` 會被投影觀察；按現行 membership contract 不成立，見 CODEX-R3-P1-02。

STATUS: DONE
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對 R2 之 D1–D11 在 v3 的閉合情況、七道必答與 §1 十一類必查後，無未閉合之 P0/P1 finding；v3 可放行 B1。

**碼證**: `sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md` → `d851e56dc1bf…`／`a9ec9e1559a8…`；R2 P0 閉合點——D1 `SPEC.md:71-81`+`§N R-5`、D2 `SPEC.md:86-88`+Task 3.3:498-501、D3 `SPEC.md:246-262`+TODO:227-238；介面——`ic_filter_orchestrator.py:269-271`（ms 拒收）、C-4:149-157（`bucket_ms` 簽名）、C-5:199-201（embargo 呼叫端）；必答 3——`test_gap3_split_blocked.py` 無三鍵斷言、`EventTablesPanel.tsx:352` 已列 Task 3.3 修改範圍。RECHECK: `rg -n '恆走|event-study-only|estimand_scope|G-5|ms_same_source|split_events_production_call_count' docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md`

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf, docs/SPLITUNIFY_TODO.md#a9ec9e1559a8

[NON-BLOCKING] 信心度=High。核對依據＝brief R2→v3 變更表 11 行逐條 grep＋必答 3/5 所列生產檔案:行號實讀；未發現會在 B1–B4 具體失敗且 v3 未覆蓋之缺口。殘留 P3：`tables.py:598-599` 行號筆誤（應指 `pipeline.py:598-599`），建議 v3.1 順手改正，**不擋 B1**。

---

## GROK-R3-P2-01

**斷言**: C-5／Task 2.2 要點 7 把「`EventSplitConfig.embargo_ms`／`embargo_ms_by_symbol` 須為 `None` 否則 raise」的落點指定在 Task 3.1 接線處，但 Task 3.1 的實作要點（僅 1–3）與驗證 (A)–(D) **都未列入該檢查**——B3 實作端只讀 Task 3.1 時會漏做。

**碼證**: SPEC C-5（約 L196-201）與 TODO Task 2.2 要點 7 明文「住呼叫端（Task 3.1）」；對照 SPEC／TODO Task 3.1 實作要點只有 holdout_boundary 接線／pipeline 選填／`split_events` 呼叫點＝0，驗證無 embargo None 之 pytest nodeid。RECHECK：`awk '/Task 3.1 —/,/Task 3.2 —/' docs/SPLITUNIFY_SPEC.md` 與同段 TODO。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf

[MAJOR] 信心度=High；**不擋 B1**（B1 不動生產碼）。會怎麼失敗：B3 接線後仍可能靜默忽略上游 `embargo_applied`（EVTLABEL 已踩過的形態），且無 mutation／驗收命令會紅。  
**修法**：Task 3.1 實作要點增「投影路徑呼叫前 assert config.embargo_* is None」＋一條 `-k embargo_must_be_none`；可施工前小補進 SPEC／TODO，不必 R4。

---

## GROK-R3-P3-01

**斷言**: Task 3.3／C-0 決議③(b) 寫「沿用 `tables.py:598-599` 之 `estimand_note` 模式」，但 `tables.py` 僅 371 行、該模式實際在 `pipeline.py:598-599`（且掛在 all-bars 表，不是 `event_forward_return_table["common"]`）。

**碼證**: `wc -l momentum/Analysis/event_samples/tables.py` → 371；`pipeline.py:598-599` 有 `rep["estimand_note"]=...`；`event_forward_return_table` 之 `common` 來自 `tables.py:130-151` `_common_constraint_block`（L279 掛上）。驗收句 `event_forward_return_table["common"]["estimand_scope"] == "full_sample_not_oos"` 本身可執行。RECHECK：對上述行號 `sed -n`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf

[MINOR] 信心度=High；**不擋 B1**。失敗模式：Agent 搜 `tables.py:598` 找不到而短暫迷惑；依驗收斷言仍會改對 `_common_constraint_block`／common。  
**修法**：把引用改為「沿用 `pipeline.py:598-599` 之揭露欄位模式，欄位寫入 `_common_constraint_block`」。

---

STATUS: DONE
