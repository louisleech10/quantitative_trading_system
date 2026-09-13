# SPLITUNIFY b9 review-r14 — codex
範圍：只審 v13→v14 diff、指定 current block、TODO T2/T3；未改碼、SPEC 正文或 TODO。結論：3 個 P1 blocker；另記 1 個 P2 metric finding。
## CODEX-R14-P1-01
**斷言**: `M-SU-D2-35`/`36` 的應紅測試只依賴缺欄時 pandas `KeyError`，未強制欄位存在；`if "feature_timeframe" in df.columns` 可短路而不紅，且具名測試目前不存在。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:545
MUTATION: 刪除 assignments/purged row dict 的 `feature_timeframe` 後執行 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'assignments_composite_key_unique or purged_composite_key_unique'`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7455b305c6f3;docs/SPLITUNIFY_TODO.md#5738e9c63f6f `[MAJOR]` 信心度=High；實跑結果為 `78 deselected / 0 selected`, rc=5。一次修訂可直接把兩列應紅字面改成：`先 ASSERT "feature_timeframe" in assignments/purged.columns，再 ASSERT not duplicated(subset=["event_id","feature_timeframe"]).any()；刪欄或以 if "feature_timeframe" in df.columns 包住 guard 均須 fail`；先欄位斷言即可阻止短路，修法可行。
## CODEX-R14-P1-02
**斷言**: Task 9.3 新 receipt 閘仍接受 exact ID set、合法列格式但全列假填 `甲 -> 甲`，並接受未與 audit HEAD 綁定的任意 `COMMIT`。
**碼證**: CODE-ANCHOR: scripts/completeness_check.sh:350
MUTATION: 構造 `TASK: 20260911-SPLITUNIFY-B9-REVIEW-R14-IMPL`、`COMMIT: deadbeef`，C5-01..29 全寫 `甲 -> 甲 fake:1`，執行 TODO:632-640 的 exact-set diff 與 row-format grep。
**來源摘要**: docs/SPLITUNIFY_TODO.md#5738e9c63f6f `[MAJOR]` 信心度=High；實跑 `EXACT_ID_SET=PASS`、`ROW_FORMAT=PASS`、`COMMIT=deadbeef`。一次修訂可在 dispatch audit 記錄 round-start HEAD，驗收強制 `COMMIT` 等於該欄，並逐 ID 對證分類與現存 `path:line`；目前規範只驗 ID/值域/格式，未驗內容。
## CODEX-R14-P1-03
**斷言**: C5 register 有五列 mutation 覆蓋不對或缺失：C5-24 的 M05 未描述唯一側去重/fail-closed，C5-25 的 M19 未描述餵入去重，C5-27 的 M13 未描述 per-symbol threshold 去重，C5-28 無 mutation，C5-29 的 M06 未描述 assignments symbol reindex。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/pattern_bridge.py:125; CODE-ANCHOR: momentum/Analysis/event_samples/ic_feed.py:56; CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:641; CODE-ANCHOR: frontend/src/components/ic-analysis/EventTablesPanel.tsx:361; CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 依序省略 pattern_bridge 唯一側去重、ic_feed survivor 餵入去重、per-symbol event_id 去重、前端事件數映射、以及 assignments symbol 唯一化，並執行各列 Task 9.3/9.4 named tests；每一列都須各自轉紅。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7455b305c6f3 `[MAJOR]` 信心度=High；逐列命令 `sed -n '93,123p' docs/SPLITUNIFY_SPEC.D-002.md` 取到 29 列：C5-01..23、C5-26 可對應，C5-24/25/27/28/29 為上述五列。一次修訂需改寫 M05 或新增五個專屬 mutation，並把 register 指向各自反向測試。
## CODEX-R14-P2-04
**斷言**: `doc_friction_ratio` 的封閉字面規則漏掉「六個下游消費面、表列九列」這類同一段明示兩個數量但未使用既有關鍵詞的文檔病。
**碼證**: `handoffs/20260912-docrot-x-consult-r3/synth.md:33` 的現行 regex 定義；brief 的 R13 B9D 反例。
**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#b668b6c7ade7;handoffs/20260911-SPLITUNIFY-B9-REVIEW-R14-BRIEF.md#f41f50fff891 `[MINOR]` doc-literal-only，信心度=High；是，集合過窄。可直接替換為 `多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張|([0-9]+|[零一二三四五六七八九十百]+)(個|處|列|項|家|支撐面|消費面).*(但|卻|與|不符|不一致|不相符|少了|多了|漏).*([0-9]+|[零一二三四五六七八九十百]+)(個|處|列|項|家|支撐面|消費面)`；按現行集合本輪為 0/4=0.00，顯示該漏報。
ANSWERS: Q1＝R13 P1-01/P1-02/P2-03 均 CLOSED（grep 顯示 C5-20→M35、C5-21→M36、B9D=七模組＋兩支撐面＝九列；duplicate probe=`DUPLICATE_ID_SET=FAIL`）；Q2＝5 列錯配如 P1-03，其餘 24 列可對應/刻意 `—`；Q3＝不足，採 P1-01 直接貼字面；Q4＝可繞過如 P1-02，最小修補為 audit HEAD＋逐 ID 分類/path 對證；Q5＝REJECTED，阻擋項可在一次修訂內關閉；Q6＝現在不可領 token，需先關閉三個 P1、三家以新 body 重簽並使 `reconcile_stamps_check` rc=0。§1：B9A–F↔9.1–9.5、必要性/quant/OOM/cache/API 無新增 finding；DOCROT 本輪 4 findings、現行字面分子 0。
ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`→`7455b305c6f3…`; counts→mutation 36、§C-9 36、register 29、條數標題恰一處；兩次 `doc_format_precheck` rc=0；C5 receipt exact/duplicate probes 與 R13 closure grep 均如上。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'assignments_composite_key_unique or purged_composite_key_unique'`→78 deselected/0 selected rc=5；未跑全套 pytest（本輪唯讀文檔審查）。
FAILURES_SEEN: 上述 0 selected 是現況證據；`reconcile_stamps_check` 讀取命令被 OPEN-debt PreToolUse gate 擋下，未繞過、未改檔。SCOPE_CHANGES: 僅新增本交件與 codex stamp；未改 `data_cache/`、根 `HANDOFF.md`、碼、SPEC 正文、TODO。NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更。HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r14-codex.md`。
VERDICT: blocked
BLOCKED-BY: CODEX-R14-P1-01,CODEX-R14-P1-02,CODEX-R14-P1-03
CLOSED: CODEX-R13-P1-01,CODEX-R13-P1-02,CODEX-R13-P2-03
STATUS: DONE
