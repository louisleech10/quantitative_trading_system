# SPLITUNIFY B9 REVIEW R24 — CODEX；task=`20260911-SPLITUNIFY-B9-REVIEW-R24`；brief-kind=`review`
(0a) 接受 Rule 12 封閉集合判定：`review` 不受 `reconcile 未核可` 阻擋；(0b) 不需 refute，既有 stamp rc=1 不是本輪拒審理由。
(1a) `CODEX-R22-P1-01/02/03` 均關閉：SU-RESID-2 已部分關閉且只留 Task 9.2b／9.3；G-3b 已 `SUPERSEDED BY Task 9.5`；metadata 交付半句已刪節、舊 needs-research 已成追溯文字。
(1b) `rg -n 'SU-RESID-2|needs-research|SUPERSEDED BY.*Task 9.5|metadata\.split_unify' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 對證；六組指定回歸實跑 `706 passed, 1 xfailed` rc=0。G-3a／G-5② 仍為一次性遷移／單 TF oracle，未誤標 superseded。
## CODEX-R24-P1-01
**斷言**: Task 9.1 目標句與 §V 已限定 producer → `EventSplitPlan.summary` 兩層，但 live mutation `M-SU-D2-03` 仍要求 metadata 值相等／exact-key，§P 同段仍要求 producer→metadata handoff；這會指示實作者交付現行入口無法產出的欄位。
**碼證**: `EventPipelineResult` 現行欄位含 `summary`、`split_plan`，沒有 `metadata`；反向 assertion 實跑失敗。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:52
MUTATION: venv/bin/python -c 'from momentum.Analysis.event_samples.pipeline import EventPipelineResult; print(sorted(EventPipelineResult.__annotations__)); assert "metadata" in EventPipelineResult.__annotations__'
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1b0890e367ab; docs/SPLITUNIFY_TODO.md#f39b30357511；輸出欄位清單無 metadata、`metadata_required_mutation_rc=1`。一次文件修訂即可把 metadata／M-SU-D2-03 改掛 SU-RESID-9A-UI，Task 9.1 僅留兩層。
## CODEX-R24-P2-02
**斷言**: TODO §E `SU-RESID-C5-TARGETS` 同時寫缺錨為 19 列與「要動 20 列 register」，同一殘留的現行數字不唯一。
**碼證**: awk 重掃輸出非 anchor=15；register=29、keyed=10，故缺錨=19；行 707-708 已說 20 是舊值，行 710 卻再寫 20。
**來源摘要**: docs/SPLITUNIFY_TODO.md#f39b30357511；docs/SPLITUNIFY_SPEC.D-002.md#1b0890e367ab；一次修訂將行 710 改為 19 即可。
(2a) `REJECTED`：有一個 P1 可實作性／文件權威阻塞及一個 P2 數字不一致；(2b) 唯一 BLOCKER 是 `CODEX-R24-P1-01`，P2 不列入 BLOCKED-BY。
(3a) §N SU-RESID-1/3 無 B9B 倒退；SU-RESID-9A-UI metadata 句與兩層邊界不一致，併入 P1；Task 2.1、2.2、3.1–3.3、4.1 無新 live 衝突；Task 9.2b SPEC/TODO 三段側別、廣播、purged、disjoint、AlignmentViolationError 一致。兩個 review commit `git diff --check` 均 rc=0；非三項 collateral 依 brief 排除。
(3b) 最小貼入修補：M-SU-D2-03 只驗 producer→summary；metadata exact-key 改掛 SU-RESID-9A-UI；§N／TODO §E 刪 metadata 本延伸承諾；§P／§R「三層」改「兩層」；TODO 行 710 的 20 改 19。
(4a) 不進 B9C，先完成上述一次文件同步；(4b) SU-RESID-2 恰有兩個 blocker：Task 9.2b 與 Task 9.3，Task 9.4／9.5 不加入。
(5a) G-3a（一次性差集）與 G-5②（單 TF assignments／purged oracle）不應 supersede；(5b) G-3b 才移交 Task 9.5，複合鍵集合是跨 TF 長期 golden，B9B 單 TF 過渡不是免驗。
(6a) B9C 入口延後至 P1 關閉；(6b) 最小閉合集合為 `CODEX-R24-P1-01`、`CODEX-R24-P2-02`，不重開 9.2b／9.3 設計。
本輪未發現 API schema、量化數值、NaN/inf、OOM/cache、資料洩漏、跨 symbol、測試獨立性或必要性新缺口；本輪 finding 為 P1 文件／入口矛盾與 P2 19/20 列數矛盾。
VERDICT: blocked；BLOCKED-BY: CODEX-R24-P1-01；CLOSED: CODEX-R22-P1-01,CODEX-R22-P1-02,CODEX-R22-P1-03
ASSUMPTIONS_VERIFIED: `brief-kind: review`；body hash=`1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`；C5 register=29/keyed=10/missing=19。
TESTS_RUN: 六組 pytest → `706 passed, 1 xfailed` rc=0；metadata mutation rc=1（預期反例）；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；兩個 review commit diff-check rc=0。
FAILURES_SEEN: 僅 brief 明示的 Task 9.2b strict-xfail 與 metadata 反向 mutation rc=1；SCOPE_CHANGES: 僅新增本報告及 SPEC 戳記，未改程式／SPEC 正文／TODO 正文／data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 未改產品數值或 schema；僅記錄文件 19/20 矛盾及現行 result 無 metadata 欄。
STATUS: DONE
