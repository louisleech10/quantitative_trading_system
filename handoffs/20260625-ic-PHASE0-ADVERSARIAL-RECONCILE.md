# IC Phase 0 SPEC — 雙家族 Adversarial Reconcile（Claude 綜合）

> 2026-06-25 ｜ 來源：`...ADVERSARIAL-CODEX.md`(GPT-5.x) + `...ADVERSARIAL-CURSOR.md`(Composer 2.5)。
> 兩家 Verdict 皆「需修補後派工」。**強烈收斂**：核心根因/Phase 切分正確，但多處 SPEC 需修補才可派工。

## 收斂結論（兩家獨立一致）
1. **IC-TIMEAXIS 真 bug = AttributeError 崩潰，非靜默 1970**。`_get_time_index` numeric 分支回傳 **Series**（非 DatetimeIndex）→ `_iter_time_groups` `time_index.to_series()` → `AttributeError`。**Claude 已親跑確認**（`'Series' object has no attribute 'to_series'`）。
2. **IC-BYVOL → (b) fail-closed + schema 預設 `by_volatility=False` + migration note**。兩家獨立同結論。**此即委員會收斂，照此執行**（使用者 2026-06-25 授權）。
3. **feature_filter 落地會靜默截斷**：前端預設 `max_features:30`（icAnalysisStore.ts:187），落地後所有 analyze 預設截成 30 → 違 §C 不靜默截斷。且 filter 進 `config_override` 後被 `ICConfig.model_validate` **靜默丟棄**（Claude 親驗 `has feature_filter False`）。我 §A#4 寫「metadata」是錯的 → 改為 config_override。
4. **max_features 排序**：用 `sorted()` 穩定可移植序（非 HDF5 欄位順序）；禁 label 衍生 IC 排序（look-ahead）；不得暗示 top/best。
5. **preview_limit 是幽靈欄**：grep api/momentum/frontend 全 0（Claude 親驗）→ F-6「改名」無對象 → 移出範圍，預覽語義改由 F-3 `metadata.truncation_mode` 涵蓋。

## Claude 拍板（reconcile 後寫進 SPEC v2）
| # | Finding（家族） | 處置 |
|---|---|---|
| R-1 | TIMEAXIS 崩潰（兩家 BLOCKING） | Task 2.1 改：`_get_time_index` numeric 分支回 `pd.DatetimeIndex`；T-3 fixture 用 RangeIndex+秒級 timestamp 欄（禁 DatetimeIndex），須先重現崩潰 |
| R-2 | BYVOL fail-closed+預設（兩家 BLOCKING） | Task 2.3 砍雙分支，寫死 (b)：`by_volatility=True` 顯式才 raise，schema 預設改 `False`+migration |
| R-3 | feature_filter 靜默截斷（codex+cursor BLOCKING） | Task 3.2/3.3：預設不截斷（全量）；前端預設 `max_features` 改 undefined；僅顯式套用才截斷；metadata 加 `truncation_mode: preview\|none` |
| R-4 | max_features 排序語義（兩家 MAJOR） | Task 3.2：`sorted(remaining_columns)` after include/exclude；metadata `truncation_order:sorted_column_name`；禁品質/look-ahead 排序 |
| R-5 | ICConfig 丟棄 feature_filter（cursor MAJOR + Claude 親驗） | Task 3.1 驗收加：`load_ic_config(api_override 含 feature_filter)` 不得丟棄；ICConfig 真有欄 |
| R-6 | §G golden 不足（兩家 MAJOR） | §G：decay 改結構化 float 比對（非 byte，同容差）+ 鍵集合相等；grouped 加 per-group row index mask/hash + group sizes；參考實作寫死 `pd.to_datetime(ts,unit='s').year` 獨立 groupby + np.isclose |
| R-7 | C-3/T-3 紅後綠（cursor MAJOR） | §V 明寫 TDD 兩 commit：僅加測試 commit 紅 → 修 code commit 綠；bug 重現腳本入 tests/fixtures |
| R-8 | U-1 漏 cross-sectional（codex MAJOR） | Task 4.3 擴：`analyze_cross_sectional`（service:154-159）也改 to_thread；U-1 驗收改可測 |
| R-9 | U-4 poll 狀態機（cursor MAJOR） | Task 4.4：retry≤3 → poll `/task/{id}` 到 terminal → fetchResult；failed setError(真訊息) |
| R-10 | §A 標籤 + 事實修正（兩家 MAJOR） | §A 每項標 fact-verified/code-verified/assumed；#2 改崩潰機制、#4 改 config_override |
| R-11 | preview_limit 幽靈（兩家 MINOR） | F-6 移出範圍，[F-6] ID 保留標「幽靈欄→併入 F-3」維持 coverage |
| R-12 | T-2 量級邊界（cursor MINOR） | Task 2.1 加 1e15+ 非法 → raise |

## 不採納 / 維持
- 兩家都未否決 Phase 切分、未指 OOM/cache/過度工程問題（Phase 0 範圍克制獲認可）。
- resume/retry 維持不做（§N 補一句不阻派工）。

## 去向
改 SPEC v2（surgical，非重寫）→ 重跑三道機檢 → 生 TODO → gate → 派 codex 實作 + composer code review。
