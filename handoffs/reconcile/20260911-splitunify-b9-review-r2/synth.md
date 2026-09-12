# Reconcile — 20260911-splitunify-b9-review-r2

**來源** 20260911-splitunify-b9-review-r2-codex.md, 20260911-splitunify-b9-review-r2-composer.md, 20260911-splitunify-b9-review-r2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

🔴 R1 之閉合狀況：**composer 三條全閉並 `proceed`**；**grok 六條全閉**但新開兩條 P1；
**codex 閉合五條**（`R1-P1-01`～`04`、`R1-P2-05`），惟 `CODEX-R1-P1-06`（mutation 目錄）
**仍未閉**並續列於其 `BLOCKED-BY`。本輪新開 11 條，歸九群，**全部採納**。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| 同側約束會誤 purge 合法事件——「D-002-C3 會把目前資料契約允許的合法多 feature TF 事件誤 purge」 | P1 | CODEX-R2-P1-01 | 採納（🔴 **我在 R2 brief 裡把「同側約束不會誤殺」列為 assumed 並請他們攻，他們攻成功了**：資料契約只要求各 cutoff `<= decision_at_ms`，並未要求不同 feature TF 之 cutoff 相同或錨定同一事件時間 ⇒ 合法事件可能天然落在不同側。修訂：C3 須先定義「何謂同一事件之可比時點」，再談同側；或改為「異側時以 trigger TF 之側為準並揭露」，不得一律 purge） |
| 混側 purge 之具名字面無唯一真相源——「C3 要求混側 purge 使用「具名字面」，但 D-001 與現行契約只允許既有 `interval_crosses_split_boundary`」 | P1 | CODEX-R2-P1-02 | 採納（我寫了「須為具名字面」卻沒指定是哪個字面、也沒說要不要新增進封閉值集。修訂：指定既有字面或明確新增並指出其單一真相源檔） |
| 三量一律定為事件數不成立——「D-002-C6 把所有 `n_train`／`n_test`／`n_purged` 都定成事件數不成立」 | P1 | CODEX-R2-P1-03 | 採納（`baseline` 的 `n_test` 語意是**實際模型輸入樣本數**，而 Task 9.3 又要把上游物化改成 `(event_id, feature_timeframe)` ⇒ 一律定為事件數會與該消費者衝突。修訂：逐消費者定義各自需要的粒度，不得一刀切） |
| 9B 未要求 producer 停止單選，核心目標未達成——「Phase 9B 沒有要求 producer 停止 `selected_timeframe` 單選並產生全量 `(event_id, feature_timeframe)` keyed rows」 | P1 | CODEX-R2-P1-04 | 採納（🔴 **最嚴重**：我只加了 schema 欄位與下游改法，卻沒寫「producer 必須停止單選、輸出全量 keyed rows」⇒ `SU-RESID-2` 的丟棄行為原封不動，整個第 9 批的目標不會達成。修訂：9B 首要 Task 改為 producer 側之單選解除） |
| clusters 粒度自相衝突且語意未定義——「Task 9.2 對 `clusters` 的粒度與 C5/既有實作互斥，未定義 feature-TF 複製後的 cluster weight、count 與 golden 語意」／「Task 9.2「assignments／purged／**clusters** 三表各加 `feature_timeframe`」與 Task 9.3「時間簇仍按**事件級** interval 合併」」 | P1 | CODEX-R2-P1-05, GROK-R2-P1-02 | 採納（兩家各自指出同一處矛盾：我要 clusters 加 `feature_timeframe`，又說簇按事件級合併、同事件多 TF 同簇——照字面做會把簇複製成多列，weight（`w=1/n`）、count 與 golden 語意全部未定義。修訂：clusters **不加**該欄、維持事件級，或明確定義複製後的權重與計數規則，二選一並寫死） |
| mutation 目錄不可作為逐處自證——「18 條 mutation 仍不可作為逐處自證目錄：文件只列 `M-SU-D2-` 前綴加序號，未列完整 ID 或每條應紅測試」 | P1 | CODEX-R2-P1-06 | 採納（兼閉 `CODEX-R1-P1-06`。我只寫了序號與一句改壞什麼，沒有完整 ID、沒有逐條「應紅之測試」欄，且 C5 明列的 `ic_feed.event_context_from_windows` survivor hash 沒有對應 mutation。修訂：改為表格，每列＝完整 ID／改壞什麼／應紅之測試，並補 survivor hash 那條） |
| `timeframe` 命名義務與新欄名互斥——「C0 的語意名稱已清楚，但「全檔與實作不得用裸 `timeframe`」與「`receipts.per_tf` 不改形狀」沒有說明既有 wire 欄位是否保留」／「Task 9.1 規定的新 summary 鍵 `discarded_per_tf_rows_by_timeframe` 含裸 `timeframe`，與同檔 `D-002-C0` (0.5)…互斥」 | P1 | CODEX-R2-P2-07, GROK-R2-P1-01 | 採納（🔴 **規格自我矛盾**：我在 (0.5) 禁用裸 `timeframe` 當新欄名，自己卻在 Task 9.1 定了 `discarded_per_tf_rows_by_timeframe` 這個新鍵；且未說明既有 wire 欄位（`per_tf.timeframe`）是保留還是只在邊界 alias。修訂：(0.5) 明確區分「既有欄位保留」與「新增欄位須分名」，並把該新鍵改名） |
| 觸及面列出不存在的章節、義務結構閘未過——「修訂版的觸及面宣告列出不存在的 `D-002-C1`／`D-002-C2`，且現行義務結構閘對此 SPEC rc=1」 | P1 | CODEX-R2-P1-08 | 採納（**已於本輪修畢**：觸及面宣告改列實際存在之 `C0`／`C3`／`C4`／`C5`／`C6`；21 條義務項行型改為白名單形狀、5 處裁決編號移出正文。🔴 主委自評：那道閘是我自己建的，這次卻只跑了格式與 xref **沒跑它**——`obligation_block_check.sh` 現為 rc=0） |
| 逐項核對後無新 finding——「本輪逐項核對後無新 finding——R1 三條均已閉合，且對 C0／C3／C6／Task 9.4 四塊之主動攻擊未構造出可證偽缺陷」 | P3 | COMPOSER-R2-P3-00 | 採納（sentinel；其 R1 三條全數閉合） |

## 主委自評（如實記）

本輪 codex 與 grok 仍 `blocked`，新開 11 條**全部採納、零駁回**。其中三條是我**自己造成的自相矛盾**：
①(0.5) 禁裸 `timeframe` 卻自己定了含它的新鍵；②要 clusters 加欄又要它維持事件級；
③觸及面列出自己已經刪掉的章節。另有一條是**核心目標漏寫**——9B 沒要求 producer 停止單選，
等於整批做完 `SU-RESID-2` 仍未解決。還有一條是我在 brief 裡自陳為 assumed 的同側約束，**被攻破**。

## 交件格式正規化（透明度）

codex 之 R2 裁決塊將**跨輪**的 `CODEX-R1-P1-06` 列入 `BLOCKED-BY`，而契約要求該欄只引用
**本檔**開過的 ID ⇒ `register-output` 拒收。主委依契約移除該跨輪 ID，**語意未流失**：
該條內容仍在 R1 交件檔內，且本輪新開之 `CODEX-R2-P1-06` 實質涵蓋同一問題（本表已註明兼閉）。
🔴 同型問題在 R1 曾發生一次（另一家把他家 ID 填入 `CLOSED`），根因是**主委 brief 的格式範例未分家族／未說明跨輪 ID 的處理**；
R3 brief 須補明「`BLOCKED-BY` 與 `CLOSED` 皆只列本檔本家族之 ID，跨輪未閉條目以新 ID 重開或於正文敘述」。

## 誠實邊界

D-002 為規格階段產物，本輪無實作、無數值影響。IC 端到端真實 run 仍未跑。

Verdict: 需修補後合併（D-002 依本收斂九群修訂後重審；codex 與 grok 之 blocked 於修訂版通過後解除）

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
BLOCKED-BY: CODEX-R1-P1-06,CODEX-R2-P1-01,CODEX-R2-P1-02,CODEX-R2-P1-03,CODEX-R2-P1-04,CODEX-R2-P1-05,CODEX-R2-P1-06,CODEX-R2-P1-08
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04,CODEX-R1-P2-05
STATUS: DONE
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無新 finding——R1 三條均已閉合，且對 C0／C3／C6／Task 9.4 四塊之主動攻擊未構造出可證偽缺陷。

**碼證**: ①R1 閉合對照 `D-002-C5` (5.5)、`D-002-C6`、`Task 9.4`、`Task 9.1` L133-137、§V L173-181 ②C3 異側反例 `split_projection.py:530-553`＋`feature_materialization.py:93-130` ③C6 消費者 `pipeline.py:760-762`、`test_splitunify_disclosure.py:282-300`、`baseline.py:120` ④C0 `rg '\btimeframe\b' docs/SPLITUNIFY_SPEC.D-002.md` → 6 行皆為引用／規則 ⑤新義務交叉讀 `D-002-C0`／`C3`／`C6`／`Task 9.4` 與 `D-002-C4` (4.4)。RECHECK: 重讀上述章節＋五處碼證行號。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5

P3；信心度=High。本輪依 brief 七群落點逐段對照修訂版 SPEC，並以現行碼（`pipeline.py:760-762`、`test_splitunify_wiring.py:103-113`、`ic_feed.py:115,142-145`、`baseline.py:120`、`test_splitunify_disclosure.py:282-300`）驗證必答 2–4。主動攻擊面含：記帳鏈閉合性、mutation 表完整性、C3 過嚴、C6 消費者列數需求、C0 殘留歧義、新義務塊互斥——均未得到需阻擋實作的 P0/P1。

## GROK-R2-P1-01

**斷言**: Task 9.1 規定的新 summary 鍵 `discarded_per_tf_rows_by_timeframe` 含裸 `timeframe`，與同檔 `D-002-C0` (0.5)「實作新增之欄位名須逐字採用 trigger_timeframe／feature_timeframe、禁用裸 timeframe 當新欄名」互斥；實作者無法同時滿足兩條義務。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md` L36＝(0.5) 禁令；L136＝Task 9.1 強制鍵名 `EventSplitPlan.summary["discarded_per_tf_rows_by_timeframe"]`；L133–134 雖正確寫 discarded 之 dict 鍵為 `feature_timeframe`，但 summary 鍵本身仍裸用 `timeframe`。RECHECK: `grep -n 'by_timeframe\|禁用裸' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5

[BLOCKING] 信心度=High。驗收時一邊要求「鍵名逐字＝Task 9.1」、一邊要求「新欄名合 C0」⇒ 必有一條紅或假綠（改名則 9.1 斷言紅；不改名則 C0 違規）。**修法**：將 summary／API／前端鍵**統一**改為不含裸 `timeframe` 之名，例如 `discarded_per_tf_rows_by_feature_timeframe`（或更短但須含 `feature_timeframe` 字面）；同步 §V ASSERT 與 mutation `01`–`03` 的鍵名。**可行性**：此鍵尚未落地（全 repo 僅 SPEC 出現）；改名零遷移成本，只改 SPEC 字面與後續實作契約。

---

## GROK-R2-P1-02

**斷言**: Task 9.2「assignments／purged／**clusters** 三表各加 `feature_timeframe`」與 Task 9.3「時間簇仍按**事件級** interval 合併、同事件多 feature TF 同簇」及既有 `clusters.set_index("event_id")` 消費者互相衝突——照 Task 9.2 字面做會破壞簇表事件級唯一性或留下無定義欄。

**碼證**: SPEC L145「三表各加 `feature_timeframe`」；L156「時間簇仍按事件級 interval 合併」；`event_split.build_time_clusters`（`event_split.py:59-75`）一 manifest 列→一 `event_id` 列、無 feature TF 維；`tables.py:229`／`:373` 對 `clusters` 做 `set_index("event_id")` 後 `.loc`／`reindex`（預設事件唯一）。若為加欄而把 clusters **展開**成 `(event_id, feature_timeframe)`，`set_index("event_id")` 變非唯一→與本 epic 要消的靜默類同構；若**不展開**只加一欄，多 feature TF 事件該填哪個值無定義。RECHECK: 讀 Task 9.2／9.3 兩句＋`tables.py:229,373`＋`build_time_clusters` 回傳欄。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5;momentum/Analysis/event_samples/tables.py#843ba7f68172;momentum/Analysis/event_samples/event_split.py#943d0721b059

[BLOCKING] 信心度=High。不改則 Task 9.2 實作時二選一皆錯：要嘛弄破 `tables`／discrimination 的簇索引，要嘛寫入無語意的 `feature_timeframe` 佔位。**修法**：Task 9.2 改為「`assignments`／`purged` 加 `feature_timeframe`；**`clusters` 維持事件級、不加該欄**」（與 Task 9.3 同簇句、C5 (5.2)、mutation `18` 之「勿過度涵蓋 event-level」一致）。若未來要 per-TF 重述簇列，須另開任務並改所有 `set_index("event_id")` 消費者，不在本句偷渡。**可行性**：`build_time_clusters` 今日即無 TF 欄；從 Task 9.2 刪除 clusters 即可，零碼阻礙。

---

