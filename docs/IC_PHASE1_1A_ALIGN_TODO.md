# IC Phase1 1-align TODO　(版本 v3 **Frozen 2026-07-09**/基於 docs/IC_PHASE1_1A_ALIGN_SPEC.md v3 Frozen/雙 RECONCILE-STAMP PASS)

> SPEC 索引(100% 追溯):Task 1.1 kernel/1.2 horizon resolver/2.1 Stage2/2.2 Stage0/2.3 slice×2/2.4 event_filter/2.5 _align_label_to_group/2.6 xsec:756;Golden G-1/G-2/G-3;Mutation M1-M7;RISK-HIT a,b,d;§ADV-RESOLUTION 13 項;Phase 依賴 P2←P1。合計:Task 8、Golden 3、Mutation 7、consumer map 10(8 接線+2 §N)。

## §0 全域規則與約束(執行端讀完即可遵守)
- **解耦**:kernel 落 `momentum/core/contracts.py`,禁 `from api.`;交付前 `grep -r "from api\." momentum/`→0。
- **驗不改**:gate 只檢查 0 副作用;檢查不過一律 raise `AlignmentViolationError`(命名先對照 contracts 既有例外家族,若已有近義類則沿用);訊息含期望/實際/首個錯位 ts。
- **D-1 型別**:Tier-1 接受 DatetimeIndex 或 int64 epoch **秒** 單調唯一 Index(gate 內 `pd.to_datetime(unit="s")` 轉後比對);毫秒(>1e12)/混單位/非單調/重複→raise;雙 RangeIndex→raise。
- **D-2 oracle**:bar-ordinal——kline 驗證軸第 i 列 vs 第 i+lag 列;禁 `t+lag×freq` 日曆查找。
- **D-3 freq**:非 gap 相鄰差(眾數 cadence)==spec.freq(±5%);gap(>1.5×cadence)允許,gap_count/gap_rate 入 metadata;不動 split `_validate_expected_frequency`。
- **D-4 同型化寫回(v3)**:stage0/stage2 gate PASS 後把 features_df+label index 實體寫回 DatetimeIndex(單一正規化點);寫回只改 index 不改值(值/NaN mask/欄名 sha256 改前後==);落盤 schema 不變;下游禁裸跨 dtype `Index.intersection`/`.equals`。
- **data_cache 唯讀(CODEX-5)**:測試/Golden 一律把 ingest/報告輸出重導 pytest tmp(monkeypatch `ic_ingest_cache` 目錄常數/config);postflight data_cache 快照 0 變化;絕不寫 `data_cache/`。
- **防假綠**:不放寬/刪除既有斷言(diff 驗);mutation M1-M7 全附轉紅 receipt;Golden 用真資料。
- **horizon**:一律經 Task 1.2 resolver;禁直接讀 `default_horizon` 當 lag。
- Logging:`get_logger(__name__)`;gate 熱路徑不 log。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1+1.2 | 無 | kernel+resolver 同屬 contracts/orchestrator 純邏輯,hermetic 可驗 | 中 |
| B2 | 2.1+2.2+2.3+2.4 | B1 | orchestrator 主鏈四接線點,共用端到端測試 | 大 |
| B3 | 2.5+2.6 | B1 | ic_engine+xsec 兩個獨立消費點,回歸面小 | 中 |
- B1→B2 Gate:`pytest tests/momentum/core/test_alignment_contract.py tests/momentum/ -k "alignment_contract or horizon_resolver" -q` 全綠+M1/M3/M4/M7 kernel 級轉紅 receipt。
- B2→B3 Gate:`pytest tests/momentum/ -k alignment_gate -q` 全綠+G-1/G-2/G-3+M5 雙腿+M6 receipt。
- B3 完成 Gate:`pytest tests/momentum/ tests/api/ -q` 無新增紅(pre-existing 2 failed 除外,名單:test_ic_filter_orchestrator_analyze/test_event_filter_fallback)。

## Phase 1 — kernel + horizon resolver(完成後:kernel 可用+horizon 同源,生產未接)

### Task 1.1 — `validate_alignment` 落地
- SPEC ref:P1/Task1.1+D-1~D-3　目標:兩層驗證純函式。
- 輸入/輸出:`(feature_data, target_data, spec: AlignmentSpec, *, close: Optional[pd.Series]=None, sample_size: int=64) -> AlignmentReport`(dataclass:gap_count/gap_rate/checked_samples;失敗=raise)。
- 實作要點:
  1. Tier-1:index 型別依 D-1 正規化(int64 秒→datetime;偽碼 `if is_integer_dtype(idx): ts=pd.to_datetime(idx, unit="s")`,>1e12 值→raise 毫秒);單調+唯一;cadence 檢查依 D-3(`diffs=np.diff(ts); cadence=mode(diffs[diffs<=1.5*median]); assert cadence≈to_offset(spec.freq)`);target 尾端結構 NaN==spec.lag(少於→raise 可疑未來值);覆蓋率<(len−lag)/len×(1−tol)→raise。
  2. Tier-2(close 給定):在 close 軸上 positional——找 feature ts 在 close index 的位置 i,`expected=log(close.iloc[i+spec.lag]/close.iloc[i])`(D-2 bar-ordinal);抽樣=頭 2+尾 2(lag 前)+隨機 sample_size;`assert_allclose(atol=1e-6, rtol=1e-5)` 超差→raise 首個錯位 ts;NaN 孔跳過另抽;有效<8→raise。
  3. 回傳 AlignmentReport 供 caller 寫 metadata;例外攜帶 expected/got/ts。
- 修改檔案:`momentum/core/contracts.py::validate_alignment`(:764 展開)+`AlignmentViolationError`+`AlignmentReport`。既有 caller:僅測試(前 3 位置參數不變)。
- 不可做:不改 AlignmentSpec 欄位;不吞例外;不修補對齊;不做日曆查找。
- 邊界:① 空/全 NaN→raise;② 重複/亂序→raise;③ lag=0+spec 明示→放行;④ NaN 孔抽樣跳過;⑤ 單點 2×freq gap→PASS 且 gap_count=1(D-3);⑥ 毫秒 index→raise。
- 風險緩解:M1/M3/M4。
- 驗證:改寫 `tests/momentum/core/test_alignment_contract.py`:正確(含 gap 場景)→pass;M1→`pytest.raises(AlignmentViolationError)`;M3/M4 同;lag=0→pass;毫秒→raise;`pytest tests/momentum/core/test_alignment_contract.py -q` 全綠。

### Task 1.2 — 共用 horizon resolver(修既存 lookahead 面)
- SPEC ref:P1/Task1.2(COMPOSER-4)　目標:label horizon 單一真相源,gate spec.lag 與 purge_gap 同源。
- 輸入/輸出:`_resolve_label_horizon_from_column(name: str, config: ICConfig) -> int`(bar 數;不可解析→raise InvalidInputError)。
- 實作要點:① regex 對齊既有 `_resolve_cross_sectional_label_horizon` 的 `return_(\d+)`;`label_return_(\d+)d` 等帶單位→依 timeframe 換算 bar 數,無 timeframe 可換算→raise;② `_resolve_effective_label_horizon`(:110-120)改真解析 labels_df 欄名(優先),fallback `default_horizon` 時 `logger.warning`+metadata `horizon_source:"default_fallback"`;③ 縱向 `purge_gap`(:548-554)與 Task 2.1/2.2 gate spec.lag 皆吃此 resolver。
- 修改檔案:`momentum/Analysis/ic_filter_orchestrator.py::_resolve_effective_label_horizon` + 新 helper;既有 caller:`analyze`(:548-554)、`_stage2_label_generation`。
- 不可做:不改 `_resolve_cross_sectional_label_horizon` 既有行為(cut2 簽核);不靜默 fallback。
- 邊界:① `return_5` 欄+default=1→resolver 回 5,purge_gap=5;② 欄名不可解析且無元資料→raise;③ 純 kline 衍生(欄名自產 `return_{h}`)→解析一致。
- 風險緩解:M7。
- 驗證:`pytest tests/momentum/ -k horizon_resolver -q`;M7:`return_5`+default=1 下斷言 `purge_gap==5`,mutation(移除解析回 default)→斷言 FAIL 轉紅 receipt。

### Phase 1 測試+Gate:見 §B B1 Gate。

## Phase 2 — 主路徑接線(完成後:consumer map 1-8 全 fail-closed)

### Task 2.1 — Stage2 kline label 軸正規化+gate
- SPEC ref:P2/2.1　目標:label 出廠掛 datetime 軸+驗。
- 實作要點:① kline `timestamp` int64 秒→datetime 設 close index(fail-closed 轉型同 D-1);② horizon 由 Task 1.2 resolver;③ 生成後 `validate_alignment(features_df, label_series, spec, close=close)`;④ AlignmentReport 入 metadata;⑤ **D-4 寫回**:PASS 後 `features_df.index`+label index 實體轉 DatetimeIndex(單一正規化點),值守恆 `sha256(df.to_numpy().tobytes())` 改前後==。
- 修改檔案:`ic_filter_orchestrator.py::_stage2_label_generation`(:1635-1669)。既有 caller:`analyze`(:605)。
- 不可做:不改 labels_df 欄名;不動 labels_path 分支。
- 邊界:① kline 缺 close→既有 raise;② feature ts 缺 kline 孔→NaN 合法交覆蓋率;③ 毫秒→raise。
- 驗證:`pytest tests/momentum/ -k alignment_gate_stage2 -q`;真 12h e53e2290 端到端(輸出重導 tmp)gate PASS+IC 輸出 sha256 與改前相等(G-2);M1 平移→`pytest.raises(AlignmentViolationError)`。

### Task 2.2 — Stage0 外部 labels gate
- SPEC ref:P2/2.2　目標:外部 labels fail-closed。
- 實作要點:① reindex 前 index 型別/單調/唯一驗(D-1);② horizon:resolver 解析選定 label 欄名,不可解析→raise;③ reindex 後任一欄全 NaN→raise;覆蓋率驗;④ kline_reader 可得→Tier-2;⑤ **D-4 寫回**同 Task 2.1(features+labels 同源 datetime,值守恆 sha256 ==)。
- 修改檔案:`ic_filter_orchestrator.py::_stage0_load`(:1609-1611)。
- 不可做:不建 symbol-aware loader;不靜默丟列。
- 邊界:① int64 秒 labels index→D-1 轉型放行;② RangeIndex labels→raise;③ 1h labels 配 12h features→cadence raise(M4);④ labels 覆蓋超集→合法。
- 驗證:`pytest tests/momentum/ -k alignment_gate_stage0 -q`;M4 轉紅 receipt。

### Task 2.3 — `_slice_by_mask`+`_slice_raw_data_by_mask` 消滅長度巧合
- SPEC ref:P2/2.3(含 COMPOSER-1B)　目標:len 相等不再默認列序一致,兩函式同規則。
- 實作要點:① len 相等分支:`features.index.equals(other.index)` 才 iloc;② 不等且同型可 reindex→維持;③ 雙 RangeIndex→raise(D-1);④ 兩函式(:443-458/:462-479)同改。
- 修改檔案:`ic_filter_orchestrator.py::_slice_by_mask`+`_slice_raw_data_by_mask`。既有 caller:執行端 `grep -n "_slice_by_mask\|_slice_raw_data_by_mask" momentum/Analysis/ic_filter_orchestrator.py` 全列並逐一確認。
- 不可做:不自動 reindex 修補錯位。
- 邊界:① index 相等→iloc 快路徑;② 同長起點錯 1→raise(M2);③ 子集→reindex 分支;④ raw kline int64 vs feature datetime→D-1 轉型後比對(禁裸跨 dtype `.equals`;D-4 寫回後混型=上游繞過→raise)。
- 驗證:`pytest tests/momentum/ -k slice_alignment -q`;M2 轉紅;真資料端到端 sha256 不變(G-2)。

### Task 2.4 — `_stage3_event_filter` timestamp 軸適配
- SPEC ref:P2/2.4(COMPOSER-1A)　目標:修「kline RangeIndex 過濾 datetime features」TypeError/錯位面。
- 實作要點:① `filter_base` 若 kline:int64 ts→datetime 軸(D-1 同款);② **交集前兩側同型化**(features 軸經 Task 2.1/2.2 D-4 寫回已 datetime;若收到 int64=上游繞過→raise);③ 過濾以 timestamp 交集選列(`features_df.loc[features_df.index.intersection(filtered_ts)]`,雙側皆 datetime);④ 禁整數 `.loc` 切 DatetimeIndex、禁裸跨 dtype intersection(R2 反例:int64∩datetime=∅);⑤ 同型化後交集為空→raise(真無交集)。
- 修改檔案:`ic_filter_orchestrator.py::_stage3_event_filter`(:1671-1704)。既有 caller:`analyze`(:610-611)。
- 不可做:不改事件過濾語義(哪些列該留);只改「用什麼軸選列」。
- 邊界:① event_filtering off→原路徑不動;② kline 與 features 完全相同軸→行為等價(回歸);③ hermetic RangeIndex 測試遷移 DatetimeIndex fixture(§C 義務,`test_stage3_event_filter_uses_raw_data` :515-524)。
- 驗證:`pytest tests/momentum/ -k "event_filter" -q` 全綠(fixture 遷移後);真資料 event_filtering on 端到端不 TypeError。

### Phase 2 測試+Gate:見 §B B2 Gate;M5 雙腿(腿A gate ON+錯位→raises PASS;腿B monkeypatch no-op+同資料→同測試 FAIL,雙 receipt);M6 sha256 對照。

## Phase 3(B3)— 獨立消費點

### Task 2.5 — `ICEngine._align_label_to_group` 長度巧合消滅
- SPEC ref:P2/2.5(CODEX-1)　目標:grouped/decay 路徑同規則。
- 實作要點:① len 相等且 index 不等→raise(現行=靜默 positional);② index 相等→快路徑;③ 可 reindex→reindex。
- 修改檔案:`momentum/Analysis/ic_engine.py::_align_label_to_group`(:594-602)。既有 caller:`grep -n "_align_label_to_group" momentum/Analysis/ic_engine.py` 全列。
- 不可做:不動 compute_grouped_ic 其他語義。
- 邊界:① grouped 測試既有綠不變;② 同長錯位→raise(M2 同款)。
- 驗證:`pytest tests/momentum/ -k "grouped or align_label" -q`;hermetic 同長錯位→`pytest.raises`。

### Task 2.6 — `analyze_cross_sectional:756` labels reindex Tier-1
- SPEC ref:P2/2.6(COMPOSER-1C)　目標:MultiIndex labels_path 分支 index 驗+覆蓋率(無 close,無 Tier-2,明文)。
- 實作要點:① reindex 前 labels index 型別/單調驗;② reindex 後 per-symbol 覆蓋率沿 cut2 `_enforce_cross_sectional_label_coverage` 既有守衛(不重造);③ 全 NaN→既有 F4 守衛接手(驗證其真觸發)。
- 修改檔案:`ic_filter_orchestrator.py::analyze_cross_sectional`(:754-756)。
- 不可做:不動 cut2 F2/F4 已簽核行為;不加 Tier-2(無 close 對照)。
- 邊界:① 合法 MultiIndex labels→放行;② index 亂序→raise;③ reindex 全落空→F4 raise(red-on-break 證明)。
- 驗證:`pytest tests/momentum/ -k cross_sectional_labels_path -q` 既有+新增全綠;cut2 18 測試斷言零修改(diff 驗)。

### Phase 3 測試+Gate:見 §B B3 完成 Gate。

## Frozen 前 handoff
SPEC=docs/IC_PHASE1_1A_ALIGN_SPEC.md TODO=docs/IC_PHASE1_1A_ALIGN_TODO.md FOCUS=R2 閉合複驗:R1 全部 BLOCKING 是否真閉合(原提出方重跑同一反例)
(R2 由原 adversarial 提出方複驗;雙 APPROVE+RECONCILE-STAMP 後才 Frozen)

## 自檢(0 FAIL)
- 追溯:SPEC Task 8/Golden 3/Mutation 7/ADV-RESOLUTION 13 全對應(1.1↔D-1~D-3+M1/M3/M4;1.2↔COMPOSER-4+M7;2.1-2.6↔consumer map 1-8;M5/M6↔CODEX-6/COMPOSER-7/8;§N↔CODEX-8/COMPOSER-9/10/11)。
- 深度:每 Task 要點≥3 含偽碼、檔案到函式名、邊界≥2、驗證可證偽。
- 語義:caller 清點=Task 2.3/2.5 明列義務;例外命名對照 contracts 定案;fixture 遷移義務=Task 2.4 邊界③。
- 全棧:純後端刀,無前端層,⋅跳過。
- 錨點:`## §0`/`## §B`/每 Task「驗證」「邊界」「不可做」✅。
