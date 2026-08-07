#!/usr/bin/env bash
# govb1_selfcheck.sh — 第 1 批 TODO 的**強制聚合自檢 runner**。
#
# 為何存在（2026-08-07，斷路器作動後由三家委員裁定；
#   收斂檔 handoffs/reconcile/20260807-govb1-x-consult-r4/synth.md D-3）：
#   主委連兩輪（R7→20、R8→19 findings）修補都留下淺層閉合。三家一致證偽
#   「批次太大」假設（同 13 Task 的 SPEC 已收斂 14→9→2→0），
#   主因是**自檢流程可跳過且失敗不 fail-closed**：
#     · 主委在 TODO 附錄 B.2 寫了三條掃描命令，**只跑了①就宣告 13/13 通過**
#     · 那些 awk **只列印不 exit** ⇒ 印出 7 個未達標 Task 仍 rc=0 ⇒ 根本不是 gate
#
# 設計約束（D-3 七條，逐條對應本檔實作；缺一即無效）：
#   1. 檢查清單由 SPEC/TODO **現讀**產生，非手寫            → _expected_check_ids()
#   2. 每個檢查 ID 須有 receipt；缺 receipt ⇒ FAIL          → _run_all() 的 seen 集合比對
#   3. 任一子命令非零 ⇒ 整體 FAIL；**禁管線吞 rc**          → 全程 rc 直接取，禁 `cmd | x` 後讀 $?
#   4. 禁 placeholder（<task>／X／Y／...）                   → CHK-NOPLACEHOLDER
#   5. 集合斷言一律 **set equality**，禁 `> 0` 型弱斷言       → CHK-BEHAVIOR-ROWS 用 == 非 >0
#   6. runner 自身須通過 mutation self-test                  → --self-test
#   7. Task／檢查 ID／receipt 三者數量與內容完全相等          → _run_all() 末段
#
# 用法：
#   bash scripts/govb1_selfcheck.sh              # 跑全部檢查，任一 FAIL ⇒ rc=1
#   bash scripts/govb1_selfcheck.sh --manifest   # 只印機器可讀 manifest（檢查 ID 清單）
#   bash scripts/govb1_selfcheck.sh --self-test  # 突變自證：runner 在該紅時是否真的紅
#
# 憲法：bash 3.2（macOS）；rc 一律直接取，禁經 pipe；每道守衛 || return。
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}" || exit 2

TODO_FILE="${GOVB1_TODO:-docs/GOVB1_INPUT_QUALITY_TODO.md}"
SPEC_FILE="${GOVB1_SPEC:-docs/GOVB1_INPUT_QUALITY_SPEC.md}"
BEHAVIOR_SRC="${GOVB1_BEHAVIOR_SRC:-docs/GOV_DISPATCH_FLOW_FIX_SPEC.md}"

# ---------------------------------------------------------------------------
# 約束 1：檢查清單由現讀產生
#   Task 類檢查：每個 TODO 內的 `### Task N.x` 各產生 3 個檢查 ID
#   全域檢查：固定 5 個（與 Task 數無關）
# ---------------------------------------------------------------------------
_task_ids() {
  LC_ALL=C awk '/^### Task [0-9]+\.[0-9]+ /{print $3}' "${TODO_FILE}"
}

_expected_check_ids() {
  _task_ids | while IFS= read -r t; do
    [ -n "${t}" ] || continue
    printf 'CHK-FENCE-%s\n'   "${t}"
    printf 'CHK-FUNCNAME-%s\n' "${t}"
    printf 'CHK-SCOPE-%s\n'    "${t}"
  done
  printf '%s\n' \
    CHK-BEHAVIOR-ROWS \
    CHK-FIXTURE-NAMES \
    CHK-NOPLACEHOLDER \
    CHK-NOFROZEN-COUNT \
    CHK-TASK-RECEIPT-EQ
}

# ---------------------------------------------------------------------------
# 個別檢查。每個回傳 rc；**不得只列印**。
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 約束 2 的真正落實：**invocation receipt 由檢查函式自己留痕**
#   〔CODEX-R10-P1-06＋COMPOSER-R10-P1-02＋GROK-R10-P1-02：
#    原 `_run_all` 的 expected==seen **比的是同一段 dispatcher 剛寫入的 ID**
#    ⇒ 只證明「dispatcher 把預期 ID 抄了一份」，**不證明每個檢查真的被呼叫過**。〕
#   改為：每個 _chk_* **在自己函式體第一行**寫入 receipt。dispatcher 漏呼叫某檢查時，
#   該 receipt 不會出現 ⇒ set equality 立即失敗。
_receipt() { printf '%s\n' "$1" >> "${_RECEIPT_FILE:-/dev/null}"; }

# 每個 Task 至少一個 ```sh 偽碼 fence
_chk_fence() {   # $1=task
  _receipt "CHK-FENCE-$1"
  # 🔴 視窗**必須**同時在 `### Task`／`### Phase`／`## ` 停止
  #   〔CODEX-R10-P0-01：主委只替 `_chk_scope` 補了停止條件，**本函式沒補**
  #    ⇒ 末個 Task 可吃到附錄的 fence，刪自身偽碼仍 PASS。「原則修了、實例沒修」第 5 次〕
  n="$(LC_ALL=C awk -v want="$1" '
        /^### Task [0-9]+\.[0-9]+ /{if(cur==want) exit; cur=$3; next}
        /^### Phase |^## /{if(cur==want) exit}
        /```sh/{if(cur==want) c++}
        END{print c+0}' "${TODO_FILE}")"
  [ "${n}" -ge 1 ] || { echo "  缺偽碼 fence" >&2; return 1; }
}

# 每個 Task 的「修改」欄須到函式名（含 () 或明示「無」/具名區段）
_chk_funcname() {   # $1=task
  _receipt "CHK-FUNCNAME-$1"
  # 視窗同 _chk_fence（同一 bug 形態，一併補）
  bad="$(LC_ALL=C awk -v want="$1" '
          /^### Task [0-9]+\.[0-9]+ /{if(cur==want) exit; cur=$3; next}
          /^### Phase |^## /{if(cur==want) exit}
          /\*\*修改\*\*：/{
            if (cur==want && $0 !~ /\(\)|案 branch|節|分支|區段|無/) print "BAD"
          }' "${TODO_FILE}")"
  [ -z "${bad}" ] || { echo "  修改欄未到函式名" >&2; return 1; }
}

# 每個 Task 的「檔案三類聯集」須涵蓋其 body 內出現的 repo 路徑
_chk_scope() {   # $1=task
  _receipt "CHK-SCOPE-$1"
  miss="$(LC_ALL=C awk -v want="$1" '
    # 🔴 視窗**必須**同時在下列三種標題停止，否則 Task 0.1 會吃進「Phase N 測試」段、
    #    末個 Task（4.3）會吃進整份附錄 ⇒ 誤報「檔案欄未涵蓋」。此為本 runner 初版 bug。
    /^### Task [0-9]+\.[0-9]+ /{
      if (cur==want) exit
      cur=$3; files=""; body=""; infiles=0; next
    }
    /^### Phase |^## /{ if (cur==want) exit }
    cur==want {
      # 🔴 起始 pattern **不得**寫成「修改檔案｜」——實際行是 `- **修改檔案**｜**修改**：`，
      #    中間有 `**`，字面「修改檔案｜」不存在 ⇒ infiles 永遠為 0 ⇒ 檔案欄從未納入
      #    ⇒ 13 個 CHK-SCOPE 全紅。此為本 runner 初版的實際 bug，具名記錄。
      if ($0 ~ /修改檔案/) infiles=1
      else if ($0 ~ /^- (\*\*)?(不可做|邊界|風險緩解|存活至|覆蓋風險|驗證|實作要點)/) infiles=0
      if (infiles) files = files " " $0; else body = body " " $0
    }
    END{
      # 🔴 **exact set membership，禁 substring containment**
      #   〔CODEX-R10-P0-03＋COMPOSER-R10-P1-05＋GROK-R10-P1-05 三家獨立命中〕
      #   原用 index(files,p)==0：宣告較長路徑會讓**未宣告的較短路徑**假 PASS
      #   （例：宣告 scripts/gate_check.sh ⇒ 未宣告的 scripts/gate.sh 也被當成已涵蓋）。
      m=split(files, fa, /[^-A-Za-z0-9_.\/]+/)
      for (j=1;j<=m;j++) if (fa[j] ~ /^(scripts|tests|docs|templates|handoffs)\//) decl[fa[j]]=1
      n=split(body, a, /[^-A-Za-z0-9_.\/]+/)
      for (i=1;i<=n;i++) {
        p=a[i]
        if (p !~ /^(scripts|tests|docs|templates|handoffs)\//) continue
        if (p ~ /\/$/) continue
        if (!(p in decl)) print p
      }
    }' "${TODO_FILE}")"
  [ -z "${miss}" ] || { printf '  檔案欄未涵蓋: %s\n' "${miss}" >&2; return 1; }
}

# 約束 5：行為表列數 **set equality**，禁 `> 0`
_chk_behavior_rows() {
  _receipt "CHK-BEHAVIOR-ROWS"
  # 🔴 **由標題錨點現讀，禁硬綁行號**
  #   〔CODEX-R10-P0-04＋COMPOSER-R10-P1-04＋GROK-R10-P1-04：原寫 NR>=141&&NR<=163，
  #    非結構錨點 ⇒ 表頭外移或表下延長時，對**舊窗口**做 hit==all 而 **PASS（假綠）**〕
  #   錨點＝「行為表（＝驗收契約」起，至該表結束（連續 `|` 表格行終止）止。
  _rows_all="$(LC_ALL=C awk '
      /行為表（＝驗收契約/{f=1; next}
      f && /^[[:space:]]*\|/{
        seen=1
        if ($0 ~ /^[[:space:]]*\|[[:space:]]*heading/) next          # 表頭
        if ($0 ~ /^[[:space:]]*\|[-:| ]*\|[[:space:]]*$/) next       # 分隔列
        n++; next
      }
      f && seen && $0 !~ /^[[:space:]]*\|/{exit}
      END{print n+0}' "${BEHAVIOR_SRC}")"
  _rows_hit="$(LC_ALL=C awk '
      /行為表（＝驗收契約/{f=1; next}
      f && /^[[:space:]]*\|/{ if ($0 ~ /^[[:space:]]*\| `.*` \| (\*\*)?rc==/) n++; seen=1; next}
      f && seen && $0 !~ /^[[:space:]]*\|/{exit}
      END{print n+0}' "${BEHAVIOR_SRC}")"
  all="${_rows_all}"; hit="${_rows_hit}"
  [ "${all}" -gt 0 ] || { echo "  行為表錨點抽取為空（標題已改？）" >&2; return 1; }
  [ "${hit}" -eq "${all}" ] || {
    echo "  行為表 pattern 部分命中: ${hit}/${all}（須相等，禁 >0 弱斷言）" >&2; return 1; }
}

# fixture 逐名存在（非數量）
_chk_fixture_names() {
  _receipt "CHK-FIXTURE-NAMES"
  names="$(LC_ALL=C awk '/fixture 清單/{f=1} f&&/^```/{n++; if(n==2) exit} f' "${SPEC_FILE}" \
           | LC_ALL=C grep -oE '[a-z0-9_]+\.(md|json)|factkey_[a-z]+/' | LC_ALL=C sort -u)"
  [ -n "${names}" ] || { echo "  SPEC fixture 清單抽取為空" >&2; return 1; }
  # 🔴 **禁用變數名 `rc`**：bash 函式預設共用作用域，此處若用 `rc` 會**覆蓋 _run_all 的累積失敗**
  #    ⇒ runner 印出 FAIL 卻回 rc=0（本檔初版實際發生：13 FAIL 卻 rc=0）。
  #    此即本 runner 存在之目的的同型錯誤，具名記錄於此以防再犯。
  _fx_rc=0
  for n in ${names}; do
    LC_ALL=C grep -q "fixtures/govb1/${n%/}" "${TODO_FILE}" || {
      echo "  TODO 未提及 fixture: ${n}" >&2; _fx_rc=1; }
  done
  return "${_fx_rc}"
}

# 約束 4：禁 placeholder
_chk_noplaceholder() {
  _receipt "CHK-NOPLACEHOLDER"
  hit="$(LC_ALL=C grep -nE '<task>|<該檔>|--task-id T |--spec X |--reconcile Y |ASSERT \.\.\.' "${TODO_FILE}" || true)"
  [ -z "${hit}" ] || { printf '  含 placeholder:\n%s\n' "${hit}" >&2; return 1; }
}

# 禁凍結分母（〔歷史〕標記行豁免＝已知殘留，見 TODO 附錄 B.4）
_chk_nofrozen_count() {
  _receipt "CHK-NOFROZEN-COUNT"
  # 🔴 除中文尾綴外，**須含比例型分母** `N/N`
  #   〔CODEX-R10-P0-02 實測：`13/13`／`8/8`／`6/6`／`5/5`／`1/1` 共 12 命中，
  #    原 regex 全數放行——而那正是主委在附錄 A 手寫的覆蓋數，即本 runner 要治的病〕
  #   誠實邊界：`〔歷史〕` 豁免仍為**紀律型旁路**（S6-4 已裁定），未解，具名保留。
  #   🔴 判準**精確化而非加豁免清單**（後者即 `票 B-23` 的黑名單陷阱）：
  #     只抓**分子分母相同**的 `N/N`——那才是「N 個中的 N 個」型**覆蓋宣稱**。
  #     `3.8416/103.8416`（Wilson 算式）、`81/193`（歷史觀測）、`1/5`（段號）、
  #     `1/2`（Phase 編號）分子分母不同 ⇒ 非覆蓋宣稱，**結構上排除，不需豁免**。
  hit="$(LC_ALL=C awk '
      /〔歷史〕/{next}
      /[0-9]+[[:space:]]*(份|列|個 fixture)/{printf "%d:%s\n", NR, $0; next}
      # 🔴 **結構判準，非詞表**〔`CODEX-R11-P0-01` [BLOCKING]：語境詞是**有限 lexical allowlist**，
      #   `完成驗證 13/13` 等未列詞可放行；主委實測複驗成立。codex 正解：
      #   「由結構化、現讀的契約/集合導出，**不能繼續擴充語境詞**」〕
      #   ⇒ 改為：`N/N` 同數且**不在 code fence 內** 即判凍結覆蓋宣稱。
      #   段號 `[gov_check] 5/5` 位於 ```sh 區塊內 ⇒ **結構上排除，不需詞表**。
      /^[[:space:]]*```/ { infence = !infence; next }
      !infence {
        s=$0
        while (match(s, /[0-9]+\/[0-9]+/)) {
          t=substr(s, RSTART, RLENGTH); split(t, p, "/")
          if (p[1]==p[2]) { printf "%d:%s\n", NR, $0; break }
          s=substr(s, RSTART+RLENGTH)
        }
      }' "${TODO_FILE}" || true)"
  [ -z "${hit}" ] || { printf '  含凍結分母:\n%s\n' "${hit}" >&2; return 1; }
}

# 約束 7：Task 數 × 3 + 全域 5 == 檢查 ID 數（機器比對，禁手寫）
_chk_task_receipt_eq() {
  _receipt "CHK-TASK-RECEIPT-EQ"
  nt="$(_task_ids | LC_ALL=C grep -c .)"
  nid="$(_expected_check_ids | LC_ALL=C grep -c .)"
  exp=$(( nt * 3 + 5 ))
  [ "${nid}" -eq "${exp}" ] || {
    echo "  檢查 ID 數 ${nid} != Task ${nt} × 3 + 5 = ${exp}" >&2; return 1; }
}

# ---------------------------------------------------------------------------
# 主流程：約束 2（缺 receipt ⇒ FAIL）＋ 約束 3（任一非零 ⇒ 整體 FAIL）
# ---------------------------------------------------------------------------
_run_all() {
  rc=0
  # 🔴 `seen_file` 由**檢查函式自己**經 `_receipt` 寫入，dispatcher **不得**代寫
  #   ——代寫即回到「只證明 dispatcher 抄了一份」的循環論證。
  seen_file="$(mktemp)"
  : > "${seen_file}"
  _RECEIPT_FILE="${seen_file}"

  for t in $(_task_ids); do
    for k in FENCE FUNCNAME SCOPE; do
      id="CHK-${k}-${t}"
      case "${k}" in
        FENCE)    _chk_fence "${t}" ;;
        FUNCNAME) _chk_funcname "${t}" ;;
        SCOPE)    _chk_scope "${t}" ;;
      esac
      sub=$?                                   # 約束 3：rc 直接取，不經 pipe
      if [ "${sub}" -eq 0 ]; then echo "PASS ${id}"; else echo "FAIL ${id}" >&2; rc=1; _printed_fail=$(( ${_printed_fail:-0} + 1 )); fi
      # （receipt 由 _chk_* 自己寫，此處**刻意不代寫**）
    done
  done

  for id in CHK-BEHAVIOR-ROWS CHK-FIXTURE-NAMES CHK-NOPLACEHOLDER CHK-NOFROZEN-COUNT CHK-TASK-RECEIPT-EQ; do
    case "${id}" in
      CHK-BEHAVIOR-ROWS)   _chk_behavior_rows ;;
      CHK-FIXTURE-NAMES)   _chk_fixture_names ;;
      CHK-NOPLACEHOLDER)   _chk_noplaceholder ;;
      CHK-NOFROZEN-COUNT)  _chk_nofrozen_count ;;
      CHK-TASK-RECEIPT-EQ) _chk_task_receipt_eq ;;
    esac
    sub=$?
    if [ "${sub}" -eq 0 ]; then echo "PASS ${id}"; else echo "FAIL ${id}" >&2; rc=1; _printed_fail=$(( ${_printed_fail:-0} + 1 )); fi
    # （receipt 由 _chk_* 自己寫，此處**刻意不代寫**）
  done

  # 約束 2＋7：expected 與 seen 須 **set equality**
  exp_file="$(mktemp)"
  _expected_check_ids | LC_ALL=C sort > "${exp_file}"
  LC_ALL=C sort -o "${seen_file}" "${seen_file}"
  if ! diff -q "${exp_file}" "${seen_file}" >/dev/null 2>&1; then
    echo "FAIL 檢查覆蓋不完整（expected != seen）：" >&2
    diff "${exp_file}" "${seen_file}" >&2
    rc=1
  fi
  rm -f "${exp_file}" "${seen_file}"

  # 🔴 **不變式守衛**：印了 FAIL 就一定要非零離開。
  #    出生事故：`_chk_fixture_names` 曾用同名變數 `rc`，覆蓋累積值 ⇒ 13 FAIL 卻 rc=0。
  #    本守衛使同型錯誤（任何子函式誤用 `rc`）**當場現形**，而非靜默假綠。
  if [ "${_printed_fail:-0}" -ne 0 ] && [ "${rc}" -eq 0 ]; then
    echo "FAIL INVARIANT: 印出 ${_printed_fail} 個 FAIL 但 rc=0（累積值被覆蓋）" >&2
    rc=1
  fi
  # 🔴🔴 **覆蓋邊界宣告（U-2）——本 runner 全綠 ≠ TODO 正確**
  #   〔COMPOSER-R10-P0-02＋GROK-R10-P0-02：主委於 brief Q2 自陳「最沒把握」，兩家證實成立〕
  #   本 runner **只覆蓋深度紅線的機械子集**（偽碼 fence／函式名／檔案欄涵蓋／
  #   placeholder／凍結分母／行為表列數／fixture 逐名）。
  #   **不覆蓋**：oracle 是否可執行、驗收條件是否可證偽、Batch Gate 是否閉合、
  #   偽碼是否真能實作、mutation 設計是否有效——**這些 runner 根本不讀**。
  #   ⇒ **禁止把 rc=0 解讀為「TODO 已修好」或「委員 findings 已閉合」。**
  cat >&2 <<'BOUNDARY'
--- 覆蓋邊界（每次執行皆印，禁移除）---
本 runner 只驗機械可判的深度紅線子集。rc=0 **不代表** TODO 正確、
亦**不代表**委員 findings 已閉合——oracle 品質、驗收可證偽性、Batch Gate 閉合性
均在覆蓋範圍外，須由委員審查判定。
BOUNDARY

  return "${rc}"
}

# ---------------------------------------------------------------------------
# 約束 6：突變自證 —— runner 在該紅時是否真的紅
#   每個突變都在**隔離副本**上做，不動 repo。
# ---------------------------------------------------------------------------
_self_test() {
  tmpd="$(mktemp -d)"
  fail=0

  # 🔴 **差分測試，非「突變後也紅」**
  #   基線目前為紅（TODO 尚有 11 個相異問題）。若只斷言「突變後 rc!=0」，
  #   **基線紅時任何突變都紅 ⇒ 該自證恆真、證明不了任何事**——本檔初版即犯此錯，
  #   且首個突變的 sed 實際失敗（bad flag）卻仍報 PASS。
  #   ⇒ 改為**逐 ID 差分**：該突變對應的檢查 ID 必須由 **PASS 轉 FAIL**；
  #      基線該 ID 若已是 FAIL ⇒ 判 **INCONCLUSIVE**（計為不通過，不得當成功）。
  base_out="${tmpd}/base.txt"
  bash "$0" > "${base_out}" 2>&1

  _state() {   # $1=輸出檔 $2=檢查ID -> PASS|FAIL|ABSENT
    if LC_ALL=C grep -qx "PASS $2" "$1"; then echo PASS
    elif LC_ALL=C grep -qx "FAIL $2" "$1"; then echo FAIL
    else echo ABSENT; fi
  }

  _probe() {   # $1=描述 $2=突變檔 $3=應轉紅的檢查ID
    before="$(_state "${base_out}" "$3")"
    if [ "${before}" != "PASS" ]; then
      echo "SELF-TEST INCONCLUSIVE: 「$1」——基線 $3 已是 ${before}，無法證明突變有效" >&2
      fail=1; return
    fi
    GOVB1_TODO="$2" bash "$0" > "${tmpd}/mut.txt" 2>&1
    after="$(_state "${tmpd}/mut.txt" "$3")"
    if [ "${after}" = "FAIL" ]; then
      echo "SELF-TEST PASS: 「$1」→ $3 由 PASS 轉 FAIL"
    else
      echo "SELF-TEST FAIL: 「$1」→ $3 仍為 ${after}（檢查空轉）" >&2; fail=1
    fi
  }

  # 突變 A：插入 placeholder ⇒ CHK-NOPLACEHOLDER 應轉紅
  { cat "${TODO_FILE}"; printf '\n- 驗證：ASSERT ...\n'; } > "${tmpd}/mutA.md"
  _probe '插入 placeholder' "${tmpd}/mutA.md" CHK-NOPLACEHOLDER

  # 突變 B：插入凍結分母 ⇒ CHK-NOFROZEN-COUNT 應轉紅
  { cat "${TODO_FILE}"; printf '\n本批共 14 個 fixture。\n'; } > "${tmpd}/mutB.md"
  _probe '插入凍結分母' "${tmpd}/mutB.md" CHK-NOFROZEN-COUNT

  # 突變 C：改壞行為表 pattern 的來源行號 ⇒ CHK-BEHAVIOR-ROWS 應轉紅
  #   （用 env 指向一個沒有該表的檔，模擬 pattern 失效）
  before_c="$(_state "${base_out}" CHK-BEHAVIOR-ROWS)"
  if [ "${before_c}" = "PASS" ]; then
    GOVB1_BEHAVIOR_SRC="${TODO_FILE}" bash "$0" > "${tmpd}/mutC.txt" 2>&1
    if [ "$(_state "${tmpd}/mutC.txt" CHK-BEHAVIOR-ROWS)" = "FAIL" ]; then
      echo "SELF-TEST PASS: 「行為表來源換成無該表之檔」→ CHK-BEHAVIOR-ROWS 由 PASS 轉 FAIL"
    else
      echo "SELF-TEST FAIL: 「行為表來源換檔」→ CHK-BEHAVIOR-ROWS 未轉紅（檢查空轉）" >&2; fail=1
    fi
  else
    echo "SELF-TEST INCONCLUSIVE: 基線 CHK-BEHAVIOR-ROWS 已是 ${before_c}" >&2; fail=1
  fi

  # 🔴 **per-Task 三類檢查的突變**〔CODEX-R10-P1-06＋COMPOSER-R10-P1-01＋GROK-R10-P1-01：
  #    原自證只覆蓋 3 個全域 CHK，**13×3 個 per-Task 檢查零突變** ⇒ 同型 rc 覆蓋 bug 可靜默復發〕

  # 突變 D：刪掉 Task 4.3 的偽碼 fence ⇒ CHK-FENCE-4.3 應轉紅
  LC_ALL=C awk '
    /^### Task 4\.3 /{inT=1} /^### Phase |^## /{if(inT) inT=0}
    { if (inT && $0 ~ /```sh/) sub(/```sh/, "```txt"); print }' "${TODO_FILE}" > "${tmpd}/mutD.md"
  _probe '刪 Task 4.3 的偽碼 fence' "${tmpd}/mutD.md" CHK-FENCE-4.3

  # 突變 E：把 Task 2.2 的修改欄函式名拿掉 ⇒ CHK-FUNCNAME-2.2 應轉紅
  LC_ALL=C sed 's|`scripts/gov_check.sh`（新增 `_gov_check_factkey()`；段號統一為 `n/5`）|`scripts/gov_check.sh`|' \
      "${TODO_FILE}" > "${tmpd}/mutE.md"
  _probe '移除 Task 2.2 修改欄的函式名' "${tmpd}/mutE.md" CHK-FUNCNAME-2.2

  # 突變 F：在 Task 3.2 body 插入一個未宣告路徑 ⇒ CHK-SCOPE-3.2 應轉紅
  LC_ALL=C awk '
    /^### Task 3\.2 /{print; print "- 備註：另參考 `scripts/audit_append.sh` 的作法。"; next}
    {print}' "${TODO_FILE}" > "${tmpd}/mutF.md"
  _probe '在 Task 3.2 插入未宣告路徑' "${tmpd}/mutF.md" CHK-SCOPE-3.2

  rm -rf "${tmpd}"
  return "${fail}"
}

case "${1:-}" in
  --manifest)  _expected_check_ids; exit 0 ;;
  --self-test) _self_test; exit $? ;;
  "")          _run_all; exit $? ;;
  *)           echo "用法: bash scripts/govb1_selfcheck.sh [--manifest|--self-test]" >&2; exit 2 ;;
esac
