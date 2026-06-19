# CGSA L3 累積磁碟預檢 (T-C) TODO
> 版本：DRAFT｜基於 SPEC：docs/CGSA_L3_DISK_PRECHECK_SPEC.md｜日期：2026-06-19

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | _precheck_cgsa_cumulative_disk 估算+abort | Phase1 |
| Task | 2.1 | multi_tf_generator persist L3/L4-L6 前呼叫 | Phase2 |
| 不變量 | BYTE | 磁碟足夠時特徵 byte 不變(guard 不污染) | §G/§V |
| 風險 | (b) | CGSA 共用生成路徑 | §RISK |
| flag | FFACT_CGSA_DISK_PRECHECK=0 一鍵停用 | 天然 flag | §R |
- 合計：Task=2、不變量=1、風險=1。

## §0 全域規則
- **解耦**：純 momentum 內,不引 api。
- **不改數值(核心)**：純 guard,磁碟足夠時 pass-through;T-C 前後 `build_l65_golden_baseline.py --check` PASS。
- **fail-fast 不誤擋**：estimate 用實際 layer.shape(非 naive 437K 上界);compact 非 primary 用 source_n_rows;寧保守附分量明細;`FFACT_CGSA_DISK_PRECHECK=0` 可停用。
- **不吞真實錯誤**：只擋「預估不足」,OS 實際寫入錯誤照拋。
- **防假綠**：不放寬既有 CGSA 測試;新斷言「persist 前 abort(非中途)」「訊息含 needed/free GiB+symbol/tf/layer」「足夠→byte 不變」。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B1 | 1.1 | 無 | 小(估算函式) |
| B2 | 2.1 | B1 | 小(接入 persist 前) |
- Gate:B1 後 mock 低 free→raise 含分量;B2 後整合 mock 低 free→L3 前 abort + 足夠→byte 不變。

## Phase 1 — 累積估算函式
### Task 1.1 — _precheck_cgsa_cumulative_disk
- SPEC ref：1.1　目標：估累積 cgsa_work footprint vs free,不足 raise。
- 實作要點:
  1. 新 method(column_group_registry.py,mirror feature_storage.py:2726 模型):入參 即將 persist 的 layer DataFrame(s)/groups + 目標 cgsa_work 路徑 + symbol/tf/layer 標籤。
  2. **(adversarial #1 BLOCKING)** `needed = planned_new_bytes + max_inflight_tmp×2 + reserve_floor`——**不加 registry_occupied(free 已扣除既佔→重複計算會誤擋)**。
  3. `planned_new_bytes`(adv#3):模擬 5000-col chunk(`range(0,n_cols,chunk)`,feature_factory.py:1159-1200)+ `_compute_shard_slices`(column_group_registry.py:772-827),Σ float32 bytes,**用實際 DataFrame.shape**(compact persist 後才標,adv#5);`max_inflight_tmp`=最大 planned shard。
  4. `reserve_floor`(adv#2):env `FFACT_CGSA_DISK_RESERVE_GIB` 預設 2.0,或複用 L7 `_resolve_l7_min_free_bytes()`。
  5. `free=_disk_free_bytes(path)`;`if free is not None and free < needed: raise ColumnGroupRegistryError(含 symbol/tf/layer/need GiB/free GiB/建議)`。
  6. 非 DataFrame/缺 .columns/coerce 失敗(adv#6)→return None 退回 per-shard guard,不 raise。
- 修改檔案:momentum/FeatureEngineering/core/column_group_registry.py。既有 caller:Phase2 接入。
- 不可做:不改特徵值;不吞 OS 寫入錯誤;不用 naive 437K 上界(用實際 shape)。
- 邊界:足夠→pass(None);不足→raise 含分量;空 layer→None;compact 非 primary→實際 n_rows 不高估。
- 驗證:mock shutil.disk_usage 低 free→raise 且訊息含 needed/free GiB+symbol/tf;充足→None;`pytest tests/feature_engineering/ -k cgsa_disk_precheck`。

## Phase 2 — 接入 persist 前
### Task 2.1 — 三條 CGSA persist 路徑 persist 前呼叫 (adv#4)
- SPEC ref：2.1　目標:persist L3(及 L4-L6)前各呼叫預檢,最先擋 L3 事故點。**三路徑都接**:serial multi-TF(multi_tf_generator.py:204-212)、parallel primary(:432-441)、single-TF(feature_factory.py:2949-2966)——建議抽共用 helper 各處呼叫避免漏。
- 實作要點:
  1. 三處各 `_persist_layer_output_groups(layerN,...)` 前呼叫 `_precheck_cgsa_cumulative_disk(layerN, _LS.LN, symbol, tf, ...)`。
  2. env `FFACT_CGSA_DISK_PRECHECK`(預設 "1" 啟用;"0" 停用回舊行為)。
  3. 沿用既有 offloaded_to_registry skip 條件,不重複預檢。
- 修改檔案:momentum/FeatureEngineering/timeframe/multi_tf_generator.py。
- 不可做:不改 persist 數值/順序(只前面加 guard);不改既有 layer skip 邏輯。
- 邊界:env=0→舊行為;layer offloaded→skip;多 TF→每 TF 各檢。
- 驗證:整合——小 layer + mock 低 free→L3 persist 前 abort(非寫中途);正常→跑完 byte 不變;`pytest tests/feature_engineering/ -k cgsa_disk_precheck_integration`。

### Phase 測試 + Gate
- 行為不變:`python scripts/build_l65_golden_baseline.py --check` PASS(磁碟足夠時)。
- 不誤擋:測「剛好夠」案例不誤 abort。

## 階段 4：Frozen 前 handoff
`SPEC=docs/CGSA_L3_DISK_PRECHECK_SPEC.md TODO=docs/CGSA_L3_DISK_PRECHECK_TODO.md FOCUS=不誤擋/byte不變/persist前abort/訊息可行動`
→ 一家 adversarial(Codex,作者非自審)reconcile 後 → Composer 實作 + Codex review。
