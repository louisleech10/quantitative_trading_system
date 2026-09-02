# HANDOFF — 當前任務狀態

**更新：2026-09-02 深夜｜狀態：GAP-3 UAT B1–B20 使用者全部驗畢；下一件＝`G3-D2` 灰色項目（順序 (a)→(c)→(b)），新 session 依 `docs/GAP3D2_KICKOFF_HANDOFF.md` 開工**

## 票（唯一權威＝`docs/IC_QUANT_GAP_REGISTRY.md`）
| 票 | 狀態 |
|---|---|
| `G3-D1` | CLOSED（R 重開；實作 `c6dd057a`→`7e0a7a94`→`dd4baa2c`；三輪 review 閉合） |
| `G3-D10`…`D17` | CLOSED（2026-09-02 晚 UAT B13–B20 抓出八票，逐票修＋推；D13／D14／D17 為正確性缺陷，皆 B10 五階段路徑未走到底所致） |
| `G3-D2` | **OPEN・下一件**：使用者裁 (a) `scenario` A／B／two_stage → (c) 三元組其餘值 → (b) `platform_random_bars`。大任務完整管線；開工交接＝`docs/GAP3D2_KICKOFF_HANDOFF.md`（§4 主委初判：(a) 內含 (c) 子集，consult 必答） |
| `KLINE-1` | OPEN：`/data-preparation` 舊 K 線下載區塊已標 deprecated；移除票待開（可穿插） |
| `G3-D3`…`D9` | CLOSED |

## 新 session 開工指令（使用者貼的 prompt 已含；此處備份）
1. 稽核本檔＋`docs/GAP3D2_KICKOFF_HANDOFF.md` vs repo 實況（git status／registry／`eventDimensions.ts` 灰項常數）。
2. 唯讀 consult（三家＋主委各完整版）：§4 四題＋§5 白話閘題；session `20260903-gap3d2-x-consult-r1`。
3. 收斂後白話給使用者裁 → SPEC（延伸檔 vs 新 SPEC 由 consult 判）→ adversarial → 戳記 → TODO → 實作 → review。

## 已知紅／不要誤判
- `tests/api` 既有紅（batch_alias／ichc_event_timestamps／progress_rss_fields×2，見 `G3-R11`）；`test_ic_deep_analysis` 與其他 pytest 並行時 ERROR、單跑綠；`tsc --noEmit` 8 行既有債。
- 具名殘留：`R35-L2-ACK`、`MUT-CSV-MAP`、`G3-R12`（小樣本 IC Mean 顯示 `--`）、`GOV-DOC-STATUS-1`、看板 42→39＋1 機械重產工具、commit-msg claim 閘以整則訊息為單位。
- `uat_samples/*拷貝*`、`_tmp_new_schema.csv` 為本機雜物，未納版控。
