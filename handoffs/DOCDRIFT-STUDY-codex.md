# DOCDRIFT Study — Codex
Task-id: docdrift-study-codex | Date: 2026-07-12 | Scope: 唯讀研究（僅新增本交接）
## (1) Rule 5/6 裁定（最重要）
- 結論：canonical 7 條應採 CLAUDE.md／ARCHITECTURE.md「持續解耦要求」後段版本：1 momentum→api 禁依賴；2 跨 domain 用 Protocol；3 API service/route/ws 只經 factories/core；4 services 不互 import；5 config 依 layer/domain 有唯一 owner；6 momentum tests 不需啟動 run_api；7 API DTO 與 core contracts 不跨界。
- 理由：CLAUDE.md 明示治理以本檔+ORCH 為準；ARCHITECTURE.md:349-358 自己也採 Config/Test 版本；`check_decoupling_phase4.sh` 明確把 Rule 6 實作成 `pytest tests/momentum/Strategy/`，實跑 135 passed。
- `check_decoupling.sh` 不是 canonical 定義的可靠來源：其 R5 只查 `momentum -> api.core.config`（已被 R1 包含，不能證明「Config single source」）；其 R6 只查 service 屬性被賦值為 lambda，不能證明「無 callback/closure bypass」。
- singleton/callback 是仍有價值的額外 invariant，但不能冒名替換 canonical R5/R6；若要保留，應另列 Rule 8/9 或 named checks，且先精確定義。程式實況仍有 singleton/global（如 `chart_signal_service.py:57`、`signal_analysis_service.py:47`、`data_source_registry.py:69/289`）與 callback wiring（如 `task_manager.py:316`、`feature_factory_service.py:3638`），故 ARCH 前段「已修復／無 callback」按字面為假。
- Gate 實況：`bash scripts/check_decoupling.sh` FAIL：R2=5、R3=12、R4=1，R1/5/6/7 pass；所以 ARCH:154「全部已通過」亦漂移。`bash scripts/check_decoupling_phase4.sh` PASS（Strategy/Optimization scoped checks + 135 tests）。
## (2) 重疊逐項比對
- 數據真實性：非純冗餘，DEV_GUIDE:237 把「任何硬編碼數值／random 測試資料」絕對禁止；CLAUDE 只禁 hardcoded symbols/prices/metrics，並只對特定資料正確性 scope 要真 kline。repo 大量單元/性質測試使用 seeded `np.random`（例 `tests/test_cgsa_manifest_schema.py:29`），故 DEV 的 blanket ban 與現行測試策略、實況衝突；應區分 production truth、byte-faithful/regression、synthetic unit/property tests。
- DEV 自身也矛盾：:237 絕對禁硬編碼數值，但 :308-324 又允許明標示的示例數值；:327 要所有測試抓真 API，會導致非決定性/網路依賴，與可獨立測試原則衝突。
- 核心原則：Data truth、quality-before-speed、profile-before-optimize 與 CLAUDE 大致一致；CLAUDE 的 6 階 perf priority 更精確且限 Feature Factory/perf。隱藏漂移是 DEV:54 的「人工驗證 + Claude 實作」與現行多 agent/SPEC/adversarial/三方簽核流程過時，Ultra Think「初版不追求所有邊界」也不得覆蓋現行先驗假設與品質 gates。
- 程式標準：type hints、向量化優先、Numba hot path、Zustand、loading/error 等精神一致；DEV 提供較完整 how-to。其範例卻有 `any`（:1574/:1841）、原地 `data.sort()`（:1774）、硬編碼 URL（:1850）及把 `!data` 當 error（未分 empty/error），不完全符合 CLAUDE 的 typed responses/三態要求；應標示 legacy/example 並修例子。
## (3) 單一真相源提案
- 贊成「規範只有一份、大文件只留 rationale/how-to/pointer」，但反對把所有規則無條件塞進 CLAUDE.md：它已有 128 行且自動注入，過長會稀釋高風險條款；canonical rule IDs/短規範可在 CLAUDE，詳細定義與可執行 mapping 宜由版本化 governance registry（或 ARCH 的非重述 reference table）承載。
- Pointer 必須穩定（heading anchor/Rule ID）、CI 可檢查；scanner 顯示名稱、文件 Rule ID、實際 enforcement 應一對一。否則只是把文字漂移改成 pointer 失效／scanner 語義漂移。DEV/ARCH 可保留解釋與例子，但不得自稱 Authority 或重列規範狀態。
## (4) 其他漂移
- Factory map 過時：`rg -c '^def (create_|get_data_source_values)' momentum/factories.py` 得 79；ARCH:216-298 清單缺 `create_feature_preprocessor/reader/library`、multi-symbol/run-lifecycle、IC artifact/split/report、MCP、LSTM、drift/cache 等多個現有 factory。
- 技術棧漂移：ARCH 寫 Tailwind 3.x，`frontend/package.json` 為 Tailwind 4；實況另有 React 19/Vitest/Playwright 未列。requirements 實際 FastAPI 0.116.1、pandas 2.3.2、numpy 1.26.4；ARCH 的寬泛版本不是錯但失去盤點價值；程式 import xgboost，而 requirements 無 xgboost 條目，屬依賴清單漂移。
- 狀態漂移：ARCH:60 仍標「2026 Q1」；:1499-1558 宣稱 Feature Factory UI/Granular 已實作，:1804-1810 又列 Feature Factory 管理介面待開發；:1897 仍把 OptimizationTaskService 寫 Singleton、:1902 寫 WebSocket callback，直接反證前段 R5/R6 狀態宣稱。
## 待辦／阻塞／決策
- 待主委定案：採 canonical 7 + singleton/callback 額外 named invariants，並先修 scanner 語義與現況 violations，再降 pointer；本研究未改治理文件、程式或測試。阻塞：none。
- VERIFY：`bash scripts/check_decoupling.sh` FAIL（R2 5/R3 12/R4 1）；`bash scripts/check_decoupling_phase4.sh` PASS（135 tests）；其餘證據由上述 `rg`/逐檔讀取取得。
