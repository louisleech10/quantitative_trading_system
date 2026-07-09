# Handoff
**Agent**: Claude | **Time**: 2026-07-09 | **Branch**: main

## ✅ 剛完成:IC 1a 剩餘刀①「1-align 前瞻錯位硬閘」全刀閉合(2026-07-09,本次 commit)
SIGNOFF:claude:DATA-CORRECT SIGNOFF:codex:DATA-CORRECT SIGNOFF:composer:DATA-CORRECT
- **SPEC v3 Frozen**(R1-R3 雙家族 adversarial,雙 RECONCILE-STAMP)→B1 kernel+horizon resolver(fd5866f)→B2 四主路徑接線+D-4 寫回(854d444)→B3 grouped/xsec(78c85bb)→fixture 遷移(e47933d)。REF:handoffs/IC1A-ALIGN-RECONCILE.md
- **重大破案**:cut1 golden 舊 baseline 凍到壞行為——rolling IC index-join 0 列(features int64 vs label RangeIndex),summary 全 None 被當標準答案;B2 修活後重凍(MIXED 裁定:index 修正留+float64 強轉修掉,dtype 保留後 grouped/turnover 與舊 baseline maxdiff=0)。RCA 詳 handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-codex.md 與 -composer.md 兩檔;摘要 REF:handoffs/IC1A-ALIGN-SIGNOFF-claude.md
- **驗收**:全套 momentum 986 passed;golden 2 passed;M1-M7 mutation 轉紅 receipt 全;Codex adversarial 簽核 10 攻擊情境全攔(錯tf/亂序/重複ts/毫秒/跨symbol標籤/邊界腐化/外部labels/等長平移×2)。REF:handoffs/IC1A-ALIGN-SIGNOFF-claude.md REF:handoffs/IC1A-ALIGN-SIGNOFF-codex.md REF:handoffs/IC1A-ALIGN-SIGNOFF-composer.md
- **殘留(登記,不擋)**:①~~2 pre-existing FF 紅~~ **已閉(a8c9ca7)**:根因=測試期望過時非 bug——L6.5 設計只做 Winsor+Fracdiff(使用者 2026-07-09 定,存記憶 ff-l65-preprocessing-scope),rank/zscore config key 被接受但不生效(幽靈 key,歸 FF preset 盤點 epic);perf 測試讀廢棄的空 metadata.feature_names,改讀 manifest;
- **B-1 缺口已補(24f36d7,省步版使用者核可)**:validate_alignment Tier-2 oracle 加 simple 報酬型(tests/momentum/core/test_alignment_contract.py 19 tests)。VERIFY:20260709T053442Z-ic1a-align-full-momentum-final(pytest tests/momentum/ 992 passed)。Codex 增量審查通過(檔載機讀 Verdict 行:handoffs/IC1A-ALIGN-B1GAP-REVIEW-codex.md)。**下一 session 義務:B-1 return_kind 語義補進 docs/IC_PHASE1_1A_ALIGN_SPEC.md 並重跑 reconcile 戳記(省步版文檔債)**;
- **B-2**(任意單點值腐化全掃描逃生口)=IC Analysis whole-map 全完成後做(使用者 2026-07-09 定);B-3/B-5 歸「79 測試換真資料」epic;B-4 ISO timestamp 契約歸 1f 刀;②Tier-2 抽樣不承諾任意單點值腐化偵測(非對齊類故障,golden 全值層承擔);③B3 3 NON-BLOCKING(2.6 例外型別等,詳 handoffs/IC1A-ALIGN-REVIEW-B3-composer.md);④report timestamp 序列化 epoch→ISO(前端現用 index 軸無影響,types 註記待補);⑤data_cache/features/BTCUSDT_1h_filtered.h5 曾被 B2 開發期中間版蓋寫(既有設計寫入點,內容=衍生物,下次正確 run 會覆新)。

## ★下一站 = 剩餘刀②「1e HAC + 1b FDR 合刀(顯著性正確化)」(大管線)
- 裁定順序(2026-07-08 使用者):①1-align ✅→**②1e+1b**→③1c Net IC 量綱→④1d attribution→⑤1f 空圖+grouped schema 殘留。REF:handoffs/IC1A-ALIGN-RECONCILE.md
- 偵察事實(三方 receipt,詳 handoffs/IC1A-CUTS-ORDER-codex.md 與 -composer.md):rolling IC 當 i.i.d. 跑 t-test(statistical_validator.py:119)無 HAC;`adjust_multiple_comparisons`(fdr_bh)存在零 caller;選擇=裸 p≤0.05(orchestrator _apply_thresholds);前端 fdr_correction 幽靈開關(store 不送);`SelectionScope` 契約在、生產 0 使用。若拆刀必 1e 先。
- 1-align 交付凍結:`effective_horizon` 語意=Task 1.2 resolver 單一真相源,1e+1b 須複用(SPEC §N 交付義務)。
- 流程同本刀:偵察交委員(附 receipt)→Claude 全量自產判斷→SPEC+TODO→雙家族 adversarial→雙戳記 freeze→Codex 實作+Composer review→三方簽核。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員審查派工 `gate.sh dispatch --task-id --risk low --template "n/a:"`;實作派工 --risk high 附 --spec/--todo/--adversarial(過戳記機檢的 reconcile 檔)/--reconcile;codex exec 必接 `< /dev/null`。委員產出 register-output 才過 claim checker。
- 執行端產物不可信;接回只讀 diff+測試+摘要;執行端不得 git checkout tracked 共用檔。
