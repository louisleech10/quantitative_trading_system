# CUT2 row_index attach — Composer 獨立資料正確性簽核

> task-id: cut2-rowindex-signoff　|　審查者: Composer　|　日期: 2026-07-07
> 依據: `handoffs/CUT2-ROWINDEX-REVIEW.md` + repo working tree diff + 獨立實跑

## Verdict: PASS

`feature_library._attach_row_index` 在 Feature Factory 資料正確性 scope（生成→計算→merge→split→無洩漏）下，對 V2 load 路徑**只補時間軸 label、不改特徵值/列序**；真實 12h run 上 G-1/G-2 成立，端到端 split 驗證邊界可證偽閉合原 bug。無 BLOCKING 資料正確性反例。

---

## 獨立驗證 receipt

### 回歸測試（13/13 passed, ~91s）

```bash
venv/bin/python -m pytest tests/momentum/test_feature_library_row_index.py \
  tests/momentum/test_feature_library_config_hash.py \
  tests/api/test_ic_analysis_service.py \
  -k "not analyze_real_run_with_config_hash_completes" -v --tb=short
# => 13 passed in 90.62s
```

### Adversarial 腳本（G-1/G-2 / 列序 / E2E / mutation / 邊界）

```bash
venv/bin/python << 'SCRIPT'  # 見本檔附錄 A 完整腳本
# 摘要輸出:
# G-2 byte-equal: PASS (head [1704067200, 1704110400, 1704153600])
# G-1 value conservation (50 cols): PASS
# parquet 448 groups all nrows=1696 == row_index len: PASS
# h5 timestamps == load.index, delta12h=43200, _validate_expected_frequency ok: PASS
# mutation arange-as-DatetimeIndex -> TimestampDiscontinuityError: PASS
# old-run no-op / length guard ValueError: PASS
```

### 第二 run 交叉驗證

```bash
# BTCUSDT/12h/f754aad4cc8fe5ccc1532296d6e279ec
# shape=(1696, 161031), G-2=True, G-1=True
```

### 解耦

```bash
grep -r "from api\." momentum/ | wc -l  # => 0
```

---

## Findings

### ADV-COMPOSER-1 — attach 時間軸 vs 特徵值錯位 [NON-BLOCKING 確認]

**假設（adversarial）**: `df.index = row_index` 只改 label，若 parquet 列序與 sidecar 不一致會靜默錯位→IC split/purge 建立在錯誤時間-值配對上。

**驗證**:
- G-1: `load()[50 cols]` 與 `load_columns_v2` 同欄 `np.array_equal(equal_nan=True)` — 兩個 run（e53e2290、f754aad4）皆 PASS。
- G-2: `load().index` int64 秒與 `load_row_index_v2` **byte-equal**。
- 448 個 parquet group 全部 `num_rows=1696`，與 `row_index`/`df` 等長；attach 不做 reindex/sort，positional 對位依賴 writer 列序不變 — 與已簽核的 `_attach_cgsa_row_index` 同契約。

**結論**: 未找到 attach 引入的錯位反例；值守恆在真實 `data_cache/features/` 上成立。

---

### ADV-COMPOSER-2 — 舊 run no-op / 長度守衛 [NON-BLOCKING 確認]

**驗證**:
- `load_row_index_v2 → None` → index 維持 `RangeIndex`（單元 + 即席腳本）。
- `len(row_index) != len(df)` → `ValueError("row_index length mismatch")`（單元 + 即席腳本）。

**結論**: fail-closed 行為正確；不會靜默貼短/長 sidecar。

---

### ADV-COMPOSER-3 — 中毒 ingest cache 無自動 invalidation [NON-BLOCKING]

**假設（adversarial）**: bug 期間寫入的 `ic_ingest_cache/*.h5`（arange 偽時間軸）在修後仍被 `if not h5_path.exists()` 重用，繞過 attach 修復。

**驗證**:
- 掃描 `data_cache/reports/ic_ingest_cache/`（1 檔）: head=`[1704067200, 1704110400, 1704153600]`，**非** `[0,1,2]` poison。
- 機制確認: `_materialize_features_for_ic` L1266 僅在 `not h5_path.exists()` 時呼叫 `_write_features_h5`；若 canonical 路徑已有 poison 檔，**確實不會自動重寫**（exists gate 設計）。
- 本 workspace 無殘留中毒顆；修後首次 materialize 已寫入真 12h 軸。

**結論**: 對**本環境資料正確性**不構成 BLOCK（現 cache 乾淨、新路徑正確）。對**曾中毒的其他部署**屬運維風險：需手動刪除對應 `{symbol}_{tf}_{hash}.h5` 或另開 cache 版本化 task — **不在本刀 attach 範圍內**，建議 follow-up 登記，不阻本刀 PASS。

---

### ADV-COMPOSER-4 — retarget 追蹤測試 [NON-BLOCKING]

**觀察**: 原 `test_analyze_real_run_with_config_hash_completes`（xfail strict, full analyze → `status==completed`）已移除，改為 `test_analyze_real_run_split_validation_passes_with_real_axis`，斷言 materialize→h5 真時間軸→`_validate_expected_frequency` 不 raise（~9s）。

**對照 SPEC §G-3 / TODO L32**: 字面要求 xfail→xpass + `completed` — **流程偏差**。

**資料正確性角度**:
- 原 bug 失敗點即 `_validate_expected_frequency`（非 full IC 計算）；新測試在真實 e53e2290 run 上直接命中該邊界。
- 三斷言可證偽: 非 arange、h5 delta=43200s、split validator 不 raise；mutation 註解與 row_index 單測互補。
- 未放寬既有 assert 門檻（舊 assert 整段移除，非降 threshold）。

**結論**: 對**本 finding（偽時間軸→split 誤判）**屬忠實閉合；對 **SPEC G-3 字面驗收**未達 — 建議 Claude 更新 SPEC/TODO 對齊 retarget 或另開 full-analyze 慢測 mark，**不阻資料正確 PASS**。

---

### ADV-COMPOSER-5 — 1d `EXPECTED_FREQ_BY_TIMEFRAME` 缺口 deferred [NON-BLOCKING]

**驗證**: `ic_filter_orchestrator.EXPECTED_FREQ_BY_TIMEFRAME` 僅含 1h/4h/12h；無真實 1d 已物化 run 可驗。

**結論**: 本刀 scope 為 V2 load attach（已用 12h 實跑驗證）；1d 盲加違「實測>假設」。1d IC 若未補 map 會在 `_resolve_expected_freq` **fail-closed raise**，非 silent 洩漏 — **同意 deferred**。

---

## 獵漏摘要

| 攻擊向量 | 結果 |
|---------|------|
| attach 重排/改值 | G-1 反例未現 |
| sidecar 與 parquet 列數不一致 | length guard raise |
| 偽時間軸通過 split | mutation → `TimestampDiscontinuityError` |
| 殘留 poison h5 | 本 env 0 poison；機制上 stale 需手動刪 |
| 跨 group concat 列數漂移 | 448 groups 全 1696 |

---

## 附錄 A — adversarial 腳本核心命令

獨立執行於 2026-07-07；完整腳本即 session 內 `venv/bin/python << 'PYEOF' ...`（G-2/G-1/group rows/E2E/cache/mutation/no-op/guard），OVERALL: PASS。

---

**產出檔**: `handoffs/CUT2-ROWINDEX-REVIEW-composer.md`
