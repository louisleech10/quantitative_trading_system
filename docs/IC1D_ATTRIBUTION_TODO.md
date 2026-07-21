# IC 1d — Factor Attribution TODO

> 版本：**v0.3 ✅ FROZEN**（2026-07-21;與 SPEC v0.5.2 同輪三家戳記凍結） | 基於 SPEC：`docs/IC1D_ATTRIBUTION_SPEC.md` **v0.5.2**（errata:C3/N1/N2/N4 措辭對齊;與本 TODO 同輪戳記凍結） | 日期：2026-07-21
> 交付定義：**幽靈契約隔離（explicitly not wired）**，非「接線修復」；完工後 `calculate_factor_attribution` production caller **仍為 0**。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **解耦**：不新增 `momentum/`→`api/` import；服務不互 import；DTO 不跨界（SPEC §C）。
- **不弱化 NaN/inf gate**：本票方向為**強化**；禁 `fillna` 補值；禁 `try/except LinAlgError` 敷衍（須在 lstsq **前**攔截）。
- **不擅改輸出大小**：新增/移除鍵須落在 §G 白名單（見各批 comparator 指令）。
- **Logging**：`get_logger(__name__)`；hot loop 不 log。Error 分類：`InvalidInputError`（invalid/logic/data format）非 retryable。
- **防假綠**：不得放寬/刪除既有測試斷言換綠燈；diff 既有斷言驗收；禁快照替代行為斷言。
- **回傳 envelope（D-6）**：ok=扁平數值欄 + `status:"ok"`；unavailable=`{status,value:None,reason}` **三鍵**、無數值欄。消費者一律先讀 `status`。
- **不做（§N）**：接真 attribution（票A/票B）；刪除 `unexplained`（遷移票）；真 residual IC；exposure 家族其餘 NaN 靜默；FR `min_samples` 與 attribution 門檻統一。
- **禁改 frozenset**：`factor_return_sanitizer.py:46 _PRESERVE_SUMMARY_STATUSES` 勿動；`completed_partial` 計數改的是 `:341 _count_status`（D-12）。

## §B 批次執行策略（依 Phase 依賴序列；每批 Claude 獨立驗 + Codex/Composer 雙審 + 批間 Gate）
| 批 | Phase | Task | 依賴 | 驗收層 |
|---|---|---|---|---|
| **B0** | 0 | 0.1 baseline + comparator | 無 | pytest baseline exit=0 |
| **B1** | 1 | 1.1 / 1.2 / 1.3 正名 | B0 | deep no-op + analyzer 單元 + npm build |
| **B2** | 2 | 2.1 / 2.2 fail-closed | B1 | **單元級**（禁用 deep JSON） |
| **B3** | 3 | 3.1 stub→unavailable+外顯 | B2 | **deep payload** comparator 20 路徑 |
| **B4** | 4 | 4.1 測試去固化 + 7 探針 | B2+B3 | mutation_probe_check exit=0（含整合檔） |
| **B5** | 5 | 5.1 前端 TS+Radar+ExportButtons | B3 | npm build + 元件測試 |
- **批間 Gate**：引用具體 pytest/comparator 指令 + exit=0；上批未閉合不派下批。
- **三方 DATA-CORRECT**（收尾）：Claude + Codex adversarial + Composer；本票屬 (a)(d) 高風險。

## 階段 1：SPEC 覆蓋追溯（100% ID，防漏基準）
- **Task IDs（9）**：0.1 / 1.1 / 1.2 / 1.3 / 2.1 / 2.2 / 3.1 / 4.1 / 5.1 → 對應 B0-B5。
- **§D 裁決（13）**：D-1 分層 / D-2 comparator+白名單 / D-3 factor_betas 不改鍵 / D-4 completed_partial / D-5 index 政策 / D-6 envelope / D-7 門檻具名 / D-8 dropna 閾值 0 / D-9 baseline 同源 / D-10 輸入端非有限 / D-11 comparator subtree / D-12 三計數點 / D-13 輸出端非有限。逐條落點見 SPEC §D-MAP。
- **Golden（§G）**：p0_before / p1_after_rename / p3_after_failclosed；comparator=`scripts/ic1d_compare.py`（B0 建）。Phase 1 allow-add=0、Phase 3 allow-change 3 + allow-remove 15 + 連帶 2 = 20 路徑。
- **mutation 探針（7）**：**analyzer 檔 5 支**（dropna / insufficient / inf / output_overflow / index_policy）+ **整合檔 2 支**（stub / module_summary）。
- **§RISK 命中**：a,b,d。**Phase 依賴**：0→1→2→3→4(依2,3)→5(依3)。**新 config key**：`factor_exposure.attribution_min_rows`（預設 10，B2 加）。

## §P 批次 Task 明細

### B0 — Baseline 前置（依賴：無）
### Task 0.1 — production 同源 close carrier + 凍 baseline
- 檔案：**新建 `scripts/ic1d_baseline_freeze.py`**（類比 `scripts/ic1cfr_stopgap_freeze.py`；**支援 `--profile {p0,p1,p3}`**，同一腳本在對應 Phase 後重跑產出對應 golden，輸出至 `handoffs/ic1d_baseline/`，ADV-GROK-3）+ 新建 `scripts/ic1d_compare.py` + 新建 `tests/momentum/Analysis/test_ic1d_baseline.py`；**不改 production**。
- 改法：① close carrier 經 production 路徑（`ic_filter_orchestrator.py:2913-2930`）注入，**禁** ad-hoc 塞 `_ic_cache`（D-9）；dump `p0_before.json`。② `ic1d_compare.py` CLI=`python scripts/ic1d_compare.py <before> <after> [--allow-add P] [--allow-change P] [--allow-remove P]`；三 flag 皆 **subtree 語意**（D-11）；**數值容差 `atol=1e-12` / `rtol=1e-9`**（float32 放寬）；NaN↔NaN 相等、NaN↔數值視為變更；exit 0/1。**Phase 3 完整白名單**（B3 用）：allow-change 3 = `results.factor_exposure.factor_attribution` + `.payload.summary.factor_attribution` + `.typed_result.payload.summary.factor_attribution`；allow-remove 15 = 三鏡像（頂層 / `payload.summary` / `typed_result.payload.summary`）**各明列** `alpha,r_squared,attribution,unexplained,factor_betas`（**禁 shell brace,須逗號分隔字面路徑**，見 B3 完整命令）；連帶 `module_summary.factor_exposure` + flatten 列數。
- **oracle 取得路徑（BLOCKING C2 修）**：deep serializer 現無 `results.factor_exposure.module_summary` nested key（`_serialize_deep_analysis` 只出 `module_statuses`）→ baseline 須從 **`DeepAnalysisReport.module_summary` dict 直接取**（非 serialized receipt）。P1 的 analyzer 數值 oracle（`calculate_factor_attribution` caller=0）須由 **獨立 real-OLS baseline** 提供：`test_ic1d_baseline.py` 直接以固定種子輸入呼叫 `calculate_factor_attribution`，存 `alpha/r_squared/intercept` 基準值供 B1 逐欄比對（不經 deep 管線）。
- **驗證（`test_ic1d_baseline.py` 寫死 assert）**：① `report.module_summary["factor_exposure"] != "skipped"` 且 `payload["portfolio_exposure"]` 非空；② **同源斷言**：mock/spy `ic_filter_orchestrator` 的 close carrier 寫入點（`:2913-2930`），assert baseline 的 close 經該呼叫棧注入（非測試直接塞 `_ic_cache`）；③ analyzer real-OLS 基準值 dump 至 `handoffs/ic1d_baseline/analyzer_oracle.json`。指令 `pytest tests/momentum/Analysis/test_ic1d_baseline.py -q` exit=0。
- **邊界**：① **（C3 已由 SPEC errata v0.5.2 對齊;Grok HYBRID 裁決）**：baseline **一律用有效 close**（非空非全 NaN）;all-NaN raise 屬 production-hardening 缺口另票,**不以 raise 為 B0 通過條件**。SPEC 正文 v0.5.2 已同步改述,C3 CLOSED。② close 短於 features → 現行 reindex 產 NaN,由 baseline 值檢查捕捉 ③ 時間軸間隙 → 正常通過（D-5）。
- **存活至**：Phase 5 後保留（`p0_before.json` 全程對照基準；`ic1d_compare.py`+`ic1d_baseline_freeze.py` 票A/票B 可複用）。
- **覆蓋風險**：無。
- 不可做：不得為求 baseline 非空而放寬 `:2174-2179` close 檢查。

### B1 — 正名（deep JSON no-op；依賴：B0）
### Task 1.1 — `unexplained` 正名（僅 analyzer 純函式；D-1）
- 檔案：**只有** `momentum/Analysis/factor_exposure_analyzer.py:142-148`。**不改 orchestrator**。
- 改法：回傳新增 `"intercept"` 指向 `beta[0]`（=alpha 同值）；`"unexplained"` **保留** deprecated alias；docstring 註明非殘差（`residual`:129 僅用於 R²，**禁**改 `unexplained=mean(residual)`）。
- **producer（ADV-GROK-3）**：B1 改完 analyzer 後 `python scripts/ic1d_baseline_freeze.py --profile p1` 產 `handoffs/ic1d_baseline/p1_after_rename.json`（p1 由本步產,非 B0）。
- **驗證**：① deep no-op — `python scripts/ic1d_compare.py handoffs/ic1d_baseline/p0_before.json handoffs/ic1d_baseline/p1_after_rename.json`（**不帶任何 `--allow-*`**）exit=0；② analyzer 單元（真實 OLS）— `assert result["intercept"]==result["unexplained"]==result["alpha"]` 且三者與 P0 記錄之 analyzer 基準值逐欄相等；③ `pytest tests/momentum/Analysis/test_factor_exposure_analyzer.py -q` exit=0。
- **邊界**：① 樣本不足/unavailable 分支下 `intercept` **不應出現**（D-6 失敗形僅三鍵）② `test_zero_r_squared` 不受影響。
- **存活至**：Phase 5 後保留（`intercept` 永久正名，票A 直接使用）。
- **覆蓋風險**：無（v0.5 已砍 orchestrator 白工）。
- 不可做：**不得**改 orchestrator；**不得刪除** `unexplained`。

### Task 1.2 — `factor_betas` / positions 語意正名（僅註解，不動鍵；D-3）
- 檔案：`ic_filter_orchestrator.py:2186`（`positions`→`equal_time_weights` 變數名）、`factor_exposure_analyzer.py:86-102` docstring。
- 改法：`positions` 更名 + docstring 說明其為**時間軸等權平均**（`len()`=列數非標的數），非交易持倉。`factor_betas` **JSON 鍵不動**（Phase 3 移除）。
- **驗證**：`python scripts/ic1d_compare.py p0_before.json p1_after_rename.json`（零 allow-add，不得改變任何輸出）exit=0；`grep -c "equal_time_weights" momentum/Analysis/ic_filter_orchestrator.py` >= 1。
- **邊界**：① 更名後所有引用點同步（舊名 `grep` 殘留=0）② docstring 正名不得改 `calculate_portfolio_exposure` 回傳值。
- **存活至**：Phase 5 後保留（變數名/docstring 屬 runner 本體非 stub 區）。
- **覆蓋風險**：無（不動 JSON 鍵；Phase 3 移的是 `factor_betas` 鍵，不重疊）。
- 不可做：不得改 `calculate_portfolio_exposure` 計算。

### Task 1.3 — UI copy 正名
- 檔案：`FeatureTierPanel.tsx:50`（**僅 copy；`types.ts` 型別歸 Task 5.1，本 Task 不碰**，ADV-C8）。
- **驗證**：`cd frontend && npm run build` exit=0；`grep -c "因子曝險歸因" frontend/src/components/ic-analysis/FeatureTierPanel.tsx` == 0；`npx tsc --noEmit` exit=0。
- **邊界**：① 舊 copy 出現在其他語系/aria-label 須一併掃 ② `DeepAnalysisConfigPanel.tsx:29` 既有 tip 已乾淨，勿誤改。
- **存活至**：Phase 5 後保留（UI copy 正名永久）。
- **覆蓋風險**：無。
- 不可做：不得改 Radar 以外其他圖表 copy。

### B2 — analyzer fail-closed（單元級驗收；依賴：B1）
### Task 2.1 — 非有限值靜默 → fail-closed（`:109-112`）
- 改法：① dropna 前後列數，任何丟棄 → `{"status":"unavailable","value":None,"reason":"nan_rows_dropped:<n>/<total>"}`（D-6/D-8 閾值 0）。② **輸入端非有限（D-10）**：`lstsq` **之前** `~np.isfinite` 統一檢查；reason 優先序=有 inf→`non_finite_values:<n>/<total>`；否則 NaN 列→`nan_rows_dropped`；兩者皆有依 inf。禁 `LinAlgError` 逸出。③ **輸出端非有限（D-13）**：計算後驗回傳數值欄 `alpha/r_squared/intercept/unexplained/factor_betas.*/attribution.*`（**不含** `factor_means`，僅 local），任一非有限 → `non_finite_output:<field>`。④ **index 政策（D-5）**：驗 unique+monotonic+tz 一致；**不驗 freq**；允許間隙；**不限索引型別**（RangeIndex 須 PASS）；僅 object/mixed → `index_type_uncomparable`；aware 不同 tz → `index_tz_mismatch`。⑤ **成功路徑必補 `status:"ok"`（ADV-GROK-2；D-6 ok 形斷鏈）**：現行 analyzer 成功回傳**無 status**；本票須改為扁平 `{status:"ok", alpha,r_squared,intercept,unexplained,factor_betas,attribution}`。否則 D-6/TS discriminated union 驗不了。
- **驗證**（全 exit=0；`pytest tests/momentum/Analysis/test_factor_exposure_analyzer.py -q`；**禁用 deep JSON 作通過條件**）：
  - NaN：40 列含 1 NaN → `status=="unavailable"` 且 `"nan_rows_dropped:1/40" in reason`
  - inf：40 列含 1 `np.inf` → `unavailable` 且 `"non_finite_values:" in reason`，**不得 raise LinAlgError**
  - 輸出溢位：`portfolio` 含 `1e200`（輸入全有限）→ `unavailable` 且 `"non_finite_output:" in reason`
  - RangeIndex 須 PASS：`pd.Series(randn(120))`+`pd.DataFrame(randn(120,3))` → `status=="ok"`
  - 錯位索引：`range(100,220)` vs `range(0,120)` → `unavailable`、`nan_rows_dropped:200/220`（D-8 涵蓋）
- **邊界（12）**：① 全 NaN ② 全 inf ③ NaN+inf 混 ④ 單列 ⑤ 索引重複 ⑥ 亂序 ⑦ tz naive/aware 混 ⑧ aware 不同 tz ⑨ RangeIndex(PASS) ⑩ object/mixed(FAIL) ⑪ 間隙合法(PASS) ⑫ 輸入有限輸出溢位(unavailable)。
- **存活至**：Phase 5 後保留（fail-closed 永久，票A 仍適用）。
- **覆蓋風險**：無（票A 或放寬結構性 NaN 閾值屬調參非覆蓋）。
- 不可做：不得 fillna；不得 `try/except LinAlgError` 敷衍。

### Task 2.2 — 樣本不足假成功 → 顯式 unavailable（`:114-121`）
- 改法：回 `{"status":"unavailable","value":None,"reason":"insufficient_rows:<n><<min>"}`（**含 `value` 鍵**）；**足夠列數的成功路徑統一由 Task 2.1 ⑤ 的 `status:"ok"` 扁平形回傳**（ADV-GROK-2，勿留無 status 舊形）；門檻具名 `factor_exposure.attribution_min_rows` 預設 10（D-7）。**wiring 三處全做（ADV-C5/CM2）**：① `ic_config_schema.py FactorExposureConfig` 加欄（`ge=2` constraint）② `FactorExposureAnalyzer.__init__` 讀該鍵存 `self._attribution_min_rows`③ `calculate_factor_attribution` 的 `< 10` 硬編碼改讀 `self._attribution_min_rows`。**否則 config 加了欄但行為不可調＝D-7 名存實亡**。
- **驗證**：① 9 列 → `unavailable` 且 `"insufficient_rows:9" in reason`；② 10 列 → `status=="ok"`；③ override：config `attribution_min_rows=11` → 10 列變 `unavailable`（證 wiring）；④ **因子欄<2**（ADV-CM7）：單因子輸入 → `unavailable` 且 `"insufficient_factors:1<2" in reason`；⑤ **dropna 跌破門檻**（ADV-CM8）：12 列含 3 NaN 列（dropna 後 9 列<10）→ 依優先序 reason 為 `"nan_rows_dropped:3/12"`（**非** insufficient_rows，因丟列優先於樣本不足）。
- **邊界**：① 恰好 10 列 ② dropna 後才跌破門檻 ③ 因子欄 < 2（現行 `shape[1]<2` 回 NaN dict → 本票改 `unavailable`+`reason:"insufficient_factors:<n><2"`，ADV-CM7）。**reason 全局優先序（ADV-CM8）**：`inf(non_finite_values) > dropna(nan_rows_dropped) > insufficient_rows > insufficient_factors > non_finite_output`。
- **存活至**：Phase 5 後保留（門檻/語義永久）。
- **覆蓋風險**：無（門檻統一屬另票調參）。
- 不可做：不得為讓測試好過調低 `attribution_min_rows` 預設。

### B3 — 幽靈契約隔離（deep payload 驗收；依賴：B2）
### Task 3.1 — orchestrator stub → 顯式 unavailable + 外顯（D-4）
- 改法：① `:2213-2227` 巢狀 `factor_attribution` → `{"status":"unavailable","value":None,"reason":"attribution_not_wired_to_canonical_contract（單標的 canonical FR 下迴歸 ill-posed；接真需另定 portfolio_returns 與 RHS 契約，見 ROADMAP 票A/票B）"}`；**移除頂層鏡像** `alpha/r_squared/attribution/unexplained/factor_betas`。**reason 禁寫「系統沒有 PnL」**（通道存在但非 attribution-ready）。② 外顯改點（D-4，逐點寫死）：`:1852-1854` 回傳後檢查巢狀 `factor_attribution.status=="unavailable"` → `module_summary[module_name]="completed_partial"`（**不是 completed**）；`deep_analysis_types.py:24` docstring 列舉合法值；`ic_reporter.py:1174-1195` 附帶 `factor_attribution` 子狀態；`types.ts` 加 `completed_partial`。③ **計數（D-12，三點全改）**：`ic_filter_orchestrator.py:1904`、`:2394`、`factor_return_sanitizer.py:341` 皆將 `completed_partial` 計入 completed（`completed_count` 不變）。**型別約束**：`module_summary: dict[str,str]` 只能字串，必須 scalar 新值。
- **producer（ADV-GROK-3）**：B3 改完 orchestrator 後 `python scripts/ic1d_baseline_freeze.py --profile p3` 產 `handoffs/ic1d_baseline/p3_after_failclosed.json`。
- **驗證**（comparator 依 §G 20 路徑：`--allow-change` 3 attribution 子樹 + `module_summary.factor_exposure`，`--allow-remove` 15 三鏡像幽靈鍵）：
  - **完整命令（ADV-GROK-1 修；禁 brace——實測三組 `{}` 連寫爆成 251 詞笛卡爾積，非 15 條）**：`python scripts/ic1d_compare.py handoffs/ic1d_baseline/p1_after_rename.json handoffs/ic1d_baseline/p3_after_failclosed.json --allow-change results.factor_exposure.factor_attribution,results.factor_exposure.payload.summary.factor_attribution,results.factor_exposure.typed_result.payload.summary.factor_attribution,module_summary.factor_exposure --allow-remove results.factor_exposure.alpha,results.factor_exposure.r_squared,results.factor_exposure.attribution,results.factor_exposure.unexplained,results.factor_exposure.factor_betas,results.factor_exposure.payload.summary.alpha,results.factor_exposure.payload.summary.r_squared,results.factor_exposure.payload.summary.attribution,results.factor_exposure.payload.summary.unexplained,results.factor_exposure.payload.summary.factor_betas,results.factor_exposure.typed_result.payload.summary.alpha,results.factor_exposure.typed_result.payload.summary.r_squared,results.factor_exposure.typed_result.payload.summary.attribution,results.factor_exposure.typed_result.payload.summary.unexplained,results.factor_exposure.typed_result.payload.summary.factor_betas` exit=0（allow-remove **15 條逗號分隔字面路徑**已展開；allow-change 4 條；**路徑含 `handoffs/ic1d_baseline/` 前綴避免 cwd 歧義**，ADV-GROK-3）
  - `assert report.module_summary["factor_exposure"]=="completed_partial"`（**D-4 的牙齒**）
  - `assert report.completed_count == <p1 baseline 值>`（**須在 sanitize 之後取值**，D-12）
  - `assert "exposure_hash" 不變`（哨兵）
  - **flatten 三條**（僅驗列數不足）：① 驗 `factor_attribution` **子樹** 2→1（非整模組 4→3）② `assert any(r["path"].endswith("factor_attribution.status") and r["value"]=="unavailable" for r in rows)` ③ `factor_attribution.reason` 外部可讀。
- **邊界**：① cache-hit ② force 僅 exposure ③ 前端收到 unavailable 不崩。
- **存活至**：Phase 5 後保留（`unavailable`+`completed_partial` 是可觀測交付本體）。
- **覆蓋風險**：**有，屬預期**：票A 接線時把 `factor_attribution` 改實值覆蓋本形。不合併 Phase 因票A 前置（equity curve 契約+portfolio_returns canonical）不在本票，且誠實標示有獨立防假交付價值。
- 不可做：**不得**接真迴歸。

### B4 — 測試去固化 + mutation 探針（依賴：B2+B3）
### Task 4.1 — 去固化 + 7 支可證偽探針（D-2/composer-B4/codex-B4）
- 檔案：`tests/momentum/Analysis/test_factor_exposure_analyzer.py`、`tests/phase25/test_factor_exposure_analyzer.py`、新建 `tests/momentum/Analysis/test_ic1d_orchestrator_integration.py`。
- 改法：① 改寫 `test_nan_factor_returns_exposure`（兩檔孿生，現僅 `assert "factor_betas" in result`）→ 斷言 `status=="unavailable"`+reason。② 改寫 `test_factor_attribution_insufficient_rows`（僅 phase25:64）+ **補 momentum 側對稱測試**。③ **7 支 mutation 探針**（檔名/函式名寫死）：
  - **analyzer 檔 5 支**：`test_mutation_dropna_restored_must_fail`（D-8）、`test_mutation_insufficient_silent_nan_must_fail`（2.2）、`test_mutation_inf_passthrough_must_fail`（D-10）、`test_mutation_output_overflow_passthrough_must_fail`（D-13）、`test_mutation_index_policy_bypassed_must_fail`（D-5）。
  - **整合檔 2 支**：`test_mutation_stub_restored_must_fail`、`test_mutation_module_summary_completed_must_fail`（D-4；斷言 summary 退回 `completed` 則 FAIL）。
  - **oracle 獨立性**（codex-v2M3）：每探針斷言須引 §G baseline 或獨立算出的期望，禁以被測函式自身輸出當 oracle。
  - **關鍵反例**（codex-B4）：改回 dropna 後若樣本 `<10` 走舊路徑保留 `factor_betas` 鍵→舊斷言仍綠；新探針須確保此情境 **FAIL**。
- **cache-hit / force-only 具名測試（ADV-C6/CM4，寫死函式名+exact 三鍵 assert）**：整合檔須含 ① `test_cache_hit_factor_exposure_completed_partial`：`_deep_analysis_cache` 命中 → `assert report.module_summary["factor_exposure"]=="completed_partial"` 且 `results.factor_exposure.factor_attribution=={"status":"unavailable","value":None,"reason":<attribution_not_wired...>}`（三鍵 exact）；② `test_force_only_factor_exposure_unavailable`：`force_modules=['factor_exposure']` → 同上三鍵 exact + `module_summary=="completed_partial"`。**「僅驗列數不足」措辭釐清（C6）**：flatten 三條中「列數 2→1」是**必要非充分**條件，狀態外顯（status/reason 可讀）為**充分**條件，兩者 AND。
- **phase25 mutation gate 標記（ADV-CM1）**：`test_factor_exposure_analyzer.py`(phase25) 無 `test_mutation_*` → 首行加 `# MUTATION-PROBE: n/a — analyzer mutations 在 momentum 孿生檔`，否則 `mutation_probe_check.sh` 對該檔 rc=1。
- **驗證**：`bash scripts/mutation_probe_check.sh <momentum檔> <phase25檔> <整合檔>` exit=0（**必含第三檔**，否則 orchestrator 兩探針不進 gate＝D-4 牙齒落空；phase25 靠 n/a 標記過）；`pytest` 三檔 exit=0；測試數 momentum 5→>=8、phase25 11→>=13、整合檔 0→>=4（含 cache/force 二測）。
- **邊界**：① 未實作前 `mutation_probe_check` rc=1、實作後 exit=0（證 gate 會動）② 既有 16 passed 不得下降。
- **存活至**：Phase 5 後保留（測試+7 探針為永久護網）。
- **覆蓋風險**：無（票A 需新增測試非覆蓋既有）。
- 不可做：不得放寬/刪除既有斷言換綠燈；不得快照替代行為斷言。

### B5 — 前端契約收尾（依賴：B3）
### Task 5.1 — TS 型別 + Radar 空狀態 + ExportButtons
- 檔案：`types.ts:2432-2459`（巢狀 `factor_attribution` 加 `{status,value,reason}`，位置=巢狀非頂層）、`FactorExposureRadar.tsx:13`、`ExportButtons.tsx:27`。
- 改法：① Radar 移除 fallback 鏈「讀 `factor_attribution.factor_betas` 當 exposure」的契約地雷。② `ExportButtons.tsx:27` `.filter(status==='completed')` → 接受 `['completed','completed_partial']`（否則 completed_partial 模組從匯出選單消失）。③ 前端其餘 `status === 'completed'`（**扣掉 ExportButtons 後 = 36 處單引號基準 / 40 含雙引號**;全體 37/41 見 SPEC D-4 實測）**逐一 triage** 標「模組狀態 vs 任務狀態」（任務狀態者不動）。
- **具名前端測試（ADV-C7/CM5）**：新建 `frontend/src/components/ic-analysis/FactorExposureRadar.test.tsx`——含 legacy payload（無 status，數值欄）與 new payload（`{status:'unavailable'}`）兩 fixture，斷言前者向後相容不崩、後者渲染空態不 throw。TS 型別採 discriminated union（`status?` 區分）。triage 產出 `handoffs/ic1d_frontend_status_triage.txt`（36 處單引號基準逐一標「模組狀態 vs 任務狀態」;計數以 SPEC D-4 的 `grep` 指令為準）。
- **驗證**：`cd frontend && npm run build` exit=0；`npx vitest run FactorExposureRadar` exit=0；`grep -c "factor_attribution?.factor_betas" frontend/src/components/ic-analysis/FactorExposureRadar.tsx` == 0；`grep -c "status === 'completed'" frontend/src/components/ic-analysis/ExportButtons.tsx` == 0（**N3 修:完整 repo-relative path,禁 `...`**）。
- **邊界**：① 注入 unavailable payload 渲染空態不 throw ② 舊 payload（無 status）向後相容不崩。
- **存活至**：Phase 5 後保留（TS 型別/Radar 修復永久）。
- **覆蓋風險**：**有，局部**：票A 接線後 `factor_attribution` ok 形需擴充 TS 型別（D-6 已載為票A 前置）；unavailable 形不被刪。
- 不可做：不得為配合新型別改 analyzer/orchestrator 回傳形（前端只做消費端適配）。

## §V 驗證策略
- **mutation**：7 支探針（analyzer 5 + 整合 2）+ `mutation_probe_check.sh`（含整合檔）exit=0；引 `docs/TEST_DESIGN_CHARTER.md` §B1.1「缺探針=BLOCKING」。
- **層級**：B0 baseline / B1 deep no-op+單元 / B2 單元 / B3 deep comparator / B4 mutation gate / B5 前端。皆可獨立 `pytest`/`npm`，不需 `run_api.py`。
- **防假綠**：Phase 4 diff 既有斷言；comparator 為唯一 golden 判準禁目視。
- **回歸盤點**：`test_zero_r_squared`（RangeIndex，D-5 放寬後維持不變）；`test_factor_attribution_insufficient_rows`（phase25，B2 後改寫+補 momentum）；`test_nan_factor_returns_exposure`（兩檔去固化）。

## §R 回退
- 每批獨立 commit 可單獨 revert；B1（deep no-op）風險最低；B2/B3 可獨立 revert 回 stub。
- flag 政策：B2/B3 fail-closed 經 pytest+mutation exit=0 後**預設 ON**；flag 僅逃生口。
- Golden comparator FAIL → 不 merge。

## §N N/A 登記
- **接真 attribution：N/A** — 單標的宇宙 OLS 只識別 position 重疊（票A/票B，Phase 4 或 ML epic）。
- **刪除 `unexplained`：N/A** — 遷移票。
- **真 residual IC：N/A** — 獨立議題。
- **exposure 家族其餘 NaN 靜默：N/A** — 他票。
- **FR `min_samples` 與 attribution 門檻統一：N/A** — 另票（D-7）。
- **真實 kline 三方簽核計畫：N/A** — 不碰 feature/kline 生成→計算→merge→split；模組級 golden 見 B0/B3。
