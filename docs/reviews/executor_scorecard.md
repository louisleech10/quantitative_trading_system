# 執行端主力記分卡（Q2：codex vs cursor）

> **目的**：用真實任務的**客觀數據**決定誰當預設寫入執行端，不靠感覺、不為測而測。
> **記錄時機**：每次**寫入型派工的驗收當下** append 一列（數據都已在手，near-zero 成本）。
> **現狀**：樣本不足 → **預設 codex 主力、cursor 溢出/routine**；Cursor 已過 T-D 可寫入。

## 偏差防範（否則記分卡會騙人）
1. 只記**客觀指標**（pass@1 / scope / BLOCKED / 時間 / tokens），不記主觀「感覺好」——避 council #9 球員兼裁判偏差。
2. 標**任務類型/大小**，只在**同類**間比（別拿 codex 的難題比 cursor 的 routine）。
3. 路由有選擇偏差 → **偶爾刻意 cross-assign**（routine 丟 codex、難題丟 cursor）取乾淨對照點。
4. **樣本夠才下結論**（每類每執行端 ~5+ 列）；不足則維持預設，不被噪音帶偏。

## 記分表（append-only，一任務一列）

| 日期 | task-id | 大小/類型 | 執行端 | pass@1 | scope乾淨 | BLOCKED輪 | wall-clock | tokens/成本 | 備註 |
|------|---------|----------|--------|--------|-----------|-----------|-----------|------------|------|
| 2026-06-01 | ram-gate-concurrency | 中/高風險(OOM·config) | codex | Y | Y | 0 | ~背景 | n/a(未捕獲) | T1-T6 全綠、golden 自驗、防篡改過；過程自解 2 個 test-env import 失敗（在其 context 內，不回灌） |

## 階段性結論（每 ~10 列或被問時更新）
- **2026-05-31**：尚無真實任務樣本（T-A/B/C 為 codex、T-D 為 cursor，皆驗證性非生產任務，不計入主力判斷）。維持預設：**codex 主力**。
- 觀察（非結論）：cursor 在 T-D 主動遵守新合約（結構化報告 + handoffs）且便宜 10–60×；codex benchmark 上 terminal/長自主較強。待真實數據驗證。
