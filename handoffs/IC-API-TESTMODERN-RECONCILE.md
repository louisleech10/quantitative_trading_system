# IC-API-TEST-MODERNIZATION reconcile(SPEC R2 定稿,派實作前)
Task-id: ic-api-testmodern | Date: 2026-07-12 | Chair: Claude(Opus 4.8)

## 審查鏈
- 起草:Claude R1(綜合 grok+composer 三方設計)。
- 雙家族 adversarial:**codex=BLOCK**(6 findings:PIT 契約/warmup/切片未證/去重收窄/分層/藏合成);
  **grok=BLOCK**(BLOCK-1 return_type simple 實證+BLOCK-2 feature PIT 不可證偽實證+4 WARN)。
- 兩腿確認 R1 方向忠實三方共識(C 分層+真 kline+拆 epic+去重+禁 phase6 路徑),未扭曲成再補合成/全刪。

## 主委裁決:全數採納,R2 定稿(兩腿 BLOCK 皆有實跑反例,adversarial 勝)
### R2-1 label 公式與 return_type **一致**;本 epic 釘 **simple**(grok BLOCK-1,CE-RETURN-TYPE 實證)
- 澄清:simple 與 log 生產**皆已實作**(label_generator.py:91-92 dispatch;config 支援 simple|log|excess|risk_adjusted|winsorized)。
  BLOCK-1 非「log 未做」,而是 **fixture label 公式必須與 config_override.return_type 同源**,否則 kline_reader+meta 下 Tier-2 forward oracle 抓不一致報錯。
- 本 epic 選 **simple**(=`config/ic_config.yaml` 預設,摩擦最小):builder labels=`close[t+5]/close[t]-1`;
  `config_override.labels.return_type="simple"` 與 builder 同源字串;oracle 用 simple 公式。
- 刪 R1 章程誤寫死「log-return」的表述(改為「與 return_type 同源,本 epic=simple」)。builder self-test:抽 ≥8 點對 full-close simple oracle 對上。

### R2-2 feature PIT 契約 + 可證偽 mutation(grok BLOCK-2 CE-FEAT-PEEK + codex #1/#2 實證)
- builder docstring 釘公式表:feature 只用 `≤t`(rolling 右端=t、`shift(+k)`);**禁 `shift(-*)` 進 features**;label 才是 `close[t+5]`。
- **新增可自動跑 mutation**(tests/momentum 或 tests/api,如 test_ic_api_real_kline_pit.py):把任一 feature 改 `shift(-1)` → self-test 必 FAIL;把 label 改 backward `close[t]/close[t-5]` → 必 FAIL(比 return_1 更抓 PIT)。不得只靠 code review。
- validate_alignment 呼叫**必傳 close**(釘死+驗)才啟用值 oracle。

### R2-3 warmup/共同裁切(codex #1)
- 讀 `max_lookback-1` warmup 根 → 算 features+labels → **共同 finite mask + 同步裁成同一 512 軸**;
  輸出 512 列 **feature 全 finite、label 僅尾 5 NaN**;禁 fill/ffill/bfill 補初值。

### R2-4 切片已實證(grok receipt,解 codex #3 DELEGATED)
- grok 實跑 receipt(handoffs/IC-API-TESTMODERN-ADV-grok.md §b):ETHUSDT/12h shape 1696、epoch 秒、全 diff=43200、0 gap;
  mid[200:712] 與 tail[-512:] 皆 512 根 0 irregular、0 OHLC NaN;mid+simple+尾5NaN+Tier-2 simple **PASS**。
- 實作採 **mid[200:712]**(避首尾);`min_rows=offset+n_rows=712`(中段)寫死註記(尾切則=n_rows)。

### R2-5 去重收窄(codex #4 + grok WARN-2)
- 刪:`test_feature_list`(≡list_available_features_success 較強)、`test_full_analysis`(≡_endpoint)、
  **`test_deep_analysis_result`**(組合測 start_and_get_result 更強;**保留 test_deep_analysis_start** 因它驗 start status,組合測沒驗)。
- 收尾報告逐一列刪除 nodeid+對照斷言;勿把「刪3」當「23→20 假綠」。

### R2-6 分層修正(codex #5)
- `test_full_analysis_endpoint`/`_with_deep_analysis_config`=**L2**(各自 POST /full-analysis 等真計算),不可由單次 /analyze 供應。
- feature-list=L1 但只讀 h5 不需 completed task;numpy 序列化=獨特 L1 serialization seam(可用 completed task 當容器,不宣稱真 deep)。

### R2-7 藏合成處置(codex #6 + grok WARN-1)
- export fixture 現手寫 `deep_analysis_result`(硬編 0.03/sharpe)+ filtered H5 `[[1.0,2.0]]`——**非 kline 衍生**。
- 裁決:**IC 輸入面(features/labels/timestamps)零合成**為硬性;deep_analysis_result / filtered artifact 若保留 inject,
  **明確標為 API serialization stub**、clone task+測後 restore 防污染,且「無合成」grep 口徑限縮為 IC 輸入面(SPEC 明寫,不用全稱)。
  或改跑真 deep 一次(session 內)。實作二選一並在報告聲明。

## 驗收(R2)
1. 去重後對應 API nodeid 全綠(刪除清單列名);2. IC 輸入面零 `rng.normal`/`np.arange` timestamp(grep)+feature 全 finite;
3. 生產 grep 零 diff;4. **PIT 三方複核**:label=結構 gate+Tier-2 simple oracle;feature=builder self-test mutation(shift(-1) 必紅、backward label 必紅);
5. 缺 kline→pytest.fail;6. 切片/analyze/2 個 full_analysis nodeid 各附獨立 receipt(非顧問聲稱)。

## Verdict
Verdict: APPROVE(條件式)— codex+grok 雙 BLOCK 全數以 R2-1~R2-7 納入化解;兩腿反例皆實跑,R2 每項對應可證偽 gate。
待 codex+grok append RECONCILE-STAMP 確認其 BLOCK 化解後,遷 docs/ 派實作。

## 戳記
(待 codex / grok append)
RECONCILE-STAMP: codex APPROVED 2026-07-12 sha256:28892db629e00b13477e779e2d59350a1bb126549c695a64b4cdf5d6ab525531 task:icatm-recon-codex
RECONCILE-STAMP: grok APPROVED 2026-07-12 sha256:28892db629e00b13477e779e2d59350a1bb126549c695a64b4cdf5d6ab525531 task:icatm-recon-grok
