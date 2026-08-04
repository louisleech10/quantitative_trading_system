#!/usr/bin/env bash
# cx_run.sh — 委員派工安全模板(治本;取代手搓 inline prompt)。
# 根除三反覆錯:①反引號被 shell 當命令替換 ②`&` detach 掉 harness 通知 ③PATH 127。
#
# 用法(Claude 一律經此派委員,勿再手搓 codex/grok/cursor-agent 命令列):
#   ROUND_ID=<uuid> bash scripts/cx_run.sh <family> <brief_path> <output_path> [effort]
#   family ∈ {codex, grok, composer}
#   brief_path : repo 內指示檔(prompt 全文放這;可自由用反引號,它被讀非 shell 插值)
#   output_path: 委員產出寫到這(handoffs/*.md)
#   effort     : codex only, 預設 xhigh
#   ROUND_ID   : 必填（由 committee_run.sh 開債後注入）；直呼亦須帶合法 round
#
# 設計:命令列給委員的 prompt 是**固定極簡模板**「讀 <brief> 照做, 家族名=X, 產出寫 <out>」——
#   無反引號/無 $/無特殊字元 → 引號陷阱不可能發生。絕對路徑寫死。腳本本身不加 `&`;
#   Claude 用 Bash run_in_background:true 背景執行本腳本即可(勿在呼叫本腳本時加 `&`)。
#
# P1-6 Task 1.3：CLI 前後做 round 六道 fail-closed 前置；結束後寫 committee_family_result。
#   不得把 CLI 執行放進 audit 鎖臨界區。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"

fam="${1:-}"; brief="${2:-}"; out="${3:-}"; effort="${4:-xhigh}"
[ -n "${fam}" ] && [ -n "${brief}" ] && [ -n "${out}" ] || {
  echo "用法: bash scripts/cx_run.sh <codex|grok|composer> <brief_path> <output_path> [effort]"; exit 2; }
[ -f "${brief}" ] || { echo "ERROR: brief 檔不存在: ${brief}"; exit 2; }

# ---------------------------------------------------------------------------
# brief 合規閘 + stamp-target 驗證：**實作已抽到 scripts/brief_conformance_check.sh**
#   （GOV-DOC-CHECK-AT-WRITE，2026-08-02）。本處只呼叫，不重列邏輯。
#
# 為何抽出去：同一份檢查現在有兩個呼叫點——①本處（派工前硬擋）②doc_format_precheck.sh
#   （PostToolUse hook，寫完當下就報）。**複製一份到 hook＝第二真相源**，必然漂移。
# 為何用 --emit 檔而非 $() 捕獲：被抽出的區塊有一半錯誤訊息走 stdout（brief-kind 段），
#   用 $() 捕獲會把那些訊息吃掉，使用者看不到失敗原因；且既有測試對 stdout/stderr 分別斷言。
# 為何用重導而非 $()：$() 會建子 shell（GOV-STAMP-TASKID-INJECT 踩過，export 傳不出去）。
# ---------------------------------------------------------------------------
_bc_kv="$(mktemp)"
# ⚠️ **本腳本只准有這一個 EXIT trap**：bash 的 `trap ... EXIT` 是覆寫不是疊加，
#    第二個 trap 會讓第一個管的暫存檔洩漏。`_taskid_file`（GOV-STAMP-TASKID-INJECT，
#    在 _assert_round_preconditions 內建立）一併在此收，故先宣告為空值供 set -u。
_taskid_file=""
trap 'rm -f "${_bc_kv}" ${_taskid_file:+"${_taskid_file}"}' EXIT
bash "${SCRIPT_DIR}/brief_conformance_check.sh" "${brief}" --emit "${_bc_kv}" || exit $?
_bk="$(sed -n '1p' "${_bc_kv}")"
stamp_target="$(sed -n '2p' "${_bc_kv}")"

# ---------------------------------------------------------------------------
# 角色閘(2026-07-29 使用者定;防「Claude 憑腦中模型選家族」)
# 事故:2026-07-24 與 2026-07-29 連續兩次,把實作派給 reviewer、把 implementer 排進
#   code review(違反實作者不自審)。**兩次 ORCH §1 與記憶檔都寫對了**——散文規則擋不住,
#   故做成閘門。角色 SoT = scripts/governance_roles.json,**只有使用者可改**。
# 規則:impl → 家族須 == implementer。**implementer_backup 不自動放行**(僅供錯誤訊息提示);
#      切換實作端一律由使用者改 SoT(bash scripts/set_roles.sh <family>),不是 Claude 選備援。
#      (CODEX-R5-P1-02:本註解原寫「或 implementer_backup」,與下方程式碼及 SoT 相反)
#      review → 家族【不得】是 implementer(實作者不自審);closure/stamp/consult 不限(三家全員)
# fail-closed:SoT 缺檔/壞 JSON/缺鍵 → 拒派。
# ---------------------------------------------------------------------------
_ROLES="$(dirname "$0")/governance_roles.json"
# ⚠️ 家族不在 SoT 時【跳過角色閘】,交給檔尾 dispatch case 的 `*)` 分支去報錯。
#    理由(2026-07-29 實測):角色閘若搶先判非法家族,會把 `notafamily` 報成「角色不符」——
#    既誤導,又弄壞 test_impl_kind_not_required_to_have_finding_clauses。
#    另:**不得**在此另寫一份家族清單(憲法禁寫死;且會搶走 test_consumer_family_list_matches_sot
#    釘選的那一行,導致抽出空集合誤判漂移)。故用 SoT 函式庫判定,不列清單。
#    ⚠️ 連【註解】都不可出現該測試釘選的字樣——起草者已因此踩坑兩次(訊息一次、註解一次)。
. "$(dirname "$0")/governance_families.sh" 2>/dev/null || true
_KNOWN_FAM="$(families_get review_families '|' 2>/dev/null || echo '')"
_fam_known=0
[ -n "${_KNOWN_FAM}" ] && printf '%s' "${fam}" | grep -qE "^(${_KNOWN_FAM})$" && _fam_known=1

if [ "${_fam_known}" = "1" ] && { [ "${_bk}" = "impl" ] || [ "${_bk}" = "review" ]; }; then
  [ -f "${_ROLES}" ] || { echo "ERROR: 角色 SoT 缺檔: ${_ROLES}(fail-closed)"; exit 2; }
  _impl="$(python3 -c "import json,sys;d=json.load(open('${_ROLES}'));print(d['implementer'])" 2>/dev/null)"
  _bkup="$(python3 -c "import json,sys;d=json.load(open('${_ROLES}'));print(d.get('implementer_backup',''))" 2>/dev/null)"
  _revs="$(python3 -c "import json,sys;d=json.load(open('${_ROLES}'));print(' '.join(d['reviewers']))" 2>/dev/null)"
  [ -n "${_impl}" ] && [ -n "${_revs}" ] || { echo "ERROR: 角色 SoT 解析失敗或缺鍵(fail-closed): ${_ROLES}"; exit 2; }

  # ⚠️ implementer_backup 【不】自動放行(僅供錯誤訊息提示)。
  #    使用者原話:「Grok 或 Codex 實作是我指定,你只能遵守,不能變更,我會根據額度調配」
  #    ⇒ 切換實作端 = 使用者改 SoT 的 implementer 欄,不是由 Claude 選備援。
  #    (本 oracle 首跑即抓到:若允許 backup,等同放行 2026-07-29 我犯的那個錯)
  if [ "${_bk}" = "impl" ] && [ "${fam}" != "${_impl}" ]; then
    echo "ERROR: 角色不符 — brief-kind=impl 的實作端須為 '${_impl}',但收到 '${fam}'。"
    echo "  角色 SoT: ${_ROLES}(**只有使用者可改**;Claude 不得自行變更,備援 '${_bkup}' 亦不自動放行)"
    echo "  若使用者本次指定改由 '${fam}' 實作,請【請使用者先更新該檔的 implementer 欄】再派工。"
    exit 2
  fi
  if [ "${_bk}" = "review" ] && [ "${fam}" = "${_impl}" ]; then
    echo "ERROR: 角色不符 — '${fam}' 是現行 implementer,不得擔任 code review(實作者不自審)。"
    echo "  現行 reviewers: ${_revs}　角色 SoT: ${_ROLES}"
    exit 2
  fi
fi

case "${out}" in handoffs/*) : ;; *) echo "ERROR: output 須在 handoffs/: ${out}"; exit 2 ;; esac

# ---------------------------------------------------------------------------
# Task 1.3 — 六道 fail-closed 前置（僅合法家族在 dispatch 前執行）
# ① ROUND_ID 已設
# ② audit 有對應 committee_round_open
# ③ 該家族在該輪 participants
# ④ 產出路徑與 expected_outputs 登記一致
# ⑤ 本次 brief sha256 == 開債時 brief_sha256
# ⑥ 該 (round, family) 最新 result_state 不是 success
# ---------------------------------------------------------------------------
_resolve_debt_audit() {
  # 與 audit_append.sh 同契約：DEBT_AUDIT_OVERRIDE 須綁 harness
  if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
    if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
      echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
      return 1
    fi
    printf '%s\n' "${DEBT_AUDIT_OVERRIDE}"
    return 0
  fi
  python3 - "${SCRIPT_DIR}/audit_events.json" "${REPO}" <<'PY'
import json, os, sys
reg_path, repo = sys.argv[1], sys.argv[2]
try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(1)
rel = reg.get("audit_log_path")
if not isinstance(rel, str) or not rel:
    print("ERROR: registry 缺 audit_log_path", file=sys.stderr)
    sys.exit(1)
print(os.path.join(repo, rel))
PY
}

_assert_round_preconditions() {
  # 家族名由 $1 直取（呼叫端傳 fam），不得從路徑推導
  local family="$1"
  local brief_path="$2"
  local output_path="$3"

  if [ -z "${ROUND_ID:-}" ]; then
    echo "ERROR: ROUND_ID 未設（須由 committee_run 開債後注入，或直呼時帶合法 round）" >&2
    return 1
  fi

  local audit_path
  audit_path="$(_resolve_debt_audit)" || return 1

  # 讀 audit、驗六道；audit 不存在 → 建立空檔（邊界：建立而非崩潰），再判 round 不存在
  ROUND_ID="${ROUND_ID}" \
  BRIEF_PATH="${brief_path}" \
  OUTPUT_PATH="${output_path}" \
  FAMILY="${family}" \
  AUDIT_PATH="${audit_path}" \
  python3 <<'PY'
import hashlib
import json
import os
import re
import sys
from pathlib import Path

round_id = os.environ["ROUND_ID"]
family = os.environ["FAMILY"]
brief_path = os.environ["BRIEF_PATH"]
output_path = os.environ["OUTPUT_PATH"]
audit_path = Path(os.environ["AUDIT_PATH"])

# 邊界：audit 不存在 → 建立而非崩潰
audit_path.parent.mkdir(parents=True, exist_ok=True)
if not audit_path.exists():
    audit_path.touch()

def iter_events():
    try:
        raw = audit_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: 讀 audit 失敗: {exc}", file=sys.stderr)
        sys.exit(1)
    for line in raw.splitlines():
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            # 與 audit_append.sh 一致：以 { 開頭但壞 JSON → fail-closed（不得 skip）
            # 必須在 CLI 啟動前擋下，否則會留下 output 卻永遠寫不進 result
            print("ERROR: audit 含無法解析的 JSON 行", file=sys.stderr)
            sys.exit(1)
        if isinstance(rec, dict):
            yield rec

opens = [r for r in iter_events() if r.get("event") == "committee_round_open" and r.get("round_id") == round_id]
if not opens:
    print(f"ERROR: audit 無對應 committee_round_open（round_id={round_id}）", file=sys.stderr)
    sys.exit(1)
if len(opens) > 1:
    # 不隱含選取；開債端應保證唯一，此處 fail-closed
    print(f"ERROR: round_id 對應多筆 committee_round_open（round_id={round_id}）", file=sys.stderr)
    sys.exit(1)
open_ev = opens[0]

participants = open_ev.get("participants") or []
if not isinstance(participants, list) or family not in participants:
    print(f"ERROR: 家族 '{family}' 不在該輪名單 participants={participants!r}", file=sys.stderr)
    sys.exit(1)

expected = open_ev.get("expected_outputs") or {}
if not isinstance(expected, dict):
    print("ERROR: committee_round_open.expected_outputs 非 object", file=sys.stderr)
    sys.exit(1)
reg_out = expected.get(family)
if reg_out is None:
    print(f"ERROR: expected_outputs 未登記家族 '{family}'", file=sys.stderr)
    sys.exit(1)
if str(reg_out) != str(output_path):
    print(
        f"ERROR: 產出路徑與開債登記不一致: got={output_path!r} expected={reg_out!r}",
        file=sys.stderr,
    )
    sys.exit(1)

# brief sha256（raw file bytes，對齊開債端 _brief_sha256）
try:
    brief_bytes = Path(brief_path).read_bytes()
except OSError as exc:
    print(f"ERROR: 讀 brief 失敗: {exc}", file=sys.stderr)
    sys.exit(1)
brief_sha = hashlib.sha256(brief_bytes).hexdigest()
recorded = open_ev.get("brief_sha256") or ""
if brief_sha != recorded:
    print(
        f"ERROR: brief_sha256 與開債記錄不符（換 brief 掛既有 round 已拒）",
        file=sys.stderr,
    )
    sys.exit(1)

# 最新 (round, family) result：取 sequence 最大；無 sequence 則取最後出現
results = [
    r
    for r in iter_events()
    if r.get("event") == "committee_family_result"
    and r.get("round_id") == round_id
    and r.get("family") == family
]
if results:
    def seq_key(r):
        s = r.get("sequence")
        if isinstance(s, int) and not isinstance(s, bool):
            return s
        if isinstance(s, str) and s.isdigit():
            return int(s)
        return -1
    latest = max(results, key=seq_key)
    if latest.get("result_state") == "success":
        print(
            f"ERROR: 家族 '{family}' 在 round {round_id} 最新結果已是 success，拒重派",
            file=sys.stderr,
        )
        sys.exit(1)

# 第⑦道前置：open_ev.task_id 必填且非空（GOV-STAMP-TASKID-INJECT / D-001 §D2）
# 錯誤一律 stderr；stdout 僅在成功時輸出單一 task_id（不得混入錯誤訊息）
task_id = open_ev.get("task_id")
if task_id is None or (isinstance(task_id, str) and task_id == ""):
    print("ERROR: open_ev 缺 task_id 或為空字串（第⑦道前置，拒派）", file=sys.stderr)
    sys.exit(1)
if not isinstance(task_id, str):
    print(f"ERROR: open_ev.task_id 型別非法: {type(task_id).__name__}", file=sys.stderr)
    sys.exit(1)
# 白名單：擋 ERE 來源污染；`.` 等仍合法者於 grep 內插前再逐字跳脫
if re.fullmatch(r"[A-Za-z0-9._-]+", task_id) is None:
    print(
        f"ERROR: open_ev.task_id 不符合白名單 ^[A-Za-z0-9._-]+$（第⑦道前置，拒派）: {task_id!r}",
        file=sys.stderr,
    )
    sys.exit(1)
print(task_id)
sys.exit(0)
PY
}

_compute_output_sha() {
  # success 時呼叫；檔必須存在且非空
  shasum -a 256 "$1" | awk '{print $1}'
}

_emit_family_result() {
  # $1=cli_rc  $2=fmt_rc（可選，預設 0）
  # 家族名直取 $fam；不得從路徑推導。
  # 契約（GOVFLOW Task 2.1 / D-003）：格式檢查須在本函式之前完成；
  #   cli_rc==0 且產出非空 且 fmt_rc!=0 → format-failed + 非空 sha
  #   cli_rc==0 且產出非空 且 fmt_rc==0 → success + 非空 sha
  #   其餘 → failed + 空 sha（audit_append 空 sha 例外僅 failed）
  local cli_rc="$1"
  local fmt_rc="${2:-0}"
  local result_state="failed"
  local out_sha=""
  local attempt_id

  if [ "${cli_rc}" -eq 0 ] 2>/dev/null && [ -s "${out}" ]; then
    out_sha="$(_compute_output_sha "${out}")" || return 1
    if [ "${fmt_rc}" -ne 0 ] 2>/dev/null; then
      result_state="format-failed"
    else
      result_state="success"
    fi
  else
    # failed：output_sha256 填空字串（與 success／format-failed 互斥）
    result_state="failed"
    out_sha=""
  fi

  attempt_id="$(python3 -c 'import uuid; print(uuid.uuid4())')" || return 1

  # 寫入在 CLI 之後；audit_append 自己取鎖——CLI 不在鎖內
  bash "${SCRIPT_DIR}/audit_append.sh" \
    --event committee_family_result \
    --field "round_id=${ROUND_ID}" \
    --field "family=${fam}" \
    --field "attempt_id=${attempt_id}" \
    --field "cli_rc=${cli_rc}" \
    --field "output_path=${out}" \
    --field "output_sha256=${out_sha}" \
    --field "result_state=${result_state}" \
    --field "actor=cx_run" \
    --field "origin_script=cx_run.sh"
}

CODEX="/opt/homebrew/bin/codex"
GROK="/Users/louis/.grok/bin/grok"

# prompt 延後至前置成功並捕獲 task_id 後組建（D-001 §D2 / TODO Task 1.1 改法④）。
# :337 原字串錨點僅標示模板語意，非執行順序；task_id 不得從 env 讀。
prompt=""
task_id=""

# 測試 stub（反 bypass：CX_STUB_MODE 必須綁 GOVERNANCE_TEST_HARNESS=1）
# success=寫非空產出 rc0；fail_rc=CLI 非0 無產出；fail_empty=rc0 但空檔
if [ -n "${CX_STUB_MODE:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "ERROR: CX_STUB_MODE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
  exit 1
fi

# harness-only prompt capture（V1 CLI spy）：僅 GOVERNANCE_TEST_HARNESS=1 時生效
_capture_prompt_if_harness() {
  if [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] && [ -n "${CX_PROMPT_CAPTURE:-}" ]; then
    printf '%s' "${prompt}" > "${CX_PROMPT_CAPTURE}"
  fi
}

# GOV-STAMP-TASKID-INJECT / D-001 §D3 改法⑨：brief-kind=stamp 且三條件成立才 register-output
# 合法 no-op vs 註冊失敗必須機械可分（V13）；皆不改 cx_run rc、不回捲 family_result。
_maybe_register_stamp_output() {
  local cli_rc="$1"
  # 僅 stamp kind
  [ "${_bk}" = "stamp" ] || return 0
  [ -n "${stamp_target}" ] || return 0
  [ -n "${task_id}" ] || return 0

  # 條件①：result_state=success（cli_rc=0 且產出非空）
  if [ "${cli_rc}" -ne 0 ] 2>/dev/null || [ ! -s "${out}" ]; then
    return 0
  fi

  # 條件②：單行同時含 fam / APPROVED / 日期 / task:<task_id> / sha256:<body_hash>
  # reconcile_body_hash.sh rc≠0（缺 ## 戳記 等）→ 條件②不成立 → 合法 no-op
  # stderr 吞掉，不得逸出成 cx_run 錯誤輸出；不得以空字串當 hash 繼續比對
  local body_hash
  body_hash="$(bash "${SCRIPT_DIR}/reconcile_body_hash.sh" "${stamp_target}" 2>/dev/null)" || return 0
  [ -n "${body_hash}" ] || return 0

  # 內插前逐字跳脫 ERE metachar（白名單擋非法來源；跳脫擋白名單內仍合法的 .）
  # 跳脫字元：. * + ? [ ] ( ) { } | ^ $ \
  # fam（SoT）／body_hash（sha256 hex）同樣內插 → 一併跳脫
  local fam_e task_e hash_e
  fam_e="$(printf '%s' "${fam}" | sed -e 's/[][\\.^$*+?(){}|]/\\&/g')"
  task_e="$(printf '%s' "${task_id}" | sed -e 's/[][\\.^$*+?(){}|]/\\&/g')"
  hash_e="$(printf '%s' "${body_hash}" | sed -e 's/[][\\.^$*+?(){}|]/\\&/g')"

  # 單一 grep -E 對同一行一次匹配（明文禁止兩次獨立 grep 取交集）
  # 順序無關：同一行同時錨定 sha256:<hash> 與 task:<id>（兩種合法順序）
  # 採用 alternation 而非兩次檔案級 grep，避免跨行誤配
  if ! grep -qE "^RECONCILE-STAMP:[[:space:]]+${fam_e}[[:space:]]+APPROVED[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}[[:space:]]+(sha256:${hash_e}[[:space:]]+task:${task_e}|task:${task_e}[[:space:]]+sha256:${hash_e})([[:space:]]|$)" "${stamp_target}"; then
    return 0
  fi

  # 條件③：家族名取 ${fam}（$1 直取），已用上方 ${fam}
  if ! bash "${SCRIPT_DIR}/gate.sh" register-output "${task_id}" "${stamp_target}"; then
    # 註冊失敗（與合法 no-op 機械可分）：可辨識錯誤字串、rc 不變、不回捲 family_result
    echo "ERROR: register-output 失敗（待人工補記）task=${task_id} path=${stamp_target}" >&2
  fi
  return 0
}

_write_stub_success_output() {
  # CX_STUB_MODE=success：findings-kind 寫最小合法四欄 finding（裁定採①）；
  # impl/stamp 維持 stub-ok（不誤觸 format 檢查）。
  # 禁止 GOVERNANCE_TEST_HARNESS=1 時跳過格式檢查（SPEC 硬約束）。
  case "${_bk}" in
    review|consult|closure)
      local fam_u
      fam_u="$(printf '%s' "${fam}" | tr '[:lower:]' '[:upper:]')"
      {
        printf '## %s-R1-P2-01\n\n' "${fam_u}"
        printf '**斷言**: CX_STUB_MODE=success harness minimal legal finding\n\n'
        printf '**碼證**: scripts/cx_run.sh CX_STUB_MODE=success\n\n'
        printf '**來源摘要**: handoffs/stub-%s.md#aaaaaaaaaaaa\n\n' "${fam}"
        printf 'stub harness body\n'
      } > "${out}"
      ;;
    *)
      printf 'stub-ok family=%s\n' "${fam}" > "${out}"
      ;;
  esac
}

_run_format_check_if_needed() {
  # $1=cli_rc → stdout 印 fmt_rc（0=合規／跳過；非 0=不合規或 checker 不可用）
  # 只對 findings-kind 且 cli 成功且產出非空跑格式檢查。
  # 🔴 順序契約：本函式必須在 _emit_family_result 之前呼叫。
  # 不用全域／local 跨函式寫回——bash local 對子函式不可見。
  local _cli="$1"
  local _rc=0
  case "${_bk}" in
    review|consult|closure)
      if [ "${_cli}" -eq 0 ] 2>/dev/null && [ -s "${out}" ]; then
        local _cc="${SCRIPT_DIR}/completeness_check.sh"
        # fail-closed：checker 不存在／不可讀／bash 無法執行 → 不得記 success
        if [ ! -f "${_cc}" ] || [ ! -r "${_cc}" ]; then
          echo "ERROR: completeness_check.sh 不存在或不可讀 → fail-closed（不得記 success）" >&2
          _rc=127
        else
          bash "${_cc}" --single "${out}" --family "${fam}" >&2 || _rc=$?
        fi
      fi
      ;;
  esac
  printf '%s' "${_rc}"
}

_run_cli_and_emit() {
  # 前置已過；執行 CLI（或 stub）後寫 result。CLI 不在 audit 鎖內。
  # 契約（SPEC Task 1.3 改法④）：CLI launch failure 仍須寫 failed result 帶 cli_rc，不得靜默 exit。
  # 契約（GOVFLOW Task 2.1）：格式檢查 → emit（含 format-failed）→ 再 exit。
  #   順序是規則本身——audit append-only，success 一旦寫入不可變。
  local cli_rc=0
  local _fmt_rc=0
  _capture_prompt_if_harness
  if [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] && [ -n "${CX_STUB_MODE:-}" ]; then
    case "${CX_STUB_MODE}" in
      success)
        _write_stub_success_output
        cli_rc=0
        ;;
      fail_rc)
        cli_rc="${CX_STUB_RC:-1}"
        ;;
      fail_empty)
        : > "${out}"
        cli_rc=0
        ;;
      *)
        # 未知 stub：仍遵守「格式檢查（此處跳過）→ emit → exit」同一順序
        echo "ERROR: 未知 CX_STUB_MODE=${CX_STUB_MODE}" >&2
        cli_rc=2
        _fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"
        _emit_family_result "${cli_rc}" "${_fmt_rc}" || {
          echo "ERROR: 寫入 committee_family_result 失敗" >&2
          exit 1
        }
        exit "${cli_rc}"
        ;;
    esac
  else
    case "${fam}" in
      codex)
        if [ ! -x "${CODEX}" ]; then
          echo "ERROR: codex 不存在: ${CODEX}" >&2
          cli_rc=2
        else
          "${CODEX}" exec -s workspace-write -m gpt-5.6-luna -c model_reasoning_effort="${effort}" "${prompt}" </dev/null
          cli_rc=$?
        fi
        ;;
      grok)
        if [ ! -x "${GROK}" ]; then
          echo "ERROR: grok 不存在: ${GROK}" >&2
          cli_rc=2
        else
          "${GROK}" -m grok-4.5 --sandbox workspace --always-approve --output-format plain -p "${prompt}"
          cli_rc=$?
        fi
        ;;
      composer)
        if ! command -v cursor-agent >/dev/null 2>&1; then
          echo "ERROR: cursor-agent 不存在（composer CLI）" >&2
          cli_rc=2
        else
          cursor-agent -p --force --output-format text --model composer-2.5 "${prompt}"
          cli_rc=$?
        fi
        ;;
    esac
  fi

  # ---------------------------------------------------------------------------
  # GOVFLOW-B2 / D-003：格式檢查**必須**在 audit append 之前。
  #
  # 病根：舊順序 = emit success → 再 completeness_check → exit 3，
  #   audit append-only ⇒ success 不可變 ⇒ 守衛⑥永久拒重派 ⇒ 只能 abandon。
  # 本 session 主委實踩三次（B0 review／B1 review／R6 grok）。
  #
  # 只對「產 findings 的 brief-kind」檢查（review／consult／closure）。
  # impl／stamp 產出依契約無 canonical finding ID，判準與行為皆不變。
  # 禁止 GOVERNANCE_TEST_HARNESS=1 時跳過格式檢查。
  # ---------------------------------------------------------------------------
  _fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"
  _emit_family_result "${cli_rc}" "${_fmt_rc}" || {
    echo "ERROR: 寫入 committee_family_result 失敗" >&2
    exit 1
  }
  # 改法⑨：emit 之後才嘗試 register-output（不回捲 family_result）
  # stamp kind 不跑格式檢查；format-failed 不會出現在 stamp 路徑
  _maybe_register_stamp_output "${cli_rc}"

  if [ "${_fmt_rc}" -ne 0 ]; then
    echo "[cx_run] ⚠️ ${fam} 產出**格式不合規**（見上）：${out}" >&2
    echo "[cx_run]    audit 已記 result_state=format-failed（可同輪重派；debt_clear 仍拒銷帳）。" >&2
    echo "[cx_run]    請於此時修正或重派，勿等到收集節點才發現。" >&2
    echo "[cx_run] ${fam} done rc=${cli_rc} out=${out}（格式不合規 → exit 3）"
    exit 3
  fi

  echo "[cx_run] ${fam} done rc=${cli_rc} out=${out}"
  exit "${cli_rc}"
}

# 前置成功後捕獲 task_id（stdout），再組 prompt，再跑 CLI
_prepare_and_run() {
  # 捕獲 stdout 為 task_id；錯誤訊息在 stderr，不得混入。
  # 用檔案重導（非 $( )）以免子 shell 吃掉函式內 export 等副作用
  # （test_b3_mutation_round_id_guard 依賴此行為；D-001 §D2 仍以 stdout 回傳 task_id）
  _taskid_file="$(mktemp)"
  # 不在此設 trap：檔頭那個唯一的 EXIT trap 已涵蓋 _taskid_file（trap 是覆寫非疊加）
  _assert_round_preconditions "${fam}" "${brief}" "${out}" > "${_taskid_file}" || exit $?
  task_id="$(cat "${_taskid_file}")"
  # 固定極簡 prompt + task-id 注入句（逐字，D-001 §D2）
  prompt="讀 ${brief} 照其指示做。你的家族名=${fam}。產出寫到 ${out}。收尾清 /tmp workdir(保留 claude-501)。你的 task-id=${task_id}。RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。"
  _run_cli_and_emit
}

case "${fam}" in
  codex)
    _prepare_and_run
    ;;
  grok)
    _prepare_and_run
    ;;
  composer)
    _prepare_and_run
    ;;
  *) echo "ERROR: family 須為 codex|grok|composer, 得到: ${fam}"; exit 2 ;;
esac
