# 派工:修 P0-FF-3 metadata gate 一致性(Composer)

## 現況(關鍵:因果健全,只是 gate 矛盾)
`test_c3_multitf_truncation_invariant` 失敗在 **metadata gate**(`ff_truncation_mr_helpers.py:1028`):
`assert full.manifest.feature_schema_hash == trunc.manifest.feature_schema_hash`。
**但 columns + values + NaN gate 全先過了**(gate 順序 columns→values→warmup→metadata)→ **多 TF 對齊因果健全、無 look-ahead**(值在容差內穩定)。對齊 mutation `test_mutation_align_lookahead_fails` 也正確紅。

`feature_schema_hash = compute_feature_schema_hash(feature_columns)` = **欄集 hash**。多 TF(4h/12h 對齊衍生 near-empty 欄)列數依賴 churn → full/trunc 欄集略不同 → schema_hash 不同。**但 columns gate 已用「交集 + 不對稱掉欄門檻 max(100,0.1%union)」接受這種有界 churn 且通過**(差異在門檻內)。所以 metadata schema_hash exact **與 columns gate 自相矛盾**。

## 修法(一致性,對齊已戳記 columns gate;不新放寬、不削弱因果)
- `_assert_metadata_gate`:**移除/放寬 `feature_schema_hash` exact 斷言**(欄集差異已由 columns gate 有界把關)。
- **保留**其他 metadata 不變量:`config_hash`/`config_used`(若有)、symbol、timeframe、**present_timeframes/timeframes.training 含 [1h,4h,12h]**(防退化單 TF);`row_count`/`data_range` 維持「符合截斷後預期」非 ==full。
- 此修在共用 helper,**B2(P0-FF-2)也受惠**(單 TF 通常 schema_hash 相同,行為不變;但移除矛盾斷言對 B2 回歸無害)。確認 B2 c2_1/c2_2 仍過。

## 收尾(別硬撐慢全鏈)
- 改完 py_compile + helper smoke。**全鏈 c3 + B2 回歸 + mutation 留 Claude 4h timeout 驗**。改完即交。
- 更新 `handoffs/20260630-FF-P0FF3-RESULT.md`。完成 STATUS: DONE/BLOCKED。
