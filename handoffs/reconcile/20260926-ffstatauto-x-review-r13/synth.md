# Reconcile — 20260926-ffstatauto-x-review-r13

**來源** 20260926-ffstatauto-x-review-r13-codex.md, 20260926-ffstatauto-x-review-r13-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 倍數量測忽略 NaN：v32把`warmup_table.ya | P1 | CODEX-R13-P1-01 | 採納（Task 2.4：量測於評估窗內 ground truth 有值而 test 非有限即回 inf；收據逐指標記 finite count、首個有效列、採用 K；加刪 finite guard 之 mutant） | code-contract |
| 雙起點對證不可執行：§G⑦的雙起點gate目前既沒有定義混合 | P1 | CODEX-R13-P1-02 | 採納（§G⑦ 改為逐單一原生週期、K 與 M 以該週期原生列計、M_tf＝K_max_tf＋F_max_tf、A／B 以絕對時間戳對齊、最少重疊 500 列、資料不足輸出 blocked 收據不得算通過；12h 預設全設定列 §N blocked-by，12h 以可容納之設定子集驗機制） | code-contract |
| 死欄過濾不知遮罩：v32要求L3`_dead_filter | P1 | CODEX-R13-P1-03 | 部分採納（採「L3 與 L7 共用同一逐欄純函式、frame 與 CGSA 同」；不採逐欄 mask metadata——所有遮罩皆只延長開頭 NaN 段，故 NaN 率改自各欄首個有限值起算即與遮罩長度無關；有效樣本數只計穩定後之值，欄集合差異逐欄列原因交使用者核可） | code-contract |
| 覆蓋收據範圍不足：09-27coveragereceipt | P2 | CODEX-R13-P2-01 | 採納（Task 2.4：覆蓋腳本列舉基本六類、pattern、microstructure、entropy、tail_risk、cumulative 與多輸出元件；類別集合少一即紅） | doc-sync |
| 無起始日校準時間驗收衝突：v32「未填起始日、平穩化開啟」之路徑下 | P1 | COMPOSER-R13-P1-01 | 採納（§G③ 與 Task 2.1 驗證分支：有起始日保留 `max(校準時間) < 輸出起始日`；`per_column` 改為 `max(校準時間) <` 該欄公開輸出起點） | doc-sync |
| 穩定後逐位元組不變過寬：§C「公開值之不變量」與§G②「`sta | P1 | COMPOSER-R13-P1-02 | 部分採納（收窄：逐位元組相同只限鏈上無第②③類步驟之欄，第②③類以 §G⑦ 為準；駁回其 L1 遞迴反例——v32 之 L1 於未遮罩輸入上計算、只遮輸出，探針遮的是輸入 close，與條文不符；條文補寫遮罩點以免誤讀） | code-contract |
| L5 L6 未查與盤點前提不一致：§AFACT-RECEIPT仍標「L5、 | P2 | COMPOSER-R13-P2-01 | 採納（§A 補 L4、L5、L6、多週期對齊、state_counters 之碼證事實，取自本輪三方探針與讀碼） | doc-sync |

**主委自審**（`handoffs/20260926-ffstatauto-x-review-r13-claude.md`，委員交件前寫成，不列入本輪 lock）另提四條，皆採納入 v33：①逐點 NaN 變有限值之類別缺漏（L2 `binary_signal` 預設啟用，`derived_operators.py:433` 比較後 `astype(int)`）⇒ §C 增第④類；②L6 consensus 同屬第④類（codex 必答 3b 亦指 `consensus_features.py:52,57`）；③`state_counters` 不在生成路徑（`OperatorRegistry` 無呼叫者），盤點收據標明；④進階 atomic `fillna(0.0)` 由 L1 遮罩覆蓋，列入 Task 2.4 量測對象。

**裁決塊修正紀錄**：codex 交件原寫 `CLOSED: none`，係主委 brief 誤指示「r12 無 open ID 者寫 `CLOSED: none`」所致（codex r12 有 sentinel `CODEX-R12-P3-00`），verdict 解析拒收；主委改為 `CLOSED: CODEX-R12-P3-00` 後重新 register-output，findings 內容未動。

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R13-P1-01

**斷言**: v32 把 `warmup_table.yaml` 當作穩定點唯一來源，但現有量測演算法把測試輸出的 NaN 從誤差計算排除，因此可能把仍未產生有效值的 K 認成已收斂；這會直接違反 R1／R4 的「第一個輸出值已穩定」契約。

**碼證**: CODE-ANCHOR: scripts/verify_l1_warmup_requirements.py:114
MUTATION: 對真實 BTCUSDT/12h 以現行 `find_min_warmup` 搜尋 DEMA、TEMA、T3 的 period=13，保留 NaN 排除邏輯；量測輸出會接受含 NaN 的測試尾段。
在 `/private/tmp/r13-review-probe` 以真實 `data_cache/feature_klines/kline_cache.h5` 執行 `load_klines`、`build_indicator_tests`、`find_min_warmup` 並計數測試尾段 NaN，結果為 `DEMA 13 13 [11] 0.000472326184847565`、`TEMA 13 13 [23] 0.0005908107775640778`、`T3 13 13 [59] 0.00018470876356400964`。根因是 `scale_normalized_error` 在 :114–126 用 `mask = ~(np.isnan(gt) | np.isnan(test))` 後才算誤差；同一真實 TEMA probe 的 legacy error 為 `0.0005908107775640778`，strict finite guard 應為 `inf`，`test_nan=23`。現行表亦把 TEMA 的 `recommended_factor` 記為 1.0（`warmup_table.yaml:313-321`）。
修法：量測時只要 evaluation window 中 ground truth 有值而 test 非有限，立即回傳 `inf`；並在收據逐指標記 test／ground-truth 的 finite count、首個有效列與採用 K。Task 2.4 的表格 gate 另加「evaluation window 無未預期 NaN」及刪除 finite guard 的 mutant。可行性證據是同一真實 probe 已顯示 strict guard 將現行誤接受轉為 `inf`，不需改變指標計算或輸出 schema。

**類別**: code-contract

**來源摘要**: scripts/verify_l1_warmup_requirements.py#6ce233d3b77f; momentum/FeatureEngineering/atomic/warmup_table.yaml#d1fbdeae67c8; docs/FFSTAT_SPEC.md#96038395d4f2; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0

## CODEX-R13-P1-02

**斷言**: §G⑦ 的雙起點 gate 目前既沒有定義混合原生週期 K／M 的單位與時間戳對齊，也沒有處理前史不足的欄；依 SPEC 指定的預設全設定與真實資料，BTCUSDT/12h 的 B 起點甚至不存在，故 gate 不能按原文得到可證偽的 pass／red 結果。

**碼證**: CODE-ANCHOR: momentum/FeatureEngineering/warmup_window.py:300
MUTATION: 將 §G⑦ 的 B 切片起點實作為 `M = 2 * max(K)`，以真實 BTCUSDT/12h 執行預設 `ConfigManager().get_merged_config()`；若依目前表與 `estimate_max_warmup_bars` 得到的 2051 個 primary bars，B 起點為 4102，則 1696 根 12h 資料無法建立 B。
在 `/private/tmp/r13-review-probe` 執行 `ConfigManager().get_merged_config()`、`estimate_max_warmup_bars` 與 HDF5 shape probe，實際輸出為 `training ['12h'] primary 12h`、`max_primary_bars 2051`、`m 4102`、`BTCUSDT/12h 1696`、`BTCUSDT/4h 5088`、`BTCUSDT/1h 20352`。§C:47 將 K 定義為 native row count，而 `warmup_window.py:300-319` 又把多週期 N／window 換成 primary bars；§G:79 只寫「倍數表最大 K」而沒有指定 native／primary 單位、A/B 的絕對時間戳 join 或有限值不足時的處置。當前 12h 還有 K 大於可用歷史的非 cumulative 欄，不能直接套用「每個非 start-dependent 欄」的分位數判準。
修法：把 gate 定義成每個單一原生週期的 `K_tf`／`M_tf=2*max(K_tf)`，A/B 以共同絕對 timestamp 對齊，不做位置相減；先明定共同 finite evaluation rows 的最小數量，任一資料不足或欄無 finite overlap 時輸出 blocked receipt（不能算 pass，也不能把欄靜默放進分母）。對目前 12h 歷史不足的情況，§N 應明列為此 gate 的 blocked-by，而不是在 Task 2.3 把它當成已可執行的驗收。可行性證據是上面的 metadata／shape probe 在秒級即可判斷 eligibility，且不需跑全設定 FF run；同一規則可直接驗證 1h／4h 現有 20352／5088 根資料。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2; momentum/FeatureEngineering/warmup_window.py#757a1f8a84ad; data_cache/feature_klines/kline_cache.h5#b1ee5b9abcc1; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0

## CODEX-R13-P1-03

**斷言**: v32 要求 L3 `_dead_filter` 與 L7 dead-feature drop 不把逐欄 stable/calibration mask 列算入 NaN 率，但沒有定義這個逐欄 mask 如何從 L1 經 L2–L6 傳到兩個 dead-filter API；目前兩個 API 只收 DataFrame，真實遮罩前綴會被當成資料缺失並改變欄集合。

**碼證**: CODE-ANCHOR: momentum/FeatureEngineering/operators/rolling_aggregator.py:819
MUTATION: 以真實 BTCUSDT/12h 的前 1696 根 close，依 v32 行為將前 1540 根設為 NaN，再執行 `_variance_filter`；現行結果 `rows 1696 finite 156 nan_rate 0.9080188679245284 kept []`，即使剩餘 156 根有限值且有變異，仍因 mask 列計入 NaN 率而剔除。
`rolling_aggregator.py:819-835` 以整個 `df.isna().mean()`、`(~df.isna()).sum()` 判定；`utils/dead_feature_filter.py:78-87` 同樣以整個輸入的 `nunique`／`notna().sum()` 判定。CGSA 的 `feature_factory.py:3017-3020` 又明載 registry-side L7 dead drop 不在現行 frame step 內，與 Task 2.3 要求兩路徑同一遮罩語意之驗收沒有共同介面。
修法：在 layer result／ColumnGroup metadata 定義逐欄 `stable_mask`（含無起始日 calibration mask）及其衍生欄的 mask 組合規則；L3 與 L7 都以該欄 eligible rows 計算 NaN rate、有效樣本數、常數性，CGSA streaming 與 frame 共用同一純函式。規格須明定 mask 不計入 NaN 分母但仍如何影響 `min_valid_samples`，以及沒有 mask metadata 時 fail-closed。可行性證據是現有 registry 已逐 group 保存 columns／layer／timeframe，frame 與 CGSA 都有單一 dead-filter 呼叫點；以同一真實資料 probe 把 prefix mask 顯式排除後即可分別核對「NaN rate 不剔除」與 `min_valid_samples` 的獨立行為，不需合成行情或全 FF run。

**類別**: code-contract

**來源摘要**: momentum/FeatureEngineering/operators/rolling_aggregator.py#cf448d635077; momentum/FeatureEngineering/utils/dead_feature_filter.py#d465c64126cd; momentum/FeatureEngineering/feature_factory.py#47f362f67de2; momentum/FeatureEngineering/timeframe/multi_tf_generator.py#68174b7a58e4; docs/FFSTAT_SPEC.md#96038395d4f2

## CODEX-R13-P2-01

**斷言**: 09-27 coverage receipt 不能證明 Task 2.4 的「所有 active L1、advanced、CDL 均已入表」；重現腳本只迭代 trend／momentum／volatility／volume／cycle／statistics 六類，排除 pattern 與 advanced 類別，且現行 receipt 仍是 `total_indicators=76 in_table=37 missing=39`。

**碼證**: `handoffs/run_receipts/20260927-warmup-table-coverage.py:13-25` 的 category tuple 沒有 `pattern`、`microstructure`、`entropy`、`tail_risk`；`warmup_table.yaml:367-387` 另以 cumulative／pattern special case 存放非 factor 項。於 `/private/tmp/r13-review-probe` 重跑同名腳本，stdout 仍為 `total_indicators=76 in_table=37 missing=39`，且 missing 清單沒有任何 CDL。這使「missing=0」即使日後出現，也可能只代表六類已補齊，而不代表 Task 2.4 宣稱的完整範圍。
修法：coverage script 明列並驗證 pattern default、三個 advanced category、cumulative family 與每個 active multi-output component；收據逐指標記實際 symbol／timeframe／K，另以 `warmup_lookup` 的 no-fallback API 驗證未知項在 hash/cache 前失敗。這是既有腳本的有限迭代範圍修正，已可由目前 ConfigManager 的 category model 與同一真實 HDF5 來源重跑驗證。

**類別**: doc-sync

**來源摘要**: handoffs/run_receipts/20260927-warmup-table-coverage.py#c3239f7031ad; handoffs/run_receipts/20260927-warmup-table-coverage.txt#f7bb507b7508; momentum/FeatureEngineering/atomic/warmup_lookup.py#31d5e03e39e6; momentum/FeatureEngineering/atomic/warmup_table.yaml#d1fbdeae67c8; docs/FFSTAT_SPEC.md#96038395d4f2

必答成對回覆：

(1a) R1–R7 的核心方向均已寫入 v32：R1 在 §A／§C 要求預熱恆開；R2 在版本註記與 Phase 2 合併；R3 在逐欄 `stable_start`、不全表切齊；R4 在 L1 參數×倍數表與 Task 2.4；R5 在查不到表項時生成前 fail-closed；R6 在完整縮尾窗遮罩與 `+251` 驗收；R7 在 §N 將 post-IC rank／zscore 移交 IC-First。這個判定不把主委提出的疊加層加窗細節誤標成另一次使用者明示裁定。

(1b) 條文出處為 `docs/FFSTAT_SPEC.md:4,47-72,79,106-118,159-165`；裁定／同意方式以 `handoffs/20260927-ffstat-b4-redesign-rulings.md:8-16` 為準。偏離只在「已落實」的證據層：R5 目前 lookup 仍有 4.5 fallback、coverage receipt 仍缺 39 項，故需要 P2-01 與 Task 2.4 完成後的新收據；R4 的量測可靠性另受 P1-01 阻擋。

(2a) 有。新 finding 為：P1-01（warmup measurement 忽略 NaN）、P1-02（§G⑦ 的 M／資料 eligibility／timestamp 對齊不可執行）、P1-03（dead-filter 缺逐欄 mask 介面），以及 P2-01（coverage receipt 範圍不足）。

(2b) 可重現反例：P1-01 的真實 BTCUSDT/12h DEMA／TEMA／T3 結果見其 `**碼證**`；P1-02 的 `max_primary_bars=2051`、`M=4102` 與 12h `1696` 根見其 `**碼證**`；P1-03 以真實 BTCUSDT/12h 1696 根資料套前 1540 根遮罩後得到 `nan_rate=0.9080188679245284`、`kept=[]`；P2-01 的重跑 stdout 為 `total_indicators=76 in_table=37 missing=39`。

(3a) assumed #1 不成立。它把「除 winsor 外每步驟傳遞 NaN」當成尚未驗證的全域事實；實際碼證已見 `state_counters.cross_count` 對首 5 根 NaN 在 lookback=3 時第 3 列即輸出 0，L6 `np.where`／`mean(skipna=True)` 也可能在輸入尚未全穩時出有限值，L5 先 `dropna()` 再做 returns／rolling。這些是 P1-03 所要求的 mask／step inventory 必須覆蓋的反例，不是可用假設。

(3b) `momentum/FeatureEngineering/operators/state_counters.py:67-75` 的 `cross_count` 真實 probe 輸出 `first_input_finite 5`、`first_output_finite 3`；`momentum/FeatureEngineering/meta_features/consensus_features.py:52,57` 使用 `np.where` 與 `skipna=True`；`feature_factory.py:1966-1989` 對 L5 先 `dropna()` 再 `pct_change()`。probe 均在 `/private/tmp/r13-review-probe`，輸入來源為真實 HDF5。

(4a) ①命中：L4 shift 可傳遞，但 L5、L6、state counter、ADF／FFD 與 MTF 不能只靠全域假設，P1-03 及上述碼證已否證部分步驟；②未形成獨立 finding：CGSA executor 先完成 L1 再把 `layer1` 傳給 L2，但 v32 mask 尚未實作，必須以同一函式落在 L1 persistence 前；③命中 P1-03，現行 L3/L7 API 不知道逐欄 mask；④命中 P1-02，8GB 下 12h 之 M 與資料長度不相容；⑤未形成獨立 P1，SPEC 文字以資料起點作為 D 加倍終點，但仍需記錄迭代／載入成本；⑥未發現與 Task 2.3 明文衝突，replace／衍生欄遮罩有列入驗收，尚未有實作證據；⑦未發現 v32 新衝突，v29–v31 的 `run_ic_first` 驗收仍明定平穩化開啟且無起始日即拒絕；⑧命中 P2-01，現有量測 catalog 未涵蓋 MAMA、SAREXT、HT_PHASOR、HT_SINE、KLINGER 的實際收斂測量。

(4b) ①碼證見 `momentum/FeatureEngineering/operators/lag_processor.py:63`、`momentum/FeatureEngineering/feature_factory.py:1966-2003`、`momentum/FeatureEngineering/meta_features/consensus_features.py:52-57`、`momentum/FeatureEngineering/operators/state_counters.py:67-75`、`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3627-3692`、`momentum/FeatureEngineering/timeframe/tf_aligner.py:225-260`；② `momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1460-1467`；③ `rolling_aggregator.py:819-835`、`dead_feature_filter.py:78-87`；④ `warmup_window.py:300-319` 與真實 HDF5 shape probe；⑤ `docs/FFSTAT_SPEC.md:52-56`；⑥ `docs/FFSTAT_SPEC.md:114-116`；⑦ `feature_factory.py:2384-2451` 與 `docs/FFSTAT_SPEC.md:115`；⑧ `scripts/verify_l1_warmup_requirements.py:195-330` 未列該五項，coverage receipt 同樣未列 CDL／advanced。

(5a) 本專案適合「L1 遮罩＋逐步驗證 NaN 傳遞＋對不傳遞步驟另遮」；不需要為所有欄建立完整血緣圖，符合 R3 逐欄與 R4 不在每次生成量測。前提是每個 step 的輸入有限性、mask 起點與不傳遞規則都可機械驗證，且 dead filter 能讀到逐欄 mask。

(5b) 反例是 `cross_count` 的 NaN 前綴輸出有限 0、L6 consensus 的 `skipna=True`、以及 L5 `dropna()` 壓縮時間軸；它們證明單純「L1 先 NaN、其餘自然傳遞」不足，但不證明完整 lineage 是唯一解。可維護的落點是 step-level inventory 加每欄 mask metadata；P1-03 正是目前缺少後者的 contract。

(6a) 目前不可判為可證偽且合理。三個 mutant 的意圖可被 Task 2.3 的 L1／winsor 單項測試捕捉，但 §G⑦ 自身仍有 K／M 單位、timestamp join、finite overlap 與資料不足未定義；在 12h 上連 B 都無法建立，不能宣稱三 mutant「必紅」。

(6b) 真實數字為 `max_primary_bars=2051`、`M=4102`、12h rows=`1696`；此外，state counter real probe 的 `first_input_finite=5` 而 `first_output_finite=3` 也說明只用收斂差值 gate 不能取代步驟級 NaN gate。修正後至少需把每個 `tf` 的 eligibility、共同 timestamp finite rows、mutant 對應測試與 blocked receipt 寫進驗收。

(7a) 不可定案；本輪結論為 blocked。

(7b) 只有以下 P0/P1 blocker：`CODEX-R13-P1-01`、`CODEX-R13-P1-02`、`CODEX-R13-P1-03`。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、本輪 brief、SPEC v32、rulings、r12 codex 交件、template、governance allowlist、manifest；確認目標 diff 只含 docs/FFSTAT_SPEC.md；所有可引用的資料探針已在 `/private/tmp/r13-review-probe` git 複本以真實 HDF5 執行。
TESTS_RUN: `venv/bin/python` 真實 probe（warmup NaN、§G⑦ 資料長度、state counter、dead filter、coverage receipt）均完成；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r13-codex.md --family codex --round-id 8dadad06-3861-4c67-a5c2-fed85a2c2ec9` → `COMPLETENESS PASS(single)`, rc=0；`git status --short -- momentum api scripts tests docs templates config` 前後 `diff -u` rc=0。
FAILURES_SEEN: completeness 首次執行 rc=1，原因是三個 P1 的 `**碼證**` 標籤與 CODE-ANCHOR 分行造成 strict empty-shell 判定；已就地合併格式後重跑 rc=0。收尾 `rm -rf /private/tmp/r13-review-probe /private/tmp/ffstat-r13-wd` 被執行環境安全閘拒絕且未執行；未改寫命令繞過；無其他 PreToolUse hook 阻擋。
SCOPE_CHANGES: none；未改 momentum、api、scripts、tests、docs、templates、config、data_cache 或 git；只新增本家 review 交件與最後狀態交接檔。
NUMERIC_OR_SCHEMA_IMPACT: none；本輪唯讀審查，未改數值、schema、輸出大小或既有測試斷言。
HANDOFF_OUTPUT: handoffs/20260926-ffstatauto-x-review-r13-codex.md；status handoff: handoffs/20260926-20260926-FFSTATAUTO-X-REVIEW-R13.md
TMP_CLEANUP: cleanup 命令被安全閘拒絕，故本輪 `/private/tmp/r13-review-probe` 與指定 `/private/tmp/ffstat-r13-wd` 尚未刪除；`/private/tmp/claude-501` 未列入刪除目標並保留。

VERDICT: blocked
BLOCKED-BY: CODEX-R13-P1-01,CODEX-R13-P1-02,CODEX-R13-P1-03
CLOSED: CODEX-R12-P3-00
STATUS: DONE
## COMPOSER-R13-P1-01

**斷言**: v32「未填起始日、平穩化開啟」之路徑下，§G ③ 與 Task 2.1 仍要求每欄 `max(校準時間) < 輸出起始日`，與 §C 同欄校準值取公開域 `stable_start` 後最早 N 個有效值且校準列留於全史 index 內之設計不可同時滿足（校準時間必 ≥ 該欄首個有效值時間，而全史模式無使用者 `start_date` 時「輸出起始日」若指資料首列則恒不成立）。

**碼證**: `git show 9c37a345:docs/FFSTAT_SPEC.md` → §C「未填起始日」校準列定義；同檔 §G 通過條件③「`max(校準時間) < 輸出起始日`」；Task 2.1 驗證首句同句。對照 §C「校準資料無洩漏」已 split 無起始日例外，但 §G／Task 2.1 未 split。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:79
MUTATION: 以無 `start_date`、平穩化開啟之真實 1h run 產出收據，任取一欄令 `max(校準時間)` 為第 N 個有效值時間、`輸出起始日` 取 manifest 資料首列時間 ⇒ 斷言 `max < start` 失敗而 §G ③ 紅。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0

**修法**: §G ③ 與 Task 2.1 校驗句分支——僅「有 `start_date`＋校準域／封包路徑」保留 `max(校準時間) < 輸出起始日`；`output_start_source=per_column` 時改為 `max(校準時間) < 該欄公開輸出起點`（=第 N 個有效值下一列）且 Task 2.3 ④ 之 spy 為準。可行性：純 SPEC／manifest 文案與既有測試名分支，無新長跑檢查。

---

## COMPOSER-R13-P1-02

**斷言**: §C「公開值之不變量」與 §G ②「`stable_start` 之後四 hash 與改前（無遮罩基準）逐欄全等」對遞迴／受前史輸入影響之欄不成立——L1 前段改 NaN 後同索引之重算值可與改前未遮罩值大幅偏離，與 brief assumed「stable_start 後逐位元組相同」矛盾。

**碼證**: `venv/bin/python /tmp/ffstat-r13-wd/probe_invariance.py` → BTCUSDT 1h 前 800 根：`close.ewm(span=20)` 全史 vs 前 200 根置 NaN，索引 250 處 `46252.99` vs `46254.85`，`max_abs_diff_after_mask_end=250.49`（非零）。§A 已有 codex EWM 600 列改變之前例；v32 宣稱與 §G ② 未限定僅 window_only。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:61
MUTATION: 對任一 recursive L1 欄（如 EMA_233），無起始日 run 在 `stable_start` 列取改後值，與 worktree 重冻之改前 baseline 同 timestamp 比對 ⇒ 超出 float 相等，§G ② 紅。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0

**修法**: 刪除或收窄 §C 不變量／§G ②——改前基準改為「同遮罩語意下重冻」或僅對 window_only／已證 L2+ min_periods=window 鏈路聲明 hash 全等；recursive 與 L3+ 改以 §G ⑦ 收斂容差為唯一公開正確性判準。可行性：§G ⑦ 與 Task 2.3 ⑥ 已規劃全設定探針，調整 ② 文案不新增生成期分鐘級 gate。

---

## COMPOSER-R13-P2-01

**斷言**: §A FACT-RECEIPT 仍標「L5、L6 未查」，但 v32 §C 要求 L2–L6.5 與多週期對齊完整 NaN 傳遞盤點收據，設計前提與已驗證事實清單不一致，實作前無法確認「只遮 L1＋縮尾」是否充分。

**碼證**: `git show 9c37a345:docs/FFSTAT_SPEC.md` §A 末條 FACT「L5、L6 未查」；§C「盤點範圍：… L5 … L6 … 多週期對齊」。Task 2.3 ② 要求盤點收據與 AST 步驟集合全等。靜態：`tf_aligner.py:225-249` 對 `idx_map=-1` 寫 NaN（傳遞）；`state_counters.py:128-133` `cross_count` 窗未滿前為 NaN 但语义 0 计数——须入盘点。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:34
MUTATION: 若盤點收據缺 L5 reference 對齊或 L6 state_counters 任一步 ⇒ Task 2.3 ②「少一即紅」在 impl 前即無法簽 off。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2

[P2] 不單獨挡 VERDICT；须于 Task 2.3 动工前补 FACT 或收拢盘点范围措辞。

---

