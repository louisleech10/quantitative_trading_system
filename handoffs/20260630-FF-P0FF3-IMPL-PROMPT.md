# 派工:實作完整 P0-FF-3(Composer)

讀 `handoffs/20260630-FF-P0FF3-RECONCILE.md`(三方戳記定案)。

## 1. 抽 B2 helper 到共用 module(行為不變)
- 新 `tests/feature_engineering/ff_truncation_mr_helpers.py`:從 `test_ff_fullchain_truncation_mr.py` 抽出 TruncationPair/GenerationArtifacts/gates(columns交集/both-non-NaN值/NaN分層/覆蓋守衛)/批次讀parquet/分層抽樣/`_build_truncation_pair`(**參數化 primary_tf/training_tfs/symbol**)/`_select_required_probe_columns`/`_assert_mutation_layer_coverage`/FIXED_ENV/常數(FLOAT16_RTOL=2e-3 等)。
- B2 檔改 `from ...ff_truncation_mr_helpers import ...`(P0-FF-2 行為不變,須回歸通過)。禁 test-to-test import。

## 2. 新 `tests/feature_engineering/test_ff_multitf_truncation_mr.py`
- config:`PRIMARY_TF="1h"`, `TRAINING_TFS=["1h","4h","12h"]`, open_minus, BTCUSDT;其餘同 B2 base。
- window:`estimate_max_warmup_bars(config,1h,[1h,4h,12h])`(=2051)+ TRUNC_K(10)+POST(20)+ALIGN_MARGIN(12)=2093。`patch_fetch` 只改 primary 1h kline。
- 主 MR `test_c3_multitf_truncation_invariant`:同 B2 收斂 gate(columns/both-non-NaN值rtol2e-3/NaN分層/覆蓋/metadata)。
- **metadata gate 加**:assert run metadata `present_timeframes`/`timeframes.training` 含 [1h,4h,12h](防退化單TF假綠)。
- **覆蓋守衛加對齊層**:required-probe 須含 ≥1 `4h_` + ≥1 `12h_` 非 primary 欄(優先 high-fill close/volume);`_assert_mutation_layer_coverage` 缺 alignment(4h,12h)即 fail。

## 3. 對齊 look-ahead mutation(關鍵)
- `test_mutation_align_lookahead_fails`:monkeypatch `TimeframeAligner.build_asof_index_map` 成 wrapper(`out[valid]=min(原因果idx+1, len(source)-1)`=forward未來偏置)→ `pytest.raises(AssertionError): _assert_truncation_invariants(pair)`。
- **12h 邊界選窗**:full_end 落 12h 收盤邊界、trunc_end=full_end-trunc_k*1h(0<k<12)→ full 多載下一根 12h、trunc 沒 → forward 偏置現形(粗 TF 衍生欄值漂移)。
- **B2 既有 center/winsor/lag mutation 改 multi-TF config 後仍須 FAIL**(防回歸);過 mutation_probe_check。

## 收尾(別硬撐慢全鏈到 timeout)
- 改完 py_compile + `python scripts/mutation_probe_static.py <2檔>` PASS + helper smoke(秒級小合成 frame)。
- **B2 回歸(P0-FF-2 行為不變)+ P0-FF-3 全鏈 + mutation 真紅留 Claude 4h timeout 驗**。改完即交。
- 寫 `handoffs/20260630-FF-P0FF3-RESULT.md`。完成 STATUS: DONE/BLOCKED。
