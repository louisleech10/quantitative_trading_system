# fracdiff max_lag SPEC/TODO 雙家族 adversarial — Reconcile（Claude 編）

> 日期：2026-07-03 | 兩腿：`20260703-FRACDIFF-MAXLAG-ADV-CODEX.md`（6 BLOCKING + 4 NB）、
> `20260703-FRACDIFF-MAXLAG-ADV-COMPOSER.md`（4 BLOCKING + 多 MAJOR/NB）
> 修訂落點：`docs/FRACDIFF_MAXLAG_{SPEC,TODO,MANIFEST,EPIC_BRIEF}.md`（三機檢 re-PASS）
> 待兩委員 append RECONCILE-STAMP 後才過實作 gate。

## Finding → 處置對照（全數 ACCEPT，無 REJECT）

| # | 提出方 | Finding | 處置（落點） |
|---|---|---|---|
| 1 | Codex#1 + Composer B1 | §G「byte 級」實為抽樣 hash，可假綠 | **ACCEPT**：§G oracle 改 per-column 全量 value/nan-mask sha256 + dtype + index + schema hash；禁 `build_l65_golden_baseline.py` 抽樣工具充當 oracle；stats 降為診斷（SPEC §G、TODO 0.1/3.1） |
| 2 | Codex#2 | G2 與修後跑共用 d\* cache → 條件 1 套套邏輯 | **ACCEPT**：每 run 獨立空 cache 目錄；修後必 fresh 重算；receipt 記 resolved max_lag/fracdiff_hash/hit-miss（SPEC §G、TODO 0.1/3.1） |
| 3 | Codex#3 | 「舊 cache 必 miss」對顯式 pin=50 舊 cache 為假 | **ACCEPT**：Task 1.4 分兩案——舊 auto(60) 必 miss；舊 pin=50 payload+strong_value_fp 全符允許合法命中（SPEC/TODO 1.4） |
| 4 | Codex#4 | 推導是 inline 運算式，無 monkeypatch seam | **ACCEPT**：Task 1.1 新增 `_resolve_fracdiff_max_lag(self) -> int` resolver（production 唯一推導點）；Task 2.2 只 patch 該 seam（SPEC/TODO 1.1/2.2） |
| 5 | Codex#5 + Composer P0-2/MAJOR | B-3「fingerprint」非 v3 guard；且漏 max_lag/calibration_bars∈fracdiff_hash 核心軸；與既有測試重複風險 | **ACCEPT**：mutant 重設計為 7 項 v3 真實 guard（path symbol/TF、fracdiff_hash 之 max_lag 與 calibration_bars 成分、payload row_count/time_range、strong_value_fp）；`data_fingerprint` §N 登記不做；已覆蓋者引用標不重複；加 `mutation_probe_check.sh`（SPEC/TODO 2.3、MANIFEST B-3、§N） |
| 6 | Codex#6 + Composer⑤ | B-2 只證 d\* gate 單場景；parallel 無 mutation 實測 | **ACCEPT**：兩 MR 各一 mutation 檢查 + parallel（n_jobs>1）mutation case 實測（SPEC/TODO 2.2、MANIFEST B-2） |
| 7 | Composer B2 | Task 0.1 缺可重現 run contract | **ACCEPT**：寫死 config=`_fracdiff_mr_config_payload()`、窗長=`_fracdiff_window_bars`≥600、BTC+ETH×1h、輸出 parquet+digest json、穩定性前置連跑兩次（TODO 0.1） |
| 8 | Composer B3 | BRIEF 10×3 vs SPEC 2×1 範圍矛盾 | **ACCEPT**：BRIEF §7 改為 BTC+ETH×1h 全量逐值 + 說明 10×3 發生在 IC 定版重生成（使用者手動）；SPEC §N 登記理由 |
| 9 | Composer MAJOR「60→50 硬編」 | G1 max_lag 依實際窗長非必 60 | **ACCEPT**：C-1/條件 2 改「G1 實際推導 max_lag 記入 receipt」（MANIFEST C-1、SPEC §G） |
| 10 | Composer MAJOR「receipt 缺 fracdiff_hash」 | 無法證 pin 生效/cache 隔離 | **ACCEPT**：receipt 必記 resolved max_lag、DStarCache path、fracdiff_hash、hit/miss（TODO 0.1/3.1） |
| 11 | Composer MAJOR「Task 3.1 hash vs stats 雙軌矛盾」 | 內部表述衝突 | **ACCEPT**：oracle=canonical digest 單軌，任一欄不同即 FAIL；stats 輔助（TODO 3.1） |
| 12 | Composer MAJOR「§G 與 B-1 脫鉤」 | 全量守恆≠截斷不變 | **ACCEPT**：§G 加條件 4=[B-1] slow receipt 必要；明寫「必要非充分」（SPEC §G、TODO 3.1） |
| 13 | Composer④ + Codex NB#3 | 短 df 邊界 oracle 不足 | **ACCEPT**：短 df oracle 明定（resolved==50、row count 不變、無例外、NaN gate 不弱化、d\* 實用 300 bars）；短窗截斷 MR 保證 §N 排除（SPEC/TODO 1.1、§N） |
| 14 | Codex NB#2 | warmup 252 不影響 §G row count 需論證 | **ACCEPT**：Task 1.3 補論證（base_windows 先含 calibration_bars≥500）+ §G 條件 2 加 row-count/index 相等（SPEC 1.3） |
| 15 | Codex NB#1/#4、Composer NB | `_native_tf_helpers` 全路徑、`Field(ge=0)`、`len(clean)<20` 邊界、digest 穩定性命令 | **ACCEPT**：全數落 SPEC/TODO 對應行 |

## 判定
- 兩腿交叉印證主軸一致（抽樣 hash / cache 隔離 / B-3 對錯層），無互斥 finding，無需仲裁。
- 修向本體（max_lag 解耦 len(df)、calibration-derived、G2 對照法）兩腿皆認可，未動。
- 依「Finding 閉合再驗證」：請兩委員各自 re-review 修訂後文件確認自己的 BLOCKING 已真閉合（不憑「已修」信任），並**特別盯 Claude 的腿**（本 reconcile 為 Claude 所編，處置歸類/落點可能有誤）。

## 戳記區（委員 append，勿改上文）
RECONCILE-STAMP: codex APPROVED 2026-07-03 sha256:a2b09930c3f3c2f2d8bfcaa070c4a3f87340d223bcb967ac457628b1c1fbf9ee task:fracdiff-maxlag-stamp-codex-20260703
RECONCILE-STAMP: composer APPROVED 2026-07-03 sha256:a2b09930c3f3c2f2d8bfcaa070c4a3f87340d223bcb967ac457628b1c1fbf9ee task:fracdiff-maxlag-stamp-composer-20260703
