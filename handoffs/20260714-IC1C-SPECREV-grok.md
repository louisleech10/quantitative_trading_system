# IC1C SPEC Adversarial Review — grok

**task-id**: IC1C-SPECREV  
**標的**: `docs/IC1C_NETIC_SPEC.md` v0.1 draft  
**角色**: 獨立 adversarial 委員（獵洞，非背書）  
**約束**: 唯讀；未寫檔；未跑寫 `data_cache` 命令  
**依據讀取**: SPEC 全文；`net_ic_analyzer.py` 全檔；`ic_filter_orchestrator.py:1942-1956` + module runner 序；`factor_return_analyzer.py`；consumer 端 `ic_reporter` / `ic_analysis_service` / `ic_models` / frontend；既有 tests（phase24/25/26、momentum/Analysis、api）  

**數值手算 receipt（本機 exec 跳過 package init）**:  
`compute_net_ic(0.05, 1.5, cost_bps=10)` → `net_ic=0.047`；手算 `cost_drag=(10/10000)×1.5×2=0.003`；`0.05−0.003=0.047`。證實：**相關係數 − 報酬率** 被當「淨 IC」。

---

## 修法二案獨立裁決（面向 1）

| 案 | 判斷 |
|----|------|
| **A 同單位化** | 技術上可做（Grinold 型 `E[r]≈IC·σ_signal·σ_label`），但引入兩條估計量與額外假設；SPEC 目標是修量綱 bug，不是疊近似。**不推薦**。 |
| **B 拆報告+損益平衡點** | 與現碼一致：`compute_net_factor_return` 已是報酬−報酬（:44-70）；`compute_net_ic` 才是量綱錯（:34）。修法=刪錯公式 + 接通正確路徑，不引入新估計量。**推薦**。 |
| **第三案** | 見下「弱 B / 資訊分層」——本質仍屬 B 家族，**不是**與 B 對立的獨立修法。 |

**Claude 推薦理由是否站得住**: **是**。核心不是「A 數值不對」，而是 A 用**額外模型假設**去救一個**定義錯誤的減法**；B 直接拒絕無意義運算。

**RULING 細節**（正式行在文末）: **B**。  
第三案（可選強化，不取代 B）: **資訊分層**——(1) 永遠輸出 `gross_ic`；(2) 有成本時輸出 `cost_drag_return`（報酬空間）；(3) 僅在有因子期報酬序列時輸出 `net_factor_return` / 報酬基 `breakeven` / `profitable_after_cost`；(4) **禁止**任何名為 `net_ic` 的鍵（含別名），避免下游繼續誤讀。此為 B 的嚴格執行面，非新數學。

---

## Findings

### ID: GROK-1
**嚴重度**: **BLOCKING**  
**面向**: Task 1.2 factor_returns 來源存在性  

**證據**:
- SPEC Task 1.2:「來源=既有 factor return 計算模組」+ e2e 斷言 `features[*]["net_factor_return"]["net_mean"]` 為有限 float。
- `momentum/Analysis/factor_return_analyzer.py` **存在**（factory: `create_factor_return_analyzer`）。
- `compute_factor_returns` 回傳 dict 僅含：`long_short_mean_return`（scalar）、`quantile_returns_summary`、`risk_metrics`、`*_sampled` 列表等（:96-104）。
- 內部 `ls_returns = high − low`（:87）**計算後未寫入回傳**。
- `compute_batch`（:167-189）只包上述 dict / skipped。
- `NetICAnalyzer.batch_analyze` 契約：`factor_returns: Optional[dict[str, pd.Series]]`（:125），並 `gross_series = factor_returns[feature_name]` 餵 `compute_net_factor_return`（:174-180）。
- orchestrator `_run_net_ic`（:1956）目前 `batch_analyze(summary, turnover_data)`，未傳第三參。

**可證偽反例**:
1. 假設「既有模組可直接餵 `batch_analyze`」→ 取 `FactorReturnAnalyzer.compute_batch(...)[feat]` 當 `pd.Series` → **TypeError / 非 Series**（實際是 dict）。
2. 假設「用 `long_short_mean_return` 當 series」→ `compute_net_factor_return` 需要 index 對齊的 Series → 失敗或語意錯。
3. 僅接 scalar 均值做 breakeven 可算，但 **無法**滿足 SPEC 寫死的 `net_factor_return.net_mean` 有限 float（那要期序列 − 成本序列）。

**建議修法**:
- 在 SPEC 明寫二選一（委員會裁）:
  - **(i)** 擴大 scope：`factor_return_analyzer` 匯出 `ls_return_series: pd.Series`（或等價 period L/S return），orchestrator 從 `_run_factor_return` 結果或 `_ic_cache` 組 `dict[str, Series]`；**或**
  - **(ii)** 縮小 1.2 驗收：breakeven/profitable 允許用 `long_short_mean_return` scalar；`net_factor_return` 僅在 series 存在時出現，e2e 改為「有 series 才 finite / 無則 skipped+reason」，刪除「一律 finite net_mean」。
- 並寫清 **模組依賴**：`net_ic_analysis` 在 `factor_return` disabled 時的 fail-closed 語意（目前兩模組可獨立 toggle）。

---

### ID: GROK-2
**嚴重度**: **BLOCKING**  
**面向**: fail-closed 語意（殘留 5.0 bps / 幽靈預設）  

**證據**:
- `ic_config_schema.NetICAnalysisConfig.default_cost_bps: float = Field(default=5.0)`（:268）。
- `NetICAnalyzer.__init__`: `cfg.get("default_cost_bps", 5.0)`（:21）— schema 預設 + 程式二次 fallback。
- `compute_net_ic` / `compute_net_factor_return`: `cost_bps is None → _default_cost_bps`（:31, :50）。
- Phase 2 只「加 `cost_enabled` + `cost_bps`」，**未要求刪除/禁用 `default_cost_bps`**。
- `DeepAnalysisRequest` 僅 `modules: DeepAnalysisModules`（bool）+ 自由 `config_override: Dict`（`api/models/ic_models.py:31-35`）；成本非一等欄位。
- `ic_analysis_service._build_deep_module_override`（:1140-1141）: 只傳 `enabled`，再 `**(request.config_override or {})` — 任意 dict 可灌進 net_ic 節。
- §R:「舊 request 不帶新欄=模組 disabled 路徑」— 但 **未定義 `cost_enabled` 預設**；且 `modules.net_ic_analysis` 預設 **True**（`ic_models.py:28`）。

**可證偽攻擊路徑**:
1. 客戶端只送 `{modules: {net_ic_analysis: true}}`，不帶 cost → 若驗證未做在 Pydantic/service 入口 → analyzer 仍用 **5.0 bps** → **不是 422**，幽靈成本復活。
2. `config_override: {net_ic_analysis: {default_cost_bps: 5}}` 繞過「無寫死」前端 UI。
3. 若 `cost_enabled` 預設 True 且缺 cost→422，則舊客戶全紅；若預設 False 卻仍留 `default_cost_bps=5`，cost_sensitivity 固定階梯 `[1,3,5,10,20]` 仍硬編碼（analyzer:22 + NetICChart:44）。

**建議修法**:
- 明定：`cost_enabled` **default=False**（additive）；`cost_enabled=True` 且 `cost_bps is None` → **API 層** 422（typed field，非只靠 analyzer）。
- **刪除或 deprecate** `default_cost_bps` 預設；analyzer 在 enabled 且缺 cost 時 raise/skip，**禁止** `5.0` fallback。
- 列出必須拔除的殘留：schema Field default、`cfg.get(..., 5.0)`、前端 NetICChart `useState(5)`、hardcoded scenario 下拉。
- `config_override` 對 cost 的白名單/校驗規則寫進 SPEC。

---

### ID: GROK-3
**嚴重度**: **BLOCKING**  
**面向**: Case B 後 summary / schema 空洞  

**證據**:
- Task 1.1 schema 列 feature 級欄位，**未重定義** `summary`。
- 現碼 summary（:186-214）:
  - `profitable_count` ← `profitable_after_cost`（目前由錯誤 `net_ic>0`）
  - `avg_ic_loss_pct` ← `(gross_ic − net_ic)/|gross_ic|`（:193-200）
  - `rank_correlation_gross_vs_net` ← spearman(gross_ic 列表, **net_ic** 列表)（:182-184, :202-205）
- Case B 若移除 `net_ic`，上述三者 **全部失去定義**。
- §G baseline 仍要求 summary 四欄 + 選擇性等值；diff 表白名單只有 feature 級 `net_ic/breakeven/profitable`，**未含 summary 語意重定義**。

**可證偽反例**:
1. 實作刪 `net_ic` 但不改 summary → `KeyError` 或靜默用別名假 `net_ic` → 量綱 bug 從 feature 漏到 summary。
2. 實作改 summary 未列入 diff 表 → 依 §G「未列欄位改變=FAIL」→ **合法修法被 golden 擋死**。
3. 實作保留 `avg_ic_loss_pct` 名稱但改算 cost_drag/gross → 下游以為仍是「IC 損失%」→ 標籤謊言。

**建議修法**:
- SPEC 凍結 Case B 的 **summary 契約**，例如:
  - `profitable_count`: 僅計有限 `net_factor_return` 且 net_mean>0；缺報酬者不計入（或分母改 `evaluable_count`）
  - 刪除或更名 `avg_ic_loss_pct` → `avg_cost_drag` / `avg_return_loss`（報酬空間）
  - `rank_correlation_gross_vs_net` → `rank_correlation_gross_ic_vs_net_return` 或在無 series 時 NaN+reason
- §G diff 表必含 summary 全欄。

---

### ID: GROK-4
**嚴重度**: **BLOCKING**  
**面向**: §G 選擇性等值可證偽性不足  

**證據**:
- §G: `gross_ic`/`turnover`/`cost_bps` byte 不變；`net_ic`/`breakeven`/`profitable` 列表 diff；「未列=FAIL」。
- Phase 1 行為變更後 **必變** 且未在 diff 白名單點名的:
  - 新增 `cost_drag_return`、`net_factor_return`、`cost_semantics`、`reason`
  - summary 三欄（見 GROK-3）
  - `cost_sensitivity[*].net_ic` → 應改 `cost_drag`/`net_factor_*`
  - `capacity.calibration` 標記（Task 1.1）
- 選擇性等值 **未**規定：對「改了不該改的」欄（如 `gross_ic` 被重算）有獨立 mutation；也未規定 **禁止** 用 IC 頂替 breakeven 的 golden 負例。
- 手算 receipt ≥3 feature 只對「量綱修正方向」，**不覆蓋**「summary / sensitivity schema」。

**可證偽反例**:
1. 惡意實作：只把 `net_ic` rename 成 `cost_drag_return` 但公式仍 `IC − cost×turn×2` → feature 手算若只查 `cost_drag=0.003` 可能過，但若同時檢查 `profitable` 仍依混量綱 → 需明確負例。
2. 實作「正確」新增欄但 golden 腳本只 hash 舊鍵 → **假綠**（新錯欄不進 hash）。
3. Phase 2 拿掉 default 5bps 後 `cost_bps` 不再 byte 等值於 baseline → Phase 0 golden 與 Phase 2 衝突；SPEC 未分 phase 的 golden 生命週期。

**建議修法**:
- Golden 分層：Phase0 全量 baseline；Phase1 **allowlist + denylist**（denylist=任何仍出現的混量綱 `net_ic` 公式輸出）；Phase2 重凍 cost 相關。
- 明確「新增欄必須進 schema 清單+測試」；mutation：**復原混減** 後 sha256 不得與 Phase1 目標相等。
- 寫清 `cost_bps` 在 Phase1 仍固定 vs Phase2 使用者輸入的 freeze 策略。

---

### ID: GROK-5
**嚴重度**: **NON-BLOCKING**（consumer-map 不完整；漏列會在實作期炸，建議升 BLOCKING 若要 freeze）  
**面向**: consumer-map 完整性  

**SPEC §C 已列**（grep 確認存在）:
| 點 | 狀態 |
|----|------|
| orchestrator `_run_net_ic` :1942-1956 | 有 |
| ic_reporter :150/:209/:570/:631-634/:773 | 有，:631 讀 **`"net_ic"` 鍵** |
| ic_analysis_service :1140 | 有（僅 enabled） |
| api/models :28 | 有（僅 bool） |
| NetICChart / DeepAnalysisConfigPanel / store / types | 有 |

**grep 發現但 SPEC 未列**:
| 漏列 | 證據 | 風險 |
|------|------|------|
| `frontend/.../page.tsx:823` | 掛載 NetICChart | schema 變更渲染 |
| `FeatureTierPanel.tsx:39` | tier 開關文案「成本調整後淨 IC」 | 幽靈語意 |
| `tests/momentum/test_export_formats.py:73-75` | fixture `{"net_ic": 0.04}` | export 測試 |
| `tests/phase24/test_deep_analysis_config.py:23,55,70,74` | **斷言 default_cost_bps==5** | Phase2 必紅 |
| `factories.create_net_ic_analyzer` | factories.py:505 | 低 |
| **`turnover_analyzer.compute_net_ic_proxy`** | :125-137；測試斷言 `0.1 − 0.01×2.0 = 0.08` | **同族量綱/近似減法**，另一入口 |
| `NetICAnalysisConfig.slippage_bps=2.0` | schema:269；**全 repo 僅 schema 一處** | 幽靈 config |
| cost_sensitivity / NetICChart 硬編碼 `[1,3,5,10,20]` | analyzer:22；NetICChart:44 | Phase3 |

**可證偽**: 只改 `net_ic_analyzer` + SPEC 所列 consumer，不改 `test_deep_analysis_config` / export fixture / reporter CSV 欄 → CI 仍可能綠或局部紅未在 SPEC 測試清單。

**建議**: consumer-map 補上表；**turnover proxy** 要嘛納入 1c scope、要嘛 §N 明示「已知同病、另票」，禁止靜默。

---

### ID: GROK-6
**嚴重度**: **NON-BLOCKING**  
**面向**: §V mutation M1–M4 與既有測試紅點清單  

**既有會受影響的斷言（SPEC 漏列細節）**:

| 測試 | 現斷言 | Case B 後 |
|------|--------|-----------|
| `tests/phase25/test_net_ic_analyzer.py` + 幾乎相同的 `tests/momentum/Analysis/test_net_ic_analyzer.py` | `result["net_ic"]` 與 gross 相近（zero turnover / zero cost）；`profitable_after_cost is False`（負 gross_ic）；`default_cost_bps` 驅動 batch | 鍵/語意必改；**負 IC 不再自動 profitable=False**（若改看 factor return） |
| `test_cost_sensitivity_custom_scenarios` | scenarios 含 `net_ic` | schema 改 |
| `test_batch_analyze_*factor_returns*` | 有 `net_factor_return` 鍵即可 | 應升級為量綱/手算 |
| `tests/phase24/test_deep_analysis_config.py` | `default_cost_bps == 5` | Phase2 紅 |
| `tests/momentum/test_export_formats.py` | 結構含 net_ic | 欄位 |
| `tests/momentum/test_turnover_analyzer.py::test_net_ic_proxy` | 混量綱近似 **被當成正確** | 若不動 proxy＝雙重標準 |
| `tests/api/test_ic_deep_analysis.py` | 只關 `net_ic_analysis: False`，**無 net_ic 數值斷言** | Task 1.2 說 `-k net_ic` e2e — **現無此測試**，屬新建 |
| phase26 integration/factories | 模組名/runner 映射 | 多半仍綠 |

**Mutation 證偽缺口**:
- **M1/M2**: 現有測試**沒有**斷言「禁止 IC−cost」或 `×2`；多數在 **固化錯誤 API**（有 `net_ic` 鍵）。M1/M2 需 **新** 手算測試，否則「改壞必紅」不成立。
- **M3**: **全測試樹無 `breakeven_cost_bps` 數值斷言** → M3 目前是紙面 mutation。
- **M4**: wiring 測試不存在；store 只傳 module bool，無 cost_bps 通道可證偽。

**建議**: SPEC §V 附「新建 vs 改寫」測試表；M1–M4 各綁 **具體 test 函式名**；明示 phase24 default=5 必須改寫原因（舊斷言錯在固化寫死成本）。

---

### ID: GROK-7
**嚴重度**: **NON-BLOCKING**（語意不足；使用者「1h–1w 不定」可能未滿足）  
**面向**: Phase 3 timeframe 情境掃描  

**證據**:
- 使用者裁定：持倉 1h~1w 不定 → 情境掃描、不綁單一 TF。
- Task 3.1: 以使用者 **cost_bps 為中心 ±階梯** + 標籤 `cost_semantics == "per_rebalance_not_annualized"`。
- 現 `cost_sensitivity` 只掃 **成本 bps**，不掃 **再平衡頻率 / 持倉期 / turnover 情境**。
- `cost_drag = (bps/10000)×turnover×2` 已是 **每 rebalance**；TF 影響主要在 **turnover 與 label horizon**，不是 bps 階梯本身。
- 階梯數「委員會裁」— SPEC 未給預設值 → 實作/測試門檻未鎖。

**可證偽**:
1. 宣稱「已支援多持倉期」但只改 bps∈{1,3,5,10,20} → 1h 與 1w 策略成本敘事仍可能被誤讀（若 UI 不解釋 turnover 已含頻率）。
2. 若有人把結果「×(periods_per_year)」年化 → 標籤字串測試可抓；但 **若根本不做年化、卻暗示跨 TF 可比** → 字串測不過問。

**建議**:
- 文件/UI 明確：掃描維度=**交易成本 bps**，不是持倉期；跨 TF 比較要固定成本假設並並列 turnover。
- 或增加 **turnover 乘數 / rebalance 情境**（例：0.5×/1×/2× 觀測 turnover）才對齊「持倉頻率不定」。
- 鎖死階梯演算法（例：`{c/2,c,2c,5c}` clamp）與測試常數。

---

### ID: GROK-8
**嚴重度**: **NON-BLOCKING**  
**面向**: `net_ic` 鍵去留未裁 + reporter/前端硬依賴  

**證據**: Task 1.1「移除或更名—委員會裁決」；`ic_reporter:631-634` 與 `NetICChart` / `types.ts:2456-2461` 全讀 `net_ic`。

**可證偽**: 裁決「保留別名=gross_ic−cost」→ 下游繼續畫「Net IC」scatter → **bug 換皮存活**。

**建議**: SPEC 凍結前 **必須** 寫死：`net_ic` **禁止輸出**（或只允許 deprecated 且恒 NaN+reason）；reporter 欄位改 `cost_drag_return` / `net_factor_return_mean`；前端軸標重命名。第三方案「禁別名」併入 B。

---

### ID: GROK-9
**嚴重度**: **NIT**  
**面向**: 其他  

- `slippage_bps` 幽靈欄位：建議 Phase2 刪或接入，否則「成本全棧」敘事不完整。  
- batch_analyze 有 factor_returns 時 `turnover_series = 常數 scalar`（:176）— 期內換手變動被抹平；SPEC 未披露此近似。  
- `force_modules=["net_ic_analysis"]` 可在無 factor_return 結果時跑 — 與 1.2 e2e「必有 net_mean」衝突。  
- TODO 檔 `docs/IC1C_NETIC_TODO.md` 尚不存在（SPEC 自述凍結後生成）— 預期內。  
- 核心 bug 診斷（FACT-RECEIPT）與 orchestrator 未傳 factor_returns：**同意，已複核**。

---

### ID: GROK-10
**嚴重度**: **NIT**  
**面向**: 案 A 補充  

若未來有人重提 A：必須另附 σ 估計 PIT、樣本定義、與 `compute_net_factor_return` 交叉校準；**不得**在本 1c 混進 A。本票維持 B-only 正確。

---

## 面向對照（簡表）

| # | 面向 | 結論 |
|---|------|------|
| 1 | 量綱二案 | **B**；Claude 理由成立；嚴格執行=禁 `net_ic` 別名 |
| 2 | consumer-map | 主鏈有；漏 export/tests/FeatureTier/page/turnover proxy/slippage |
| 3 | §G golden | 選擇性等值方向對，但 summary/新欄/phase 生命週期不足 → 可假綠或假紅 |
| 4 | factor_returns 來源 | 模組**在**，Series **契約不在** → Task 1.2 現文 **BLOCKING** |
| 5 | fail-closed | 422 敘述與 `default_cost_bps=5` / config_override **衝突** → BLOCKING |
| 6 | M1–M4 | 方向對；現測多固化舊錯；M3/M4/e2e 需新建 |
| 7 | TF 掃描 | 標籤有用；「持倉期情境」≠「bps 階梯」— 語意需收斂 |

---

## Verdict

**BLOCKING 計數**: 4（GROK-1, GROK-2, GROK-3, GROK-4）

SPEC-REVIEW: REJECT(4 BLOCKING)

RULING: B

---

## 結構化收尾（編排用）

```
ASSUMPTIONS_VERIFIED: 量綱混減公式與手算0.05-0.003=0.047；orchestrator未傳factor_returns；FactorReturnAnalyzer不回傳pd.Series；default_cost_bps=5雙層預設；summary依賴net_ic；consumer grep補漏
TESTS_RUN: 未跑pytest（唯讀審查）；以讀檔+targeted exec手算驗證量綱；NUMBA路徑package import曾失敗故改exec片段
FAILURES_SEEN: none
SCOPE_CHANGES: none（審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）
HANDOFF_NOT_UPDATED: 唯讀沙箱，使用者要求stdout交卷、編排端落檔
OUTPUT_PATH_EXPECTED: handoffs/20260714-IC1C-SPECREV-grok.md
```

STATUS: DONE
