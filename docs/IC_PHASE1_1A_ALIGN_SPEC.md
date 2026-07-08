# IC Phase1 1-align — Feature_t ↔ Target_{t+lag} 前瞻錯位硬閘 — SPEC v3【Frozen 2026-07-09】

> **Frozen**:R1-R3 雙家族 adversarial 全閉合;雙 RECONCILE-STAMP 機檢 PASS(handoffs/IC1A-ALIGN-RECONCILE.md sha256:d68783b6…)。實作期間改本檔須重開 reconcile。

> v3 2026-07-08:修 R2 Composer STILL-OPEN(ADV-COMPOSER-1A:Task 2.4 跨 dtype 交集恆空)+ NEW-ISSUE MAJOR(index 同型化)→新增 **D-4**;Codex R2 已 APPROVE v2(v3 增量送雙方 R3 確認)。

> 來源:三方委員會偵察 `handoffs/IC1A-CUTS-ORDER-codex.md`+`IC1A-CUTS-ORDER-composer.md`+`IC1A-REMAINING-CUTS-ORDER-claude.md`(task-id IC1A-CUTS-ORDER)+ Claude 抽驗　|　v2 2026-07-08:修雙家族 adversarial 全部 BLOCKING(`handoffs/IC1A-ALIGN-SPECADV-{codex,composer}.md`,雙 REJECT→本版逐項回應,見 §ADV-RESOLUTION)　|　對應 TODO:docs/IC_PHASE1_1A_ALIGN_TODO.md

## §RISK 風險分級(gate 讀此決定要求強度)
- **大小**:大。跨模組(contracts ↔ orchestrator ↔ ic_analysis_service)、ML/回測正確性核心。
- **命中**:(a) 資料品質——label/feature 錯位→IC 全假;(b) 跨模組共用路徑;(d) ML/回測正確性——差 1 bar 錯位把「動量」測成「反轉」且不報錯。
- **RISK-HIT 宣告**(機檢行):
RISK-HIT: a,b,d
- (a)(d) → §G Golden 必填、雙家族 adversarial 必跑(R1 已跑,雙 REJECT→v2)、三方數據正確性簽核。實作 Codex、review Composer。

## §ADV-RESOLUTION(R1 findings → v2 裁決對照)
| Finding | 裁決 | 落點 |
|---|---|---|
| CODEX-1/COMPOSER-1 consumer-map 漏 | ACCEPT:補全 §C(event_filter/_slice_raw_data_by_mask/_align_label_to_group/xsec:756);IC-first raw+ML 服務=§N 明示另立 epic | §C/§P/§N |
| CODEX-2/COMPOSER-3 oracle 語義 | ACCEPT:定案 **bar-ordinal**(第 i 列 vs 第 i+lag 列,與 `shift(-h)` 一致);禁日曆查找 | §A D-2/Task1.1 |
| CODEX-3/COMPOSER-5 freq/gap 矛盾 | ACCEPT:兩段政策——非 gap 相鄰差==spec.freq;gap 允許但計數/率入 metadata;gate 不取代 split 的 `_validate_expected_frequency`(職責不同,明文) | §A D-3/Task1.1 |
| CODEX-4/COMPOSER-2/6 Tier-1 殺主路徑 | ACCEPT:Tier-1 接受 DatetimeIndex **或** int64 epoch 秒單調 Index(gate 內統一轉 datetime 比對);loader 本刀不改 schema;G-2 必測 materialize→load 真路徑;hermetic RangeIndex 測試遷移義務入 TODO | §A D-1/Task1.1/2.3 |
| CODEX-5 Golden 寫 data_cache | ACCEPT:Golden harness 唯讀 `data_cache`;ingest cache 輸出重導 tmp(環境變數/config 注入);TODO §0 紅線 | §G/TODO §0 |
| CODEX-6/COMPOSER-7/8 M5-M6 不自洽 | ACCEPT:M5 改雙腿 mutation 程序(正常腿 PASS+no-op 腿必 FAIL,雙 receipt);M6 用測試 monkeypatch no-op 對照(非 production flag);M1 抽樣強制含頭尾 2+2+變異區 | §V |
| CODEX-7/COMPOSER-4 horizon | ACCEPT:共用 resolver 解析 `return_(\d+)`(對齊 `_resolve_cross_sectional_label_horizon` 既有 regex);外部 labels 無明確 horizon 元資料/可解析欄名→raise;`purge_gap` 與 gate spec.lag **同源**(修既存 lookahead 面) | §P Task1.2/2.x |
| CODEX-8/COMPOSER-9 Phase 3 | ACCEPT:**defer**——移 §N(cut2 direct-vs-reindexed 雙探針不可丟,收斂另立+漂移測試) | §N |
| CODEX-9 檔名 | ACCEPT:已更正(本檔頭) | — |
| COMPOSER-1 漏項A event_filter TypeError | ACCEPT:Task 2.4 event_filter 同步適配(timestamp 交集過濾,禁 RangeIndex `.loc` 切 datetime);**v3:交集前兩側先做 D-4 同型化,禁裸跨 dtype `Index.intersection`**(R2 反例:int64∩DatetimeIndex=∅) | Task 2.4 |
| R2 COMPOSER NEW-ISSUE index 同型化 | ACCEPT:新增 **D-4**——stage0/stage2 gate PASS 後 orchestrator 把 features_df 與 label 的 index **實體寫回**同型 DatetimeIndex(單一正規化點),下游 slice/event_filter/IC 全吃同型軸,消滅三路分裂;寫回只改 index 不改值(值守恆 sha256 驗) | §A D-4/Task 2.1/2.2 |
| COMPOSER-10/11 接縫/ML | ACCEPT:交付 handoff 凍結 `effective_horizon` 語意;ML label=另立 epic 明示 | §N |

## §A 假設與待使用者確認
- **FACT-RECEIPT**(三方偵察+R1 adversarial 實跑,HEAD 4264bd3):
  - stub:`contracts.py:746-766` `AlignmentSpec` 在,`validate_alignment`=NotImplementedError,生產 0 caller(雙 receipt)。
  - 縱向錯位面(Claude 抽驗+雙 adversarial 擴充):Stage0 `:1609-1611` 無檢查 reindex;Stage2 `:1651-1669` label 掛 kline 原生 index;`_slice_by_mask` `:443-458` 長度巧合 iloc;`_slice_raw_data_by_mask` `:462-479` 同型(COMPOSER-1B);`_stage3_event_filter` `:1671-1704` kline RangeIndex 過濾 datetime features(COMPOSER-1A,實跑 TypeError);`ICEngine._align_label_to_group` `ic_engine.py:594-602` 長度巧合 positional(CODEX-1);`analyze_cross_sectional:756` MultiIndex reindex 無值驗(COMPOSER-1C)。
  - **型別現實(COMPOSER-2 實跑)**:materialize→`_load_features_hdf5`(:2469-2471)回 **int64 秒 Index** 非 DatetimeIndex;`test_load_features_hdf5` 斷言無 timestamps→RangeIndex 合法;V2 `lib.load()` 帶真 DatetimeIndex(6a991c2)。→ 兩型並存=D-1 相容裁決依據。
  - **label 語義**:`generate_log_return=close.shift(-horizon)`=**bar 位移**(label_generator.py:43-47)→ D-2 bar-ordinal 依據。
  - **真資料 gap 現實(雙 adversarial 實跑)**:3sym×12h e53e2290 gap_rate=0%;`data_cache/kline_cache.h5` ETHUSDT/1h 有 >1.5×median 大 gap、`infer_freq=None` → D-3 兩段政策依據;Golden 須補 gap 場景 hermetic。
  - **horizon 既存洞(COMPOSER-4)**:`_resolve_effective_label_horizon`(:110-120)`del labels_df` 只回 config `default_horizon`;縱向 `purge_gap=effective_horizon`(:548-554)→ `return_5`+default=1 時 purge 不足=既存 lookahead 面,本刀 Task 1.2 一併修(命中 (d),不 defer)。
  - 既有紅測:`test_ic_filter_orchestrator.py` 現況 2 failed(pre-existing,HANDOFF 已登)。
- **設計裁決(D-1~D-3,技術決策,依 R1 雙家族建議收斂)**:
  - **D-1 型別相容**:Tier-1 接受 `DatetimeIndex` 或「int64 epoch **秒** 單調唯一 Index」(gate 內轉 datetime 再比;毫秒/混單位/非單調→raise);雙 RangeIndex(無任何時間軸)→raise。
  - **D-2 oracle 語義=bar-ordinal**:第 i 列 close vs 第 i+lag 列 close(kline 驗證軸上 positional),與 label 生成 `shift(-h)` 一致;**禁** `t+lag×freq` 日曆查找;缺棒不產生歧義(跟著 bar 走)。
  - **D-3 freq 兩段**:①非 gap 相鄰差(=眾數 cadence)必須==spec.freq(超 5% 容差→raise);②gap(相鄰差>1.5×cadence)允許,計 gap_count/gap_rate 入 metadata,對齊正確性由 timestamp 精確匹配+oracle 證明,非由連續性;③gate 不取代 split `_validate_expected_frequency`(strict,職責=purge 連續性),兩者並存明文。
  - **D-4 index 同型化寫回(v3,R2 Composer NEW-ISSUE)**:stage0(外部 labels)/stage2(kline 衍生)gate PASS 後,orchestrator 於**單一正規化點**把 `features_df.index` 與 label index 實體轉換寫回 DatetimeIndex(D-1 轉法);下游(`_slice_by_mask`/`_slice_raw_data_by_mask`/`_stage3_event_filter`/IC 計算)一律收到同型軸,禁任何裸跨 dtype `Index.intersection`/`.equals` 比較。寫回只改 index 不改值——值/NaN mask/欄名 sha256 改前後相等(值守恆),`_write_features_h5` 落盤仍存 int64 秒(schema 不變)。
- **待確認:無**(scope 已裁定;D-1~D-3 屬技術裁決,由 R2 閉合複驗把關)。

## §C 約束
- **解耦**:gate kernel 落 `momentum/core/contracts.py`,禁 `from api.`;grep→0 保持。驗不改(0 副作用);不弱化 NaN gate;不改 label 生成語意。
- **consumer map(v2 補全,每項標處置)**:
  1. `_stage2_label_generation`(:1642-1669)— **接 gate**(Task 2.1:kline int64→datetime 軸+驗)
  2. `_stage0` 外部 labels(:1609-1611)— **接 gate**(Task 2.2;horizon 元資料必給或可解析,否則 raise)
  3. `_slice_by_mask`(:443-458)— **消滅長度巧合**(Task 2.3)
  4. `_slice_raw_data_by_mask`(:462-479)— **同 Task 2.3 一併修**(COMPOSER-1B)
  5. `_stage3_event_filter`(:1671-1704)— **timestamp 軸過濾適配**(Task 2.4,COMPOSER-1A:否則 Phase2 接線後 TypeError)
  6. `ICEngine._align_label_to_group`(ic_engine.py:594-602)— **消滅長度巧合**(Task 2.5,CODEX-1)
  7. `analyze_cross_sectional:756` MultiIndex labels reindex — **Tier-1 檢查接入**(Task 2.6;值 oracle 不可行=外部 labels 無 close 對照,Tier-1 index 驗+覆蓋率)
  8. `_resolve_effective_label_horizon`(:110-120)+`purge_gap`(:548-554)— **共用 resolver 修 horizon 同源**(Task 1.2,COMPOSER-4)
  9. cut2 `_append_cross_sectional_labels` oracle — **§N deferred**(雙 adversarial 同判:direct-vs-reindexed 雙探針語意 gate 不涵蓋,硬換=回歸風險)
  10. IC-first raw(`feature_factory.py:2158-2214`→`compute_ic_from_l7_raw`)+ ML label 消費(`xgboost_task_service.py:195-200`/`cross_symbol_training_service.py:52-67`)— **§N 另立 epic 明示**(本刀=IC orchestrator 主流程;不暗示全平台覆蓋)
- **測試遷移義務(COMPOSER-6)**:依賴 RangeIndex positional 語意的 hermetic 測試(`test_stage3_event_filter_uses_raw_data` 等)遷移為 DatetimeIndex fixture;`test_load_features_hdf5` RangeIndex 斷言=loader 行為不變故保留;不得刪除/弱化既有斷言充當修法(diff 驗)。
- **不改**:loader HDF5 schema(D-1 於 gate 內轉型,非改 `_load_features_hdf5`/`_write_features_h5`);cut1 單幣 OOS;cut2 cross_sectional 已簽核行為。

## §G Golden / Baseline((a)(d) 必填)
- **資料**:真實 run `data_cache/features/`(3sym×1h 4a8a0b37 + 12h e53e2290/f754aad4)+ 真 `kline_cache.h5`;禁合成 fixture 充 Golden(hermetic 單元另計,且必補「單點 2×freq gap」hermetic 場景,COMPOSER-5)。
- **唯讀紅線(CODEX-5)**:Golden harness 對 `data_cache/` 唯讀;端到端所需 ingest/報告輸出一律重導測試 tmp(monkeypatch/config 注入 `ic_ingest_cache` 目錄);postflight data_cache 快照必須零變化。
- **oracle**:bar-ordinal(D-2)——每幣以 kline close 第 i 列 vs 第 i+lag 列算 `ln(close[i+lag]/close[i])`,與 label 逐列 `np.testing.assert_allclose(atol=1e-6, rtol=1e-5)`+timestamp 精確匹配。
- **G-2 byte-equal**:gate on vs off(off=測試 monkeypatch `validate_alignment`→no-op,非 production flag)同資料同 config,IC 輸出 DataFrame `.to_numpy().tobytes()` sha256 相等;**必測 materialize→`_load_features_hdf5` 真 ingest 路徑**(int64 Index 型,COMPOSER-2),不只 V2 `lib.load()`。
- **通過條件(可證偽)**:G-1 錯位必抓(M1-M4 各轉紅);G-2 正確必放(上述雙路徑 sha256 相等+gate PASS);G-3 fail-closed(判定不能→raise:毫秒混入/非單調/重複/雙 RangeIndex/horizon 不可解析)。

## §P Phase 與依賴

### Phase 1 — kernel + horizon resolver(依賴:無)
**Task 1.1 — `validate_alignment` 落地**:Tier-1(型別 D-1/單調唯一/cadence D-3/尾端結構 NaN==lag/覆蓋率);Tier-2(close 給定時,bar-ordinal 抽樣 oracle D-2,抽樣強制含頭 2+尾 2+變異敏感區+隨機,有效樣本<8→raise)。例外 `AlignmentViolationError`(命名對照 contracts 既有家族定案)。
**Task 1.2 — 共用 horizon resolver(COMPOSER-4,修既存 lookahead 面)**:抽 `_resolve_label_horizon_from_column(name)`(regex 對齊 `_resolve_cross_sectional_label_horizon` 的 `return_(\d+)`;`label_return_{n}d` 等含單位名→單位換算為 bar 數或 raise);`_resolve_effective_label_horizon` 改真解析(labels_df 欄名優先,fallback default 須 log warning+metadata 標記);縱向 `purge_gap` 與 gate `spec.lag` 同源。mutation:`return_5`+`default_horizon=1`→purge 斷言 FAIL 轉紅。

### Phase 2 — 縱向主路徑接線(依賴:P1)
**Task 2.1** Stage2 kline label 軸正規化(int64 秒→datetime,fail-closed 轉型)+gate;**gate PASS 後依 D-4 把 features_df+label index 同型化寫回**(值守恆 sha256 驗)。
**Task 2.2** Stage0 外部 labels:index 型別/單調驗→reindex→覆蓋率驗;horizon 由欄名 resolver(Task 1.2)解析,不可解析→raise;kline 可得→Tier-2;**PASS 後同 D-4 寫回**。
**Task 2.3** `_slice_by_mask`+`_slice_raw_data_by_mask`:len 相等須 index 逐列相等才 iloc;雙 RangeIndex→raise(D-1);混型同長(int64 vs datetime)→D-1 轉型後比對,禁裸跨 dtype 比較(D-4 寫回後此況不應出現,出現=上游繞過→raise)。
**Task 2.4** `_stage3_event_filter` timestamp 軸適配:**交集前兩側各做 D-1/D-4 同型化**(kline int64→datetime;features 軸經 D-4 已 datetime),再 timestamp 交集過濾;禁整數 `.loc` 切 DatetimeIndex、禁裸跨 dtype `Index.intersection`(R2 反例:int64∩datetime=∅→誤殺);同型化後交集為空→raise(此時=真無交集)。
**Task 2.5** `ICEngine._align_label_to_group` 長度巧合消滅(同 2.3 語義)。
**Task 2.6** `analyze_cross_sectional:756` labels reindex 接 Tier-1(index 驗+per-symbol 覆蓋率;無 close 故無 Tier-2,明文)。
- 各 Task 邊界與 pytest 細目見 docs/IC_PHASE1_1A_ALIGN_TODO.md(Task 2.1-2.6);共同紅線:錯位=raise 非修補;無 production 關閉開關。

### Phase 3 —(v2 移除,見 §N)

## §V 驗證策略與邊界測試目錄
- **mutation(對照 TEST_DESIGN_CHARTER,全部須附轉紅 receipt)**:
  - M1 label 平移 ±1 bar→Tier-2 raise(抽樣含變異區,COMPOSER-8)。
  - M2 同長列序錯 1→Task 2.3/2.5 raise。
  - M3 RangeIndex(雙邊無時間軸)→Tier-1 raise。
  - M4 錯 tf(1h label 配 12h features)→cadence 檢查 raise。
  - M5(**雙腿程序,CODEX-6**):腿A=gate ON+M1 資料→測試 PASS(pytest.raises 命中);腿B=monkeypatch `validate_alignment`→no-op+同資料→**同一測試必 FAIL**(無 raise);雙腿命令+輸出 receipt 皆附,缺一=未過。
  - M6 gate ON vs no-op 對照,正確資料 IC 輸出 sha256 相等(0 副作用證明)。
  - M7(Task 1.2)`return_5`+default=1→purge/lag 斷言 FAIL。
- **層級**:單元(kernel hermetic,含單點 2×freq gap 場景)+Golden(真 3sym×1h/12h,雙載入路徑)+端到端(analyze 真路徑;consumer map 1-8 每項至少一 red-on-break)。
- **邊界目錄**:☑ 空DF ☑ 全NaN ☑ 重複/亂序 ts ☑ 長度巧合 ☑ 錯 tf ☑ lag=0 ☑ NaN 孔抽樣 ☑ 單點 gap ☑ int64 秒/毫秒混入 ☑ event_filter+datetime 軸 ☐ Inf/std=0(不涉)。

## §R 回退
- 每 Task 獨立 commit 可 revert。gate fail-closed 無 production 開關(off 對照僅測試 monkeypatch)。Task 1.2 horizon 修法若使既有 run 的 purge 變寬→行為變更屬正確性修復,metadata 標記,不做相容 shim。Golden FAIL→不 merge。

## §N N/A 登記
- **Phase 3 cut2 oracle 收斂**:v2 defer(雙 adversarial 同判);另立時須保留 direct-vs-reindexed 雙探針+漂移測試。
- **IC-first raw 路徑 gate**(`compute_ic_from_l7_raw`):FF pipeline 對齊另立 epic;本刀不涵蓋,不暗示覆蓋。
- **ML 訓練 label 消費**(xgboost/cross_symbol):FF 產物語意,另立 epic(COMPOSER-11)。
- **loader schema 改造**(HDF5 roundtrip 保 DatetimeIndex):D-1 以 gate 內轉型替代;schema 改造=獨立 epic(影響所有 H5 消費者)。
- **1d 頻率地圖**:沿 cut1/cut2 deferred。
- **features_path vs config_hash 校驗**:pre-existing P2 正交。
- **交付 handoff 義務**:凍結 `effective_horizon` 語意供 1e+1b 刀複用(COMPOSER-10)。
