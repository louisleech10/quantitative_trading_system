# 測試設計 & 驗證審查章程（v1，三方收斂）

> **用途**：回答「此 ML 量化交易專案 + 這些 code，該做哪些測試類別、過關條件為何、測試設計本身如何受審」。往後**每份 SPEC 須附「測試章程」**（§G 模板），從 §A 勾選類別 + 填 Oracle 矩陣 + §F 統計項，並過 §B 的設計審查。
> **來源**：Claude 草稿 + Codex(gpt-5.5) + Composer(2.5) 雙家族專業補全收斂。原始：handoffs/20260627-TEST-DESIGN-CHARTER-{CLAUDE-DRAFT,CODEX,COMPOSER}.md。
> **核心命題**：「測試綠燈」≠「嚴謹驗證」。算個數字/查個欄位的廉價綠，與證明性質的嚴謹綠，份量天差地別——靠 §0 分級 + §B 可證偽硬門檻區分。連動 [[feedback_test_design_rigor_reviewed]]。

## §0 Oracle / 保證等級（每條測試必標）
每條測試標 `ORACLE` 與 merge 是否計入「正確性保證」：
| 等級 | 定義 | 計入正確性? |
|---|---|---|
| **EXACT** | 整數/邏輯/schema `==`、exception 型別、解耦腳本 exit 0 | 是 |
| **TOLERANCE** | 浮點分尺度 `abs≤1e-9 或 rel≤1e-7`、雙路徑對照 | 是 |
| **METAMORPHIC** | 變換關係不變（擾動「不該影響」者→輸出不變） | 是（防洩漏主力） |
| **STATISTICAL** | 預註 H0/α/n_min/多重比較校正的統計檢定 | 是（量化） |
| **SMOKE** | 只驗不炸/非空/200/有欄位 | **否**（不算正確性簽核） |

**可證偽分級（P0-P3，§B1）**：P0 正確性（有 mutation probe，改壞必 FAIL）/ P1 回歸 golden / P2 契約 / **P3 smoke（不計入正確性）**。

## §A 測試類別地圖（✦=本專案高風險預設必做）
1. **✦資料正確性/完整性/血緣**：來源真實(真 kline 非合成)、schema/dtype/**timestamp 單位(epoch 秒)**、OHLC 約束全量掃描、缺口/重複/排序、symbol/TF 隔離、config_hash/manifest 一致。過：真實資料跑 + 值守恆 100% + mismatch raise。ORACLE: EXACT+METAMORPHIC。
2. **✦防洩漏/前瞻/PIT/OOS**：chronological split、purge≥horizon、embargo、fit-on-train、rolling 僅用過去、scope=test/applied 語義。過：**擾動 test/purge→train 指標 bitwise 不變**（每改 split/preprocess/align 的 Task ≥2 條 MR）。ORACLE: METAMORPHIC+EXACT。
3. **✦數值正確性/golden（分三層,float 不可裸 sha256）**：L1 整數/邏輯 `==`；L2 浮點分欄(nan 位置 exact + finite 容差);L3 整表 canonical hash 僅回歸告警。NaN/inf gate；決定性(易變欄白名單寫死 `{generated_at,run_id,wall_time}`)；flag-off deep-equal。ORACLE: EXACT|TOLERANCE。
4. **量化/統計嚴謹**：見 §E。門檻有文件依據、報效應量+CI(非只 p)、多重比較必校正。ORACLE: STATISTICAL。
5. **不變量/property-based(Hypothesis)**：代數(IC rank 對單調變換/winsor 冪等/align 冪等)、守恆(equity 起點/倉位 bound/prob∈[0,1])。過：≥100 組隨機合法輸入成立 + 反例 shrink 固定為回歸。ORACLE: METAMORPHIC。(需補 `hypothesis` 基建)
6. **邊界/退化/錯誤分類**：空/單列/全NaN/短於窗/常數/gap/重複/亂序ts/零volume/極端值。過：逐條明確 raise|skip|fallback|empty + 錯誤分類，禁 broad except 吞資料錯。ORACLE: EXACT。
7. **行為不變型重構**：改前==改後(值 L2/形狀/輸出大小差>0.5%須批准)。ORACLE: TOLERANCE。
8. **✦整合/真實管線**：materialized service/full run 非只 unit fixture(IC 1a `_slice_by_mask` 教訓:unit 抓不到整合 bug)。過：真實 ingestion→FF/IC path,BTC/ETH×1h/4h,缺檔明確 skip。**任何改主流程 Task ≥1 條 G-NEW/G-OLD**。ORACLE: TOLERANCE golden。
9. **✦跨tier/多symbol/OOM/Resume/Fault**：8/16/24/32GB 語義一致、symbol 隔離、中斷續跑無孤兒、RunLease 競爭、OOM 降級後 TOLERANCE 等價。ORACLE: METAMORPHIC+TOLERANCE。
10. **效能/回歸**：committed budget JSON、複雜度不悄變 O(n²)、**perf PR 必附 A7 等價測試**(僅 perf 無等價=BLOCKING)。ORACLE: SMOKE 上界+A7。
11. **架構契約/解耦**：`grep "from api\." momentum/`=0、services 不互引、factory、DTO 邊界。ORACLE: EXACT。
12. **API/型別/相容**：Pydantic↔TS 對照、WS 協議、向後相容(新參數有 default)、eval_status 不進榜、metadata(scope/applied)達前端。ORACLE: EXACT+snapshot。
13. **冪等/重現性**：同 config_hash 讀回一致、cold/hot cache 同、Optuna seed、CI correctness 用 `NUMBA_NUM_THREADS=1`。ORACLE: TOLERANCE canonical hash。
14. **Metamorphic(變換關係)**：每高風險模組≥3 條 MR、≥1 條走真實 kline（如 feature×c→Spearman IC 不變、label shift(purge 外)→rolling IC 不變、重複 winsor 冪等、多餘高頻欄→輸出不變）。ORACLE: METAMORPHIC。
15. **Differential/雙實作對照**：向量化回測 vs 逐 bar reference、rank IC vs `scipy.stats.spearmanr`(≤1e-12)、fast vs legacy winsor、pandas vs numba。ORACLE: TOLERANCE vs trusted slow oracle。
16. **Fuzzing/結構魯棒**：config JSON 巢狀/缺欄/型錯、壞 HDF5/manifest、畸形 WS payload。過：不 crash→可預期 ValidationError、錯誤分類正確、case 存為 regression。**禁對 OHLCV 數值亂數 fuzz 當正確性 oracle**。ORACLE: EXACT exception|SMOKE。
17. **Test Data 版本化/Golden 治理**：`tests/fixtures/DATA_MANIFEST.json`(kline sha256/symbols/TF/row/凍結日)、golden 側車 meta(git commit/freeze 命令)、缺失策略、**golden 更新=獨立 PR+adversarial+三方簽核**。過：golden 可追溯 manifest、漂移→明確 FAIL 非 silent。
18. **CI Flaky/Quarantine 治理**：markers(`slow/integration/requires_kline/network/tier_matrix`)、PR 預設排除 slow、連 3 次無關失敗→quarantine+issue(不刪 assert)、network 測試 mock 或 mark、correctness **禁 rerun**。
19. **觀測性/運維契約**：progress 單調、batch terminal vs completed 語義、error retryable 標籤、critical metadata 型別。ORACLE: EXACT。
20. **ML 校準/對抗**：機率校準(Brier/reliability)、標籤置亂→AUC/IC 降至 null、特徵 shuffle→IC 崩潰、walk-forward/CPCV ≥smoke。ORACLE: STATISTICAL+METAMORPHIC。

## §B 測試設計審查紀律（Meta-QA）
- **B1 可證偽硬門檻(mutation)**：聲稱 P0 正確性的測試**必須有 mutation probe**——人工注入已知 bug(拿掉 fit_mask/移除 purge/train-test 顛倒/cache key 少 symbol)**必 FAIL**。做不到→降 P3，**禁在 SPEC 寫「資料正確性已驗證」**。不必全庫 mutmut（成本），用人工 probe 最低集。
- **B2 測真實路徑**：主正確性路徑用 `kline_cache.h5` 或 byte-faithful 錄製(含 index dtype+單位)；sanitized fixture 僅限 A6 邊界或 A15 慢 oracle 輸入；symlink kline+hermetic tmp data_cache 算真實。
- **B3 防假綠**：diff 既有 assert；放寬 tolerance 須 SPEC 明列+adversarial；禁 `pytest.skip` 把 fail 變 skipped。
- **B4 覆蓋追溯矩陣**：SPEC 附 `|性質ID|類別|Oracle|測試檔:函式|Mutation probe|`;缺口=BLOCKING。
- **B5 測試章程 adversarial**：雙家族**專攻測試本身**(弱 oracle/合成掩蓋/缺 MR/無 manifest),與實作 review 分開出 finding。
- **B6 統計檢定設計審查**：每 STATISTICAL 測試預註 H0/H1/α/n_min/多重比較策略；禁 data snooping(用 test 集調門檻再報 test 績效)。
- **B7 Fixture 審計**：每 fixture 標 `FAITHFUL|SYNTHETIC|MOCK` + 覆蓋的真實契約欄位 + 已知不覆蓋項(如 ms vs s)。

## §C 流程接入點
| 階段 | 動作 |
|---|---|
| SPEC | §A 勾選 + 填 §G 章程(Oracle 矩陣 B4 + §E 統計項) |
| Adversarial | 專審測試章程(B5)+ 統計設計(B6) |
| 實作 | 先寫 P0/P1(洩漏/數值 TDD)再寫 feature code |
| 接回 | Claude 抽 mutation(B1)+diff assert(B3)+核 G-NEW 真跑 |
| 資料三方簽核 | A1+A2+A8 真實 kline,三方獨立 adversarial |
| Release | tier-matrix + full slow + manifest 對齊 |

## §D 不做/降級清單
全庫 mutmut CI(用 B1 人工 probe)、OHLCV 數值 fuzz 當 oracle、100% line coverage gate、合成 kline 三方簽核、每 PR 全 tier-matrix(放 nightly)。

## §E 本專案高風險模組 → 必測對照（摘要；全表見 Composer 補全 §E）
- **Feature Factory**：L0 epoch 秒vs ms(A1,A8)、MTF align PIT(A2,A14,A15 補截斷未來 bar MR)、L6.5 causal winsor/fracdiff+d_star cache key 含 symbol(A2,A3,A9)、RunLease 雙進程競爭(A9,A13)、7 層 G-NEW full run+batch resume(A8)、warmup trim(A6)、symbol order permutation invariant(A1,A9)。
- **IC Gatekeeper**：split purge/horizon(A2,A8 已有)、DataPreprocessor train-only fit MR(A2,A14)、analyze OOS scope(A8,A12)、**ic_engine rolling IC vs scipy(A15 待補)**、**cross_sectional cut2 上線 G-NEW 必做**、**FDR/eval_status 1b BH 金樣本待建(A4)**、default-ON fallback `applied:false` 契約(A6,A12)。
- **回測**：VectorizedBacktest 信號延遲1bar MR(A2,A14 現多 smoke)、performance_metrics 手算 Sharpe/MDD 對照(A15,A4)、commission/slippage 單筆 PnL 手算(A15)、Optuna overfit CPCV/walk-forward smoke(A4,A20)。
- **Cache**：config_hash 組成(A1,A13)、batch orphan/hermetic diff(A9,A19)、CGSA resume 孤兒(A9)、API data_cache_path 用 tmp(A8)。
- **API/WS**：IC WS mock/mark network(A18,A12)、batch resume(A8,A9)、response v2 型別(A12)、xgboost training gate(A6,A20)。

## §F 量化/統計檢定清單（具體可執行；全表見 Composer 補全 §F）
- **IC/因子**：F-IC-2 IC 序列 t 檢定(n_eff≥30)、F-IC-3 Fisher z CI、**F-IC-4 Newey-West/block bootstrap(自相關>0.1 必做)**、F-IC-6 標籤置亂(P0 metamorphic)、F-IC-7 特徵置換、F-IC-8 train vs test IC diff+CI(1a OOS 必報)。
- **多重比較(1b+)**：**F-MC-1 Benjamini-Hochberg FDR(q 明訂,僅對 eval_status=valid+scope=test)**、F-MC-2 有效 m 記錄、F-MC-3 禁逐特徵裸 p 無校正。
- **策略/回測**：F-ST-1 Sharpe 年化手算對照、**F-ST-2 Deflated Sharpe(Optuna trials>10)**、**F-ST-3 PBO/CSCV(發布前)**、F-ST-4 bootstrap equity CI、F-ST-5 n_trades<30 不宣稱顯著。
- **ML**：F-ML-1 walk-forward ≥3 fold、F-ML-2 CPCV purge≥horizon、F-ML-3 adversarial validation、F-ML-5 機率校準 Brier。
- **門檻溯源**：min IC/ICIR(樣本量公式或 calibration run ID)、FDR q(業務文件)、purge_gap=f(horizon)。檢定化用**合成 IC 序列(非合成價格)**構造已知 p/FDR 場景 assert 決策邊界。

## §G SPEC 測試章程模板（複製用）
```markdown
### 測試章程 — <Task ID>
**風險原則**: (a)(b)(c)(d) 命中項
**必做類別**: A1, A2, …
**Oracle 矩陣**:
| 性質 | 類別 | Oracle(EXACT/TOL/META/STAT/SMOKE) | 測試檔:函式 | Mutation probe |
**統計(§F)**: F-IC-2, F-MC-1, …
**真實路徑**: G-OLD / G-NEW / hermetic
**資料 manifest**: kline_cache.h5@<sha>
**CI 標記**: PR / nightly / slow / network
**已知不測**: …
```

## §H 現有資產健康度（範本 vs 缺口）
- **可當範本**：IC 1a leakage/split/oos/golden、failopen V-7、mtf_align_golden、b4 hermetic data_cache、vectorized_backtest 邊界。
- **缺口（待建）**：cross_sectional(cut2)、FDR BH 金樣本(1b)、deep cache invalidation、Hypothesis 基建、正式 DATA_MANIFEST、回測 A15 雙實作+look-ahead MR、CI quarantine/network/tier_matrix 統一 marker。
