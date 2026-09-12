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
TESTS_RUN: `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` rc=0（A/C 各 2 列且只 1h，B/D 依舊 raise）；`venv/bin/pytest -q tests/momentum/event_samples/test_splitunify_wiring.py --tb=short` 9 passed；obligation rc=0；r1-r4 xref 各 rc=0；completeness 命令被 PreToolUse gate 擋下，未取得 rc。
FAILURES_SEEN: 初次 xref 誤用 5 參數、一次 fixture helper 名稱誤讀，後已用正確命令完成；指定 completeness 尚未執行（`gate.sh dispatch` rc=1：本輪 review round OPEN）。 SCOPE_CHANGES: 只新增本交接檔；OUTPUT: handoffs/20260911-splitunify-b9-review-r5-codex.md。 NUMERIC_OR_SCHEMA_IMPACT: 未改程式、SPEC、資料或輸出。
STATUS: DONE
