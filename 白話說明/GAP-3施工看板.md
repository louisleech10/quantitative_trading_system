# GAP-3 事件型 UAT — 施工進度看板

> **這份只回答一件事：42 個 Task，哪些做了、哪些沒做、卡在哪。**
> 由 `docs/GAP3_EVENT_UX_TODO.md`（**FROZEN v1.0**）＋ `docs/GAP3_EVENT_UX_TODO.D-001.md`
> **機械產生，禁手抄**。

## 一眼看完

| | |
|---|---|
| 規格（SPEC） | 🔒 **已凍結** |
| 施工清單（TODO） | 🔒 **已凍結 v1.0**，可據以派工 |
| **實作** | **第一批施工中** |
| Task 總數 | **42** |
| 已完成 | **3** |
| 進行中 | **1** |
| 未開工 | **38** |

🔴 **現在在做**：第一批 —— 契約與深度根基。程式已寫完、三家審過一輪、3 條問題全部修掉，
正要派第二輪確認。

## 批次順序（做的順序；本表不帶狀態，狀態一律看下方逐 Task 表）

| 批 | 含哪些 Task | 依賴 |
|---|---|---|
| **B1 契約與深度根基** | 1.1、1.10、2.1b、4.2（僅 §G S-9 參考實作部分）　🔴 **依 D-001 A-001 更正** | 無 |
| **B2 CSV 匯入主線** | 1.2、1.3、1.4、1.8 | B1 |
| **B3 深度三層防線** | 1.11、1.12、1.9 | B1、B2、**Task 2.1b** |
| **B4 匯入前端** | 1.5、1.6、1.7 | B2 |
| **B5 匯出前篩選** | Phase 2 全部（扣除已於 B1 完成之 2.1b） | B1 |
| **B6 刪除** | Phase 3 全部 | 無 |
| **B7 匯出端報酬欄** | Phase 4 全部（4.2 之 S-9 部分已於 B1 完成） | B1、**Task 2.1b** |
| **B8 訊息與表頭** | Phase 5 全部 | Task 5.0 |
| **B9 IC 止血閘** | Phase 6 全部 | Task 6.0 |
| **B10 全棧接線** | Phase 7 全部 | B1–B9 |

🔴 **第一批是唯一沒有前置的**，其餘全部等它。裡面有兩個「被很多批共用」的工具
（深度計算函式、序列化參考實作），**原本被排在需要它們的批次之後**——第二輪審查抓出來才提前的。

⚠️ **第一批那一列是我在做這份看板時才發現要更正的**：施工清單的批次表寫兩個 Task，
但同一節下方的依賴表寫四個——**兩處互斥**。三輪委員審查加一輪蓋章都沒抓到，
是「把文件做成看板」這個動作抓到的。更正記在 `docs/GAP3_EVENT_UX_TODO.D-001.md`
（凍結後不就地改，走延伸檔）。✅ 該延伸檔**已於 2026-08-24 過三家委員蓋章**（codex／composer／grok
全數同意），開工前置已清。

## 逐 Task 狀態（42 個）

| Task | 在做什麼 | Phase | 狀態 |
|---|---|---|---|
| **Task 1.1** | 契約先行：新增 reason 與 label_definition.filters | Phase 1 | ✅ |
| **Task 1.2** | 新端點 `POST /api/v1/case/import-events/csv` | Phase 1 | ⬜ |
| **Task 1.3** | `event_id` 沿用既有 canonical（D-2） | Phase 1 | ⬜ |
| **Task 1.4** | t0 單位偵測 | Phase 1 | ⬜ |
| **Task 1.5** | 前端上傳、預覽與對映 UI（含強制確認） | Phase 1 | ⬜ |
| **Task 1.6** | 對映 provenance 落檔（D-1） | Phase 1 | ⬜ |
| **Task 1.7** | 可疑欄警示（D-1） | Phase 1 | ⬜ |
| **Task 1.8** | 異質列顯式拒收（A-5′） | Phase 1 | ⬜ |
| **Task 1.10** | 欄位級 `lookahead_bars` 契約（D-7 之 L1） | Phase 1 | ✅ |
| **Task 1.11** | 未知欄強制宣告（D-7 之 L2） | Phase 1 | ⬜ |
| **Task 1.12** | 不可證則禁進切分（D-7 之 L3） | Phase 1 | ⬜ |
| **Task 1.9** | 答案窗宣告與 purge 下界（D-7 之 L2 使用者介面） | Phase 1 | ⬜ |
| **Task 2.1** | `/search` 匯出前篩選面板 | Phase 2 | ⬜ |
| **Task 2.1b** | 由篩選條件自動導出答案窗下界（D-7 第 2 層） | Phase 2 | ✅ |
| **Task 2.2** | 篩選條件寫入 `label_definition.filters` | Phase 2 | ⬜ |
| **Task 2.3** | 即時筆數顯示 | Phase 2 | ⬜ |
| **Task 3.1** | `DELETE /api/v1/case/events/{import_id}` | Phase 3 | ⬜ |
| **Task 3.2** | 前端刪除鈕與二次確認 | Phase 3 | ⬜ |
| **Task 3.3** | 已被引用批次之警語 | Phase 3 | ⬜ |
| **Task 4.1** | 匯出檔之附帶 `future_*` 欄；移除匯出端之答案窗與 `label_value`（D-3′） | Phase 4 | ⬜ |
| **Task 4.1b** | 匯出時揭露每個選項在動什麼 | Phase 4 | ⬜ |
| **Task 4.1c** | 明文標示本批不提供 IC decay | Phase 4 | ⬜ |
| **Task 4.2** | 事件後報酬表顯示完整曲線（拆兩半：序列化規則這半做了，曲線那半排在後面的批次） | Phase 4 | 🔧 |
| **Task 4.3** | 缺欄確認框逐 horizon 列出 | Phase 4 | ⬜ |
| **Task 5.0** | 建立指標詞彙 SoT | Phase 5 | ⬜ |
| **Task 5.1** | `.source.json` 誤傳之訊息追加正解 | Phase 5 | ⬜ |
| **Task 5.2** | 事件型兩表 tooltip（讀 Task 5.0 之 SoT） | Phase 5 | ⬜ |
| **Task 5.3** | 缺答案窗欄之確認框 | Phase 5 | ⬜ |
| **Task 6.0** | IC 錯誤 reason 之登記處（D-6） | Phase 6 | ⬜ |
| **Task 6.1** | analyze 前置特徵數檢查 | Phase 6 | ⬜ |
| **Task 6.2** | 上限值之量測協定（D-5） | Phase 6 | ⬜ |
| **Task 6.3** | 進度回報與前端狀態區分 | Phase 6 | ⬜ |
| **Task 6.4** | 止血閘之存活驗證（D-5） | Phase 6 | ⬜ |
| **Task 7.0** | 前置：擴 `EventExportOptions` 補齊五維度 | Phase 7 | ⬜ |
| **Task 7.0b** | 分析時 `label_value` producer 與其 wiring | Phase 7 | ⬜ |
| **Task 7.1** | 五維度全部接出前端（依賴 7.0） | Phase 7 | ⬜ |
| **Task 7.2** | 機械閘：可操作選項集合＝`selectable(path,dim)` 且選值真的傳到落檔（依賴 7.0／7.1） | Phase 7 | ⬜ |
| **Task 7.3** | 動態揭露本批設定 | Phase 7 | ⬜ |
| **Task 7.4** | 條件 IC decay 之邊界揭露 | Phase 7 | ⬜ |
| **Task 7.5** | 事件後報酬表正／反／全體三組 | Phase 7 | ⬜ |
| **Task 7.6** | IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定 | Phase 7 | ⬜ |
| **Task 7.7** | Feature run `time_range` 與事件期之對證 | Phase 7 | ⬜ |

## 狀態符號與「完成」的判準

⬜ 未開工　🔧 進行中　✅ 已完成　⛔ 卡住（**須寫**：卡在什麼、誰能解）

🔴 **標 ✅ 的條件（不得放寬）**：該 Task「驗證」欄的命令**全部 rc=0**，
**而且**它的 mutation 已經實跑過——**故意改壞會轉紅、還原後轉綠**，receipt 路徑寫進 commit。
**只有測試綠、沒有 mutation receipt ⇒ 仍是 🔧，不是 ✅。**
理由：測試綠只證明「現在沒壞」，mutation 才證明「壞了測得出來」。

## 這份怎麼維護

每做完一個 Task 就改該列並補 receipt；每收一批就更新「一眼看完」的三個數字。
**歷史不寫在這裡**——過程在 [治理進度日誌.md](治理進度日誌.md)、
踩過的坑在 [流程摩擦記錄.md](流程摩擦記錄.md)、
每個 Task 是誰要的在 [GAP-3規格42個Task勾選表.md](GAP-3規格42個Task勾選表.md)。
