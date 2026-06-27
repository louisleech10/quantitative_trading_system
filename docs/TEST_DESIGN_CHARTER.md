# 測試設計 & 驗證審查章程（v2，三方收斂 + 雙家族驗證修正）

> **用途**：回答「此 ML 量化交易專案 + 這些 code，該做哪些測試類別、過關條件、測試設計本身如何受審」。**每份 SPEC 須自帶「測試章程」**（§G 模板，自包含),從 §A 勾類別 + 填 Oracle 矩陣 + §F 統計項,並過 §B 設計審查。
> **來源**：Claude 草稿 + Codex/Composer 雙家族補全 → reconcile → **雙家族驗證最終稿(抓 reconcile 漏/錯)** → v2。原始:handoffs/20260627-TEST-DESIGN-CHARTER-*、20260627-CHARTER-VERIFY-*。
> **核心命題**：「測試綠燈」≠「嚴謹驗證」。靠 §0 分級 + §B1 可證偽硬門檻區分廉價綠與嚴謹綠。連動 [[feedback_test_design_rigor_reviewed]]。

## §0 Oracle 等級 + 保證語義（每條測試必標兩者）
**ORACLE（判定方式）**：
| 等級 | 定義 | 注意 |
|---|---|---|
| EXACT | 整數/邏輯/schema `==`、exception 型別、解耦 exit 0 | **只保證 contract/架構,不保證量化數值正確** |
| TOLERANCE | 浮點分尺度、雙路徑對照 | **門檻非通用**;由 SPEC 或既有 frozen budget 按路徑(IC/feature matrix/float32 vs 64)定義,不可一律 1e-9 |
| METAMORPHIC | 變換關係不變(擾動不該影響者→輸出不變);防洩漏主力 | 與 property(A5)不同:此含「未來資料/因果」語義 |
| STATISTICAL | 預註 H0/α/n_min/多重比較校正的統計檢定 | **區分「統計公式正確」vs「策略真有 alpha」**:公式 golden ≠ 投研結論 |
| SMOKE | 只驗不炸/非空/200/有欄位 | **不計入正確性保證** |

**保證等級(claim 層級,與 Oracle 正交)**:`correctness`(數值/資料/洩漏,需 §B1 mutation)/ `contract`(API/schema/解耦,不宣稱量化正確)/ `regression`(golden,P1)/ `smoke`(不計正確性)/ `perf`(**不可替代 correctness**,perf PR 必附 A7 等價否則 BLOCKING)。
**可證偽分級**:P0 correctness(有 mutation probe,改壞必 FAIL)/ P1 regression golden(**無 probe 不可升 P0**)/ P2 contract / P3 smoke(不計正確性)。
**信心標記**:資料/洩漏/數值類若缺「真實 run + mutation + 三方 review」任一 → 只能標 `partial confidence`,不得宣稱「已驗證」。

## §A 測試類別地圖（✦=本專案高風險預設必做；每類:測什麼/過關/ORACLE）
1. **✦資料正確性/完整性/血緣**:來源真實(真 kline 非合成)、schema/dtype/**timestamp epoch 秒**、OHLC 約束(`low≤open,close≤high`)全量掃描、缺口/重複/排序、symbol/TF 隔離。**血緣 metadata 最低欄位:`source/version/row_count/time_range/schema_hash/config_hash`**;mismatch raise。過:真資料跑+值守恆 100%(非抽樣)。ORACLE: EXACT+METAMORPHIC(隔離)。
2. **✦防洩漏/前瞻/PIT/OOS**:chronological split、purge≥horizon、embargo、fit-on-train、rolling 僅過去、scope=test/applied 語義。**最低 MR 集(改 split/preprocess/align 的 Task ≥2 條)**:
   - **MR-L1**:test 標籤 future k 期置亂(purge 外)→ train IC bitwise 不變
   - **MR-L2**:train 末段刪除 → test IC 不變
   - **MR-L3**:test 特徵×常數(c>0)→ Spearman IC 不變(rank 不變)
   過:上述 MR 成立 + scope 契約。ORACLE: METAMORPHIC+EXACT。
3. **✦數值正確性/golden(三層)**:L1 整數/邏輯 `==`;L2 浮點分欄(nan 位置 exact + finite 容差,容差由 SPEC/frozen budget 定);L3 整表 canonical hash 僅回歸告警。NaN/inf gate、決定性(易變欄白名單寫死 `{generated_at,run_id,wall_time}`)、flag-off deep-equal。**澄清:資料檔/JSON artifact 可 sha256;浮點計算表不可只靠整表 hash 當唯一 oracle**。ORACLE: EXACT|TOLERANCE。
4. **量化/統計嚴謹**:見 §F。門檻有文件依據、報效應量+CI(非只 p)、多重比較必校正。ORACLE: STATISTICAL。
5. **不變量/property-based(Hypothesis)**:代數(IC rank 對單調變換/winsor 冪等/align 冪等)、守恆(equity 起點/倉位 bound/prob∈[0,1])。過:≥100 組隨機合法輸入成立+反例 shrink 固定為回歸。**ORACLE: property(代數/守恆,非 metamorphic;A5=代數守恆,A2/A14=因果/洩漏)**。
6. **邊界/退化/錯誤分類**:空/單列/全NaN/短於窗/常數/gap/重複/亂序ts/零volume/極端值。過:逐條明確 raise|skip|fallback|empty+分類,禁 broad except 吞資料錯。ORACLE: EXACT。
7. **行為不變型重構**:改前==改後(值 L2/形狀/輸出大小差>0.5%須批准)。ORACLE: TOLERANCE。
8. **✦整合/真實管線**:materialized service/full run 非只 unit fixture(IC 1a `_slice_by_mask` 教訓)。過:真實 ingestion→FF/IC,BTC/ETH×1h/4h。**任何改主流程 Task ≥1 條 G-NEW/G-OLD**。ORACLE: TOLERANCE golden。
9. **✦跨tier/多symbol/OOM/Resume/Fault**:8/16/24/32GB 語義一致、symbol 隔離、中斷續跑無孤兒、RunLease 競爭、OOM 降級後 TOLERANCE 等價。ORACLE: METAMORPHIC+TOLERANCE。
10. **效能/回歸**:committed budget JSON、複雜度不悄變 O(n²)。**perf PR 必附 A7 等價,缺=BLOCKING(不可只 SMOKE 上界)**。ORACLE: SMOKE 上界+A7。
11. **架構契約/解耦**:`grep "from api\." momentum/`=0、services 不互引、factory、DTO 邊界。ORACLE: EXACT(contract,非量化正確)。
12. **API/型別/相容**:Pydantic↔TS 對照、WS 協議、向後相容、eval_status 不進榜、metadata(scope/applied)達前端。ORACLE: EXACT+snapshot。
13. **冪等/重現性**:同 config_hash 讀回一致、cold/hot cache 同、Optuna seed、CI correctness `NUMBA_NUM_THREADS=1`。ORACLE: TOLERANCE canonical hash。
14. **Metamorphic(變換關係)**:每高風險模組≥3 條 MR、≥1 走真實 kline(feature×c→Spearman IC 不變、label shift(purge 外)→rolling IC 不變、重複 winsor 冪等、多餘高頻欄→輸出不變、price&ATR 同 scale→交易次數/方向不變)。ORACLE: METAMORPHIC。
15. **Differential/雙實作對照**:向量化回測 vs 逐 bar reference、**rank IC vs `scipy.stats.spearmanr`(逐窗 ≤1e-12)**、fast vs legacy winsor、pandas vs numba。ORACLE: TOLERANCE vs trusted slow oracle。
16. **Fuzzing/結構魯棒**:config JSON 巢狀/缺欄/型錯、壞 HDF5/manifest、畸形 WS。過:不 crash→可預期 ValidationError、錯誤分類、case 存 regression。**禁對 OHLCV 數值亂數 fuzz 當正確性 oracle**。ORACLE: EXACT|SMOKE。
17. **Test Data 版本化/Golden 治理**:`tests/fixtures/DATA_MANIFEST.json`(kline sha256/symbols/TF/row/凍結日)、golden 側車 meta(git commit/freeze 命令)、**correctness job 缺 golden/kline = FAIL 非 skip**(用 `requires_kline` mark 分 job,非靜默 skip)、golden 更新=獨立 PR+adversarial+三方簽核。過:golden 可追溯 manifest、漂移→明確 FAIL。
18. **CI Flaky/Quarantine 治理**:markers(`slow/integration/requires_kline/network/tier_matrix/property/metamorphic/flaky_quarantine`)**須註冊進 `pytest.ini`(現缺,待建)**;成本分層(PR=縮影/nightly=full/pre-release=tier-matrix/manual);連 3 次無關失敗→quarantine+issue(不刪 assert);network mock 或 mark;correctness 禁 rerun。
19. **觀測性/運維契約**:progress 單調、batch terminal vs completed 語義、error retryable 標籤、critical metadata 型別。ORACLE: EXACT。
20. **ML 校準/對抗**:機率校準(Brier/reliability)、標籤置亂→AUC/IC 降至 null、特徵 shuffle→IC 崩潰、walk-forward/CPCV ≥smoke。ORACLE: STATISTICAL+METAMORPHIC。
21. **✦回測真實性**:交易會計、雙邊成本/滑價、entry/exit 時點、**同 bar stop/take-profit 優先序**、**unknown exit timestamp 不可 silent skip**、未平倉、MAE/MFE、position sizing、equity 曲線。過:小表逐 trade 手算 oracle 精確比對;禁未來 bar 影響 entry。ORACLE: METAMORPHIC(信號延遲)+TOLERANCE(逐 trade)。
22. **✦多 symbol/cross-sectional**:symbol 隔離、MultiIndex 對齊、label 不可由單幣 ts reindex 誤貼、symbol 順序不變、per-timestamp rank corr、cross-symbol sign conflict、leave-one-out。過:任一 symbol 缺不改其他 IC;報告每 symbol n/coverage/IC dispersion。ORACLE: METAMORPHIC+STATISTICAL。

## §B 測試設計審查紀律（Meta-QA）
- **B1 可證偽硬門檻(mutation)**:聲稱 P0 的測試**必須有 mutation probe**——注入已知 bug 必 FAIL。**最低 probe 集(改相關模組抽 1)**:① 移除 purge → 必紅;② train/test 顛倒 fit(fit_mask=test_mask)→ 必紅;③ cache key 少 symbol → 隔離測試必紅。**須留證據**:patch 摘要 + 哪個測試紅 + 錯誤摘要。做不到→降 P3,禁寫「已驗證」。不全庫 mutmut(成本),用人工 probe。
- **B2 測真實路徑**:主正確性用 `kline_cache.h5` 或 byte-faithful 錄製(含 index dtype+單位);sanitized fixture 僅 A6 邊界或 A15 慢 oracle 輸入;symlink kline+hermetic tmp data_cache 算真實。
- **B3 防假綠**:diff 既有 assert;放寬 tolerance 須 SPEC 明列+adversarial;禁 `pytest.skip` 把 fail 變 skipped。
- **B4 覆蓋追溯矩陣**:SPEC 附 `|性質ID|類別|Oracle|測試檔:函式|Mutation probe|`;缺口=BLOCKING。
- **B5 測試章程 adversarial**:雙家族**專攻測試本身**(弱 oracle/合成掩蓋/缺 MR/無 manifest),與實作 review 分開出 finding。**reconcile 後的最終章程/測試套件本身也須回送驗證**(本 v2 即補此步)。
- **B6 統計檢定設計審查**:每 STATISTICAL 預註 H0/H1/α/n_min/多重比較;禁 data snooping;區分公式正確 vs 有 alpha。
- **B7 Fixture 審計**:每 fixture **在檔旁標** `FAITHFUL|SYNTHETIC|MOCK` + 覆蓋的真實契約欄位 + 已知不覆蓋項(如 ms vs s)。
- **B8 Finding 閉合再驗證(退回修改後必做,2026-06-27)**:任一 review/adversarial/實作 抓到的 Block/Bug,① 給 finding 一個 ID;② 修補須註明「關閉哪個 finding ID」;③ **由原提出方(非修補者)重跑該 finding 的完全相同反例/重查該點**,確認從紅→綠 **且** 該測試可證偽(mutation:把修補還原仍 FAIL);④ 閉合留證(原話/數值前後對比)。**不可只憑「已修」字樣信任**(執行端可能放寬門檻交差)。模型:IC 2 LEAK→修→R2 Codex 重跑原反例證 ROLLING_EQUAL True + OLD_WOULD_EQUAL False。

## §C 流程接入點
SPEC:§A 勾選+填 §G 章程(Oracle 矩陣 B4+§F 統計項) → Adversarial:專審測試章程(B5)+統計設計(B6) → 實作:先寫 P0/P1(洩漏/數值 TDD) → 接回:Claude 抽 mutation(B1,留證據)+diff assert(B3)+核 G-NEW 真跑 → 資料三方簽核:A1+A2+A8 真實 kline → Release:tier-matrix+full slow+manifest 對齊。

## §D 不做/降級
全庫 mutmut CI(用 B1 人工 probe)、OHLCV 數值 fuzz 當 oracle、100% line coverage gate、合成 kline 三方簽核、每 PR 全 tier-matrix(放 nightly)。

## §E 本專案高風險模組 → 必測對照（完整,自包含）
### E1 Feature Factory (`momentum/FeatureEngineering/`)
| 模組 | 風險 | 必做類別 | 具體測試/待補 |
|---|---|---|---|
| L0 ingestion | epoch 秒vs ms | A1,A8 | test_v2_timestamp_golden;擴多 TF |
| MultiTF/Aligner | PIT、對齊錯位 | A2,A14,A15 | mtf_align_golden;**補 MR:截斷高頻未來 bar** |
| L6.5 causal winsor/fracdiff | 非因果、cache 污染 | A2,A3,A9 | causal_winsor;d_star cache key 含 symbol |
| _d_star_cache | 跨 symbol、部分失效 | A1,A9,A13 | **補 strong/weak/exact column fingerprint + 跨 symbol 檔名隔離** |
| FeatureStorage/RunLease | 雙寫、鎖 | A9,A13 | **補雙進程 lease 競爭** |
| generate_features 7 層 | 整合 | A8,A7 | G-NEW full run(縮窗);batch resume |
| Warmup/trim | 誤裁 | A6,A19 | test_b6_warmup_trim |
| Failopen | 語義分歧 | A7,A15 | failopen V-7 系列 |
| Batch multi-symbol | 順序/並行污染 | A1,A9,A22 | symbol_order_permutation_invariant |
### E2 IC Gatekeeper (`momentum/Analysis/`)
| 模組 | 風險 | 必做 | 具體/待補 |
|---|---|---|---|
| split | purge/horizon | A2,A8 | test_ic_1a_cut1_split/leakage(已有) |
| DataPreprocessor | train-only fit | A2,A14 | winsor/coverage/standardize MR(已有) |
| analyze OOS | scope 語義 | A8,A12 | oos+golden G-NEW(已有) |
| **ic_engine rolling IC** | **算法錯,僅 SMOKE** | **A15,A5** | **必補 vs scipy 逐窗;window 邊界(現缺)** |
| cross_sectional | 未接 split | A2,A8,A22 | **cut2 上線 G-NEW 必做** |
| FDR/eval_status(1b) | 多重比較 | A4,A12 | **待建 BH-FDR 合成 IC 金樣本** |
| default-ON fallback | 假 OOS | A6,A12 | applied:false 契約(已有 engine,補 API) |
### E3 回測 (`momentum/Strategy/`)
VectorizedBacktest 信號延遲1bar MR(A2,A14,現多 smoke)、performance_metrics 手算 Sharpe/MDD(A15,A4)、commission/slippage 單筆 PnL 手算(A15)、同 bar stop/TP 優先序+unknown exit 不可 silent(A21)、Optuna overfit CPCV smoke(A4,A20)。
### E4 Cache/儲存
config_hash 組成(A1,A13)、batch orphan/hermetic diff(A9,A19)、CGSA resume 孤兒(A9)、API data_cache_path 用 tmp(A8)。
### E5 API/WS
IC WS mock/mark network(A18,A12)、batch resume(A8,A9)、response v2 型別+applied:false 不進榜(A12)、xgboost training gate(A6,A20)。

## §F 量化/統計檢定清單（完整,自包含）
**IC/因子**:F-IC-1 Spearman/Pearson IC;F-IC-2 IC 序列 t 檢定(H0:μ_IC=0,n_eff≥30,報 t/p/IC mean);F-IC-3 Fisher z+95%CI;**F-IC-4 Newey-West/block bootstrap(自相關>0.1 必做)**;F-IC-5 ICIR 穩定性;F-IC-6 標籤置亂(P0 metamorphic,permuted IC<<real);F-IC-7 特徵置換;F-IC-8 train vs test IC diff+CI(1a OOS 必報);F-IC-9 decay profile 形狀契約。
**多重比較(1b+)**:**F-MC-1 Benjamini-Hochberg FDR(q 明訂,僅對 eval_status=valid+scope=test)**;F-MC-2 有效 m 記錄(fallback 不進 m);F-MC-3 禁逐特徵裸 p 無校正;敏感性加 Bonferroni/Holm。
**策略/回測**:F-ST-1 Sharpe 年化手算;**F-ST-2 Deflated Sharpe(Optuna trials>10)**;**F-ST-3 PBO/CSCV(發布前)**;F-ST-4 bootstrap equity CI;F-ST-5 n_trades<30 不宣稱顯著;F-ST-6 commission±50% 方向不變;White Reality Check/SPA(多策略試驗)。
**ML**:F-ML-1 walk-forward≥3 fold;F-ML-2 CPCV purge≥horizon;F-ML-3 adversarial validation;F-ML-5 機率校準 Brier。
**顯著性補充**:one-sample t 僅 baseline;補 sign test/Wilcoxon/permutation。
**門檻溯源**:min IC/ICIR(樣本量公式或 calibration run ID)、FDR q(業務文件)、purge_gap=f(horizon)。檢定化用**合成 IC 序列(非合成價格)**構造已知 p/FDR assert 決策邊界。

## §G SPEC 測試章程模板（複製用）
```markdown
### 測試章程 — <Task ID>
**風險原則**: (a)(b)(c)(d)
**必做類別**: A1, A2, …
**Oracle 矩陣**:
| 性質 | 類別 | Oracle(EXACT/TOL/META/STAT/SMOKE) | 保證(correctness/contract/regression/smoke/perf) | 測試檔:函式 | Mutation probe + 證據 |
**統計(§F)**: F-IC-2, F-MC-1, …
**真實路徑**: G-OLD/G-NEW/hermetic
**資料 manifest**: kline_cache.h5@<sha>
**CI 標記**: PR/nightly/slow/network/requires_kline
**信心**: full / partial(缺哪步)
**已知不測**: …
```

## §H 現有資產健康度（誠實分級,勿高估）
- **強(可當範本)**:1-contract `test_split_contract`/`test_split_leakage_golden`(P0 EXACT+METAMORPHIC,真 BTC+ETH);1a `test_ic_1a_cut1_leakage`(4/5 P0 METAMORPHIC)、`test_purge_label_mutation_*`(真 mutation probe)、split purge 反例(EXACT)。
- **中(P1/P2,勿當 P0)**:1a golden(P1 regression,且**缺檔會 skip→須改 requires_kline job FAIL**);1-contract `test_baseline_frozen`(僅 P3 SMOKE,不算 correctness)。
- **弱/缺口(高風險必補)**:**ic_engine rolling IC 無 scipy 差分(A15,1a OOS 核心,兩家列第一)**;MR-L2/L3 缺;train/test 顛倒 mutation probe 缺;stage5 統計用注入假 ic_results 無 STATISTICAL;Phase0 grouped/decay 6 列合成 toy(非真 kline);by_volatility 端到端 config override fail-closed 缺;DATA_MANIFEST 不存在;pytest.ini 缺 marker。
- **延後**:cross_sectional(cut2)、FDR 金樣本(1b)、Hypothesis 全庫、Newey-West、回測 A15/A21、d-star fingerprint 全量。
