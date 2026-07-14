# IC 1c Net IC 量綱正確化 TODO(版本 **Frozen r7(2026-07-14,r7=B2 審後修訂:G-NEW2 gross_ic 不變式+離線鐵則+單檔擴scope核可,交 codex 閉合輪核可)**——六輪三家 adversarial 全閉合(grok r3/composer r5/codex r6 APPROVE),RECONCILE-STAMP 機檢 PASS(body sha256:936daabc)/基於 docs/IC1C_NETIC_SPEC.md **v1.1**(負 turnover→SKIPPED 補裁)/2026-07-14;r1 16 主題+r2 三家 REJECT(codex 7B/composer 2B/grok 1B)合併 T-F17~T-F26 全落本版,見 handoffs/20260714-IC1C-TODOREV-RECONCILE.md)

## §0 全域規則與約束(執行端讀完即可遵守)

- **修法=B-strict(委員會三家裁決)**:永不從相關係數(IC)減報酬率。`net_ic` 鍵**全樹禁止輸出,含別名**。canonical 因子報酬序列未建立(票 1c-FR)前,`net_factor_return`/`breakeven_cost_bps`/`profitable_after_cost` 一律 `{"status":"unavailable","value":null,"reason":"canonical_factor_return_series_not_built (1c-FR)"}`;**禁以 IC 或 `long_short_mean_return`(錯位構造)代填**。
- **§U 唯一佔位形狀**:conditional metric 存在時必為 `{status:"ok"|"unavailable", value, reason}`;`unavailable`→`value=null`+`reason` 非空;`ok`→`reason=null`。禁裸 null/裸 number/頂層 reason。
- **§U 三 profile 鍵集合(equality oracle,多/少鍵=FAIL)**:
  - `SCHEMA_SKIPPED={skipped, reason}`(turnover 缺/非有限/**負值**(SPEC v1.1)/gross_ic 非有限)
  - `capacity` 允許子鍵(SPEC v1.1,**鍵集合+型別斷言**,r5):恰為 `{estimated_capacity_usd: number|null, capacity_tier: str, calibration: 恒=="uncalibrated"}`,多/少子鍵=FAIL(入 SCHEMA 常數與 T1)
  - `SCHEMA_GROSS_ONLY={gross_ic, turnover, turnover_semantics, capacity, net_factor_return}`
  - `SCHEMA_COST_ENABLED=GROSS_ONLY ∪ {cost_bps, cost_semantics, cost_drag_return, cost_sensitivity, breakeven_cost_bps, profitable_after_cost}`
- **§T 成本語意**:`cost_drag_return=(cost_bps/10000)×turnover`——**無 ×2**(quantile_turnover 已含進出雙腿);`turnover_semantics="membership_change_both_legs_per_bar"`;`cost_semantics="per_rebalance_not_annualized"`;禁年化。階梯=`{c/2,c,2c,5c}` clamp [0.1,1000] 四捨五入 0.1 去重。
- **fail-closed**:`cost_bps` 合法域=有限且 `0<cost_bps≤1000`(**0 非法**;「無成本」唯一表示=`cost_enabled=False`);**域驗證與 enabled 無關——`cost_bps` 非 None 一律驗域**(T-F7:`{cost_enabled:False, cost_bps:NaN}` 也必須被三層拒絕),enabled 時另驗非 None;5.0 bps 預設三處(schema/YAML/analyzer)全拔;`config_override.net_ic_analysis` 整節 API reject(**雙入口**:`DeepAnalysisRequest.config_override` 與 `ICAnalyzeRequest.config_override` 皆 422;merge 順序禁 override 蓋 typed 欄)。
- **JSON strict**:所有 baseline dump 與 API 序列化 `json.dumps(..., allow_nan=False)`;**非有限 capacity 欄(`estimated_capacity_usd` 等)於 batch 組 dict 邊界轉 `null`**(計算函式 `estimate_factor_capacity` 本體不動)。
- 解耦 7 條 checklist(本票適用性):R1 momentum 不 import api(適用,analyzer/orchestrator 改動)|R2 跨域走 Protocol(適用,api 不得直 import analyzer class,走 `create_net_ic_analyzer`)|R3 services 用 factories(適用)|R4 services 不互 import(適用,ic_analysis_service 改動)|R5 config 單源(適用,`ic_config_schema.py`+`ic_config.yaml` 是唯一成本 config 源)|R6 測試不靠 run_api.py(適用,T1/T3/T5 獨立跑;T2 fixture 層隔離 Binance ping)|R7 DTO 不跨界(適用,`NetICAnalysisRequest` 留 api/models,momentum 只吃 dict)。`bash scripts/check_decoupling.sh` 全綠不得破。
- 防假綠:不得放寬既有斷言換綠;改寫舊測試須附「舊斷言為何錯」(SPEC §V 改寫表);JSON 禁 NaN/inf 字面值。
- 資料:驗證一律真-kline fixture `tests/fixtures/ic_api_real_kline.py`;禁新合成 fixture;禁碰 `data_cache/`。
- commit 訊息 operational claim 須 `VERIFY:<receipt>` backing;每 Phase 獨立 commit 可 revert。
- **擴 scope 核可記錄(r7)**:`frontend/src/hooks/useFeatureFactory.batchDate.test.ts` 單檔最小 eslint 修(刪未用參數)——編排端 2026-07-14 正式核可(理由:既存 lint 錯擋 Frozen 要求的 `npm build` gate,最小 enabler;語意中性,codex 已驗)。
- **離線可重現鐵則(r7,codex B2-B2)**:B2/B3 Gate 全部命令(collect/probe/new2)須在**無網環境**可重現——`api.main` import 的 Binance ping 須以 fixture/conftest 層 stub 隔離(沿用既有 `ic_persist_redirect` 模式),freeze 腳本 new2 模式同樣自帶隔離;禁靠環境在線才綠。

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|-------|---------|------|----------|------|
| B0 | 0.1 | 無 | baseline 獨立凍結 | 小 |
| B1 | 1.1+1.2+1.3+1.4 | B0 | 同 Phase 數值核心+全部 momentum 層消費點,共用測試檔 | 大 |
| B2 | 2.1+2.2 | B1 | API+前端接線一氣呵成(防幽靈開關需同批驗) | 中-大 |
| B3 | 3.1 | B2 | UI 註記收尾,零 schema | 小 |

- 批次 Gate(命令可直接執行,T-F2):
  - B0→B1:`python scripts/ic1c_freeze_baseline.py --baseline old && python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json && shasum -a 256 -c handoffs/ic1c_baseline/g_old.sha256` exit 0,且決定性以字面命令驗(r5):`h1=$(python scripts/ic1c_freeze_baseline.py --baseline old >/dev/null && shasum -a 256 handoffs/ic1c_baseline/g_old.json | cut -d' ' -f1); h2=$(python scripts/ic1c_freeze_baseline.py --baseline old >/dev/null && shasum -a 256 handoffs/ic1c_baseline/g_old.json | cut -d' ' -f1); [ "$h1" = "$h2" ]` exit 0。
  - B1→B2:`venv/bin/pytest tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/Analysis/test_net_ic_schema_profiles.py tests/momentum/test_turnover_analyzer.py tests/momentum/test_export_formats.py -q` 全綠+`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/test_turnover_analyzer.py` PASS+`python scripts/ic1c_freeze_baseline.py --baseline new`(G-NEW 比對+diff_manifest 產出)exit 0。**M10 於 B1 僅 T1 層;三層完整=B2**(T-F4)。
  - B2→B3:`venv/bin/pytest tests/api/test_ic_deep_analysis.py --collect-only -q`(離線 collect 前置,r5 入 Gate)+`venv/bin/pytest tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py -q`+`bash scripts/mutation_probe_check.sh tests/api/test_ic_deep_analysis.py tests/phase24/test_deep_analysis_config.py`+`npm --prefix frontend run test -- NetICChart`(M4 前端 probe 明列通過)+`npm --prefix frontend run build`(r3:repo root 無 package.json,一律 `--prefix frontend`)+`python scripts/ic1c_freeze_baseline.py --baseline new2` exit 0。
  - B3 完:Phase 3 驗證+`venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q`(r3 補 phase26 factories/integration 回歸)+兩支 decoupling scanner 全綠。
- 每批派工 prompt:各 Phase 首行「前置狀態」+該批 Task 全文+驗證命令(如 B1=`venv/bin/pytest tests/momentum/Analysis/test_net_ic_analyzer.py -q`);執行端=Grok(workspace 沙箱),審查=Codex+Composer。

## Phase 0 — Baseline 凍結(目標:改前輸出可比對;完成後系統狀態:程式碼零變更,handoffs/ic1c_baseline/ 有 G-OLD)

### Task 0.1 — G-OLD 凍結
- SPEC ref:Task 0.1/§G　目標:凍結改前 net_ic 模組全量輸出。
- 輸入:`tests/fixtures/ic_api_real_kline.py` fixture。輸出:`handoffs/ic1c_baseline/g_old.json`+`g_old.sha256`。
- 實作要點(T-F10 冷啟動準入口):①新腳本 `scripts/ic1c_freeze_baseline.py --baseline old|new|new2`(三模式,輸出固定 `handoffs/ic1c_baseline/g_{old,new,new2}.{json,sha256}`);②**入口偽碼(old 模式)**:`fixture=load ic_api_real_kline features/labels → 依 fixture 衍生 IC 統計構造 summary={feat:{"ic_mean":spearman(feat,label)}}(排序後逐 feat)+turnover_data={feat: quantile_turnover(...)}(呼叫現行 turnover_analyzer) → NetICAnalyzer({現行 default config}).batch_analyze(summary, turnover_data)`——**不跑 full deep pipeline**(直呼 analyzer=G 的比對對象;`_run_net_ic` 的傳導由 T1b/T2 測);③確定性:feature 名排序、無隨機、`json.dumps(sort_keys=True, allow_nan=False)`(非有限值先轉 null 並記於 `non_finite_fields` 清單);④skipped 注入(具名步驟,**真 fixture 特徵名**,r3 修):`turnover_data.pop("oc_return")`(造 turnover_missing)+`summary["hl_range"]["ic_mean"]=float("nan")`(造 gross_ic_missing)——fixture `FEATURE_NAMES`=`log_return_1,log_return_3,rvol_20,zscore_20,hl_range,oc_return,close_sma_ratio_20`(7 欄,無 obv/ad);⑤lineage:JSON 頂層記 `{"fixture_sha256":..., "git_head":..., "generated_by":"ic1c_freeze_baseline --baseline old"}`;⑥**獨立內容 validator** `scripts/ic1c_validate_baseline.py`(producer 不得自證,T-F5):驗 feature 數≥N(fixture 特徵數-2)、必含兩 skipped 路徑、鍵數/型別、fixture hash 與現檔一致,任一不符 exit 1。
- 修改檔案:僅新增兩腳本+baseline 檔;不動 momentum/api/frontend 任何函式。
- 不可做:不得順手修 bug;不得改 fixture;不得跑完整 deep pipeline。
- 邊界:①重跑腳本 sha256 一致(確定性);②baseline 含 `net_ic` 鍵(現行錯誤輸出,故意保留作對照);③非有限值不得以 NaN 字面落 JSON。
- 風險緩解:T-F5 producer 自證→獨立 validator。
- 驗證:`python scripts/ic1c_freeze_baseline.py --baseline old && python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json && shasum -a 256 -c handoffs/ic1c_baseline/g_old.sha256` exit 0;連跑兩次 hash 相同。

### Phase 0 測試+Gate:上述驗證命令=Gate;無單元測試(零程式變更)。

## Phase 1 — 核心量綱修復(目標:B-strict 落地;完成後狀態:analyzer/orchestrator/proxy 無混量綱路徑,G-NEW 三 profile 凍結)

### Task 1.1 — net_ic_analyzer B-strict 改寫
- SPEC ref:Task 1.1/§T/§U　目標:刪混減公式,輸出三 profile。
- 輸入:B0 完成。輸出:新版 `NetICAnalyzer`。
- 實作要點:①刪 `compute_net_ic`;新 `compute_cost_drag(cost_bps: float, turnover: float) -> float` = `(cost_bps/1e4)*turnover`(無 ×2;**呼叫前提=turnover 已過 profile 檢查**:非有限或 `<0`→該 feature SKIPPED(reason=`non_finite_turnover`/`negative_turnover`),**禁 `max(0,·)` 靜默 clamp**,SPEC §U v1.1);②`cost_sensitivity_analysis(cost_bps, turnover) -> list[dict]`:階梯 `sorted(set(round(clamp(x,0.1,1000),1) for x in [c/2,c,2*c,5*c]))`,每項 `{cost_bps, cost_drag_return}`——**無 net_ic 鍵**;③`batch_analyze(ic_summary, turnover_data)`:per feature 依 §0 三 profile 組 dict;conditional metrics 恒 `_unavailable("canonical_factor_return_series_not_built (1c-FR)")`;`capacity` 沿用 `estimate_factor_capacity` 並加 `"calibration":"uncalibrated"`,**組 dict 時非有限欄轉 null**(T-F9,函式本體不動);④`__init__`:刪 `cfg.get("default_cost_bps",5.0)`/`_cost_scenarios`;讀 `cost_enabled`(default False)+`cost_bps`(None);**validator 統一偽碼(r3,三層同此)**:`if cost_bps is not None and (not isfinite(cost_bps) or not 0<cost_bps<=1000): raise ValueError`+`if cost_enabled and cost_bps is None: raise ValueError`——非 None 一律驗域,與 enabled 無關;⑤summary=`{total_analyzed, evaluable_count(恒0), profitable_count(只計 evaluable), avg_cost_drag_return(cost_enabled 時 mean,否則鍵不存在)}`——刪 `avg_ic_loss_pct`/`rank_correlation_gross_vs_net`/spearmanr import;⑥`compute_net_factor_return` 標 deprecated docstring,`batch_analyze` 不再呼叫(忽略任何注入)。
- 修改檔案:`momentum/Analysis/net_ic_analyzer.py`(上列函式);`momentum/Analysis/ic_config_schema.py:266-271`(刪 `default_cost_bps`/`slippage_bps`/`cost_scenarios`,新 `cost_enabled: bool=False`+`cost_bps: Optional[float]=None`+field_validator 域檢);`config/ic_config.yaml:181-186` 同步。既有 caller:`ic_filter_orchestrator._run_net_ic`(Task 1.2 同步)、`factories.create_net_ic_analyzer`(簽名不變)。
- 不可做:不實作 IC→報酬轉換;不動 `estimate_factor_capacity` 計算邏輯;不留任何 `net_ic` 別名鍵;不引入年化。
- 邊界:①turnover=0→`cost_drag_return=0.0`、breakeven unavailable;②gross_ic NaN→SKIPPED;③turnover 非有限→SKIPPED(reason=`non_finite_turnover`);④`cost_bps=0`→raise;⑤cost_enabled=False→GROSS_ONLY(無任何 cost 鍵)。
- 風險緩解:SPEC RISK-HIT a,d→golden+mutation 全綁。
- 驗證:T1 新測試(見 Phase 1 測試);手算 oracle `compute_cost_drag(10,1.5)==0.0015`;`test_no_net_ic_key_anywhere` 遞迴斷言;profile 鍵集合==`SCHEMA_*` 常數。

### Task 1.2 — orchestrator fail-closed 接線
- SPEC ref:Task 1.2　目標:runner 走新 API,不傳 factor_returns。
- 輸入:Task 1.1。輸出:`_run_net_ic` 新版。
- 實作要點:①`_run_net_ic(:1942-1956)`:`NetICAnalyzer(config.net_ic_analysis.model_dump())` 不變;`batch_analyze(summary, turnover_data)` 兩參呼叫(明確不傳第三參);②模組依賴矩陣:net_ic_analysis 不依賴 factor_return 模組——`FactorReturnAnalyzer` **不動勿刪**(canonical series=票 1c-FR);③skipped/`turnover_not_available` 頂層語意保留。
- 修改檔案:`momentum/Analysis/ic_filter_orchestrator.py::_run_net_ic`。既有 caller:deep analysis runner 迴圈(:1648,模組名不變)。
- 不可做:不開模組間資料通道(1c-FR);不動其他 runner。
- 邊界:①`force_modules=["net_ic_analysis"]` 單跑→GROSS_ONLY/COST_ENABLED 正常;②turnover_data 空→頂層 skipped。
- 風險緩解:⊘。
- 驗證(T-F3,B1 內自足):T1b(T1 檔內)`test_run_net_ic_orchestrator_direct`(新):以最小 orchestrator 實例直呼 `_run_net_ic`,斷言 `net_factor_return["status"]=="unavailable"`+reason 非空+輸出樹無 `net_ic` 鍵;API e2e 版歸 Task 2.1/B2。

### Task 1.3 — turnover proxy 同病清除
- SPEC ref:Task 1.3　目標:消滅第二個混量綱入口。
- 輸入:Task 1.1(§T 公式)。輸出:proxy 刪除或正名。
- 實作要點:①`turnover_analyzer.py:125-137` `compute_net_ic_proxy` 刪除(首選;grep 確認除測試外無 caller)或正名 `compute_cost_drag_proxy`=§T 公式;②`tests/momentum/test_turnover_analyzer.py` **全部** proxy 測試同步改寫:`:60-66`(舊斷言 `0.1-0.01×2=0.08` 固化混量綱+四腿計費=錯)+`test_net_ic_proxy_nan_turnover(:92-96)`(T-F11;nan turnover 規則=**raise ValueError**,與 Task 1.3 邊界②及 SPEC v1.1 一致,r5 釘死);③全 repo `grep -rn "net_ic_proxy"`==0。
- 修改檔案:`momentum/Analysis/turnover_analyzer.py::compute_net_ic_proxy`+對應測試。既有 caller:僅測試(執行端 grep 複驗)。
- 不可做:不動 `quantile_turnover` 計算本體。
- 邊界:①正名版 turnover=0→0.0;②負/非有限 turnover→raise ValueError(對齊 SPEC v1.1,**禁 clamp**;r4 修 composer R3-1)。
- 風險緩解:M8。
- 驗證:`grep -rn "net_ic_proxy" momentum/ tests/ api/`==0;T3 新斷言手算 `(10/1e4)*1.5==0.0015`。

### Task 1.4 — reporter/export 消費點正名(r2 新增,T-F1)
- SPEC ref:§C consumer 4/16　目標:momentum 層報表無 `net_ic` 殘留。
- 輸入:Task 1.1 新 schema。輸出:reporter/export 對齊 §U。
- 實作要點:①`ic_reporter.py:150` summary CSV 欄 `net_ic`→`cost_drag_return`;`:209` detailed alias 同步;`:631-634` `_safe_nested(...,"net_ic")`→讀 `cost_drag_return`(**裸有限 number,非 union**——union 只限 net_factor_return/breakeven/profitable 三欄,r3 修 codex R2-NEW-2;GROSS_ONLY 時鍵不存在→CSV 空);export 測試具名斷言 `cost_drag_return` 欄==手算值(10bps×turnover);`:773` inject 映射鍵名不變(模組鍵 `net_ic_analysis` 保留);②`tests/momentum/test_export_formats.py:73-75,107-113` fixture 改 §U profile+新斷言 CSV 欄集合**不含** `net_ic`(red-on-break:改回舊鍵→紅)。
- 修改檔案:`momentum/Analysis/ic_reporter.py`(上列 4 處)+`tests/momentum/test_export_formats.py`。既有 caller:`ic_analysis_service` 經 reporter 產物(B2 驗)。
- 不可做:不動 reporter 其他模組欄;模組鍵 `net_ic_analysis`(config/toggle 名)不改。
- 邊界:①feature 全 SKIPPED→CSV 該欄空not crash;②union unavailable→CSV 出 null 非 "unavailable" 字串誤植。
- 風險緩解:M1 全樹掃描含 reporter 輸出。
- 驗證:`venv/bin/pytest tests/momentum/test_export_formats.py -q` 綠;`grep -n '"net_ic"' momentum/Analysis/ic_reporter.py`==0(僅 `net_ic_analysis` 模組鍵允許)。

### Phase 1 測試(單元/邊界/mutation 三層)
- **T1=`tests/momentum/Analysis/test_net_ic_analyzer.py` 全重寫**(合併刪除 `tests/phase25/test_net_ic_analyzer.py` 近重複本——舊檔斷言 `net_ic` 鍵/`default_cost_bps` 驅動=固化錯 API):具名測試=`test_no_net_ic_key_anywhere`/`test_cost_drag_hand_calc`/`test_breakeven_unavailable_1c`/`test_no_default_cost_fallback`/`test_summary_contract_b_strict`/`test_unavailable_union_shape`/`test_finite_invariants`(**含 capacity 子樹 strict-JSON 可序列化+鍵集合恰等+calibration=="uncalibrated"**,T-F9/r5)/`test_negative_turnover_skipped`(**r5 具名**:注入 `turnover=-0.2`→SKIPPED reason=`negative_turnover`;同檔 probe `test_mutation_m11_restore_clamp`:恢復 `max(0,·)`→紅)/scenario 階梯 `test_cost_sensitivity_ladder`(值符 §T 公式+`cost_semantics` 字串)+T1b `test_run_net_ic_orchestrator_direct`。**三 profile 鍵集合常數依 Frozen SPEC 落專檔 `tests/momentum/Analysis/test_net_ic_schema_profiles.py::SCHEMA_SKIPPED/SCHEMA_GROSS_ONLY/SCHEMA_COST_ENABLED`(唯一來源,T1/T2/freeze 腳本一律 import 此檔,禁複製,T-F6)**。
- **同檔自證 probe**(章程 B1.1,基線綠→注入紅→還原綠):`test_mutation_m1_restore_mixed_subtraction`/`m2_reinstate_x2`/`m3_ic_numerator_backfill`/`m5_revive_cfg_get_default`/`m6_ic_vs_ic_rankcorr`/`m9_bare_null_placeholder`/`m10_drop_finite_guard`;T3 `test_mutation_m8_restore_proxy_subtraction`。
- **G-NEW 凍結**:`scripts/ic1c_freeze_baseline.py --baseline new`:同 fixture 跑新碼(config 直開 cost_enabled+cost_bps=10 產 COST_ENABLED;預設產 GROSS_ONLY;含 SKIPPED——三注入:pop oc_return/hl_range NaN/**zscore_20 turnover=-0.2**(r5 負值))→機器比對並 exit code 表態:①`gross_ic`/`turnover` vs G-OLD byte 等值——**比對集排除三個注入特徵(oc_return/hl_range/zscore_20;排除常數與 G-NEW2 共用)**(r6 修 codex R5-1:注入特徵改驗其 SKIPPED profile 形狀+reason 正確,不驗舊值等值);②鍵集合==`SCHEMA_*`(import 專檔);③**canonical 重算=腳本內嵌獨立 numpy 3 行(`drag=(bps/1e4)*t`;`t` 非有限或 `<0` 須為 SKIPPED,否則 exit 1——r3 去 clamp,SPEC v1.1),禁止 `import net_ic_analyzer`**(T-F5 防自指 oracle),全量 `atol=1e-12`;④JSON strict(allow_nan=False);⑤產出機器可讀 `handoffs/ic1c_baseline/diff_manifest.json`(必變欄逐 feature 舊→新,T-F14),未列欄變動→exit 1。
- **Phase 1 Gate**(=§B B1→B2 命令,含 T1/T1b/T3/T4(export)/SCHEMA 專檔+帶參 probe check+`--baseline new`)。

## Phase 2 — 成本參數全棧接線(目標:成本=前端輸入+啟用勾選,fail-closed;完成後狀態:UI→API→engine 全鏈可證非幽靈)

### Task 2.1 — API typed request+HTTP 邊界 422
- SPEC ref:Task 2.1/§U finite validator　目標:成本欄一等公民,拒絕一切繞道。
- 輸入:Phase 1。輸出:typed API 契約。
- 實作要點:①`api/models/ic_models.py`:新 `class NetICAnalysisRequest(BaseModel): cost_enabled: bool=False; cost_bps: Optional[float]=None`+`@model_validator`(r3 統一偽碼,同 Task 1.1 ④):非 None 一律驗域(有限且 `0<x≤1000`),enabled 另驗非 None→raise(→FastAPI 422;`{cost_enabled:false, cost_bps:NaN}` 也 422);`DeepAnalysisRequest` 加 `net_ic: NetICAnalysisRequest=NetICAnalysisRequest()`;②`config_override` 檢查(T-F12 雙入口):`DeepAnalysisRequest.config_override` **與** `ICAnalyzeRequest.config_override` 兩路徑之 `net_ic_analysis` 鍵出現→皆 422(整節 reject,白名單空集);`_build_deep_module_override` merge 順序改為 typed 欄**最後**注入(override 不得蓋 typed);③`ic_analysis_service.py:1140` `_build_deep_module_override`:注入 `{"enabled":..., "cost_enabled":..., "cost_bps":...}` 自 typed 欄;④驗證必須在 route 同步路徑(`ic_analysis.py:107-118` 回 200 前)——Pydantic request model 天然滿足,補測試釘死;⑤`types.ts` 同構 union+request 型別;⑥`ic_analysis_service.py:1198-1213` 序列化:conditional metric 三鍵物件**原樣保留禁扁平化**(T-F16),T2 斷言 response JSON 中 union 形狀完整;⑦request body 示例(T-F15):
```json
{"modules": {"net_ic_analysis": true}, "net_ic": {"cost_enabled": true, "cost_bps": 7.0}, "config_override": null}
```
(注意:request 欄名 `net_ic`,config/模組鍵 `net_ic_analysis`——service 負責映射,前端不得混用。)
- 修改檔案:`api/models/ic_models.py`(上列 class)/`api/services/ic_analysis_service.py::_build_deep_module_override`/`frontend/src/lib/types.ts:2451-2474`(NetICAnalysisData 重寫為新 profile+union)。既有 caller:`useICAnalysis.ts` request builder(Task 2.2)。
- 不可做:不留 `default_cost_bps` 任何殘影;不放寬 `config_override` 其他節行為。
- 邊界:①`{cost_enabled:true}` 缺 cost_bps→422(同步);②`cost_bps=0`/NaN/inf/1000.1→422;③舊 request(無 net_ic 欄)→cost_enabled=False→GROSS_ONLY 照跑(相容);④`config_override:{"net_ic_analysis":{...任意}}`→422。
- 風險緩解:M5/M7/M10。
- 驗證:T2 具名=`test_cost_bps_range_422`(含 0/NaN/inf/上界)/`test_config_override_net_ic_rejected`/`test_legacy_request_gross_only`;probe=`test_mutation_m7_allow_override_key`/`test_mutation_m10_api_drop_validator`;T5(R `tests/phase24/test_deep_analysis_config.py`,舊 `default_cost_bps==5` 斷言=固化寫死成本,刪)=`test_net_ic_cost_validator`+probe `test_mutation_m10_config_drop_validator`。

### Task 2.2 — 前端成本輸入+圖表正名
- SPEC ref:Task 2.2　目標:UI 輸入成本、圖表不再稱 Net IC、假值清零。
- 輸入:Task 2.1 契約。輸出:前端全鏈。
- 實作要點:①`DeepAnalysisConfigPanel.tsx`:net_ic 模組列加「啟用成本」checkbox+bps 數字欄(0.1-1000,step 0.1;disabled 時隱藏);label/tip 改「成本拖累(報酬空間)」;②`icAnalysisStore.ts`:state+request builder 帶 `net_ic:{cost_enabled,cost_bps}`;③`NetICChart.tsx`:刪 `useState(5)`/硬編 `[1,3,5,10,20]`/turnover fallback `0.1`(缺 turnover→顯示「無資料」空狀態);Y 軸/標題改 `cost_drag_return`;scenario 下拉改讀後端 `cost_sensitivity[].cost_bps`;④`FeatureTierPanel.tsx:39` 文案同步;⑤`page.tsx:419-428,823`+`useICAnalysis.ts:320-331` wiring。
- 修改檔案:上列 5 檔+`NetICChart.test.tsx`(T4 新建)。既有 caller:page.tsx 掛載點。
- 不可做:不留任何寫死 bps/scenario 常數;不畫任何名為 Net IC 的軸;空/loading/error 三態齊。
- 邊界:①cost_enabled=False→圖表 gross-only 模式(無 cost 軸);②API 422→表單錯誤顯示;③feature 全 SKIPPED→空狀態。
- 風險緩解:M4。
- 驗證:T4 vitest 具名(r3 補三態 oracle):`sends_cost_bps`(UI 7bps→request payload 7)+`shows_error_on_422`(API 422→表單錯誤文字可見)+`shows_empty_on_all_skipped`(全 SKIPPED→空狀態非 spinner)+`shows_no_data_when_turnover_missing`+同檔 probe `test_mutation_m4_frontend_drop_cost`;T2 `test_cost_bps_fullstack_wiring`(request 7→engine artifact 記 7)+probe `test_mutation_m4_drop_cost_passthrough`;`npm --prefix frontend run build` 綠;靜態檢查鎖**舊 fallback 表達式**(T-F8):`grep -nE "useState\(5\)|turnover \?\? 0\.1|\|\| ?0\.1" NetICChart.tsx`==0(UI `step={0.1}`/`min=0.1` 合法不受限);行為守衛=T4 RTL 測試「缺 turnover→顯示無資料、不代入任何數值」。

### Phase 2 測試+Gate(=§B B2→B3 命令;離線可 collect,fixture 層隔離 Binance ping)
- **G-NEW2 定義(T-F5,可執行 oracle;r5 統一編號)**:`scripts/ic1c_freeze_baseline.py --baseline new2` 流程:**步驟 1 取得 API 輸出(三段 bootstrap,deep-analysis 掛既有 IC task 下)**:1a `POST /api/v1/ic/analyze`(fixture paths)→輪詢至 completed 得 `task_id`;1b `POST .../deep-analysis/{task_id}`(body 含 `net_ic:{cost_enabled:true,cost_bps:10}`;現行 route 為背景任務,POST 只回 `{task_id,status}`);1c 輪詢 `GET .../deep-analysis/{task_id}/result`(0.5s 間隔,timeout 60s)至 completed 取 features dict(參照 `tests/api/test_ic_deep_analysis.py::completed_ic_task` fixture 既有模式,含 `ic_persist_redirect`)。**步驟 2 比對(r7 修訂,codex B2-B1 finding 走 Frozen 變更程序)**:與 G-NEW(config 直開 10bps)feature 級 dict 逐鍵 sha256 等值——比對集=排除三注入特徵後的其餘特徵;**`gross_ic` 鍵另則**(B2 實作發現:API 路徑 IC 由完整 pipeline 計算,與 freeze 腳本直算 spearman 來源不同,值必然差——非成本傳導缺陷):`gross_ic` 不做等值,改驗不變式=有限、∈[-1,1]、非注入 feature 數相同、且 **API 側 gross_ic 與 G-NEW 側 |diff|≤0.2;同號檢查僅在 max(|gi|)≥0.05 時強制**(r7b:近零 IC 兩路徑〔freeze spearman vs pipeline ic_mean〕異號屬噪聲,實證 log_return_3 +0.021/-0.016;主脫鉤防線=|diff|≤0.2);其餘全部鍵(turnover/cost_bps/cost_drag_return/cost_sensitivity/union 三欄/capacity)維持逐鍵 sha256 等值。本修訂由 codex 閉合輪核可後生效。**步驟 3**:不等→列出 diff+exit 1;產出 `handoffs/ic1c_baseline/g_new2.{json,sha256}`。離線 collect 前置已入 §B B2 Gate 行。T2 測試矩陣另含雙 override 入口 422+`{cost_enabled:false, cost_bps:NaN}` 422(T-F7)。

## Phase 3 — UI 語意註記(目標:禁年化/禁跨 TF 直比進 UI;完成後狀態:零 schema 變更收尾)

### Task 3.1 — 註記與文件
- SPEC ref:Task 3.1/§T　目標:語意標籤面向使用者。
- 輸入:Phase 2。輸出:UI 註記+docs。
- 實作要點:①NetICChart 加說明文字/tooltip:「成本為每次再平衡(per-rebalance),未年化;不同 timeframe 間不可直接比較」;②`grep "per_rebalance"` 可證;③docs 唯一路徑=`docs/API_SPECIFICATION.md` Net IC 小節(r3 釘死)同步新契約。
- 修改檔案:`NetICChart.tsx`(註記)+docs。既有 caller:無新。
- 不可做:零 schema/payload 變更;不加年化換算功能。
- 邊界:①tooltip 在 gross-only 模式亦正確;②文案繁中。
- 風險緩解:⊘。
- 驗證:`npm --prefix frontend run build` 綠;`grep -n "per_rebalance" frontend/src/components/ic-analysis/NetICChart.tsx` ≥1;G-NEW2 重跑 byte 等值(證零 schema)。

### Phase 3 測試+Gate:上述+全套 `venv/bin/pytest tests/momentum/ tests/api/ tests/phase26/ -q`(與 §B「B3 完」一字對齊,r4 修 composer R3-3)+`./scripts/check_decoupling_phase4.sh`+`bash scripts/check_decoupling.sh`。

---
覆蓋追溯:SPEC Task 0.1/1.1/1.2/1.3/2.1/2.2/3.1(7/7)→TODO 同名 Task+新 Task 1.4(SPEC §C consumer 4/16 reporter,r1 審查揭漏);M1-M10(10/10)→Phase 1/2 測試節+§B Gate(M10:B1=T1 層,B2=三層完整);G-OLD/G-NEW/G-NEW2(3/3)→Task 0.1/Phase1 測試節/Phase2 Gate(皆具可執行命令+獨立 validator);§U 三 profile→§0+專檔 `test_net_ic_schema_profiles.py`;1c-FR 拆票→§0+Task 1.2 不可做;§C 16 consumer→Task 1.1(1,5,6,7)/1.2(2)/1.3(3)/1.4(4,16 部分)/2.1(8,9,10,14)/2.2(11,12,13,15)/3.1(11 註記)。
SPEC=docs/IC1C_NETIC_SPEC.md TODO=docs/IC1C_NETIC_TODO.md FOCUS=B-strict fail-closed 完整性+全棧 wiring 防幽靈
