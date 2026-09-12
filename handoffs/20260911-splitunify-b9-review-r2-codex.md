# SPLITUNIFY D-002 閉合輪 R2：codex

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R2
findings-round: R2

§0 前提挑戰：fact-verified＝R1 七群 15 條全採納（R1 synth）；`doc_format_precheck` rc=0；`spec_xref_check --synth` rc=0；`event_id` 的 trigger TF 來源已讀碼。assumed＝C3 不誤殺、C6 三量全是事件數、18 mutation 覆蓋完整、C0 無殘留歧義；本輪以程式碼、測試與可重跑命令挑戰，前三項均有反證，C0 留有契約歧義。

必查 11 類：矛盾/互斥＝P1-02、P1-05、P1-08；端到端＝P1-03、P1-04、P1-05；不可測＝P1-02、P1-06；quant／leakage＝P1-01、P1-02；過度工程＝無；OOM/並行＝無；cache＝無；API/型別＝P1-03、P1-04；測試品質＝P1-01、P1-06；Agent 可執行性＝P1-04、P1-06、P2-07；必要性/短命工＝無。

R1 closure：`CODEX-R1-P1-01` CLOSED（D-002-C5 (5.5)、C6、Task 9.4）；`CODEX-R1-P1-02` CLOSED（Task 9.1 返回形狀、跨邊界與三層揭露）；`CODEX-R1-P1-03` CLOSED（C0 分出 trigger/feature 語意）；`CODEX-R1-P1-04` CLOSED（Task 9.3 逐處列名、groupby 折疊與 event-level 粒度）；`CODEX-R1-P2-05` CLOSED（G-1/G-2/G-3）；`CODEX-R1-P1-06` 仍 blocked（見 P1-06）。

## CODEX-R2-P1-01

**斷言**: D-002-C3 會把目前資料契約允許的合法多 feature TF 事件誤 purge；它只要求各 cutoff `<= decision_at_ms`，沒有要求不同 TF cutoff 相同或以同一事件時間錨定。

**碼證**: `momentum/Analysis/event_samples/alignment.py:197-213` 對每個 `sub_tf` 各自以 as-of 規則取 `feature_cutoff_ms`，唯一 PIT 閘是 `cutoff <= decision_at`；`docs/SPLITUNIFY_SPEC.D-002.md:44-50,167-170` 卻把異側一律 purge。VERIFY：`venv/bin/python -c 'from pprint import pprint; rows=[("E","1h",1000,"train"),("E","4h",2000,"test")]; pprint({"same_event":len({r[0] for r in rows})==1,"asof_cutoffs":all(r[2] <= 3000 for r in rows),"sides":{r[1]:r[3] for r in rows},"mixed_side":len({r[3] for r in rows})>1})'` → `same_event=True`, `asof_cutoffs=True`, `mixed_side=True`。RECHECK：重跑命令並讀上述 alignment 行。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/alignment.py#0da3c48b2668;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。這不是不合規或 look-ahead 輸入：兩個 cutoff 都早於同一 decision，卻可跨 split boundary，Task 9.x 將合法樣本從 train/test 兩側整批刪掉並改變統計分母。修法：明確選定「事件時間錨定同側」或承認這是保守資料損失；若保留 purge，須把它寫成有意政策並給損失量與成對測試。可行性證據是現行 alignment 已提供 per-TF cutoff 產生點，新增一個雙 TF fixture 即可驗證政策。

## CODEX-R2-P1-02

**斷言**: C3 要求混側 purge 使用「具名字面」，但 D-001 與現行契約只允許既有 `interval_crosses_split_boundary`，D-002 沒有指定新字面或其唯一真相源。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:46,169` 只寫「具名字面」；`docs/SPLITUNIFY_SPEC.D-001.md:152-155` 禁止另造 purge reason 並指定既有字面；`momentum/Analysis/contracts/split_unify.json:2,11-17` 指向 `event_import_contract.json`，其 `:465-466` 只有 `interval_crosses_split_boundary`；`momentum/Analysis/event_samples/split_projection.py:58-77,187-188` 以該封閉集合自證。VERIFY：`rg -n 'split_purge_reasons|interval_crosses_split_boundary|具名字面' docs/SPLITUNIFY_SPEC.D-001.md docs/SPLITUNIFY_SPEC.D-002.md momentum/Analysis/contracts momentum/Analysis/event_samples/split_projection.py` → 只見既有字面與 D-002 未定名要求。RECHECK：重跑同一 `rg`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f;momentum/Analysis/contracts/split_unify.json#5aaf5f8efa15;momentum/Analysis/contracts/event_import_contract.json#d52dc4f6ad39

[BLOCKING] 信心度=High。實作者若造新字面會違反 D-001 的封閉契約，若重用舊字面則無法從輸出辨識答案窗跨界與混側 purge，驗收的「具名字面」也無法寫成固定斷言。修法：在同一契約 SoT 登記明確 mixed-side reason 並同步 Python/測試/前端，或明確規定重用舊字面且補充 reason 不分流。可行性證據是現有 `_PURGE_REASON` 與 import-time membership check 已有可沿用的契約接線。

## CODEX-R2-P1-03

**斷言**: D-002-C6 把所有 `n_train`／`n_test`／`n_purged` 都定成事件數不成立；既有 `baseline` 的 `n_test` 是實際模型輸入樣本數，Task 9.3 又要求上游物化改成 `(event_id, feature_timeframe)`。

**碼證**: `momentum/Analysis/event_samples/baseline.py:105-120` 以 assignments 的 test event IDs 與 `features_at_decision` 做 intersection，並以 `len(idx)` 寫入 report `n_test`；`docs/SPLITUNIFY_SPEC.D-002.md:88-92` 卻宣稱既有消費者全部事件語意，`docs/SPLITUNIFY_SPEC.D-002.md:150,153` 要求物化改為 feature-TF 粒度但未定 baseline 報告的 row/sample 語意。RECHECK：讀上述 baseline 行，構造 1 event×2 feature TF 的輸入，確認 `n_test` 必須區分 event count 與 model-row count，而非共用裸鍵。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。若照 C6 把 baseline 的 `n_test` 改成 distinct event count，報告會低報實際餵給 AUC/PR-AUC 的列數；若維持 row count，又違反 C6，且 MultiIndex 與目前 `Index.intersection` 的相容性未定。修法：把 C6 限定在 `EventSplitPlan.summary`／事件批面板，另明定 baseline 的 `n_test_rows` 或每 feature TF 的報告粒度，並配一個 1 event×2 TF 的數值守恆測試。可行性證據是 baseline 已在 `report` 建立計數欄，可局部改名與補測，不需改統計算法。

## CODEX-R2-P1-04

**斷言**: Phase 9B 沒有要求 producer 停止 `selected_timeframe` 單選並產生全量 `(event_id, feature_timeframe)` keyed rows；只加 output 欄位會讓 SU-RESID-2 仍被靜默丟棄。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:133-146` 只把 `discarded` 與 selected TF 放在 9A，9B 只說 assignments/purged/clusters 加欄；`docs/SPLITUNIFY_SPEC.D-002.md:74` 仍把 `build_event_keys` 描述成「選定 feature TF 後」一事件一列。現行 `momentum/Analysis/event_samples/split_projection.py:256-303` 在 `:279` 過濾 selected TF、在 `:291-292` 使用 `validate="1:1"`；既有 `tests/momentum/Analysis/test_splitunify_derive.py:933-942` 也固定「只取 selected」。VERIFY：`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'build_event_keys_picks_selected_timeframe_only'` → `1 passed, 77 deselected`、rc=0。RECHECK：重跑測試並讀 `:279-303`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/split_projection.py#99bfddace904;tests/momentum/Analysis/test_splitunify_derive.py#cbcd20a668e3

[BLOCKING] 信心度=High。實作者可照 9A 做完 `discarded`、照 9B 加欄與 uniqueness assertion，卻仍只輸出 selected TF，形成假綠的複合鍵支援。修法：在 9B 明定 producer 的全量返回 shape、`feature_timeframe` 欄與缺 cutoff/重複的 per-TF 行為，並把現有 selected-only 測試限定為 9A 回歸、增加雙 TF 輸出列數與值守恆測試。可行性證據是現有 helper 已以 `per_tf` DataFrame 作 keyed merge，只需把 selected 分支的契約與 caller 一起明定。

## CODEX-R2-P1-05

**斷言**: Task 9.2 對 `clusters` 的粒度與 C5/既有實作互斥，未定義 feature-TF 複製後的 cluster weight、count 與 golden 語意。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:74` 說 `build_time_clusters` 是一 manifest 列對一 event_id 列；`:144-146` 又要求 clusters 增加 `feature_timeframe`；`:150-155` 同時要求 cluster 仍按事件級 interval、同事件多 TF 同簇。現行 `momentum/Analysis/event_samples/event_split.py:59-74` 函式只收 manifest/bucket，依 event-level `decision_at_ms` 產一列並以 event rows 算權重；`tests/momentum/Analysis/test_splitunify_derive.py:541-569` 對該 event-level frozen oracle 逐值驗證。RECHECK：重跑上述行號，並對 1 event×2 TF 比較「複製兩列」與「維持一列」兩種 `cluster_weight` 結果。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/event_split.py#943d0721b059;tests/momentum/Analysis/test_splitunify_derive.py#cbcd20a668e3

[BLOCKING] 信心度=High。若複製 cluster rows，`n_time_clusters` 可能不變但權重總和與 golden row count 會改；若維持一列，又違反 Task 9.2 的三表加欄要求。修法：明定 clusters 是 event-level parent table 並不加 feature_timeframe，或讓函式接收 per-TF rows 並明定聚合/權重仍以 event 粒度計算，再更新 oracle。可行性證據是現行函式與 oracle 已把 event-level 粒度和權重公式集中在單一位置。

## CODEX-R2-P1-06

**斷言**: 18 條 mutation 仍不可作為逐處自證目錄：文件只列 `M-SU-D2-` 前綴加序號，未列完整 ID 或每條應紅測試，且 C5 明列的 `ic_feed.event_context_from_windows` survivor hash 沒有對應 mutation。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:173-182` 的條目只有 `01`～`18`，最後才泛稱「每條須指名應紅之測試」；`docs/SPLITUNIFY_SPEC.D-002.md:78` 明列 survivor 六鍵 hash；`momentum/Analysis/event_samples/ic_feed.py:43-74` 實際以排序後 event_id/label window 算 hash。VERIFY：`rg -n 'M-SU-D2-[0-9]{2}' docs tests momentum api frontend scripts --glob '!*.pyc'` → `0`；`rg -n 'M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` → 只見前綴與序號。RECHECK：重跑兩個 `rg`，再對照 C5 每一處與 mutation 表。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/ic_feed.py#741f697b3964;tests/momentum/Analysis/test_splitunify_derive.py#cbcd20a668e3

[BLOCKING] 信心度=High。這正是 `CODEX-R1-P1-06` 未閉合：Agent 無法由規格知道 mutation 的完整 selector、應紅 nodeid 或 survivor hash 是否已覆蓋，做完六個/十八個形狀變更仍可假綠。修法：逐條寫完整 `M-SU-D2-01`～`18`、具名測試 nodeid 與預期 rc=1，另補 survivor hash、baseline/count、cluster/producer 等 C5 未覆蓋面；每條先跑 baseline 再跑 mutant。可行性證據是現有 `test_splitunify_derive.py`、wiring、golden 與 API 測試路徑已存在，可承接具名 nodeid。

## CODEX-R2-P2-07

**斷言**: C0 的語意名稱已清楚，但「全檔與實作不得用裸 `timeframe`」與「`receipts.per_tf` 不改形狀」沒有說明既有 wire 欄位是否保留或只在邊界 alias，留下會破壞 schema 的實作分歧。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:28-36` 同時下全檔禁用與引用 `canonical_event_id(..., timeframe, ...)`、`per_tf.timeframe`；`:145` 又規定 `receipts.per_tf` 不改形狀。現行 `momentum/Analysis/event_samples/alignment.py:40` 的 `_PER_TF_COLS` 仍是 `timeframe`，`split_projection.py:279-301` 也讀該欄。RECHECK：重跑 `rg -n 'timeframe|trigger_timeframe|feature_timeframe' docs/SPLITUNIFY_SPEC.D-002.md momentum/Analysis/event_samples/alignment.py momentum/Analysis/event_samples/split_projection.py`，確認既有欄位與新欄位的邊界。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/alignment.py#0da3c48b2668;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[MAJOR] 信心度=High。若全量 rename，會改動既有 receipts wire shape；若不 rename，則「全檔禁裸名」無法 literal 達成。修法：明定 legacy `per_tf["timeframe"]`／event-level `timeframe` 的保留與轉換邊界，新增欄只用 `trigger_timeframe`／`feature_timeframe`，並補 schema round-trip 測試。可行性證據是目前欄位集中在 alignment 常數與 projection merge，可局部定義 alias，不需重寫資料模型。

## CODEX-R2-P1-08

**斷言**: 修訂版的觸及面宣告列出不存在的 `D-002-C1`／`D-002-C2`，且現行義務結構閘對此 SPEC rc=1；因此 `doc_format_precheck`/xref 通過不能代表規格可進下一道治理關卡。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:15-20` 宣告新增 C0/C1/C2/C3，但 `rg -n '^##?#+ D-002-C[12]|D-002-C[12]' docs/SPLITUNIFY_SPEC.D-002.md` 只命中宣告行，沒有 C1/C2 heading/obligation block。VERIFY：`bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → `OBLIGATION_RC=1`，並報告 24/28/30/32/34/36/40/44/46/48/50/58/60/62/64/72/74/76/78/80/88/90/92 等義務行型或裁決編號不合規；先前實跑 `doc_format_precheck` rc=0、`spec_xref_check --synth` rc=0。RECHECK：重跑 obligation check 與 C1/C2 `rg`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;scripts/obligation_block_check.sh#90737c0c0d7b;scripts/completeness_check.sh#c76692e041da

[BLOCKING] 信心度=High。治理流程若只看 brief 所列兩個 rc=0 會放過一份下一道白名單閘明確拒收的 SPEC；同時 C1/C2 的虛假 touchpoint 會讓審查與實作者無法定位複合鍵/揭露義務。修法：刪除或補齊 C1/C2 的正式 obligation block，並依閘的現行行型/歷史專區規則整理正文；修後重跑三個檢查。可行性證據是閘輸出已逐行指名違規類型與位置，修補範圍可被固定命令驗收。

Verdict：仍需修補後再審。主動攻擊面包括：合法異側 cutoff、reason 封閉集合、baseline sample denominator、producer selected-only、cluster 粒度/權重、18 mutation 逐處覆蓋、legacy timeframe wire name、治理閘與 touchpoint declaration；未發現新增 OOM、cache 或 quant 計算式問題。

VERDICT: blocked
BLOCKED-BY: CODEX-R2-P1-01,CODEX-R2-P1-02,CODEX-R2-P1-03,CODEX-R2-P1-04,CODEX-R2-P1-05,CODEX-R2-P1-06,CODEX-R2-P1-08
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04,CODEX-R1-P2-05
STATUS: DONE
