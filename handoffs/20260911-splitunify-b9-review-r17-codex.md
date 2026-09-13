## CODEX-R17-P1-01
**斷言**: `Task 9.3` 的 fallback `basename` 對證在 20 列中有 15 列無任何檔名副檔名，故這 15 列的 receipt 無法被現行判準執行性地核對：`C5-01`..`C5-12`、`C5-20`、`C5-22`、`C5-24`。
**碼證**: VERIFY: `awk` 掃 SPEC register 得 `count=15` 且上述 ID；`C5-20` 對應實際 assignments seam。  
CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:555  
MUTATION: 在 Task 9.2a 移除 `split_projection.py:555` 的 `feature_timeframe` 寫入，再跑 TODO:659 的 basename 對證；C5-20 仍無 `split_projection.py` basename 可綁定該破壞。
**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c; momentum/Analysis/event_samples/split_projection.py#99bfddace904。 [MAJOR] 信心度=High；目前 `grep -qF` 對 15 列只能永遠找不到帶副檔名的 basename，合法 receipt 會被卡住，或若以模組名代替則失去 path 身分。一次修訂可關閉：為這 15 個 ID 補實際 repo-relative source basename／line range；預期重掃 `NO_BASENAME=0`。排除 receipt 對證會弱化既有 gate，不採用。
## CODEX-R17-P1-02
**斷言**: `SU-RESID-C5-TARGETS` 的現行觸發句沒有判定人、精確時點、輸入 receipt、獨立重掃產物或比較命令；現有 Task 9.3 條文也沒有專用重掃機械閘，因此「receipt 通過但實際未重掃」可無限期不觸發。
**碼證**: VERIFY: `rg -n 'register-rescan|Task 9\.3|basename' scripts` 只命中一般 basename／既有文字工具，沒有 Task 9.3 receipt 重掃實作；現行觸發字面在 TODO:667-668。  
CODE-ANCHOR: docs/SPLITUNIFY_TODO.md:667  
MUTATION: 構造一份通過 receipt 第 1–4 點且碼證指向既有檔案行的交件，再不做獨立重掃；現行條文沒有任何命令會產生或比較第二份重掃結果，故無法觸發升級。
**來源摘要**: docs/SPLITUNIFY_TODO.md#84de58113d9c。 [MAJOR] 信心度=High；一次修訂可關閉：直接把觸發改成「判定人=Task 9.3 驗收執行者；時點=首個 implementation commit 前；輸入=唯一通過第 1–4 點的 receipt 與同時點獨立重掃檔；命令=`TASK93_RECEIPT="$r" TASK93_RESCAN="$s" bash -c 'test -s "$TASK93_RECEIPT" -a -s "$TASK93_RESCAN" && diff <(sed -n "3,$p" "$TASK93_RECEIPT" | awk "{print \$1,\$2,\$3,\$4}") <(sed -n "3,$p" "$TASK93_RESCAN" | awk "{print \$1,\$2,\$3,\$4}")'`；rc≠0 或任一 fallback basename `grep -qF` 失敗即升級 `TARGETS` 並重簽」。
### 必答
1a=`FIX-FIRST`；1b：若錯選而應 `PROCEED`，首個 receipt 會以 `grep -qF` 在 15 列失敗，重跑上述 awk 應仍見 `count=15`；若本立場不採，至少保留 `SU-RESID-C5-TARGETS` 並把這 15 個 ID 具名化。
2a=適用於「補 20 列 TARGETS 以加一層收據腳手架」；`HANDOFF.md:32` 與 b16bed64 的原始裁定均把同型治理缺陷降為具名殘留，且 TODO:664-668 已明文套用。2b=N/A；機械分界是「補現有契約缺失的實際落點」可修，新增／加嚴驗收工具或以排除替代證據則屬治理擴建／弱化。
3a=15 列：`C5-01`..`C5-12`、`C5-20`、`C5-22`、`C5-24`。3b=補實際檔名與行範圍；不把它們排除於 receipt，因那會降低 fail-closed 覆蓋。
4a=不可執行；現句沒有 owner/time/command/independent rescan，且沒有現成專用命令。4b=採 P1-02 中的 owner、時點、雙 receipt `diff` 命令字面；任一分類差異或 basename check rc≠0 即升級並重簽。
5a=`REJECTED`；body hash 實跑為 `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`，C5-25 seam 實讀為 `ic_feed.py:56-65`、呼叫端 `pipeline.py:406-408`，本身無新增 finding。5b=阻擋項為 `CODEX-R17-P1-01`、`CODEX-R17-P1-02`，各可在一次修訂內關閉。
ASSUMPTIONS_VERIFIED: `git show 0908ffad` 指定 diff；register=29、exact anchors=9、fallback 無 basename=15、mutation IDs=40 且 01–40 連續；C5-25 seam／呼叫端與 brief 相符；HANDOFF ruling scoped search 未找到更早的「SPEC 欄位 vs 治理工具」分界定義。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → d42b3f14… rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r17-codex.md --family codex` → `COMPLETENESS_RC=0`；register awk → 15 IDs；`nl -ba` seam 56–65／406–408 實讀。
FAILURES_SEEN: review skill alias 路徑先誤拼後已改正；gstack analytics 寫入 ~/.gstack 被 sandbox 拒絕，未影響專案交件。
SCOPE_CHANGES: 僅新增本交件與 append SPEC 戳記；未改 production、tests、TODO 或根 HANDOFF.md；未 commit。
NUMERIC_OR_SCHEMA_IMPACT: none；review-only，SPEC body 未改，僅新增 r17 codex REJECTED stamp。
OUTPUT_ARTIFACT: `handoffs/20260911-splitunify-b9-review-r17-codex.md`; TMP_CLEANUP: `/private/tmp` 無本輪可辨識 workdir，`claude-501` 保留；`.BBE…`、root-owned `powerlog`、`sessions` 未動。
VERDICT: blocked
BLOCKED-BY: CODEX-R17-P1-01,CODEX-R17-P1-02
CLOSED:
STATUS: DONE
