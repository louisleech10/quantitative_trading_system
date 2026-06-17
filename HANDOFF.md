# Handoff
**Agent**: Claude | **Time**: 2026-06-17 | **Branch**: main

## 任務 A ✅ 完成並 push
修 :4109 ref-cache key 硬編碼 BTCUSDT(孤兒碼潛伏 bug,降小任務自修)。讀寫兩端統一以 config.cross_sectional.reference_symbol 為單一真相 + 回歸測試(防假綠驗過)。

## 任務 B — d* walk-forward 子項已三方否決,範圍縮為子項 1+3
**子項 2 (walk-forward d*) ❌ 否決**(2026-06-17 三方真實 kline 實證):d* 會漂(rolling std≈0.25)但**無下游價值**(真實 L1 n=232 配對 dIC_mean=−0.002、WF較佳僅42%、|IC|不增反減),成本 16–50×。連帶否決 d_min floor。詳見記憶 project-dstar-walkforward-rejected + docs/DSTAR_WALKFORWARD_COMMITTEE_BRIEF.md + handoffs/20260617-dstar-{codex,composer}.md + scripts/diag_dstar_*.py。

**剩餘施作 = 子項 1 + 3**(使用者拍板):
1. 全移除 legacy L6.5 + UI 切換鈕 + env(FFACT_IC_FIRST_PIPELINE, get_multi_symbol_ic_first_enabled),IC-First 唯一路徑(接受輸出改變)。
3. causal_preprocessing 程式釘死 True(讀取端強制+忽略外部False+warn)+三處註解。
SPEC/TODO 已更新移除 Phase 3:docs/L65_PREPROCESSING_HARDENING_{SPEC,TODO,BRIEF}.md(範圍=子項1+3)。

### 下一步(接手就做)
- [ ] 雙家族 adversarial 稽核 SPEC/TODO(GPT-5.5+Composer 各一次,reconcile)— 範圍已縮小
- [ ] 過 gate dispatch → **Composer 2.5 實作 + Codex review**(中/大分工,2026-06-17 使用者重申)
- [ ] 接回:diff 防假綠 + 真實 kline 三方資料正確性簽核
- 影響面(實測):後端 feature_factory(ic_first 分支 392-409/2339-2344/2369/2420/2457 + _layer6_5_legacy)、feature_config、core/config、feature_preprocessor(causal:147)、batch_service:660;前端 PreprocessingPanel/types/ic-analysis;~10 測試檔。
- pre-existing 失敗(非本線):test_l65_parallel::test_tier_auto_selects_workers(_column_layer_map,走 legacy,移除時連帶處理)。

## 方法論(本 session 教訓)
先量測再決定:Claude 自產實驗→三方審。我最初「d* 穩定不必做」直覺**理由錯**(d* 其實漂)但**結論對**(不該做 WF)——靠真實 L1 配對 IC 實證校正。委員會 proxy 有 bug 風險(我首版 n=4 是 NaN 卷積污染,修 ffill 後 n=232),壞 run 不可當證據。
