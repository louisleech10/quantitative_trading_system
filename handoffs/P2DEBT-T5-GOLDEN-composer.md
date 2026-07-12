# P2DEBT-T5 golden 資料正確性 — Composer 獨立簽核
Task-id: p2debt-t5-golden-composer | Agent: Composer | Date: 2026-07-12
Authority: handoffs/P2DEBT-T5-GOLDEN-SIGNOFF-CHAIR.md（只讀 chair 摘要；本檔為獨立實測，非複述）

## 簽核標的
1a cut1 golden：baseline_meta/new_meta + freeze 腳本 diff（4 檔）；working-tree payload `fd932a6e`（old）/ `35e15ce9`（new）。payload 檔 gitignored，票5 diff 未改 byte。

---

## (1) 新 baseline fd932a6e 是否真修 B2 bug（舊 963ba4f2 壞值）— PASS

**舊值壞（不可保留）**
- HEAD `baseline_meta.json` 仍宣告 `baseline_sha256=963ba4f2…`；payload 已 gitignore 無法 `git show` 還原。
- RCA `handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-composer.md` 獨立 bisect：OLD feature epoch-index vs label RangeIndex → `pd.concat` **0/20352 列** → `rolling_ic` 全空 → `summary_table` **0/50** 非空 `ic_mean`/`icir`（全 None）。屬 index-join 靜默失效，非 golden 意圖。

**新值修對（非引入錯）**
- `shasum -a 256 baseline_old_btc_1h_a384e6d2.json` → `fd932a6e…` == working-tree `baseline_meta.json` 宣告。
- 新 payload 實測：`rolling_ic_series` **50/50** 有窗；`summary_table` **50/50** 非空 `ic_mean`+`icir`；`filter_log.stage5_thresholds.removed_features.icir` **7** 特徵（與 RCA §2.2 七特徵名一致）。此為 B2 修軸後 rolling 可算、threshold 流水線語義恢復，非隨機漂移。
- `n_samples=20352` 未變；無新增未來資料路徑（B2 改 stage2 index 對齊，非 label horizon 前瞻）。

---

## (2) flag-off 無前瞻、值守恆（票5 未再 freeze）— PASS

**flag-off 語意**
- diff 於 `freeze_baseline.py` + `baseline_meta.json` 寫死 `config_override.ic_train_test_split=false`。
- 新 payload：`metadata.scope=None`；`metadata.selection_scope.split_label=full`；`metadata.significance.fdr` 存在（method=fdr_bh）。全樣本 IC，非 test-scope OOS。
- `test_ic_1a_cut1_golden.py:56` 顯式 `split_on=False`；G-NEW 對照 `scope==test` 僅在 flag-on 測試斷言。

**值守恆**
- `git diff tests/golden/ic_phase1_1a_cut1/` 僅 4 檔（兩 meta + 兩 freeze 腳本）；**未觸** gitignored `baseline_old_*.json` / `baseline_new_*.json`。
- 票5 變更 = provenance 閉合 + reuse guard + 顯式 override 記錄；payload byte 與前 session 重凍 `fd932a6e` 一致（meta sha 對磁碟檔）。

---

## (3) 語意 replay 自跑 — PASS

```bash
source venv/bin/activate && pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -v --tb=short
# 2 passed in ~54s (2026-07-12 Composer 實跑)
```

- `test_flag_off_deep_equal_baseline`：service 路徑 + `ic_train_test_split=false` → 與 `fd932a6e` payload deep-equal（僅豁免 `generated_at`）。
- `test_flag_on_matches_new_golden`：`scope==test` + 與 `35e15ce9` new golden 一致。

---

## (4) provenance 三事由誠實對應 diff + reuse guard mutation — PASS

**三事由 vs diff（誠實、分述、已移除錯誤 float64 話術）**

| 事由 key | diff 對應 | 獨立佐證 |
|----------|-----------|----------|
| `b2_rolling_oracle_alignment` | sha `963ba4f2→fd932a6e`；events[0] 2026-07-09 | §(1) rolling 50/50、icir 桶 7 |
| `explicit_flag_off_override` | `request.config_override` + freeze 腳本 L167-170 | §(2) flag-off replay 綠 |
| `post_b2_code_drift_oracle` | events[1] 2026-07-11 refreeze task_id | payload `metadata.selection_scope`+`fdr` 完整結構、`split_label=full` |

- 舊單行 `rebaseline_reason`（含 float64 混述）已替換為結構化三事由；`grep float64 tests/golden/ic_phase1_1a_cut1/` → 0。
- `provenance_events` append-only 三筆（2026-07-09/11/12）；`input_manifest` H5/meta SHA 與磁碟 inputs **match**（`fb3332ba…` / `c3aa5921…`）。

**reuse guard mutation（真 raise）**

```bash
pytest tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py -v --tb=short
# 8 passed (2026-07-12 Composer 實跑)
```

3 mutation × 2 modules（flag_off/flag_on）各 `RuntimeError`：
- H5 值變、meta 不變 → `H5 SHA256`
- `selected_features` 與 H5 順序分歧 → `feature order`
- 內嵌 `config_hash` 變 → `meta identity/subset`
另 Gate B 重建 SHA 一致 2 passed。

---

## Composer 簽核

**GOLDEN DATA-CORRECT: PASS**
