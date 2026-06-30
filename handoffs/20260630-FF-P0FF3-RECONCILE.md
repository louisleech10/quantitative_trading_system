# P0-FF-3 多 TF 全鏈截斷 MR — 三方 reconcile(設計定案)

三腿(Claude/Codex/Composer)強烈收斂。

## config(三方一致)
`PRIMARY_TF="1h"`, `TRAINING_TFS=["1h","4h","12h"]`, `ALIGNMENT_MODE="open_minus"`, `SYMBOL="BTCUSDT"`。其餘同 B2 `_values_gate_mr_config_payload`(全 atomic、winsor/rank/zscore/gaussian 開、fracdiff/adf 關、cross_sectional False、l7_dead_drop False、FIXED_ENV 含 MULTI_TF_PARALLEL=0)。理由:高頻截斷=截最細 primary 1h;三 TF 覆蓋 4h/12h as-of 對齊衍生欄。12h primary 矩陣列 P1(V-6 已覆 up)。

## 檔案結構(Composer 定案,採)
- 抽 B2 共用到 **新 `tests/feature_engineering/ff_truncation_mr_helpers.py`**:TruncationPair/gates/批次讀/抽樣/`_build_truncation_pair`(參數化 primary_tf/training_tfs/symbol)/mutation 層覆蓋/FIXED_ENV。
- **新 `test_ff_multitf_truncation_mr.py`**:multi-TF config + module-scoped pair + 主 MR + mutations。
- B2 `test_ff_fullchain_truncation_mr.py` 改 `from ff_truncation_mr_helpers import ...`(行為不變,P0-FF-2 回歸)。禁 test-to-test import。

## window(三方一致)
`estimate_max_warmup_bars(config, 1h, [1h,4h,12h])=2051`(同 B2,主導 L3 W233)。`window = 2051 + TRUNC_K(10) + POST_WARMUP(20) + ALIGN_MARGIN(12) = 2093` 1h bars。`patch_fetch` 只改 primary 1h kline;粗 TF 由 MultiTFGenerator 按同 end_date 載入。

## 對齊 look-ahead mutation(收斂,取 Composer +1 wrap)
- monkeypatch **`TimeframeAligner.build_asof_index_map`**(單點覆蓋 CGSA+searchsorted)成 wrapper:`out[valid] = min(原因果 idx + 1, len(source)-1)`(forward 偏置=用下一根粗 bar=未來)。不 patch `align_to_primary` 本體。不複用 V-6 frozen before.json 當 mutation(機制可複用,但需 runtime 動態探針)。
- **12h 邊界選窗(Codex,必要)**:full_end 落 12h 收盤邊界、trunc_end = full_end - trunc_k*1h(0<k<12)→ full 多載下一根 12h source、trunc 沒有 → forward 偏置在 trunc 前綴尾端映到該 future row → 現形。
- **oracle = 值**(Composer 從 V-6 實據:對齊 look-ahead 現形是粗 TF 衍生欄值漂移,如 close_12h_raw@12:00 錯值,非僅 NaN)。用 B2 values gate(both-non-NaN rtol2e-3);粗 TF 欄(`_12h_`/`_4h_`)最早觸發。探針 `pytest.raises(AssertionError)` + `_assert_truncation_invariants`。
- 探針:`test_mutation_align_lookahead_fails`(主)+ 可選 `_with_tail_perturb`(加 c2_2 ±1e6 加強)。**B2 既有 center/winsor/lag mutation 改 multi-TF config 後仍須 FAIL**(防回歸)。

## 抽樣/覆蓋(沿用 B2 + 加對齊層)
- 批次讀 + 分層抽樣(K≈40/組、3k-8k 欄、min 3000 不降);multi-TF 欄 ×2.5-3。
- **覆蓋守衛加對齊層**:required-probe 須含 ≥1 `4h_` + ≥1 `12h_` 非 primary 欄(優先 high-fill close/volume 類避免空轉);`_assert_mutation_layer_coverage` 缺 alignment(4h,12h) 即測試設計錯 fail。
- **metadata gate 加** assert run metadata `present_timeframes`/`timeframes.training` 含 [1h,4h,12h](防退化單 TF 假綠)。

## 範圍
新 2 檔 + B2 小改 import。不改 production。

## 戳記(委員 R2 確認 reconcile 忠實收斂後 append;v2 須 sha256)
（Claude 收斂三腿;待 codex/composer R2 確認設計定案無誤後 append `^RECONCILE-STAMP: <family> APPROVED 2026-06-30 sha256:<hash> task:p0ff3-r2`。append 前 `bash scripts/reconcile_body_hash.sh <本檔>`。）
RECONCILE-STAMP: codex APPROVED 2026-06-30 sha256:5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd task:p0ff3-r2
RECONCILE-STAMP: composer APPROVED 2026-06-30 sha256:5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd task:p0ff3-r2
