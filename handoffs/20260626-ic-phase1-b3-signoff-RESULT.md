# IC Phase 1 B3 — 三方數據正確性簽核結果：未過（回修）

> Claude(獨立) ✅PASS、Composer(獨立) ✅PASS、**Codex(adversarial 自挑戰) ❌ 6 [LEAK]**。
> 鐵律：任一方有疑→不通過。Codex 實跑最小反例、Claude 自驗 #1/#3 為真 → **B3 不過,回 Codex round-2 修**。
> 教訓見記憶 [[feedback_adversarial_beats_signoff]]：簽核式 review 會漏,adversarial 獵漏才現形。

## 必修 LEAK（Codex 自挑戰，Claude 部分自驗）

| # | LEAK | 嚴重度 | Claude 自驗 | 修法 |
|---|---|---|---|---|
| L1 | `expected_freq=None` 時 rows-purge 遇 gap 直接放過（gap 偵測被 `and expected_freq is not None` 短路） | 高 | ✅ 實跑反例放過 | rows-purge **必須要求 expected_freq**,否則 raise;只有 timedelta 才允許 None |
| L2 | **無 train/test pair-level 檢查**：validate_split_integrity 只驗單 plan,沒驗 train 是否落入 test 的 purge/embargo 區間（核心洩漏向量） | 高 | ✅ 碼證(函式只收單 plan) | 新增 `validate_split_pair_integrity(train_plan,test_plan,...)`:依 test ranges 重算禁止區間,assert train 不落入 |
| L3 | 空 `row_index` 提早 return,繞過 symbol 必填/純度檢查 | 中 | ✅ 實跑反例放過 | 先驗 symbol/dtype/base shape 再對空 row_index 決定;空 train/test 由 adapter 明確 skip/raise 非 silently valid |
| L4 | symbol dtype/NaN 不 fail-closed:bytes symbol 通過;`split_per_symbol` 的 `groupby` 預設 dropna=True 靜默丟 NaN symbol 列 | 中 | 碼證(無 type validation+groupby預設) | symbol 先 normalize 非空 str;bytes decode;NaN/None/pd.NA → raise;`groupby(dropna=False)` 並對 NaN group raise |
| L5 | WF adapter 忽略 embargo:WF 只用 purge_gap 設 test_start,adapter 只把 embargo 寫進 plan metadata 不檢 train,後續 fold 可訓練在前 fold test 後 embargo 內 | 高 | 碼證(wf:267 無 embargo;adapter:125 只寫不檢) | WF adapter 重算每 fold `[test_end,test_end+embargo_len)`,assert 各 fold train 不含先前 fold embargo rows;或明確不支援 WF embargo 則 raise |
| L6 | CPCV strict check 以 returned test 為真,無獨立驗 expected test boundaries(splitter bug 改 test 邊界且 train 一致則漏) | 低 | 碼證 | adapter 依 n_groups/n_test_groups/max_paths 自建 expected test group sets,assert returned test==expected 再檢 train |

## 每個 LEAK 須補可證偽測試（真實 kline,反例必 pytest.raises）
- L1: rows+expected_freq=None → raise。L2: train 落入 test embargo → raise。L3: 空 row_index+symbol=None → raise。L4: NaN/bytes symbol → raise。L5: WF 跨 fold embargo 違反 → raise。L6: 偽造 returned test 邊界 → 被獨立重建抓到。

## 不變
- Composer 簽核的 POSITIVE 仍成立:跨 symbol 強條件、gap 查 base 時間線(L1 是它的「expected_freq 未設」缺口)、解耦 0、wf/cpcv 未改、用真實 kline。修 L1-L6 是**強化**不是推翻。
