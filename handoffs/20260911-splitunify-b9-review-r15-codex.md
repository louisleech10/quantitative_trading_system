# SPLITUNIFY b9 review-r15 — codex；範圍：只審 brief 指定 current block＋0de1a17f diff；未改碼、SPEC 正文或 TODO，僅準備本輪 review 交件與 SPEC 戳記。
## CODEX-R15-P1-01
**斷言**: Task 9.3 receipt 閘仍可用正確 `甲/乙/丙` 分類＋每列同一個真實 `docs/SPLITUNIFY_SPEC.D-002.md:1` 繞過；現行新增 path 檢查只驗存在與行數，不驗 C5 對應。
**碼證**: CODE-ANCHOR: scripts/completeness_check.sh:350
MUTATION: 構造 exact C5-01..29、分類全依現況填寫、所有碼證填 `docs/SPLITUNIFY_SPEC.D-002.md:1`、`COMMIT: deadbeef`，執行 TODO:642-651 的 exact-set／row-format／path 檢查；輸出前三者皆 PASS。
**來源摘要**: docs/SPLITUNIFY_TODO.md#23f19deb2784；[MAJOR] 信心度=High。修法：逐列以 C5-NN keyed 對證 register 之 target path:line（允許該列列出的行範圍），不得只驗檔案存在；並以 audit round-start HEAD 對證 COMMIT。可行性：register 已有逐列 path:line，現有 shell/awk 檢查可加入 keyed diff。
## CODEX-R15-P1-02
**斷言**: `M-SU-D2-38` 所稱「多 TF survivor 餵入端未去重」沒有可達的被測輸入：`build_event_ic_inputs` 先按單一 `timeframe` 過濾，分析時 `WindowRow` 也只有事件級資料。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/ic_feed.py:109
MUTATION: 將 receipts.per_tf 放入同一 event 的 1h／4h 兩列並執行 `build_event_ic_inputs(..., timeframe="1h")`；line 109 先只留下 1h，無法形成該 mutation 描述的多 TF survivor 三元組。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#c342d27bdf04；[MAJOR] 信心度=High。修法：把 M38 改成可達的同 TF 重複輸入 invariant，或明確指定多 TF rows 如何進入 survivor hash 並讓具名測試走該 seam；可行性：`ic_feed.py:43-65` 的 hash 輸入與 `:77-109` 的單 TF 餵入落點都已存在。
## CODEX-R15-P1-03
**斷言**: `M-SU-D2-39` 同時宣稱保護 `per_symbol_n`、`per_symbol_test_n` 與 threshold，但唯一具名測試只寫 threshold；只讓 `per_symbol_n` 錯而保持 threshold 去重時，測試仍會綠。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:716
MUTATION: 保留 `per_symbol_n` 對 composite-key rows 的 `value_counts()`、只修 `per_symbol_test_n`，執行 `test_tier_min_test_events_counts_unique_event_ids`；1 event×2 TF 仍判不足，故該 mutant 不轉紅而 summary 計數可錯。
**來源摘要**: docs/SPLITUNIFY_TODO.md#23f19deb2784；[MAJOR] 信心度=High。修法：在同一具名測試另斷言 `summary["per_symbol_n"]` 等於 unique event_id，或把 per-symbol summary 與 threshold 拆成各自 mutation/test。可行性：`split_projection.py:559-569` 已有 summary 計數落點，新增值斷言不需改 API。
## CODEX-R15-P1-04
**斷言**: `M-SU-D2-40` 把 raw `set_index("event_id").reindex(idx)` 描述成「靜默取錯 symbol」，但 pandas 對 duplicate index 會先明確 `ValueError`，因此目前 mutation 不是所述可執行反例。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 以 `venv/bin/python -c 'import pandas as pd; s=pd.Series(["BTC","ETH"], index=["e1","e1"]); print(s.reindex(pd.Index(["e1"])))'` 重現；stdout/stderr 為 `ValueError: cannot reindex on an axis with duplicate labels`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#c342d27bdf04；[MAJOR] 信心度=High。修法：明定正向 same-symbol duplicate 應去重後成功，另以 conflicting-symbol duplicate 驗 fail-closed；M40 反向移除 explicit reducer 時前者才會轉紅。可行性：line 372 已是單一可變異 seam，pandas probe 已證明 raw path 的實際結果。
(1a)(1b) R14 `CODEX-R14-P1-01`、`P1-02`、`P1-03` 均 closed：`rg` 取得 M35/M36 欄位 ASSERT＋軟包禁令＋多 TF＋兩種破壞；receipt probe=`EXACT_ID_SET=PASS ROW_FORMAT=PASS PATH_EXISTENCE=PASS`，新增內容對證會拒全甲且文字綁 audit HEAD；register grep 取得 C5-24→M05/M37、25→M38、27→M39、28=blocked-by、29→M40。R14 `P2-04` 的「保留原指標、另報加強字面數」可接受，仍不視為指標健康證明。(2a)(2b) 檔案逐條對照：M01/M02/M03→derive/disclosure present；M04→feature_materialization；M05/M37→pattern_bridge；M06/M40→tables；M07/M19/M38→gap3_conditional_ic；M08→counterexample；M09→candidate；M10→dedupe；M11→`frontend/src/app/search/eventExportByEventId.test.tsx` ABSENT；M12/M13/M14/M15/M18/M20/M21/M22/M23/M24/M25/M26/M30/M35/M36→derive/wiring present；M16/M17/M27/M28/M29/M33/M34→golden/script present；M31/M32/M39→baseline/derive present。collect-only→196 collected，future nodes（含 M35–40）皆未收集；Task 尚未開工故可接受，完工前不得宣稱 closed。
(3a)(3b) 仍可繞過「分類照抄 register＋全部真實同一行」；最小字面＝每列碼證須等於該 C5-NN register target 的 path:line 之一（keyed 對證），不得只驗存在／行數，並保留 COMMIT＝audit round-start HEAD。M38/M40 另為本輪 P1。(4a)(4b) R14-P2-04 處置可接受；量測中只有主委依使用者／治理 SSOT 於量測結束後改判並重開量測才有權改。
(5a)(5b) body `c674086e…` 判 REJECTED；一次修訂 blockers＝CODEX-R15-P1-01..04，各可由 keyed receipt／可達 mutation／完整計數 assertion／正確 pandas 反例一次關閉。(6a)(6b) 不可領 impl token；須先關四條 P1、三家對同一 body APPROVED stamp，且 `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0。r13/r14 同類仍有新 blocker，判「仍在收斂」；連續兩輪零新 P0/P1 且無新可達性／mutation 缺口才算遞減報酬。§1：矛盾/漏項/不可測/測試＝上述；quant/OOM/cache/API/必要性＝無新 finding；agent 可執行性＝M38/M39/M40。
ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`→`c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0`；counts mutation=40、§C-9=40、register=29、literal=1；兩檔 `doc_format_precheck` 皆 rc=0；`grep -rn '\.run(' api --include='*.py'` 無 canonical pipeline run。TESTS_RUN: collect-only 12 檔→196 collected rc=0；receipt textual probe→exact/row/path PASS；pandas duplicate reindex→ValueError。FAILURES_SEEN: 首次內嵌換行 probe SyntaxError，單行重跑已取得結果。
SCOPE_CHANGES: 僅新增本交件與 SPEC `## 戳記` 之 codex REJECTED 行；未改碼、SPEC 正文、TODO、HANDOFF.md、data_cache。NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更。HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r15-codex.md`。
VERDICT: blocked
BLOCKED-BY: CODEX-R15-P1-01,CODEX-R15-P1-02,CODEX-R15-P1-03,CODEX-R15-P1-04
CLOSED: CODEX-R14-P1-01,CODEX-R14-P1-02,CODEX-R14-P1-03
STATUS: DONE
