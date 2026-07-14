# IC1C B0 驗收 receipt(2026-07-14,Claude 獨立實跑)

Gate B0→B1 命令實跑(非轉述 Grok 聲稱):
```
python scripts/ic1c_freeze_baseline.py --baseline old && python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json && shasum -a 256 -c handoffs/ic1c_baseline/g_old.sha256
→ VALIDATE OK(features=7 min=5;skipped: oc_return=turnover_missing, hl_range=gross_ic_missing;non_skipped_with_net_ic=5;fixture_sha256=601c7e78...;git_head=97022a75)+ g_old.json: OK,exit 0
h1/h2 決定性雙跑 → h1==h2==6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179,exit 0
真 kline 路徑:data_cache/feature_klines/kline_cache.h5 ETHUSDT/12h 1696 根(stdout log 為證)
```
Scope 驗:`git diff --stat momentum/ api/ frontend/` → 空(零既有程式碼變更)。
Code review:codex CODE-REVIEW APPROVED 0 BLOCKING(handoffs/IC1C-B0-CODEREV-codex.md)/composer CODE-REVIEW APPROVED 0 BLOCKING(handoffs/IC1C-B0-CODEREV-composer.md);兩檔已 register-output(audit.log)。
