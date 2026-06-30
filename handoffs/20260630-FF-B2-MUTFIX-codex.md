# B2 mutation 2 修 — Codex 委員定案

## 讀碼依據
- 已讀 `HANDOFF.md`、`CLAUDE.md`、`AGENTS.md`、`handoffs/20260630-FF-B2-MUTFIX-PROMPT.md`、`handoffs/20260630-FF-B2-MUTFIX-CLAUDE.md`。
- 聚焦讀碼：`tests/feature_engineering/test_ff_fullchain_truncation_mr.py`、`scripts/mutation_probe_static.py`、`momentum/FeatureEngineering/operators/lag_processor.py`、FeatureFactory Layer0 slicing。

## 問題1：L4 `shift(-1)` 探針沒紅
- 根因定案：C 是主因。`LagProcessor.compute_all()` 在 `estimated_output_cols <= FFACT_LAYER4_FAST_PATH_MAX_COLS` 時走 fast path，直接呼叫 `selected_df.shift(lag)`，不經 `_apply_lag()`；現有 mutation monkeypatch `_apply_lag` 很可能未打到實際 production 路徑。
- A/B 判定：不是觀測到沒紅的第一根因。若 mutation 真生效，`shift(-1)` 對 c2_1 截斷 MR 主要表現為截斷邊界附近 `full finite / trunc NaN`；both-non-NaN values gate 會跳過，只有高 fill-rate NaN mask gate 才抓得到。這是 c2_1 對此類 bug 的結構性弱點，但目前先被 C 掩蓋。
- 修法定案：採 Claude 提案1，將 L4 mutation 負控改成 c2_2 tail perturbation 邏輯，而不是依賴 c2_1 截斷 NaN mask。
- mutation 注入方式定案：不要再 patch `_apply_lag`。改 patch `LagProcessor.compute_all()` 或等價覆蓋 fast path 的 shift 呼叫，使所有 lag 產出使用 `selected_df.shift(-lag).add_suffix(...)`。這能覆蓋目前 production fast path，避免 registry/快取/legacy path 假綠。
- 不採提案2作為主修：把 c2_1 的 `full finite / trunc NaN` 一律升級 fail 容易誤殺列數依賴、低填充率與合法 warmup/dead-column 邊界；若要加，也只能作為很窄的 diagnostic，不應成為主 oracle。

## 問題2：fracdiff calibration perturb 靜態誤判
- 根因定案：`mutation_probe_static.py` 只把 monkeypatch/setattr/patch 或 AST 中引用 module-level project import 視為 touches_system；`test_mutation_fracdiff_calibration_perturb_fails` 透過 `patch_fetch` 擾動真 kline，再呼叫 `_build_truncation_pair()` 走 `generate_features()`，但函式 AST 沒直接引用 imported `momentum` 符號，因此被誤判。
- 修法定案：不放寬全域靜態啟發。不要把 `generate_features`、`perturb`、`kline` 這類普通 token 加白名單，否則空心/偽 raises 可用同名本地 helper 繞過。
- 推薦改探針：在 fracdiff calibration perturb 探針內加入行為不變的 spy monkeypatch：
  - 保存 `FeaturePreprocessor._calibration_series`
  - monkeypatch 成 wrapper，呼叫原函式並計數
  - `pytest.raises(AssertionError)` 後斷言計數 `> 0`
  這同時滿足靜態 touches_system、證明負控觸達 fracdiff calibration 路徑，且不削弱靜態檢查對空心/偽 raises 的攔截。

## B2-MUTFIX 定案
- 問題1：修 mutation 探針本身，覆蓋 L4 fast path；oracle 使用 c2_2 tail perturbation prefix invariant 的大幅值差，不用 c2_1 NaN mask 當主要捕手。
- 問題2：修 fracdiff mutation probe，顯式、行為不變地觸達 `FeaturePreprocessor._calibration_series`；不改寬 `mutation_probe_static.py`。
- 數值/schema 影響：無。這是測試設計定案，不改 production 數值或輸出 schema。

## 驗證
- `source venv/bin/activate && python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py`：FAIL，唯一 fatal 為 `test_mutation_fracdiff_calibration_perturb_fails` 未碰到待測系統；符合問題2描述。
- 未跑慢全鏈；本次依 prompt 以讀碼推理為主。
