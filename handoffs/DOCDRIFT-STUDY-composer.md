# DOCDRIFT 研究報告 — Composer
Task-id: docdrift-study-composer | Agent: Cursor Composer | Date: 2026-07-12  
模式: 唯讀研究，**未改任何治理文件**。

---

## 題 1：Rule 5/6 衝突 — canonical 7 條解耦規則裁定

### 結論

**規範層（normative）canonical 7 條應採 CLAUDE.md / AGENTS.md / .cursorrules 同一套（Config + Tests 佔位 5/6）。**  
**執行層（enforcement）目前分裂：`check_decoupling.sh` 的 R5/R6 語意對齊 ARCHITECTURE §150（config-import 邊界 + lambda bypass），`check_decoupling_phase4.sh` 的 R6 對齊憲法（standalone pytest）。**  
**ARCHITECTURE.md 單檔內至少有三套 Rule 5/6 語意，且「全部已通過驗證」與 2026-07-12 實跑腳本不符。**

建議定案後的 **canonical 7 條**：

| # | 規則 | Quick Check |
|---|------|-------------|
| 1 | `momentum/` 不得 import `api/` | `grep -r "from api\." momentum/` → 0 |
| 2 | 跨 Domain → Protocol 注入 | 無跨 domain 具體 import；`momentum/core/protocols.py` |
| 3 | `api/` 僅透過 `factories.py` / `momentum.core` 接觸引擎 | `check_decoupling.sh` R3 |
| 4 | `api/services/` 互不 import | `check_decoupling.sh` R4 |
| 5 | **Config 單一來源**：引擎用 `momentum/core/config.py`，API 用 `api/core/config.py`；`momentum/` **不得** import `api.core.config` | `check_decoupling.sh` R5 |
| 6 | **測試不依賴 `run_api.py`**：`pytest tests/momentum/` 可獨立跑 | `check_decoupling_phase4.sh` R6 語意 |
| 7 | DTO 不跨層：`api/models/` ↔ `momentum/core/contracts.py` 無雙向依賴 | `check_decoupling.sh` R7 |

**不佔 5/6 號位、但應保留的補充約束**（原 ARCHITECTURE §150 主表）：
- 無 mutable global singleton 跨 Domain 共享（實務上散見 `service_providers.py`、batch service DI singleton 註解）
- 無 callback/lambda monkeypatch 繞過邊界（`check_decoupling.sh` 現標為 R6，**應與憲法 R6 脫鉤重命名**，避免雙重語意）

### 證據

**四源 Rule 5/6 對照**

| 來源 | Rule 5 | Rule 6 |
|------|--------|--------|
| CLAUDE.md L105-106 | Config single source | Tests without `run_api.py` |
| AGENTS.md / .cursorrules L78-79 | 同左 | 同左 |
| ARCHITECTURE.md §150 L162-163 | 不得有 Mutable global singleton | 無 callback/closure bypass |
| ARCHITECTURE.md §349 L357-358 | Config 單一來源 | Test 配置隔離 |
| ARCHITECTURE.md §489-492 範例 | Config-driven（Rule 5） | Pipeline 獨立可測（Rule 6）— **第三套語意** |
| `check_decoupling.sh` L114-137 | `momentum/` 不得 `from api.core.config` | `api/services/` 不得 lambda monkeypatch |
| `check_decoupling_phase4.sh` L54-57 | （未檢） | `pytest tests/momentum/Strategy/` 獨立 |

**腳本實跑（2026-07-12）**

```bash
bash scripts/check_decoupling.sh
# Rule 1 PASS | Rule 2 FAIL (5) | Rule 3 FAIL (12) | Rule 4 FAIL (1)
# Rule 5 PASS | Rule 6 PASS (lambda) | Rule 7 PASS
```

與 ARCHITECTURE §154「全部已通過驗證 / ✅ 0 violation」矛盾。

**程式實況摘錄**
- R2 違規：`momentum/Analysis/*` → `momentum.FeatureEngineering.*`（5 處，如 `kline_cache.py:29`）
- R3 違規：`api/services/*`、`api/routes/*` 直接 import `momentum.FeatureEngineering.*`（12 處）
- R4 違規：`feature_factory_batch_adapters.py:9` import `feature_factory_service`
- R5 通過：`momentum/` 無 `api.core.config` import
- 憲法 R6（standalone test）：`phase4` 只驗 `tests/momentum/Strategy/`，非全 `tests/momentum/`

**裁定理由**
1. **自動注入憲法** + 執行端合約（AGENTS/.cursorrules）已統一 Config/Tests → 新人/agent 預設讀這套。
2. **ARCHITECTURE §349**（V1→V3 演進表）與憲法一致，§150 主表更像 REFACTOR V4 舊快照。
3. **腳本標號與憲法不一致**是工具漂移，不是再發明第七套規則；定案後應改腳本註解/編號，而非改憲法去遷就 `check_decoupling.sh` 的 R6=lambda。

---

## 題 2：數據真實性 / 核心原則 / 程式標準 — 冗餘還是衝突？

### 結論

| 重疊項 | 判定 | 隱藏衝突？ |
|--------|------|-----------|
| 數據真實性 | **主體冗餘**（憲法 1 句 vs DEV_GUIDE §233 長文+範例） | **有邊界衝突**：DEV_GUIDE 範例將「任何硬編碼閾值」一律禁止；憲法只列 symbols/prices/metrics。DEV_GUIDE §327-345 暗示單元測試也應真實子集；憲法/SCAR_LEDGER 對 Feature Factory 禁合成 fixture，但 repo 大量 unit test 用 synthetic — **若把 DEV_GUIDE 當全域規範會與現況衝突**。 |
| 核心原則 / Validate Assumptions | **冗餘+互補**：憲法 §86-93（實測>假設、三方簽核、byte-faithful）；DEV_GUIDE §31（First Principle、Ultra Think 三步） | **無直接矛盾**；DEV_GUIDE 偏流程教學，憲法偏治理鐵律。DEV_GUIDE 未收錄 Optimization Priority / 三方簽核 — **缺口非衝突**。 |
| 程式標準 | **冗餘**：憲法 §111-115 摘要；DEV_GUIDE §349+（DRY/KISS/函式長度/Zustand 等） | **無實質衝突**；DEV_GUIDE 較細（如函式 <50 行）憲法未否定。 |
| Optimization Priority | 僅憲法 + 執行端合約 | DEV_GUIDE 核心原則寫「質量優先於速度」與 Priority #4 runtime — **相容**，非衝突。 |

### 證據

- CLAUDE.md L80-81：`No hardcoded symbols, prices, or metrics.`
- DEV_GUIDE.md L237-243：禁止假數據、虛擬數據、**硬編碼數值（如 threshold = 0.05）**、示例默認值
- CLAUDE.md L92-93：Feature Factory 三方簽核、禁合成 fixture、`data_cache/feature_klines/kline_cache.h5`
- DEV_GUIDE.md L330-345：測試應使用真實數據子集，反例為 `pd.DataFrame` 假價格
- CLAUDE.md L111-115 vs DEV_GUIDE.md L349+：type hints / 向量化 / Numba / Zustand — 後者展開，前者為 checklist 子集

---

## 題 3：「CLAUDE.md 為規則唯一權威、大文件降 pointer」可行性

### 結論

**可行，且與現有制度方向一致（copilot-instructions 已 8 行 pointer；CLAUDE L126 已寫「治理以本檔+ORCH 為準」）**，但需先完成題 1 定案並處理下列反對點，否則 pointer 會指向仍含錯誤 Rule 5/6 的 ARCHITECTURE §150。

### 支持理由
1. 憲法已 session 注入，最短路徑降低 agent 讀錯表。
2. ARCHITECTURE / DEV_GUIDE 的價值在 **機制與範例**（Protocol 列表、factory map、呼叫流程、Ultra Think），非重複規範表。
3. 可減少 ARCHITECTURE 內部三套 Rule 5/6 並存問題。

### 反對 / 風險（需在定案時處理）
1. **腳本標號與憲法 R6 不一致**：pointer 到 CLAUDE 後，開發者跑 `check_decoupling.sh` 仍看到「Rule 6 = lambda」— 需同步腳本註解或拆成 `check_decoupling.sh` + `check_test_isolation.sh`。
2. **憲法篇幅短**：singleton/callback 若降為 pointer-only 可能從主視野消失 → 建議在 CLAUDE 增「補充約束」小節（≤5 行），而非僅靠 ARCHIVED。
3. **ARCHITECTURE 狀態聲稱**：「✅ 0 violation」需改為「見 `scripts/check_decoupling.sh`」動態表述，否則 pointer 後大文件仍誤導。
4. **HANDOFF 維護權**：執行端合約仍指向 HANDOFF；單一真相源需明確 **CLAUDE = 規範、HANDOFF = 任務狀態、ORCH = 流程**，三者不互搶。
5. **DEV_GUIDE 測試數據範例**：降 pointer 時須加 scope 句（「通用 unit test 允許 minimal synthetic；Feature Factory 真實路徑見憲法三方鐵律」），避免與憲法 SCAR 條款衝突。

---

## 題 4：其他漂移

### 結論

除 Rule 5/6 外，至少五類漂移：**ARCHITECTURE factory 清單過時**、**合規狀態過時**、**ARCHITECTURE 內部 Rule 語意不一致**、**技術棧細節未同步**、**治理文件交叉引用過時**。

### 證據

**Factory map（§211-298 vs `momentum/factories.py`）**

```bash
# ARCHITECTURE 列出的 create_*（去重）vs 實際 factories.py
# ARCH 獨有（文檔有、repo 無獨立 factory）:
#   create_lightgbm_analyzer  → 已併入 create_model_trainer(engine="lightgbm")
#   create_chat_service, create_agent_orchestrator, create_new_engine  → §349 未來項，尚未實作
# 實際有、ARCH 清單未列（部分）: 80 個 create_*/get_data_source* vs ARCH ~47 項
#   create_feature_factory_mcp, create_run_lifecycle_manager, create_ic_reporter,
#   create_lstm_engine, create_kline_cache, create_drift_analyzer, ...
```

**合規狀態漂移**
- ARCHITECTURE L154-164、L1387-1394：宣稱 Rule 1-7 全通過
- 實跑 `check_decoupling.sh`：R2/R3/R4 失敗（見題 1）

**ARCHITECTURE 內部**
- §150 表：singleton / callback
- §349 表：config / test isolation（= 憲法）
- §492 範例：config / pipeline testability

**技術棧**
- ARCH L88-98：Next.js 15、TS 5.x — `frontend/package.json` 為 `next: 15.3.4`、`react: ^19.0.0`（React 19 未記載）
- 後端 ML 棧描述大致仍準；factory 域劃分未涵蓋 IC reporter、run lifecycle、MCP 等新增域

**交叉引用過時**
- ARCHITECTURE L487：仍要求更新 `.github/copilot-instructions.md`，但該檔 L1-8 已標 **淘汰**，指向 CLAUDE.md

---

## 建議定案順序（供主委）

1. 採 **題 1 canonical 7 條**（憲法 Config/Tests 佔 5/6；singleton+callback 為補充約束）。
2. 改 `check_decoupling.sh` 註解：現 R6 lambda → 補充約束編號；憲法 R6 併入 phase4 或擴展全 `tests/momentum/`。
3. 再執行單一真相源：ARCH §150 規則表 → pointer；DEV_GUIDE 規範段 → pointer + scope 句。
4. 刷新 ARCH factory map / 合規狀態 / copilot 引用。

---

## 驗證命令摘要

```bash
bash scripts/check_decoupling.sh
bash scripts/check_decoupling_phase4.sh   # 需 venv；未在本次全跑
grep -E '^def create_|^def get_data_source' momentum/factories.py | wc -l   # → 80
comm 比對 ARCHITECTURE create_* 與實際（見題 4）
```

---

*產出：`handoffs/DOCDRIFT-STUDY-composer.md`*
