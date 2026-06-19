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
  - **(adversarial #1) `free` 已扣除 registry 既佔檔案** → needed **不可**再加 registry_occupied（會重複計算→誤擋）。needed=增量(planned_new+tmp+reserve)。
  - **(adversarial #3) persist 分塊**：`_persist_layer_output_groups` 切 5000-col group（feature_factory.py:1159-1200），registry 再 shard（`_compute_shard_slices` :772-827）→ planned 須模擬 chunk+shard，tmp=最大 planned shard。
  - **(adversarial #4) 三條 persist 路徑**：serial multi-TF(:204-212)、parallel primary(:432-441)、single-TF(feature_factory.py:2949-2966) 都要接。
  - **(adversarial #5) compact 在 persist 後標記**：persist 前 DataFrame 是 source rows → planned 用實際 DataFrame.shape；registry 佔用量若需用 `ColumnGroup.total_shard_bytes`(physical,compact-safe)。
- **待使用者確認**：無。
- **已確認**（2026-06-19）：只做 T-C；T-A/T-B 暫緩。
- **Codex adversarial reconcile**(handoffs/20260619-tc-adv-codex.md)：#1 BLOCKING needed 公式去重(增量制) + #2 reserve env 定義 + #3 chunk/shard planned 模型 + #4 三路徑 + #5 compact 時序 + #6 非 DataFrame fallback。全納入。

## §C 約束
- 解耦：純 momentum 內；不引入 api。
- **不可違反**：不改特徵值/不弱化 NaN·inf gate/不改輸出大小；預檢失敗用既有例外型別（ColumnGroupRegistryError / RuntimeError "Layer 3 failed"）路徑，不新建吞錯。
- 本任務注意：**fail-fast 不可誤擋**——estimate 寧可保守附分量明細；compact-align 非 primary 列較少不可高估成 abort；可由 env 一鍵停用（回舊行為）。

## §G Golden / Baseline
- N/A（移 §N）。行為不變驗證：磁碟充足時 T-C 前後**特徵輸出 byte 一致**（`build_l65_golden_baseline.py --check` PASS）——預檢只是 pass-through，不改數值。

## §P Phase 與依賴

### Phase 1 — 累積估算函式（依賴：無）
**Task 1.1 — _precheck_cgsa_cumulative_disk 估算 + abort**
- 目標：估「**這次 persist 即將新增**的 cgsa_work 增量 bytes」vs free，不足則 raise 清楚訊息。
- 檔案：momentum/FeatureEngineering/core/column_group_registry.py（新 method，mirror feature_storage.py:2726 模型）。
- 改法（adversarial #1 BLOCKING 修正）：**`free` 已扣掉 registry 既佔檔案 → 不可再加 registry_occupied（會重複計算→誤擋）**。
  `needed = planned_new_bytes + max_inflight_tmp_bytes + reserve_floor`；
  - `planned_new_bytes`（adversarial #3）：模擬 `_persist_layer_output_groups` 的 5000-col chunk（`range(0,n_cols,chunk_cols)`，feature_factory.py:1159-1200）+ registry shard 切分（`_compute_shard_slices`，column_group_registry.py:772-827），Σ 最終 planned float32 bytes，**用實際 DataFrame.shape**（compact 在 persist 後才標記，adversarial #5）。
  - `max_inflight_tmp_bytes` = 最大「planned shard/file」（非最大既有 group）× 2（.tmp 雙份）。
  - `reserve_floor`（adversarial #2）：env `FFACT_CGSA_DISK_RESERVE_GIB`（預設 2.0），或直接複用 L7 `_resolve_l7_min_free_bytes()`（若相依可接受）。
  `free = _disk_free_bytes(cgsa_work)`；`if free is not None and free < needed: raise ColumnGroupRegistryError(含 symbol/tf/layer/needed GiB/free GiB/建議:清磁碟·減特徵·FFACT_CGSA_TEMP_DTYPE)`。
- 驗證：mock `shutil.disk_usage` 低 free → raise 含 needed/free GiB + symbol/tf；充足 → None；**長 run 既有 registry 大量佔用但增量小 → 不誤擋**（adversarial #1 回歸）；`pytest tests/feature_engineering/ -k cgsa_disk_precheck`。
- 邊界：① 充足→None；② 不足→abort；③ 非 DataFrame/缺 .columns/coerce 失敗（adversarial #6）→return None 退回既有 per-shard guard，**不 raise 除非 free 確定不足**；④ compact 非 primary→用 DataFrame 實際 shape（不高估）；⑤ 既有 registry 佔用→**不計入 needed**（free 已扣）。
- 不可做：不改特徵值；不吞 OS 寫入錯誤；不加 registry_occupied 進 needed。

### Phase 2 — 接入各 CGSA persist 前（依賴：Phase 1）
**Task 2.1 — 三個 persist 路徑 persist 前呼叫（adversarial #4）**
- 目標：persist L3/L4/L5/L6 之前各呼叫預檢，最先擋 L3（事故點）；**涵蓋三條路徑**：serial multi-TF（multi_tf_generator.py:204-212）、parallel primary（:432-441）、single-TF CGSA（feature_factory.py:2949-2966）。
- 檔案：multi_tf_generator.py（:204-212 serial、:432-441 parallel）+ feature_factory.py（:2949-2966 single-TF）。三處 persist L3/L4-L6 前都呼叫（建議抽共用 helper 各處呼叫，避免漏路徑）。
- 改法：各 `_persist_layer_output_groups(layerN,...)` 前先 `_precheck_cgsa_cumulative_disk(layerN, _LS.LN, symbol, tf, cgsa_work_path)`。env `FFACT_CGSA_DISK_PRECHECK=0` 一鍵停用回舊行為（預設啟用）。
- 驗證：整合——小 layer + mock 低 free → L3 persist **前**即 abort（非寫到一半）；正常 free → 完整跑完 byte 不變；**三路徑各一測**（serial/parallel/single-TF）；`pytest tests/feature_engineering/ -k cgsa_disk_precheck_integration`。
- 邊界：① env 停用→舊行為；② layer offloaded_to_registry→沿用既有 skip 不重複；③ 多 TF→每 TF 各檢；④ parallel/single-TF 路徑同樣擋。
- 不可做：不改 persist 數值/順序（只前面加 guard）。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（估算 mock disk_usage 低/高/邊界）/ 整合（三 persist 路徑：小 layer + mock 低 free → persist 前 abort；正常 → byte 不變）/ 行為不變（byte）。
- **防假綠**：不放寬既有 CGSA 測試；新斷言「低 free → persist 前 raise（非中途）」「訊息含 needed/free GiB + symbol/tf/layer」「足夠 → byte 不變」。
- **行為不變**：磁碟足夠時 `python scripts/build_l65_golden_baseline.py --check` PASS（純 pass-through，abs≤1e-6）。
- **不誤擋（adversarial #1 核心回歸）**：① `needed` **不含** registry 既佔（free 已扣）→ 構造「registry 已大量佔用 + 本次增量小 + free 足夠增量」→ **不 abort**；② estimate 用實際 DataFrame.shape（非 naive 437K）；③ 測「剛好夠」不誤 abort。
- **reserve env**：`FFACT_CGSA_DISK_RESERVE_GIB` 預設 2.0 可調；測預設值。
- **邊界目錄**：free 不足 abort/free 充足 byte 不變/env 停用回舊/registry 大佔+小增量不誤擋(adv#1)/非 DataFrame 退回 per-shard guard(adv#6)/三路徑各擋/訊息含分量。

## §R 回退
- 單一 commit 可 revert。`FFACT_CGSA_DISK_PRECHECK=0` env 一鍵停用（天然 flag）。
- 誤擋（false abort）回報 → 調 reserve_floor 或停用 env。byte 變=立即 revert（guard 絕不該改數值）。

## §N N/A 登記
- §G Golden：**N/A — 純磁碟 guard,不碰特徵值/數值計算**；改以「磁碟足夠時特徵 byte 不變」(`build_l65_golden_baseline.py --check` PASS, abs≤1e-6) 行為不變驗證替代。
