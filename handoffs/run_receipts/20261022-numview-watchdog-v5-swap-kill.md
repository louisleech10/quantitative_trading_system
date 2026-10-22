# NUMVIEW 卡住偵測：判準 v5 swap 條件誤殺紀錄與 v6 停用依據（2026-10-22）

## 可獨立查證之依據（決定停用 swap 終止條件所依）
- 現行估時收據 `handoffs/run_receipts/20261022-numview-estimate.json`（`criteria_sha256` 綁判準 v6）之 `measurements.C_BTCUSDT_1h`：`status=measured`、`child_wall_seconds≈1050.7`、`swap_growth_max_mb≈3799.1`（正常完成之全特徵生成）。
- 判準 v5（`git show 065c80ab:tests/_golden/numview/preregistered_criteria_v5.json`）之門檻＝0.5 × 實體記憶體；本機 `sysctl -n hw.memsize` ⇒ 8192 MB ⇒ 4096 MB。上列正常跑之增長＝門檻之 93%；v5 `_basis` 自訂之校準規則（任一正常完成格之 `swap_growth_max_mb` ≥ 門檻之半 ⇒ Phase 1 收據前調整）即觸發。
- 可分辨性：正常全特徵生成之增長已觀測至約 3.8 GB（上列），2026-10-22 post-IC 卡住為 swap 總量 9 GB（判準 `scale_note.measured.swap_used_gb`；當時基線未記錄）；8 GB 機上無門檻能以安全邊際同時「不誤殺正常」且「早於 log 靜默偵測卡住」⇒ 停用 swap 終止條件，只記錄增長；卡住偵測依 log 靜默 600 秒（正常最大間隔 324 秒，判準 `cell_rules.watchdog._basis`）與牆鐘上限。

## v5 誤殺事件（補充紀錄）
估時器輸出（`venv/bin/python handoffs/run_receipts/numview_probes/estimate.py --targets C_BTCUSDT_1h`，判準 v5 已提交於 065c80ab；stdout／stderr 逐字，略去 INFO 行）：

```
[estimate] 實測 C_BTCUSDT_1h …
[estimate] C_BTCUSDT_1h: stalled 
[watchdog] C_BTCUSDT_1h: stalled（卡住偵測終止：swap 自啟動增長 4896 MB > 門檻 4096 MB 連續 2 次（見 /var/folders/_c/3xdf41hd3tvgxpx63mrml2c00000gn/T/numview-estimate/measure_C_BTCUSDT_1h.log）；270 秒）— 停止後續目標，不寫收據
estimate_rc=3
```

主委當時之工具輸出轉錄（同一 session）：
- 開跑約 2 分鐘：外部監看報 `swap 自開跑增長 > 3000 MB（4251.25→7748.56）`；子行程 log 末行 `2026-10-22 23:17:12,950 … Layer 3 starting, rss=2415MB`（log 檔 33,583 bytes）；`sysctl -n vm.swapusage` ⇒ `total = 9216.00M used = 8118.06M`。
- 終止後：同一子行程 log `grep -o "Layer [0-9.]* [a-z]*"` 末三行 `Layer 6 completed`、`Layer 6 done`、`Layer 6 done`；`sysctl -n vm.swapusage` ⇒ `total = 10240.00M used = 8787.75M`。

限制：子行程 log 已被下一次（v6）實測覆寫，上列「Layer 3 → Layer 6」無原檔可重查，僅為轉錄；停用之決定不依賴此段，依上節可查證依據。
