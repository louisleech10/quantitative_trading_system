# IC1C-TODOREV-R3 — Composer 閉合重驗

> SPEC=`docs/IC1C_NETIC_SPEC.md` §U **v1.1 補裁**(負 turnover→SKIPPED+capacity 子鍵;banner 仍 v1.0 Frozen,內文已落 §U L36-37) | TODO=`docs/IC1C_NETIC_TODO.md` r3 | RECONCILE T-F17~T-F26 | reviewer=composer | 2026-07-14

## Verdict：r2 兩 BLOCKING 已閉合；r3 殘留 1 內部矛盾 → 需 r4 一字修後重審

r3 已落地 T-F17~T-F26(RECONCILE r2 補記全 ACCEPT)；**SPEC §U v1.1 補裁(composer concur)**：負 turnover→`SCHEMA_SKIPPED`/`negative_turnover`、禁 `max(0,·)`、`capacity` 允許 `calibration:"uncalibrated"` 子鍵——與 Task 1.1/§0/G-NEW oracle 一致。**不蓋 RECONCILE 戳記**(見末行 REJECT)。

---

## SPEC §U v1.1 補裁核可

| 條目 | 判定 | 證據 |
|------|------|------|
| 負 turnover→SKIPPED(`negative_turnover`) | **APPROVE** | SPEC §U L36；TODO §0/Task 1.1 L54/G-NEW L94 同向 |
| 禁 `max(0,·)` 靜默 clamp | **APPROVE** | SPEC §U L36；Task 1.1 ④、G-NEW canonical 重算 L94 |
| `capacity` 允許子鍵(`calibration` 等) | **APPROVE** | SPEC §U L37；Task 1.1 L54 `calibration:"uncalibrated"`；解 ADV-COMPOSER-11 |
| 版本標頭 | **NOTE(非 BLOCKING)** | SPEC L3 仍寫 v1.0 Frozen；§U 內文已 v1.1——建議 r4 同步 banner,不阻 B0 |

---

## r2 BLOCKING 反例重跑（R2-1 / R2-2）

| ID | r2 嚴重度 | 判定 | r3 證據 / 反例重跑 |
|----|-----------|------|-------------------|
| ADV-COMPOSER-R2-1 | BLOCKING | **CLOSED** | Task 0.1 L40：`pop("oc_return")`+`summary["hl_range"]` NaN；列全 7 欄 `FEATURE_NAMES`、明示無 obv/ad。`rg FEATURE_NAMES tests/fixtures/ic_api_real_kline.py`→含 oc_return/hl_range,無 obv/ad |
| ADV-COMPOSER-R2-2 | BLOCKING | **CLOSED** | §0 L12+Task 1.1 L54+Task 2.1 L102 統一偽碼：`cost_bps is not None` 一律驗域+`cost_enabled` 另驗非 None；T2 L124 含 `{false,NaN}` 422。`rg 'cost_enabled and' docs/IC1C_NETIC_TODO.md`→0(僅 `cost_enabled and cost_bps is None` 合法句) |

---

## r2 MAJOR 重判（R2-3 / R2-4 / R2-5）

| ID | r2 嚴重度 | 判定 | r3 證據 |
|----|-----------|------|---------|
| ADV-COMPOSER-R2-3 | MAJOR | **STILL-OPEN** | Task 1.1/G-NEW/SPEC v1.1 已去 clamp；**Task 1.3 L77 仍寫「②負 turnover clamp」**——與 v1.1 直接矛盾(見 R3-1) |
| ADV-COMPOSER-R2-4 | MAJOR | **CLOSED** | §B B3 L32 含 `pytest tests/phase26/ -q`；解 ADV-COMPOSER-0b |
| ADV-COMPOSER-R2-5 | MINOR | **CLOSED** | Task 3.1 L131 釘死 `docs/API_SPECIFICATION.md`；解 ADV-COMPOSER-15 |

---

## r1 殘留 MAJOR/MINOR 快判（r3 相關項）

| ID | 判定 | 說明 |
|----|------|------|
| ADV-COMPOSER-0b | **CLOSED** | phase26 入 B3 Gate(T-F24) |
| ADV-COMPOSER-11 | **CLOSED** | SPEC v1.1 capacity 子鍵+Task 1.1 calibration |
| ADV-COMPOSER-12 | **STILL-OPEN**(MINOR) | Phase 2 仍無 `collect-only` 命令；未點名 `ic_persist_redirect` 既有模式 |
| ADV-COMPOSER-15 | **CLOSED** | T-F25 |

---

## RECONCILE T-F17~T-F26 曲解檢查

| 主題 | 曲解? | 說明 |
|------|-------|------|
| T-F17 真 fixture 名 | 否 | oc_return/hl_range 已落 Task 0.1 |
| T-F18 validator 統一偽碼 | 否 | §0/1.1/2.1 三處一致 |
| T-F19 負 turnover SKIPPED | **部分** | Task 1.1/§U/G-NEW 已落；**Task 1.3 L77 未同步**→R3-1 |
| T-F20 G-NEW2 async | **部分** | 已補輪詢 GET；**缺前置 IC task bootstrap**(見 R3-2 MAJOR) |
| T-F21 npm --prefix | 否 | §B B2 L31 |
| T-F22 cost_drag 裸 number | 否 | Task 1.4 L84 |
| T-F23 UI 三態 oracle | 否 | Task 2.2 L121 四具名 RTL |
| T-F24 phase26 Gate | **文面漂移** | §B B3 L32 有；Phase 3 Gate L138 仍缺 phase26(見 R3-3 MINOR) |
| T-F25 docs 路徑 | 否 | Task 3.1 L131 |
| T-F26 B0 雙跑+shasum | 否 | §B B0 L29+Task 0.1 L45 |

RECONCILE r1 表 T-F5「7bps」：r3 已統一 G-NEW/G-NEW2=10bps、wiring 測試仍 7bps——敘述性漂移,非功能矛盾。

---

## r3 新洞掃描

### ADV-COMPOSER-R3-1 [BLOCKING] 信心度:High — Task 1.3 邊界仍要求「負 turnover clamp」

- **證據**: Task 1.3 L77 `②負 turnover clamp`；同檔 L54/Task 1.1 禁 clamp+SKIPPED；SPEC §U v1.1 L36 禁 `max(0,·)`。
- **反例**: B1 實作 proxy 測試依 L77 寫 clamp 斷言→與 analyzer SKIPPED 語意分叉；G-NEW oracle「t<0 須 SKIPPED」與 proxy 路徑不一致→假綠/假紅。
- **修法**: L77 改「②負 turnover→raise 或對齊 §U SKIPPED(若 proxy 刪除則刪該邊界句)」；與 T-F19 一字閉合。

### ADV-COMPOSER-R3-2 [MAJOR] 信心度:High — G-NEW2 仍缺兩段式 API bootstrap

- **證據**: TODO L124「POST deep-analysis→取 task_id」；現 route `POST /deep-analysis/{task_id}`(**需已有 IC task**),POST 回傳同 task_id+status,非新建 id。
- **RECHECK**: `tests/api/test_ic_deep_analysis.py` `completed_ic_task` fixture=先 `POST /analyze`→wait→再 deep-analysis。
- **反例**: 冷啟動照 L124 字面→404/無 task；B2 Gate `--baseline new2` 不可執行。
- **修法**: L124 補偽碼：①`POST /api/v1/ic/analyze`(fixture paths)→wait task completed；②`POST .../deep-analysis/{task_id}`+net_ic；③輪詢 `GET .../deep-analysis/{task_id}/result`。

### ADV-COMPOSER-R3-3 [MINOR] — Phase 3 Gate 與 §B B3 不一致

- **證據**: §B B3 L32 含 phase26；Phase 3 測試+Gate L138 僅 `tests/momentum/ tests/api/`。
- **修法**: L138 對齊 L32 或註明「phase26 僅 B3 完結 Gate」。

### ADV-COMPOSER-R3-4 [MINOR] — Task 3.1 驗證 npm 未帶 prefix

- **證據**: Task 3.1 L136 `npm run build`；§B B2 已改 `npm --prefix frontend`；root 無 package.json。
- **修法**: L136 同步 `--prefix frontend`。

---

## 覆蓋追溯重算（r3）

| 錨點 | r3 | 判定 |
|------|-----|------|
| r2 BLOCKING 2/2 | 全 CLOSED | PASS |
| SPEC §U v1.1 | 內文核可 | PASS(banner 漂移 NOTE) |
| G-OLD/G-NEW/G-NEW2 | G-OLD 可冷啟動；G-NEW2 缺 bootstrap | **PARTIAL** |
| M10 三層 | 偽碼統一；T1 仍靠 `test_finite_invariants` 泛稱(未具名 disabled+NaN 單測,可接受因偽碼已釘死) | PASS |
| §C 16 + Task 1.4 | 未回退 | PASS |

---

## Suggestions（非 Blocking）

- SPEC banner 升 v1.1 與 §U 內文對齊。
- Task 1.3 L74 nan turnover「raise 或 0.0 擇一」建議改唯一規則(對齊 batch SKIPPED 或 §T raise)。
- B2 Gate 可補 `pytest tests/api/test_ic_deep_analysis.py --collect-only -q` 釘離線 collect(延續 r2 suggestion)。

---

ASSUMPTIONS_VERIFIED: fixture FEATURE_NAMES 含 oc_return/hl_range 無 obv/ad(讀檔);`POST /deep-analysis/{task_id}` 需既有 task(test_ic_deep_analysis.py);mutation_probe 無參 exit 1;root 無 package.json
TESTS_RUN: `bash scripts/mutation_probe_check.sh`→exit 1; `rg FEATURE_NAMES tests/fixtures/ic_api_real_kline.py`; `rg 'obv|"ad"|oc_return|hl_range|負 turnover|phase26|cost_enabled and' docs/IC1C_NETIC_TODO.md`; `rg 'negative_turnover|v1\.1' docs/IC1C_NETIC_SPEC.md`
FAILURES_SEEN: none（唯讀審查）
SCOPE_CHANGES: none；產出 `handoffs/20260714-IC1C-TODOREV-R3-composer.md`；RECONCILE 未 append stamp(REJECT)
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀；SPEC §U v1.1 補裁已存在於檔內）

STATUS: DONE

TODO-REVIEW-R3: REJECT(1 BLOCKING)
