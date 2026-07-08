# Handoff
**Agent**: Claude | **Time**: 2026-07-08 | **Branch**: main

## ✅ 剛完成:IC 1a 剩餘刀順序裁定(三方委員會一致+使用者裁定)
- 三方獨立偵察+提案:handoffs/IC1A-CUTS-ORDER-{claude,codex,composer}.md(gate register-output 已註冊,task-id IC1A-CUTS-ORDER)
- **裁定順序**:① 1-align 前瞻硬閘(大)→ ② 1e HAC+1b FDR 合刀「顯著性正確化」(大)→ ③ 1c Net IC 量綱(大)→ ④ 1d attribution 正名+NaN(中/大開工定)→ ⑤ 1f 空圖 schema+grouped 殘留(小-中,最後)
- **偵察關鍵事實(三方 receipt 交叉驗證)**:validate_alignment=NotImplementedError stub 零 caller(contracts.py:764);FDR adjust_multiple_comparisons 從未被呼叫+前端 fdr_correction 幽靈開關(store 不送);Net IC 量綱錯(net_ic_analyzer.py:34);attribution 真 OLS 存在但 _run_factor_exposure 不呼叫+fillna(0) 遍地;HAC 缺(statistical_validator.py:119 i.i.d. t-test);1f 巢狀 quantile_returns vs 前端頂層讀(恒空);**grouped_ic 崩潰已修(Phase 0 11507f5),移出清單**,殘留 schema/UX 面併 1f
- ROADMAP P0 已更新裁定;grouped_ic 殘留=IC-PERF(P1 正交 epic)

## ★下一站 = 1-align 前瞻硬閘(大管線起手)
- 走完整大管線:SPEC+TODO(gate artifact token)→ 雙家族 adversarial → reconcile 雙 RECONCILE-STAMP → freeze → **Codex 實作 + Composer review**(2026-07-08 使用者指示切換)→ 三方數據正確性簽核
- Scope 核心:實作 validate_alignment(Feature_t vs Target_{t+lag} 硬閘)+接進 orchestrator 縱向 label reindex 路徑(:754-756 無 lag 不變量檢查);cut2 oracle 只蓋 cross_sectional kline 路徑
- SPEC 事實依據直接引用三方偵察檔 receipt(新分工:偵察交委員,Claude 只抽驗分歧點——已存記憶)
- Composer 提醒:1-align 若只包裝 cut2 oracle 可降小,但傾向維持中/大(longitudinal/外來 labels/多 horizon caller-map+red-on-break)

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員審查派工 `gate.sh dispatch --task-id --risk low --template "n/a:"`;codex exec 必接 `< /dev/null`。委員產出 register-output 才過 claim checker。
- 執行端產物不可信;接回只讀 diff+測試+摘要;執行端不得 git checkout tracked 共用檔。
