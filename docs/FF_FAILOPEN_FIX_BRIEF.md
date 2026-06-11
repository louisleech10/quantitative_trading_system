# Feature Factory fail-open 鏈修復 — 決策/簡述(給使用者)

> 大任務第 2 件(承 L1-L4 因果化)。深稽:`docs/FF_FAILOPEN_AUDIT.md`(三方互審)。
> 使用者 2026-06-09 定:**四主軸全包一次**。優先序:正確性 > 效率 > 存檔。

## 問題(一句話)
Feature Factory 在「層失敗 / NaN-Inf / 部分 TF 失敗」時**靜默降級成「看似完整」的殘缺 artifact**,標 `complete=true` 餵給 IC/training/回測 → 命中 look-ahead 以外的「資料真實性」風險。

## 病灶三段斷裂(Claude 委員 C 論點,三方確認)
1. **源頭標錯**:兩條 persist 路徑(CGSA 預設 + 非CGSA)persist 前不檢查 has_nan/空層;品質訊號(layer_counts/has_nan/skipped_timeframes)算了卻不 gate,manifest 無條件 `complete=True`。
2. **訊號粒度不足**:manifest 只有粗布林 `complete`,無 `expected/present/failed × {layer,timeframe}`。
3. **降級靜默**:`_safe_execute` 吞例外回空 DF、multi_tf 吞 TF 失敗、L6.5 失敗回退原 layers 卻用 preprocessing config persist。

## 四主軸修法(全包)
| 軸 | 內容 | 主要檔案 |
|---|---|---|
| **A. manifest 語義完整性** | 加 `expected_layers/present_layers/failed_layers`、`expected_timeframes/actual_timeframes/failed_timeframes`、`quality_status: complete\|partial\|failed`、failure_reasons | `feature_storage.py`、`feature_reader.py`、manifest schema |
| **B. 消費者 gate** | IC/training **預設拒 partial**(需 `allow_partial_*`);UI/browser/coverage 可瀏覽但標示;修 `_adapt_legacy_manifest_v2` 不再強制 complete:True;cache/resume 命中驗語義完整性 | `ic_engine.py`、cross_symbol_training、xgboost_batch、`feature_reader.py`、`feature_factory.py`(resume) |
| **C. producer fail-closed** | 層/TF 例外**預設 abort**;`allow_partial_layers`/`allow_partial_timeframes` 顯式 opt-in(不靠空 DF 隱式);L6.5 失敗時 config↔artifact 語義對齊 | `feature_factory.py`(`_safe_execute` 改/層編排)、`multi_tf_generator.py` |
| **D. CGSA TF rollback** | TF 中道失敗 → rollback 該 TF 已寫 registry groups,或 L7 stream 只含 `actual_timeframes`(消除「metadata 說跳過、artifact 含 partial L1/L2」矛盾) | `multi_tf_generator.py`、`column_group_registry.py` |

## 關鍵約束(Codex 深稽 D,務必守)
**既有測試固化了部分 fail-open 是「刻意」**:
- `test_multi_tf_generator.py:161` — 缺 lower TF 仍成功
- `test_feature_factory_optimization_e2e.py:177` — 單 engine 例外仍產其他特徵

→ 修法**必須區分**:① 「可選 engine 失敗→partial」是**合法保留**(個別指標算不出不該炸全 run);② 「整層空 / 整 TF 失敗 / NaN-Inf 超標 / 標錯 complete」才**翻 fail-closed**。
→ 改既有測試前**逐一辨明**哪些是合法 partial、哪些要翻;**改既有斷言須在 SPEC 列出+理由**(防假綠,實作端不得自行放寬)。

## 語義決策(SPEC 需釘死,adversarial 重點挑戰)
1. `complete` vs 新 `quality_status` 的關係:保留 `complete` 為「可讀/identity」、新增 `quality_status` 為「語義完整」?還是統一?(避免雙來源不一致)
2. `allow_partial_*` 預設值:producer 預設 fail-closed;消費者預設拒 partial。UI 例外白名單怎麼界定。
3. 「NaN-Inf 超標」門檻:沿用既有 inf_ratio 統計還是新訂?fail-closed 是硬 0 還是可配置比率?
4. 既有 partial artifact(已在 disk,complete=true 但實為殘缺)遷移:重生成 bust 還是 lazy 標記?

## 風險
**大**:(b) 跨 8+ 模組 + manifest schema;(c) 改既有測試契約、多 phase、難回退;(d) 直接關係 ML/回測資料真實性。

## 驗收方向
- 注入「層失敗 / NaN / 部分 TF 失敗」→ 產出 **fail-closed 或標 partial**,且 IC/training **拒用**(真實路徑測試,非合成)。
- 合法 partial(可選 engine 失敗)仍依約成功(辨明後保留的既有測試)。
- manifest 語義欄位逐項可證偽;cache/resume 殘缺不命中。
- 改前 vs 改後:殘缺 artifact 從「complete=true 被消費」→「partial 被拒」。

## 管線(大,不跳步)
本 BRIEF → manifest(扁平 ID)→ SPEC → **SPEC/TODO 雙家族 adversarial(Codex+Composer 都做)** → TODO → gate → Codex 實作 + Composer code review → 接回 diff 防假綠 + 親跑 + postflight。
