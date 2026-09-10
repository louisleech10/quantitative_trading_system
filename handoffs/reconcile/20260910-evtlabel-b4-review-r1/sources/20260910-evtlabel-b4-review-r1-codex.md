## CODEX-R1-P0-01
**斷言**: _binary_label_window_bars 是跨 run 的 instance state，且只在 split 分支寫入；無切分 binary 會沿用前值或 0，0 會關掉依賴保護。**碼證**: target ic_filter_orchestrator.py:1065,1211-1215,4764-4767,2387-2410；最小修法是在每次 analyze/refilter 建立 run-local 尺度，無法取得時 fail-closed。**來源摘要**: source_digest: 47eb852bf0aa; TODO:0921c74ab73a
## CODEX-R1-P1-01
**斷言**: 事件最小正間距不是特徵 K 線長度；目標碼在事件每 3 根、W=12 時推 bar=10,800,000、L=12,n_blocks=2，真值 bar=3,600,000、L=4,n_blocks=5，會過度綁定並假性 unavailable。**碼證**: target ic_filter_orchestrator.py:4764-4767,4844-4855；target probe 實得上述 stdout；最小修法由 metadata timeframe_seconds/feature timeframe 注入 authoritative bar，未知即 fail-closed。**來源摘要**: source_digest: 47eb852bf0aa
## CODEX-R1-P1-02
**斷言**: stage3 對 sparse filtered_features 套用 full-frame split_context test_mask，selection scope 不成立且會直接中斷。**碼證**: target ic_filter_orchestrator.py:3651-3656,3759-3767；target probe 實得 IndexError: Boolean index has wrong length: 10 instead of 3；最小修法以 test_plan.row_index/timestamp intersection 產生唯一 selection index，stage3/stage5 共用。**來源摘要**: source_digest: 47eb852bf0aa
## CODEX-R1-P1-03
**斷言**: 負對照不是同一套 selector：target 永遠重算 BH q（未接 fdr_enabled），主路徑可讀 raw p；且 observed 是 oracle 後 3 個、null 是 full-table 16 個。**碼證**: target ic_filter_orchestrator.py:4736-4745,4783-4828,4993-4996；target probe 實得 passed_before_oracle=16 survivors_after_oracle=3、n_observed=3、q95=16；最小修法抽共用 binary threshold selector，observed/null 使用同 universe、同 stage。**來源摘要**: source_digest: 47eb852bf0aa
## CODEX-R1-P1-04
**斷言**: 39,373×165 之 10% NaN 全表 MW 約 4.79s/次，target 固定 50 次即約 239s，違反 TODO 每道小於 120s；clean 約 0.56×50=28s 不代表通過。**碼證**: target loop ic_filter_orchestrator.py:4806-4828、negative_control_n=50；probe 20260910-probe-oracle-bench.py stdout 含 c 239s；最小修法是可證明的批次/快取設計，或有上限且揭露 n_planned/n_effective/budget 的降階，不得靜默砍 N。**來源摘要**: source_digest: 47eb852bf0aa; TODO:0921c74ab73a
## CODEX-R1-P1-05
**斷言**: binary downstream 仍用報酬統計：redundancy_scores 對 imported binary 取 ic_mean，且 stage6b 未標 diagnostic；service/event-rule 也未交付 primary/effect disclosure，可能移除有效 binary feature 或誤讀報告。**碼證**: target ic_filter_orchestrator.py:3476-3488,5202-5272、api/services/ic_analysis_service.py:275-306、event_label_mode.py:156-180；probe 得 scores={binary_strong:0.01,binary_weak:0.9}；最小修法 binary redundancy 用 abs(rank_biserial)，stage6b 固定 diagnostic/no removal，並同步契約揭露。**來源摘要**: source_digest: 47eb852bf0aa; TODO:0921c74ab73a; API:067a48dd6645
## CODEX-R1-P2-01
**斷言**: stage5 第三道 guard 沒驗 owner,ts,label：owners 建了但未使用，只比 ts,label；summary row 對不上也 continue，會變成 silent binary_unavailable 而非接線錯誤。**碼證**: target ic_filter_orchestrator.py:4902-4912,4921-4935,4980-4983；owner probe 在非預期 event IDs 下仍 merge_returned=True,binary_status=ok；最小修法以 owner map 驗完整 triple，欄名集合 mismatch 直接 raise。**來源摘要**: source_digest: 47eb852bf0aa; contract:de3ee1a17b87
## Verdict
1a/1b: 真洞但 brief 所稱「低估」方向相反；此實作把 3 根當 1 根而 L 高估。bar 必須由 feature timeframe/metadata 傳入，不由事件密度猜。
2a/2b: 會跨 run／無切分殘留或為 0；analyze 入口清空並在 event isolation 已知時於 split 外設定，較佳是 run-local immutable context。
3a/3b: 不同；BH/raw-p 與 duplicated predicate 已可分歧。複用同一 selector/helper，並傳遞 fdr_enabled。
4a/4b: 是；oracle 後 survivors 與 full-table shuffled counts 不同義。觀測量改為 threshold-pass（另揭露 consumable）或兩端都跑完整相同流程。
5a/5b: 實測 clean 約 28s、10% NaN 名目 239s（4.79s×50），後者超 120s；應改設計或有揭露的時間預算降階，不能放寬品質閘。
6a/6b: 不恆等；stage3 先對 sparse frame 套 full mask，已實得 IndexError。守衛應比對同一個 canonical test/event index，而非目前物件的錯位 mask。
7a/7b: 應 raise；row-name mismatch 是集合/接線錯，不是單欄 unavailable。fail-closed raise 並附 feature 名稱。
8: 未見 ≥10× 不必要複雜；但 P0/P1 blockers、stage6/6b 語意與 disclosure 未收斂，不宜進第三批。
TESTS_RUN: clean target archive pytest 指定 B4 五檔 → 95 passed, 2 warnings, rc=0；bench probes → oracle rc=0、MW rc=0。
FAILURES_SEEN: 初次 archive 測試漏 cd 而誤跑 dirty repo；修正後 clean target 95 passed。dirty repo 另見後續測試 109 passed/1 failed，未納入 target verdict；全套 Analysis 因 archive 缺 golden/data 且卡既有 benchmark，以 Ctrl-C rc=130 終止。
SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: review only，指出 block scale、negative-control semantics、stage6/statistic disclosure 影響，未改產品碼或測試。
ASSUMPTIONS_VERIFIED: target commit、SPEC/TODO RECONCILE-STAMP、上述 runtime probes、clean-target B4 tests、39,373×165 benchmark outputs。
STATUS: DONE
