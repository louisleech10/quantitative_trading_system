# IC 1d — Factor Attribution 正名 / Fail-Closed / 幽靈契約隔離 — SPEC

> 來源：`handoffs/1d-RECHECK-SYNTHESIS.md`(四方複核) + `handoffs/1d-FEASIBILITY-SYNTHESIS.md`(四方可行性挑戰)
> 日期：2026-07-20　|　對應 TODO：`docs/IC1D_ATTRIBUTION_TODO.md` **v0.3**(已生成;與本 SPEC v0.5.2 同輪戳記凍結)　|　版本：**v0.5.2 ✅ FROZEN**（2026-07-21;三家戳記+provenance,機檢 PASS body sha256:4109a47b） | *前版 v0.5.1 FROZEN*（2026-07-21；制度案補欄後三家重新 APPROVED + provenance 完整，機檢 PASS `sha256:6ae5b9f9…`；含制度改動同輪受審。本體凍結，修改須重走戳記輪）
>
> **v0.2→v0.3 變更**：三家閉合複驗 **v0.1 BLOCKING 全數 CLOSED**（grok 5/5、codex 5/5、composer 4/5+1 PARTIAL），但三家皆 **FREEZE-BLOCKED**，交出 4 個新 BLOCKING，全數處理：
> ① **D-4 重寫**（三家一致判「只換措辭」）：實測 `module_summary: dict[str,str]` 只能存字串 → 改 scalar `"completed_partial"` + 四個改點逐一寫死。
> ② **§G Phase 3 白名單三重鏡像窮舉**（codex 實測 18 changed / 12 unlisted）：`summary` 同一物件被 `payload`/`typed_result.payload`/頂層展平三處引用 → 20 條路徑全列。
> ③ **D-10 inf 政策新增**（codex 獨家）：實測 inf → `LinAlgError` 逸出，v0.2 只規格 NaN，違反 §C 不弱化 inf gate。
> ④ **Phase 1 只加巢狀 intercept**（grok leaf-diff 雙分支）：不加頂層即消解「保留變新幽靈／刪除白名單漏列」兩難。
> 另補 D-11 comparator CLI 語法、tz/index 型別細則、mutation 探針檔案歸屬與 oracle 獨立性。
>
> **v0.1→v0.2 變更**：三家 adversarial 交出 15 BLOCKING(去重後 9 個獨立問題)全數處理。
> 主要重寫：§G golden 分層重做(廢除「byte 級一致」不可執行語義)、§P Phase 分層對齊實際程式層級、§V mutation 探針落實到檔名/函式名、新增 §D 設計裁決。
> **交付語彙**：本票=**幽靈契約隔離(explicitly not wired)**，**非**「接線修復」——完工後 `calculate_factor_attribution` production caller 仍為 0。此為三家一致要求，防假交付。

## §RISK 風險分級
- **大小**：**大**。
- **命中高風險原則**：
  - **(a) 數值/資料品質**：改 NaN 處理語意（靜默 dropna → fail-closed），影響輸出值與可用性判定。
  - **(b) 跨模組/共用路徑**：analyzer ↔ orchestrator ↔ deep JSON ↔ module_summary ↔ reporter flatten ↔ TS 型別 ↔ UI。
  - **(d) ML/回測正確性**：錯標欄位會誤導特徵選擇決策。
RISK-HIT: a,b,d
- 命中 (a)(d) → **§G Golden 必填、adversarial review 必跑**。

## §A 假設與待使用者確認

### 已驗證事實
- FACT-RECEIPT: `nl momentum/Analysis/factor_exposure_analyzer.py` → `:144 "alpha": float(beta[0])` 與 `:147 "unexplained": float(beta[0])` **同一表達式**（Composer 實跑 `alpha=-0.270368722045468, unexplained=-0.270368722045468, equal=True`，2026-07-20）
- FACT-RECEIPT: AST probe over `momentum/`+`api/` for `calculate_factor_attribution` → 印出 `0 production callers`（codex 實跑 2026-07-20）
- FACT-RECEIPT: `nl momentum/Analysis/ic_filter_orchestrator.py` → `:1854 base_report.module_summary[module_name] = "completed"` 對**任何正常回傳**無條件標記 completed；僅 `except ModuleUnavailableError`(`:1860-1867`) 才寫 unavailable（Claude 實跑複驗 2026-07-20）
- FACT-RECEIPT: `python -c` OLS toy `q=p1` → 印出 `β=[≈0,1,≈0], R²=1, max_resid=1.1e-16`（codex 實跑 2026-07-20）→ 單標的下迴歸只識別 position 重疊
- FACT-RECEIPT: `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_exposure_analyzer.py tests/phase25/test_factor_exposure_analyzer.py` → 印出 `rc=1`（兩檔皆無 `test_mutation_*`），但一般 `pytest` 仍 `16 passed`（codex 實跑 2026-07-20）
- FACT-RECEIPT: pandas index probe → 印出 `full hourly freq=<Hour>；gapped freq=None/infer=None；reconstructed freq=None/infer='h'；full.equals(reconstructed)=True`（codex 實跑 2026-07-20）→ **freq 屬性不可作為一致性判準**
- FACT-RECEIPT: reporter probe → 印出 `flatten_rows_before=2, flatten_rows_after=1`（Composer 實跑 2026-07-20）
- FACT-RECEIPT: `grep -c '^def test_'` → momentum 檔 **5**、phase25 檔 **11**；`test_factor_attribution_insufficient_rows` 僅 phase25:64（Composer 實跑）
- FACT-RECEIPT: freeze baseline `ic1cfr_full_baseline/{before,after_full}.json` 中 `factor_exposure` 狀態 = `skipped`（缺 close_series；codex/grok 實跑）

### 待使用者確認
**待確認：無**

### 已確認結果
- `2026-07-15 使用者定 1d scope：正名 + NaN fail-closed + 幽靈接線修復；真 residual IC 歸 Phase 2B`
- `2026-07-20 四方複核 + 四方可行性挑戰 CONVERGED：「接線修復」在本票的可達形式=顯式契約隔離(explicitly not wired)。根因=單標的宇宙下 ls_returnᵢ=positionᵢ⊙r、組合報酬=position_p⊙r 共用同一 r，OLS 只識別 position 重疊度而非風險曝險。接真拆票 A/B，階段=Phase 4 或 ML epic，不插隊 Phase 1`（技術決策，依 CLAUDE.md「技術決策委派委員會」；綜合見 `handoffs/1d-FEASIBILITY-SYNTHESIS.md`）

## §D 設計裁決（v0.2 新增；逐條對應 adversarial BLOCKING）

| # | 裁決 | 解決的 BLOCKING |
|---|---|---|
| **D-1 分層（v0.5 重寫：Phase 1 = pure analyzer only）** | **Phase 1 只改 analyzer 純函式，deep JSON no-op**。<br>**v0.4.5 曾要求「兩檔都改」，v0.5 撤銷**——三家 SIMPLIFY-YES 一致：orchestrator 側 Phase 1 加的巢狀 `intercept`，**Phase 3 會把整棵 `factor_attribution` 子樹換掉而一併刪除**，屬兩階段後即消失的**冗餘工作**；且 `unexplained` **零 runtime 消費者**（全 repo 僅 `types.ts:2443` optional 型別宣告，無程式讀值）→「遷移窗」是**假前提**（grok 語）。<br>**當初選 (A) 的理由已過期**（composer 自我推翻）：(A) 是為堵「測錯層/假交付」，但該洞現已由 **Phase 2 單元級 / Phase 3 deep 級**分層驗收堵死；grok-B1 當初的 **(B) pure-function only** 反而與現行分層一致。<br>**「為與 D-1 一致而必須做兩檔」是循環論證**（grok）：因當初選 (A) 才需兩檔；改 (B) 後 D-1 本應重寫。<br>**可觀測交付落在 Phase 3**（unavailable + `completed_partial`），非 Phase 1。**Phase 2 只改 analyzer 純函式，驗收=單元級 golden，禁用 deep JSON 作通過條件**。**Phase 3 改 orchestrator，驗收=deep payload**。 | grok-B1, codex-B1, grok-B5 |
| **D-2 golden 語義** | **廢除「byte 級一致」措辭**（不可執行：加鍵必然改 sha256）。改為 **canonical comparator + allow-add 白名單**：白名單路徑允許「新增」，其餘路徑 exact 比對，**任何未列路徑的新增/刪除/值變 = FAIL**。沿用 `scripts/ic1cfr_stopgap_freeze.py:934-974 compare_non_fr_paths_exact` 模式。 | composer-B1, grok-B2, codex-B3 |
| **D-3 factor_betas 不改鍵名** | Phase 1 對 `factor_betas` **只改 docstring/變數名，不動 JSON 鍵**（避免與既存 `portfolio_exposure:2214` 撞車）。錯標的 `factor_betas` 幽靈鍵**在 Phase 3 隨 stub 一併移除**，屬象限 II。 | composer-B2 |
| **D-4 module_summary 外顯（v0.3 重寫；原版被三家判「只換措辭」）** | **型別約束（實測）**：`deep_analysis_types.py:24 module_summary: dict[str, str]` **只能存字串**；`api/models/ic_models.py:207 ModuleStatusResponse.status: str`。→ **巢狀 status 在型別上不可行**（codex probe：nested → `rejected string_type`）。**裁決=採 scalar 新狀態值**：`factor_exposure` 模組整體仍有效（exposure/concentration），但 attribution 子項不可用 → module_summary 寫入**新 scalar 值 `"completed_partial"`**。**改點寫死**：① `ic_filter_orchestrator.py:1852-1854`（runner 回傳後檢查巢狀 `factor_attribution.status=="unavailable"` → 寫 `"completed_partial"` 而非 `"completed"`）② `deep_analysis_types.py:24` docstring 列舉合法值 ③ `ic_reporter.py:1174-1195 _build_module_summaries` 附帶 `factor_attribution` 子狀態 ④ TS `types.ts` 對應。**不 raise**（raise 會連帶下架有效的 exposure/concentration）。<br>**⚠️ v0.4 前端消費者掃描（codex-v3B4；Claude 首次 grep 誤用 `head -10` 截斷，結論失真）**：前端 `status === 'completed'` 精確計數（**v0.4.3 修正；codex-v4M2 指出 46 有誤**）：`grep -rn "status === 'completed'" frontend/src --include="*.ts" --include="*.tsx" | wc -l` → **37**；含雙引號變體 `grep -rnE "status === ['\"]completed['\"]"` → **41**（Claude 實測 2026-07-20；先前「46」來自較寬鬆 pattern `=== *['\"]completed['\"]` → 50，已作廢）。**必修**：`frontend/src/components/ic-analysis/ExportButtons.tsx:27` `.filter((item) => item.status === 'completed')` → `completed_partial` 模組會**從匯出選單消失**，與 D-4「exposure/concentration 仍有效可用」直接矛盾。**改法**：該 filter 改為接受 `['completed','completed_partial']`。**其餘 36 處（單引號基準）/ 40 處（含雙引號）**須於 Phase 5 逐一 triage 並在 TODO 標記「模組狀態 vs 任務狀態」分類（任務狀態者不動）。**驗證**：`grep -c "status === 'completed'" frontend/src/components/ic-analysis/ExportButtons.tsx` == 0。 | codex-B2, composer-v2B2, grok-v2B1, codex-v3B4 |
| **D-10 非有限值（inf）政策（v0.3 新增）** | **實測反例**：`f1` 含 1 個 `inf` → `calculate_factor_attribution` raise `LinAlgError: SVD did not converge`（Claude 實跑複驗 2026-07-20），**非** graceful unavailable。v0.2 只規格 NaN，違反 §C「不得弱化 NaN/inf gate」。**裁決**：`lstsq` **之前**統一檢查非有限值（`~np.isfinite`），NaN 與 inf 走**同一個檢查點** fail-closed；**禁**讓 `LinAlgError` 逸出。<br>**⚠️ v0.4.1 reason 優先序消歧（codex-v3M2；v0.3 措辭自相矛盾）**：「同路徑」指**同一個檢查點**，非同一個 reason 字串。優先序寫死：<br>① **存在 inf** → `"non_finite_values:<n>/<total>"`（inf 代表資料損壞，**不套用「丟列」政策**）<br>② **否則存在 NaN 列** → `"nan_rows_dropped:<n>/<total>"`（可丟列語義，D-8 閾值 0）<br>③ 兩者皆有 → 依 ① 回報 inf（較嚴重者優先）。<br>**輸出端**另見 D-13（`non_finite_output:<field>`），三者互斥不重疊。 | codex-v2B2, codex-v3M2 |
| **D-12 `completed_partial` 的計數語義（v0.3 新增；Claude 自查，非委員提出）** | **實查反例**：`ic_filter_orchestrator.py:1903-1905` `completed_count = sum(1 for status in module_summary.values() if status == "completed")`。引入 `"completed_partial"` 會使 `factor_exposure` **不被計入** → `completed_count` 少 1 → 這是 report envelope 欄位，**會進 golden diff 且不在 §G 白名單**。**裁決**：`completed_partial` **應計入** `completed_count`（模組確實執行並產出有效 exposure/concentration，僅子項不可用）→ **改點寫死**：`:1903-1905` 條件改為 `status in ("completed", "completed_partial")`。**效果**：`completed_count` **維持不變** → 不需列入白名單，且語義正確。<br>**⚠️ v0.3.1 補（grok-v3B1；Claude 首次自查遺漏）**：只改 orchestrator **不夠**——`factor_return_sanitizer.py:335-355 _recompute_status_counts` 會在 `_sanitize_deep_report_factor_returns`(`:1911`) 中**重算並覆寫** `completed_count`/`skipped_count`/`deep_analysis_summary.completed`，且該遞迴walk **不限 factor_returns**（`:341 completed = _count_status(statuses, "completed")`）。若不同步，orchestrator 的修正會被 sanitize **打回 −1**。**第二改點寫死**：`_count_status`（或其呼叫點 `:341`）須將 `"completed_partial"` 一併計入。<br>**v0.4 完整掃描結果（Claude 不截斷全掃，共 **3** 個計數點，缺一即漂移）**：① `ic_filter_orchestrator.py:1904` ② `ic_filter_orchestrator.py:2394`（net_ic 下架路徑重算，v0.3 遺漏）③ `factor_return_sanitizer.py:341`。**三處全改**。（後端其餘 `== "completed"` 比較：`api/routes/pattern_analysis.py:1164`、`api/services/search_task_service.py:383` 皆為**任務狀態**非模組狀態，**不受影響**。）**驗證**：`assert report.completed_count == <p1 baseline 值>` **且**須在 `_sanitize_deep_report_factor_returns` **之後**取值（否則測到假綠）。<br>**已排除的誤報**（Claude 追查後確認**非**破壞）：`_PRESERVE_SUMMARY_STATUSES:46-48` 雖不含新值，但 `:174-188` 迴圈僅對 `_FACTOR_RETURNS_KEY` 正規化，其餘模組走 `:188 else: _sanitize_node(mv)` 原樣通過 → 狀態字串本身不受影響。**實作者勿誤改該 frozenset**；要改的是**計數**（`:341`），不是**正規化白名單**。 | Claude 自查 + grok-v3B1 |
| **D-11 comparator 語法規格（v0.3 新增）** | `scripts/ic1d_compare.py` CLI 寫死：`python scripts/ic1d_compare.py <before.json> <after.json> [--allow-add P1,P2] [--allow-change P1,P2] [--allow-remove P1,P2]`。**路徑語法（v0.3.1 修正；grok-v3B3）**：三個 `--allow-*` flag 一律採 **subtree 語意**——所列路徑代表「**該節點及其下所有葉**」。<br>**為何不用 leaf exact**：`factor_betas` 是 **dict（feature 名 → 值）**，其葉為 `factor_betas.<feature_name>`，而 feature 名**隨資料而變、無法在 SPEC 靜態窮舉**；同理 `attribution`。若採 leaf exact，`--allow-remove ...factor_betas` 將**匹配不到任何葉** → Phase 3 必假 FAIL。<br>**過度寬鬆的防範**：SPEC 白名單須列**最窄節點**；且 `exposure_hash` / `portfolio_exposure` / `concentration` 等**不在任何白名單內**，任何變動仍 FAIL（哨兵不受 subtree 語意影響）。<br>**NaN canonical**：NaN 視為與 NaN 相等（mask 比對），NaN↔數值 視為變更。exit 0=PASS，exit 1=印出違規路徑清單。 | codex-v2M1, grok-v3B3 |
| **D-5 index 政策（v0.4 放寬；codex-v3B5）** | **禁用 `freq` 屬性作判準**（實測 gapped/reconstructed 皆 `freq=None`，正常資料會誤判）。政策=**只驗 unique + monotonic increasing + tz-awareness 一致**；**允許時間間隙**（crypto 常態）。<br>**⚠️ v0.4 撤銷「須為 DatetimeIndex」**：v0.3 曾規定非 `DatetimeIndex` → unavailable，**過嚴且會造成既有測試回歸**——`tests/momentum/Analysis/test_factor_exposure_analyzer.py:40-47 test_zero_r_squared` 使用 `pd.Series(np.random.randn(120))`（預設 **RangeIndex**）並斷言 finite，屬**正當測試**（測 R²≈0 行為，與索引無關）。**裁決**：**不限索引型別**；RangeIndex 因 unique+monotonic 而通過。僅 `object`/mixed dtype 等**無法可靠比較**的索引 → unavailable(`reason:"index_type_uncomparable"`)。**理由**：索引「型別」非正確性問題，「對齊」才是。 | grok-B3, codex-B5, codex-v3B5 |
| **D-13 輸出端非有限值（v0.4 新增；codex-v3B3）** | **實測反例**：輸入**全部有限**（`portfolio` 含 `1e200`）→ Claude 實跑得 `ALL_INPUT_FINITE True` 但 `r_squared=nan`、`alpha=2.43e+198`，`analyzer:131-132` 計算 `ss_res/ss_tot` 時 overflow。→ **D-10 的輸入端 gate 擋不住此類**。**裁決**：除輸入端檢查外，**計算後**再驗**實際回傳的數值欄**是否有限——`alpha`、`r_squared`、`intercept`、`unexplained`、`factor_betas.*`、`attribution.*`（**v0.4.3 修正；codex-v4M1**：v0.4 誤列 `factor_means`，該值僅為 `:137` local 中間變數、**不在回傳中**，無法作為 gate 欄位）；任一非有限 → `{"status":"unavailable","value":None,"reason":"non_finite_output:<field>"}`。**禁**回傳含 NaN/inf 的「成功」結果。**驗證**：`portfolio` 含 `1e200`（輸入有限）→ `assert result["status"]=="unavailable"` 且 `"non_finite_output:" in result["reason"]`；mutation：移除輸出端檢查 → 該測試須 FAIL。 | codex-v3B3 |
| **D-6 回傳 envelope 統一（v0.4.3 釘死 schema；codex-v4B1）** | v0.4.2 只說「含 `status`」，**未定成功時欄位在頂層還是 `value` 內** → 實作與驗收必分歧。**裁決＝扁平＋status（backward-compatible）**：<br>**ok**：`{"status":"ok", "alpha":float, "r_squared":float, "intercept":float, "unexplained":float, "factor_betas":{...}, "attribution":{...}}`（數值欄**維持頂層**）<br>**unavailable**：`{"status":"unavailable", "value":None, "reason":str}`（**無**數值欄）<br>**為何選扁平**：既有正當測試以頂層存取（`test_zero_r_squared` `assert np.isfinite(result["alpha"])`），改巢狀 `value` 會造成**非必要的回歸**；且 `unavailable` 分支保留 `value:None` 以對齊 `net_ic` 慣例。<br>**不是雙軌**（grok-M1 原慮）：兩分支**皆有 `status`**，消費者一律先讀 `status` 再取值；「失敗無 alpha」是刻意契約（**禁**回傳假數值）。<br>**落地**：Task 2.1 / 2.2 / 3.1 失敗形一律 `{status,value,reason}` 三鍵；§V 既有頂層斷言在 **ok 分支維持有效、無需改寫**。<br>**⚠️ 適用層級消歧（v0.4.3 補；防與 D-1 混淆）**：本裁決規範的是 **analyzer 純函式 `calculate_factor_attribution` 的回傳**。orchestrator deep JSON 內的 `results.factor_exposure.factor_attribution` 是**另一層**——本票 Phase 3 後它**恆為** unavailable（production caller=0，見 §N），故同樣是 `{status,value,reason}` 三鍵，兩層在**本票範圍內形狀一致**。TS `types.ts` 依此建模。**若未來票 A 真接線**，該巢狀節點的 ok 形應採本裁決的扁平欄位（`status:"ok"` + 數值欄），**屆時須同步更新 TS 型別**——此為票 A 的前置，不在本票。 | grok-M1, codex-M1, codex-v4B1 |
| **D-7 門檻具名可配置** | 新增 config key `factor_exposure.attribution_min_rows`，**預設 10**（沿用現值，不擅改數值語意）；FR `min_samples=30` 的統一議題**明確另票**。 | codex-M3, grok-M4 |
| **D-8 dropna 閾值** | 本票 analyzer 純函式維持**任何丟棄即 unavailable**（閾值 0），因 production caller=0、無現網衝擊。**但明記**：票 A 接真時須先定「結構性 NaN（lag warmup）豁免或比例閾值」，否則 `market_proxy` 前 2 列 NaN 即全面 unavailable。 | composer-M2, grok-M3 |
| **D-9 baseline provenance** | Phase 0 close carrier **須走 production 同源路徑**（`ic_filter_orchestrator.py:2913-2930` carrier 寫入），**禁**直接 ad-hoc 塞 `_ic_cache`；並斷言同源。Phase 1/2/3 的「行為不變」錨點=**Phase 0 新 baseline**，**非** `ic1cfr` freeze（後者 exposure 為 skipped，不可比）。 | composer-B5, codex-M4 |

### §D-MAP 裁決↔落地對照（v0.4.2 新增；**每次修訂 §D 必須同步檢查本表**）

> **為何有這張表**：v0.1→v0.4 期間**連續四次** BLOCKING 源於「改了 §D 裁決卻沒同步改對應的 §P Task / §G 白名單」（composer-v3B1、grok-v3B2、grok-v4B1、composer-v4B1）。眼睛掃會再漏，故做成對照表；**修訂任一 D-N 時，須逐一確認下列落地點皆已同步**。

| 裁決 | 落地點（全部須一致） |
|---|---|
| D-1 分層（v0.5） | Task 1.1 **僅 analyzer 檔**；§G Phase 1 **allow-add=0 / deep no-op**；Phase 2/3 分層驗收 |
| D-2 golden 語義 | §G comparator 段；各 Task 驗證指令 |
| D-3 factor_betas 不改鍵名 | Task 1.2 改法；§G Phase 3 allow-remove |
| D-4 completed_partial | Task 3.1 外顯改點**與 flatten 三條驗收（範圍/狀態外顯/reason 可見）**；§G Phase 3 allow-change `module_summary`；Task 5.1 前端；D-12 計數 |
| D-5 index 政策 | **Task 2.1 index 段 + 邊界⑨⑩**；§V 回歸盤點 |
| D-6 envelope | Task 2.1/2.2/3.1 的**失敗形**（三鍵 `{status,value:None,reason}`）；**ok 形無 `value`**（扁平數值欄 + `status:"ok"`）。**v0.4.4 修正（composer-v5B1）**：本列原寫「皆須含 `value`」，與 D-6 的 ok 分支**直接矛盾**——`value` 只存在於 unavailable 分支。 |
| D-7 門檻具名 | Task 2.2 改法與 reason |
| D-8 dropna 閾值 | Task 2.1 改法；§N 票 A 前置 |
| D-9 baseline provenance | Task 0.1 改法與驗證 |
| D-10 輸入端非有限 + reason 優先序 | **Task 2.1 輸入端段 + 驗證 NaN/inf 兩條** |
| D-11 comparator 語法 | §G comparator 段；Task 1.1/1.2/3.1 的 `--allow-*` 指令 |
| D-12 計數三點 | **三個計數點**：`ic_filter_orchestrator.py:1904`、`ic_filter_orchestrator.py:2394`、`factor_return_sanitizer.py:341`（v0.4.4 補列；codex-v5m2：本列原未點名，與正文三點不一致）；Task 3.1 驗證 `completed_count` 斷言（須在 sanitize **之後**取值） |
| D-13 輸出端非有限 | **Task 2.1 輸出端段 + 驗證 `1e200` 條 + Phase 4 mutation 探針** |

## §C 約束
- 解耦 7 條：不新增 `momentum/`→`api/` import；不新增服務互 import；DTO 不跨界。
- **不得弱化 NaN/inf gate**（本票方向為強化）；不擅改輸出大小（新增/移除鍵須在 §G 白名單明列）。
- **下游消費者全清單**（審查補齊）：deep JSON → `ic_reporter._flatten_module_rows` 展平匯出、`_build_module_summaries:1174-1195`(`keys/size`)、`typed_result`+`consumer_deny:2262`、TS `types.ts:2432-2459`、UI `FactorExposureRadar.tsx:13` / `FeatureTierPanel.tsx:50`。
- **pre-existing 不在本票**：Rule 4 `api/services/pattern_management_service.py:78`（codex-m1，baseline 債）；`ModuleUnavailableError` 死碼清理（grok-m2）。

## §G Golden / Baseline

- **feature/kline 條件**：本票不改 feature/kline 生成/計算/merge/split → 不適用真實 kline 三方簽核計畫；但屬 (a)(d)，須模組級 golden。
- **前置阻斷**：現有 freeze fixture 缺 `close_series` → `:2174-2179` raise `InvalidInputError` → 整模組 skipped，**凍不到值**。Phase 0 必先解（依 D-9 走 production 同源路徑）。
- **baseline 存放**：`handoffs/ic1d_baseline/{p0_before.json,p1_after_rename.json,p3_after_failclosed.json}`（gitignored；摘要 json/txt 入 commit）。
- **comparator**（D-2；**唯一通過判準，禁目視**）：`scripts/ic1d_compare.py`（新建，沿用 `ic1cfr_stopgap_freeze.py:934-974` 模式）
  - 輸入：兩份 json + allow-add 路徑白名單 + allow-remove 路徑白名單
  - 行為：白名單外任何路徑的**新增/刪除/值變/NaN mask 變** → 印出該路徑與 diff → **exit 1**
  - 數值容差：`nan_ratio` exact；float `abs<=atol(1e-12)` 或 `rel<=rtol(1e-9)`；鍵集合 sha256 記錄於報告
- **Phase 1 通過條件**（正名，**deep JSON no-op**；v0.5 簡化）
  - **allow-add 白名單 = 空集合（0 條）**。Phase 1 **不改 orchestrator**，故 deep JSON **完全不變**：
    `python scripts/ic1d_compare.py p0_before.json p1_after_rename.json` （**不帶任何 `--allow-*`**）exit=0
  - **為何比 v0.4.5 更嚴**：舊版允許新增 3 條路徑；新版**一條都不准變**（0 白名單 vs 3 允許新增），對「防誤改產品輸出」是**更強**的閘門，且更簡單。
  - **數值守恆改由 analyzer 單元承擔**（grok 指出）：orchestrator 側回的是**寫死 NaN stub**，用它證明「正名沒偷改數值」證明力極弱（NaN→NaN）。真正的守恆驗證放在 analyzer 單元測試（**真實 OLS**，`pytest tests/momentum/Analysis/test_factor_exposure_analyzer.py -q` exit=0）：
    `assert result["intercept"] == result["unexplained"] == result["alpha"]`（同值）
    且與 Phase 0 記錄的 analyzer 基準值逐欄比對（真實數值，非 stub）。
- **Phase 2 通過條件**（analyzer 純函式，**單元級 golden，不碰 deep JSON**；D-1）
  - 對 `calculate_factor_attribution` 直接呼叫的回傳 schema 做斷言；**禁**以 deep JSON 鍵變更作為 Phase 2 通過條件
- **Phase 3 通過條件**（deep payload，allow-change/allow-remove **窮舉**）
  - **⚠️ 三重鏡像（v0.3 新增；codex-v2B1 / composer-v2B1）**：`summary` 是**同一物件被三處引用**（Claude 實查 `ic_filter_orchestrator.py:2243-2265`）：
    ① `payload = ExposurePayload(summary=summary)` → `payload.summary.*`
    ② `typed = FactorModuleResult(payload=payload)` → `typed_result.payload.summary.*`
    ③ `out.update(summary)` → 頂層展平
    → **改 `summary` 一次，三處同動**。v0.2 只列頂層 → comparator 必 FAIL 12 條未列路徑（codex 實測 `changed_paths=18, unlisted=12`）。
  - **allow-change（3 條）**：
    `results.factor_exposure.factor_attribution`、
    `results.factor_exposure.payload.summary.factor_attribution`、
    `results.factor_exposure.typed_result.payload.summary.factor_attribution`
    （各為子樹根 → `{status,value,reason}`；依 D-11 須用 `--allow-change` 明示遞迴）
  - **allow-remove（15 條 = 5 鍵 × 3 鏡像）**：
    `results.factor_exposure.{alpha,r_squared,attribution,unexplained,factor_betas}`、
    `results.factor_exposure.payload.summary.{alpha,r_squared,attribution,unexplained,factor_betas}`、
    `results.factor_exposure.typed_result.payload.summary.{alpha,r_squared,attribution,unexplained,factor_betas}`
  - **allow-change（連帶）**：`module_summary.factor_exposure`（`completed` → **`completed_partial`**，D-4）、reporter flatten 列數（**預期 2→1**，須明載於 baseline 報告並附實跑 receipt）
  - **exact 不變**：`portfolio_exposure`、`neutralized_portfolio_exposure`、`concentration`、`neutralization_*`、
    **`exposure_hash`**（實查 `:2236-2242` 僅由 `summary["portfolio_exposure"]` 計算，attribution 變動**不影響**；若實作後 hash 變 = 有人動了 exposure = **FAIL**，此為刻意的哨兵）
  - **合計白名單 = 3 change + 15 remove + 2 連帶 = 20 路徑**；任何未列路徑變動 = FAIL

## §P Phase 與依賴

### Phase 0 — Baseline 前置（依賴：無）
**Task 0.1 — production 同源 close carrier + 凍 baseline**
- 目標：讓 `factor_exposure` 在 freeze 路徑真正跑起來，取得非空 golden。
- 檔案：baseline 產生腳本（沿用 `ic1cfr_full_baseline/` 模式）+ `scripts/ic1d_compare.py`；**不改 production**。
- 改法（D-9）：close carrier **經 production 路徑**（`ic_filter_orchestrator.py:2913-2930`）注入，禁 ad-hoc 塞 `_ic_cache`；dump `p0_before.json`。
- **驗證（可證偽）**：`p0_before.json` 中 `results.factor_exposure` 的 `module_summary` != `skipped` 且 `portfolio_exposure` 非空；斷言 carrier 來源 == production 路徑（assert 同源，非僅非空）。指令：`pytest tests/momentum/Analysis/test_ic1d_baseline.py -q` exit=0
- **邊界**：① **（v0.5.2 errata；C3 三家裁決 HYBRID）** baseline **一律使用有效 close**（非空、非全 NaN）。現行 production `:2174-2180` 僅拒 `None`、不拒 all-NaN（reindex→NaN market_proxy→靜默續算），屬 **pre-existing production-hardening 缺口，本票不修、另票追蹤**；本 Task **不**以 all-NaN raise 為 B0 通過條件（原「須 raise」措辭與「不改 production」互斥,已改述）。② close 長度短於 features → 現行 reindex 產 NaN，由 baseline 值檢查捕捉 ③ 時間軸有間隙（crypto 常態）→ 須正常通過（D-5）。
- 不可做：不得為求 baseline 非空而放寬 `:2174-2179` 的 close 檢查。

- **存活至**：Phase 5 完工後**保留**：`p0_before.json` 為全程對照基準；`scripts/ic1d_compare.py` 為長期工具（票A/票B 可複用）。
- **覆蓋風險**：**無**。baseline 與 comparator 不被任何後續 Phase 刪除或覆蓋。
### Phase 1 — 正名（**deep JSON no-op**；依賴：Phase 0）
**Task 1.1 — `unexplained` 正名（**僅 analyzer 純函式**；D-1 v0.5）**
- 目標：`unexplained` = `beta[0]` = alpha，名實不符。
- 檔案：**只有** `momentum/Analysis/factor_exposure_analyzer.py:142-148`。**不改 orchestrator**（v0.5：其巢狀 `factor_attribution` 由 Phase 3 整棵替換，先正名為冗餘工作）。
- 改法：回傳新增 `"intercept"` 指向同值；`"unexplained"` **保留**為 deprecated alias（**縮小解凍面**：三家建議不在本輪一併移除 alias，避免擴大修訂範圍；移除歸遷移票）。docstring 註明「非殘差；`residual`(`:129`) 僅用於 R²，**禁**順手改為 `unexplained=mean(residual)`」。
- **驗證（可證偽；全部 exit=0，指令見各子項 pytest / scripts/ic1d_compare.py）**：
  - **deep no-op**：`python scripts/ic1d_compare.py p0_before.json p1_after_rename.json`（**不帶任何 `--allow-*`**）exit=0 —— 任何 deep 變動 = FAIL（比 v0.4.5 的 allow-add×3 更嚴）
  - **analyzer 單元**（真實 OLS，非 stub）：`assert result["intercept"] == result["unexplained"] == result["alpha"]`；且三者與 Phase 0 記錄之 analyzer 基準值逐欄相等
  - `pytest tests/momentum/Analysis/test_factor_exposure_analyzer.py -q` exit=0
- **邊界**：① 樣本不足/unavailable 分支下 `intercept` **不應出現**（D-6：失敗形僅三鍵）② 既有頂層斷言（`test_zero_r_squared`）不受影響。
- 不可做：**不得**改 orchestrator（v0.5 明確排除）；**不得刪除** `unexplained`（歸遷移票）。

- **存活至**：Phase 5 完工後**保留**：analyzer 的 `intercept` 是永久正名，票A 接線時直接使用。
- **覆蓋風險**：**無**（v0.5 已砍掉會被覆蓋的部分）：v0.4.5 曾要求同步改 orchestrator，該產出會被 Phase 3 整棵替換＝白工，經三家 SIMPLIFY-YES 移除。
**Task 1.2 — `factor_betas` / positions 語意正名（僅註解，不動鍵；D-3）**
- 檔案：`ic_filter_orchestrator.py:2186`（`positions` → `equal_time_weights`，變數名）、`factor_exposure_analyzer.py:86-102` docstring
- 改法：`positions` 變數更名並補 docstring 說明其為**時間軸等權平均**（`len()`=列數非標的數），**非交易持倉**。`factor_betas` **JSON 鍵不動**（Phase 3 移除）。
- **驗證（可證偽）**：`python scripts/ic1d_compare.py handoffs/ic1d_baseline/p0_before.json handoffs/ic1d_baseline/p1_after_rename.json` exit=0（**零 allow-add,不帶任何 flag**，本 Task 不得改變任何輸出；errata v0.5.2:禁 `...`）；`grep -c "equal_time_weights" momentum/Analysis/ic_filter_orchestrator.py` >= 1
- 不可做：不得改動 `calculate_portfolio_exposure` 的計算。

- **存活至**：Phase 5 完工後**保留**：`equal_time_weights` 變數名與 docstring 屬 runner／`calculate_portfolio_exposure` 本體，非 stub 區。
- **覆蓋風險**：**無**。本 Task **不動 JSON 鍵**（D-3）；Phase 3 移除的是 `factor_betas` **鍵**，與本 Task 的註解/變數名正名不重疊。
- **邊界**：① `equal_time_weights` 更名後所有引用點須同步（`grep` 舊名殘留=0）② docstring 正名不得改變 `calculate_portfolio_exposure` 的回傳值。
**Task 1.3 — UI copy 正名**
- 檔案：`FeatureTierPanel.tsx:50`（**v0.5.2 errata；N1**：移除 `types.ts`，型別歸 Task 5.1，本 Task 僅 copy）
- **驗證（可證偽）**：`cd frontend && npm run build` exit=0；`grep -c "因子曝險歸因" frontend/src/components/ic-analysis/FeatureTierPanel.tsx` == 0；`npx tsc --noEmit` exit=0

- **存活至**：Phase 5 完工後**保留**：UI copy 正名為永久。
- **覆蓋風險**：**無**。
- **邊界**：① 舊 copy 出現在其他語系/aria-label（須一併掃）② `DeepAnalysisConfigPanel.tsx:29` 既有 tip 已較乾淨，勿誤改。
- 不可做：不得順手改動 Radar 以外的其他圖表 copy（超出本票範圍）。
### Phase 2 — analyzer fail-closed（**單元級驗收**；依賴：Phase 1）
**Task 2.1 — 非有限值靜默 → fail-closed（`:109-112`）**
- 改法：計算 dropna 前後列數，任何丟棄 → 回 `{"status":"unavailable","value":None,"reason":"nan_rows_dropped:<n>/<total>"}`（D-6 統一 envelope**含 `value` 欄**、D-8 閾值 0）。
- **輸入端非有限值（D-10）**：`lstsq` **之前**以 `~np.isfinite` 統一檢查（**同一個檢查點**）；**reason 優先序**：有 inf → `"non_finite_values:<n>/<total>"`；否則有 NaN 列 → `"nan_rows_dropped:<n>/<total>"`；兩者皆有依 inf 回報。**禁**讓 `LinAlgError` 逸出。
- **輸出端非有限值（D-13；v0.4.1 補入本 Task）**：計算後驗**實際回傳的數值欄**（v0.4.3 修正；codex-v4M1：`factor_means` 僅為 local 中間值、不在回傳中）：`alpha`、`r_squared`、`intercept`、`unexplained`、`factor_betas.*`、`attribution.*`，任一非有限 → `{"status":"unavailable","value":None,"reason":"non_finite_output:<field>"}`。**禁**回傳含 NaN/inf 的「成功」結果。
- **索引錯位由 D-8 涵蓋（v0.4.4 明文；composer-v4M2 OPEN 之結案依據）**：兩側索引無交集/部分交集時，`concat` 產生 union、`dropna` 大量收縮 → **D-8「任何丟棄即 unavailable」直接命中**，不需另立 `index_misaligned` 裁決。
  **Claude 實測**：`portfolio index=range(100,220)` + `factors index=range(0,120)` → `union_rows=220, after_dropna=20, dropped=200` → D-8 判定 **unavailable**。
  （Composer R5 的 OPEN 是在**現行未實作碼**上測得 `r_squared=0.102` finite，屬實作前行為，非 SPEC 缺口；grok R4 亦獨立得同結論。）
  **驗證**：錯位索引輸入 → `assert result["status"]=="unavailable"` 且 reason 為 `nan_rows_dropped:200/220`。
- **index 政策（D-5；v0.4.1 同步放寬——原文與 §D 矛盾，已改）**：驗 unique + monotonic increasing + tz-awareness 一致；**不驗 freq**；**允許間隙**。
  **⚠️ 不限索引型別**：`RangeIndex` 等非 `DatetimeIndex` 只要 unique+monotonic **即通過**（v0.3 曾規定非 DatetimeIndex → unavailable，**已撤銷**：會使既有正當測試 `test_zero_r_squared` 回歸失敗，見 §V 回歸盤點）。
  僅 `object`/mixed dtype 等**無法可靠比較**者 → unavailable(`reason:"index_type_uncomparable"`)；兩側**皆 naive** 或 **皆 aware 且 tz 相同** 才通過，**aware 但不同 tz** → unavailable(`reason:"index_tz_mismatch"`)。
- **驗證（可證偽；全部須 exit=0，指令見各子項 pytest / scripts/ic1d_compare.py）**：
  - NaN：40 列含 1 列 NaN → `assert result["status"]=="unavailable"` 且 `"nan_rows_dropped:1/40" in result["reason"]`
  - **inf**：40 列含 1 個 `np.inf` → `assert result["status"]=="unavailable"` 且 `"non_finite_values:" in result["reason"]`；**且不得 raise `LinAlgError`**（v0.3 前實測會 raise）
  - **輸出端溢位（D-13）**：`portfolio` 含 `1e200`（**輸入全有限**）→ `assert result["status"]=="unavailable"` 且 `"non_finite_output:" in result["reason"]`（Claude 實測 v0.4 前得 `r_squared=nan` 卻回「成功」）
  - **RangeIndex 須 PASS**：`pd.Series(np.random.randn(120))` + `pd.DataFrame(np.random.randn(120,3))` → `assert result["status"]=="ok"`（護欄：防實作者誤加 DatetimeIndex 硬性要求而弄紅 `test_zero_r_squared`）
  - 指令 `pytest tests/momentum/Analysis/test_factor_exposure_analyzer.py -q` exit=0。**禁**以 deep JSON 作通過條件（D-1）。
- **邊界**：① 全 NaN ② 全 inf ③ NaN+inf 混合 ④ 單列 ⑤ 索引重複 ⑥ 索引亂序 ⑦ tz-aware vs naive 混用 ⑧ 兩側 aware 但不同 tz ⑨ **RangeIndex（須 PASS）** ⑩ `object`/mixed dtype index（須 FAIL→unavailable）⑪ **有間隙但合法**（須 PASS）⑫ **輸入有限但輸出溢位**（須 unavailable）。
- 不可做：不得 fillna 補值；不得以 `try/except LinAlgError` 敷衍（須在 lstsq **前**攔截，否則無法區分成因）。

- **存活至**：Phase 5 完工後**保留**：analyzer fail-closed 為永久行為，票A 接線後仍適用。
- **覆蓋風險**：**無**。票A 未來可能放寬結構性 NaN 閾值（D-8 已載），屬**調參非覆蓋**。
**Task 2.2 — 樣本不足假成功 → 顯式 unavailable（`:114-121`）**
- 改法：回 `{"status":"unavailable","value":None,"reason":"insufficient_rows:<n><<min>"}`（**v0.4.4 補 `value` 鍵**，對齊 D-6 失敗形三鍵；composer-v5B1）；門檻具名 `factor_exposure.attribution_min_rows` 預設 10（D-7）。
- **驗證（可證偽）**：9 列 → `assert result["status"]=="unavailable"` 且 `"insufficient_rows:9" in result["reason"]`；10 列 → `status=="ok"`。
- **邊界**：① 恰好 10 列 ② dropna 後才跌破門檻（與 2.1 交互，reason 須指明主因）③ 因子欄 < 2。

- **存活至**：Phase 5 完工後**保留**：門檻與 unavailable 語義為永久。
- **覆蓋風險**：**無**。門檻若與 FR `min_samples` 統一（D-7 另票）屬**調參非覆蓋**。
- 不可做：不得為讓測試好過而調低 `attribution_min_rows` 預設值（10 為現行語義，變更須另票）。
### Phase 3 — 幽靈契約隔離（**deep payload 驗收**；依賴：Phase 2）
**Task 3.1 — orchestrator stub → 顯式 unavailable + 外顯（D-4）**
- 改法：`:2213-2227` 巢狀 `factor_attribution` → `{"status":"unavailable","value":None,"reason":"attribution_not_wired_to_canonical_contract（單標的 canonical FR 下迴歸 ill-posed；接真需另定 portfolio_returns 與 RHS 契約，見 ROADMAP 票A/票B）"}`；**移除頂層鏡像** `alpha/r_squared/attribution/unexplained/factor_betas`。
- **reason 禁寫**「系統沒有 PnL」（三家指出：**那是錯的**，通道存在但非 attribution-ready）。
- **外顯改點寫死（D-4；v0.3 重寫）**——三家判 v0.2「只換措辭」，故逐點指定：
  - `ic_filter_orchestrator.py:1852-1854`：runner 回傳後檢查巢狀 `factor_attribution.status=="unavailable"` → `module_summary[module_name] = "completed_partial"`（**不是** `"completed"`）
  - `deep_analysis_types.py:24`：docstring 列舉合法 scalar 值（`completed` / `completed_partial` / `unavailable` / `skipped` / …）
  - `ic_reporter.py:1174-1195 _build_module_summaries`：附帶 `factor_attribution` 子狀態（現通用分支只出 `keys/size`）
  - `frontend/src/lib/types.ts`：module status 型別加 `completed_partial`
  - **型別約束**：`module_summary: dict[str, str]` 只能存字串（實測 nested → Pydantic `rejected string_type`），故**必須用 scalar 新值**，不得塞巢狀物件。
- **驗證（可證偽；全部須 exit=0，指令見各子項 pytest / scripts/ic1d_compare.py）**：
  - comparator（依 §G 窮舉 20 路徑；`--allow-change` 3 條 attribution 子樹 + `module_summary.factor_exposure`，`--allow-remove` 15 條三鏡像幽靈鍵）→ `python scripts/ic1d_compare.py handoffs/ic1d_baseline/p1_after_rename.json handoffs/ic1d_baseline/p3_after_failclosed.json --allow-change results.factor_exposure.factor_attribution,results.factor_exposure.payload.summary.factor_attribution,results.factor_exposure.typed_result.payload.summary.factor_attribution,module_summary.factor_exposure --allow-remove results.factor_exposure.alpha,results.factor_exposure.r_squared,results.factor_exposure.attribution,results.factor_exposure.unexplained,results.factor_exposure.factor_betas,results.factor_exposure.payload.summary.alpha,results.factor_exposure.payload.summary.r_squared,results.factor_exposure.payload.summary.attribution,results.factor_exposure.payload.summary.unexplained,results.factor_exposure.payload.summary.factor_betas,results.factor_exposure.typed_result.payload.summary.alpha,results.factor_exposure.typed_result.payload.summary.r_squared,results.factor_exposure.typed_result.payload.summary.attribution,results.factor_exposure.typed_result.payload.summary.unexplained,results.factor_exposure.typed_result.payload.summary.factor_betas` exit=0（errata v0.5.2:禁 `...`,15 條字面路徑）
  - `assert report.module_summary["factor_exposure"] == "completed_partial"`（**v0.3 前為 `"completed"`，此斷言即 D-4 的牙齒**）
  - `assert report.completed_count == <p1_after_rename baseline 值>`（D-12：新狀態須計入，計數**不得**因本票變動）
  - `assert "exposure_hash" 不變`（哨兵：變了代表有人動 exposure）
  - **flatten 驗收（v0.4.5 強化；codex-v3M1 REJECTED 本項不足）**——**僅驗列數不足以擋漏外顯**，三條全須成立：
    1. **範圍限定**：所驗列數為 **`factor_attribution` 子樹**（`2→1`），**非**整個 `factor_exposure` 模組（實測整模組為 `4→3`）。實作/驗收**禁**以整模組列數替代。
    2. **狀態外顯**：`_flatten_module_rows('factor_exposure', payload)` 的輸出中**須存在**一列其路徑指向 `factor_attribution.status` 且值為 `"unavailable"` → `assert any(r["path"].endswith("factor_attribution.status") and r["value"]=="unavailable" for r in rows)`。**只對列數不驗此條 = 驗收失效**（codex-v3M1 反例：SPEC 可被實作為僅驗列數而漏外顯）。
    3. **reason 可見**：同一輸出中 `factor_attribution.reason` 須可被外部消費者讀到（非僅存在於 typed payload 內部）。
- **邊界**：① cache-hit ② force 僅 exposure ③ 前端收到 unavailable 不崩。
- 不可做：**不得**接真迴歸（§N）。

- **存活至**：Phase 5 完工後**保留**：`unavailable` + `completed_partial` 是本票的可觀測交付本體。
- **覆蓋風險**：**有，屬預期且已規劃**：票A 真接線時會把 `factor_attribution` 由 unavailable 改為實值而覆蓋本輸出形。**不合併 Phase 之理由**：票A 前置（equity curve 契約修復＋portfolio_returns canonical 定義）不在本票範圍；且本票的誠實標示在票A 落地前有**獨立防假交付價值**。
### Phase 4 — 測試去固化 + mutation 探針（依賴：Phase 2/3）
**Task 4.1 — 去固化 + 可證偽探針（D-2/composer-B4/codex-B4）**
- 檔案：`tests/momentum/Analysis/test_factor_exposure_analyzer.py`、`tests/phase25/test_factor_exposure_analyzer.py`
- 改法：
  - 改寫 `test_nan_factor_returns_exposure`（兩檔孿生）：現僅 `assert "factor_betas" in result`（momentum `:37`）→ 改斷言 `status=="unavailable"` + reason 內容。
  - 改寫 `test_factor_attribution_insufficient_rows`（**僅 phase25:64**）→ 並**補 momentum 側對稱測試**。
  - **新增 in-file mutation 探針**（檔名/函式名寫死，禁只寫「mutation」二字）——**v0.3 修正檔案歸屬（grok-v2M2/codex-v2M3）**：
    - `tests/momentum/Analysis/test_factor_exposure_analyzer.py`（**analyzer 單元層**）：
      `test_mutation_dropna_restored_must_fail`、`test_mutation_insufficient_silent_nan_must_fail`、
      **`test_mutation_inf_passthrough_must_fail`**（v0.3 新增，對應 D-10）、
      **`test_mutation_output_overflow_passthrough_must_fail`**（v0.4.2 新增，對應 D-13：移除輸出端有限性檢查 → 須 FAIL；composer R4 要求探針落地），
      **`test_mutation_index_policy_bypassed_must_fail`**（v0.3 新增，對應 D-5；codex-v2M1 指出 index 路徑原無探針）
    - `tests/momentum/Analysis/test_ic1d_orchestrator_integration.py`（**新建；orchestrator 整合層**）：
      **`test_mutation_stub_restored_must_fail`**、**`test_mutation_module_summary_completed_must_fail`**（對應 D-4，斷言若 summary 退回 `"completed"` 則 FAIL）
      → **理由**：stub 與 module_summary 都在 orchestrator，掛在 analyzer 單元檔無法命中（v0.2 誤置）。
    - **oracle 獨立性**（codex-v2M3）：`mutation_probe_check.sh` 只驗 AST/真跑、不驗 oracle 獨立；故每個探針的斷言**須引用 §G baseline 或獨立算出的期望值**，禁以被測函式自身輸出當 oracle。
  - **關鍵反例必涵蓋**（codex-B4）：把 fail-closed 改回 dropna 後，若樣本仍 `<10` 會走舊路徑並保留 `factor_betas` 鍵 → **舊式斷言仍綠**。新探針須確保此情境 **FAIL**。
- **驗證（可證偽）**：`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_exposure_analyzer.py tests/phase25/test_factor_exposure_analyzer.py tests/momentum/Analysis/test_ic1d_orchestrator_integration.py` exit=0（v0.1 實測 rc=1；**v0.3.1 修正：必須含第三個整合測試檔**，否則 orchestrator 的 `test_mutation_stub_restored_must_fail` / `test_mutation_module_summary_completed_must_fail` 兩支探針不進機械 gate＝D-4 的牙齒落空；composer R3 PARTIAL）；`pytest` 三檔 exit=0；測試數 momentum 5→>=8、phase25 11→>=13、整合檔 0→>=4（**v0.5.2 errata；N2/N4**：整合檔含 stub/module_summary 二探針 + cache-hit/force-only 二情境測試）。**mutation 探針共 7 支**：**analyzer 檔 5 支**〔dropna/insufficient/inf/output_overflow/index〕+ **整合檔 2 支**〔stub/module_summary〕；承載於 **2 個測試檔**（analyzer + 整合）。
- **Task 3.1 驗收須含整合情境（composer-M5 PARTIAL）**：cache-hit / force-only-exposure 不得只列在 §V 邊界目錄，須於 `test_ic1d_orchestrator_integration.py` 有對應測試並納入上述 pytest 指令。
- **防假綠**：diff 既有斷言，不得放寬/刪除換綠燈。

- **存活至**：Phase 5 完工後**保留**：測試與 7 支 mutation 探針為永久護網。
- **覆蓋風險**：**無**。票A 接線時需**新增**測試，非覆蓋既有。
- 不可做：不得放寬/刪除既有斷言換綠燈；不得以快照測試替代行為斷言。
### Phase 5 — 前端契約收尾（依賴：Phase 3）
**Task 5.1 — TS 型別 + Radar 空狀態**
- 檔案：`types.ts:2432-2459`（巢狀 `factor_attribution` 現僅建模數值欄位，須加 `{status,value,reason}`，位置=巢狀非頂層；codex-M1）、`FactorExposureRadar.tsx:13`、**`ExportButtons.tsx:27`**（v0.4.3 補；codex-v4M2：D-4 已點名必修但 Phase 5 檔案清單漏列）
- 改法：移除 fallback 鏈中「讀 `factor_attribution.factor_betas` 當 exposure」的契約地雷。
- **驗證（可證偽）**：`cd frontend && npm run build` exit=0；`grep -c "factor_attribution?.factor_betas" frontend/src/components/ic-analysis/FactorExposureRadar.tsx` == 0；注入 `{status:'unavailable'}` payload 的元件測試斷言渲染空狀態且不 throw。

- **存活至**：Phase 5 完工後**保留**：TS 型別與 Radar 契約修復為永久。
- **覆蓋風險**：**有，局部**：票A 接線後 `factor_attribution` 的 ok 形需擴充 TS 型別（D-6 適用層級消歧已載「屆時須同步更新 TS 型別，此為票A 前置」）；本票的 unavailable 形不被刪除。
- **邊界**：① 注入 `{status:'unavailable'}` payload 須渲染空態不 throw ② 舊 payload（無 status）不得使前端崩潰（向後相容）。
- 不可做：不得為配合新型別而修改 analyzer/orchestrator 的回傳形（前端只做消費端適配；形狀變更歸 Task 2.x/3.1）。
## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT 含 a,d → **必附可執行探針**（非 prose）。Phase 4 已寫死 **7 支 `test_mutation_*` 函式**（analyzer 5 + 整合 2，承載於 **2 個測試檔**）+ `scripts/mutation_probe_check.sh` gate（v0.5.2 errata N4:原「三個檔」措辭與 Task 4.1 矛盾,已改）（引 `docs/TEST_DESIGN_CHARTER.md` §B1.1「缺探針=BLOCKING」）。
- 測試層級：單元（analyzer 純函式，Phase 2 驗收層）/ 整合（orchestrator runner + cache/force 情境，Phase 3 驗收層）/ Golden 對照（comparator + 白名單）/ 邊界。
- 可獨立 `pytest tests/...` 跑，不需 `run_api.py`（Rule 6）。
- **防假綠**：Phase 4 明列 diff 既有斷言紀律；comparator 為唯一 golden 判準，禁目視。
- **既有測試回歸盤點（v0.4 新增；codex-v3B5）**：新政策可能使**既有正當測試**變紅，須於 TODO 逐一列出並判定「該改測試」或「該放寬政策」，**禁**為求綠燈而放寬正確性：
  - `test_zero_r_squared`（兩檔 `:40-47`）：用 RangeIndex + 斷言 finite → **D-5 已放寬（不限索引型別），此測試維持不變**。
  - `test_factor_attribution_insufficient_rows`（phase25 `:64-69`）：斷言 `np.isnan(result["r_squared"])` → **Phase 2.2 改 unavailable 後須同步改寫**（已列 Task 4.1）。**v0.4.4 補（codex-v4M3）**：momentum 側**目前無**此測試，Task 4.1 要求**新增對稱測試**，其斷言直接採 unavailable 形（`status`/`reason`），非改寫。
  - `test_nan_factor_returns_exposure`（兩檔 `:32-37`）：僅斷言 key 存在 → **已列 Task 4.1 去固化**。
  - phase25 `:81,:101` 的 `RangeIndex(200/400)`：屬 `neutralize_*` 測試，**不經** `calculate_factor_attribution`，**不受影響**（Claude 實查）。
- **邊界目錄**：☑空DF ☑全NaN列 ☑std=0（`:133` `ss_tot>0` 分支）☑重複 timestamp ☑亂序 timestamp ☑**合法間隙（須 PASS）** ☑tz 混用 ☑樣本 9/10/11 ☑cache-hit ☑force-only-exposure。

## §R 回退
- 每 Phase 獨立 commit，可單獨 revert。Phase 1（**deep no-op，僅改 analyzer 純函式**）風險最低；Phase 2/3 可獨立 revert 回 stub。
- **軟依賴說明**（grok-m6）：Phase 2 技術上不依賴 Phase 1 正名，串行僅為 baseline 切片順序；回退時可單獨取出。
- **flag 政策**：依「驗過就別預設關閉」，Phase 2/3 fail-closed 經 `pytest tests/momentum/Analysis/test_factor_exposure_analyzer.py -q` exit=0 + mutation 探針 exit=0 驗證後 **預設 ON**；flag 僅作逃生口。
- Golden comparator FAIL → 不 merge。

## §N N/A 登記
- **接真 attribution：N/A — 明確不在本票**。根因=單標的宇宙下 `ls_returnᵢ=positionᵢ⊙r`、組合報酬=`position_p⊙r` 共用同一 `r`，OLS 只識別 position 重疊度而非風險曝險（codex toy：β=[≈0,1,≈0], R²=1, 殘差 1.1e-16）。
  - ⚠️ **v0.1 錯誤更正**：先前稱「真實 equity curve 無 production 通道」**係錯誤**。通道存在（`prediction_analyzer.py:136` + caller `pattern_analysis.py:1047`），但**非 attribution-ready**：`strategy_returns` 實裝 `np.cumsum`(`:163`)、只有 long/flat(`:152`)、缺值 `fillna(0)`(`pattern_analysis.py:1050`)。
  - **拆兩張條件票**（不取消，防未來失憶）：**票 A** timing-overlap 診斷（前置=修 equity curve 契約）；**票 B** true multi-asset attribution（前置=CS FR 管線+持倉權重 canonical）。階段=Phase 4 或 ML epic，**不插隊 Phase 1**。定位已寫入 `docs/ROADMAP.md`。
- **真 residual IC：N/A** — 獨立議題，勿與本票混（ROADMAP Phase 表為準）。
- **exposure 家族 NaN 靜默（`:36,44,54,59,64,73,84,94,101,155`）：N/A** — 影響 Radar 主圖，歸他票。
- **FR `min_samples=30` 與 attribution 門檻統一：N/A** — D-7 明確另票。
- **刪除 `unexplained` 鍵：N/A** — 破壞性契約變更，歸遷移票。
- **真實 kline 三方簽核計畫：N/A** — 不碰 feature/kline 生成→計算→merge→split 路徑；模組級 golden 仍必做（見前述 Golden 段）。
- **pre-existing 債：N/A** — Rule 4 `pattern_management_service.py:78`、`ModuleUnavailableError` 死碼、`strategy_returns` 命名說謊、`analyze_cross_sectional` 繞過 deep 棧、ROADMAP 表/敘事不一致，皆另記。
