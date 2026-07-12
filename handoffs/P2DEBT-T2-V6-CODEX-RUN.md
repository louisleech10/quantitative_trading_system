# P2DEBT T2 V6 Codex 對照代跑

- Task-id: `p2debt-t2-v6-codex`
- Date: 2026-07-11
- Command: `bash scripts/run_ic_persist_hermetic.sh --set V6 > /tmp/t2-v6-codex.log 2>&1; echo V6_RC=$? >> /tmp/t2-v6-codex.log`
- Pytest summary 原文: `=================== 3 failed, 9 passed, 20 errors in 18.25s ====================`
- Digest 原文: `DIGEST_DIFF_EMPTY[V6]=1`
- Return code 原文: `V6_RC=1`
- 判定: **FAIL（非 sandbox 假紅的反證）**；Codex 對照亦重現 3 failed + 20 errors，且 digest 無差異。
- 判定補充: log 顯示 fixture task timeout/task failed，並記錄 `InvalidInputError: label horizon cannot be resolved from column: label`；matplotlib 不可寫警告亦有出現。
- 執行狀態: receipt 最終完整產生；外部等待曾跨過 60 秒門檻，因此依派工規則標記 **DELEGATED**，但上述原文均來自本次完整 log，未臆造。
- 待辦: 主委可直接使用 `/tmp/t2-v6-codex.log` 與本 receipt 對照 grok sandbox 結果。
- 阻塞: none（結果為測試失敗，不是 receipt 缺失）。
- 數值/schema/data_cache: 未改程式或 schema；`DIGEST_DIFF_EMPTY[V6]=1`。
