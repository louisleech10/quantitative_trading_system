# Reconcile — 20260805-govb0-b3-review

**來源** 20260805-govb0-b3-review-codex.md, 20260805-govb0-b3-review-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併。B3 不得直接進 B4；C1–C5 本批修完並補回歸測試後重審。

### 主委獨立實跑（不採信報告，對照 pre-Phase2 snapshot）

`VERIFY:20260805T124806Z-b3-failopen-independent-repro`（`.claude/tmp/probe_b3.sh`；rc 直接取，未經 pipe）

| 探針 | 舊 rc | 新 rc | 判定 |
|---|---|---|---|
| 基準：裸 `codex exec x` | 2 | 2 | 無回歸 |
| 引號內命令替換 `echo "$(codex exec x)"` | **0** | **0** | **非 B3 回歸**（舊版同樣放行） |
| 引號 env 前綴 `FOO="bar" codex exec x` | 2 | **0** | fail-open 回歸，重現 |
| 8KiB 後綴 | 2 | **0** | fail-open 回歸，重現 |

🔴 **對委員裁決的一項更正**：codex 報 3 條 BLOCKING，
但 `CODEX-R1-P1-01`（引號內命令替換）**舊版 rc 亦為 0**，不符 brief 判準
「舊版擋、新版放行且確為真派工者一律 BLOCKING」⇒ **不是 B3 造成的回歸**。
該漏洞本身為真（`$()` 在雙引號內確實會執行），故**不降低修復優先度**，
但歸屬應記為**既有缺陷**而非 B3 回歸——歸屬錯誤會使後續「B3 引入幾個洞」的統計失真。

### 群集

| # | 群集 | 來源 ID | 級別 | 處置 |
|---|---|---|---|---|
| **C1** | `_gate_lex.sh` 8KiB 截斷 → 尾端真派工放行 | `CODEX-R1-P1-03`＋`COMPOSER-R12-P0-01`（兩家獨立同結論） | **BLOCKING** | **本批修**。採 composer 首選：取消截斷改流式掃描；若保留上限則超長一律 fail-closed，禁靜默 ALLOW |
| **C2** | 引號 env 賦值前綴 → 家族 CLI 放行 | `CODEX-R1-P1-02` | **BLOCKING** | **本批修**。`gate_check.sh:167-169` 的剝除字元類需 quote-aware |
| **C3** | 雙引號內 `$()`／反引號命令替換放行 | `CODEX-R1-P1-01` | 既有缺陷（**非 B3 回歸**） | **本批一併修**。理由：正落在 Task 2.1「引號感知」主題內——引號內的 `$()` **不是**字面字串，B3 的剝引號規則依其自身設計意圖即應處理 |
| **C4** | 排除機制 reverse-1 mutation 為恆真斷言 | `CODEX-R2-P2-04` | MAJOR | **本批修**。屬 B3 交付物之測試品質；需真實注入 victim 後 mutation 轉紅 |
| **C5** | 抽取器未涵蓋 TODO 絕對態敘述（「皆 BLOCK」） | `COMPOSER-R12-P1-01` | MAJOR | **本批修**。現況不紅，但削弱「清單窮舉 TODO 轉向」前提，B4+ 擴語料 A 會再撞同一設計矛盾 |
| **C6** | 多 heredoc 第二 body 未消耗 → 誤擋 | `CODEX-R2-P2-05` | MINOR | **具名殘留，順延 B4**。方向為誤擋（fail-closed）不影響安全；B4 本就要動同一檔 |

### 出場判準核算（本輪）

findings 去重後 **6** 群（≤5 ✗，超 1 群）｜BLOCKING **2**（brief 判準；codex 原報 3，一條經實跑更正為既有缺陷）
⇒ **未通過**，符合預期：本輪目的即為攔截，且 fail-open 正是 brief 新增的攻擊方向所命中。

### 委員合約違反（具名記錄，不影響本輪結論）

composer 自陳「誤跑 `extract_phase2_expected_flips.py`（無 `--check`），已 `git checkout --` 還原」。
**執行端禁對 tracked 檔 `git checkout`** 為明文合約條款。
主委實跑 `git status --short tests/governance/fixtures/` 為空 ⇒ 本次未造成實害。
歸因：brief 硬性要求第 3 條已寫明禁令，委員仍違反 ⇒ 屬**執行端合約遵循**問題，記入 backlog。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: `echo "$(codex exec x)"` 與 `echo "`codex exec x`"` 是可執行真派工卻 ALLOW；**碼證**: `_gate_lex.sh:143-166,196-203,305-311` 對整個 quote span 把空白改 US；**來源摘要**: `scripts/_gate_lex.sh#86ffda54b321`; [BLOCKING] 信心度=High；修法：double-quote state 內對 `$()`/backtick 建 nested command scan；RECHECK：`GATE_DIR_OVERRIDE=$(mktemp -d) bash scripts/gate_check.sh <<<"$(jq -n --arg cmd 'echo "$(codex exec x)"' '{tool_name:"Bash",tool_input:{command:$cmd}}')"`，目前 rc=0，應 rc=2。
## CODEX-R1-P1-02
**斷言**: 合法 quoted env assignment 後的家族 CLI 被放行；**碼證**: `gate_check.sh:167-169` 只剝 `[A-Za-z0-9_./:@%+=,-]+`；`FOO="bar" codex exec x` 舊 snapshot rc=2、新 rc=0；**來源摘要**: `scripts/gate_check.sh#2ec2254dba3a`; [BLOCKING] 信心度=High；修法：quote-aware assignment-word tokenizer，保留 `$()` 防護且不漏掉引號值；RECHECK：以同一 payload 分別執行 `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` 與 `scripts/gate_check.sh`，期望 2/2。
## CODEX-R1-P1-03
**斷言**: 真派工位於第 8192 byte 後會被截斷而 ALLOW；**碼證**: `_gate_lex.sh:291-305` `raw` 只取前 8192；`x×9000; codex exec x` 舊 rc=2、新 rc=0；**來源摘要**: `scripts/_gate_lex.sh#86ffda54b321`; [BLOCKING] 信心度=High；修法：完整掃描，或超長時 fail-closed 並保留可證明的界線；RECHECK：`prefix=$(printf 'x%.0s' {1..9000}); cmd="$prefix; codex exec x"; payload=$(jq -n --arg cmd "$cmd" '{tool_name:"Bash",tool_input:{command:$cmd}}'); GATE_DIR_OVERRIDE=$(mktemp -d) bash scripts/gate_check.sh <<<"$payload"`，目前 rc=0，應 rc=2。
## CODEX-R2-P2-04
**斷言**: exclusion reverse-1 mutation 沒有驗證判定流程；**碼證**: `test_gate_deny_fields.py:530-557` 只對非 flip victim 再呼叫 `_flip_matches_command` 並 assert `hit is None`，未改 gate/test subject、未執行 altered `excluded` trace；**來源摘要**: `tests/governance/test_gate_deny_fields.py#e64635d078c5`; [MAJOR/non-blocking] 信心度=High；`pytest ... -k invariance_exclude_nonflip_mutation`=1 passed 只證明 helper；修法：真實注入 victim 後要求 mutation test 轉紅；RECHECK：該 pytest 應在移除 reverse-1 assertion 的 mutation 下 rc≠0。
## CODEX-R2-P2-05
**斷言**: 多 heredoc 的第二個 body 未被消耗，body 中的 `codex exec x` 被誤擋；**碼證**: `_gate_lex.sh:99-135` 找到第一個 `<<` 後即消耗其 body，未排程同一 header 的後續 delimiter；`cat <<A <<B\nbodyA\nA\ncodex exec x\nB\ntrue` 新 gate rc=2，shell heredoc 語意應 ALLOW；**來源摘要**: `scripts/_gate_lex.sh#86ffda54b321`; [MINOR] 信心度=High；修法：先收集 header 全部 heredoc delimiter 再按序消耗，補第二 body TP；RECHECK：上述 payload 應 rc=0，並加入反向 mutation。
## COMPOSER-R12-P0-01

**斷言**: `_gate_cmd_is_dispatch` 在指令長度 >8192 時截斷掃描字串，使**舊版會 BLOCK 的真派工**（前綴填充 + `; codex exec …`）在新版變成 **ALLOW（fail-open）**。

**碼證**:
- `scripts/_gate_lex.sh:291-303`：`local _max_lex=8192` + `head -c "$_max_lex"`
- RECHECK:
```bash
python3 -c "pad='x'*8200; import json,subprocess,os; cmd=pad+'; codex exec hi'; p=json.dumps({'tool_name':'Bash','tool_input':{'command':cmd}}); subprocess.run(['bash','scripts/gate_check.sh'],input=p,env={**os.environ,'GATE_DIR_OVERRIDE':'/tmp/govb0-gate-dir-composer'}).returncode"
# 現行 → 0 (ALLOW)
bash scripts/gate_check.sh <<< "$(python3 -c "import json; print(json.dumps({'tool_name':'Bash','tool_input':{'command':'x'*8200+'; codex exec hi'}}))")" ; echo rc=$?
# 現行 rc=0；pre-Phase2 snapshot rc=2（本 reviewer 對照實跑）
```

**來源摘要**: scripts/_gate_lex.sh#86ffda54b321

[BLOCKING] 信心度=High。委員 prompt 可達數十 KB；攻擊者可在前 8KiB 填無害內容、尾端放 `; codex exec …` 繞過 PreToolUse。brief 明文：舊擋新放之真派工一律 BLOCKING。

**修法**:
1. **首選（fail-closed）**：取消截斷；改以單次 awk 流式掃描或分塊掃描，保留「命令位置」語意且 O(n) 而非 O(n²) 拼接。
2. **次選**：截斷時若末尾未見完整 shell 句法且長度被截 → `return 0`（BLOCK），勿靜默 ALLOW。
3. **測試**：新增語料 B TP + mutation——截斷邏輯 revert 後該條須轉 ALLOW（證偽）。

---

## COMPOSER-R12-P1-01

**斷言**: `extract_phase2_expected_flips.py` 只辨識「由 BLOCK 轉 ALLOW／維持 …」等方向標記，**未覆蓋** TODO 中以絕對態寫法的行為變更（如 `TEST-2.1-RECURSE`「六條皆 BLOCK」、`TEST-2.2-REGRESS`「兩條須 BLOCK」），未來若這些命令進語料 A 且 Phase 2 改動判定，**不會自動進排除清單**。

**碼證**:
- `docs/GOVB0_FRICTION_TODO.md:336-337`（RECURSE 六條，無「由 ALLOW 轉」字樣）
- `scripts/extract_phase2_expected_flips.py:128-131`（無方向標記則 `continue`）
- 現況安全：`gate_invariance_corpus.txt` 無 `bash -c "codex exec` 等 RECURSE 條目（`grep` 0 命中）；`test_01_invariance_decision_trace` 仍綠

**來源摘要**: scripts/extract_phase2_expected_flips.py#f4f54dabbefe

[MAJOR] 信心度=High。不阻斷當前 invariance，但削弱「清單窮舉 TODO 轉向」前提；B4+ 若語料 A 擴充可能再次撞主委式矛盾。

**修法**: 抽取器增第三類「絕對態＋命令列舉」（`皆 BLOCK`／`須 BLOCK` + 反引號命令），或要求 TODO 一律用「由 X 轉 Y」格式；並加測試：RECURSE 六條若模擬進 A 必須在 flips 或明確 `maintain`。

---


## 戳記

<!-- 委員 append RECONCILE-STAMP 行於此區段之後；本區段之前為 body-hash 計算範圍 -->
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:f9c4e0ee67936ffaddd6617eb4428d4bc5702cea884751eb5bde6d3170f33bf5 task:GOVB0-B3-STAMP
RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:f9c4e0ee67936ffaddd6617eb4428d4bc5702cea884751eb5bde6d3170f33bf5 task:GOVB0-B3-STAMP
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:f9c4e0ee67936ffaddd6617eb4428d4bc5702cea884751eb5bde6d3170f33bf5 task:GOVB0-B3-STAMP-GROK
