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

# GOVB1 Task 1.1：brief-kind SSOT＝govflow_lifecycle.json（檔案優先；缺則 base64 embed）
_LIFECYCLE_JSON="${SCRIPT_DIR}/govflow_lifecycle.json"
_LIFECYCLE_EMBED_B64='ewogICJfZG9jIjogIkdPVkIxIFRhc2sgMS4xIOKAlCBicmllZi1raW5kIGxpZmVjeWNsZSBtYXRyaXjvvIjllq7kuIDnnJ/nm7jmupDvvInjgIJcblxuc2luZ2xlLXdyaXRlciDlpZHntITvvJpcbiAgLSBUYXNrIDEuMSDnjajljaDlu7rnq4vpoILlsaQgc2NoZW1h77yI5pys5qqU5LmLIGtpbmRz77yPc3RhZ2Vz77yPX2RvY++8ieOAglxuICAtIFRhc2sgMS4zIOWPquW+l+aWsOWinuWFt+WQjeevgCBleHBlY3RlZF9kZWx0Ye+8m+emgeaUueaXouacieevgOOAglxuICAtIFRhc2sgNC4yIOWPquW+l+aWsOWinuWFt+WQjeevgCB6ZXJvX2ZpbmRpbmdzX2NvbnRyYWN077yb56aB5pS55pei5pyJ56+A44CCXG4gIC0g5b6M57qMIFRhc2sg5a6M5oiQ5b6M6aCIIGpxIC1yICdrZXlzW10nIOmpl+eCuuWJjeS4gCBUYXNrIOe1kOaenOS5i+i2hembhuOAglxuXG7mnproiInpgornlYzvvIjli7/mt7fvvInvvJpcbiAgLSDmnKzmqpQga2luZHMg55qEIGtleSDvvJ0gYnJpZWYta2luZO+8iHJldmlld3xjb25zdWx0fGNsb3N1cmV8aW1wbHxzdGFtcO+8ieOAglxuICAtIGRlYnRfY2xlYXIg5qyE77yd6KmyIGJyaWVmLWtpbmQg55qE44CM6Yq35biz5YmN572u5qKd5Lu244CN5o+P6L+w77yM5LiN5pivIENMSSDml5fmqJnjgIJcbiAgLSBzY3JpcHRzL2RlYnRfY2xlYXIuc2ggLS1raW5kIOaYryBhYmFuZG9uX2tpbmTvvIhuby1maW5kaW5ncy1leHBlY3RlZHxjb2xsZWN0aW9uLWZhaWxlZO+8ie+8jFxuICAgIOaemuiIiea6kOiHqiBzY3JpcHRzL2F1ZGl0X2V2ZW50cy5qc29uIGVudW1zLmFiYW5kb25fa2luZOKAlOKAlOiIhyBicmllZi1raW5kIOaYr+S4jeWQjOaemuiIieOAglxuXG7mtojosrvnq6/vvJpzY3JpcHRzL2JyaWVmX2NvbmZvcm1hbmNlX2NoZWNrLnNo44CBc2NyaXB0cy9jeF9ydW4uc2gg5Y+q5YeG6K6A5pys5qqU5Y+WIGtpbmQg6ZuG5ZCI6IiH6ZqO5q615peX5qiZ77ybXG7npoHlnKjohbPmnKzlhaflho3noaznt6jnorwga2luZCDnmb3lkI3llq7miJYgZmFsbGJhY2vjgIJKU09OIOe8uiBraW5k77yP6Kqe5rOV6YyvIOKHkiBmYWlsLWNsb3NlZCByY+KJoDDvvIzoqIrmga/lkKvmnKzmqpTlkI3jgIIiLAogICJzdGFnZXMiOiB7CiAgICAiX2RvYyI6ICJicmllZiDnlJ/lkb3pgLHmnJ/pmo7mrrXpoIbluo/jgILmnKwgbWF0cml4IOimhuiTi+WIsCByZWNvbmNpbGUg5LmL5YmN55qE5rS+5bel6Y+I77ybcmVjb25jaWxlIC0tbW9kZSDoiIcgYnJpZWYta2luZCDmnproiInlsI3pvYrlsaznpaggQi0xM++8jOS4jeWcqOacrCBUYXNr44CCIiwKICAgICJvcmRlciI6IFsKICAgICAgInByZWNoZWNrIiwKICAgICAgImN4X3J1biIsCiAgICAgICJyZWNvbmNpbGUiLAogICAgICAiZGVidF9jbGVhciIKICAgIF0KICB9LAogICJraW5kcyI6IHsKICAgICJyZXZpZXciOiB7CiAgICAgICJyZXF1aXJlc190ZW1wbGF0ZV9hbmRfcHJlbWlzZXMiOiB0cnVlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiB0cnVlLAogICAgICAic3RhbXBfcHJvbXB0X2luamVjdCI6IGZhbHNlLAogICAgICAiY29tcGxldGVuZXNzX3NlbGZjaGVjayI6IHRydWUsCiAgICAgICJkZWJ0X2NsZWFyIjogewogICAgICAgICJfZG9jIjogIumKt+W4s+WJjee9ruaineS7tu+8iOmdniBhYmFuZG9uX2tpbmTvvInjgILmraPopo/pirfluLPpoIjlkITlrrbml48gcmVzdWx0X3N0YXRlPXN1Y2Nlc3Mg5LiUIHNvdXJjZXMubG9jayDlj6/mlLbmloLvvJvnhKEgZmluZGluZ3Mg5pyf5pyb5pmC6LWwIGRlYnRfY2xlYXIgLS1raW5kIGFiYW5kb24g55qEIGFiYW5kb25fa2luZCDmnproiInvvIjkuI3lkIzlkb3lkI3nqbrplpPvvInjgIIiLAogICAgICAgICJwcmVjb25kaXRpb25zIjogWwogICAgICAgICAgImFsbF9mYW1pbGllc190ZXJtaW5hbCIsCiAgICAgICAgICAiZm9ybWF0X29rX3doZW5fZmluZGluZ3Nfa2luZCIsCiAgICAgICAgICAic291cmNlc19sb2NrX2NvbnZlcmdlZF9vcl9hYmFuZG9uIgogICAgICAgIF0KICAgICAgfSwKICAgICAgInN0YWdlcyI6IHsKICAgICAgICAicHJlY2hlY2siOiAiYnJpZWZfY29uZm9ybWFuY2XvvJrnr4TmnKzlvJXnlKggKyBmYWN0LXZlcmlmaWVkL2Fzc3VtZWTvvJtyb2xlX2dhdGXvvJpmYW1pbHkgIT0gaW1wbGVtZW50ZXIiLAogICAgICAgICJjeF9ydW4iOiAiZm9ybWF0IGNoZWNrICsgY29tcGxldGVuZXNzIOiHquaqoiBwcm9tcHTvvJvkuI3ms6jlhaUgUkVDT05DSUxFLVNUQU1QIiwKICAgICAgICAicmVjb25jaWxlIjogIuaUtumbhiBmaW5kaW5nc++8m2NvbXBsZXRlbmVzcyAvIHNvdXJjZXMubG9jayIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfSwKICAgICJjb25zdWx0IjogewogICAgICAicmVxdWlyZXNfdGVtcGxhdGVfYW5kX3ByZW1pc2VzIjogdHJ1ZSwKICAgICAgInByb2R1Y2VzX2ZpbmRpbmdzIjogdHJ1ZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiBmYWxzZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiB0cnVlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICLlkIwgcmV2aWV377yaZmluZGluZ3Mta2luZCDmraPopo/pirfluLPmop3ku7bvvJthYmFuZG9uX2tpbmQg5Y+m5YaK44CCIiwKICAgICAgICAicHJlY29uZGl0aW9ucyI6IFsKICAgICAgICAgICJhbGxfZmFtaWxpZXNfdGVybWluYWwiLAogICAgICAgICAgImZvcm1hdF9va193aGVuX2ZpbmRpbmdzX2tpbmQiLAogICAgICAgICAgInNvdXJjZXNfbG9ja19jb252ZXJnZWRfb3JfYWJhbmRvbiIKICAgICAgICBdCiAgICAgIH0sCiAgICAgICJzdGFnZXMiOiB7CiAgICAgICAgInByZWNoZWNrIjogImJyaWVmX2NvbmZvcm1hbmNl77ya56+E5pys5byV55SoICsgZmFjdC12ZXJpZmllZC9hc3N1bWVk77ybcm9sZV9nYXRl77ya5LiN6ZmQ5Yi2IGltcGxlbWVudGVyIiwKICAgICAgICAiY3hfcnVuIjogImZvcm1hdCBjaGVjayArIGNvbXBsZXRlbmVzcyDoh6rmqqIgcHJvbXB077yb5LiN5rOo5YWlIFJFQ09OQ0lMRS1TVEFNUCIsCiAgICAgICAgInJlY29uY2lsZSI6ICLmlLbpm4YgZmluZGluZ3PvvJtjb21wbGV0ZW5lc3MgLyBzb3VyY2VzLmxvY2siLAogICAgICAgICJkZWJ0X2NsZWFyIjogIuimiyBkZWJ0X2NsZWFyLnByZWNvbmRpdGlvbnMiCiAgICAgIH0KICAgIH0sCiAgICAiY2xvc3VyZSI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IHRydWUsCiAgICAgICJwcm9kdWNlc19maW5kaW5ncyI6IHRydWUsCiAgICAgICJzdGFtcF9wcm9tcHRfaW5qZWN0IjogdHJ1ZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiB0cnVlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICJjbG9zdXJlIOeUoiBmaW5kaW5ncyDkuJQgcHJvbXB0IOWQq+aIs+iomOaMh+ekuu+8m+mKt+W4s+S7jeS+nSBzdWNjZXNz77yPYWJhbmRvbiDot6/lvpHvvIzpnZ4gYWJhbmRvbl9raW5kIOa3t+WFpSBraW5kc+OAgiIsCiAgICAgICAgInByZWNvbmRpdGlvbnMiOiBbCiAgICAgICAgICAiYWxsX2ZhbWlsaWVzX3Rlcm1pbmFsIiwKICAgICAgICAgICJmb3JtYXRfb2tfd2hlbl9maW5kaW5nc19raW5kIiwKICAgICAgICAgICJzb3VyY2VzX2xvY2tfY29udmVyZ2VkX29yX2FiYW5kb24iCiAgICAgICAgXQogICAgICB9LAogICAgICAic3RhZ2VzIjogewogICAgICAgICJwcmVjaGVjayI6ICJicmllZl9jb25mb3JtYW5jZe+8muevhOacrOW8leeUqCArIGZhY3QtdmVyaWZpZWQvYXNzdW1lZO+8m3JvbGVfZ2F0Ze+8muS4jemZkOWItiIsCiAgICAgICAgImN4X3J1biI6ICJmb3JtYXQgY2hlY2sgKyDoh6rmqqIgcHJvbXB0ICsgUkVDT05DSUxFLVNUQU1QIOazqOWFpeWPpSIsCiAgICAgICAgInJlY29uY2lsZSI6ICLmlLbpm4YgZmluZGluZ3PvvJvlj6/lkKvmiLPoqJjopIfpqZciLAogICAgICAgICJkZWJ0X2NsZWFyIjogIuimiyBkZWJ0X2NsZWFyLnByZWNvbmRpdGlvbnMiCiAgICAgIH0KICAgIH0sCiAgICAiaW1wbCI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IGZhbHNlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiBmYWxzZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiBmYWxzZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiBmYWxzZSwKICAgICAgImRlYnRfY2xlYXIiOiB7CiAgICAgICAgIl9kb2MiOiAiaW1wbCDkuI3nlKIgY2Fub25pY2FsIGZpbmRpbmcgSUTvvJvpirfluLPliY3nva7ngrrlrrbml48gc3VjY2Vzc++8iOaIliBhYmFuZG9uX2tpbmQg5piO56S677yJ77yM5LiN6LeRIGZpbmRpbmdzIOaUtuaWguOAgiIsCiAgICAgICAgInByZWNvbmRpdGlvbnMiOiBbCiAgICAgICAgICAiYWxsX2ZhbWlsaWVzX3Rlcm1pbmFsIiwKICAgICAgICAgICJub19maW5kaW5nc19mb3JtYXRfZ2F0ZSIKICAgICAgICBdCiAgICAgIH0sCiAgICAgICJzdGFnZXMiOiB7CiAgICAgICAgInByZWNoZWNrIjogImJyaWVmX2NvbmZvcm1hbmNl77ya5YOFIGtpbmQg55m95ZCN5Zau77ybcm9sZV9nYXRl77yaZmFtaWx5ID09IGltcGxlbWVudGVyIiwKICAgICAgICAiY3hfcnVuIjogIueEoSBmb3JtYXQgY2hlY2vvvI/nhKEgUkVDT05DSUxFLVNUQU1QIOazqOWFpSIsCiAgICAgICAgInJlY29uY2lsZSI6ICLpgJrluLjnhKEgZmluZGluZ3Mg5pS25paC77yIbm8tZmluZGluZ3MtZXhwZWN0ZWQg5bGsIGFiYW5kb25fa2luZO+8iSIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfSwKICAgICJzdGFtcCI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IGZhbHNlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiBmYWxzZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiB0cnVlLAogICAgICAiY29tcGxldGVuZXNzX3NlbGZjaGVjayI6IGZhbHNlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICJzdGFtcCDovKrms6jlhaUgUkVDT05DSUxFLVNUQU1Q77yb6Yq35biz55yL5a625pePIHN1Y2Nlc3PvvIzkuI3ntpMgZmluZGluZ3MgZm9ybWF0IGdhdGXjgIIiLAogICAgICAgICJwcmVjb25kaXRpb25zIjogWwogICAgICAgICAgImFsbF9mYW1pbGllc190ZXJtaW5hbCIsCiAgICAgICAgICAibm9fZmluZGluZ3NfZm9ybWF0X2dhdGUiCiAgICAgICAgXQogICAgICB9LAogICAgICAic3RhZ2VzIjogewogICAgICAgICJwcmVjaGVjayI6ICJicmllZl9jb25mb3JtYW5jZe+8mmtpbmQgKyBzdGFtcC10YXJnZXQg6Lev5b6R77yP5a2Y5Zyo5oCn77ybcm9sZV9nYXRl77ya5LiN6ZmQ5Yi2IiwKICAgICAgICAiY3hfcnVuIjogIlJFQ09OQ0lMRS1TVEFNUCDms6jlhaXvvJtyZWdpc3Rlci1vdXRwdXQg5qKd5Lu26Lev5b6R77yIX21heWJlX3JlZ2lzdGVyX3N0YW1wX291dHB1dO+8jEctNiDlh43ntZDvvIkiLAogICAgICAgICJyZWNvbmNpbGUiOiAi5oiz6KiY6KSH6amX77yIcmVjb25jaWxlX3N0YW1wc19jaGVja++8iSIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfQogIH0KfQo='

_cx_lifecycle_resolve() {
  if [ -f "${_LIFECYCLE_JSON}" ]; then
    if ! jq empty "${_LIFECYCLE_JSON}" 2>/dev/null; then
      echo "ERROR: lifecycle matrix JSON 語法錯: ${_LIFECYCLE_JSON}" >&2
      return 1
    fi
    printf '%s\n' "${_LIFECYCLE_JSON}"
    return 0
  fi
  _tmp="$(mktemp)"
  if ! printf '%s' "${_LIFECYCLE_EMBED_B64}" | base64 -d > "${_tmp}" 2>/dev/null; then
    echo "ERROR: lifecycle matrix 不存在: ${_LIFECYCLE_JSON}" >&2
    rm -f "${_tmp}"
    return 1
  fi
  if ! jq empty "${_tmp}" 2>/dev/null; then
    echo "ERROR: lifecycle matrix JSON 語法錯: ${_LIFECYCLE_JSON}" >&2
    rm -f "${_tmp}"
    return 1
  fi
  if cp "${_tmp}" "${_LIFECYCLE_JSON}" 2>/dev/null; then
    rm -f "${_tmp}"
    printf '%s\n' "${_LIFECYCLE_JSON}"
  else
    printf '%s\n' "${_tmp}"
  fi
  return 0
}

_cx_lifecycle_ok() {
  _cx_lifecycle_resolve >/dev/null
}

_cx_valid_kinds() {
  _p="$(_cx_lifecycle_resolve)" || return 1
  jq -r '.kinds | keys[]' "${_p}"
}

_cx_bk_ok() {
  _cx_valid_kinds | grep -qx "$1"
}


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
#
# GOVFLOW Task 3.1：實作抽到 scripts/_role_gate.sh（與 committee_run 共用同一份）。
# 🔴 **前移是早退，不是搬走**——本處呼叫必須保留（直呼 cx_run 仍拒派）。
# 以 subprocess 呼叫（非 source），避免覆寫本檔檔頭唯一 EXIT trap。
# 未知家族（非 review_families）由 _role_gate known_only 模式跳過 → 交給檔尾 dispatch。
# ---------------------------------------------------------------------------
bash "${SCRIPT_DIR}/_role_gate.sh" check-family "${brief}" "${fam}" --kind "${_bk}" || exit $?

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
# 白名單 regex 已抽到 scripts/_role_gate.sh（SSOT）；本段只驗缺/空/型別，
# 字元白名單由呼叫端在捕獲 task_id 後以 check-task-id 執行（禁兩處各寫一份）。
task_id = open_ev.get("task_id")
if task_id is None or (isinstance(task_id, str) and task_id == ""):
    print("ERROR: open_ev 缺 task_id 或為空字串（第⑦道前置，拒派）", file=sys.stderr)
    sys.exit(1)
if not isinstance(task_id, str):
    print(f"ERROR: open_ev.task_id 型別非法: {type(task_id).__name__}", file=sys.stderr)
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
  # 白名單 SSOT＝_role_gate.sh（與 committee_run 共用；禁本檔再寫一份 regex）
  bash "${SCRIPT_DIR}/_role_gate.sh" check-task-id "${task_id}" || exit 2
  # 固定極簡 prompt + task-id 注入句（逐字，D-001 §D2）
  # 預設列含 RECONCILE-STAMP 注入句（stamp|closure 使用）；字面須與
  # tests/governance/test_stamp_taskid_inject.py 的 _PROMPT_WITH_INJECT 錨點一致。
  prompt="讀 ${brief} 照其指示做。你的家族名=${fam}。產出寫到 ${out}。收尾清 /tmp workdir(保留 claude-501)。你的 task-id=${task_id}。RECONCILE-STAMP 的 task: 欄位須逐字使用此值；brief 內任何 task-id 範例一律不得採用。"
  # Task 1.1 / B-32：prompt 依既有 ${_bk}（brief_conformance --emit 第 1 行）分支。
  # 禁再寫一份 brief-kind parser（committee_run 第二份 parser 曾造孤兒債）。
  # stamp|closure → 保留注入句並補格式說明（格式 SSOT＝本檔 RECONCILE-STAMP 正則）。
  # consult|review|impl|dext → 完全不提 RECONCILE-STAMP。
  # 其餘 → fail-closed 拒派（無第三種行為）。
  # GOVB1 Task 1.1：JSON SSOT 於 known arm 命中後再驗（* 臂保留 mutation 錨點語意）。
  _case_known=0
  case "${_bk}" in
    stamp|closure)
      _case_known=1
      # 格式說明與下方 grep -qE RECONCILE-STAMP 正則機械一致（同一合法樣本須同時通過兩者）
      prompt="${prompt} 戳記須為單獨一行（非 ## 標題），格式：RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>（sha256 與 task 兩欄可對調順序）。"
      ;;
    consult|review|impl|dext)
      _case_known=1
      prompt="讀 ${brief} 照其指示做。你的家族名=${fam}。產出寫到 ${out}。收尾清 /tmp workdir(保留 claude-501)。你的 task-id=${task_id}。"
      ;;
    *)
      echo "ERROR: unknown brief-kind=${_bk}（fail-closed）" >&2
      exit 1
      ;;
  esac
  if [ "${_case_known}" -eq 1 ] && ! _cx_bk_ok "${_bk}"; then
    echo "ERROR: unknown brief-kind=${_bk}（fail-closed）" >&2
    exit 1
  fi
  # 票 B-31：對「會跑格式檢查的 kind」追加交件前自檢指示。
  # kind 集合須與 _run_format_check_if_needed 一致（review|consult|closure）——
  # impl／stamp／dext 依契約無 canonical finding ID，加了會誤導委員去跑必然 vacuous 的檢查。
  #
  # 為何進 prompt 模板而非每份 brief 手寫（使用者定死「工具必須自帶強制機制，
  # 不准靠紀律和記憶」）：2026-08-06 GOVB39-B1-CONSULT R1 兩家皆 format-failed
  # （composer 缺 source_digest、grok 觸發 heading 誤判），主委在 R2 brief **手寫**
  # 同一指示後兩家一次全過。手寫版靠主委每次記得，本層讓它恆常生效。
  #
  # 淨摩擦：新增成本＝委員每輪多跑一次秒級唯讀檢查；
  # 省下＝一次 format-failed 的整份重跑（實測 composer 約 15 分鐘，見票 B-31 事故欄）。
  # --family 必須帶：交件檢查是 `--single "${out}" --family "${fam}"`（見 _run_format_check_if_needed）。
  # 不帶時 extract_heading_ids 改由檔名推 family，慣例路徑 handoffs/*-<family>.md 下行為等價，
  # 但產出路徑不含家族後綴時自檢會**弱於**交件（自檢過、交件仍 format-failed）
  # ⇒ 破壞「先跑等於預跑」的前提。〔COMPOSER-R1-P2-02 實測：無 --family rc=0、帶 --family rc=1〕
  #
  # 🔴 措辭不得寫成「與交件檢查等價」：--single 與收斂路徑對「0 findings」判定不同
  #    （--single 回 PASS，_run_id_layer 對 sources_with_ids=0 回 FAIL ⇒ 自檢假綠）。
  #    〔CODEX-R1-P1-01 實測 BLOCKING〕
  #
  # 票 B-38（2026-08-07）：給誠實回報 0 findings 者一條**能正規收斂**的出路。
  #   舊版只說「明確寫出『本輪 0 findings』」⇒ 那是散文，收斂端抽不到 heading ID
  #   ⇒ sources_with_ids 不增 ⇒ vacuous FAIL ⇒ **誠實則卡住、捏造則通過**（08-07 實際發生）。
  #   解法＝沿用既有 P3-00 sentinel 慣例：它是合法 canonical ID（P[0-3] ＋ [0-9]{2,}），
  #   抽得到就不觸發 vacuous，且空殼會被 _validate_finding_body 擋。**檢查器零改動。**
  #   實測（2026-08-07，.claude/tmp/b38/）：
  #     實質 sentinel 收斂 → rc=0 ；source 端空殼 sentinel → rc=1 ；--single 空殼 → rc=1
  #   ⚠️ 本句同時取代主委 08-06 誤造的第三種格式（散文「本輪 0 findings」），
  #     避免與舊 P3-00 慣例並存造成三種寫法。
  case "${_bk}" in
    review|consult|closure)
      prompt="${prompt} 寫完產出後，請自行執行 bash scripts/completeness_check.sh --single ${out} --family ${fam} 並確認 rc=0；若非 0 請就地修正格式後再結束（此為交件時的同一支檢查同一組參數，先跑可免整份重跑）。注意：若你的結論確實是 0 個 finding，請寫一條 sentinel：heading 用 ## <你的家族大寫>-R<本輪輪次>-P3-00，body 照常填 **斷言**／**碼證**／**來源摘要**，內容為「本輪逐項核對後無 finding」與你的核對依據。只寫散文或留空會被判空殼而擋下；寫成 sentinel 才能正常收斂。勿為了湊數而捏造實質 finding。"
      ;;
  esac
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
