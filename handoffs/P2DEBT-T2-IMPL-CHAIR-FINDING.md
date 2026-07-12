# 票 2 實作主委獨立驗收 finding(BLOCKING)
Task-id: p2debt-t2 | Chair: Claude(Opus 4.8) | Date: 2026-07-11

## 背景:代跑 codex delegated 的 hermetic 全套
Codex 因沙箱 60s 卡死把 `run_ic_persist_hermetic.sh --set all` 等 5 項 DELEGATED 給主委。主委代跑(receipt 20260711T122923Z-p2debt-t2-impl-final)。

## BLOCKING C-1:V1 skip 白名單比對誤判合法 skip → hermetic all 在 V1 中止
### 證據(receipt log 直接證據)
- log L181:`SKIPPED [1] tests/momentum/test_ic_e2e.py:236: Set RUN_IC_E2E_PERF=1 to run`(= perf 測試 `test_performance_800_features`,SPEC §V V1 白名單允許 skip)。
- log L183:`SKIP_WHITELIST_FAIL[V1]=1`。
- script L26-28(assert_skips_allowed V1 分支):`echo "$skip_lines" | rg -v 'test_performance_800_features'` → skip 行是 `file:236:reason` 格式**不含測試函式名** → `rg -v` 命中(印出該行)→ 條件成立 → SKIP_WHITELIST_FAIL=1 → return 1。
- script L2 `set -e` + L124-129 `all` 循序 `run_v1;run_v2;...` → V1 `run_guard` return 1 → script 立即退出非零 → **V2/V5/V6/V7 從未執行**。
- 主委原命令 `... | tail -40` 的 exit 0 是 tail 回傳,非 script;真相=hermetic all 在 V1 失敗停。

### 根因
skip 白名單以「測試函式名」比對,但 pytest `-q -ra` 的 short summary skip 行只有 `file:line: reason`,無 nodeid 函式名 → 白名單永遠比不中自己允許的 skip → 合法 perf skip 被誤判違規。V7 分支同款風險(以檔名+reason 片語比對,較不易中招但須一併查)。

### 影響
- 驗收 gate 邏輯錯:即使 redirect 完全正確,V1 gate 也必假失敗;V2-V7 完全未驗證。
- **非 data_cache 安全問題**:V1 的 `DIGEST_DIFF_EMPTY[V1]=1`(pre==post,內部 digest 未變);主委獨立 11007 檔 aggregate digest 對照(pre f0224e8b...,post 計算中)另附。redirect 核心看似正常,但**驗收未完成**,不得宣告 PASS。

## 修法要求(派 codex)
1. V1(及 V7)skip 白名單改用**穩定可比對的識別**:pytest 加 `-rs`/`--no-header` 仍不含 nodeid;應改以 **file:line**(`test_ic_e2e.py:236`)或 **skip reason 片語**(`RUN_IC_E2E_PERF`)比對,或用 `pytest --co -q` 預先解析 nodeid 映射。修法須自證:合法 perf skip → PASS;非白名單 skip → FAIL(兩極性實跑 receipt)。
2. 修好後**完整重跑 `--set all`**(直接執行,勿 `| tail`;或 `; echo RC=$?`),V1-V7 全綠 + 各 set DIGEST_DIFF_EMPTY=1;經 run_with_receipt 出 receipt。
3. 若沙箱卡死:標 DELEGATED,主委代跑該 set 並回填 receipt。

## 誠實邊界
Codex 原 RESULT 誠實標「V1/V2/final 為 DELEGATED,不作 PASS claim」——**codex 未偽稱通過**,本 finding 是驗收 gate 邏輯 bug 非偽綠。責任=實作 harness 的 skip 比對機制;該設計在 SPEC/TODO 全輪 adversarial 中未被任一方(含主委)以「真跑 pytest 看 skip 行格式」驗證 → 列 SCAR 素材(紙面審查漏掉 pytest 輸出格式假設)。
