# SPLITUNIFY b9 review-r30 — codex；輸入 `git show fa0ca3f4`、O1–O5、`SU-RESID-V8-ATTEST`；排除 HISTORY／沿革、白話說明、docs/site、HANDOFF、SCAR_LEDGER，未重開 Task 9.3–9.5 設計。
## CODEX-R30-P1-01
**斷言**: O3 字面切斷事後 BASE/H1 平移，未切斷初始同源算錯；G-4e 可在錯誤初始時間軸上相等。
**碼證**: `_feature_index()` 用 `BASE + i*H1`，`_event_keys()` 用 index 產生實際 decision，並以同函式 hand mapping 產生 expected；自建 probe 得 BASE-only `13` mismatches，但 BASE+hand 同步平移得 `BASE_SHIFT_AND_HAND_SHIFT_G4E_EQUAL True`（sample `1700000000017 1700000000017`）。
CODE-ANCHOR: scripts/freeze_splitunify_golden.py:151
MUTATION: 暫存 import 將 `BASE` 平移 17ms，並同步把 `_event_keys()` 回傳的 `expected_decision_at_ms` 平移 17ms；執行 G-4e 時刻比較，觀察兩欄仍相等。
**來源摘要**: scripts/freeze_splitunify_golden.py#d67f48046c6c; tests/momentum/Analysis/test_splitunify_golden.py#09ea562d2e5c。P1/High；一次修訂將事件輸入改為獨立、手寫、非 BASE/H1 生成的 13 筆 committed fixture，expected mapping 由獨立測試／receipt 提供；既有 JSON/bytes/digest 對證模式證明可落地，同 commit 惡意替換仍是既有 user-ruling 殘留。
## CODEX-R30-P1-02
**斷言**: SPEC §P `Task 9.2:197-202` 未標 SUPERSEDED，仍把 B9B 舊契約寫成現行碼態；照 SPEC 實作會退回 selected 必傳、四參數閘、單列 merge。
**碼證**: SPEC 仍寫 `build_event_keys(... selected_timeframe=str(selected_timeframe))`、四者同時非 None、每事件恰一列；現行 `pipeline.py:727-743` 只要求三個 canonical 邊界，wiring 兩測試實跑 `2 passed`。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:727
MUTATION: 把 `selected_timeframe` 加回 `projection_args` required set 並保留 `str(None)`，執行 `test_partial_boundary_gate_accepts_none_selected_timeframe` 與 `test_run_without_selected_timeframe_emits_all_feature_tf_rows`；兩者應轉紅。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1c29e2132fa8; momentum/Analysis/event_samples/pipeline.py#ab9322e5cf0f; tests/momentum/event_samples/test_splitunify_wiring.py#6f1e3711c2fc。P1/High；可直接貼入：「`selected_timeframe=None`＝全量 `(event_id,feature_timeframe)` keyed rows；字串＝可選過濾；required set 僅三 canonical 邊界；merge 以 `per_tf` 為行粒度、欄取 `per_tf.timeframe`；docstring 改為複合鍵唯一」。
## CODEX-R30-P2-03
**斷言**: O1 實作要求 `<key>=<old8>:<new8>`，但 `--help` 仍說「逗號分隔之既有頂層鍵清單」，會引導到必然被拒的 key-only 語法。
**碼證**: `venv/bin/python scripts/freeze_splitunify_golden.py --help` 顯示舊 help；temp probe key-only `rc=1`，正確 token `g4_per_symbol_n=dd296919:b7088eec` `rc=0`，改新值同 token `rc=1`。CODE-ANCHOR: scripts/freeze_splitunify_golden.py:558；**來源摘要**: scripts/freeze_splitunify_golden.py#d67f48046c6c。P2/Medium、doc-literal-only；help 改為 old8/new8 canonical JSON sha256 前 8 碼說明，非 blocking。
# 必答
**(1a/1b)** r29 P1-01 CLOSED（exact digest）；P1-02 STILL-OPEN（HISTORY half closed；四檔同 commit half 仍是 `SU-RESID-V8-ATTEST` user-ruling）；P1-03 CLOSED（BASE-only）；P1-04 CLOSED（main init/transaction）；P1-05 CLOSED。自建 O1/O2/O3/O4 probes 分別觀察 key-only拒／貼回正確且改值拒、HISTORY anchor `None`、13 mismatches／同步錯仍 equal、init pair 建立後 digest fail-closed 並可刪後重建；O5 fixture 13/12/`bnd_shift`，node `1 passed`。
**(2a/2b)** `REJECTED`；blocking=`CODEX-R30-P1-01,CODEX-R30-P1-02`。一次修訂最小集合：獨立非 BASE/H1 timestamp fixture＋independent expected mapping；同步把 SPEC §P Task 9.2 三個舊字面改成三參數／全量複合鍵／per_tf 行粒度；P2 help 可同批修。
**(3a/3b)** O2 residual 歸類成立；O1 digest 不等價於無閘成立；O3 共因假設不成立，修法見 P1-01；O5 修補對齊但窮盡假設不成立，修法見 P1-02。O2 不需新工具：`run_with_receipt.py:4-5` 明載 receipt/audit 同一可寫主體且非防惡意偽造，`verify_audit_chain.py:72-74` 純報告永遠 rc=0，`git config --get commit.gpgsign` 無輸出，既有倉內層不能成獨立信任根。
**(4a/4b)** 自立詞表：`legacy side source`、`legacy row grain`、`legacy timestamp source`、`legacy count/source`、`stale auth syntax`；命令為自建 `venv/bin/python - <<'PY'` regex scan（SPEC 截於沿革、TODO 全文）。SPEC C0/C5/C6/RISK/A/G/V/N 與 TODO §0/§B/Task1–4/9.1/9.2b–9.5/§D/§E 無新矛盾；TODO 9.2a xfail hits 均有 SUPERSEDED/刪節線且現行 1 passed；唯一 live contradiction 是 SPEC §P Task 9.2:197-202（P1-02）；可貼字面見 P1-02。
**(5a/5b)** 不可進 B9D；最小阻擋集合 `CODEX-R30-P1-01,CODEX-R30-P1-02`。`SU-RESID-V8-ATTEST` 是 user-ruling、非 blocking；O1/O4/O5 已修半不另增 blocker。
VERDICT: blocked
BLOCKED-BY: CODEX-R30-P1-01,CODEX-R30-P1-02
CLOSED: CODEX-R29-P1-01,CODEX-R29-P1-03,CODEX-R29-P1-04,CODEX-R29-P1-05
ASSUMPTIONS_VERIFIED: O1 exact token；O2 same-writer receipt boundary；O4 init-v8 delete/rebuild 後仍 digest fail-closed；O5 13/12/bnd_shift；O3 深層共因被 probe 否證；SPEC §P 舊 live 字面被 scan 確認。
TESTS_RUN: O1–O4 自建 temp probes；fixture probe；指定 node→1 passed；wiring pair→2 passed；derive pair→2 passed；doc_format SPEC/TODO→rc=0；reconcile_body_hash→`bc4a2b3e…`, rc=0；freeze `--help` 與 `git diff --name-status fa0ca3f4^ fa0ca3f4` 已實跑；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r30-codex.md --family codex`→PASS, rc=0。
FAILURES_SEEN: 初版 O1 probe 忘建 temp receipt dir、再漏設 temp REPO，均為 harness setup traceback；修正後結論完成，未改 repo code/test。 NUMERIC_OR_SCHEMA_IMPACT: 未修改 runtime、golden、numeric 或 wire schema；修法為提案。
SCOPE_CHANGES: 僅新增本檔及 append required codex REJECTED stamp；未改 code、SPEC正文、TODO、root HANDOFF、data_cache；`/tmp/workdir` 不存在、無需刪除，`/tmp/claude-501` 保留。 OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r30-codex.md
STATUS: DONE
