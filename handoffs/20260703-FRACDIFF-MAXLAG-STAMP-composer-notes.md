# fracdiff max_lag — Composer stamp review notes

> task-id: `fracdiff-maxlag-stamp-composer-20260703`  
> 對照：`handoffs/20260703-FRACDIFF-MAXLAG-ADV-COMPOSER.md` findings vs 修訂後四份文件 + reconcile 對照表  
> 方法：重讀 SPEC/TODO/MANIFEST/BRIEF 對應段；必要處對照實碼（`_d_star_cache.py`、`ff_truncation_mr_helpers.py`、`build_l65_golden_baseline.py` 行號主張）

## ① BLOCKING 閉合核查（4 項，含 §G 合併項）

| # | 原 finding | 修訂落點 | 閉合判定 |
|---|---|---|---|
| B1 | §G「byte 級」實為抽樣 hash 可假綠 | SPEC §G L32-33 oracle=per-column 全量 value/nan-mask sha256；禁 `build_l65_golden_baseline.py` 抽樣；TODO 0.1 L47-48 新 helper + 禁抽樣 | **CLOSED** — 明確禁止 13-row 抽樣作 PASS |
| B2 | Task 0.1 缺 run contract | SPEC §G L30-31 + TODO 0.1 L45-46：`_fracdiff_mr_config_payload()`、`_fracdiff_window_bars`≥600、BTC+ETH×1h、獨立 cache | **CLOSED** — 實碼確認兩 helper 存在（`ff_truncation_mr_helpers.py:158,207`） |
| B3 | EPIC_BRIEF 10×3 vs SPEC 2×1 | BRIEF §7 L70-74 改 BTC+ETH×1h；10×3 移至 §8 IC 定版；SPEC §N L117 登記 | **CLOSED** |
| B4 | B-3 五探針漏 max_lag/fracdiff_hash | SPEC/TODO 2.3 + MANIFEST B-3：7 項 v3 guard，含 fracdiff_hash 之 max_lag ③與 calibration_bars ④ | **CLOSED** — 實碼確認兩欄位在 hash（`_d_star_cache.py:221,227`） |

§G「G2 byte 等價驗收鏈」與 B1 同源（抽樣 hash），另加 cache 隔離（reconcile #2 / SPEC §G L33）補套套邏輯 — **CLOSED**。

## ② MAJOR 閉合核查（8 項）

| # | 原 finding | 修訂落點 | 閉合判定 |
|---|---|---|---|
| M1 | 「60→50」硬編敘事 | SPEC §G L31/L36、MANIFEST C-1 L46-47、TODO 0.1 L54 | **CLOSED** |
| M2 | receipt 缺 fracdiff_hash | SPEC §G L33、TODO 0.1 L48、3.1 L150 | **CLOSED** |
| M3 | fingerprint 未指名 / 與既有測試重複 | SPEC/TODO 2.3：指名 v3 guard、構造同 path 錯 payload、引用 P1-FF-5 不重複 | **CLOSED** |
| M4 | calibration_bars∈hash 未覆蓋 | TODO 2.3 mutant ④ | **CLOSED** |
| M5 | Task 3.1 hash vs stats 雙軌矛盾 | TODO 3.1 L150、SPEC 3.1 L93：oracle=canonical digest 單軌 | **CLOSED** |
| M6 | §G 與 B-1 脫鉤 | SPEC §G L38 條件 4、TODO 3.1 L153 | **CLOSED** |
| M7 | Task 1.1 短 df 邊界 | SPEC/TODO 1.1 邊界 + §N 短窗截斷 MR 排除 | **CLOSED** |
| M8 | Task 2.2 parallel 無 mutation | SPEC/TODO 2.2 L78/L115、MANIFEST B-2：n_jobs>1 實測 | **CLOSED** |

## ③ Reconcile 對照表忠實度（Claude 腿）

- 本人 4 BLOCKING + 8 MAJOR 皆在表中對應（#1/#7/#8/#5/#9/#10/#11/#12/#6/#13），**無漏項、無誤降級為 REJECT/NB**。
- #1 與 Codex#1 合併合理（同源抽樣 hash）；#5 與 Codex#5 合併合理（B-3 重設計）。
- 未發現「已修」口號與文件脫節：每條 ACCEPT 均可在 SPEC/TODO 找到可執行落點。

## ④ 非阻擋觀察（不影響 APPROVED）

1. **MANIFEST A-4** 仍寫「修後舊 cache 自動 miss」簡述；Codex#3 兩案分立僅在 SPEC/TODO 1.4（Codex 已戳 APPROVED，非本次 BLOCKING）。
2. **TODO 追溯索引 B-3 節錄**（L13）仍為舊「fingerprint」字樣；Task 2.3 正文已為 7 項 mutant — 建議實作前順手更新節錄，非閉合缺口。
3. oracle helper 建議新檔 `ff_maxlag_golden_helpers.py`；既有 `canonical_frame_digest`（`ff_artifact_compare_helpers.py:345`）為整表 digest，修訂要求 per-column dict 更利 diff 報告 — 合理。

## 戳記

```
body-hash: bash scripts/reconcile_body_hash.sh handoffs/20260703-FRACDIFF-MAXLAG-RECONCILE.md
→ a2b09930c3f3c2f2d8bfcaa070c4a3f87340d223bcb967ac457628b1c1fbf9ee（與 Codex 戳記一致）
```
