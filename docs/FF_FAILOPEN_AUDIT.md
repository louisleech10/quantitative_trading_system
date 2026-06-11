# Feature Factory fail-open 鏈 — 深稽定稿(C2/C3/R1)

> 三方獨立深稽 + reconcile(2026-06-09)。Claude(委員C,親讀程式碼)/ Codex(GPT-5.5)/ Composer 2.5。
> 稽核檔,不 commit。修法走另立大任務管線(BRIEF→SPEC→雙家族 adversarial→TODO→impl→review)。

## 0. Claude 獨立版(委員 C,親讀真實程式碼)

親讀路徑:`feature_factory.py` L262-332(層編排)、L382-411(`_safe_execute`)、L2611-2696(非CGSA persist)、L2304-2476(CGSA raw persist)、`feature_validator.py` L129-181、`multi_tf_generator.py` L140-301。

**我的核心論點:病灶不是「沒有 gate」,是三段斷裂**
1. **源頭標錯**:兩條 persist 路徑(CGSA 預設 + 非CGSA legacy)都在 `if persist:` 直接寫,**persist 前不檢查 has_nan / 空層**。`layer_counts`、`validation.has_nan` 都算出來存進 metadata,卻無人據此中止。完整性訊號在源頭就標成「成功」。
2. **訊號粒度不足**:manifest 只有粗布林 `complete`,沒有 `expected/present/failed × {layer, timeframe}` 語義完整性,消費者無從細查。
3. **降級靜默**:`_safe_execute` 把例外吞成空 DF、multi_tf 把 TF 失敗吞成 `continue`+metadata 註記、L6.5 失敗回退原 layers 卻用 preprocessing-enabled config persist(語義不一致)。失敗一路降級成「看似完整」。

**我確認的三點主軸**:C2(層失敗→空DF→續跑→persist 無 gate)、C3(NaN/Inf 只 warning 不 raise,兩路徑 persist 不 gate;非CGSA 還疊全樣本 winsor=L6 洩漏)、R1(部分非primary TF 失敗只記 metadata,primary缺/全跳才 raise)。

## 1. 三方共識(高度一致)

- C2/C3/R1 皆為真實 fail-open,跨 production CGSA 與 legacy 非CGSA。
- Producer 無條件標 `complete=True`(`feature_storage.py:1529,1550`);metadata 有品質訊號但 producer 不 gate。
- 修法主軸三方一致:**manifest 語義完整性(expected/present/failed × layer+timeframe + quality_status) + 消費者 gate + 預設 fail-closed,partial 須顯式 opt-in**。

## 2. 互審補洞(單一視角會漏)

| 來源 | 補的洞 |
|---|---|
| Composer | IC(`ic_engine.py:482-501`)+ V2 Reader(`feature_reader.py:339`)**已 fail-closed 檢查 `complete`**——但被源頭標 true + `_adapt_legacy_manifest_v2:365-378` **強制 complete:True** 繞過;cache 命中不驗完整性 |
| Composer | L6.5 空→用原 layers 但 persist 用 preprocessing config(語義不一致);combine 丟空層靜默縮特徵;winsor 後不重掃 NaN;API task 永遠 `completed` 與品質脫鉤 |
| Codex | **`skipped_timeframes` 全 repo 無任何消費者 gate**(只 profiling 讀);IC gate 不驗 layer/timeframe 數,只驗 complete/非空 |
| Codex | **(B) CGSA serial TF 失敗不 rollback → metadata 說跳過、artifact 卻含該 TF partial L1/L2(矛盾)** |
| Codex | 下游消費者:FeatureLibrary、cross_symbol_training、**xgboost 跨symbol取欄位交集會掩蓋缺欄**、coverage、browser、API restart(見 manifest 就標 completed) |
| Codex | **(D) 既有測試固化 fail-open**:`test_multi_tf_generator.py:161`(缺lowerTF仍成功)、`test_feature_factory_optimization_e2e.py:177`(單engine失敗仍產特徵)→ 修法須區分「可選engine partial(合法保留)」vs「整層/整TF殘缺(該gate)」,不能一刀翻 |

## 3. 修法方向(reconcile,僅方向非實作)

兩層策略(三方一致,Codex/Composer 措辭略異):
1. **manifest 語義完整性**:加 `expected_layers/present_layers/failed_layers`、`expected_timeframes/actual_timeframes/failed_timeframes`、`quality_status: complete|partial|failed`、failure reason。
2. **消費者 gate**:IC / training **預設拒 `partial`**(需 `allow_partial_*` 才用);UI/browser/coverage 可瀏覽 partial 但標示。修正 `_adapt_legacy_manifest_v2` 不再無條件 complete:True;cache/resume 命中須驗語義完整性。
3. **producer**:層/TF 例外**預設 fail-closed**,`allow_partial_layers`/`allow_partial_timeframes` 顯式 opt-in(不靠空 DF 隱式代表);CGSA TF 失敗 rollback 該 TF groups 或只 stream `actual_timeframes`;L6.5 失敗時 config 與 artifact 語義對齊。
4. **關鍵約束(Codex D)**:保留「可選 engine 失敗→partial」的合法路徑,只 gate「整層空 / 整 TF 失敗 / NaN-inf 超標」。改既有 fail-open 測試前須逐一辨明哪些是合法 partial、哪些要翻成 fail-closed。

## 4. 風險定級
**大**:(b) 跨 feature_factory + validator + multi_tf + storage + reader + IC + training + manifest schema(改一處影響一片);(d) partial/NaN artifact 餵 ML/回測=正確性/真實性;(c) 多 phase + 改既有測試契約難回退。→ 修法走完整大任務管線,SPEC/TODO 雙家族 adversarial。

## 5. 待使用者決策
- 是否進入修法 SPEC 設計(本深稽到此為止,還是接著做)。
- 修法範圍:四主軸全包,還是先做 manifest 完整性+消費者 gate(衝擊最小、擋住 V3 誤用)再分期做 producer fail-closed。
