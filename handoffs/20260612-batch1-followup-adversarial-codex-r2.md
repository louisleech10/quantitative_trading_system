# Batch1 Follow-up SPEC/TODO Adversarial Review Round 2

日期：2026-06-12  
範圍：V2 SPEC/TODO/MANIFEST/DECISION；對照 round1 16 findings  
嚴格度：MAXIMUM；reviewer：Codex（獨立重判）

## Verdict：仍需修補，不可派工

機械 gate 已通過，但核心數值語義、winsor 注入、metadata 格式化與真實資料驗收仍未收斂。以下 BLOCKING 修完後需再 reconcile。

## Round1 16 findings 收斂矩陣

| # | R2 狀態 | V2 原文證據與判定 |
|---|---|---|
| 1 風險分級 | **RESOLVED** | SPEC:7-9 明列「大」、命中 (a)(b)、雙家族 adversarial；DECISION:15 記錄升級。 |
| 2 N6 fallback 互斥 | **RESOLVED** | SPEC:72-78、TODO:81-93 唯一定義：producer 必產鍵；缺鍵 warning + 保留 `1-coverage`。 |
| 3 N6 helper ownership | **PARTIAL** | SPEC:62-70、TODO:61-79 已定 `utils/nan_stats.py`，解掉循環依賴；但其全 NaN 語義寫錯，見新 BLOCKING 1。 |
| 4 N3 config 注入不存在 | **PARTIAL** | SPEC:87-94、TODO:110-122 找到正確 config 與 resolver，卻仍把 constructor/setter 留給實作者二選一，且 0 值規格矛盾，見 BLOCKING 2。 |
| 5 Golden 自我認證/hash 衝突 | **RESOLVED** | SPEC:31-38、43-49；TODO:27-42：獨立 freeze script、production 改動前單獨 commit、唯一 hash、缺檔 FAIL、禁 skip。 |
| 6 77 passed 錯誤 | **RESOLVED** | SPEC:18,119、TODO:25 明訂 HEAD 實測 78，gate 為 exit 0 且 pass >=78。 |
| 7 N6 非真 producer | **PARTIAL** | SPEC:76,116-117、TODO:93 已要求 registry -> stream -> gate；但資料仍是 tmp registry 合成三欄，不是專案鐵律要求的真實 kline，見 BLOCKING 4。 |
| 8 N7 schema/migration | **RESOLVED** | SPEC:97-104、MANIFEST:9 明定 persisted manifest 保持裸 `L{n}`，只在 result.metadata 邊界 canonicalize，無 migration。 |
| 9 N7 同源自證 | **PARTIAL** | SPEC:100-102、TODO:131-138 加硬編 list、保序、舊 fixture；但 `failure_reasons` 無可實作轉換且第二個真實組裝點漏列，見 BLOCKING 3。 |
| 10 N6 無效能 gate | **PARTIAL** | SPEC:80-84、TODO:95-106 補寬 group gate；對照注入點、量測工具與門檻來源未成立，見 BLOCKING 5。 |
| 11 N4 resource/package | **PARTIAL** | SPEC:51-59、TODO:46-57 補 module constant 與缺檔注入；SPEC:19-21 仍承認無部署證據，且無 wheel/container/package-data 驗證。 |
| 12 min_periods 分歧 | **RESOLVED** | SPEC:87-94、TODO:110-122 共用 resolver，252->63、100->25，禁止新增第二 config 欄。 |
| 13 T5 persisted compatibility | **RESOLVED** | SPEC:106-113、TODO:140-151 明訂無 production reader、硬改名、無 alias/migration，並列 4 個測試更新。 |
| 14 無 requirement IDs | **RESOLVED** | MANIFEST:6-15 建立 [B1-1]~[B1-10]；實跑 SPEC/TODO coverage 均 10/10 PASS。 |
| 15 N4 搬移/複製矛盾 | **RESOLVED** | SPEC:56、TODO:48-54 改稱 production-owned canonical copy，test oracle 保留。 |
| 16 grep-in-pytest | **RESOLVED** | SPEC:111、TODO:151 把 grep 移至驗收 shell gate，pytest 測三條 producer contract。 |

總計：11 RESOLVED / 5 PARTIAL / 0 UNRESOLVED。PARTIAL 中有 5 項升成下列實質 BLOCKING。

## V2 新一輪 adversarial findings

### BLOCKING

1. **[High] `nan_stats` 把全 NaN 欄由 abnormal 全數計入改成 0，直接弱化 NaN gate。**  
   V2 證據：SPEC:65,68 與 TODO:67-74 定義 `abnormal = nan_total - leading_nan - trailing_nan_run`，並明寫「無有效值 -> abnormal=0」。現行 `feature_factory.py:2780-2787` 對 `has_valid=False` 使用 `abnormal=total_nan`。因此 V2 所稱「語義完全一致」為假；全 NaN 未被 dead-drop 的路徑會由 partial 變 complete。TODO:79 的三方對拍在改委派後也會讓 `FeatureFactory._abnormal_nan_count` 與新 helper 同源，不能代表 pre-change oracle。  
   必修：明定並實作 all-NaN `abnormal=nan_total`；在 production 改動前凍結獨立 reference outputs，測試至少含 empty、all-NaN、leading-only、trailing-only、mid-hole、跨 chunk 邊界。

2. **[High] winsor config 傳遞仍未選定，且 constructor 規格讓 `window=0` 靜默變 252。**  
   V2 證據：SPEC:89、TODO:116 仍要求實作者在 init 傳值與 per-call setter 間二選一；TODO:114 指定 `self._winsor_window = winsor_window or 252`，但 SPEC:92/TODO:120 又要求 `window<=0` raise。`FeatureFactory` 實際在 `generate_features` 每次呼叫才於 `feature_factory.py:222` resolve config，而 validator 在 `:192` 長期持有；setter 還引入共享 mutable state/並行呼叫風險。  
   必修：SPEC 先選唯一 API。建議讓 `validate_factory_output(..., winsor_window=...)` 或等價顯式 per-call 參數傳遞，`None` 才取 252，所有 `<=0` 明確 raise；列出 standalone `FeatureTaskService` 的相容行為。

3. **[High] metadata 邊界設計對 `failure_reasons` 的資料形狀判讀錯誤，且漏列真正第二個組裝點。**  
   V2 證據：SPEC:99、TODO:128 要輸出 `{lid}:{tf}:{reason}`，但現行 `build_completeness_meta_from_layer_results` 已在 `feature_storage.py:582` 產字串 `L3:<reason>`，不是 `(lid, reason)` 結構；文件沒有定義安全 split/canonicalization。TODO:134 指向 `feature_factory.py:3219`，該行實為 quality-gate call；真正第二個單 TF metadata 組裝點是 `feature_factory.py:3325-3326`。此外 SPEC:100/TODO:131 允許「若否就在 multi_tf 聚合點補轉換」，卻未把該分支列入確定修改 scope。  
   必修：定義結構化 formatter 輸入/輸出與 reason 含冒號時的規則；明列 3070-3071、3325-3326 兩路徑及 worker 路徑的唯一處理位置；加入 failure_reasons 的硬編 expected tests。

4. **[High] N6 驗收仍未符合 Feature Factory 資料正確性的真實 kline 規則。**  
   V2 證據：SPEC:21,76 與 TODO:93 把「真 ColumnGroupRegistry + 合成三欄」稱真實鏈；它只證明 storage API 被呼叫，未證明真實 ingestion/L6.5/dead-drop/sanitize/shard 路徑下的統計。CLAUDE.md 驗證保真度要求此類 finding 不得降級，且 Feature Factory correctness 必用 `data_cache/feature_klines/kline_cache.h5`。  
   必修：增加至少一個真實 kline 路徑測試，覆蓋生成到 stream summary/gate；合成三欄可保留作精確單元測試，但不能取代真實路徑 gate。

5. **[High] perf gate 不可執行且門檻無來源。**  
   V2 證據：SPEC:82、TODO:99-106 要以 flag/monkeypatch 關閉統計，但 production 設計沒有該 injection point，Task 2.3 又聲稱僅改測試檔；新增 production flag 會越 scope。10%/15% 也未附 baseline 實測來源。2000x20000 本體即 40M values（float32 160MB/float64 320MB，另有 mask/parquet），`tracemalloc` 與 wall-clock ratio 在一般 CI 不足以作穩定 RSS/runtime gate。  
   必修：先在 pre-change HEAD 實測並凍結可重現 benchmark 方法；定義不需 production test flag 的 comparator、RSS 量測工具、warmup/repetition/statistic、slow marker/資源需求，再據證據設定門檻。

### MAJOR

6. **[Medium] N4 只把檔案移入 package tree，未證明部署 artifact 會包含它。**  
   SPEC:19-21 已承認 assumed；TODO 只有 source checkout sha/缺檔測試。需補 wheel/container/minimal install 後以 `importlib.resources` 或等價方式讀取的 packaging gate，否則 round1 #11 仍只收斂一半。

7. **[Medium] freeze baseline 的 w100 oracle 是直接呼叫 kernel，不是 pre-change public validator 行為。**  
   TODO:35 明寫 HEAD validator 尚不可配置，腳本直接呼叫 `rolling_winsorize_array`。這可鎖定期望公式，但不能證明新 config 傳遞真的走到 validator；最終測試必另對 public `FeatureValidator` 路徑做 exact hash，且避免與 resolver 同源生成 expected。

## §0/§1 十類與錨點摘要

- 前提挑戰：全 NaN 語義、真實資料保真、perf 門檻、package 可用性仍被當成已解決或可直接實作。
- 矛盾：`winsor_window or 252` vs `window<=0` raise；all-NaN=0 vs「沿用既有語義」。
- 端到端漏項：真 kline N6、standalone validator、failure_reasons、deployment artifact。
- OOM/並行：per-column scalar state方向合理；但 40M-value pytest 與 mutable validator setter 未設計並行邊界。
- Cache：本批 d* 已抽出，未見新 cross-symbol cache 問題。
- API/schema：manifest 邊界決策合理；result.metadata formatter 尚未完成。
- 測試品質：coverage/template 機檢均 PASS；數值 oracle/真路徑/perf comparator 仍可假綠或假紅。
- Agent 可執行性：winsor 二選一、metadata conditional scope、perf 關閉 flag 仍要求實作者臨場決策。

## 結論

**仍需修補，不可派工。** 最低放行條件：修正 BLOCKING 1-5，重新跑 coverage/template，並由另一家族 reconcile 修訂版。N4 packaging 與 w100 public-path oracle 至少要轉成明確 Task/驗收，不可只留說明。

ASSUMPTIONS_VERIFIED: 對照 V2 原文與現行 feature_factory/feature_storage/feature_validator/preprocessor/multi_tf_generator/factories/API caller；確認現行 all-NaN abnormal=total_nan、config per-call resolve、failure_reasons 已扁平化為 `Lx:reason`。
TESTS_RUN: `coverage_check.sh` 對 SPEC/TODO 均 10/10 PASS；`template_check.sh` 對 SPEC/TODO 均 PASS。未跑 production pytest（本任務為 read-only design review）。
FAILURES_SEEN: none from mechanical checks；adversarial 發現 5 BLOCKING、2 MAJOR。
SCOPE_CHANGES: none；僅新增本 review，未修改 docs/、momentum/、data_cache/ 或根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: review 本身 none；V2 若照現稿實作會把 all-NaN abnormal ratio 降為 0，構成 quality-gate 弱化；metadata formatter 亦未定義完整。
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 依執行合約由 Claude 維護；本次寫入指定 append-only handoff。
STATUS: DONE

## Round 3 確認

日期：2026-06-12  
範圍：V3 `BATCH1_FOLLOWUP_SPEC/TODO/MANIFEST`；只複核 round2 B1-B5、M6-M7。

| Finding | 狀態 | V3 原文證據與判定 |
|---|---|---|
| B1 all-NaN 語義/獨立 oracle | **RESOLVED** | SPEC:62-65 明定 `seen_valid=False -> nan_total`、all-NaN==total_nan；SPEC:37、TODO:34 要求 production 改動前凍結 HEAD `_abnormal_nan_count` 的 6 案例（empty/all-NaN/leading/trailing/mid-hole/cross-chunk），改後 exact 對拍，已解除弱化 gate 與同源自證。 |
| B2 winsor 注入未定/0 值矛盾 | **RESOLVED** | SPEC:87-92、TODO:110-121 唯一定案 per-call API，明禁 constructor/setter 與 `or 252`；只有 `None -> 252`，`window<=0 -> ValueError`；factory 傳 resolved config，standalone API caller 不傳參維持 252。 |
| B3 failure_reasons 形狀/漏組裝點 | **RESOLVED** | SPEC:16 確認現況是扁平 `L{n}:<reason>`；SPEC:95-100、TODO:125-136 定義首冒號後插入 tf、含冒號 reason 案例、冪等規則，並把 3070-3071、3325-3326、multi-TF worker :546 三處列為確定 scope；stream/legacy/multi-TF 都有硬編 expected。 |
| B4 缺真實 kline gate | **RESOLVED** | SPEC:80-84、TODO:99-106 新增獨立 Task 2.4：指定 `kline_cache.h5` BTCUSDT/12h 真實 CGSA generate/persist tmp，summary `nan_ratio` 與已寫盤 arrays 重算相等、quality_status 一致；資料缺失/abort 均 FAIL，禁 skip/合成替代。 |
| B5 perf gate 不可執行/無基準 | **RESOLVED** | SPEC:38、74-78 與 TODO:35、90-97 改為 pre-change HEAD 同機凍結 2000x20000 真 stream-write baseline；固定 shard/workers、warmup 1、median-of-3，post 用完全相同參數比較 wall<=1.15x、peak<=1.10x，明禁 production flag，另有 O(1) 結構斷言與 slow marker。 |
| M6 resource packaging 證據 | **RESOLVED** | SPEC:54-59、TODO:46-57 已成明確 Task：先檢查 repo packaging 型態；若有 package 設定則補 package-data + `importlib.resources` 測試，若無則把 source-deploy 判定命令與輸出寫入交接。實查 repo 無 `pyproject.toml/setup.py/setup.cfg/MANIFEST.in`，V3 分支可直接執行。 |
| M7 w100 未走 public validator | **RESOLVED** | SPEC:40、87-90 與 TODO:36、121 明確區分 P0 kernel 凍結 expected 與最終 public-path 驗收；w100 必經 public `FeatureValidator`，hash exact==獨立 baseline，並驗 `resolve_winsor_min_periods(100)==25`。 |

新 BLOCKING：none。未重開已定案的 per-call、metadata persisted contract、門檻等決策。

ASSUMPTIONS_VERIFIED: 對照 round2 B1-B5/M6-M7 原文與 V3 SPEC/TODO/MANIFEST；確認 repo 根及三層內無 Python packaging 或 Docker manifest。
TESTS_RUN: `coverage_check.sh` 對 SPEC/TODO 均 10/10 PASS；`template_check.sh` 對 SPEC/TODO 均 PASS；本輪為文件確認，未跑 production pytest。
FAILURES_SEEN: 初次 deployment 搜尋受 zsh unmatched glob 影響，改以 `find` 驗證；未影響判定。
SCOPE_CHANGES: none；只追加本 handoff，未修改 docs/、momentum/、data_cache/ 或根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none（review only）。
STATUS: PASS — 可派工
