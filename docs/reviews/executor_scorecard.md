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

## 2026-06-02 multi-symbol fix 數據點

| 日期 | 任務 | 執行端 | pass@1(真實環境) | scope 紀律 | BLOCKED | 假綠 | 備註 |
|------|------|--------|------|------|------|------|------|
| 06-02 | multi-sym Phase 1 (P1-1~4, batch/registry/store) | codex | ✅ 12+8 passed | ✅ 只動 Phase1 | env 偽陰(無網路/semaphore) | ❌無 | stdin-hang 派工坑→模板加 timeout+/dev/null |
| 06-02 | multi-sym Phase 2 (P2-1~5, 注入seam/C1/品質loader) | codex | ✅ 78 passed + 解耦135 | ✅(揭露1 benchmark caller-sync) | 無 | ❌無 | 注入 seam 守住 Rule 4;h5py 問題修正 |
| 06-02 | **P3-1 同任務 A/B**(get_slowpath_n_jobs 並行感知,隔離 worktree) | **codex** | ✅ 6 passed | ✅ | 無 | ❌無 | 實作正確、精簡 |
| 06-02 | **P3-1 同任務 A/B** | **cursor** | ✅ 7 passed | ✅ | 無 | ❌無 | 實作正確、多1測+docstring,略周全 |

**P3-1 同任務對打結論（唯一真正可比的 head-to-head）**：**實質平手**。兩邊實作等價正確（`max(1,cap//concurrent)`、預設1、保留<12GB gate、防壞輸入）、皆 pass@1、零假綠、皆 monkeypatch gate 測 (16,2)。cursor 略周全（+1測+docstring），codex 略精簡。此單點不足以翻轉預設；**維持 codex 主力**，cursor 經此確認在小型 config 類任務品質追平、可信賴當溢出/routine。樣本仍 <5/類，不下定論。

## 2026-06-02 Phase 3/4 數據點(續)
| 日期 | 任務 | 執行端 | pass@1(真實環境) | scope | BLOCKED | 假綠 | 備註 |
|------|------|--------|------|------|------|------|------|
| 06-02 | multi-sym Phase 3 (P3-1/P3-2 worker預算+flag) | **cursor** | ✅ 25 passed+解耦 | ✅ | 無 | ❌無 | FFACT_PARALLEL_BUDGET off 維持現狀正確;首個真實寫入任務乾淨過 |
| 06-02 | multi-sym Phase 4 (P4-1 golden+P4-2 IC-First清理,ML高風險) | codex | ✅ 36 passed;**golden compare PASS(數值不變)** | ✅(揭露golden fixture) | 無 | ❌無 | C3 (d) 硬 gate 過;_compute_single_ic_first 0 caller(getter 殘 dead code 小 cruft) |

**累積觀察**：codex 3 批(P1/P2/P4)、cursor 2 任務(A/B P3-1、Phase 3)。兩邊真實任務皆 pass@1、零假綠、scope 乾淨。cursor 在 config/worker 類追平 codex。codex 仍處理最高風險(P2 注入、P4 ML)。**維持 codex 主力、cursor 可靠溢出**;cursor 樣本累積中,config/routine 類已具翻轉潛力,待 ~5 樣本再定。
