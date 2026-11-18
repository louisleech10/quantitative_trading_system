# TESTREG rewrite 核可：tests/registry/test_timeout_registry.py

- 目標：`tests/registry/test_timeout_registry.py::test_boundary_12_repo_scan_every_hit_registered_and_not_class_a`
- 處置：rewrite（catalog `disposition=rewrite`、`rewrite_targets` 只含上列函式）；收據 `handoffs/run_receipts/testreg-rewrite/test_timeout_registry-rewrite.json`。
- 核可者：主委（TESTSEL 收尾 E 項，2026-11-13 對子代理之裁定訊息）。

## 改寫理由

主委 2026-11-13 裁定原文（逐字）：「boundary_12 裁定：走 TESTREG rewrite 收據程序（不立碑）——此為刻意語意改寫（「全部已登記」→「已登記或列待施工清單且清單只減不增」），mutant 皆為掃描級、成本低。」

背景：全庫掃描之未登記逾時寫法 75 處，皆屬 NOCAP 尚未施工之 Task（docs/NOCAP_SPEC.md §P）——Phase 1 Task 1.1（numview 探針 2 處）、Phase 3 Task 3.1（等 IC 完成之腳本與 golden 凍結腳本 29 處）、Phase 4 Task 4.1（verify_l1_warmup 與其測試 8 處）、Phase 5 Task 5.3／5.4（api、frontend、config 產品碼 35 處）；其中 1 處（icfirstalign 封存探針）依登記檔規則登記 D 類。其餘 74 處 blocked-by 上列 NOCAP Task，於本分支不改（含產品碼與重凍基準，屬 NOCAP 票 SPEC 範圍）。原斷言「全部已登記」在 NOCAP Phase 3–5 完成前恆紅；以 xfail／skip 處置會失去擋新增之保護，故改寫為業界 baseline 棘輪：

- 舊：全庫每處命中皆已登記且非 A 類。
- 新：全庫每處命中已登記且非 A 類，或列於 `scripts/timeout_pending_nocap.json`（每列附 nocap_task 與類別，以綁定比對、不用行號）；清單外之未登記命中照擋；清單列已無對應命中亦紅（修好須移出，只減不增）；清單列 nocap_task 空值即拒。

## mutant（只改 production_roots 下之 scripts/）

| id | 補丁 | 意義 | 舊版 | 新版 |
|---|---|---|---|---|
| m1 | `test_timeout_registry-m1.patch` | scripts/ffprod_measure.py 新增一處未登記逾時呼叫 | failed | failed（新增照擋） |
| m2 | `test_timeout_registry-m2.patch` | timeout_registry.json 刪一筆既有登記（numview _watchdog swap_used_mb） | failed | failed（失去登記即為新增） |
| m3 | `test_timeout_registry-m3.patch` | timeout_pending_nocap.json 加一筆 nocap_task 空值 | failed | failed（load_pending 拒） |

各 session 於 head（a48f76154a297bb78d600348f9501fde8c6324d1）乾淨 worktree 套補丁實跑，ledger 紀錄見收據 session_id／compare_session_id；head＋compare 補丁（無 mutant）之基線 session 73a1514d-cb54-4720-95a1-f87c93a7439c 中改寫後之目標 outcome＝passed。
