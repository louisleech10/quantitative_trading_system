# SPLITUNIFY b9 — codex stamp-r2
task-id: `20260911-SPLITUNIFY-B9-STAMP-R2`
family: `codex`
findings-round: `R2`
brief: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R2-BRIEF.md`
審查範圍：`docs/SPLITUNIFY_TODO.md` Task 9.3 第 5 點與 `b27002f3` diff；禁改碼、SPEC 正文、TODO。

## CODEX-R2-P2-01
**斷言**: current `SU-RESID-C5-TARGETS` 仍寫「那 20 列」；現行 register 是 10 keyed／4 basename／15 `NO-ANCHOR`，故缺精確 `path:line` 實為 19 列，殘留字面會過度指示 TARGETS 範圍。
**碼證**: VERIFY: `awk` register 分類輸出 `keyed=10 basename=4 no_filename=15 total=29`，另算 `rows_without_exact_path_line=19`；CODE-ANCHOR: `docs/SPLITUNIFY_TODO.md:670`; MUTATION: 依「20 列」建立 TARGETS 清單再以 current register 重掃，會得到實際 19 列，且把已在 keyed 組的 `C5-25` 重複納入；RECHECK: 同兩條 awk 命令重跑。
**來源摘要**: `docs/SPLITUNIFY_TODO.md#0c76ece1efac`
修法：將殘留段的 20 改為 19；可行性為單一字面同步。本 P2 不阻擋本輪 body 重簽。

## 必答
1a. `CODEX-R17-P1-01`、`CODEX-R17-P1-02`：均 `CLOSED`。1b. register awk 實跑得到 15 個指定丙類 ID；分組為 `10+4+15=29`；`rg -n -A8 '觸發條件' docs/SPLITUNIFY_TODO.md` 顯示兩條客觀事件、owner 與驗收時機均已落地。
2a. 是，(乙) 應逐列具名以使互斥分組自足；2b. `C5-15`、`C5-16`、`C5-17`、`C5-18`。算式目前可重算，未另列 blocker。
3a. 不會；若 15 列分類全維持現況，第 2 條不觸發是事件條件未成立，不等於殘留不存在。3b. `N/A`。
4a. `APPROVED`。4b. `N/A`；body hash 實跑為 `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R17-P1-01,CODEX-R17-P1-02
ASSUMPTIONS_VERIFIED: body hash、register 29、mutation 40 且 01–40 連續、10/4/15 分組、C5-25 之 `ic_feed.py:56-65` keyed seam、兩條殘留觸發字面均已實跑或讀證。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `d42b3f14…` rc=0；register awk → `keyed=10 basename=4 no_filename=15 total=29`；exact path:line awk → `19`；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-stamp-r2-codex.md --family codex` → `COMPLETENESS PASS` rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=1，工具報 codex task output hash pending、待 Claude `register-output`。
FAILURES_SEEN: stamp check 的唯一失敗為 provenance pending；另一次讀取既有 stamp-r2 檔案的複合 shell 指令被治理 hook 擋下，未改檔。
SCOPE_CHANGES: 僅新增本交件與 append SPEC 戳記；未改碼、TODO、SPEC 正文、根 HANDOFF.md、data_cache/。
NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更；P2 僅為文件計數字面。
OUTPUT_ARTIFACT: `handoffs/20260911-splitunify-b9-stamp-r2-codex.md`
TMP_CLEANUP: `/private/tmp` 僅保留既有 `claude-501` workdir；其他本輪 workdir 無。
STATUS: DONE
