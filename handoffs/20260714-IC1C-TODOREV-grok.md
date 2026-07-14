# IC1C-TODOREV — Grok Adversarial Review (TODO vs SPEC v1.0 Frozen)

- **Reviewer**: Grok (independent adversarial, family ≠ author)
- **Date**: 2026-07-14
- **SPEC**: `docs/IC1C_NETIC_SPEC.md` v1.0 Frozen (body stamp claimed ab910286; not re-hashed this review)
- **TODO**: `docs/IC1C_NETIC_TODO.md` (DRAFT, based on SPEC v1.0)
- **PLAN**: N/A
- **Focus**: 100% SPEC 覆蓋追溯(Task/M1–M10/G-OLD·NEW·NEW2/§U profile)、每 Task 深度、驗證可證偽、批次依賴、防假綠
- **Discipline**: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13
- **Scope constraint**: 除本檔外未改任何檔

## Verdict

**需修補後派工** — 覆蓋表宣稱 7/7·10/10·3/3 表面成立，但 **consumer-map 核心出口(ic_reporter/export)、Gate 命令可執行性、G-NEW2 可證偽程序** 三處 BLOCKING；冷啟動實作風險與 JSON/NaN 契約衝突為 MAJOR。  
不得以「Task 同名齊全」當 DONE。

---

## 覆蓋追溯總表（機械勾稽）

| SPEC 錨點 | TODO 落點 | 判定 |
|-----------|-----------|------|
| Task 0.1 / 1.1 / 1.2 / 1.3 / 2.1 / 2.2 / 3.1 | 同名 7 Task | **名目 7/7** |
| M1–M10 具名 test+probe | Phase1 T1/T3 + Phase2 T2/T4/T5 | **名目 10/10**（M4 前端 probe 命令有列） |
| G-OLD | Task 0.1 | 有，但進 orchestrator 路徑偏空殼 |
| G-NEW | Phase1 測試節 `--new` | 有；NaN/capacity 衝突未解 |
| G-NEW2 | Phase2/3 Gate 括號一句 | **程序空殼 → BLOCKING** |
| §U 三 SCHEMA_* | §0 + `test_schema_profiles` | 有；常數檔路徑與 SPEC 不一致 |
| 1c-FR 拆票 | §0 + Task1.2 不可做 | 有 |
| §C consumer #4 `ic_reporter.py` | **無任何 Task 修改檔** | **漏項 → BLOCKING** |
| §V 改寫 `test_export_formats.py` | 覆蓋表/Task 皆無 | **漏項（併入 consumer finding）** |
| §C #9 service NaN 路徑 :1198–1213 | 未點名（可能被 _to_json_compatible 吸納） | 風險 MAJOR 級旁註 |

---

## Findings

### ADV-GROK-1 [BLOCKING] 信心度 High — §C consumer `ic_reporter` + §V export fixture 零 Task

- **證據 (SPEC)**: §C #4 `momentum/Analysis/ic_reporter.py:150/:209/:570/:631-634/:773`(CSV 欄+alias+inject)；§V 改寫表含 `tests/momentum/test_export_formats.py:73-75,107-113`。
- **證據 (TODO)**: 全文無 `ic_reporter`、`export_formats`；覆蓋追溯行只列 Task/M/G/§U。
- **證據 (repo, VERIFY)**:
  - `rg '"net_ic"' momentum/Analysis/ic_reporter.py` → CSV deep column `"net_ic"`、`_safe_nested(..., "net_ic")` 仍讀已刪鍵。
  - `tests/momentum/test_export_formats.py:73-75` fixture 仍 `{"net_ic": 0.04}`。
- **反例 / 會怎麼失敗**: Phase1 刪 feature 級 `net_ic` 後，summary CSV 深欄恒空、detailed flatten 無 `cost_drag_return`；Phase3「全套 pytest tests/momentum/」必撞 export_formats 或靜默產出錯欄（假綠若只跑 T1/T2）。Agent 嚴格 scope「只改 Task 列檔」→ **合法完成 TODO 仍破壞 consumer**。
- **修法**: 新增 Task（建議 1.4 或併 1.1/1.2）明示改 `ic_reporter` 欄位→`cost_drag_return`（或 skipped/unavailable 語意）、alias 保留模組名 `net_ic_analysis` 但禁止再 inject 已死鍵；改寫 `test_export_formats` fixture+欄斷言，附「舊斷言為何錯」。
- **RECHECK**: `rg -n '"net_ic"' docs/IC1C_NETIC_TODO.md` 應出現 reporter 任務；`rg -n ic_reporter docs/IC1C_NETIC_TODO.md` ≥1。

### ADV-GROK-2 [BLOCKING] 信心度 High — Gate 命令 `mutation_probe_check.sh` 不可執行（假綠入口）

- **證據 (TODO)**: §B B1 Gate + Phase1 Gate：`` `bash scripts/mutation_probe_check.sh` PASS ``（無 test_path 參數）。
- **證據 (repo, VERIFY)**:
  ```text
  $ bash scripts/mutation_probe_check.sh
  用法: mutation_probe_check.sh <test_path> [<test_path>...]
  ```
  腳本 `[ $# -ge 1 ] || exit 1`。
- **反例**: 執行端照抄 Gate → 立即 fail 或「略過當 PASS」；若有人改腳本預設掃全樹又與「僅 Python M*」意圖不符。章程 B1.1 本意是**帶路徑真跑 probe**，現行 TODO 寫法使 M1–M3/M5/M6/M8–M10 閉合聲明不可證偽。
- **修法**: 寫死例如  
  `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/test_turnover_analyzer.py`  
  Phase2 另加 `tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py`；並重申 T4 不在此腳本、`npm run test -- NetICChart` 才閉 M4 前端 probe。
- **RECHECK**: 對修正後命令 `bash -n` + 乾跑 usage 不觸發；文件字面含 `test_path`。

### ADV-GROK-3 [BLOCKING] 信心度 High — G-NEW2 無產出/比對程序（可證偽空洞）

- **證據 (SPEC §G)**: G-NEW2(Phase2 後)僅驗 API 傳導等值，feature 級 schema 凍結不變。
- **證據 (TODO)**: Phase2 Gate「+G-NEW2(API 傳導等值…)」；Phase3「G-NEW2 重跑 byte 等值」——**無**腳本 flag、無 artifact 路徑、無 request payload 樣本、無比對命令、無 sha256 receipt 位置。G-NEW 有 `scripts/ic1c_freeze_baseline.py --new`；G-NEW2 無對等。
- **反例**: 執行端可宣稱「schema 沒變」而不留下可重放 receipt；幽靈成本 wiring（M4）可在 API 層被 tail 測到但仍缺 golden 傳導錨。Phase3「零 schema」依賴未定義基線 → 驗收空轉。
- **修法**: 定義 `g_new2.json`+sha256：同 fixture、`cost_enabled=true,cost_bps=7`（或 10）經 **API/service 同步等價路徑**（或 document 的 TestClient 入口）dump feature 級 dict，vs G-NEW COST_ENABLED byte/鍵集合；列明確命令與失敗條件。
- **RECHECK**: TODO 出現 `g_new2` 路徑 + 一條可 copy-paste 命令。

### ADV-GROK-4 [MAJOR] 信心度 High — Task 1.2 驗收在 T2，但 Phase1/B1 Gate 不跑 T2

- **證據 (SPEC Task 1.2)**: 驗證 `pytest tests/api/test_ic_deep_analysis.py -k net_ic`。
- **證據 (TODO)**: Task1.2 驗證=`test_net_ic_e2e_unavailable`(T2)；Phase1 Gate 僅  
  `pytest tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/test_turnover_analyzer.py`；  
  B1→B2 列 M1–M3/M5/M6/M8–M10 Python，**未含 T2 e2e**。
- **反例**: B1 可在 orchestrator 仍誤傳第三參/未接 profile 時，靠 T1 unit 綠過 Gate（若 1.2 改動極薄且未單測 orchestrator）。批次依賴「1.2 完成」名存實亡。
- **修法**: B1 Gate 加 orchestrator 級測試（T1 內 `test_run_net_ic_*` 或提前最小 T2 collect-safe 用例）；或明示 1.2 的 T2 屬 B2 hard gate 並把 Task 移 Phase2（與 SPEC 文意對齊需改 SPEC 或 TODO 一致化）。
- **RECHECK**: B1 Gate 命令字串含 `net_ic_e2e` 或 orchestrator 測試路徑。

### ADV-GROK-5 [MAJOR] 信心度 High — Task 0.1 冷啟動不足：fixture≠orchestrator 可跑狀態

- **證據 (TODO Task0.1)**:「載 `ic_api_real_kline` → 跑 orchestrator `net_ic_analysis` 模組」。
- **證據 (repo)**: `_run_net_ic` 依賴 `self._report["summary_table"]` + `turnover_analysis`（`ic_filter_orchestrator.py:1946-1956`），**不是**直接吃 kline fixture；fixture 只建 features/labels h5。
- **反例**: Agent 呼叫 `batch_analyze` 自造 summary 與「orchestrator 全量輸出」不等價；或硬跑 full deep pipeline OOM/超時/路徑漂移 → baseline 不可復現，G-OLD 作廢。
- **修法**: 給準入口偽碼（最小：構造 `summary`/`turnover_data` 自 fixture 衍生 IC 統計 **或** document 的 `run_deep_analysis(force_modules=...)` 完整前置）；列確定性 seed/排序；`json.dumps(..., allow_nan=False)`；skipped 人工注入 API。
- **RECHECK**: Task0.1 含可搜尋函式名 + 輸入結構示例。

### ADV-GROK-6 [MAJOR] 信心度 High — capacity `NaN` vs §G「JSON 禁 NaN」+「不動 estimate_factor_capacity」互斥

- **證據 (TODO 1.1)**: capacity 沿用 `estimate_factor_capacity` 並加 `calibration:uncalibrated`；不可做：不動計算邏輯。
- **證據 (SPEC §G)**: JSON 禁 `inf`/`NaN` 字面值。
- **VERIFY**:
  ```text
  estimate_factor_capacity(0.5, None) → estimated_capacity_usd: nan
  json.dumps(..., allow_nan=False) → ValueError
  json.dumps 預設 → {"estimated_capacity_usd": NaN}  # 非法 JSON 字面
  ```
- **反例**: G-NEW dump 要嘛寫出 NaN 字面（違 §G），要嘛腳本私自 null 化（未寫入 TODO → agent 分叉）。`test_finite_invariants` 若只盯 cost 裸欄，capacity 成漏網假綠。
- **修法**: 在 batch 輸出邊界規定 non-finite capacity 欄 → `null`（計算函式可不動，**序列化/組 dict 時轉換**）；T1 斷言 capacity 子樹可 JSON strict；或擴充 finite 不變式含 capacity。
- **RECHECK**: TODO 明示 `allow_nan=False` + capacity null 規則。

### ADV-GROK-7 [MAJOR] 信心度 High — Task 1.3 測試改寫範圍漏刀

- **證據 (TODO 1.3)**: 只點 `tests/momentum/test_turnover_analyzer.py:60-66`。
- **證據 (repo)**: 同檔 `test_net_ic_proxy_nan_turnover`(:92-96) 亦呼叫 `compute_net_ic_proxy`。
- **反例**: 刪 proxy 後 pytest 收 T3 仍紅；或只刪 60-66 測、留 nan 測 → 執行端「超 scope」困惑 / 假綠若 Gate 未收該檔全量（Gate 有收檔但未列改寫理由表）。
- **修法**: 改寫表列齊全部 `compute_net_ic_proxy` 測試；刪除或改 cost_drag 語意（nan→SKIP/0 規則對齊 §T）。
- **RECHECK**: `rg compute_net_ic_proxy tests/` 在 Task 完成定義下==0。

### ADV-GROK-8 [MAJOR] 信心度 Medium — `config_override` 拒收面是否覆蓋雙入口未釘死

- **證據 (SPEC/TODO)**: `config_override.net_ic_analysis` 整節 reject。
- **證據 (repo)**: `DeepAnalysisRequest.config_override` 與 `ICAnalyzeRequest.config_override` 並存；`_build_config_override` deep-merge deep 節；`_build_deep_module_override` 末尾 `**(request.config_override or {})` 可蓋掉 typed 注入。
- **反例**: 只在 nested `net_ic` validator 拒、主 request `config_override` 仍塞 `net_ic_analysis:{default_cost_bps:5}` → 5bps 幽靈復活（M5 靜態 grep 過但 runtime override 活）。
- **修法**: Task2.1 寫明兩入口皆 422；測試矩陣含 `ICAnalyzeRequest.config_override` 與 `deep_analysis_config.config_override`；override merge **不得**在 typed net_ic 之後覆蓋同鍵。
- **RECHECK**: 具名測試字串含兩 path。

### ADV-GROK-9 [MAJOR] 信心度 Medium — TODO §0 解耦子集不完整（範本 §2）

- **證據 (範本)**: TODO §0 應含解耦 7 條相關子集；缺 → MAJOR。
- **證據 (TODO §0)**: 僅「`check_decoupling.sh` 全綠、`momentum/` 不 import `api/`、services 走 factories」——對應 R1/R3 片斷；未點 R2 Protocol、R4 服務互引、R5 config 單源（雖 Task 有改 schema/yaml）、R6 測不靠 run_api、R7 DTO 不跨界（types/models 同構有做但未升成 §0 約束）。
- **反例**: 執行端在 api service 直 import analyzer class、或 DTO 塞進 momentum contracts「圖省事」。
- **修法**: §0 補 7 條 checklist 一行表 + 本票適用/N/A。
- **RECHECK**: §0 出現 Rule 1–7 或明確 N/A。

### ADV-GROK-10 [MINOR] 信心度 High — §U SCHEMA 常數路徑與 SPEC 漂移

- **證據 (SPEC §U)**: 常數落 `tests/momentum/Analysis/test_net_ic_schema_profiles.py::SCHEMA_*`。
- **證據 (TODO)**: 常數在 T1/`test_schema_profiles` 同檔。
- **反例**: 多檔複製 SCHEMA 不一致 → equality oracle 分裂。
- **修法**: 跟 SPEC 單檔 export，或改 SPEC（凍結後應改 TODO 對齊 SPEC）。
- **RECHECK**: 路徑字串單一來源。

### ADV-GROK-11 [MINOR] 信心度 Medium — request 欄名 `net_ic` vs 模組鍵 `net_ic_analysis` 易接錯線

- **證據 (TODO 2.1/2.2)**: `DeepAnalysisRequest.net_ic` + store `net_ic:{...}`；override 注入鍵仍為 `net_ic_analysis`。
- **反例**: 前端把成本欄塞進 `modules` 或 `config_override.net_ic`；TypeScript 與 Python 欄名漂移。
- **修法**: 給一則 JSON 請求示例（完整 deep-analysis body）。
- **RECHECK**: TODO 含 fenced JSON example。

### ADV-GROK-12 [MINOR] 信心度 Medium — Task2.2 grep `0.1` 過寬（假紅/假綠）

- **證據 (TODO)**: `grep -n "useState(5)\|0.1" NetICChart.tsx` 無假值殘留；同 Task UI step 0.1 bps。
- **反例**: 合法 `step={0.1}` 觸發 grep 紅 → agent 刪 step 或放寬 grep；SPEC 原意是 **turnover fallback 0.1**。
- **修法**: 對準 `turnover ?? 0.1` / `useState(5)` / 硬編 scenario 陣列。
- **RECHECK**: 驗證命令含更特異 pattern。

---

## §1 十類速檢

| # | 類 | 結論 |
|---|-----|------|
| 1 | 矛盾/互斥 | 有：capacity NaN vs JSON 禁；1.2 驗收 vs B1 Gate；SCHEMA 路徑 (ADV-6/4/10) |
| 2 | 漏項/E2E | **有 BLOCKING**：reporter/export (ADV-1)；G-NEW2 程序 (ADV-3) |
| 3 | 不可測驗收 | **有 BLOCKING**：mutation 命令 (ADV-2)；G-NEW2 (ADV-3)；0.1 路徑 (ADV-5) |
| 4 | 可疑 quant | 無新增；B-strict/§T 與已驗證混減 bug 一致（見下 FACT） |
| 5 | 過度工程 | 無 |
| 6 | OOM/並行 | 無（邊界目錄並發/OOM 仍未勾，可接受 N/A） |
| 7 | Cache | 無本票 cache 面 |
| 8 | API/型別/相容 | MAJOR：override 雙入口 (ADV-8)；欄名 (ADV-11) |
| 9 | 測試品質 | MAJOR：proxy 次測漏 (ADV-7)；reporter 無紅測 |
| 10 | Agent 可執行性 | BLOCKING Gate 命令；MAJOR 0.1 深度 |

## 被當成事實的未驗證假設（§0 挑戰前提）

| 陳述位置 | 當事實？ | 本審判定 |
|----------|----------|----------|
| 覆蓋「7/7 Task + consumer 完整」暗示 | 是（覆蓋行自信） | **assumption 且為假** — reporter 未落 TODO（ADV-1） |
| `mutation_probe_check.sh` 無參可 PASS | 是（Gate 字面） | **fact-checked 假**（ADV-2） |
| fixture→orchestrator 可直接凍 G-OLD | 是 | **assumption 未驗證**；依賴 _report 前置（ADV-5） |
| capacity 可原樣進 G-NEW JSON | 暗含 | **fact-checked 衝突**（ADV-6） |
| 混減公式 bug | SPEC FACT-RECEIPT | **fact-verified**：`compute_net_ic(0.05,1.5,10)→net_ic=0.047`（本機 2026-07-14） |
| `quantile_turnover` 已含雙腿、禁 ×2 | SPEC FACT | 未在本輪重讀 turnover 本體；**沿用 SPEC 三家 receipt，標 assumed-by-SPEC**（非本 TODO 回歸點） |
| `scripts/ic1c_freeze_baseline.py` 將存在且 `--new` 足夠 | 是 | 腳本目前不存在（預期新建）；**API 面 G-NEW2 仍缺** |

## 每 Task 深度摘要（冷啟動可寫碼？）

| Task | 檔案/函式精度 | 偽碼/公式 | 不可做 | 驗證可證偽 | 冷啟動 |
|------|---------------|-----------|--------|------------|--------|
| 0.1 | 腳本名有；orchestrator 入口空 | 弱 | 有 | sha256 有、路徑弱 | **勉強/高風險** |
| 1.1 | 強（函式+公式+profile+summary） | 強 | 強 | T1 具名強 | **可** |
| 1.2 | 中（行號有；e2e 不進 Gate） | 中 | 有 | T2 延後 | **可改碼、難收口** |
| 1.3 | 中（漏次測） | 中 | 有 | grep+T3 | **可**（測表需補） |
| 2.1 | 強；override 面需加硬 | 中 | 有 | T2/T5 具名 | **可** |
| 2.2 | 強（多檔+刪假值） | 中 | 有 | vitest+M4 | **可** |
| 3.1 | 弱-中（docs 目標飄） | 弱 | 有 | grep+build | **可**（文案） |

## 批次依賴

- B0→B1→B2→B3 順序與 SPEC Phase 一致，合理。
- B1 合併 1.1+1.2+1.3：同意（數值核心同批），但 **1.2 缺少同批可證偽 Gate**（ADV-4）。
- B2 API+前端同批：同意（防幽靈開關），M4 雙端 probe 命令有寫 — 佳。
- B3 零 schema：依賴未定義 G-NEW2（ADV-3）。

## 防假綠

| 機制 | TODO | 評 |
|------|------|-----|
| 改寫附理由 | phase25/default_cost/proxy 有 | reporter/export **缺** |
| mutation probe | 具名齊 | **Gate 命令廢** → 閉合可被跳過 |
| golden+canonical | G-NEW 有 | capacity/NaN、G-NEW2 洞 |
| 禁放寬斷言 | §0 有 | 佳 |
| 真 kline fixture | §0 有 | 佳 |

## 空殼掃描（範本 §2）

- Task 1.1 / Phase1 測試矩陣：**非空殼**（具名函式+oracle 數值 0.0015）。
- G-NEW2、mutation Gate 無參、Task0.1 orchestrator 鏈：**邏輯空殼**（有標題無程序）。
- §RISK/§A/§G 在 SPEC 已落實；TODO 繼承 B-strict 正確。

## 建議修補優先序（不重寫 TODO 全文，僅方向）

1. 補 consumer Task（reporter + export 測試）  
2. 修正所有 `mutation_probe_check.sh` 呼叫簽名  
3. 寫實 G-NEW2 freeze/compare  
4. 對齊 1.2↔B1 Gate；補 0.1 偽碼；capacity JSON 規則；proxy 全測；override 雙入口  

---

## 結構化收尾（機器可掃）

```
ASSUMPTIONS_VERIFIED:
  - compute_net_ic(0.05,1.5,10)->0.047 (mixed-dimension bug live)
  - mutation_probe_check.sh requires >=1 test_path (usage exit)
  - capacity NaN fails json.dumps(allow_nan=False)
  - ic_reporter still hardcodes feature key "net_ic"
  - test_turnover has 2 proxy tests (60-66 and 92-96)
TESTS_RUN:
  - python one-liner NetICAnalyzer.compute_net_ic / estimate_factor_capacity + json.dumps
  - bash scripts/mutation_probe_check.sh (usage only)
  - rg net_ic across momentum/Analysis, tests, api, frontend (read-only)
FAILURES_SEEN: none (review-only)
SCOPE_CHANGES: none — output only handoffs/20260714-IC1C-TODOREV-grok.md
NUMERIC_OR_SCHEMA_IMPACT: none (no code changes)
```

STATUS: DONE

TODO-REVIEW: REJECT(3 BLOCKING)
