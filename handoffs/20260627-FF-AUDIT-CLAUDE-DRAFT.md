# Feature Factory 正確性稽核 — Claude 風險假設草稿(scoping)

> 緣由:使用者擔心「IC 蓋在 FF 上;FF 若錯/有瑕疵,IC 步步錯」(GIGO)。IC 正確性工程假設 FF 輸出正確,但此假設從未系統稽核。
> 用章程 docs/TEST_DESIGN_CHARTER.md(§0 Oracle 分級 + §A 類別 + §E1 FF 清單)當尺。**scoping 先評估現況嚴謹度,再決定深稽深度**。
> Claude 先自產風險假設([[feedback_claude_own_version]]),交雙家族獨立稽核,reconcile(走 RECONCILE-STAMP 機制)。

## 觀察:FF 測試面大(~50+ 檔),含 golden/causal/align,非「沒測」
test_multi_tf_golden_equivalence、test_timeframe_aligner、test_fracdiff_fft_opt、test_cgsa_multi_tf、test_searchsorted_align、test_winsorize_partition_opt、test_golden_output_generation、failopen V-7… → 覆蓋廣。**問題是嚴謹度(correctness-grade vs smoke/perf),非有無。**

## GIGO 致命軸(請委員按 Oracle 等級分類現有測試 + 標高風險缺口)
1. **特徵計算正確性**:operators/indicators 算出來的是不是它宣稱的東西?有無對 reference 實作(scipy/talib/手算)做 differential(A15)?還是只 smoke(算得出來/非空)?**最怕:某 operator 公式錯,所有用它的特徵全錯,IC/回測全錯。**
2. **生成期因果/無前瞻(最致命)**:特徵在**生成時**有無用到未來 bar?(rolling/lag/shift 方向、fracdiff、d\*、indicator 窗口)。這比 IC 層的洩漏更上游——**若特徵生成就偷看未來,IC 切 train/test 也救不回**。有無「截斷未來資料→歷史段特徵 bitwise 不變」的因果 MR(A2/A14)?
3. **多 TF 對齊(PIT)**:粗→細 TF 對齊有無 look-ahead(用了還沒收盤的高 TF bar)?test_multi_tf_golden_equivalence/timeframe_aligner 是真因果驗還是值比對?(記憶 [[project_mtf_direction_b7_parked]] 有相關但未必涵蓋因果 MR)
4. **L6.5 preprocessing 因果 + cache 正確性**:winsor/fracdiff/d\*/ADF 是否 causal(只用過去)?d_star cache key 是否含 symbol(跨 symbol 不污染)?strong/weak/exact fingerprint 部分失效正確?(記憶 [[project_dstar_first500_optionA]] [[project_stateful_param_audit]] 有相關)
5. **NaN/inf gate + warmup trim**:生成期 NaN/inf 處理、warmup 區是否正確裁切(不把暖機期當有效特徵餵下游)?
6. **跨 symbol 隔離(生成期)**:batch/並行生成時 symbol A 特徵不含 B 資料?(test_cross_symbol_features/symbol_order_permutation 是否真隔離驗)

## 請委員(各獨立)輸出
1. **FF 測試嚴謹度分級**:上 6 軸現有測試各屬 P0/P1/P2/P3(Oracle 等級),哪些是真 correctness、哪些只 smoke/perf。
2. **高風險缺口優先序**:GIGO 致命(尤其軸 1/2)若缺嚴謹驗 → 必補,附模組+為何+建議測試類別。
3. **scoping 判斷**:FF 整體地基「穩/有疑/不穩」?需不需要深稽?哪幾塊最該先補。
4. 我可能漏的 FF 風險軸。
輸出 handoffs/20260627-FF-AUDIT-{CODEX,COMPOSER}.md,STATUS: DONE。
