# Handoff
**Agent**: Claude | **Time**: 2026-07-06 | **Branch**: main

## ★制度層總審查 epic — 實質完成(A 憲法 + B 腳本 + U-13 慣例)

### 進度
- **Phase A**(憲法重構+合約補齊)✅ commit(0e974a1 等)。
- **Phase B**(治理腳本 U-9/12/14/15)✅ commit f86a714+push:兩層 sync+選層反向檢查、gate DENY 落 audit、pre-commit index-only 尾空白 auto-fix、gate.sh 用法模板+新 dispatch.sh。governance 140 passed/9 pre-existing。
- **Phase C**:**U-13**(批次戳記慣例+同檔並發序列化)✅ 本次寫進 ORCH §戳記後。**U-20/U-21 裁決本身=先別做**(U-20 累積 violation 證據再機械化;U-21 維持 scorecard 不裁定)→ 屬長期觀察項,非待辦。
- **結論:制度層 epic 的可實作項全數完成**;U-20/21 為 standing 監測項。

### IC 測試定向重驗 已辦(2026-07-06,含 Codex adversarial review)
- **成果**:IC Phase0/1 targeted 測試 **49 passed / 4 skipped / 0 failed**(起初 45/6;VERIFY:20260706T052454Z-ic-reverify-final-20260706,exit0)。
- **修法**:`ic_analysis_service.py` fail-closed 守衛收斂到 registry 解析路徑——`config_hash` 未註冊時,只有 features_path **也**缺席才 `raise run not found`;呼叫端明確給 features_path(golden/artifact replay)不再被擋。run-selector「靜默錯 run」保證不變(features_path 缺席仍 fail-closed)。**證據**:2 golden byte-equal frozen baseline + 2 hermetic 契約測試(fail-closed 保留/relaxation 生效)+ mutation(還原硬守衛→relaxation 測試轉 fail)。
- **run_selector 4 測試**:改 `is_materialized` skip-guard——12h 特徵資料 gitignored,乾淨 checkout 缺 → 誠實 skip(非造綠);契約覆蓋由上述 hermetic 測試(不需真資料)補回。
- **Codex review**:[P1](skip 掩蓋契約)已補 hermetic 測試閉合。殘留 **[P2 另立]**:給了 features_path 卻與 config_hash 不一致時未校驗一致性(pre-existing,我的改把它擴到未註冊 hash);不擋本刀,另開小 epic。
- **⚠️ 未重凍舊-run goldens**:1a_cut1 golden 沿用**已存在的** input .h5(a384e6d2,present),未把 registry 對準現行 `4a8a0b37…`。run_selector 若要實際執行(非 skip)仍需生成 12h 資料——屬 provisioning,未做。

### ★下一站 = IC 1a 第二刀(cross_sectional `analyze_cross_sectional` 防洩漏)
- 續 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖;P0.5 grouped_ic 止血。目標=79 全合成 IC 測試換端到端真實資料。**建議新 session 起跑**(context 乾淨)。
- 前置皆就緒:IC SPEC conformance ✅、targeted 重驗 ✅、FF 測試資料(3 sym×1h+12h、max_lag 後、`data_cache/features/`)✅。

### 技術債(另記,不擋)
- governance 9 pre-existing 紅(b4/b5/r7:舊 spec/fixture 不符演進後 template_check/D-1/provenance)。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt 或檔載出處。委員派工帶 --task-id+--output,產出後 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要,diff 既有測試斷言防假綠;**執行端不得 git checkout tracked 共用檔**。
