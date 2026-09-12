# Reconcile — 20260911-splitunify-b9-review-r5

**來源** 20260911-splitunify-b9-review-r5-codex.md, 20260911-splitunify-b9-review-r5-composer.md, 20260911-splitunify-b9-review-r5-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **H1 核心目標第四種不可達形態：producer 內部 merge 與輸出 TF 欄**——「第五次修訂宣稱`Task9.2`＋`9.」「第五次修訂宣稱Task9.2／9.2a／」：`build_event_keys` 之 `event_level.merge(..., validate="1:1")` 在全量多 TF 必 MergeError；且輸出 `timeframe` 取自 event_level（觸發 TF），merge 只帶 feature_cutoff_ms | P1 | COMPOSER-R5-P1-01, GROK-R5-P1-01 | 採納（`Task 9.2` 改法增逐行指名 `split_projection.py:291-303`：改以 `per_tf` 為行粒度接合、`validate` 改複合鍵判準、輸出欄新建 `feature_timeframe` 取自 `per_tf` 而非冒充 `event_level` 之觸發 TF；`(5.2)` 之交叉引用由 `Task 9.2a` 改指 `Task 9.2`；主委已自驗該 merge 與輸出欄逐字如指控） |
| **H2 (3.2) 有義務無施工落點**——「`(3.2)`要求投影端對異側擲`Ali」：`AlignmentViolationError` 只出現在義務與驗收與 mutation，任一 Task 改法均未指名在何處插入同側檢查 | P1 | GROK-R5-P1-02 | 採納（`Task 9.2b` 增改法條：於複合鍵唯一 guard 之後、寫入 `assignments` 之前，按 `event_id` 分組檢查 `split_label` 唯一，異側即 raise 且訊息含 event_id，指名 `_derive_single_symbol`；主委已自驗該符號在本 SPEC 僅出現於義務與 §V 與 mutation，無改法行） |
| **H3 mutation 目錄自相矛盾且缺第四層**——「SPEC§Vmutation目錄宣稱「共」「mutation目錄23條未覆蓋**`b」「SPEC宣稱mutation共23條但表」：宣稱 23 實列 22，且無一條抓 producer 內部 merge | P1 | GROK-R5-P1-03, COMPOSER-R5-P1-02, CODEX-R5-P1-04 | 採納（正文與沿革之條數改為實數；新增 `M-SU-D2-23` 抓 merge 與 `feature_timeframe` 產出欄、`M-SU-D2-24` 抓答案窗仍用逐列 in_train、`M-SU-D2-25` 抓 `D-002-C3` 同側檢查早於複合鍵 guard；主委已自驗表列實為 22 且沿革算術為 20+2） |
| **H4 Task 9.4 未排除 baseline 例外**——「Task9.4的廣義「n_train／n」：C6 明定 baseline 之 n_test 為模型輸入樣本數，9.4 的廣義事件數會誤報 | P1 | CODEX-R5-P1-01 | 採納（`Task 9.4` 明列 `baseline` 為例外並與 `n_event_tf_rows` 分名，配一事件兩列之 fixture） |
| **H5 Task 9.1 之終端揭露在現行生產 route 不可達**——「Task9.1要求discarded到API」：現行 service 永遠走 event-study-only，拿不到 canonical universe 也無 discarded 來源 | P1 | CODEX-R5-P1-02 | 採納（`Task 9.1` 須明定 API 改走何一可取得 universe 之 producer，或把終端揭露自事件掃描端移出；此為主委前一版「逐處指名落點」時未查生產可達性之缺口） |
| **H6 9.2b 未定義 decision_at 如何映射邊界**——「9.2b雖定`decision_at_ms`」：跨 TF 合法時刻可不在同一網格（實證 1h open 非 4h open 15,264/20,352），側別未定 | P1 | CODEX-R5-P1-03 | 採納（`Task 9.2b` 須寫死 `decision_at_ms` 相對 test 邊界之側別判準與越界處置，**不得**僅依集合成員；主委探針二只驗 12h 觸發配 12h 與 4h 特徵（整數倍必命中），本條正確限縮該結論——特徵網格較粗於觸發 TF 時會落空，須配 fail-closed） |
| **H7 端到端斷言標的未指定且物化仍折疊**——「9.2的「產出列數」未指定`res.sp」：未指定 assignments 或 features；物化仍 groupby event_id 折疊；既有 wiring 測試仍把 None 視為必須 raise | P1 | CODEX-R5-P1-05 | 採納（§V 之 `Task 9.2` 端到端斷言明指 `assignments` 列數，另以 `Task 9.3` 覆蓋 `feature_materialization` 之複合鍵值守恆；並明列既有 wiring 之 partial-boundary 參數化案例須**替換**而非另加） |
| **H8 TODO 狀態同步債尚未清**——「`SU-RESID-2`TODO狀態尚未」：治理檔仍可被實作者讀成 selected-only | P2 | CODEX-R5-P2-01 | 採納（維持 §N 既定時點：三家戳記後、`Task 9.1` 動工前同步；本條為落地前之債，非本輪 blocker） |

**Verdict**: 需修補後合併

**本輪主委自評**

1. **核心目標第四次以不同形態沒補到**：只加欄位 → 沒改 caller → caller 前有四參數閘 → **閘後還有 producer 內部的 merge 與輸出欄**。三家這次獨立撞到同一層。前三次我都只補「被指出的那一層」，這次連「端到端驗收」都寫進去了仍漏——因為我把「端到端」寫成一句斷言，卻沒有自己走完那條路。
2. **我的探針結論被 codex 正確限縮**：探針二只覆蓋「特徵網格為觸發 TF 之整數倍」的情形，我卻寫成一般結論。
3. **`Task 9.1` 的落點是我查了行號卻沒查可達性**：指名了 route 與 service 與前端行號，但那條 route 的 service 永遠走 event-study-only，根本拿不到 universe。**指名落點 ≠ 該落點走得到**。

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R5-P1-01
**斷言**：Task 9.4 的廣義「n_train／n_test／n_purged＝事件數」未排除 C6 明定的 baseline `n_test`＝模型輸入樣本數；多 TF 後會有 1 event×2 rows 的誤報風險。**碼證**：SPEC:90-94,181-183；`baseline.py:105-120` 以 test event IDs 與 features 交集後寫 `n_test`。
**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e；修補須在 Task 9.4 明列 baseline 例外、event count 與 `n_event_tf_rows_*` 分名並補 1×2 fixture。
## CODEX-R5-P1-02
**斷言**：Task 9.1 要求 discarded 到 API/前端，但現行 production route 的 service 永遠走 event-study-only，拿不到 canonical universe、也沒有 `build_event_keys` 的 discarded 來源；僅列檔案路徑不足以使 9A 可驗收。**碼證**：`case_import_service.py:1592-1609,1620-1626`；response 只有寬 summary，面板在 unavailable 時不顯示 split rows (`event_import_models.py:306-318`; `EventTablesPanel.tsx:347-379`)。
**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e；需明定 API 改走何一可取得 universe 的 producer，或把 9A 終端揭露從事件掃描端移出。
## CODEX-R5-P1-03
**斷言**：9.2b 雖定 `decision_at_ms`，未定義如何映射 train/test plan；若照現行「feature_index 集合成員」語意，跨 TF 合法時間可不在同一網格（實證 1h open 非 4h open 15,264/20,352），側別會未定。按事件側 purge 的差異亦未被 mutation 捕捉。**碼證**：`alignment.py:197-213` 各 TF as-of；`split_preview.py:275-280` 禁 ms 回流；現行 `split_projection.py:530-553` 仍以 cutoff/in_train purge。
**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e；須寫死 `decision_at_ms` 相對 test boundary 的 side、邊界/越界處置，並驗 train-side crossing purge 所有 TF rows、test-side 不誤 purge。
## CODEX-R5-P1-04
**斷言**：SPEC 宣稱 mutation 共 23 條但表格實際只有 22 條（`rg ... | wc -l`＝22）；缺 `M-SU-D2-23`（保留 per-row `in_train` 的答案窗 purge）且第 24 條應是 `M-SU-D2-24`（C3 同側檢查先於 composite-key guard），兩者皆可在核心測試假綠。**碼證**：SPEC:160-164,166-170,196-200,214-225；purge 現況 `split_projection.py:539-553`。
**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e；補兩條完整 ID、各自反例與應紅測試後才可宣稱 23/24 覆蓋。
## CODEX-R5-P1-05
**斷言**：9.2 的「產出列數」未指定 `res.split_plan.assignments` 還是 `res.features`；`run` 在 assignments 後立即進入 `feature_materialization`，其 `groupby("event_id")`＋`row_vals.update` 仍折成一列/事件，且既有 wiring test 仍把 `selected_timeframe=None` 視為必須 raise。**碼證**：`pipeline.py:755-763`; `feature_materialization.py:93-132`; `test_splitunify_wiring.py:117-125`。
**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e；9.2 應分別指定 assignments e2e、物化複合鍵值守恆，並明列舊 partial-boundary 參數化案例的替換而非另加假綠測試。
## CODEX-R5-P2-01
**斷言**：`SU-RESID-2` TODO 狀態尚未實際同步；§N 只把同步排在三家戳記後、Task 9.1 前，故目前治理檔仍可被實作者讀成 selected-only。**碼證**：`docs/SPLITUNIFY_SPEC.D-002.md:231-238`；`docs/SPLITUNIFY_TODO.md:470` 仍為 needs-research 與舊理由。
**來源摘要**：docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e；docs/SPLITUNIFY_TODO.md#e44da6448b01；此為落地前同步債，不是本輪程式碼 blocker。
R3/R4 closure：R3 P1-01/02/03/04/06/08/09 由 C5、9.2/9.2a/9.2b、§V 與 probe 閉合；P1-05→本檔 P1-01、P1-07→P1-02、P2-02→本檔 P2-01；R3 P2-01 由 C0(0.6)閉合。Codex R4 僅為被駁回的 stamp 拒審，無實質 finding，故本輪補完整審查。
答覆#2：C5 第四層是記帳/報告鏈；run→assignments 實際關卡依序為 lookahead `assert_split_allowed`(pipeline:720)、`_prepare`(721)、四參數閘(727-733)、canonical embargo 閘(739-744)、producer selected/empty/duplicate/missing-cutoff(279-299)、projection 欠欄/索引同源/重複 event guard(366-522)，最後才是 cutoff-side/purge(530-553)；assignments 後物化仍有 event_id 折疊(93-132)。
答覆#3：事件側為 train 且答案窗跨 test boundary 時，新語意 purge 該 event 的全部 feature-TF rows；事件側為 test 時不因某一 cutoff 落 train 而 purge。現行 540-542 只看 `in_train`，544-553 可把另一 TF 留在 assignments，故差異是可觀察且非單純 schema。
答覆#4：若先上 C3.2 raise，尚未 9.2b 的合法 mixed-cutoff 事件會被現行 per-cutoff 判側製成異側並 raise；SPEC 9.2b:167-170 文字上要求先改 decision_at、再讓 C3 fail-closed，9.2a:160-163 也要求 key guard 先於 C3，但未提供不可部分上線的機械 gate。
答覆#5：第五版 (5.2) 與 9.2/9.2a/9.2b 已一致；新問題即本檔 P1-01～05、P2-01。與 D-001 的 per-symbol index/legacy receipts 不衝突，但 side mapping 必須保留其同源與欄位邊界；與 C6 的直接衝突是 baseline 粒度。
VERDICT: blocked
BLOCKED-BY: CODEX-R5-P1-01,CODEX-R5-P1-02,CODEX-R5-P1-03,CODEX-R5-P1-04,CODEX-R5-P1-05
CLOSED:
ASSUMPTIONS_VERIFIED: 以真實 probe、現行 run/projection/materialization/API/test 路徑逐項核對；R3 closure 狀態如上。
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（A/C 各 2 列且只 1h，B/D 依舊 raise）；`venv/bin/pytest -q tests/momentum/event_samples/test_splitunify_wiring.py --tb=short` 9 passed；obligation rc=0；r1-r4 xref 各 rc=0。
FAILURES_SEEN: 初次 xref 誤用 5 參數、一次 fixture helper 名稱誤讀；均未改檔，後以正確命令完成查證。 SCOPE_CHANGES: 只新增本交接檔；OUTPUT: handoffs/20260911-splitunify-b9-review-r5-codex.md。 NUMERIC_OR_SCHEMA_IMPACT: 未改程式、SPEC、資料或輸出。
STATUS: DONE
## COMPOSER-R5-P1-01

**斷言**: 第五次修訂宣稱 `Task 9.2`＋`9.2a`＋`9.2b` 到位即可達全量路徑，但 **`build_event_keys` 內部 `event_level.merge(..., validate="1:1")`（`:291-292`）與輸出欄取自 `event_level.timeframe`（`:300-302`，trigger TF）仍未被任何 Task「改法」逐行指派**；`(5.2)` L76 將 merge 改判準 cross-ref 至 `Task 9.2a`，而 9.2a 改法僅列 `assignments`／`purged` schema 與 `:284-289`／`:441-444` guard——**不含 `:291-303`**。

**碼證**: `split_projection.py:291-303` 現行 `validate="1:1"` on `event_id`；merge 子集僅 `["event_id","feature_cutoff_ms"]`，輸出 `timeframe` 來自 `event_level`（`alignment.py:216` trigger TF），非 `per_tf.timeframe`（feature TF，`alignment.py:210`）。探針 Case C：`venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` → 仍只產 2 列。RECHECK: `sed -n '291,303p' split_projection.py`＋對照 `Task 9.2` L153、`Task 9.2a` L156-163、`(5.2)` L76。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e;momentum/Analysis/event_samples/split_projection.py#99bfddace904;momentum/Analysis/event_samples/alignment.py#e3b1c9a02f1d

[BLOCKING] 信心度=High。Agent 完成 Task 9.2 caller／四參數閘與 9.2a guard 後，在 G4 仍 `validate` fail-closed，或 G5 產出兩列相同 trigger `timeframe` 而 `(event_id, feature_timeframe)` 鍵碰撞／靜默覆蓋——**SU-RESID-2 第四次以不同形態復活**。**修法**：`Task 9.2` 改法增逐行：`build_event_keys:291-303` 改為以 `per_tf` 為行粒度 join `event_level`（複合鍵 `validate`）、輸出欄含 `per_tf.timeframe` 並依 `D-002-C0` (0.3) 命名 `feature_timeframe`；修正 `(5.2)` L76 cross-ref 指向 `Task 9.2` 而非 9.2a；§V 增一條 `build_event_keys` 輸出列數＝`per_tf` 列數 ASSERT。**可行性**：單函式局部重寫，不動切分數學。

## COMPOSER-R5-P1-02

**斷言**: mutation 目錄 23 條未覆蓋 **`build_event_keys:291-292` 仍保留 event-level `validate="1:1"`** 之缺陷——`M-SU-D2-20`／`21` 抓 caller／閘，`M-SU-D2-22` 抓判側迴圈，**無一條**抓 producer 內部 merge 路徑；Agent 可讓端到端測試 mock 全量列數而 merge 仍在單事件多 TF 時 fail-closed。

**碼證**: §V mutation 表 L202-225 共 23 行 ID；`rg 'validate.*1:1' momentum/Analysis/event_samples/split_projection.py` → L292。`M-SU-D2-20` 應紅測試＝端到端列數（L223），**不會**在僅改 caller、未改 merge 時紅（G4 在 `build_event_keys` 內先炸）。RECHECK: 對照表 L202-225＋`sed -n '291,292p' split_projection.py`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。缺少第 24 條 mutation ⇒ 回歸測試無法機械擋下 G4 復活。**修法**：新增 `M-SU-D2-24`｜`build_event_keys` 保留 `event_level.merge(..., validate="1:1")`｜`Task 9.2` 之 `per_tf` 列數＝輸出列數 ASSERT（或單元測試直接餵 2-TF receipts 期望 4 列輸出）。

## GROK-R5-P1-01

**斷言**: 第五次修訂宣稱 Task 9.2／9.2a／9.2b 到位後全量路徑可達，但 `build_event_keys` 的 `event_level.merge(..., validate="1:1")`（`split_projection.py:291-293`）在全量多 feature TF 時必 `MergeError`；且 merge 未納入 `per_tf.timeframe` 為 `feature_timeframe`（輸出 `timeframe` 來自 `event_level`＝trigger TF）。`(5.2)` 把 merge 改判準掛在 Task 9.2a，但 Task 9.2a 正文未提及該 merge——核心目標第四種不可達形態。

**碼證**: VERIFY: 探針構造 2 event × 2 TF → `MergeError: Merge keys are not unique in right dataset`；`1:m` 後 `OUT_TIMEFRAMES=['1d']`（trigger）。`sed -n '279,303p' momentum/Analysis/event_samples/split_projection.py`。SPEC：`(5.2)` L76 含「merge validate…見 Task 9.2a」；Task 9.2a L156-164 無 `merge`／`validate`／`291`。RECHECK: 重跑 `/tmp/grok-splitunify-b9-review-r5/probe_summary.txt` 步驟＋對讀 L76 vs Task 9.2a。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。Agent 若只改四參數閘＋caller `None`＋Optional 過濾，進 `build_event_keys` 全量分支仍被 merge 擋死，§V 端到端全量 ASSERT 必紅或被繞去單選假綠。**修法**：在 `Task 9.2`（或 9.2a）具名 `split_projection.py:291-302`——(a) 全量時 merge 改 `validate="1:m"`（或先以 `(event_id, feature_timeframe)` 為鍵再與 event_level 接合）；(b) 自 `per_tf` 帶出 `timeframe` 並**新建**輸出欄 `feature_timeframe`（不得把 trigger 的 `event_level.timeframe` 冒充）；(c) 單選過濾路徑維持每事件一列時可續用 `1:1`。**可行性證據**：同探針 `PROPER_MERGE rows=4 ftf=['1h','4h']`（rename＋`1:m`）已跑通；不改切分數學、只改 keyed 表組裝。

## GROK-R5-P1-02

**斷言**: `(3.2)` 要求投影端對異側擲 `AlignmentViolationError`，且 Task 9.2a 以「同側檢查」為 guard 先後前提，但**任一 Task 之「改法」均未指名**在 `derive`／`_derive_single_symbol` 何處插入該檢查；義務／§V／mutation 有、施工單無——與 R4 之「(3.1) 有義務無落點」同型殘留。

**碼證**: `AlignmentViolationError` 僅出現於 SPEC L48（義務）、L195（§V）、L217-218（mutation 14／15）；Task 9.2／9.2a／9.2b 改法段無此符號、無「插入同側檢查」行。Task 9.2a L162 只寫複合鍵 guard「須在 D-002-C3 同側檢查**之前**執行」。RECHECK: `grep -n AlignmentViolation docs/SPLITUNIFY_SPEC.D-002.md`＋讀 Task 9.2a／9.2b 全文。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e

[BLOCKING] 信心度=High。實作者可做完 9.2b 廣播（結構性同側）而**永不寫** fail-closed 檢查 ⇒ `M-SU-D2-14`／`15` 與 §V 反例無碼可紅、回歸可把檢查整段刪掉而不被 Task 清單擋住。順序上 9.2b「不可做」與 §R「不得部分上線」有文字，但缺落點仍會讓「先上 raise」或「從未上 raise」兩種失敗。**修法**：在 `Task 9.2b`（或 9.2a）增改法條——於複合鍵唯一 guard 之後、寫入 `assignments` 之前，按 `event_id` 分組檢查 `split_label` 唯一，異側即 `raise AlignmentViolationError`（訊息須含 event_id）；指名函式 `_derive_single_symbol`（與現判側迴圈同檔）。**可行性**：`AlignmentViolationError` 已在專案他處使用（b8 adapter 路徑）；同檔已有 fail-closed raise 模式，只需加分組檢查，不改 purge reason 字面。

## GROK-R5-P1-03

**斷言**: SPEC §V mutation 目錄宣稱「共 23 條」，表格實列僅 `M-SU-D2-01`…`22`（22 條）；沿革「20→23（新增 21、22）」算術亦為 22；且對 P1-01 之 merge／`feature_timeframe` 產出欄**無**對位 mutation——宣稱覆蓋三 Task＋四參數閘為假。

**碼證**: `awk` 計數表列＝22；`grep M-SU-D2-23`＝0；L200 正文「共 23 條」；L247 沿革「20 → **23** 條（新增 `M-SU-D2-21`…`22`）」。RECHECK: 重跑表列計數＋對照 L200／L247。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#51f66eb84f8e

[BLOCKING] 信心度=High。機械／人工驗收若信「23」會以為目錄完整；缺 merge mutant 則 Agent 可保留 `validate="1:1"` 而端到端全量測試若被寫成只打 pipeline 閘＋schema，仍可能假綠。**修法**：①正文與沿革改為「共 22 條」或補 `M-SU-D2-23`；②新增 `M-SU-D2-23`＝「全量路徑仍保留 `merge validate='1:1'` 或不寫入 `feature_timeframe`」→ 應紅＝Task 9.2 端到端全量列數＋`feature_timeframe` 值斷言。**可行性**：純文檔＋一列 mutation；與既有 20→22 表格格式相同。

---

