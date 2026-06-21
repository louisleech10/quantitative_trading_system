# B5 v2 adversarial — Composer — 2026-06-22

## Verdict
**需修補後派工**。v2 已修正 v1「BatchGenerateRequest 有 date」事實錯誤；threading 鏈與 strict-window/B6 邊界清楚。仍剩 mock 清單錯檔、驗收命令漏跑、列數斷言 TF 混淆——Agent 照 SPEC 實作會假綠。

## Findings
- **[BLOCKING|High]** §A/TODO Task3.1 列 `test_multi_window_rolling` 錯檔：該檔僅 `_compute_single_window_reference`，零 `FeatureFactoryBatchService._compute_single`。遺漏 `tests/feature_engineering/test_multi_symbol_ic_first.py`（6 處 direct call）。Task3.1 驗收 `pytest tests/api/ -k batch` **不會跑** IC-first → 簽名改動 TypeError 漏抓。
- **[MAJOR|High]** §V「167天→~4009列」TF 混淆：4009≈1h strict 列數；使用者 bug 為 primary 12h（20352 全史）。整合測須明訂 TF、讀 manifest/metadata `row_count`、給容差；不能跨 TF 硬套 4009。
- **[MAJOR|High]** §V③ config_hash 批次=單 path 無專屬 Task/命令，僅 Gate 一句；易漏驗。應加 spy/hash equality pytest。
- **[MAJOR|Medium]** Task1.2 未指名 batch handler：實際 `page.tsx:244 handleGenerate` else `:262-268` 呼叫 `startBatchGeneration`；`:259` 是單 path `startGeneration`。
- **[MAJOR|Medium]** strict-window 非 look-ahead（`_layer0` :738-749 先 mask），但 rolling 缺前史→首段 NaN 偏多；B6 warmup 邊界已寫，§V 應要求「同 date 單 vs batch row_count/hash 一致」防 threading 偏差。
- **[MAJOR|Medium]** Task1.1 寫比照 `:225-226` 實為 `FeatureGenerationRequest`；應比照 `FeatureGenerateRequest :39-40` Field 風格。
- **[MINOR|Medium]** vitest「2 案例」無目標檔（現無 batch-date test）；`featureFactoryStore.ts:875`、`BatchGenerationPanel.tsx:87` 為無 caller 死碼 batch 入口。
- **無**：Pydantic→`/batch`→`model_dump` checkpoint→`execute_resume`→`_process_item_wave`→`run_in_executor:581-590`→`_compute_single`→`generate_features` 鏈完整；舊 checkpoint 缺 date→None 相容；`config_hash` 含 `_start_date/_end_date`(:3575-3576) None 不污染舊 cache。

## 被當成事實的未驗證假設
§A「8 mock 檔含 multi_window_rolling」→ **假**（應為 7 檔 + IC-first）。§A「4009=167天」→ **部分事實**（僅 1h，非 12h primary）。

ASSUMPTIONS_VERIFIED: BatchGenerateRequest:176-184 無 date；batch 未送 date(:262-268)；_compute_single 無 date；checkpoint `request_payload` resume；config_hash 含 date。TESTS_RUN: read-only rg/Read。FAILURES_SEEN: none。SCOPE_CHANGES: none。NUMERIC_OR_SCHEMA_IMPACT: none。

STATUS: DONE
