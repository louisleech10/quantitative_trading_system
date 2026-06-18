# Handoff
**Agent**: Claude | **Time**: 2026-06-18 | **Branch**: main

## 任務 A ✅ 完成 push (:4109 ref-cache 修正 + 防假綠回歸測試)

## 任務 B — L6.5 強化(子項1移legacy + 子項3釘死causal;子項2 walk-forward 已三方否決)
**狀態:雙家族 adversarial 已過+reconcile;實作進行中(Codex 實作,Composer shell 被擋 role-swap)**

- ✅ **B0**(Task 0.1):scripts/build_l65_golden_baseline.py + tests/golden/l65_hardening/(6 records,--check PASS)。commit 751067b。
- ✅ **B1**(Task 1.1,1.2):causal 釘死 True+warn+傳播鏈測試+三處註解;6 個既有 causal=False 測試**忠實重寫**(對照獨立 causal oracle,防假綠,我 diff 驗過)。203 passed。commit e8b62c9。
- ✅ **B2**(commits f6bf409 移legacy + 6d749ba F1-F4修補 + 4d8cae7 frozen-doc):IC-First 唯一路徑。golden --check PASS、grep0、npm build、targeted 132 passed。Codex 2 次 timeout(全suite慢)→我 targeted 驗+代commit。Composer review 跑中(b04g8hkik);全suite backstop 跑中(b9qx6u3qc)。
- ✅ **B3a**(1cbcd25 causal死碼清理 byte不變 + d829754 B2review#1-6修補+config_hash golden重生):targeted 226 passed+golden check+多symbol smoke PASS。Composer review跑中(boxxeflr6);全suite backstop跑中(bvn9fmjr5)。
  - backstop 抓到 config_hash golden stale(移ic_first_pipeline欄→hash 57c4→1dbe,正確後果,已重生)+perf flaky(忽略)。⚠️副作用:config_hash變→現有特徵快取失效需重生。
- ⬜ **B3b**:真實 kline **三方資料正確性簽核**(Claude+Codex+Composer 各獨立驗 生成→計算→merge→split→無洩漏;§V 不變量表)。任務B最後一哩。

### 接回驗收要點(每批我必做)
postflight(data_cache 防刪)+ diff 既有斷言**防假綠**+ 自跑驗證(不信執行端報告)+ golden --check byte 一致 + commit(Codex sandbox `.git/index.lock` 不可寫→commit 我代勞)。B2 完待 Composer read-only code review。

### Pre-existing 失敗(非本線,勿誤判回歸)
1. test_l65_parallel::test_tier_auto_selects_workers + test_ic_first_pipeline 4 個 = `_column_layer_map`/`_storage` AttributeError(走 legacy 路徑;B2 移 legacy 後應調整/消失)。
2. test_failopen_matrix::test_v8_frozen_doc_covers_every_existing_assertion_change = frozen doc 過期(含我 Task A 測試 + 一堆無關 hardware/phase_d 測試→session 前就紅)。**治理 housekeeping,需重生 frozen doc,獨立於 L65**。

## 關鍵文件
docs/L65_PREPROCESSING_HARDENING_{SPEC(權威),TODO,BRIEF}.md;記憶 project-dstar-walkforward-rejected;handoffs/20260617-l65-adv-* + 20260618-l65-impl-*。
執行端:中/大實作 Composer,Codex review(但本機 Composer shell 被擋→暫由 Codex 實作 role-swap)。
