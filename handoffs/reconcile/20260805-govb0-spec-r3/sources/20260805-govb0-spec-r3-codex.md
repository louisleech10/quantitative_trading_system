# GOVB0 SPEC R3 adversarial review | family: codex | task-id: GOVB0-SPEC-R3 | scope: docs/GOVB0_FRICTION_SPEC.md only; no code/test changes
## CODEX-R3-P0-01
**斷言**: Task 0.1 的 audit schema 與判定不變驗收仍互斥，R2 `CODEX-R2-P0-03` 未閉合。
**碼證**: `nl -ba docs/GOVB0_FRICTION_SPEC.md | sed -n '104,118p'` → line 105 排除 audit 欄位，line 117 仍要求兩份 JSON diff 為空；`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f
[BLOCKING] 信心度=High；改法仍未命名/分離 decision trace 與 audit record，新增欄位後「完整 JSON diff 為空」不可成立；固定兩種輸出、key/type/escaping/空值/截斷契約，分別驗 `(rc,kind)` 與 audit schema。
## CODEX-R3-P0-02
**斷言**: Task 2.0 雖列 10 項，unquoted `-c`、recursion cap、escape 與 heredoc 仍沒有確定結果；1b 的跨行設計與 Task 2.1 的 shell/`sed` 限制也衝突。
**碼證**: `bash handoffs/govb0_probes/b15probe4.sh` → 現行 gate 的 eval/`$()`/反引號/子 shell 五向量均 ALLOW；`bash handoffs/govb0_probes/b15probe6.sh` → awk 跨行 4/4、sed 0/4；spec lines 175–178 仍寫「依契約定義／有上限／須定義」。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f
[BLOCKING] 信心度=High；先固定有限 grammar、每項 TP/TN 的精確 ALLOW/BLOCK、數值 cap/逾限、escaped quote/backslash-newline、heredoc delimiter/body/外部分號；熱路徑須明定 in-process shell 或准許單次 awk 並附 latency receipt。未見 repo 實例的 `$'...'`/process substitution 可列 P2、不阻擋本批。
## CODEX-R3-P0-03
**斷言**: 序列化拒絕解掉原 R2「兩份成功 payload 互相覆蓋」問題，但新設計未定義 lock ownership/release、timeout 後 retry 與被拒 attempt 的狀態，可能誤拒正常重派。
**碼證**: spec lines 320–327 僅規定第二 attempt `rc≠0`＋audit，lines 339–341 僅規定 timeout/三值 `result_state`；`rg -n 'lock|retry|rejected|重派' docs/GOVB0_FRICTION_SPEC.md` 無具體 primitive、釋放/重試/被拒狀態契約。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f
[BLOCKING] 信心度=High；固定原子鎖/registry、正常/格式失敗/SIGKILL/outer-timeout 的釋放與 stale recovery、retry eligibility/backoff，以及被拒請求是「無 attempt 的獨立 audit」或哪個狀態；否則「每 attempt 恰一筆 result_state」與 rejection 互相無法驗收。
## CODEX-R3-P1-04
**斷言**: E-10 要求的 codex 嚴格門檻未落到 R3：brief 要求每家族 ≥50 筆＋≥3 個 session/UTC 日期，但 SPEC 仍為 ≥20，且只對 <10 標 `PROVISIONAL`，10–19 未定義。
**碼證**: brief line 56 明列 `≥50`＋`≥3`；`rg -n '≥20|≥50|session|UTC|PROVISIONAL' docs/GOVB0_FRICTION_SPEC.md` → Task 3.3:344 為 `≥20`、347 僅 `<10`；template/task count receipt → 11 tasks、`TEMPLATE PASS` rc=0。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f; handoffs/20260805-GOVB0-SPEC-R3-BRIEF.md#1c47569db2f9
[MAJOR] 信心度=High；改為 ≥50＋≥3 session/UTC date、缺欄排除、選值公式與 10–49 的 provisional 行為；Q4 的「先上安全 timeout、Task 3.3 不宣稱完成、B-14 未定稿」取捨可接受，但目前文字未實作該取捨。
## CODEX-R3-P1-05
**斷言**: B-36 是 MAJOR/P1 的判斷層完整性漏洞，應併入 B-13，不應只靠人工自檢。
**碼證**: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r2/sources.lock` → `COMPLETENESS PASS`（10/10、7/7、全來源 ID 在 synth），但 backlog lines 1202–1227 記錄附錄使 ID 必然存在而群集表仍可漏；brief lines 105–109 同列實證。
**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#93d86e7c4ae7; handoffs/20260805-GOVB0-SPEC-R3-BRIEF.md#1c47569db2f9
[MAJOR] 信心度=High；B-13 吸收 B-18 與本票，優先在 `reconcile_build.sh` 預填全部 ID 的產出端攔漏，再保留 `completeness_check --lock` 群集段逐 ID 檢查作防線。
Q1：R2 P0-01 NOT-CLOSED/OUT-OF-SCOPE（309–312 明文不解）；P0-02 CLOSED（320–324 序列化後原覆蓋反例不再成立）；P0-03 NOT-CLOSED（105/117）；P0-04 NOT-CLOSED（175–178）；P0-05 CLOSED（364–365、grep=11）；P0-06 NOT-CLOSED/OUT-OF-SCOPE（§N 403–405）；P1-07 NOT-CLOSED（344/347）；P1-08 CLOSED（325–327）；P1-09 CLOSED（367–373、unknown 四項狀態）；P1-10 CLOSED（A/B corpus 與 snapshot 分離 104–109）。
Q2：有新矛盾：10 項 lexical contract 與 2.1–2.4 的驗收缺 exact oracle；A/B 分離的概念本身不互斥，但 105/117 的 JSON diff 仍使驗收不明；序列化拒絕與 timeout retry 的 lock/release/result-state 互動未定義。
Q3/Q4：跨行有狀態設計正確（b15probe6：awk 4/4、sed 0/4）；awk 只有在明文解除「hot path 禁 subprocess／純 shell/sed」並附效能 receipt 後可用，需補 heredoc、續行、`$'...'`、escaped quote 規則；暫定 timeout policy ACCEPT，但不得標 Task 3.3 DONE，且門檻須改為 codex 嚴格版。
## Verdict: 需修補後派工；Q5 B-36 併 B-13、產出端為主檢查點；Q6 明確 `ASSERT` 均有同 Task 狀態斷言，但 JSON diff 與 Task 2.0 mutation oracle 仍不可證偽；Q7 BLOCKING=`CODEX-R3-P0-01/02/03`、`CODEX-R3-P1-04`，B-36 為 TODO 前收斂工具前置；OUT-OF-SCOPE=`B-35/B-34/B-24` 機械面/B-15 FP-2。STATUS: DONE
