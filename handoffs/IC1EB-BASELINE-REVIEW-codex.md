# IC 1e+1b Golden baseline capture 獨立設計審查（Codex）

**正在做/範圍**：獨立核對 `IC1EB-BASELINE-DESIGN.md`、capture script、SPEC §A/§C/§G、TODO §0/Task 5.1 與實際 service→orchestrator→reporter 路徑；未採用其他委員結論。**本次決策**：BLOCK，須修 capture 並重跑受影響 baseline。
**證據基準**：RECONCILE-STAMP 兩方 APPROVED；HEAD=`ce667ba58e995a513cdc68936d1dd7d285807461`。以下每點均附可證偽驗證。

## D-A～D-H 覆蓋
- **D-A — AGREE（有限）**：9 顆縱向真資料能保存舊 pooled-i.i.d. p 與非顯著性值，足供預設 split 路徑 G-1/G-2；但 script 未斷言各 run 實際 `metadata.scope=test`、effective horizon、非 fallback。驗證：capture 後逐 run assert scope/config hash/horizon/summary rows，任一 fallback 即另列 run，不得仍標同矩陣格。
- **D-B — AGREE**：circular block bootstrap 是測試 oracle、非 production 行為，排除 Golden 合理；驗證：T-1.3 固定 seed、B=2000、block≥h 且 mutation 轉紅 receipt。
- **D-C — CHALLENGE（BLOCKING）**：old p 有完整 report 可取，但 `result` 是 report，top-level 沒有 `passed_features`（`_stage7_report` 僅放 summary/filter_log，orchestrator:2378-2402）；script:182 因而永遠取 `[]`，`passed_set_sha256` 不是舊 selection。驗證：先 assert `"passed_features" in result` 應轉紅；修法可由 `summary feature set - union(filter_log.stage5_thresholds.removed_features.*)` 重建並核對 `output_features`，或正式輸出 passed list。
- **D-D — CHALLENGE**：只靠契約 T-2.3 不足以證明真資料 full-sample 的 stage5 universe/evaluated/base hash/report 接線及 G-1 不漂；「省重放成本」不是排除行為 branch 的正確性理由。驗證：至少加 1 顆相同真資料 `ic_train_test_split=False` representative run，assert scope=full、非顯著性五 hash、selection_scope 三個集合關係。
- **D-E — CHALLENGE**：「無真實事件源」不成立：`_stage3_event_filter` 會以真 kline `raw_data` 作 `filter_base`（orchestrator:1982-1995），可由真資料分位值導出 query 而不造假；目前預設 event disabled 完全不走 low_confidence α 變更面。驗證：加 1 顆真 kline 導出 threshold、樣本落 30–99 的 event run，舊/新 G-1 相等且 G-2 顯示 α/pass/reason；若仍排除，須把「無 Golden 覆蓋」列明並以真路徑 integration（非純契約）補足。
- **D-F — AGREE（有限）**：完整舊 report 保存 iid p，G1 欄集合涵蓋現行 summary 的全部非顯著性欄；UI nullability/tooltip 不適合用數值 Golden 驗，應由 T-4.2。驗證：B5 另 assert 新增 t/p/q 與 canonical metadata schema，前端舊 report null/缺欄相容。
- **D-G — AGREE（有限）**：舊 raw-p baseline 對新 default-ON 是正確 G-2 對照，OFF 是新逃生 branch、由 M-G 真 config 鏈 e2e 守可接受；但 capture 必記錄完整 effective config，不能只寫全域 `mode=longitudinal/config_override=None`。驗證：每 run manifest 存 effective split/feature filter/significance predecessor state，T-4.3 assert canonical 與 threshold_log mirror。
- **D-H — CHALLENGE（BLOCKING，同型 xsec 盲點仍在）**：xsec entry 傳單一 `config_hash`，但 service:129-145 在 `symbols` 分支設 `config_hashes=None`，`load_multi` 遂各 symbol 取 latest；現 registry 的 BTC 12h latest 已非 e53e2290，故標籤「3sym×e53e2290」不真。且 `analyze_cross_sectional` 未呼叫 `_apply_feature_filter`，所以 `max_features=500` 對 xsec 無效；無 `labels_path` 時 service:157-163 只附 `return_1`，未覆蓋 D-H 最危險的 labels_path `return_5`/改名前解析。驗證：改用 `cross_sectional_runs` 三個明確 full hash，capture assert report input count=500 與 selected-name hash；另加真 kline 衍生 `return_5` labels_path run、assert h=5/maxlags≥4/排序 hash不變。

## 五 hash、canonical 化與 G-2
- **AGREE**：index/columns/dtypes/nanmask/values 分離比單一 ndarray hash 強；p/t/q 排除 G-1、xsec 缺欄補 NaN 作語意對齊方向正確；同環境下 exact float64 bytes 適合作「不准數值漂移」gate。
- **CHALLENGE（BLOCKING，排序被 canonical 掩掉）**：`sort_index()` 與固定 `reindex(columns=G1_COLUMNS)` 使 row/column output order 改變仍同 hash，直接漏掉 D-H「ICIR 排序不得變」與 SPEC columns 含順序；實跑反轉兩列 summary，五 hash 比較為 `True`。驗證：同時保存 raw `summary_feature_order_sha256`、raw G1 column-order hash，再保存 feature-sorted canonical value hash；ordering mutation 必轉紅。
- **CHALLENGE（BLOCKING，非法值碰撞）**：`to_numeric(errors="coerce")` 會吞 schema/data corruption；實跑 `"corrupt-A"` vs `"corrupt-B"` 的兩 frame，全部五 hash仍相同。驗證：numeric 欄 `errors="raise"` + finite/NaN 型別 gate；該 mutation 必 raise，不能變成同一 NaN。
- **CHALLENGE**：index/columns 用 newline join，未 length-frame、未拒 duplicate feature，短 hash resolver 亦以 dict 靜默覆蓋 8-char collision；float bytes 未明定 endian/C-order/NaN bit、也未記 Python/numpy/pandas 版本。驗證：canonical JSON array或 length-prefix、unique index assert、prefix exactly-one assert、`<f8` contiguous 並 canonical NaN；跨兩次 clean capture hash相等。
- **CHALLENGE（G-2 完整性）**：manifest 沒有 report-file sha，filter removal reason 可被改而 p/pass hash不變；`p_value_old_sha256` 也不能保護整份 G-2 source。驗證：每份 report 寫完後記 byte sha256/size，B5 讀前先驗完整性；passed set、old p mapping、threshold removal mapping各有 canonical hash。

## max_features、可重放性與程序稽核
- **CHALLENGE**：lexical first-500 在固定 universe 可重放，但同一批名字跨 9 顆重複且已知偏向 microstructure，跨 symbol/config 只增加資料實現、不增加 family 覆蓋；不能把「500 足量」等同代表性。驗證：記完整 selected-name list/hash與 family/data-source 分布；改採按 metadata family 的 deterministic stratified sample，或至少 stable SHA-256(name) 均勻樣本，並以「同輸入兩跑同集合、各主要 family 有 coverage」反證偏差。
- **CHALLENGE（BLOCKING，data_cache）**：SPEC §G:95/TODO §0:10 明定 data_cache 唯讀與 postflight 零變化；script 經 service 會建立 `data_cache/reports/ic_ingest_cache`（service:1260-1279）、覆寫 report/filter log（orchestrator:2729-2739），可能寫 filtered H5（2721-2727）。設計檔 §7 的「可重生衍生物」不能覆蓋凍結紅線。驗證：capture 前後對整個 `data_cache/` tree 做 path/size/mtime/content hash，必零 diff；所有 writer 注入 tmp output root。
- **CHALLENGE（BLOCKING，provenance/原子性/唯讀）**：只記 HEAD 不識別 dirty/untracked capture script；審查時該 script 本身未在 HEAD。`git rev-parse` 未 `check=True`，manifest 不記 script/input/registry/dependency hash；OUT_DIR 非空不拒、逐檔覆寫非 atomic，失敗或重跑會混合 stale artifacts，且文件宣告「唯讀」無完整性 enforcement。現場 `handoffs/ic1eb_baseline/` 已有另一命名的 `manifest.json`/reports/generator，正證明污染風險。驗證：clean-tree allowlist + script sha/input manifest sha/env versions；fresh staging dir→10/10 schema/invariant 全驗→atomic rename；manifest per-file sha；B5 前後 baseline tree hash相同。

**待辦/阻塞/踩坑提醒**：先修 xsec run selector+filter、passed-set 來源、order/strict-numeric hash、data_cache tmp redirect、provenance+atomic publish；補 1 顆 full、1 顆真 event、1 顆 labels_path h=5 xsec（可合併 representative run 時須證明同時命中 branches），再重跑。任何只改 manifest 文案而不讓上述 mutation/前後快照轉紅，仍不合格。
VERDICT: BLOCK(xsec 實際資料集與 max_features 不符、D-H 排序被 hash 掩蔽、passed_set 為空假快照、to_numeric 可碰撞、data_cache 寫入違反凍結紅線、HEAD/發布程序不可稽核；另須補 full/event/labels_path 真路徑覆蓋)
