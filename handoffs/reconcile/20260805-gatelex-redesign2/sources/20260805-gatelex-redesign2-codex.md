# GATELEX-REDESIGN2 — codex（brief-kind: consult）
RECONCILE-STAMP: `handoffs/reconcile/20260805-govb0-b3-fix2review/synth.md` 的 composer/grok/codex 三筆均 APPROVED；本報告禁改碼、禁改測試、未 commit/push。
## Verdict
不通過主委 §B 原提案的直接派工條件；E-1/E-2 根因獨立，需先做獨立 B3.5 lexer contract/prototype；latency 維持現狀並列 named residual。FINDINGS_COUNT: 3
## §0 前提宣告
fact-verified：`grep -c '^{'` 語料 A/B=`30/65`、SPEC/TODO Task=`11/11`；E-1 probe newline/semicolon=`rc 0/2`；quoted E-2=`100K 1.32s`、`500K 31.00s`。
assumed/待攻：proposal ② 的「first token＋cmdsub span＋unclosed flags」是否足以導出全部 11 契約；冷 cache I/O 未取得獨立證據，不把它當根因。
## 逐項核對表
### §A 問1～問5
問1：共同背景是缺單一結構化 lexer，但 E-1 是 grep/跨行命令位置語義缺口，E-2 是 `awk out=out c` 的超線性物化，根因獨立；問2：提案②按原輸出契約不可涵蓋 3/7/10，且 4/5/8/9 欄位不足；問3：採 enriched event contract（token sequence、decoded/normalized command word、context、heredoc validity/body span、recursive depth、parse error）＋單一 scanner/reducer；問4：維持現狀，若修則先 prototype/differential，再一次共享 lexer 改寫，不做局部 B4 拼補；問5：獨立 B3.5，通過後才 B4。
### §B 提案①～②
提案①部分成立、共同根因判斷過度合併：E-1 可由跨行狀態修正，E-2 可由避免全文 `out=out c` 修正，任一可單獨發生；提案②的 O(1)「逐項 emit」方向可行，但 first token 無法區分 `bash -c codex`/`bash -c echo`，cmdsub spans 不涵蓋 `-c`/`eval` 引數，也沒有 path normalization、depth、heredoc malformed/closed span 的事實。
### §B 提案②逐條核對
`1=Y,1b=Y,2=Y,3=N,4=Y*,5=Y*,6=Y,7=N,8=N*,9=Y*,10=N`；`*` 僅在 enriched token/escape/depth/span facts 補齊後成立，否則不是可驗收設計。
### §B 提案③與下一步
scanner 以 callback/reducer 直接產生 `COMMAND(depth,start,words,decoded_basename,context)`、`EXEC_SPAN(kind,start,end,depth)`、`HEREDOC(status,delimiter,body_span)`、`LEX_ERROR(kind,offset)`；熱路徑 O(1) working memory，trace mode 才保存事件。B3.5 先在 `/tmp` 做 11×TP/TN、26 parity、A/B differential、11 mutation、100K/500K timeout；未通過不派 B4。
### §D 問D1～問D5
D1：同 34,796 行/2,155,184B audit，無負載 `cold=74.9ms`；8 CPU hog `cold=144.2ms, second=155.9ms`；獨立 gate 0/1K/10K/34,787 行 12 次平均 `11.65/11.59/11.79/11.86ms`，故已證 CPU/scheduler 競爭，audit 規模非單獨解釋，冷 I/O仍未證明；Task 路徑在 `gate_check.sh:159-162` 直接設 dispatch，不經 lexer。D2：選(a)維持現狀，拒(b)min、(c)升門檻、(d)隔離競爭；D3：5 次 `150,150,150,150,70ms` 時 min=70 會假綠；D4：`git log -S'test_gate_check_latency_under_100ms'` 只有 `141e4b8` 首次加入，`c2a351f/fd6dc77` 證明唯一著名紅燈是抖動並造成錯誤封存，未見抓到真實結構退化；D5：`nl -ba docs/P16_COMMITTEE_DEBT_SPEC.md | sed -n '504,508p'` 明列單次 `<100ms` 與超標須 tail/index，升門檻仍是放寬契約；與 lexer redesign 無依賴。
## CODEX-R17-P0-01
**斷言**：proposal ② 原輸出不能導出全部 11 契約。**碼證**：`pytest -q tests/governance/test_gate_lexical_contract.py tests/governance/test_debt_gate.py`→23 passed；`grep -c '^{'`→A/B=30/65；`bash scripts/gate_check.sh` newline/semicolon→0/2，顯示需完整 token/recursive facts。**來源摘要**：`docs/GOVB0_FRICTION_TODO.md#a1410ec31fcd`、`scripts/_gate_lex.sh#debe1484a7e5`、`tests/governance/fixtures/gate_decision_corpus.txt#1ffb72e0e666`。[BLOCKING|P0] 信心度 High；先補 output contract 與 differential/mutation oracle。
## CODEX-R17-P1-02
**斷言**：O(1) emit 宣稱與現行 shell 介面及 proposal 的「emit span content」互相衝突。**碼證**：`nl -ba scripts/_gate_lex.sh | sed -n '75,181p;362,424p'` 可見 `src=src line`、`out=out c`、`cmdsubs=$(...)`；quoted probe `timeout 40 /usr/bin/time -p bash scripts/gate_check.sh`→100K `real 1.32s`、500K `real 31.00s`、rc=0。**來源摘要**：`scripts/_gate_lex.sh#debe1484a7e5`、`scripts/gate_check.sh#b454a55ea513`。[MAJOR|P1] 信心度 High；scanner 應 reducer/stream-span，另定資源上限與 fail-closed，不回復 8192 截斷放行。
## CODEX-R17-P1-03
**斷言**：現 latency 測試不是 lexer gate，且在 CPU 競爭下可偶發假紅，不能作 B3 redesign oracle。**碼證**：`pytest -q -s ...test_gate_check_latency_under_100ms` baseline `cold=74.9ms` passed；同命令併 8 `yes` hog→`cold=144.2ms, second=155.9ms` failed；`git log -S'test_gate_check_latency_under_100ms'`→`141e4b8`。**來源摘要**：`tests/governance/test_debt_gate.py#f4d28ce5adbd`、`docs/P16_COMMITTEE_DEBT_SPEC.md#56915f8bdab3`。[MAJOR|P1] 信心度 High；保留 100ms canary，不改成 min/提高門檻，另立 lexer-size benchmark。
## 出場判準核算
FINDINGS_COUNT: 3；unique clusters=3（≤3），deliverable-invalidating=1，BLOCKING=1，故不得進 B4；建議 B3.5 先行。 ASSUMPTIONS_VERIFIED: 三筆 reconcile stamp APPROVED；dirty B3 工作區未被本任務改動；11 contracts/65 B rows；Task latency bypass lexer；100ms 出自 P16 SPEC:507。
TESTS_RUN: targeted governance `23 passed`；quoted E-2 100K/500K=`1.32s/31.00s` rc=0；latency baseline pass/load fail；`restore_golden_inventory.sh` rc=128（sandbox 禁寫 `.git/index.lock`），但 `git status --short -- tests/golden/` 與 diff 均空。
FAILURES_SEEN: CPU-load latency 1 intentional reproduction；restore rc=128 未宣稱成功；無修碼失敗。 SCOPE_CHANGES: none；未碰 data_cache、tracked code/test、commit/push。 NUMERIC_OR_SCHEMA_IMPACT: none。 TMP_CLEANUP: 本次 `/tmp/gatelex-*` 均已不存在；`/tmp/claude-501` 保留。
STATUS: DONE
