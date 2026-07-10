# IC 1e+1b Golden baseline capture 設計(委員審查標的)

**狀態**:capture 執行中(產物將落 `handoffs/ic1eb_baseline/`);本檔=編排端(Claude)在 SPEC §G 凍結框架下的落地設計,請各委員**全面審**:覆蓋是否足夠、程序是否可重放、hash 定義是否能支撐 B5 G-1/G-2。發現 BLOCKING 缺口趁早退回重跑(增量成本 25min/顆)。

**審查對象**:本檔 + `scripts/capture_ic1eb_baseline.py`(實際執行碼)
**上游依據**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §G(v2.2 凍結)+`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Task 5.1

## 設計決策(凍結框架外,編排端裁量,即挑戰點)

1. **run 矩陣=10 顆**:9 顆縱向(3sym × [1h/4a8a0b37, 12h/e53e2290, 12h/f754aad4],=§G 明文資料集全矩陣;使用者 2026-07-10 裁決維持 9 顆不砍)+1 顆 xsec 橫截面(3sym×12h/e53e2290;§G 未明文,由 D-H「xsec p_value 從 None 變誠實值、ICIR 排序不得變」反推需要改前快照)。
2. **max_features=500**(欄名排序確定性截斷,orchestrator 既有 sorted_column_name 行為):與顯著性無關、可重放;500 讓 FDR 多重比較素材足量(實測 12h 首500欄 finite p 498、其中 409 過舊 p≤0.05 閘)。截斷發生在 ingestion 後,全寬成本照付(單顆 12h 23.5min 實測)。
3. **config 全預設**:mode 預設 config(`ic_train_test_split=True` 預設 ON)、無 config_override、無 event_query。
4. **五 hash 定義**:summary_table 非顯著性欄(`ic_mean/ic_std/icir/ic_hit_rate/monotonicity_score/long_short_spread/coverage/turnover_rate/ic_half_life/regime_robust`,排除 p_value)→ pandas DataFrame(index=feature_name sort_index)→ index/columns/dtypes/nanmask/values 各 sha256;values 逐欄 to_numeric→float64 canonical 化;`.to_numpy().tobytes()` 僅附加。xsec 缺欄 reindex 補 NaN(新舊同程序→可比)。
5. **G-2 素材**:完整 report JSON 每顆落檔(含 summary_table 全欄=舊 i.i.d. p 保存)+passed_set sha256+p_value 排序 JSON sha256。
6. **明知排除(候選缺口,請挑戰)**:
   - event tier run(D-E α 語意變更):無真實事件源,造事件=合成違反 golden 紅線;判由 M-B/M-D+T-2.2 守。
   - split-off full run(Task 2.3 full 映射):判由契約測試 T-2.3 守,不入 golden 免日後重放成本。
7. **副作用披露**:service 既定行為每顆 run 覆寫 `data_cache/features/{SYM}_{tf}_filtered.h5`+`data_cache/reports/ic_report_ic_gatekeeper.json`(gitignored 衍生物,可重生,非 baseline 產物)。
8. **HEAD 記錄**:manifest 記 `head_sha`(ce667ba);工作樹在 capture 期間凍結不動(B1 實作派工待 baseline 落地後才開)。

## 已知風險自陳
- 12h 500 欄首段為同族 microstructure 特徵(欄名排序副作用)→家族多樣性低;縱向 9 顆跨 sym/config 補了多樣性,但單 run 內同族相關性高,BH PRDS 假設議題(SPEC 已有 fdr_assumption_note 披露義務)在 G-2 解讀時要記得。
- 舊路徑 12h 顆 `passed_features=0`(ic_mean/icir 閘殺光)→G-2 最終 pass/fail diff 可能兩邊皆 0,診斷價值集中在 p 閘層(409/498 舊過)與淘汰原因欄。

## 產出物規格(供 B5 消費)
`handoffs/ic1eb_baseline/`:`report_<tag>.json`×10 + `baseline_manifest.json`(head_sha/max_features/g1_columns/每顆五hash+passed_set hash+耗時)。實作端唯讀;禁重產。

## 委員回覆格式
`handoffs/IC1EB-BASELINE-REVIEW-{codex,composer}.md`:逐點 AGREE/CHALLENGE(附理由與可證偽建議);結論行 `VERDICT: PASS` 或 `VERDICT: BLOCK(原因)`。
