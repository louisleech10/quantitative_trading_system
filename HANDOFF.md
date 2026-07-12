# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-12 | **Branch**: main

## ✅ P2 債已閉合入版
- 票 1 governance(d0d0ebf);票 3 tsc(492c4cc);票 2 data_cache redirect(e6825d9,final7 五 set 綠);
  票 4 codex 沙箱繞法固化+根因(#18243 族,非 #7852;Grok X 搜尋修正)(669c6fa/59c691e/bc2fa94)。

## ▶ 進行中:IC-API-TEST-MODERNIZATION epic(票6 升級,使用者 2026-07-12「現在就做」)
- **緣起**:票6 原「rename label→return_5」實作揭露 23 個 main 既有紅是**多層 stale 合成 fixture**
  (label 名/cadence 12h/尾端 NaN…),用 `rng.normal` **違反鐵律**(數據正確性須真 kline,禁合成)。
- **三方共識**(handoffs/P2DEBT-T6-TESTSTRATEGY-{chair,grok,composer}.md,grok+composer 收斂):
  不全刪(失 API 覆蓋);改用**真 kline 衍生共用 session fixture**:ETHUSDT/12h/~512 根切自
  data_cache/feature_klines/kline_cache.h5,衍生 features(非 rng)+return_5+尾5NaN;分層 L0 純契約(404/422 免資料)
  /L1 API 表面/L2 真管線;去重約 3 個 deep 重複測;範本=conftest.requires_kline_data+test_ic_1eb_b4_fullstack
  (勿抄 phase6 過期路徑);test_ic_e2e.py 同病納 Phase 2。
- **狀態**:三方諮詢完成;下一步=主委寫 epic SPEC → 雙家族 adversarial → reconcile → 實作 → 雙審 → 驗收
  (23 綠+無合成+生產零 diff+PIT 無洩漏)。RISK-HIT a/d,大,完整管線。
- 票6 rename 本體(VERIFY-EXEMPT:doc-example:t6-pivot;證據見 P2DEBT-T6-IMPL-RESULT-codex 反向極性)可行但停損不硬補合成;23 暫列已知既存紅。

## P2 債剩餘
- **票 5** golden provenance(大):與票2相鄰;工作樹留 5 個 golden 檔(baseline_*.json+2 freeze 票5 hunk+l65)。
- epic 完成後回頭票5,或依使用者排序。

## 未 commit 殘留(刻意)
- .claude/settings.json(本機);票5 golden hunk(見上)。
