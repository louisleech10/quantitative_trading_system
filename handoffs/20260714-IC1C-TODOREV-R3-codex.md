# IC1C-TODOREV R3 Codex 閉合重驗
Verdict: REJECT；指定 r3 於審查中被共享工作區更新為 DRAFT r4，本判定鎖定 TODO sha256 `1f04f1b5bff6e972d524ddde273f924a3f38fd1f8ba85f3cb81a2f8e0a7dfa11`。
SPEC v1.1 補裁判定: **APPROVE**（負 turnover=SKIPPED/禁 clamp；capacity 僅允許三子鍵的契約自洽）；但 TODO 尚未以可證偽 oracle 完整承接。

## 原 7 個 BLOCKING 逐條重跑
- ADV-CODEX-1 **STILL-OPEN [BLOCKING]**：TODO:54/77/94 已寫禁 clamp，但 §0:8 漏列負值，且 T1/G-NEW 沒有注入 `turnover=-0.2` 的具名測試；現有真 fixture 不會觸發，clamp mutant 仍可過 Gate。
- ADV-CODEX-6 **CLOSED**：TODO:12/54/102/124 明定 non-None 與 enabled 無關，且 analyzer/API/config 三層及 false-branch 皆有 oracle。
- ADV-CODEX-7 **STILL-OPEN [BLOCKING]**：TODO:124 已補 analyze→deep-analysis→GET 輪詢，但 G-NEW 含人為 missing/NaN skipped 注入，API bootstrap 未做同輸入注入，仍要求全 feature dict sha 等值；兩側輸入不同，oracle 不可達。
- ADV-CODEX-8 **CLOSED**：TODO:40 使用真 fixture 的 `oc_return`/`hl_range`；實讀 `FEATURE_NAMES` 7 欄吻合。
- R2-NEW-1 **STILL-OPEN [BLOCKING]**：npm 已改 `--prefix frontend`、B0 有 `shasum -c`；但「連跑兩次 hash 相同」仍只是敘述，命令未保存第一次 hash再比較，與「Gate 命令可直接執行」不符。
- R2-NEW-2 **CLOSED**：TODO:84 明定 `cost_drag_return` 是裸有限 number，並以 10bps×turnover 的 CSV 手算值守衛。
- R2-NEW-3 **CLOSED**：TODO:121 具名 422 error、all-skipped empty、missing-turnover no-data 與非 spinner oracle。

## r4 快照新洞
- R4-CODEX-1 **[BLOCKING] capacity 補裁未被精確守衛**：SPEC:37 限 `{estimated_capacity_usd,capacity_tier,calibration}`；TODO:13/54/92 只驗 strict JSON/加 calibration，沒有 nested key equality、型別/固定 calibration 斷言；多餘子鍵或缺鍵可過 Gate。
- R4-CODEX-2 **[BLOCKING] B2 collect gate 漂移**：TODO:124 宣稱 `--collect-only` 為 B2 Gate 前置，但 §B:31 的實際 B2 Gate 未含該命令。
- RECONCILE 未 append codex stamp；REJECT 不符合加戳條件。body hash 實算命令輸出=`6c2a230df7f952069af7d1779d235f47e3a17bcdcc88e44fda53d2e95d4affe0`，僅供核對、未使用。

ASSUMPTIONS_VERIFIED: fixture 具名欄、deep-analysis 需既有 completed task、POST/GET async 路徑、root 無 package.json、capacity 現碼僅兩子鍵、SPEC v1.1 契約。
TESTS_RUN: `nl/sed/rg` 全讀 SPEC/TODO/reconcile/r2 與 route/service/analyzer/fixture；`shasum -a 256` 鎖 TODO/SPEC；reconcile body-hash pipeline→`6c2a...affe0`。文件審查，未跑產品測試。
FAILURES_SEEN: none（靜態反例重跑）。
SCOPE_CHANGES: 僅新增 `handoffs/20260714-IC1C-TODOREV-R3-codex.md`；未改 TODO/SPEC/RECONCILE/HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none；僅審查。SPEC v1.1 補裁獨立 APPROVE，TODO 傳播仍有 5 BLOCKING。
TODO-REVIEW-R3: REJECT(5 BLOCKING)
