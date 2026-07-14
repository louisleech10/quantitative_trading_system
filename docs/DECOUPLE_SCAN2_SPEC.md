# DECOUPLE-SCAN2 — R4 AST 接管+api/models 掃描根補洞 — SPEC

> 來源 PLAN/診斷：ROADMAP DECOUPLE-TRIAGE-2 ②　|　日期：2026-07-14(r2:三家 adversarial 3 BLOCKING/13 MAJOR 全吸收;triage 終判入 §C)　|　對應 TODO：docs/DECOUPLE_SCAN2_TODO.md

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：小-中。
- **命中高風險原則**：(b) 跨模組共用路徑(scanner+manifest)。零數值/ML。
- RISK-HIT: b
- §G 於 §N;adversarial r1 已跑,r2=修訂。

## §A 假設與待使用者確認（r2 依 ADV-CODEX-4/ADV-COMPOSER-0/1、ADV-GROK-1 修正 receipt）
- **已驗證事實**(receipt ×4)：
  - FACT-RECEIPT: `grep -rnE "^from momentum\.|^import momentum\.|    from momentum\.|    import momentum\." api/models --include="*.py" | grep -v "momentum.core|momentum.factories"` → **2 筆**(`feature_factory_models.py:12` SUPPORTED_TIMEFRAMES;`training_window_config.py:16` DataSourceEnum)(r1 命令漏 `-E` 已更正;三家覆核僅此 2 筆,含 import/縮排形式)。
  - FACT-RECEIPT: `sed -n '55,70p' scripts/check_decoupling.sh` → R4 現行=無 caret 的 `grep 'from api\.services\.'`+`R4_ROUTES` 段(`from api.routes.`);**縮排 `from` 其實抓得到**(r1「不抓縮排」敘述不實,composer/codex 實證);**真盲區=`import api.services.x`/`from api import services` 包聚合/相對 import**。
  - FACT-RECEIPT: codex/grok 實查 `_node_targets()` 對 `node.level>0`(相對 import)直接 return → **沿用現 helper 會靜默跳過相對 import**(Task 1 必修點)。
  - FACT-RECEIPT: 三家實查 `training_window_config.py` → `DataSourceEnum` 僅 L16 import+L134 docstring 提及;`data_source` 欄實型別 `str`,無 validator 用 enum → **死 import**。`SUPPORTED_TIMEFRAMES` 在 `feature_factory_models.py` 3 個 validator 真實消費;另 `api/models/case_models.py` 等有重複清單副本(債,另記)。
- **待使用者確認**：無(使用者 2026-07-14 已裁定開票;triage 由委員會終判,見 §C)。
- **已確認結果**：`2026-07-14 使用者:「開一張小-中票(R4 AST 接管+api/models 掃描與 triage,同管線),pending 5 筆改綁 Optuna epic 退場」`。

## §C 約束+triage 終判(r2)
- 收緊不放鬆:**R4 AST 接管必須涵蓋現行 shell 全部語意**——services 檔 import `api.services.<other>` **與 `api.routes.*`**(ADV-CODEX-1/GROK-3:漏 routes=倒退);只准多抓。
- **R4 自身模組排除=唯一可實作語意**(ADV-CODEX-2):以 repo-relative path 解析每檔完整 source module(如 `api.services.foo`);violation 判定前,**相對 import(`from .bar import X`/`from . import bar`)先 resolve 成絕對 module 再檢**(不得沿用 `_node_targets` 跳過);self 例外=解析後目標 module==自身 module 的精確等值,**僅此一種**;`__init__.py` 無特殊豁免;package-level `from api.services import x`/`from api import services` 一律紅。
- **Triage 終判**(三家裁決 2026-07-14):
  - `DataSourceEnum` → **改 code:刪 `training_window_config.py:16` 死 import**(三家一致 DISAGREE 白名單;docstring L134 提及可留);**零 manifest 變更**。
  - `SUPPORTED_TIMEFRAMES` → **白名單**(composer/grok AGREE,2:1 多數;symbol 級僅此常數,contract=行為凍結 timeframe 驗證常數);**codex 少數意見存檔**:正解=清單本體遷 `momentum/core/constants.py`+`feature_config` re-export+models 改 import core → 記入 manifest contract 註記為 **relocate-to-core-constants P3**;重複副本(case_models 等)列債入 ROADMAP。
- manifest 變更=+1 條(共 10)→ 重戳輪必跑。
- R4 無白名單(canonical 零容忍);掃描接管後若冒既存紅(TYPE_CHECKING/相對互引)→ **停手回報當場 triage,不吞不豁免**。

## §G Golden / Baseline
- 移 §N。

## §P Phase 與依賴

### Phase 1 — 四 Task(1→2→3 依序同 scanner 檔;4=主委)

**Task 1 — R4 AST 接管(含 routes 面+相對 import)**
- 目標:R4 由 AST 接管,全形式覆蓋且不倒退。檔案:`scripts/check_decoupling_imports.py`、`scripts/check_decoupling.sh`(R4 段)、`tests/decoupling/test_import_scanner.py`。
- 改法:①依 §C 唯一語意實作(repo-relative module 解析/相對 import resolve-then-check/self 精確等值/`__init__` 無豁免);違規目標=`api.services.<other>`+`api.routes.*`+包聚合形式;②shell R4 段(含 R4_ROUTES)刪除改委派;③矩陣 ≥12 案例:他 service from/import/包聚合(`from api.services import x`+`from api import services`)/routes 三式(絕對/聚合/相對)/相對 `from .bar import X`+`from . import bar`/nested package/同名模組/`__init__`/self 綠/import api.models 綠/多 alias/TYPE_CHECKING 紅(獨立測試)。
- 驗證:`bash scripts/check_decoupling.sh` 全綠 exit 0(既存紅若冒出→停手回報);`pytest tests/decoupling -q` 0 failed;CANARY-R4 三式(`from api import services`/`import api.services.data_service`/`from ..routes import config`)各紅、刪後綠(stdout 入 receipt)。
- 邊界:(1) `from api.services import foo` 出現在 `foo.py` → 紅(package-level 一律紅,self 例外僅絕對精確式);(2) 相對 import 越層(`from ...api import services`)→ resolve 後紅。
- 不可做:不動 R2/R3;無 R4 白名單;不碰 manifest。

**Task 2 — DataSourceEnum 死 import 刪除(triage 終判)**
- 目標:刪 `api/models/training_window_config.py:16`。檔案:僅該檔一行(docstring 可不動)。
- 驗證:`grep -c "DataSourceEnum" api/models/training_window_config.py` ≤1(僅 docstring);`pytest tests/api -k "training_window or strategy_config" -q` 0 failed(無匹配則跑 `pytest tests/api -q` 對照 baseline 無新紅);model JSON schema 修前後 `==`(python 實跑 `TrainingWindowConfig.model_json_schema()` 等價類,receipt 兩份)。
- 邊界:(1) schema/欄位零變(str 型別本就未用 enum);(2) 若刪後任何 import error → 停手回報(表示有隱藏 caller,receipt 附)。
- 不可做:不改 `data_source` 欄型別;不動 enum 本體;不碰 Indicators。

**Task 3 — api/models 掃描根+SUPPORTED_TIMEFRAMES 白名單**
- 目標:R3 roots+`api/models`;manifest +1 條。檔案:`scripts/check_decoupling_imports.py`、`scripts/decouple_allowlist.md`(**併入既有表尾**,不開第三表——單源,composer ADV-7 裁決)、矩陣擴充。
- 改法:①R3 roots 加 api/models;②manifest 加 `momentum.FeatureEngineering.feature_config`(symbols=`SUPPORTED_TIMEFRAMES`;module_import=deny;owner=`committee/DECOUPLE-SCAN2`;contract=「行為凍結 timeframe 驗證常數;**relocate-to-core-constants P3**(codex 少數意見);重複副本債另記」);戳記區清空=預期紅;③矩陣:models 內非白名單 momentum import 紅/`momentum.core.*` 綠;CANARY-M(feature_library from 式)紅→刪→綠。
- 驗證:stub-verifier 函式呼叫真 repo → R3=0(歸因表:2 筆中 1 刪 1 放行);`grep -cE "^\| momentum\." scripts/decouple_allowlist.md` 輸出 `10`;CANARY-M receipt。
- 邊界:(1) models import momentum.core/factories 綠;(2) 發現第 3 筆 → 停手回報。
- 不可做:不動 models 業務欄位;不開第三表。

**Task 4 — manifest 重戳輪(主委;依賴 Task 3)**
- codex+composer 審新條目(含少數意見註記忠實度)append v2 戳記(新 hash)。
- 驗證:`reconcile_stamps_check.sh` PASS;`check_decoupling.sh` 全綠 exit 0;篡改 mutation receipt。
- 邊界:(1) REJECTED → 改處置重審;(2) 戳記前紅=正確。
- 不可做:主委不得自寫戳記。

## §V 驗證策略與邊界測試目錄(r2 依 ADV-CODEX-3/7 擴充)
- mutation ×3:M1=R4 跳縮排/相對節點 → 相對/縮排測試 FAIL;M2=self-exclusion 改 basename 比對(過寬)→ nested/同名測試 FAIL;M3=相對 resolver 停用(回 `_node_targets` 舊行為)→ 相對測試 FAIL。實跑 receipt 後還原。
- **全套驗收防口頭歸因**(ADV-CODEX-7):targeted suites 必 0 failed;大套件 `pytest tests/api tests/momentum -q` 修前修後同命令實跑,receipt 列 before/after 的 passed/failed/errors 計數+failing nodeid 集合 diff==空(新增失敗=0),禁「口頭既存」。
- canary ×2(R4 三式/models);manifest 篡改 mutation(既有機制)。

## §R 回退
- 各 Task 獨立 commit;Task 2 revert=恢復一行 import;manifest 受戳記保護。

## §N N/A 登記
- §G:N/A — 掃描器側+1 行死 import 刪除+1 條 manifest,零數值/行為(Task 2 有 schema 等值 receipt 承擔)。
- §V 數值邊界:N/A。
- 重複 timeframe 清單副本(case_models 等):N/A 於本票——列債入 ROADMAP(與 relocate-to-core-constants 同票處理)。
