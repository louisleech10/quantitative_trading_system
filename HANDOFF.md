# Handoff
**Agent**: Claude | **Time**: 2026-06-26 | **Branch**: main

## ★進行中：IC Phase 1 第一刀 = 1-contract（契約層）實作
- **文件**：SPEC=`docs/IC_PHASE1_CONTRACT_SPEC.md`、TODO=`docs/IC_PHASE1_CONTRACT_TODO.md`（皆過雙家族 adversarial+reconcile，Frozen）。決策見 [[project_ic_phase1_decisions]]。
- **批次進度**：B0✅ B1✅ B2✅ B3✅(三方簽核PASS) B4✅ B5✅ B6✅ **全落地**。61 IC測試過,解耦0+腳本PASS。**最終 Composer 全diff review 中**(`bds0ujlz0`),過後即 commit+push。
- **B5/B6 修補**：B5 BLOCKED於export StreamingResponse測試hang→Claude套Codex診斷修法;B6 Codex根治export route(type=='bytes' StreamingResponse→buffered Response)。9 export errors=既有環境timeout(stash對照確認非回歸)。
- **B0**：`tests/golden/ic_phase1_contract/baseline_btc_1h.json`，config_hash `a384e6d22ca15fc639757cb3162e7cb3`(BTC/1h)，top50 deterministic 子集，sha256 `25aee97f...`。G1 deep-equal 須剔 `generated_at`。
- **B3 三方簽核**：4輪修補抓8真LEAK(L1-L6全閉)，`handoffs/20260626-ic-phase1-b3-FINAL-SIGNOFF.md`。教訓 [[feedback_adversarial_beats_signoff]]。
- **B3 殘留(B5/B6 必落實)**：① ICSplitAdapter 接線傳真實 symbol universe(allowed_symbols)；② expected_freq 從 timeframe 推導；③ G3 補 split_per_symbol golden；④ 契約 1a 才接 IC 主 pipeline。
- **B4**：`ICArtifactSchema`+`momentum/Analysis/ic_artifact_writer.py`+`create_ic_artifact_writer()`；Parquet+atomic+不接 result path；G2 全表 sha256(NaN/inf bit-level 保真)+O(page) 不載全表，Claude 自驗真。
- **接回鐵律**：每批 Claude 自驗 diff既有斷言防假綠 + 解耦grep=0 + 三方數據簽核(洩漏/值守恆) + Composer code review。
- **執行端注意**：Codex 派工須寫 `handoffs/<date>-<task>.md`，**勿覆寫根 HANDOFF**(已發生2次)。

## 維運/背景
- IC地圖入口 `handoffs/20260624-ic-map-00-INDEX.md`；記憶 [[project_ic_analysis_map]]。
- B0 清理：刪 orphan `ic_ingest_cache/BTCUSDT_1h_a384e6d2.h5`(全量中斷手補,provenance不可驗,資料品質>速度)。
