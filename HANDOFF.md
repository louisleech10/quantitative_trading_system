# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-12 | **Branch**: main

## ✅ 已閉合入版
- 票 1 governance(d0d0ebf);票 3 tsc(492c4cc)。

## ▶ 票 2 data_cache redirect(大)——實作雙審中(未 commit)
- **final6**: V1 9p/V2 2p/V5 3p/V7 133p+8skip 五 set DIGEST_DIFF_EMPTY=1,V6 9p+23既有紅但 V6_NO_NEW_RED=1,scripts/run_ic_persist_hermetic.sh --set all exit_code=0 VERIFY:20260712T003131Z-p2debt-t2-impl-final6
- 驗收 finding 鏈 C-1~C-5 全閉合:C-1 skip anchor/C-2+C-3 chdir cwd 依賴/C-4 V6 既有紅(雙STAMP改準則)
  /C-5 V7 真洩漏(守衛立功,lightgbm save+_persist_outputs 補接縫)。
- **現正進行**:grok+composer 雙家族實作 adversarial 審(brief=handoffs/P2DEBT-T2-IMPL-REVIEW-BRIEF.md;
  產出 P2DEBT-T2-IMPL-REVIEW-{grok,composer}.md)。VERIFY-EXEMPT:wip:p2debt-t2-review
- 分工鐵律(使用者):修=codex/跑=grok/主委只讀 receipt,三方分離,主委不自跑代跑。
- **⚠️ commit scoping 待決**:4 個 freeze/baseline 腳本混雜票 2(run_with_manual_redirect 包裝)
  +票 5(h5 快取/config_override 854d444);審查給建議後再切 git add -p。
  純票 5 禁 commit:tests/golden/*/baseline_*.json、l65/test_inventory.txt。
- 雙審 APPROVE → commit(票 2 檔 scope,見 brief)+push → 更新 ROADMAP。

## 新票候補
- 票 6(P-2 裁決):label horizon 既有紅(api IC full analysis 23 nodeid+service cross-sectional 3);
  fixture `label` 欄名 vs 生產 `return_(\d+)` 解析器;涉 a 類完整管線。
- 票 4 蒐證(A/B 裁決);票 5 golden provenance(與票 2 相鄰,含上述混雜檔票 5 hunk)。

## 教訓(SCAR 素材)
- chdir 型 hermetic 測試落地前必附 cwd 依賴盤點(C-2/C-3 三連環)。
- 驗收解析 CLI 輸出附真實樣本(C-1);digest oracle 抓到真洩漏證明守衛可證偽非廉價綠(C-5)。
- 未 commit 殘留:.claude/settings.json(本機)+票 5 golden hunk+票 2 全部產物。
