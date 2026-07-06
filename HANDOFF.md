# Handoff
**Agent**: Claude | **Time**: 2026-07-06 | **Branch**: main

## ★制度層總審查 epic — 實質完成(A 憲法 + B 腳本 + U-13 慣例)

### 進度
- **Phase A**(憲法重構+合約補齊)✅ commit(0e974a1 等)。
- **Phase B**(治理腳本 U-9/12/14/15)✅ commit f86a714+push:兩層 sync+選層反向檢查、gate DENY 落 audit、pre-commit index-only 尾空白 auto-fix、gate.sh 用法模板+新 dispatch.sh。governance 140 passed/9 pre-existing。
- **Phase C**:**U-13**(批次戳記慣例+同檔並發序列化)✅ 本次寫進 ORCH §戳記後。**U-20/U-21 裁決本身=先別做**(U-20 累積 violation 證據再機械化;U-21 維持 scorecard 不裁定)→ 屬長期觀察項,非待辦。
- **結論:制度層 epic 的可實作項全數完成**;U-20/21 為 standing 監測項。

### ★新 session 起點 = IC 測試定向重驗(中任務,命中 a+d → 完整管線+另一方 review)
- **緣由**:SPEC conformance 後重跑 51 個 IC Phase0/1 測試(VERIFY:20260706T044007Z-ic-phase01-rerun-20260706,exit1)= **45 passed / 6 failed**。45 個屬核心正確性(phase0_golden/timeaxis/crash/decay/1a_split/1a_oos/split_adapter,用已提交 fixture)。
- **6 紅根因**(實查非猜):全是 `run not found` — goldens/run_selector 釘死在**舊 run**(1a_cut1=`a384e6d22…`、run_selector=12h `1c4b825…`/`90f586…`),現 registry 只有**現行資料集 `4a8a0b37…`**(batch「FF for IC Analysis Test」);輸入 .h5 gitignored 故乾淨 checkout 湊不齊。
- **⚠️疑似回歸待裁**:`ic_analysis_service.py:180-184`(run-selector 硬化 commit 643c5c2)即使給了明確 `features_path`,只要 config_hash 未註冊就先 `raise run not found` → **把 1a_cut1 golden replay 路徑弄斷且無人察覺**(receipt 紀律晚於此)。**是回歸(服務該認 features_path) vs 設計(測試須 seed registry)= 委員會裁,勿 solo**。
- **任務範圍**:① 釐清 643c5c2 fail-closed 性質 ② 依現行資料集 `4a8a0b37…` 重凍 goldens/run_selector fixture(或註冊舊 run)。目標=IC 測試全綠且每項有真 receipt。**建議新 session 起跑**(context 乾淨)。
- **原 IC 路線圖**(重驗後接回):第二刀 `analyze_cross_sectional` 防洩漏;續 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖;P0.5 grouped_ic 止血。目標=79 全合成 IC 測試換端到端真實資料。
- **已完成前置**:IC SPEC conformance pass ✅ commit(4 份過 template_check;RISK-HIT+FACT-RECEIPT 補齊,受查發現 4 份皆對應已落地工作 PHASE0=11507f5/1a=done/RUN_SELECTOR=643c5c2/CONTRACT=ic_split_adapter.py,FACT-RECEIPT 全 2026-07-06 當日重跑無湊假)。FF 測試資料就緒同上。

### 技術債(另記,不擋)
- governance 9 pre-existing 紅(b4/b5/r7:舊 spec/fixture 不符演進後 template_check/D-1/provenance)。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員派工帶 --task-id+--output,產出後 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要,diff 既有測試斷言防假綠;**執行端不得 git checkout tracked 共用檔**。
