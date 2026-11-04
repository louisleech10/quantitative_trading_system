# 2026-11-04 磁碟清理清單（委員諮詢 20261104-CLEANUP-X-CONSULT-R1 收斂後定稿）

依據：`handoffs/reconcile/20261104-cleanup-x-consult-r1/synth.md`；盤點 `runs/cleanup_inventory.txt`（`scripts/runs_inventory.py`）；引用查核 `runs/cleanup_refs.sh`。

## A. 現在可刪（約 13.8 GB）
- 舊版與中途正確性擷取：runs/icperf/correctness-20261101、-20261102、-20261102b、-20261103、-20261104、-20261104b、-20261104c
- pytest 暫存：runs/icperf/task04/pytest_tmp、runs/icperf/task04/pt_v558
- 量測工作目錄：runs/icperf/icperf-volprobe-20261101-011249-_e4o5cya、runs/icperf/icperf-longcell-20261101-151457-j5i5mn0u、runs/icperf/gate-heavy-20261101、runs/icperf/task04/logs
- toggle 量測之工作檔：runs/icperf/task04/toggle_impact/work、runs/icperf/task04/toggle_impact/subsets（保留同目錄之 run_toggle_impact.py 與結果 json，供日後 ⓘ 重測）
- HEAD 對照副本 head_wt4：其唯一未入版控之差異檔已存 handoffs/run_receipts/20261104-cleanup-head_wt4-untracked.diff（對 9c96b4ac 版之 diff，可完整還原）；以 git worktree remove 移除
- 前端建置快取：frontend/.next（下次 npm run dev／build 自動重建）
- 探針與暫存收據：runs/icperf/hac_method/probe_h21、runs/icperf/hac_method/receipt_dryrun.json、receipt_dryrun2.json、receipt_dryrun3.json

## B. 條件成立後再刪
- runs/icperf/correctness-20261104d（821 MB）：現行收據綁定之擷取；**下一次重擷取產生新擷取並重組收據後**才刪（任何 receipt_code_paths 內程式改動都會使其失效，屆時即可刪）。
- runs/icperf/hac_method/head_wt5（1.1 GB，worktree @ fa642d6c）與 runs/icperf/hac_method/probe_h34（99 MB）：㊹ 測試刪改清單小審收斂並推送後。
- handoffs/run_receipts/.ffprod-*（約 435 MB，未入版控之 10-26 執行日誌）：FFPROD 票收案後。

## C. 保留
- runs/icperf/task02（Task 0.2 正式量測尚未做）、.testreg（測試讀取）、data_cache、venv、frontend/node_modules、已進版控之 handoffs/ic1a_cut1_*。

## A 之刪除指令（於專案根目錄執行）
```
git worktree remove --force runs/icperf/task04/head_wt4
rm -rf runs/icperf/correctness-20261101 runs/icperf/correctness-20261102 runs/icperf/correctness-20261102b runs/icperf/correctness-20261103 runs/icperf/correctness-20261104 runs/icperf/correctness-20261104b runs/icperf/correctness-20261104c
rm -rf runs/icperf/task04/pytest_tmp runs/icperf/task04/pt_v558 runs/icperf/task04/logs runs/icperf/task04/toggle_impact/work runs/icperf/task04/toggle_impact/subsets
rm -rf runs/icperf/icperf-volprobe-20261101-011249-_e4o5cya runs/icperf/icperf-longcell-20261101-151457-j5i5mn0u runs/icperf/gate-heavy-20261101
rm -rf runs/icperf/hac_method/probe_h21 runs/icperf/hac_method/receipt_dryrun.json runs/icperf/hac_method/receipt_dryrun2.json runs/icperf/hac_method/receipt_dryrun3.json
rm -rf frontend/.next
```
