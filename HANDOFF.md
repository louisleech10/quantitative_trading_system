# Handoff
**Agent**: Claude | **Time**: 2026-06-26 | **Branch**: main

## ✅ 上一任務:IC Phase 1 第一刀 = 1-contract(契約層)— 完成、已 commit+push (`e857834`)
- **6 批次全落地**:契約 DTO(SplitPlan/RowMaskPlan/SelectionScope/AlignmentSpec/ICArtifactSchema/eval_status)+ 洩漏紅線(validate_split_integrity/pair/split_per_symbol/ic_split_adapter)+ Parquet artifact(ic_artifact_writer)+ API 版本化(ic_response_v2 flag/?schema_version=2/ICResultV2Response,flag-off byte 不變)+ export route 根治。
- **三方數據簽核 PASS**:adversarial 自挑戰抓 8 真 LEAK(confirm-review 全漏),4 輪修補全閉;L4 allowlist 權威防線。SPEC+TODO 過雙家族 adversarial。61 測試過,解耦 0+腳本 PASS,真實 kline。
- **文件**:docs/IC_PHASE1_CONTRACT_{SPEC,TODO}.md;留痕 handoffs/20260626-ic-phase1-*;b3-FINAL-SIGNOFF 記三方。
- **教訓**:[[feedback_adversarial_beats_signoff]](簽核式 review 會漏洩漏洞,adversarial 才現形)。

## ★下一個任務:IC Phase 1 — 1a train/test split（接線+其餘正確性 kernel）
- **1a 必落實 1-contract 殘留(否則紅線不生效)**:① ICSplitAdapter 接線傳真實 symbol universe(allowed_symbols);② expected_freq 從 timeframe 推導(gap fail-closed 生效);③ 契約接進 IC 主 pipeline(目前 opt-in 未接,正確性僅保護經 adapter 路徑)。
- **後續 Phase 1 kernel**(CONVERGED §Phase1):1-align 前瞻偏誤硬閘 → 1b FDR 接線 → 1c Net IC 量綱 → 1d factor_attribution → 1e HAC/block bootstrap → 1f 靜默空圖。
- **G1 baseline**:`tests/golden/ic_phase1_contract/` 用 `freeze_baseline.py` 本地再生(52MB v1 payload 不進 git,config_hash a384e6d2);baseline 依賴測試 clean checkout 會缺檔→ 1a 宜改 skip-if-absent 或縮小 golden。
- **MINOR(Composer)**:contracts private helper 暴露(1a 收斂 public);export_analysis 對 dataclass 預存 TypeError 風險。
- **★1a 起手式(新 session)**:級別判斷=**大**(命中 (b) 跨模組 + (d) ML 正確性/防洩漏,接線會動 IC 主流程 caller)→ 走完整管線(短文件→manifest→SPEC→雙家族 adversarial→TODO→gate→派工→接回三方簽核)。先讀 `docs/IC_PHASE1_CONTRACT_{SPEC,TODO}.md`(契約介面)+ `handoffs/20260626-ic-phase1-b3-FINAL-SIGNOFF.md`(殘留清單)+ phasing-CONVERGED §Phase1(1a 範圍)。**接線=讓既有正確性紅線真的保護主流程,不是新功能**。三方數據簽核(split/leakage,真實 kline)鐵律仍適用。

## 背景/維運
- IC 地圖入口 `handoffs/20260624-ic-map-00-INDEX.md`;記憶 [[project_ic_analysis_map]] [[project_ic_phase1_decisions]]。
- 執行端派工須寫 `handoffs/<date>-<task>.md`,勿覆寫根 HANDOFF(本次發生 2 次)。
