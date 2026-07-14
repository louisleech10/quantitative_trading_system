# IC1C B3 驗收 receipt(2026-07-14,Claude 獨立實跑)

```
npm --prefix frontend run build → exit 0
grep -c per_rebalance NetICChart.tsx → 3
python scripts/ic1c_freeze_baseline.py --baseline new2 → exit 0(features byte 等值;sha 變因=git_head lineage)
bash scripts/check_decoupling.sh → ALL RULES PASS;check_decoupling_phase4.sh → PASSED
```
Code review:codex APPROVED 0 BLOCKING+composer APPROVED 0 BLOCKING;conftest.py 越界(全域 stub Binance ping)兩家裁核可=TODO r7 離線鐵則 Gate enabler,RESULT SCOPE 聲明已依 composer NB-3 更正。
測試意義:B3 零 schema 變更由 G-NEW2 features byte 等值機器證明;UI 註記(per-rebalance/未年化/禁跨 TF 直比)=使用者訪談決策②的最後一哩;docs/API_SPECIFICATION.md Net IC 節與實作契約一致(composer 逐節核)。
