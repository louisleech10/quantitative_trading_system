# DOCDRIFT-STUDY — grok（唯讀研究）
Task-id: docdrift-study-grok | Agent: Grok | Date: 2026-07-12  
Scope: 唯讀；**未改** CLAUDE.md / ARCHITECTURE / DEV_GUIDE / AGENTS / 腳本。  
Inputs: `handoffs/DOCDRIFT-MAP-CHAIR.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md` §解耦, `docs/DEVELOPMENT_GUIDE.md` 原則/數據真實性/代碼質量, `scripts/check_decoupling*.sh`, `momentum/factories.py`, 程式抽查。

---

## Q1 — Canonical 7 條解耦規則（最重要）

### 結論
**兩邊都不全；腳本也不是單一真相。** 歷史凍結線（REFACTOR V4 / ARCHITECTURE 主表 / `check_decoupling.sh` 血統）與現行憲法（CLAUDE / AGENTS / .cursorrules）在 **Rule 5、6 編號槽位**對撞；且 **ARCHITECTURE 文件內部自相矛盾**。若要以「可強制的執行邊界」定案，建議 **9 個獨立概念**（或「7 條核心 + 2 條配套」），**不要**再假裝只有一套 7 條。

### 三源對照

| # | CLAUDE.md / AGENTS / .cursorrules | ARCHITECTURE §154 主表 | ARCHITECTURE §357 演進表 | `check_decoupling.sh` 實際 | `check_decoupling_phase4.sh` 實際 |
|---|-----------------------------------|------------------------|--------------------------|----------------------------|-----------------------------------|
| 1 | momentum ↛ api | 同 | 同 | 全樹 `from api.` / `import api.` | 僅 Strategy + Optimization |
| 2 | Cross-domain → Protocol | 跨 Domain 禁 concrete import | Domain 內 Protocol | 跨 domain concrete import 掃描 | 僅查 strategy_backtest 有 IBacktestEngine/IPositionSizer |
| 3 | Services use factories | services 不直接建構 → factories | 同 | api services/routes/ws 只准 factories/core | 查 factories 有 create_backtest_engine / create_position_sizer |
| 4 | Services 互不 import | 同 | 同 | service↔service + service→routes | **未查** |
| 5 | **Config 單一來源**（core 或 api config） | **無 Mutable global singleton** | **Config 單一來源** | **momentum ↛ api.core.config** | **未查** |
| 6 | **Tests without run_api.py** | **無 callback/closure bypass** | **Test 配置隔離** | **api/services 禁 lambda monkeypatch** | **pytest tests/momentum/Strategy/** |
| 7 | DTO 不雙向 | 同 | 同 | api/models ↔ momentum/core | **未查** |

### 腳本強制項（地面真相，2026-07-12 實跑）

`bash scripts/check_decoupling.sh` → **EXIT 1**（非文件宣稱的全綠）：

| Script Rule | 結果 | 含義 |
|-------------|------|------|
| R1 | PASS | momentum 不 import api |
| R2 | **FAIL 5** | Analysis→FeatureEngineering concrete imports |
| R3 | **FAIL 12** | services/routes 直接 import FeatureEngineering concrete |
| R4 | **FAIL 1** | feature_factory_batch_adapters → feature_factory_service |
| R5 | PASS | = **config 邊界**（非 singleton） |
| R6 | PASS | = **lambda monkeypatch**（非 tests） |
| R7 | PASS | DTO 雙向乾淨 |

→ 腳本 **R5≈CLAUDE 系 Config 的子集**；腳本 **R6≈ARCHITECTURE 主表 callback 的子集**。  
→ phase4 的「Rule 6」= **CLAUDE 系 tests 獨立**。同一編號在兩腳本指不同東西。

### 歷史血統（為何 ARCHITECTURE 主表寫 singleton/callback）

`docs/Archived/DECOUPLING_COMPLIANCE_REVIEW.md`（2026-04-04，Baseline=ARCHITECTURE + REFACTOR V4）：

- R5: **mutable global singleton 跨 domain**
- R6: **callback/closure bypass**（lambda monkeypatch）
- Scanner: `check_decoupling.sh`

之後腳本 R5 被改成「momentum 不得 import api.core.config」（合規報告裡本是 singleton 段落的旁支），**規則文字沒跟著全域同步** → 今日三套敘事。

### 程式實況（對 5/6 兩族）

| 概念 | 實況 | 文件聲稱 |
|------|------|----------|
| Config 單一來源 / 禁 api.core.config in momentum | 腳本 R5 PASS；兩檔 config 路徑存在 | CLAUDE R5 ✅ 可驗證 |
| Mutable global singleton「已修復」 | **仍存在**：`api/services/*` 多處 `_instance`；`momentum/Analysis/strategy_registry.py` singleton；`case_storage` global instance | ARCHITECTURE §162「✅ 已修復」、§1392「無 Mutable global singleton」→ **過時/假綠** |
| lambda monkeypatch | 腳本 R6 PASS（api/services 無命中） | ARCHITECTURE R6 可對應腳本 |
| Tests without run_api | `tests/momentum/` 可獨立存在；phase4 跑 Strategy 子集 | CLAUDE R6；**全掃描器不查** |
| R2/R3/R4 全綠 | 今日腳本 **FAIL** | ARCHITECTURE 多處「0 violation / 完全遵守」→ **漂移** |

### 裁定建議（給主委定案用，本研究不改檔）

**A. 若 canonical =「執行邊界完整性」（歷史 REFACTOR 精神 + full scanner）**  
1 momentum↛api · 2 跨域禁 concrete · 3 api 只 factories/core · 4 service 不互 import · 5 **無 mutable singleton（跨邊界）** · 6 **無 callback/lambda bypass** · 7 DTO 不雙向  
+ **配套強制**（今日腳本/phase4 已做或 CLAUDE 強調）：Config 分層（momentum/core vs api/core）、pytest 不依賴 run_api。

**B. 若 canonical =「現行 agent 憲法」（CLAUDE/AGENTS 注入面）**  
1–4、7 同 · 5 Config 單一來源 · 6 Tests without run_api  
→ singleton / callback **仍是真實架構風險**，應降為「強化條款」或併入 R3/R4 敘事，**不可繼續用同一編號 5/6 與 ARCHITECTURE 主表對打**。

**C. 本研究推薦（避免再壓成矛盾的 7）**  
固定 **核心 7（採用 B 的編號，與 CLAUDE/注入一致）** + 明列 **附加 2（歷史 A 的 singleton + callback）**，並規定：

- **規範文字 SSOT** = CLAUDE.md  
- **強制 SSOT** = `scripts/check_decoupling.sh`（+ phase4 或合併）必須與規範文字 **同一編號語義**  
- ARCHITECTURE §154 主表改 pointer；§357 已偏 B，應刪掉 §154/§1387 的 singleton/callback 假狀態，或改寫成「附加條款 + 實況：singleton 仍存在」

**不可接受現狀**：ARCHITECTURE 同一檔 §154=A、§357=B、§492 又把 R5/R6 當 Config/可測（B），§1387 再寫回 A 且宣稱全綠。

---

## Q2 — 數據真實性 / 核心原則 / 程式標準：冗餘還是衝突？

### 結論總表

| 主題 | 關係 | 判定 |
|------|------|------|
| 數據真實性 | CLAUDE 一句 + 驗證保真度/三方簽核 vs DEV_GUIDE 長篇例子 | **精神一致；層級冗餘；少數軟衝突/過時** |
| 核心原則 | CLAUDE Non-Negotiable（Optimization Priority、Validate Assumptions…）vs DEV_GUIDE First Principle/質量優先 | **重疊少、互補多；非硬衝突** |
| 程式標準 | CLAUDE 短清單 vs DEV_GUIDE DRY/KISS/函式設計長文 | **純冗餘（教學 vs 憲法）；無對立規則** |
| 日誌/錯誤分類 | CLAUDE 極短；DEV_GUIDE 有專章 | **冗餘+CLAUDE 為 api-oriented**（momentum 用 momentum.core.logging — ARCHITECTURE 反模式 2 已寫） |

### 逐項

**2.1 數據真實性**  
- CLAUDE：No hardcoded symbols/prices/metrics；Feature Factory 禁合成 fixture、三方簽核、byte-faithful。  
- DEV_GUIDE §233：禁假數據/random/硬編碼閾值/示例當預設；要從 API/config 讀。  
- **一致**：禁 fake / 要真實來源。  
- **軟衝突 / 歧義**：  
  1. DEV_GUIDE 禁止「硬編碼閾值 `threshold=0.05`」範圍比 CLAUDE「symbols/prices/metrics」**更寬**；agent 可能把合法常數（數學 ε、協議固定值）也當違規。  
  2. DEV_GUIDE 測試範例仍寫 `fetch_real_data('BTCUSDT')` / 示例列表含 BTCUSDT——與「禁硬編碼 symbol」並陳，易誤導。  
  3. CLAUDE 的 **三方數據正確性 / 禁 sanitized fixture / receipt** 在 DEV_GUIDE **完全沒有** → 不是衝突，是 **DEV_GUIDE 落後於憲法**。  
- **判定**：主要冗餘；隱藏風險是「寬度不同 + 範例自打臉」，不是兩套相反真理。

**2.2 核心原則**  
- DEV_GUIDE：數據真實第一、質量>速度、性能與規範平衡、AI 驅動開發、Ultra Think 三步驟。  
- CLAUDE：Optimization Priority 1–6、Validate Assumptions、驗證保真度鐵律、三方簽核。  
- **無硬衝突**。CLAUDE 的 perf 排序（repeatability → stability → data quality → runtime…）比 DEV_GUIDE「先正確再優化」**更具體且 quant-specific**；若並讀，以 CLAUDE 為準（DEV_GUIDE 文首已 disclaimer 治理以 CLAUDE+ORCH）。  
- Ultra Think 流程僅 DEV_GUIDE：教學層，不構成規則對立。

**2.3 程式標準**  
- CLAUDE：type hints、向量化、Numba hot path、docstring 中文；TS 型別/Zustand/empty-loading-error/ResponsiveContainer；commit 前綴。  
- DEV_GUIDE §349+：DRY/KISS/函式長度/單一職責等長文。  
- **純冗餘 + 分工**：憲法摘要 vs how-to。未見「CLAUDE 要求 A、DEV_GUIDE 禁止 A」。

**2.4 Pre-commit / 解耦檢查**  
- CLAUDE Pre-Commit 寫 decoupling grep=0；Dev Commands 推 `check_decoupling_phase4.sh`（只蓋部分規則）。  
- 全量 `check_decoupling.sh` **今日紅** → checklist「通過」若指全量則 **文件樂觀**。屬操作漂移，非兩檔互相打架。

---

## Q3 — 「CLAUDE.md 規則唯一權威、大文件降 pointer」可行嗎？

### 結論
**可行，且應做；但附條件。反對「只改 pointer、不對齊強制腳本與執行端複本」。**

### 贊成（與證據）
1. **現況已半套用**：ARCHITECTURE / DEV_GUIDE 文首 disclaimer「治理以 CLAUDE + ORCH」；copilot-instructions **已 8 行 pointer**（2026-07-05）。  
2. **衝突主因是多份完整規則表**：§154 vs CLAUDE vs §357 vs §1387 — pointer 化直接消滅。  
3. Session 自動注入 CLAUDE → 當規則 SSOT 符合 agent 實務。  
4. ARCHITECTURE 應保留 **domain map / Protocol 機制 / 呼叫流 / Artifact Contract**（how 系統長什麼），不是再抄 7 條。  
5. DEV_GUIDE 應保留 **how-to 與範例**，規範句改「見 CLAUDE §…」。

### 反對 / 風險（需定案時處理）
1. **雙 SSOT 殘留**：規範在 CLAUDE、強制在 `check_decoupling.sh`。今日兩者 R5/R6 語義已分叉 → **只 pointer 不改腳本註解/規則對照表 = 假單一真相**。  
2. **AGENTS.md / .cursorrules 仍全文重述 7 條**（與 CLAUDE 同 B 組）— 若只動 ARCHITECTURE/DEV_GUIDE，執行端仍是第二憲法。建議改「規則見 CLAUDE；本檔只合約/紅線」。  
3. **Token 膨脹**：把 DEV_GUIDE 長規範全搬進 CLAUDE 會肥 session；正確做法是 **規範短表住 CLAUDE，長例子留 DEV_GUIDE**，不是整本合併。  
4. **ARCHITECTURE 的「狀態欄 ✅」不可 pointer 掉就完事** — 須刪除或改寫假綠（singleton 已修復、R2=0），否則 pointer 後殘留誤導句。  
5. **歷史審查 / Archived** 仍寫 A 組 7 條：可標 deprecated，避免 agent 讀 archive 當現行。

### 建議落地序（研究建議，非施工）
1. 先定 Q1 的 7+2 編號語義  
2. 對齊 `check_decoupling.sh` 註解與檢查項命名  
3. CLAUDE 寫定稿 7（+ 附加條款）  
4. ARCHITECTURE/DEV_GUIDE 刪重述表 → pointer  
5. AGENTS/.cursorrules 縮成 pointer 或「必須與 CLAUDE 同步」的單向生成說明  

---

## Q4 — 其他漂移

### 4.1 Factory map 過時（高）
| 指標 | 值 |
|------|-----|
| `momentum/factories.py` `create_*`/`get_*` | **87** |
| ARCHITECTURE §Factory 模式 code block | **53** |
| 實有、map 無 | **35**（含 create_lstm_engine, create_feature_reader, create_multi_symbol_runner, create_feature_factory_mcp, create_ic_reporter, create_label_generator, create_cv_validator, create_kline_cache, get_strategy_registry…） |
| map 有、實無 | **1**：`create_lightgbm_analyzer()` — 實作為 `create_model_trainer(engine="lightgbm")` |

### 4.2 Protocol 列表不完整（中）
ARCHITECTURE 示例列 IKlineReader / IIndicatorEngine / IModelTrainer / IOptimizationObjective / IBacktestEngine / IPositionSizer；  
`momentum/core/protocols.py` 另有 **IICAnalyzer, IBrowseRegistrar, IQualityComputer, ILabelGenerator, ICVValidator, IFeatureReader** 等未進主解耦節。

### 4.3 解耦「全綠」宣稱 vs 腳本（高）
- ARCHITECTURE：Rule1–7 ✅、0 violation、已修復 singleton。  
- 今日 `check_decoupling.sh`：**R2/R3/R4 FAIL**；singleton 程式仍在。  
- 驗證工具節仍寫未來 `python scripts/check_architecture_rules.py`（**檔不存在**）；真實工具是 `check_decoupling.sh` / `check_decoupling_phase4.sh`。

### 4.4 技術棧版本（中-低）
| 文件 | 實況抽查 |
|------|----------|
| Python 3.11 | 環境 default 曾見 3.9.6；以 venv 為準需另核（文件偏樂觀） |
| FastAPI 0.100+ | requirements `0.116.1`；一環境 import 見 0.121.0 |
| pandas 2.0+ / numpy 1.24+ | req pandas 2.3.x、numpy 1.26.4；import 見 numpy 2.0.2 可能混環境 |
| Next.js 15 | package.json `15.3.4` ✅ 大致準 |
| 開發狀態總覽「2026 Q1」 | 文檔 v7.0 已 2026-05-25 → 標題過時 |

### 4.5 Domain 目錄（低-中）
`momentum/Indicator/` 與 `momentum/Indicators/` **雙目錄並存**；ARCHITECTURE 目錄敘事易只認一個。

### 4.6 執行端複本
AGENTS / .cursorrules 與 CLAUDE 的 7 條 **同 B 組**（Config/Tests），與 ARCHITECTURE 主表 A 組衝突；三者對 agent 同時可見時，**以注入的 CLAUDE/AGENTS 勝出**，ARCHITECTURE 成為陷阱源。

### 4.7 copilot
已 pointer-only → **非漂移**，可作 pointer 化範本。

---

## 總結給主委

1. **Canonical 7 不是「選 CLAUDE 或 ARCHITECTURE 二選一就結束」**：歷史 A 與憲法 B 各有腳本半邊；**ARCHITECTURE 內部已分裂**；full scanner 今日 **未全綠**。推薦 **CLAUDE 編號（B）為規範 7 + 明示附加 singleton/callback**，腳本與狀態欄對齊。  
2. **數據/原則/程式標準**： overwhelmingly **冗餘與落後**，硬衝突少；最需處理的是 DEV_GUIDE 閾值寬度與 CLAUDE 三方/fixture 鐵律未同步。  
3. **單一真相源提案：贊成**；必須連動腳本語義 + 執行端複本 + 刪假綠狀態。  
4. **其他高價值漂移**：factory map −35/+1 stale、解耦全綠假象、不存在的 check_architecture_rules.py、Protocol/雙 Indicator 目錄。

---

## 證據清單（可複核）

| 證據 | 命令或路徑 |
|------|------------|
| 全量解耦掃描 | `bash scripts/check_decoupling.sh` → EXIT 1；R2=5 R3=12 R4=1 |
| 腳本 R5/R6 語義 | `scripts/check_decoupling.sh` L114–138 |
| phase4 R6=tests | `scripts/check_decoupling_phase4.sh` L54–58 |
| CLAUDE 7 條 | `CLAUDE.md` §The 7 Decoupling Rules |
| ARCH A 主表 | `docs/ARCHITECTURE.md` ~L154–164 |
| ARCH B 演進表 | 同檔 ~L349–359 |
| ARCH 再寫 A+全綠 | 同檔 ~L1387–1394 |
| 歷史 R5/R6 | `docs/Archived/DECOUPLING_COMPLIANCE_REVIEW.md` §2 |
| Factory 差集 | factories.py 87 vs map 53；缺 35；stale `create_lightgbm_analyzer` |
| Singleton 仍在 | `api/services/signal_analysis_service.py` 等 `_instance`；`momentum/Analysis/strategy_registry.py` |
| copilot 已 pointer | `.github/copilot-instructions.md` |

## 驗證
- ASSUMPTIONS_VERIFIED: 腳本 R5/R6 語意、今日 FAIL 計數、factory 差集、ARCHITECTURE 雙表衝突 — 均實跑/實讀  
- TESTS_RUN: `bash scripts/check_decoupling.sh` FAIL as above；未跑 phase4 pytest（避免長測；語意以讀腳本為準）  
- HANDOFF_ROOT: 未改 `HANDOFF.md`（研究產物寫本檔）  
- 治理文件: **0 修改**

STATUS: DONE
