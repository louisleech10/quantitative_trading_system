# P2DEBT-T5-GOLDEN — Grok 獨立簽核

**task-id**: t5-golden-grok | **agent**: Grok | **date**: 2026-07-12  
**scope**: 只讀 + 自跑指定 pytest；**未改碼**  
**input**: `handoffs/P2DEBT-T5-GOLDEN-SIGNOFF-CHAIR.md` + WT diff 4 golden 檔 + RCA + 既有 adv

## VERDICT

GOLDEN DATA-CORRECT: PASS

## 四項獨立驗

### (1) fd932a6e 修 B2 bug（舊 963ba4f2 壞）非引入錯 — PASS

| 證據 | 結果 |
|------|------|
| 磁碟 G-OLD sha | `fd932a6e616dad7d…`（meta claim 一致） |
| HEAD meta 仍記 | `963ba4f2…` + 明文「rolling IC index-join 0 列壞行為」（payload gitignore，舊件不可還原） |
| 現 payload 簽名 | `summary_table` 50/50 有限 `ic_mean`+`icir`；`rolling_ic_series` 50/50 非空（含 window_21/63/126） |
| stage5 | `removed.ic_mean=43`、`removed.icir=7`；7 特徵名與 Composer/Codex RCA **完全一致** |
| RCA 對照 | 舊行為：rolling concat 0 列→summary 全 None→50 進 ic_mean 桶、0 進 icir；現值反其道，屬軸對齊修後可計算 oracle |
| float64 敘事 | RCA 已定 MIXED：index 主因、dtype 次因；現 meta 不把 float64 當獨立重凍事由（誠實） |

抽樣（G-OLD 七 icir 特徵）與 RCA B2-current 同量級（例 Cross max_drawdown ic_mean≈0.05993）；微差符合 post-B2 drift 事由，非 all-None 回歸。

### (2) flag-off 無前瞻、值守恆（票5 未再 freeze）— PASS

| 命題 | 證據 |
|------|------|
| flag-off 語意 | `baseline_meta.request.config_override.ic_train_test_split=false`；`freeze_baseline.py` 寫死 False；golden 測 `split_on=False` |
| 無 OOS 前瞻誤用 | G-OLD `metadata.scope is None`、`selection_scope.split_label=="full"`（全樣本 IC，非 test-scope 洩漏） |
| G-NEW 對照 | `scope=="test"`、`split_label=="test"`、override true — 與 flag-on 契約一致 |
| 票5 值守恆 | `git status` 僅 4 檔：`baseline_meta.json` / `baseline_new_meta.json` / `freeze_baseline.py` / `freeze_baseline_new.py`；**無** baseline_*.json payload 變更；payload mtime 2026-07-11、meta/freeze mtime 2026-07-12 |

### (3) 語意 replay — PASS（自跑）

```text
cmd: source venv/bin/activate && pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py -v --tb=short
result: 10 passed, 4 warnings in 53.25s  (exit 0)
  test_flag_off_deep_equal_baseline PASSED
  test_flag_on_matches_new_golden PASSED
```

service 路徑 + 顯式 flag；deep-equal exempt `generated_at` 與現碼一致。

### (4) provenance 三事由 ↔ diff；reuse guard mutation raise — PASS

**三事由**（`rebaseline_reason` object，兩 meta 同構）對應：

| key | 對 diff / 史實 |
|-----|----------------|
| `b2_rolling_oracle_alignment` | 舊 HEAD 單行 reason 同義保留；payload 簽名證 B2 修後 oracle |
| `explicit_flag_off_override` | freeze + meta.request 寫入 override；關閉隱形參數債（new 側對應 true + event 文「flag-on」） |
| `post_b2_code_drift_oracle` | 承認非僅 flag-off：selection_scope/FDR 全結構（G-OLD 有 full scope）≠ 窄理由洗寬漂移 |

另：`provenance_events` append-only 三筆（07-09 B2 / 07-11 refreeze / 07-12 R2 meta）；`input_manifest` h5/meta sha 與磁碟一致（`fb3332ba…` / `c3aa5921…`）；`canonical_projection` exempt generated_at/task_id；gate_b 限制誠實寫明。

**reuse guard**（`test_ic_1a_freeze_reuse_guard.py`，同上 session）：

| mutation | match | flag_off | flag_on |
|----------|-------|----------|---------|
| h5 value 99.0 | `H5 SHA256` | PASSED raise | PASSED raise |
| selected_features 反序 | `feature order` | PASSED raise | PASSED raise |
| config_hash 污染 | `meta identity/subset` | PASSED raise | PASSED raise |

= 6 mutation raise 全綠；另 gate_b rebuild sha 對齊 2 PASSED。

## 限制（非 FAIL）

- 舊 `963ba4f2` payload 已滅（gitignore），無法本機 byte 重播 all-None；依 RCA 雙家 + HEAD meta 明文 + 現簽名反證。
- G-NEW meta 的 reason key 仍名 `explicit_flag_off_override`（文案偏 old），但 request/event 對 flag-on 正確；不影響數值 oracle。

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: fd932a6e=B2修後有限rolling/icir(7特徵名吻合RCA); 票5未動payload; flag-off=full sample; 三事由對diff; reuse 6 raise
TESTS_RUN: pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py -v --tb=short → 10 passed / 53.25s
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀+測+handoff）
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）
```

GOLDEN DATA-CORRECT: PASS
