# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-19 | **Branch**: **feat/ic-1cfr-full-impl** | **狀態**: ✅ **1c-FR-FULL 完工(三方 DATA-CORRECT 全 PASS;待 push/merge)**

## ✅ 1c-FR-FULL 完工(branch feat/ic-1cfr-full-impl)
- **SPEC v0.6.2 + TODO FROZEN**(winsorize REMOVE 四方一致/EXPANDING FINAL/pit_stats 手刻;TODO R1→R3.1 四輪 adversarial,三家 RECONCILE-STAMP PASS)。
- **7 批全完成雙審閉合**:B0(5bafd45 baseline)/F0(e72e26d+3163c1f PIT 計算根,雙審抓6洞回修)/F1(c8bd4dc+7b035db runner+series owner,抓cache-hit一致性)/F2(beaa024+5089c9f sanitizer §U+全出口,codex抓4洞含假綠+data_cache污染)/F3(9964452+4150f73 前端+正名,抓假wiring)/F4(ea61359 net_ic breakeven+NetICChart,一次過)/F5(34f2341+a1a8e7d+48db0b8+daf78d7 測試改寫+enabled=True flip,抓check-nodeids假receipt+M-pos oracle)。
- **✅ 三方 DATA-CORRECT 全 PASS**(Claude+Codex〔adversarial〕+Composer;handoffs/ic1cfr_full_baseline/DATACORRECT-*):①PIT 無前瞻真kline實證 ②value hash 逐元素 ③跨symbol/TF隔離(ETH/BTC/4h) ④正名無冒充。final gate 94 passed 0 skip/xfail+net_ic 36;check-nodeids REAL_EXIT=0;decoupling R2=1 R3=17 R4=2。
- **功能已 enabled=True 上線**;canonical=單標的逐因子擇時多空(PIT expanding,winsorize 移除)。
- **待辦**:push branch;merge main(比照 LA-2);ROADMAP 標 1c-FR-FULL DONE。
- **踩坑**:派工勿加 `&`(detach harness);`pytest|tee`/`|tail` 遮蔽 exit code(Claude 一度誤報 check-nodeids exit0,codex 抓到);每批 Claude 獨立驗+雙審閉合。

## (歷史)下一站候選:1d attribution / 1f 空圖(見 ROADMAP P1 尾巴)

## (歷史)✅ LA-2(P2)完工並合併 main

## ✅ LA-2(P2)look-ahead 整治完工並合併 main(merge commit,branch feat/ic-la2-p2-impl 可刪)
六 commit(463bfb5→38ec882→24376dd→8bf67ac→185a259→7b4be86):
- **B0** baseline 凍結+attribution validator+12 nodeid 骨架。
- **B1** winsorized 標籤禁用(三層 fail-closed,PIT 違規不可達;雙家抓 2 繞過→修→closure)。
- **B2** model OOT-only 契約:contracts receipts(field-wise sha256 防撞+envelope verify 不可繞)+validate_oot_label_horizon(嚴格`<`+跨symbol+timestamp gap)+OOT 真接線 service+calibrator 禁自簽+train_auc→in_sample_train_auc+cal/PR/Brier/ECE=cv_oof(OOF 不足 OMIT);雙家 REJECT 4B→F1-F10 修→兩輪 closure→CLOSED。
- **B3** 條件模組:regime `_fit_global` 硬移除(只剩 `_fit_expanding` PIT)+pattern 晉升 server 權威(缺三 provenance→非 active、偽造 metadata 拒)+factor proxy=trailing close-ret(`shift(1)` lag≥1 不含未來)+FactorModuleResult typed+deny_factor_in_ok_oos。
- **B4.1** mutation 全套護產線+golden 重基準(train_auc 欄名變後重基準)+final gate 禁 skip/xfail。
- **B4.2 三方 DATA-CORRECT PASS**(scope a+d 高風險):Claude+Composer 兩腿獨立收斂 DOUBT-1(verify_oot_receipt contracts.py:1474 嚴格`<`無等號邊界測試)→Grok 補 test_verify_oot_receipt_equality_boundary(nodeid 12→13)→三方各自親跑 mutate `<`→`<=` 必 FAIL 證關閉→Claude+Composer flip PASS、Codex PASS → 乾淨。**Grok=實作者不簽**。
- **final gate**:`pytest tests/momentum/test_la2_lookahead.py tests/golden/la2/` → **31 passed 0 skip/xfail** 真 kline。
- 審計:`handoffs/LA2-*`(RECON/SPEC-ADV/TODO-ADV/FREEZE/B{0..4}-{IMPL,REVIEW,CLOSURE}/B42-DATACORRECT-{claude,composer,codex}/DC-REVERIFY;gitignored 本地)。

## ▶ 下一站=**1c-FR-FULL**(資源序 LA-2→1c-FR-FULL→1d→1f;併入 IC-LOOKAHEAD-REMEDIATION epic 的 P1-4/P0-2 分位家族)
- **canonical**:因子報酬序列=**單標的逐因子擇時多空**(單 symbol high/low 永不共時,教科書橫截面不可行);必正名禁冒充橫截面(memory `project_1cfr_full_p1_canonical`)。
- **⚠ 開場稽核(2026-07-18)已抓 HANDOFF/ROADMAP 過時 2 處**:①偵察+SPEC **早已完成**(非「從頭走」);②SPEC「已凍結就緒」是**分裂裁決**——R4 Codex/Composer FREEZE-OK 但 **Grok OPEN-R4-1 BLOCKING**(§G winsorize identity vs §C 嚴格 PIT 契約自撞),ROADMAP 只寫半套。
- **實況/現狀**:`docs/IC1CFR_FULL_SPEC.md` 偵察(`handoffs/1cFRFULL-RECON/LOOKAHEAD-*`)+R1-R4 adversarial 全做完;Claude 已起草 **v0.5 修補**閉合 Grok OPEN-R4-1(採 Grok 選項3:§C 鎖 `winsorize_min_samples=100` no-op 門檻〔已在 line 42〕+§V M-winsorize 明綁 real-kline n≥100、synthetic 7-bar 禁驗 winsorize)。**TODO `docs/IC1CFR_FULL_TODO.md` 尚未生成**;`pit_stats.py`(LA-0 產物)為 PIT 複用目標。
- **✅ SPEC v0.6 FROZEN(2026-07-18)**:R5 三家確認 OPEN-R4-1 閉合後,使用者質疑「上一站不是已禁 winsorize?」→ 釐清=LA-2 禁的是 winsorized **標籤**、本票是 FR **策略報酬序列** winsorize(兩條不同路徑)→ 交委員會辯存廢 → **四方一致 REMOVE**(FR 是診斷非交易 PnL,裁尾藏尾部;砍掉整包 min_samples/M-winsorize/OPEN-R4-1 複雜度;memory `project_1cfr_winsorize_removed`)。SPEC 改 `ls_return_full=position×future_return`(raw identity)。三家戳記輪 codex+composer+grok RECONCILE-STAMP APPROVED,`reconcile_stamps_check.sh` PASS(body sha256:dd357efd)。審計=`handoffs/1cFRFULL-{WINSOR-PREMISE-*,SPEC-R5-*,SPEC-STAMP-*}`。
- **下一步=TODO 起草**:Claude 起草 `docs/IC1CFR_FULL_TODO.md`(依凍結 v0.6 SPEC 的 §P Phase DAG F0→F5)→三家 adversarial→TODO 凍結+RECONCILE-STAMP→逐批 Grok 實作+Codex+Composer 雙家 review→三方 DATA-CORRECT。`pit_stats.py`(LA-0)為 PIT qcut 複用目標。範本=`handoffs/LA{0,1,2}-*`。分工=Grok 實作/Codex+Composer 審查。

## 📌 慣例/環境(沿用)
- 派工走 `scripts/cx_run.sh <codex|grok|composer> <brief> <output> [effort]`(絕對路徑+固定 template,根除 backtick/&/PATH 反覆犯)。Grok=實作者;reviewer=Codex+Composer;gate.sh dispatch 開 token+register-output。
- 委員 /tmp workdir 收尾清理(留 claude-501);pytest collect 副作用 `tests/golden/l65/test_inventory.txt` 勿 commit(跑子集會被重寫成 BLOCKER)。
- pre-existing 7 紅(redirect state-leak 測試順序)非本 epic 另票;IC 過渡期跑 feature_filter 別全量(OOM,funnel 整個 Gatekeeper 完成後)。
