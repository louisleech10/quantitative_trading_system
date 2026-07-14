# IC1C-TODOREV-R2 — Composer 閉合重驗

> SPEC=`docs/IC1C_NETIC_SPEC.md` v1.0 Frozen | TODO=`docs/IC1C_NETIC_TODO.md` r2 | RECONCILE=`handoffs/20260714-IC1C-TODOREV-RECONCILE.md` T-F1~T-F16 | reviewer=composer | 2026-07-14

## Verdict：r1 四 BLOCKING 已閉合，r2 新現 2 BLOCKING → 需 r3 小修後重審

r2 已落地 Task 1.4、帶參 Gate、G-NEW2 oracle、SCHEMA 專檔、M10 分層、T1b 等 r1 主訴；RECONCILE T-F1~T-F16 對照 TODO 主體**無曲解**（T-F5 bps 用字 7 vs r2 實作 10 為文面漂移，非功能矛盾）。但 Task 0.1 skipped 注入特徵名與真 fixture 不符、§0 T-F7 與 Task 1.1/2.1 validator 偽碼矛盾——B0/B2 冷啟動會 KeyError 或 `{cost_enabled:false,cost_bps:NaN}` 假綠。

---

## r1 Findings 重跑（CLOSED / STILL-OPEN）

| ID | 嚴重度 | 判定 | r2 證據 / 反例重跑 |
|----|--------|------|-------------------|
| ADV-COMPOSER-0a | MAJOR | **CLOSED** | Task 1.4 + 覆蓋追溯 L141 明列 §C 16 項映射；`rg ic_reporter docs/IC1C_NETIC_TODO.md`≥4 |
| ADV-COMPOSER-0b | MAJOR | **STILL-OPEN** (MINOR) | SPEC §V L139 phase26「預期綠」；r2 B3 Gate 僅 `pytest tests/momentum/ tests/api/` **不含** `tests/phase26/`；模組名 smoke 未列 Gate |
| ADV-COMPOSER-1 | BLOCKING | **CLOSED** | §B L30「M10 於 B1 僅 T1 層;三層完整=B2」；B2 Gate 含 T2+T5 |
| ADV-COMPOSER-2 | BLOCKING | **CLOSED** | Gate 帶參：`mutation_probe_check.sh tests/momentum/Analysis/test_net_ic_analyzer.py ...`；無參仍 exit 1（已重跑） |
| ADV-COMPOSER-3 | MAJOR | **CLOSED** | Task 1.2 L69 T1b `test_run_net_ic_orchestrator_direct`；T2 e2e 歸 B2 |
| ADV-COMPOSER-4 | BLOCKING | **CLOSED** | Task 1.4 全列 ic_reporter 4 處 + export_formats red-on-break |
| ADV-COMPOSER-5 | BLOCKING | **CLOSED** | `--baseline old\|new\|new2` L40；G-NEW2 L124 可執行 oracle+artifact 路徑；獨立 validator L40 |
| ADV-COMPOSER-6 | MAJOR | **CLOSED** | 併 Task 1.4 L84-85 |
| ADV-COMPOSER-7 | MAJOR | **CLOSED** | Task 2.1 L102 T-F16 序列化禁扁平化+T2 斷言 |
| ADV-COMPOSER-8 | MAJOR | **CLOSED** | G-NEW L94 內嵌 numpy 禁 import analyzer |
| ADV-COMPOSER-9 | MAJOR | **PARTIAL→見 R2-1** | T-F10 有偽碼/lineage/validator，但 skipped 特徵名錯（見下） |
| ADV-COMPOSER-10 | MINOR | **CLOSED** | G-NEW L94 `diff_manifest.json` |
| ADV-COMPOSER-11 | MAJOR | **STILL-OPEN** (MINOR) | Task 1.1 仍加 `calibration:uncalibrated` 子鍵；§U SCHEMA 僅頂層 `capacity`；T-F9 只保 JSON 可序列化，無子鍵 oracle |
| ADV-COMPOSER-12 | MAJOR | **STILL-OPEN** | Phase 2 L123「離線可 collect」仍無 `collect-only` 命令；未點名既有 `ic_persist_redirect`（`test_ic_deep_analysis.py` 已用） |
| ADV-COMPOSER-13 | MAJOR | **CLOSED** | 專檔 `test_net_ic_schema_profiles.py` L92 |
| ADV-COMPOSER-14 | MINOR | **CLOSED** | Phase 1 測試 L92 明列合併刪除 phase25 |
| ADV-COMPOSER-15 | MINOR | **STILL-OPEN** | Task 3.1 L131 仍「API_SPECIFICATION **或** ic 相關頁」 |
| ADV-COMPOSER-16 | MAJOR | **CLOSED** | §0 完整；0.1 空殼已補但特徵名錯→R2-1 |
| ADV-COMPOSER-17 | MAJOR | **CLOSED** | G-NEW2 已非空殼 |

**r1 BLOCKING 4/4 CLOSED**；**MAJOR/MINOR 6 項中 3 CLOSED、3 STILL-OPEN（皆降為非 BLOCKING）**。

---

## RECONCILE 曲解檢查（T-F1~T-F16）

| 主題 | 曲解? | 說明 |
|------|-------|------|
| T-F1~T-F4,T-F6,T-F8,T-F11~T-F16 | 否 | r2 落點與裁決表一致 |
| T-F5 | **文面漂移** | RECONCILE 寫 G-NEW2「7bps vs 7bps」；r2 L94/L124 統一 **10bps**（與 Task 2.1 示例 7bps wiring 測試並存——建議 r3 統一敘述，非單獨 BLOCKING） |
| T-F7 | **未完整落地** | RECONCILE 稱三層「cost_bps 非 None 一律驗域」；Task 1.1 L54 / Task 2.1 L102 validator 仍僅 `cost_enabled` 時檢查→見 R2-2 |
| T-F9 | 否 | capacity 邊界轉 null 已寫入 §0+Task 1.1 |
| T-F10 | **部分落地** | 有偽碼但 skipped 特徵名與 fixture 不符→見 R2-1 |

---

## r2 新洞掃描

### ADV-COMPOSER-R2-1 [BLOCKING] 信心度:High — Task 0.1 skipped 注入特徵名不存在於真 fixture

- **證據**: TODO L40 寫死 `turnover_data.pop("obv")` + `summary["ad"]["ic_mean"]=nan`。
- **RECHECK**: `tests/fixtures/ic_api_real_kline.py` L27-34 `FEATURE_NAMES`=`log_return_1,log_return_3,rvol_20,zscore_20,hl_range,oc_return,close_sma_ratio_20`——**無 `obv`/`ad`**。
- **反例**: B0 照抄步驟④→`KeyError`；或 agent 自行發明特徵名→G-OLD skipped 路徑不可重現、validator「必含兩 skipped」失敗。
- **修法**: 改為 fixture 內真實名（建議 `oc_return` turnover pop + `hl_range` gross_ic NaN），與 validator `feature 數≥N-2` 對齊；禁止 placeholder 名。

### ADV-COMPOSER-R2-2 [BLOCKING] 信心度:High — §0 T-F7 與 Task 1.1/2.1 validator 偽碼矛盾

- **證據**: §0 L12「`cost_bps` 非 None 一律驗域」+ 例 `{cost_enabled:False,cost_bps:NaN}` 三層拒絕；Phase 2 L124 T2 矩陣含該 422。
- **RECHECK**: Task 1.1 L54 `cost_enabled and (...)` 才 raise；Task 2.1 L102 `enabled 且 (...)` 才 raise——**disabled 分支不驗 cost_bps**。
- **反例**: API/analyzer 接受 `{cost_enabled:false,cost_bps:NaN}`→T2 測試與 §0 宣稱衝突；M10「三層」假綠。
- **修法**: 三層統一「`cost_bps is not None` → 驗有限且 `0<x≤1000`；`cost_enabled` 時另驗 `cost_bps is not None`」；Task 1.1/2.1/ic_config_schema 偽碼同步。

### ADV-COMPOSER-R2-3 [MAJOR] 信心度:Medium — `max(0.0,turnover)` 無 Frozen SPEC 授權

- **證據**: Task 1.1/1.3、G-NEW canonical 重算均 `max(0,t)`；SPEC §T/§U 只裁非有限→SKIPPED，未裁負值 clamp。
- **反例**: 上游污染 turnover&lt;0 被靜默归零→成本拖累假合法（同 CODEX-1 類）。
- **修法**: SPEC 裁定 reject/SKIPPED 後再加測試；或刪 clamp 改 SKIPPED。

### ADV-COMPOSER-R2-4 [MAJOR] 信心度:High — phase26 未入任何 Gate

- **證據**: SPEC §C #16 + §V「phase26 預期綠」；B3 L138 不含 `tests/phase26/`。
- **反例**: factories/integration 模組註冊回歸 B3 不可見。
- **修法**: B3 Gate 加 `pytest tests/phase26/ -q` 或覆蓋追溯註明「僅 smoke、B3 不含」並降 SPEC 聲稱。

### ADV-COMPOSER-R2-5 [MINOR] — Task 3.1 docs 路徑仍模糊（延續 COMPOSER-15）

- **修法**: 唯一路徑 `docs/API_SPECIFICATION.md` Net IC 小節。

---

## 覆蓋追溯重算（r2）

| 錨點 | r2 | 判定 |
|------|-----|------|
| Task 7/7 + 1.4 | 8 Task 名目 | PASS |
| M1-M10 | 具名+Gate 分層 | PASS（T-F7 實作矛盾見 R2-2） |
| G-OLD/NEW/NEW2 | 三模式+validator+G-NEW2 oracle | **PARTIAL**（G-OLD skipped 名錯 R2-1） |
| §C 16 consumer | L141 映射 | PASS |
| §U SCHEMA 專檔 | 有 | PASS |

---

## Suggestions（非 Blocking）

- RECONCILE T-F5 文面 7bps 與 r2 10bps 統一敘述，避免派工混淆。
- B2 Gate 可補 `pytest tests/api/test_ic_deep_analysis.py --collect-only -q` 釘離線 collect。
- `capacity.calibration` 若保留，建議 G-NEW 對 capacity 子樹做結構斷言或寫入 §U 允許子鍵。

---

ASSUMPTIONS_VERIFIED: fixture FEATURE_NAMES 無 ad/obv（讀檔）；mutation_probe 無參 exit 1；ic1c_freeze 腳本尚不存在（預期 B0）；ic_reporter 現碼仍 net_ic（預期 B1 前）
TESTS_RUN: `bash scripts/mutation_probe_check.sh`→exit 1; `rg FEATURE_NAMES tests/fixtures/ic_api_real_kline.py`; `rg 'obv|"ad"' docs/IC1C_NETIC_TODO.md`; `rg ic_reporter docs/IC1C_NETIC_TODO.md`
FAILURES_SEEN: none（唯讀審查）
SCOPE_CHANGES: none；產出 `handoffs/20260714-IC1C-TODOREV-R2-composer.md`
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀）

STATUS: DONE

TODO-REVIEW-R2: REJECT(2 BLOCKING)
