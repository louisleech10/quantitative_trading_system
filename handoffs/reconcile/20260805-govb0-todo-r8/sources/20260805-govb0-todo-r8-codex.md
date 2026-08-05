# GOVB0 TODO R8 confirmation report | family: codex | task-id: GOVB0-TODO-R8

brief-kind: review | scope: 唯讀審查 `docs/GOVB0_FRICTION_TODO.md`；禁改碼／禁改 TODO／禁改 SPEC／不 commit。

## Verdict

需修補後再審；4 findings，BLOCKING=1。原 9 條修補中 6 條 CLOSED、3 條 NOT-CLOSED（其中 2 條為修補後新缺口）。

## §0 前提宣告

fact-verified：R7 synth 的 codex/composer/grok 三家 `RECONCILE-STAMP` 均 APPROVED；`bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0；SPEC/TODO Task=11/11、FACT-RECEIPT=10。

assumed→refuted：`TEST-3.3-B24-PARTIAL` 可由目前 B-24 bounded section 通過；`awk` 實跑 `B24_PARTIAL_COUNT=0 B24_GREEN_COUNT=0`、rc=1。assumed→unverified：真正 implementation/runtime 路徑尚未存在，本輪只審可執行契約。

## 逐項核對表

| 原修補 | 判定 | 實跑證據／落點 |
|---|---|---|
| codex P0-02 | CLOSED | `grep -n '_bc_kv' scripts/cx_run.sh` 命中 39/44/45/46/47；`_bk` 是既有輸出，`_prepare_and_run:501` 呼叫 `_run_cli_and_emit:513`。 |
| codex P0-03 | NOT-CLOSED | B0→B3 硬 Gate 與 B3 dependency 已有；但 Task 2.5 `修改檔案` 仍列 snapshot，與「只消費」矛盾，見 CODEX-R8-P1-02。 |
| codex P1-04 | NOT-CLOSED | manifest、B14 bounded、B24/H2 新測試均已加入；B24 predicate 實跑失敗，見 CODEX-R8-P0-01。 |
| codex P1-01 | CLOSED | TODO §0.2 lines 39–45 已含 OPEN-2/D-8、B-33 與 ASCII anchor 指引。 |
| codex P1-05 | CLOSED | 同上；新增 manifest path/schema/status 純函式契約在 Task 3.1 lines 467–489。 |
| composer P1-01 | CLOSED | `rg -n 'OPEN-2|D-8' docs/GOVB0_FRICTION_TODO.md` 命中 §0.2。 |
| composer P1-02 | CLOSED | `TEST-3.2-E9-ORDER` lines 578–583 含 wait→publish、恰一筆與兩個反向 mutation。 |
| composer P1-03 | CLOSED | B-14 bounded extraction 實跑命中「未定稿」；`awk` B14 section count≥1。 |
| composer P2-01 | NOT-CLOSED | `TEST-2.5-MUT` 雖列三 mutation，但 corpus hash 只有「當前 corpus ↔ 當次報表 header」，無固定 baseline，見 CODEX-R8-P1-03。 |

### 全量 SPEC 具名 ID 對照

SPEC grep 清單：D-1,D-2,D-3,D-4,D-5,D-6,D-8,D-11,D-12,D-13；E-2,E-3,E-7,E-8,E-9,E-10；F-1,F-3,F-6,F-7；OPEN-1/2/3；E-SCOPE；B-13/14/15/17/23/24/29/30/31/32/33/34/35/36/37。Task、E-SCOPE、H-1/H-2、B-24、E-10 有 TODO 落點；`F-7/B-36` 在 SPEC:587–593 有具名殘留但 TODO `rg` rc=1，見 CODEX-R8-P1-04。

## CODEX-R8-P0-01

**斷言**: `TEST-3.3-B24-PARTIAL` 指定 B-24 bounded section 必須含「部分完成」，但 canonical `^## B-24 ` 至下一 `^## B-` 區間目前沒有該字串，因此驗收必然 FAIL。

**碼證**: `awk` bounded predicate → `B24_PARTIAL_COUNT=0`、`B24_GREEN_COUNT=0`、rc=1；`grep -n '部分完成\|全綠' handoffs/20260801-GOV-AMEND-BACKLOG.md` 顯示 B-24 狀態文字只在 line 1522、位於 bounded section 外；TODO:646–647 要求該 predicate。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f；handoffs/20260801-GOV-AMEND-BACKLOG.md#e864a30429d5

[BLOCKING] 信心度=High；任何 implementation 都不能使既有 bounded predicate 通過而不改 backlog/TODO。修法：在 `## B-24` 至下一 `## B-` 內加入明確「部分完成」狀態行，並保證同區間無「全綠」；保留 `TEST-3.3-B24-PARTIAL` 不降門檻。

## CODEX-R8-P1-02

**斷言**: B0 已成為 snapshot producer，但 Task 2.5 的「修改檔案」仍把同一 snapshot 列為 Task 2.5 新增輸出，和其「只消費」及 B0→B3 hard Gate 互相矛盾。

**碼證**: TODO:79–92 將 snapshot producer 放在 B0 且 B3 依賴 B0；TODO:410–416 明說 Task 2.5 只消費，但 `修改檔案` 仍列 `gate_check_pre_phase2.sh.snapshot`。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High；實作者可在 B5 重產 snapshot，讓差集 oracle 含 Phase 2 改動。修法：Task 2.5 `修改檔案` 移除 snapshot（及其 sidecar），改列為唯讀輸入；B0 明確列出兩個 producer path 與 sha ownership。

## CODEX-R8-P1-03

**斷言**: `TEST-2.5-MUT` 的 corpus immutability mutation 不具可證偽性：只要求報表 header hash 等於當前 corpus，改 corpus 後重跑仍可重新計算並相等。

**碼證**: TODO:407–414 只規定 sha 寫入報表 header、未定固定 expected sha／sidecar；TODO:431 與 433–436 卻聲稱改 corpus 應使 `TEST-2.5-CORPUS-SHA` 轉紅。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High；測試可能假綠，無法證明「同一次驗收不得修改語料」。修法：B0 或 immutable fixture 同時提交 corpus `.sha256` SoT，報表與測試比對該固定值；mutation 改 corpus 後必須 rc≠0，再另行更新 fixture commit。

## CODEX-R8-P1-04

**斷言**: TODO §T 宣稱 SPEC ID 100% 覆蓋，但 SPEC 的具名殘留 `F-7`／`B-36` 沒有任何 TODO 落點。

**碼證**: `rg -n 'F-7|B-36|D-4|F-3' docs/GOVB0_FRICTION_SPEC.md` 命中 SPEC:587–593；同命令對 TODO rc=1；TODO §T:663–678 只列 11 Task、E-SCOPE、H-1/H-2、B-24、E-10。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#15ce4f6e6a11；docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High；下游以 §T 為完整追溯索引會漏掉「B-36 併入 B-13」的錯位殘留。修法：TODO §0/§T 增列 `F-7/B-36` 的已知 residual 與明確 OUT-OF-SCOPE/後續票落點，或把 §T 標題改成「本批 in-scope Task coverage」並列出排除清單；另同步處理 SPEC:5 的 R4 與 TODO:4 的 R7 provenance 漂移。

## 出場判準核算

findings=4 ≤ 5，但 BLOCKING=1 ≠ 0；出場判準不通過，TODO 不得標 Internal Frozen，需修補後重審。OUT-OF-SCOPE：E-SCOPE 四項、R7 H-1/H-2 設計裁決、防蓄意繞過、措辭可讀性、委員債務 OPEN 狀態，均未另開 finding。

ASSUMPTIONS_VERIFIED: R7 三家 stamp APPROVED；template rc=0；Task=11/11；FACT-RECEIPT=10；P0-02 source direction；B14 bounded「未定稿」；B24 bounded predicate rc=1；SPEC/TODO F-7/B-36 trace gap。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` rc=0；direct grep/awk receipts listed above；`grep -n '_bc_kv' scripts/cx_run.sh` rc=0；`grep -n '_prepare_and_run\|_run_cli_and_emit' scripts/cx_run.sh` rc=0；`bash scripts/gate.sh register-output GOVB0-TODO-R8 handoffs/20260805-govb0-todo-r8-codex.md` rc=0。
FAILURES_SEEN: B24 bounded predicate rc=1；其餘本輪機械檢查未失敗；尚未執行 implementation/runtime tests（產物不存在）。
SCOPE_CHANGES: none；只新增本報告，保留既有 dirty worktree 變更；未改 data_cache、碼、TODO、SPEC、backlog；未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；僅指出 TODO acceptance/trace contract 缺口，未改數值或 schema。
HANDOFF_OUTPUT: `handoffs/20260805-govb0-todo-r8-codex.md`；/tmp 無可清理項，未觸碰（保留 claude-501）。
RECONCILE-STAMP: codex REJECTED 2026-08-05 sha256:677123c980adddf56aae9d601a9a12565bb525fa7197d66212a67d56740ac626 task:GOVB0-TODO-R8
STATUS: DONE
