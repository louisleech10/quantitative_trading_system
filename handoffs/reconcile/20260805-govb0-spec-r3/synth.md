# Reconcile — 20260805-govb0-spec-r3

**來源** 20260805-govb0-spec-r3-codex.md, 20260805-govb0-spec-r3-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併 — 11 條全部歸戶，**無未分群 ID**（主委已逐 ID 自檢群集段，見下）。
**收斂趨勢轉正**：R1 19 條（5 P0）→ R2 17 條（7 P0）→ **R3 11 條**。
`E-SCOPE` 生效：codex 明確標示 `B-35`／`B-34`／`B-24` 機械面／`B-15` FP-2 為 `OUT-OF-SCOPE`，未再列 BLOCKING。
**R3 的 11 條大多是主委自身的漏改與計數漂移**，非新機制缺口 ⇒ accretion 已中止。

**收斂基數**：11 條（codex 5／composer 6）。

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| F-1 | **Task 0.1 驗收自相矛盾未閉合**：不變式已收窄為 `(rc,kind)`，但驗收仍要求「兩份 JSON diff 為空」，而 audit 新增欄位必然使 JSON 不同 | `CODEX-R3-P0-01`／`COMPOSER-R3-P0-01` | **ACCEPT-BLOCKING**（客觀矛盾） |
| F-2 | **Task 2.0 契約 4 項只列項目未定結果**（unquoted `-c`／遞迴深度上限／跳脫引號／heredoc）；且 **1b 的跨行掃描與 Task 2.1「純 shell/`sed`」限制衝突** | `CODEX-R3-P0-02` | **ACCEPT-BLOCKING** |
| F-3 | **序列化拒絕的 lock 生命週期未定義**：ownership／release／逾時後重派／被拒 attempt 的狀態 ⇒ 可能誤拒合法重派或永久鎖死 | `CODEX-R3-P0-03`／`COMPOSER-R3-P1-03` | **ACCEPT-BLOCKING** |
| F-4 | **E-10 收斂裁決未落到 SPEC**：R2 收斂已定 ≥50 筆 ＋ ≥3 session／UTC 日，SPEC 仍寫 ≥20，且 10–19 區間未定義 | `CODEX-R3-P1-04`／`COMPOSER-R3-P1-01` | **ACCEPT-BLOCKING**（主委漏改） |
| F-5 | **Task 2.0 契約計數漂移**：驗收稱「10 項」，實際條目含 `1`／`1b`／`2`–`10` 共 **11 項** | `COMPOSER-R3-P2-01` | **ACCEPT**（同 `票 B-17` 病型，本 SPEC 第二次） |
| F-6 | **Task 2.1 未列 1b 的具名語料** ⇒ 實作者可能只抄原型③（不含 1b）即通過 | `COMPOSER-R3-P1-02` | **ACCEPT** — 補四條 `b15probe6` 語料並納入語料 B |
| F-7 | **`票 B-36` 應併入 `票 B-13`**，且修法應在**產出端**（生成骨架時預列全部 ID），不得只靠人工自檢 | `CODEX-R3-P1-05`／`COMPOSER-R3-P2-02` | **ACCEPT** — 兩家一致，照辦 |

🔴 **主委在本表第一版又引錯三個 ID**（把 `COMPOSER-R3-P1-02`／`P2-01`／`P2-02` 分別誤寫成
`P0-02`／`P1-04`／`P2-01`），**由主委自己的逐 ID 自檢抓到**（`COMPOSER-R3-P2-02` 完全未被引用）。
⇒ 這是 `F-1`／`F-4`／`F-5` 同一病根（交叉引用不同步）的**第四次**現形，也再次證明
**`completeness_check --lock` 對此完全無感**（rc 全程 0）。**`票 B-36` 的優先度應調升。**

🔴 **第五次現形（2026-08-05 R3 戳記輪，三家全數拒章）**：修正上述三個 ID 後，主委仍把
`COMPOSER-R3-P1-01`（E-10 門檻）與 `COMPOSER-R3-P1-02`（1b 語料）**在 F-4／F-6 之間對調**。
codex（`STATUS: BLOCKED`）、composer、grok **三家各自獨立指出同一處**，皆拒章。已修正。

⚠️ **這條暴露主委自建逐 ID 自檢的邊界（重要）**：
該自檢問的是「**每個來源 ID 是否出現在群集段**」——兩個 ID **都出現了**，只是**掛在錯的列**
⇒ **自檢 rc=0、`completeness --lock` rc=0，兩道機檢皆無感**，只有**語意複核**抓得到。
⇒ **`票 B-36` 的產出端修法（骨架預列 ID）也只能擋「漏」，擋不了「錯位」。**
「錯位」目前**沒有任何機械防線**，只能靠委員逐條核對。**此為具名殘留，應寫入 `B-36` 票面。**

**F-1／F-4／F-5 的共同病根（主委自陳）**

三條都是**「我在 A 處改了，B 處沒同步」**：
F-1＝收窄了不變式定義，**沒回頭改驗收句**；
F-4＝收斂檔寫了較嚴門檻，**沒同步到 SPEC**；
F-5＝契約加了 `1b`，**沒改計數**。
⇒ 正是 memory `交叉引用同步`（同類錯已犯 6 次）與 `票 B-17`（手寫機器依賴表必漂）所指。
**本 SPEC 內已第二次計數漂移**（R2 是 Task 總數 10 vs 11，R3 是契約項數 10 vs 11）。
🔴 **R4 起：凡文件內出現「N 項／N 個」且該 N 可由 `grep -c` 導出者，必須在同一行註明導出命令**，
code review 逐條機械核對。**這是本批可零成本落實的 `票 B-17` 紀律面**（比照 `B-24` 紀律面的作法）。

**F-2 的具體裁決（四項未定結果，此處定死）**

| 契約項 | 判定結果（R4 寫入 SPEC） | 理由 |
|---|---|---|
| unquoted `-c` 引數（`bash -c codex`） | **BLOCK** | 語意上就是「執行 codex」，與帶引號等價 |
| 遞迴深度上限 | **上限 3 層，逾限 fail-closed（BLOCK）** | 正常派工不會嵌套；逾限即可疑 |
| 跳脫引號（`"a\"b"`、`'a"b'`） | 跳脫字元**不終止引號 span**；若掃描器無法確定 span 邊界 ⇒ **fail-closed（視為未剝除）** | 與契約第 6 項（未閉合引號）同向 |
| heredoc（`cat <<EOF; codex exec x`） | **heredoc 本體視為引號 span**（不作分隔符、不掃描）；**heredoc 之外的部分照常判定** | `COMPOSER-R2-P1-02` 的誤擋來自把 heredoc 內容當命令 |

**F-2 的第二半：1b 與「純 shell/`sed`」衝突**

Task 2.1 原寫「純 shell/`sed`，禁 subprocess 呼叫 python」（熱路徑考量），
但 1b 要求跨行狀態機，`sed` 的 `s///` 做不到。**裁決**：允許 `awk`（POSIX，非 subprocess-heavy，
與 `sed`／`grep` 同級），**維持禁 python**。R4 須把 Task 2.1 的限制句改為「純 shell/`sed`/`awk`」。
🔴 **R4 brief 須請委員裁定 `awk` 在 PreToolUse 熱路徑的成本是否可接受**（每次工具呼叫都跑），
或有更便宜的純 shell 逐字元作法。

**F-3 的具體裁決（lock 生命週期，此處定死）**

- **ownership**：lock 綁 attempt id，內容含 pid 與起始時間戳。
- **release**：publish 完成後、或 `_emit_family_result` 寫入後（無論 success／failed／format-failed）**必定釋放**。
- **stale lock**：若 lock 的 pid 已不存在，或起始時間戳距今超過「該家族 timeout ＋ 外層安全閥」⇒ **視為 stale，可強制接管**並記 audit。
- **逾時後重派**：`failed` 的 attempt 其 lock 已在 `_emit_family_result` 時釋放 ⇒ **同 `<out>` 重派正常放行**。
- **被拒 attempt 的狀態**：**不寫 `result_state`**（該 attempt 從未啟動 CLI），只記一筆 audit 拒絕事件。
  🔴 理由：`result_state` 三值是 CLI 執行結果的語意，未啟動者寫入會污染 duration 統計（Task 3.1）。

**主委逐 ID 自檢（補 `票 B-36` 的檢查器盲點；本輪起每次收斂必做）**

對本檔跑「每個來源 ID 是否出現在群集段（`## 群集` 至 `## 附錄` 之間）」的逐一比對，
11/11 全在。**此為人工自檢，不算解決**——`票 B-36` 已定應在產出端解決（兩家一致）。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R3-P0-01

**斷言**: Task 0.1 將不變式收窄為 `(rc, kind)` 序列相等，但驗收仍要求「兩份 JSON diff 為空」，與「audit 新增欄位不在不變式內」**互斥**，實作者無法同時滿足。

**碼證**: `:104-105` 不變式僅 `(rc,kind)`；`:117`「逐項比對輸出兩份 JSON 並 diff 為空」。Phase 0 必增 `gate_deny` 欄位 ⇒ 完整 JSON diff 不可能為空。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[BLOCKING] 信心度=High。E-7 文本修訂未閉合驗收句。修法：分離 decision trace diff 與 audit schema 斷言（`:112-113` 方向），刪 `:117` 全 JSON 要求。

---

## COMPOSER-R3-P1-01

**斷言**: R2 收斂 E-10 已定「定稿門檻採 codex **≥50 筆＋≥3 session/UTC 日**、主委暫定值上線但 Task 3.3 **不得宣稱完工**」，R3 Task 3.3 僅寫 **≥20** 與 **<10 PROVISIONAL**，**未落實收斂裁決**。

**碼證**: `handoffs/reconcile/20260805-govb0-spec-r2/synth.md` E-10 段（≥50／≥3 session／不得宣稱完工）；SPEC Task 3.3 `:342-347` 無 ≥50、無 ≥3 session、無「不得宣稱完工」。`grep ≥50 docs/GOVB0_FRICTION_SPEC.md` → 0 行。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MAJOR] 信心度=High。`COMPOSER-R2-P1-04` 仍 NOT-CLOSED。修法：Task 3.3 定稿規則與 synth E-10 逐字對齊；TODO §0 引用同一門檻。

---

## COMPOSER-R3-P1-02

**斷言**: 契約 **1b 跨行剝引號**為主委 R3 新增且 b15probe6 已驗，但 Task 2.1 驗收**未列具名語料**，實作者可能只抄原型③（不含 1b）即過 Task 2.1。

**碼證**: Task 2.0 `:163-168` 1b；`bash handoffs/govb0_probes/b15probe6.sh` → commit 多行 TN 須 ALLOW。Task 2.1 `:197-205` 列 eval／`-c` 等，**無** b15probe6 四條。原型③（b15probe5）**未測**多行引號 TN。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MAJOR] 信心度=High。修法：Task 2.1 增四條狀態斷言對齊 b15probe6；納入語料 B。

---

## COMPOSER-R3-P1-03

**斷言**: 序列化拒絕後，逾時 `failed`（attempt 檔殘留、`<out>` 不存在）時**同 `<out>` 重派**的生命週期未寫，可能誤拒合法重派或永久鎖死路徑。

**碼證**: Task 3.2 `:320-324` 拒絕「進行中」第二 attempt；Task 3.3 `:352-353` 逾時後 attempt 殘留；**無**「terminal `failed` 後釋放鎖／允許重派」句。邊界 `:329` SIGKILL 亦未寫鎖釋放。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MAJOR] 信心度=Medium。修法：明文 `result_state=failed`／逾時後 attempt registry 進入 terminal、允許同 `<out>` 新 attempt；並發仍拒絕。

---

## COMPOSER-R3-P2-01

**斷言**: Task 2.0 驗收稱契約「**10 項**」，但條目含 **1** 與 **1b** 及 2–10，計數與 `票 B-17` 漂移同型，TODO 生成易漏項。

**碼證**: `:161-178` 列 1、1b、2–10（11 個編號點）；`:183`「契約 **10 項**」；`:185`「10 個 mutation」。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#c4448d67356f

[MINOR] 信心度=High。修法：統一計數（1b 併入 1 或改稱 11 項／mutation 數）。

---

## COMPOSER-R3-P2-02

**斷言**: `票 B-36`（群集表盲點）應記為 MAJOR 治理債，產出端預列 ID 優於僅靠委員人工發現。

**碼證**: R2 synth `:37-41` 實證 `COMPOSER-R2-P1-01` 漏群集表、`completeness --lock` rc=0；brief Q5 待 R3 裁定。

**來源摘要**: handoffs/reconcile/20260805-govb0-spec-r2/synth.md#8b8d0a948782

[MINOR] 信心度=High。建議併入 `票 B-13` 或開 `票 B-36`；`reconcile_build.sh` 預列全部 ID。

---

ASSUMPTIONS_VERIFIED: template_check rc=0；Task count=11=§V；b15probe5 26/26；b15probe6 4/4；b15probe4 fail-open 現行 gate；SPEC sha256=c4448d67356ff0fd80a99491754986dc98079700969a6220896511617e0ffc57
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS rc=0；`grep -c '^\*\*Task '` → 11；`bash handoffs/govb0_probes/b15probe{4,5,6}.sh` rc=0；`grep -c ≥50 SPEC` → 0
FAILURES_SEEN: none（探針預期 BLOCK/ALLOW 為證據）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查禁改碼）

產出檔: handoffs/20260805-govb0-spec-r3-composer.md
/tmp 清理: 無 `govb0*` 工作目錄；保留 `claude-501`

STATUS: DONE

## 戳記



