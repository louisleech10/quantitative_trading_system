# CGSA L3 累積磁碟預檢 + 提早 abort (T-C) — SPEC

> 來源：docs/CGSA_DISK_FOOTPRINT_COMMITTEE_BRIEF.md（三方 reconcile，T-C P0）｜日期：2026-06-19｜對應 TODO：docs/CGSA_L3_DISK_PRECHECK_TODO.md

## §RISK 風險分級
- **大小**：中。
- **命中高風險原則**：**(b) 跨模組共用路徑**（CGSA 生成路徑，所有 symbol 經過）。**不命中 (a)/(d)**——純磁碟 guard，**不碰任何特徵值/數值計算**（只決定「繼續或提早 abort」）。
- → §G Golden N/A（不改數值）；以行為不變替代：`python scripts/build_l65_golden_baseline.py --check` PASS（abs≤1e-6）+ mock 低 free → raise abort（可證偽）。

## §A 假設與待使用者確認
- **已驗證事實**（grep/Read 實測，附行號）：
  - 事故：ETH L3 `persist-shard ... free_before=0.18 GiB` 磁碟撐爆（log 21:19:23）。CGSA wide 437K × float32 = ~35.6GB naive 上界；compact-align 預設 ON → 非 primary TF 按 source_n_rows 較少列存（實際 < naive）。
  - **現有單 shard guard 不足**：`column_group_registry.py:1542-1550` 只比「當前 array vs 當前 free」+ `.tmp` 雙份（:1554-1560），無累積預算。
  - **要 mirror 的累積模型**：`feature_storage.py:_precheck_l7_raw_stream_disk_space`(:2726-2791)：estimated_final + reclaimable_npy + largest_part + reserve_floor。
  - **L3 persist 插入點**：`multi_tf_generator.py:204-212`，`_persist_layer_output_groups(layer3,...)` 之前；此時 `layer3` DataFrame 已在記憶體 → **n_rows×n_cols 已知**（精確估，非預測）。
  - 釋放：release_storage 僅 L7 階段呼叫（pre-L7 零釋放）→ L3-L6 累積。
  - `_disk_free_bytes`(`column_group_registry.py:1590`)=shutil.disk_usage().free。
- **待使用者確認**：無。
- **已確認**（2026-06-19）：只做 T-C；T-A/T-B 暫緩。

## §C 約束
- 解耦：純 momentum 內；不引入 api。
- **不可違反**：不改特徵值/不弱化 NaN·inf gate/不改輸出大小；預檢失敗用既有例外型別（ColumnGroupRegistryError / RuntimeError "Layer 3 failed"）路徑，不新建吞錯。
- 本任務注意：**fail-fast 不可誤擋**——estimate 寧可保守附分量明細；compact-align 非 primary 列較少不可高估成 abort；可由 env 一鍵停用（回舊行為）。

## §G Golden / Baseline
- N/A（移 §N）。行為不變驗證：磁碟充足時 T-C 前後**特徵輸出 byte 一致**（`build_l65_golden_baseline.py --check` PASS）——預檢只是 pass-through，不改數值。

## §P Phase 與依賴

### Phase 1 — 累積估算函式（依賴：無）
**Task 1.1 — _precheck_cgsa_cumulative_disk 估算 + abort**
- 目標：給定「即將 persist 的 layer DataFrame(s) + registry 現佔 + 目標路徑」，估累積 cgsa_work footprint vs free，不足則 raise 清楚訊息。
- 檔案：momentum/FeatureEngineering/core/column_group_registry.py（新 method，mirror feature_storage.py:2726 模型）或 feature_factory helper。
- 改法：`needed = registry_occupied_bytes + planned_layer_bytes(rows×cols×4) + max_shard_bytes×2(tmp) + reserve_floor`；`free = _disk_free_bytes(cgsa_work)`；`if free < needed: raise ColumnGroupRegistryError(訊息含 symbol/tf/layer/needed GiB/free GiB/建議:清磁碟·減特徵·FFACT_CGSA_TEMP_DTYPE)`。reserve_floor 沿用 L7 既有常數風格。
- 驗證：mock `shutil.disk_usage` 回低 free → raise 且訊息含 needed/free GiB + symbol/tf；free 充足 → 不 raise（回 None）；`pytest tests/feature_engineering/ -k cgsa_disk_precheck`。
- 邊界：① free 充足→pass；② 不足→abort 清楚訊息；③ 估不到 cols（空 DataFrame）→不 raise（無事可估）；④ compact 非 primary→用實際 n_rows 不高估。
- 不可做：不改特徵值；不吞掉真實 OS 寫入錯誤。

### Phase 2 — 接入 L3(及 L4-L6) persist 前（依賴：Phase 1）
**Task 2.1 — multi_tf_generator persist 前呼叫**
- 目標：persist L3/L4/L5/L6 之前各呼叫預檢，最先擋 L3（事故點）。
- 檔案：multi_tf_generator.py:204-212（persist 各 layer 前）。
- 改法：`_persist_layer_output_groups(layer3,...)` 前先 `_precheck_cgsa_cumulative_disk(layer3, _LS.L3, ...)`；L4/L5/L6 同。env `FFACT_CGSA_DISK_PRECHECK=0` 一鍵停用回舊行為（預設啟用）。
- 驗證：整合測試——構造小 layer + mock 低 free → L3 persist 前即 abort（非寫到一半）；正常 free → 完整跑完且 byte 不變。`pytest tests/feature_engineering/ -k cgsa_disk_precheck_integration`。
- 邊界：① env 停用→舊行為（不預檢）；② layer offloaded_to_registry→沿用既有 skip 條件不重複；③ 多 TF→每 TF 各檢。
- 不可做：不改 persist 數值/順序（只在前面加 guard）。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（估算函式 mock disk_usage 低/高 free）/ 整合（小 layer + mock 低 free → L3 前 abort；正常 → 跑完 byte 不變）/ 行為不變（byte）。
- **防假綠**：不放寬既有 CGSA 測試；新斷言「低 free → 在 persist 前 raise（非中途）」「訊息含 needed/free GiB + symbol/tf/layer」「足夠 free → byte 不變」。
- **行為不變**：磁碟足夠時 `python scripts/build_l65_golden_baseline.py --check` PASS（預檢純 pass-through）。
- **不誤擋**：estimate 用實際 layer.shape（非 naive 437K 上界）；compact 非 primary 用 source_n_rows。測一個「剛好夠」案例不誤 abort。
- **邊界目錄**：free 不足 abort(2.1)/free 充足 pass+byte 不變(2.1)/env 停用回舊(2.1)/空 layer 不 raise(1.1)/compact 非 primary 不高估(1.1)/訊息含分量(1.1)。

## §R 回退
- 單一 commit 可 revert。`FFACT_CGSA_DISK_PRECHECK=0` env 一鍵停用（天然 flag）。
- 誤擋（false abort）回報 → 調 reserve_floor 或停用 env。byte 變=立即 revert（guard 絕不該改數值）。

## §N N/A 登記
- §G Golden：**N/A — 純磁碟 guard,不碰特徵值/數值計算**；改以「磁碟足夠時特徵 byte 不變」(`build_l65_golden_baseline.py --check` PASS, abs≤1e-6) 行為不變驗證替代。
