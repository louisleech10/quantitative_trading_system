# Handoff
**Agent**: Claude | **Time**: 2026-07-08 | **Branch**: main

## ✅ 剛完成:IC 1a 剩餘刀順序裁定(三方委員會一致+使用者裁定)
- 三方獨立偵察+提案:handoffs/IC1A-CUTS-ORDER-{claude,codex,composer}.md(gate register-output 已註冊,task-id IC1A-CUTS-ORDER)
- **裁定順序**:① 1-align 前瞻硬閘(大)→ ② 1e HAC+1b FDR 合刀「顯著性正確化」(大)→ ③ 1c Net IC 量綱(大)→ ④ 1d attribution 正名+NaN(中/大開工定)→ ⑤ 1f 空圖 schema+grouped 殘留(小-中,最後)
- **偵察關鍵事實(三方 receipt 交叉驗證)**:validate_alignment=NotImplementedError stub 零 caller(contracts.py:764);FDR adjust_multiple_comparisons 從未被呼叫+前端 fdr_correction 幽靈開關(store 不送);Net IC 量綱錯(net_ic_analyzer.py:34);attribution 真 OLS 存在但 _run_factor_exposure 不呼叫+fillna(0) 遍地;HAC 缺(statistical_validator.py:119 i.i.d. t-test);1f 巢狀 quantile_returns vs 前端頂層讀(恒空);**grouped_ic 崩潰已修(Phase 0 11507f5),移出清單**,殘留 schema/UX 面併 1f
- ROADMAP P0 已更新裁定;grouped_ic 殘留=IC-PERF(P1 正交 epic)

## ★進行中 = 1-align 前瞻硬閘:SPEC v3 已 Frozen(2026-07-09),待派實作
- **R1-R3 adversarial 全程**:R1 雙 REJECT(Codex 7B+Composer 6B)→v2 修全部→R2 Codex APPROVE/Composer 抓 v2 新洞(2.4 跨 dtype 交集恆空)→v3 加 D-4 同型化寫回→R3 雙 APPROVE;雙 RECONCILE-STAMP 機檢 PASS(handoffs/IC1A-ALIGN-RECONCILE.md)
- **SPEC 核心**:D-1 int64 秒相容/D-2 bar-ordinal oracle/D-3 兩段 freq/D-4 同型化寫回;Task 1.1 kernel+1.2 horizon resolver(修既存 purge lookahead)+2.1-2.6 六接線點;Golden 真 3sym data_cache 唯讀;M1-M7(M5 雙腿)
- **下一步**:派 Codex 實作 B1(Task 1.1+1.2)→Composer code review→B2(2.1-2.4)→B3(2.5-2.6)→三方數據正確性簽核。實作註記:尾端 NaN==lag 對完整軸驗(Codex R2 note)

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員審查派工 `gate.sh dispatch --task-id --risk low --template "n/a:"`;codex exec 必接 `< /dev/null`。委員產出 register-output 才過 claim checker。
- 執行端產物不可信;接回只讀 diff+測試+摘要;執行端不得 git checkout tracked 共用檔。
