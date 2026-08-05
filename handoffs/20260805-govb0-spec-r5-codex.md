# GOVB0 SPEC R5 confirmation report

task-id: GOVB0-SPEC-R5
family: codex
brief-kind: review
scope: 只確認 G-1～G-6；未改碼、未改 SPEC、未 commit/push。

## Verdict

需修補後再審（R6）。G-1 與 G-2 各有一個新的 P0 機制缺口；G-3～G-6 CLOSED。

## §0 前提與事實核對

- fact-verified：`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md` → rc=0；三家 APPROVED，body sha `ae304eeb…f88b3fa`。
- fact-verified：`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock` → rc=0；codex 3/3、composer 5/5，全部 8 IDs 歸戶。
- fact-verified：`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0；Task 計數=11、FACT-RECEIPT 計數=10。
- fact-verified：R4 收斂檔明載 G-1/G-2 為「待 R5 逐條複核」，未把文字修訂當成機械自證。
- assumed → refuted：五條 heredoc 規則足以覆蓋全部合法 heredoc；下列 G-1 反例可重現漏掃。
- assumed → refuted：八條狀態斷言覆蓋全部併發失效路徑；下列 G-2 TOCTOU interleaving 未被明確約束。
- heredoc 出現頻率無法由現有 audit 可靠統計：SPEC §A 的 receipt 已確認 audit 沒有指令欄位；本判定不依賴頻率，因失效路徑可直接重現。

## CODEX-R5-P0-01

**斷言**: G-1 的 delimiter regex 只接受 `[A-Za-z_][A-Za-z0-9_]*`，未規定合法但不匹配的 heredoc delimiter 必須 fail-closed；因此 heredoc 本體可藉第二個可匹配 marker 跨過真實外部派工。

**碼證**: SPEC Task 2.0 §10 的起點 regex 是 `<<[-]?[[:space:]]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1`。可重跑：用 delimiter `EOF-1`，body 放 `<<INNER`，真實外部命令放在 `EOF-1` 後、`INNER` 前；`bash -c` 實跑 `HEREDOC_SHELL_RC=0`、輸出含 `ATTACK_EXECUTED`，而按 identifier-only span 規則的最小掃描器輸出 `CONTRACT_SHAPE_SCAN=ALLOW`。RECHECK：同一語料將 `printf ATTACK_EXECUTED` 換成 `codex exec -s workspace-write x`，預期必須 BLOCK。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#778f73cae23a

[BLOCKING] 信心度=High；`EOF-1` 是 shell 可執行的 delimiter，並非蓄意破壞語法。掃描器不辨識第一個 heredoc，卻把本體內的 `<<INNER` 當新 span，會跳過 `EOF-1`、外部 `codex` 行與 `INNER` 終點，形成 fail-open。修法：補一條「任何合法 `<<` 但 delimiter 無法按契約解析時整段 fail-closed」的規則，或把 delimiter grammar 擴至 shell 接受的 word 並做 quote removal；在 immutable corpus 加入 `EOF-1`／quoted `EOF-1`／body 內假 marker／delimiter 後外部派工的 TP/TN 與 mutation。

## CODEX-R5-P0-02

**斷言**: G-2 定義了 owner-safe release 與存活判準，但沒有要求取得 `<out>` lock 必須是原子 exclusive claim；兩個 dispatcher 可在同一個空檢查窗口後同時啟動，故八條斷言未封閉併發重派窗口。

**碼證**: SPEC Task 3.2 §lock lifecycle 只要求 lock 綁 attempt/pid/time、啟動前檢查及 release 比對；同段未出現 `O_EXCL`、`flock`、`mkdir`、TOCTOU 或 equivalent atomic acquisition。`rg -n 'O_EXCL|flock|TOCTOU|exclusive|原子.*鎖|原子.*lock' docs/GOVB0_FRICTION_SPEC.md` → rc=1。最小 barrier 模擬中 A/B 都先看到 absent，再於 create/launch 前 sleep，stdout 出現 `A:START`、`B:START`、`TOCTOU_SIM_BOTH_PRECHECKS_PASSED=yes`。RECHECK：以兩個同一 `<out>` dispatcher 在 precheck 後 barrier 同步，必須恰有一個 CLI start、另一個 rc≠0，且 loser 不寫 `result_state`。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#778f73cae23a; handoffs/reconcile/20260805-govb0-spec-r4/synth.md#d925b789b568

[BLOCKING] 信心度=High；owner-safe release 只能防止舊 owner 釋放新 lock，不能阻止兩個 owner 同時通過「目前沒有 lock/attempt」檢查。若後寫 lock 覆蓋先寫 lock，兩個 CLI 已經啟動，④ 的 release 斷言也只能留下新 lock，無法回溯阻止並發。修法：在 CLI launch 前以每個 `<out>` 的原子 exclusive create（例如 `mkdir` lock directory 或等價 `O_CREAT|O_EXCL`）取得 ownership，失敗者重新讀 lock 後拒絕；新增 deterministic barrier race test，並把 process-discovery/lock-create 任一錯誤設為 fail-closed。

**G-1～G-6 逐條結果**

- G-1：**NOT-CLOSED**。五條規則對 identifier-only delimiter 的正常案例可執行，但對合法 `EOF-1` delimiter 存在上述漏掃反例。
- G-2：**NOT-CLOSED**。八條斷言覆蓋已列四條生命週期路徑與 lock deletion，但未明定原子取得 lock，故仍有 precheck→launch TOCTOU。
- G-3：**CLOSED**。receipt `govb0-r4-g3-factcount` 的 `grep -c '^- FACT-RECEIPT:'` stdout=`10`；現行 SPEC 同命令 stdout=`10`，證明力足以支持計數 claim。
- G-4：**CLOSED**。receipt `govb0-r4-g4-composer-ids` 與現行內容一致；以 Task heading contextual read 確認 Task 2.1 為 `P1-02`、Task 3.3 為 `P1-01`。receipt 單獨列行號屬中等證明力，與現行內容合併後足夠，未將行號漂移另列 finding。
- G-5：**CLOSED（已接受殘留，非 finding）**。receipt `govb0-r4-g5-b36-residual` 的三行內容明載 B-36 併 B-13 及「ID 錯位無機械防線」；與 SPEC §N 現況一致，依 brief 不重開。
- G-6：**CLOSED（SPEC 契約層）**。receipt `govb0-r4-g6-provisional` 命中 SPEC 的 `PROVISIONAL` 條款；現行 lines 434–438 明確列出 TODO/manifest、Task 3.3 未完工、B-14 未定稿三項斷言。TODO 尚未生成是出場判準未通過後的預期狀態，不宣稱實作已完成。

**§1 必查類別摘要**

1 矛盾/互斥：G-1/G-2 如上；2 漏項/端到端：原有 G-1/G-2 範圍外無新增；3 不可測驗收：原有條款已具命令/狀態斷言，G-1/G-2 的兩個缺口已列可執行修法；4 quant：不適用；5 過度工程：無新增；6 OOM/並行：G-2 TOCTOU；7 cache：不適用；8 API/型別：不適用；9 測試品質：G-1/G-2 修法需補 race/非 identifier corpus；10 Agent 可執行性：G-1 delimiter grammar、G-2 atomic claim 需補明文契約；11 必要性/短命工：無新增。

**出場判準與 R6**

- findings：2，滿足 `≤5`。
- 新 P0 機制缺口：2（G-1 未匹配合法 delimiter 的 fail-closed；G-2 atomic exclusive lock acquisition）。
- 判準要求 `新 P0 機制缺口 <2`；實際 `2 <2` 為 false。
- 結論：**需要 R6**，R6 只需確認上述兩個具體機制缺口已補入 SPEC/TODO 並以 heredoc bypass 與 barrier race 兩組測試關閉；不重開 E-SCOPE、命名、措辭或既有接受殘留。

ASSUMPTIONS_VERIFIED: R4 stamp/completeness/template/count receipts 已實跑；G-1 shell bypass 與 G-2 TOCTOU interleaving 已實跑；G-3～G-6 現行內容與 receipt 一致。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh ...` rc=0；`bash scripts/completeness_check.sh --lock ...` rc=0；`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0；direct grep counts 10/11；heredoc probe rc=0 with ATTACK_EXECUTED and shape scan ALLOW；TOCTOU probe A/B both START。
FAILURES_SEEN: 初次把含 literal heredoc 的複合 shell probe 送入工具後超時，已終止並改用 escaped-byte、短命令重跑；未改 repository tracked files。
SCOPE_CHANGES: none；只新增本報告。
NUMERIC_OR_SCHEMA_IMPACT: none；未改 SPEC、程式、測試、資料或輸出 schema。
HANDOFF_OUTPUT: handoffs/20260805-govb0-spec-r5-codex.md
STATUS: DONE
