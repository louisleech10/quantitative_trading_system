# DECOUPLE-SCAN2 TODO　(v2 / DRAFT / 基於 docs/DECOUPLE_SCAN2_SPEC.md r2 / 2026-07-14;r1 依三家 3B/13M 重寫)

## 階段 1 SPEC 索引(100% 覆蓋追溯)
| ID | SPEC 原文節錄(≤30字) | 本檔位置 |
|---|---|---|
| Task 1 | 「R4 AST 接管(含 routes 面+相對 import)」 | Task 1.1 |
| Task 2 | 「DataSourceEnum 死 import 刪除」 | Task 1.2 |
| Task 3 | 「api/models 掃描根+SUPPORTED_TIMEFRAMES 白名單」 | Task 1.3 |
| Task 4 | 「manifest 重戳輪(主委)」 | Task 1.4 |
| 矩陣 ≥12 | 「他 service/routes 三式/相對/nested/同名/__init__/self/多 alias/TYPE_CHECKING」 | Task 1.1 |
| M1-M3 | 「縮排相對/self 過寬/resolver 停用」 | Phase 測試 |
| CANARY-R4×3/CANARY-M | 四枚 canary | Task 1.1/1.3 |
| T1a-c/T2a-c/T3a-c/T4a-b | 驗證命令 | 各 Task |
- 合計:4 Task、驗證 11、mutation 3、canary 4。RISK-HIT: b。

## §0 全域規則與約束
- 解耦 7 條 canonical=CLAUDE.md;R4 零容忍無白名單;R2/R3 不弱化;R1/R5/R6(lambda)/R7 段不碰。
- **R4 唯一語意(凍結,不得自行變更)**:repo-relative path 解析 source module;相對 import resolve-then-check(禁沿用 `_node_targets` 對 level>0 的跳過);self 例外=絕對精確等值僅此一種;`__init__` 無豁免;package-level 一律紅;違規面=`api.services.<other>`+`api.routes.*`。
- **Triage 終判已定**:DataSourceEnum=刪死 import(零 manifest);SUPPORTED_TIMEFRAMES=白名單+relocate-to-core-constants P3 註記(codex 少數意見入 contract 欄)。
- 接管後冒既存紅 → 停手回報,不吞。
- 全套驗收:修前後同命令實跑,failing nodeid 集合 diff==空;禁口頭「既存」。
- 兩輪斷路器。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | Task 1.1→1.2→1.3 | 依序(1.1/1.3 同 scanner 檔) | 一次派工,各自 commit | 小-中 |

- B1 驗收 Gate:T1a-c/T2a-c/T3a-c+M1-M3+canary×4+全套 before/after diff==空。
- B1 後主委 Task 1.4 重戳 → scanner 全綠 → 收尾。
- 派工 prompt:「讀 docs/DECOUPLE_SCAN2_TODO.md §0+Task 1.1-1.3(冷啟動自足),依序實作+自跑驗證+receipt(handoffs/DECOUPLE-SCAN2-RECEIPT.md);**修前先跑大套件 baseline 存 receipt**;不跑 git commit(主委代);結構化收尾。」

## Phase 1

### Task 1.1 — R4 AST 接管(SPEC ref:Task 1)
- 輸入/輸出:輸入=scanner 基建+§0 唯一語意;輸出=R4 AST 檢查+shell 委派+矩陣。
- 實作要點:①每檔算 repo-relative source module(`api.services.foo`);②走訪全 Import/ImportFrom:相對(`node.level>0`)以檔案位置 resolve 成絕對 module 後檢(**新寫 resolver,不沿用 `_node_targets` 跳過行為**);③違規=目標 module 或其前綴 ∈ {`api.services.*`(≠self 精確等值), `api.routes.*`} 或包聚合(`from api import services|routes`/`import api.services`);④shell R4 段(L55-70 含 R4_ROUTES)刪除改委派 python exit code;⑤矩陣 ≥12(SPEC 清單逐項一測,TYPE_CHECKING 獨立測試,多 alias/分號行);⑥同名模組/nested package 案例(`api/services/sub/foo.py` vs `api/services/foo.py`)紅綠釘死。
- 修改檔案:`scripts/check_decoupling_imports.py`、`scripts/check_decoupling.sh`(R4 段)、`tests/decoupling/test_import_scanner.py`。
- 不可做:不動 R2/R3;無 R4 白名單;不碰 manifest;不沿用 `_node_targets` 處理 R4 相對。
- 邊界:(1) `from api.services import foo` in `foo.py` → 紅;(2) `from ...api import services` 越層 → resolve 後紅。
- 風險緩解:M1-M3+CANARY-R4×3。
- 驗證:**T1a** `bash scripts/check_decoupling.sh` 全綠 exit 0(冒既存紅→停手回報附清單);**T1b** `pytest tests/decoupling -q` 0 failed;**T1c** CANARY-R4 三式(api/services/ 臨放 `_r4_canary.py`:`from api import services`→紅;改 `import api.services.data_service`→紅;改 `from ..routes import config`→紅;刪→綠;各 stdout 入 receipt)。

### Task 1.2 — DataSourceEnum 死 import 刪除(SPEC ref:Task 2;依賴:無)
- 輸入/輸出:輸入=triage 終判;輸出=刪 `api/models/training_window_config.py:16` 一行。
- 實作要點:①刪 `from momentum.Indicators.types import DataSourceEnum`;②docstring L134 提及可留;③改前先 receipt:`python -c` 取 `TrainingWindowConfig`(等相關 model)`.model_json_schema()` 存 receipt → 改後重跑 `==`。
- 修改檔案:`api/models/training_window_config.py`(1 行)。
- 不可做:不改 `data_source` 欄型別/validator;不動 enum 本體/Indicators;不順手清 docstring 以外任何東西。
- 邊界:(1) schema 修前後 `==`(receipt 兩份);(2) 刪後任何 ImportError → 停手回報。
- 風險緩解:schema 等值 receipt。
- 驗證:**T2a** `grep -c "DataSourceEnum" api/models/training_window_config.py` 輸出 ≤`1`(僅 docstring);**T2b** schema 等值 receipt(`==` 斷言 stdout);**T2c** `pytest tests/api -q` 修前後 failing nodeid diff==空(baseline receipt 對照)。

### Task 1.3 — api/models 掃描根+白名單 1 條(SPEC ref:Task 3;依賴 1.1/1.2)
- 輸入/輸出:輸入=終判;輸出=R3 roots+api/models、manifest+1、矩陣擴充。
- 實作要點:①scanner R3 roots 加 `api/models`(scan 函式+CLI 預設);②manifest **併入既有表尾**(不開第三表)加一列:`momentum.FeatureEngineering.feature_config` | `SUPPORTED_TIMEFRAMES` | deny | committee/DECOUPLE-SCAN2 | 行為凍結 timeframe 驗證常數;relocate-to-core-constants P3(codex 少數意見);重複副本債另記;③戳記區清空(舊戳記失效=預期紅,receipt 記);④矩陣:models 內非白名單 momentum import 紅/`momentum.core.*` 綠;⑤CANARY-M:api/models/ 臨放 `_m_canary.py`=`from momentum.FeatureEngineering.feature_library import FeatureLibrary` → 紅;刪→綠。
- 修改檔案:`scripts/check_decoupling_imports.py`、`scripts/decouple_allowlist.md`、`tests/decoupling/test_import_scanner.py`。
- 不可做:不動 models 業務欄位;不開第三表;發現第 3 筆 momentum import → 停手回報。
- 邊界:(1) models import momentum.core/factories → 綠;(2) 戳記失效期 scanner 紅=正確。
- 風險緩解:CANARY-M+戳記機制。
- 驗證:**T3a** stub-verifier 函式呼叫真 repo → R3=0(歸因表:1 刪 1 放行,入 receipt);**T3b** `grep -cE "^\| momentum\." scripts/decouple_allowlist.md` 輸出 `10`;**T3c** CANARY-M 紅→綠 receipt。

### Task 1.4 — manifest 重戳輪(主委;依賴 B1)
- codex+composer 審新條目(白名單裁決+少數意見註記忠實)append v2 戳記。
- 不可做:主委不得自寫戳記。
- 邊界:(1) REJECTED → 改處置重審;(2) 戳記前紅=正確。
- 驗證:**T4a** `bash scripts/reconcile_stamps_check.sh scripts/decouple_allowlist.md` PASS+`bash scripts/check_decoupling.sh` 全綠 exit 0;**T4b** 篡改 mutation(改一字紅→還原綠)receipt。

### Phase 1 測試 + Phase Gate
- 單元:R4/models 矩陣 ≥12+TYPE_CHECKING 獨立測。整合:scanner 兩態。邊界:package-level/越層相對/nested 同名。
- mutation:M1=跳縮排/相對節點→相對測試 FAIL;M2=self-exclusion 改 basename→nested/同名測試 FAIL;M3=相對 resolver 停用→相對測試 FAIL(各實跑 receipt 後還原,還原後全綠)。
- Phase Gate:T1a-c/T2a-c/T3a-c/T4a-b+M1-M3+canary×4 全 PASS;大套件 before/after failing nodeid diff==空。

## 階段 3 自檢(0 FAIL)
- 追溯:4 Task/驗證 11/M3/canary 4 全對應 ✓。深度:語意凍結於 §0、檔案到位、邊界≥2、驗證可證偽 ✓。語義:1.1/1.3 同 scanner 檔依序;1.2 獨立;1.4 依賴 B1;無 forward dependency ✓;R4 接管涵蓋現行 shell 全語意(routes 面)✓。全棧:⋅跳過。錨點:✓。
## 階段 4 Frozen 前 handoff
SPEC=docs/DECOUPLE_SCAN2_SPEC.md TODO=docs/DECOUPLE_SCAN2_TODO.md FOCUS=r2 閉合(R4 語意唯一性/routes 不倒退/相對 resolver/triage 終判落地)
狀態:**Frozen**(2026-07-14 三家閉合全 FROZEN-OK,見 handoffs/DECOUPLE-SCAN2-ADV-{CODEX,COMPOSER,GROK}.md)
