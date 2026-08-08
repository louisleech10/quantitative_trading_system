#!/usr/bin/env bash
# brief_conformance_check.sh — brief 合規閘的**唯一實作**（GOV-DOC-CHECK-AT-WRITE）。
#
# 出生理由（2026-08-02）：本檢查原本內嵌在 cx_run.sh:29-112，只在**派工當下**才跑。
#   實證代價：本 session 4 輪、B4 批次 5 輪（該批 38%）純粹燒在「brief 格式被閘擋 → 重寫 → 重派」。
#   病根＝**檢查點在消費端不在產出端**（`GOV-FORMAT-SSOT` 症狀 B）。
#   抽成獨立腳本後有兩個呼叫點：
#     ① scripts/cx_run.sh          — 派工前硬擋（fail-closed，維持原行為）
#     ② scripts/doc_format_precheck.sh — PostToolUse hook，**寫完當下**就回灌 Claude context
#   **一份實作、兩個呼叫點**。禁把邏輯複製到呼叫端——那是第二真相源，必然漂移。
#
# 用法：
#   bash scripts/brief_conformance_check.sh <brief_path> [--emit <kv_file>]
#   bash scripts/brief_conformance_check.sh --only <check> <brief_path>
#     --emit <kv_file>：成功時把解析結果寫入該檔，第 1 行 = brief-kind，第 2 行 = stamp-target（非 stamp 為空行）
#                       （**不用 stdout 回傳**：既有錯誤訊息就走 stdout，呼叫端若重導 stdout 會把訊息吃掉）
#     --only <check>：只跑具名檢查（未知 check 名 ⇒ fail-closed rc≠0；禁靜默跑全部）
#                     現支援：expected-delta（Task 1.3）
#   rc: 0=合規；2=不合規/用法錯。
#
# ⚠️ 訊息輸出通道與抽出前**逐字相同**（brief-kind 段走 stdout、stamp-target 段走 stderr）。
#    既有測試 tests/governance/test_stamp_taskid_inject.py 對兩者分別斷言，改通道＝弄紅既有測試。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
_LIFECYCLE_JSON="${SCRIPT_DIR}/govflow_lifecycle.json"
_LIFECYCLE_EMBED_B64='ewogICJfZG9jIjogIkdPVkIxIFRhc2sgMS4xIOKAlCBicmllZi1raW5kIGxpZmVjeWNsZSBtYXRyaXjvvIjllq7kuIDnnJ/nm7jmupDvvInjgIJcblxuc2luZ2xlLXdyaXRlciDlpZHntITvvJpcbiAgLSBUYXNrIDEuMSDnjajljaDlu7rnq4vpoILlsaQgc2NoZW1h77yI5pys5qqU5LmLIGtpbmRz77yPc3RhZ2Vz77yPX2RvY++8ieOAglxuICAtIFRhc2sgMS4zIOWPquW+l+aWsOWinuWFt+WQjeevgCBleHBlY3RlZF9kZWx0Ye+8m+emgeaUueaXouacieevgOOAglxuICAtIFRhc2sgNC4yIOWPquW+l+aWsOWinuWFt+WQjeevgCB6ZXJvX2ZpbmRpbmdzX2NvbnRyYWN077yb56aB5pS55pei5pyJ56+A44CCXG4gIC0g5b6M57qMIFRhc2sg5a6M5oiQ5b6M6aCIIGpxIC1yICdrZXlzW10nIOmpl+eCuuWJjeS4gCBUYXNrIOe1kOaenOS5i+i2hembhuOAglxuXG7mnproiInpgornlYzvvIjli7/mt7fvvInvvJpcbiAgLSDmnKzmqpQga2luZHMg55qEIGtleSDvvJ0gYnJpZWYta2luZO+8iHJldmlld3xjb25zdWx0fGNsb3N1cmV8aW1wbHxzdGFtcO+8ieOAglxuICAtIGRlYnRfY2xlYXIg5qyE77yd6KmyIGJyaWVmLWtpbmQg55qE44CM6Yq35biz5YmN572u5qKd5Lu244CN5o+P6L+w77yM5LiN5pivIENMSSDml5fmqJnjgIJcbiAgLSBzY3JpcHRzL2RlYnRfY2xlYXIuc2ggLS1raW5kIOaYryBhYmFuZG9uX2tpbmTvvIhuby1maW5kaW5ncy1leHBlY3RlZHxjb2xsZWN0aW9uLWZhaWxlZO+8ie+8jFxuICAgIOaemuiIiea6kOiHqiBzY3JpcHRzL2F1ZGl0X2V2ZW50cy5qc29uIGVudW1zLmFiYW5kb25fa2luZOKAlOKAlOiIhyBicmllZi1raW5kIOaYr+S4jeWQjOaemuiIieOAglxuXG7mtojosrvnq6/vvJpzY3JpcHRzL2JyaWVmX2NvbmZvcm1hbmNlX2NoZWNrLnNo44CBc2NyaXB0cy9jeF9ydW4uc2gg5Y+q5YeG6K6A5pys5qqU5Y+WIGtpbmQg6ZuG5ZCI6IiH6ZqO5q615peX5qiZ77ybXG7npoHlnKjohbPmnKzlhaflho3noaznt6jnorwga2luZCDnmb3lkI3llq7miJYgZmFsbGJhY2vjgIJKU09OIOe8uiBraW5k77yP6Kqe5rOV6YyvIOKHkiBmYWlsLWNsb3NlZCByY+KJoDDvvIzoqIrmga/lkKvmnKzmqpTlkI3jgIIiLAogICJzdGFnZXMiOiB7CiAgICAiX2RvYyI6ICJicmllZiDnlJ/lkb3pgLHmnJ/pmo7mrrXpoIbluo/jgILmnKwgbWF0cml4IOimhuiTi+WIsCByZWNvbmNpbGUg5LmL5YmN55qE5rS+5bel6Y+I77ybcmVjb25jaWxlIC0tbW9kZSDoiIcgYnJpZWYta2luZCDmnproiInlsI3pvYrlsaznpaggQi0xM++8jOS4jeWcqOacrCBUYXNr44CCIiwKICAgICJvcmRlciI6IFsKICAgICAgInByZWNoZWNrIiwKICAgICAgImN4X3J1biIsCiAgICAgICJyZWNvbmNpbGUiLAogICAgICAiZGVidF9jbGVhciIKICAgIF0KICB9LAogICJraW5kcyI6IHsKICAgICJyZXZpZXciOiB7CiAgICAgICJyZXF1aXJlc190ZW1wbGF0ZV9hbmRfcHJlbWlzZXMiOiB0cnVlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiB0cnVlLAogICAgICAic3RhbXBfcHJvbXB0X2luamVjdCI6IGZhbHNlLAogICAgICAiY29tcGxldGVuZXNzX3NlbGZjaGVjayI6IHRydWUsCiAgICAgICJkZWJ0X2NsZWFyIjogewogICAgICAgICJfZG9jIjogIumKt+W4s+WJjee9ruaineS7tu+8iOmdniBhYmFuZG9uX2tpbmTvvInjgILmraPopo/pirfluLPpoIjlkITlrrbml48gcmVzdWx0X3N0YXRlPXN1Y2Nlc3Mg5LiUIHNvdXJjZXMubG9jayDlj6/mlLbmloLvvJvnhKEgZmluZGluZ3Mg5pyf5pyb5pmC6LWwIGRlYnRfY2xlYXIgLS1raW5kIGFiYW5kb24g55qEIGFiYW5kb25fa2luZCDmnproiInvvIjkuI3lkIzlkb3lkI3nqbrplpPvvInjgIIiLAogICAgICAgICJwcmVjb25kaXRpb25zIjogWwogICAgICAgICAgImFsbF9mYW1pbGllc190ZXJtaW5hbCIsCiAgICAgICAgICAiZm9ybWF0X29rX3doZW5fZmluZGluZ3Nfa2luZCIsCiAgICAgICAgICAic291cmNlc19sb2NrX2NvbnZlcmdlZF9vcl9hYmFuZG9uIgogICAgICAgIF0KICAgICAgfSwKICAgICAgInN0YWdlcyI6IHsKICAgICAgICAicHJlY2hlY2siOiAiYnJpZWZfY29uZm9ybWFuY2XvvJrnr4TmnKzlvJXnlKggKyBmYWN0LXZlcmlmaWVkL2Fzc3VtZWTvvJtyb2xlX2dhdGXvvJpmYW1pbHkgIT0gaW1wbGVtZW50ZXIiLAogICAgICAgICJjeF9ydW4iOiAiZm9ybWF0IGNoZWNrICsgY29tcGxldGVuZXNzIOiHquaqoiBwcm9tcHTvvJvkuI3ms6jlhaUgUkVDT05DSUxFLVNUQU1QIiwKICAgICAgICAicmVjb25jaWxlIjogIuaUtumbhiBmaW5kaW5nc++8m2NvbXBsZXRlbmVzcyAvIHNvdXJjZXMubG9jayIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfSwKICAgICJjb25zdWx0IjogewogICAgICAicmVxdWlyZXNfdGVtcGxhdGVfYW5kX3ByZW1pc2VzIjogdHJ1ZSwKICAgICAgInByb2R1Y2VzX2ZpbmRpbmdzIjogdHJ1ZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiBmYWxzZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiB0cnVlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICLlkIwgcmV2aWV377yaZmluZGluZ3Mta2luZCDmraPopo/pirfluLPmop3ku7bvvJthYmFuZG9uX2tpbmQg5Y+m5YaK44CCIiwKICAgICAgICAicHJlY29uZGl0aW9ucyI6IFsKICAgICAgICAgICJhbGxfZmFtaWxpZXNfdGVybWluYWwiLAogICAgICAgICAgImZvcm1hdF9va193aGVuX2ZpbmRpbmdzX2tpbmQiLAogICAgICAgICAgInNvdXJjZXNfbG9ja19jb252ZXJnZWRfb3JfYWJhbmRvbiIKICAgICAgICBdCiAgICAgIH0sCiAgICAgICJzdGFnZXMiOiB7CiAgICAgICAgInByZWNoZWNrIjogImJyaWVmX2NvbmZvcm1hbmNl77ya56+E5pys5byV55SoICsgZmFjdC12ZXJpZmllZC9hc3N1bWVk77ybcm9sZV9nYXRl77ya5LiN6ZmQ5Yi2IGltcGxlbWVudGVyIiwKICAgICAgICAiY3hfcnVuIjogImZvcm1hdCBjaGVjayArIGNvbXBsZXRlbmVzcyDoh6rmqqIgcHJvbXB077yb5LiN5rOo5YWlIFJFQ09OQ0lMRS1TVEFNUCIsCiAgICAgICAgInJlY29uY2lsZSI6ICLmlLbpm4YgZmluZGluZ3PvvJtjb21wbGV0ZW5lc3MgLyBzb3VyY2VzLmxvY2siLAogICAgICAgICJkZWJ0X2NsZWFyIjogIuimiyBkZWJ0X2NsZWFyLnByZWNvbmRpdGlvbnMiCiAgICAgIH0KICAgIH0sCiAgICAiY2xvc3VyZSI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IHRydWUsCiAgICAgICJwcm9kdWNlc19maW5kaW5ncyI6IHRydWUsCiAgICAgICJzdGFtcF9wcm9tcHRfaW5qZWN0IjogdHJ1ZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiB0cnVlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICJjbG9zdXJlIOeUoiBmaW5kaW5ncyDkuJQgcHJvbXB0IOWQq+aIs+iomOaMh+ekuu+8m+mKt+W4s+S7jeS+nSBzdWNjZXNz77yPYWJhbmRvbiDot6/lvpHvvIzpnZ4gYWJhbmRvbl9raW5kIOa3t+WFpSBraW5kc+OAgiIsCiAgICAgICAgInByZWNvbmRpdGlvbnMiOiBbCiAgICAgICAgICAiYWxsX2ZhbWlsaWVzX3Rlcm1pbmFsIiwKICAgICAgICAgICJmb3JtYXRfb2tfd2hlbl9maW5kaW5nc19raW5kIiwKICAgICAgICAgICJzb3VyY2VzX2xvY2tfY29udmVyZ2VkX29yX2FiYW5kb24iCiAgICAgICAgXQogICAgICB9LAogICAgICAic3RhZ2VzIjogewogICAgICAgICJwcmVjaGVjayI6ICJicmllZl9jb25mb3JtYW5jZe+8muevhOacrOW8leeUqCArIGZhY3QtdmVyaWZpZWQvYXNzdW1lZO+8m3JvbGVfZ2F0Ze+8muS4jemZkOWItiIsCiAgICAgICAgImN4X3J1biI6ICJmb3JtYXQgY2hlY2sgKyDoh6rmqqIgcHJvbXB0ICsgUkVDT05DSUxFLVNUQU1QIOazqOWFpeWPpSIsCiAgICAgICAgInJlY29uY2lsZSI6ICLmlLbpm4YgZmluZGluZ3PvvJvlj6/lkKvmiLPoqJjopIfpqZciLAogICAgICAgICJkZWJ0X2NsZWFyIjogIuimiyBkZWJ0X2NsZWFyLnByZWNvbmRpdGlvbnMiCiAgICAgIH0KICAgIH0sCiAgICAiaW1wbCI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IGZhbHNlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiBmYWxzZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiBmYWxzZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiBmYWxzZSwKICAgICAgImRlYnRfY2xlYXIiOiB7CiAgICAgICAgIl9kb2MiOiAiaW1wbCDkuI3nlKIgY2Fub25pY2FsIGZpbmRpbmcgSUTvvJvpirfluLPliY3nva7ngrrlrrbml48gc3VjY2Vzc++8iOaIliBhYmFuZG9uX2tpbmQg5piO56S677yJ77yM5LiN6LeRIGZpbmRpbmdzIOaUtuaWguOAgiIsCiAgICAgICAgInByZWNvbmRpdGlvbnMiOiBbCiAgICAgICAgICAiYWxsX2ZhbWlsaWVzX3Rlcm1pbmFsIiwKICAgICAgICAgICJub19maW5kaW5nc19mb3JtYXRfZ2F0ZSIKICAgICAgICBdCiAgICAgIH0sCiAgICAgICJzdGFnZXMiOiB7CiAgICAgICAgInByZWNoZWNrIjogImJyaWVmX2NvbmZvcm1hbmNl77ya5YOFIGtpbmQg55m95ZCN5Zau77ybcm9sZV9nYXRl77yaZmFtaWx5ID09IGltcGxlbWVudGVyIiwKICAgICAgICAiY3hfcnVuIjogIueEoSBmb3JtYXQgY2hlY2vvvI/nhKEgUkVDT05DSUxFLVNUQU1QIOazqOWFpSIsCiAgICAgICAgInJlY29uY2lsZSI6ICLpgJrluLjnhKEgZmluZGluZ3Mg5pS25paC77yIbm8tZmluZGluZ3MtZXhwZWN0ZWQg5bGsIGFiYW5kb25fa2luZO+8iSIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfSwKICAgICJzdGFtcCI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IGZhbHNlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiBmYWxzZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiB0cnVlLAogICAgICAiY29tcGxldGVuZXNzX3NlbGZjaGVjayI6IGZhbHNlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICJzdGFtcCDovKrms6jlhaUgUkVDT05DSUxFLVNUQU1Q77yb6Yq35biz55yL5a625pePIHN1Y2Nlc3PvvIzkuI3ntpMgZmluZGluZ3MgZm9ybWF0IGdhdGXjgIIiLAogICAgICAgICJwcmVjb25kaXRpb25zIjogWwogICAgICAgICAgImFsbF9mYW1pbGllc190ZXJtaW5hbCIsCiAgICAgICAgICAibm9fZmluZGluZ3NfZm9ybWF0X2dhdGUiCiAgICAgICAgXQogICAgICB9LAogICAgICAic3RhZ2VzIjogewogICAgICAgICJwcmVjaGVjayI6ICJicmllZl9jb25mb3JtYW5jZe+8mmtpbmQgKyBzdGFtcC10YXJnZXQg6Lev5b6R77yP5a2Y5Zyo5oCn77ybcm9sZV9nYXRl77ya5LiN6ZmQ5Yi2IiwKICAgICAgICAiY3hfcnVuIjogIlJFQ09OQ0lMRS1TVEFNUCDms6jlhaXvvJtyZWdpc3Rlci1vdXRwdXQg5qKd5Lu26Lev5b6R77yIX21heWJlX3JlZ2lzdGVyX3N0YW1wX291dHB1dO+8jEctNiDlh43ntZDvvIkiLAogICAgICAgICJyZWNvbmNpbGUiOiAi5oiz6KiY6KSH6amX77yIcmVjb25jaWxlX3N0YW1wc19jaGVja++8iSIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfQogIH0sCiAgImV4cGVjdGVkX2RlbHRhIjogewogICAgIl9kb2MiOiAiR09WQjEgVGFzayAxLjMg4oCUIEVYUEVDVEVELURFTFRBOiDljYDloYrlpZHntITvvIjnpaggQi0yOe+8ieOAglxuICBicmllZi1raW5kPWltcGwg5pmCIGJyaWVmIOmgiOWQq+ihjOmmliBFWFBFQ1RFRC1ERUxUQTog5LiU5qiZ6aGM5b6M6Iez56m66KGM5YmN5pyJ6Z2e56m655m95YWn5a6544CCXG4gIOmdniBpbXBsIOS4jemBqeeUqO+8iHJjPTDvvInjgILmnKznr4Dlj6rlrprnvqnlrZjlnKjmgKfvvI/pnZ7nqbrvvJvkuI3lr6bkvZzliY3lvozlsI3nhafmr5TlsI3vvIjnpaggQi0yOSDnrKwgMiDmrrXvvInjgIJcbiAg56m65Y2A5aGK5Yik5a6a56aB54Wn5oqEIFRPRE8g5YG956K85LmLIGJyYWNrZXQgY2xhc3PvvIhELUQg56+E5ZyN6YGL566X5a2Q5L2/5qiZ6aGM6KGM5oGG5ZG95Lit77yd56WoIEItNDMg56ys5LqU5L6L77yJ44CCIiwKICAgICJoZWFkZXIiOiAiRVhQRUNURUQtREVMVEE6IiwKICAgICJyZXF1aXJlZF9mb3Jfa2luZHMiOiBbCiAgICAgICJpbXBsIgogICAgXSwKICAgICJlbXB0eV9ib2R5X2ZhaWxzIjogdHJ1ZSwKICAgICJjaGVja19uYW1lIjogImV4cGVjdGVkLWRlbHRhIgogIH0KfQo='

_lifecycle_resolve() {
  if [ -f "${_LIFECYCLE_JSON}" ]; then
    if ! jq empty "${_LIFECYCLE_JSON}" 2>/dev/null; then
      echo "ERROR: lifecycle matrix JSON 語法錯: ${_LIFECYCLE_JSON}" >&2
      return 1
    fi
    printf '%s\n' "${_LIFECYCLE_JSON}"
    return 0
  fi
  # 明確吃 TMPDIR（macOS bare mktemp 會忽略 TMPDIR；回歸測靠此）。
  _tmp="$(mktemp "${TMPDIR:-/tmp}/govflow_lc.XXXXXX")"
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
  # 缺檔：只回傳 temp 路徑（唯讀物化）。禁止 cp 回 repo／隔離目錄（靜默寫檔＝假綠源）。
  # 「缺 JSON fail-closed」落在 govb1_final_gate lifecycle_embed 閘，不在此執行期。
  # caller 必須在 jq 成功／失敗後 _lifecycle_cleanup_if_temp（權威路徑 no-op）。
  printf '%s\n' "${_tmp}"
  return 0
}

# 權威檔路徑 no-op；temp 路徑一律 rm（成功與失敗路徑皆須呼叫）。
_lifecycle_cleanup_if_temp() {
  _p="${1:-}"
  [ -n "${_p}" ] || return 0
  [ "${_p}" = "${_LIFECYCLE_JSON}" ] && return 0
  rm -f "${_p}"
}

_lifecycle_json_ok() {
  _p="$(_lifecycle_resolve)" || return 1
  # resolve 已做 jq empty；此處只回收可能的 temp（勿 >/dev/null 丟 path）。
  _lifecycle_cleanup_if_temp "${_p}"
  return 0
}

_valid_kinds() {
  _p="$(_lifecycle_resolve)" || return 1
  _keys="$(jq -r '.kinds | keys[]' "${_p}")"
  _rc=$?
  _lifecycle_cleanup_if_temp "${_p}"
  [ "${_rc}" -eq 0 ] || return 1
  printf '%s\n' "${_keys}"
}

_bk_ok() {
  _valid_kinds | grep -qx "$1"
}


brief=""
emit_file=""
only_check=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --emit)
      [ "$#" -ge 2 ] || { echo "ERROR: --emit 需要參數" >&2; exit 2; }
      emit_file="$2"; shift 2 ;;
    --only)
      [ "$#" -ge 2 ] || { echo "ERROR: --only 需要參數" >&2; exit 2; }
      only_check="$2"; shift 2 ;;
    -*)
      echo "ERROR: 未知旗標: $1" >&2; exit 2 ;;
    *)
      if [ -n "${brief}" ]; then
        echo "ERROR: 多餘位置參數: $1" >&2; exit 2
      fi
      brief="$1"; shift ;;
  esac
done

[ -n "${brief}" ] || {
  echo "用法: bash scripts/brief_conformance_check.sh <brief_path> [--emit <kv_file>]" >&2
  echo "      bash scripts/brief_conformance_check.sh --only <check> <brief_path>" >&2
  exit 2
}
[ -f "${brief}" ] || { echo "ERROR: brief 檔不存在: ${brief}" >&2; exit 2; }

# ---------------------------------------------------------------------------
# Task 1.3 — EXPECTED-DELTA: 存在性＋非空（票 B-29）
# 空區塊判定：剔除標題行後再驗非空白（禁 TODO 偽碼 bracket class；票 B-43 第五例）
# ---------------------------------------------------------------------------
_check_expected_delta() {
  # $1=brief_path → rc 0=ok；1=缺/空（訊息 stdout，與既有 ERROR 同通道）
  _ed_brief="$1"
  _ed_bk_all="$(grep -E '^brief-kind:' "${_ed_brief}" 2>/dev/null \
    | sed 's/^brief-kind:[[:space:]]*//;s/[[:space:]]*$//' | sort -u)"
  _ed_bk_n="$(printf '%s\n' "${_ed_bk_all}" | grep -c '[^[:space:]]' || true)"
  if [ "${_ed_bk_n}" -gt 1 ]; then
    echo "ERROR: brief 有多個【不一致】的行首 'brief-kind:' 宣告: $(printf '%s' "${_ed_bk_all}" | tr '\n' ' ')"
    return 1
  fi
  _ed_bk="$(printf '%s\n' "${_ed_bk_all}" | head -1)"
  # 非 impl 不適用
  [ "${_ed_bk}" = "impl" ] || return 0

  if ! grep -qE '^EXPECTED-DELTA:' "${_ed_brief}"; then
    echo "ERROR: brief-kind=impl 缺 EXPECTED-DELTA: 區塊"
    return 1
  fi
  # 區塊＝標題行至下一空行；剔除標題後須有非空白（勿用 [^[:space:]EXPECTED-DELTA:]）
  if ! sed -n '/^EXPECTED-DELTA:/,/^$/p' "${_ed_brief}" \
      | grep -vxF 'EXPECTED-DELTA:' \
      | grep -qE '[^[:space:]]'; then
    echo "ERROR: EXPECTED-DELTA: 區塊為空"
    return 1
  fi
  return 0
}

# --only 捷徑：只跑具名檢查（未知名 fail-closed；勿靜默跑全部）
if [ -n "${only_check}" ]; then
  case "${only_check}" in
    expected-delta)
      _check_expected_delta "${brief}" || exit 2
      exit 0
      ;;
    *)
      echo "ERROR: 未知 --only 檢查名: ${only_check}（允許 expected-delta）" >&2
      exit 2
      ;;
  esac
fi

# ---------------------------------------------------------------------------
# brief 合規閘 P1-1(2026-07-24 使用者定;防「手搓 brief 漏掉範本必填條款」)
# 兩次實證事故(同一病根):手搓 brief 未引用範本 →
#   ①委員不知用 canonical 格式 → 產出 F-01/GROK-T1-01/無ID → completeness 抽不到
#     → Claude 手做 reconcile → 掉項(漏 grok T1-01)
#   ②未含 §0 挑戰前提 → Claude 的錯誤前提被當 finding 帶回(偽 finding C2)
# 治本(P1-1):不在此重列範本條款(會與範本漂移/漏),改**強制 brief 引用範本**(單一真相源)
#   + 補**任務專屬前提宣告**(fact-verified/assumed;範本給不了、每次必須 Claude 攤開)。
#   格式細節(canonical ID/四欄/§0-§3/Verdict)全由範本承載;閘只驗「有沒有用範本 + 有沒有攤前提」。
# 收集 findings 類 brief 缺 → 拒派(fail-closed)。impl/stamp 不產 findings → 不強制(不誤擋)。
# 對應範本:review/adversarial→SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT;語意審→COMMITTEE_SEMANTIC_REVIEW_TEMPLATE;
#   finding 格式→COMMITTEE_FINDING_TEMPLATE(三者互引,brief 引任一即涵蓋格式契約)。
# ---------------------------------------------------------------------------
# ⚠️ 必須【錨定行首】+【拒收多筆不一致宣告】(CODEX-R5-P0-01,2026-07-29 實跑 probe 證實):
#    未錨定時,brief 內任何一行註解如 `# brief-kind: review` 會被 head -1 取到而蓋掉真宣告
#    → 角色閘被繞過(非 implementer 可跑 impl)。此解析是角色閘的判定依據,故 fail-closed。
# 完整擷取宣告值（行首 brief-kind: → 行尾，trim 尾隨空白），再整值比對白名單。
# 禁止 grep -oE '...[a-z]+' 前綴擷取：stamp-evil 會被截成 stamp（與 committee_run 同步，CR2 群 E）。
_bk_all="$(grep -E '^brief-kind:' "${brief}" 2>/dev/null | sed 's/^brief-kind:[[:space:]]*//;s/[[:space:]]*$//' | sort -u)"
_bk_n="$(printf '%s\n' "${_bk_all}" | grep -c '[^[:space:]]' || true)"
if [ "${_bk_n}" -gt 1 ]; then
  echo "ERROR: brief 有多個【不一致】的行首 'brief-kind:' 宣告: $(printf '%s' "${_bk_all}" | tr '\n' ' ')"
  echo "  (角色閘與 brief 合規閘都依此判定,歧義一律 fail-closed)"
  exit 2
fi
_bk="$(printf '%s\n' "${_bk_all}" | head -1)"
# lifecycle 必須可解析（SSOT）；語法錯訊息含檔名
_lifecycle_json_ok || exit 2
[ -n "${_bk}" ] || {
  echo "ERROR: brief 缺 'brief-kind:' 宣告。請於 brief 加一行,值 ∈ review|consult|closure|impl|stamp"
  echo "  (收集 findings 類=review/consult/closure,會另檢範本引用+前提宣告)"
  exit 2
}
# 行為分支：findings 前置 + mutation 錨點（* 臂）。JSON SSOT 在 case 後對「命中 known arm」再驗。
_case_known=0
case "${_bk}" in
  review|consult|closure)
    _case_known=1
    # ① 強制引用委員範本(單一真相源承載 canonical ID/四欄/§0-§3/Verdict)
    grep -qE 'SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT|COMMITTEE_SEMANTIC_REVIEW_TEMPLATE|COMMITTEE_FINDING_TEMPLATE' "${brief}" \
      || { echo "ERROR: brief-kind=${_bk} 須**引用**委員範本(brief 內寫明 templates/<範本>.md 全文照做);"
           echo "  範本承載 canonical finding 格式+§0挑戰前提+Verdict,不引用委員不會照格式 → completeness 抽不到。"
           echo "  review/adversarial→SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT;語意審→COMMITTEE_SEMANTIC_REVIEW_TEMPLATE。"; exit 2; }
    # ② 任務專屬前提宣告(範本給不了):至少各一條 fact-verified / assumed
    #    逼 Claude 在寫 brief 當下攤開假設 → 錯誤前提死在筆下,不燒一輪委員(事故 C2)。
    # grep -c 未命中時 stdout=0 但 rc=1;用 || true 吞 rc(勿再 echo 0,否則變多行 "0\n0" 致 [ 炸)。
    _n_fact="$(grep -cE 'fact-verified:' "${brief}" 2>/dev/null || true)"
    _n_assumed="$(grep -cE 'assumed:' "${brief}" 2>/dev/null || true)"
    if [ "${_n_fact}" -lt 1 ] || [ "${_n_assumed}" -lt 1 ]; then
      echo "ERROR: brief-kind=${_bk} 須含任務專屬**前提宣告**(範本 §0):逐條標 'fact-verified: <前提> → <查證>' 或 'assumed: <前提>'。"
      echo "  現況:fact-verified=${_n_fact} assumed=${_n_assumed};**至少各 1 條**。"
      echo "  '至少一條 assumed':宣稱零假設本身可疑(沒有 brief 真的零假設);逼你攤開可疑前提,否則錯前提被當 finding 帶回(C2)。"
      exit 2
    fi
    ;;
  impl|stamp) _case_known=1 ;;
  *) echo "ERROR: 未知 brief-kind: ${_bk}(允許 review|consult|closure|impl|stamp)"; exit 2 ;;
esac
# U4：case known arm 命中但 JSON 無該 kind ⇒ fail-closed（SSOT＝JSON）
if [ "${_case_known}" -eq 1 ] && ! _bk_ok "${_bk}"; then
  echo "ERROR: 未知 brief-kind: ${_bk}(允許 review|consult|closure|impl|stamp)"
  exit 2
fi

# ---------------------------------------------------------------------------
# GOV-STAMP-TASKID-INJECT / D-001 §D3 defense-in-depth：brief-kind=stamp 驗證 stamp-target
# 與 committee_run.sh 同判準；涵蓋直呼 cx_run 路徑（不經 committee_run）。
# 失敗 rc=2；其餘 brief-kind 不解析、不強制。
# ---------------------------------------------------------------------------
stamp_target=""
if [ "${_bk}" = "stamp" ]; then
  _st_all="$(grep -E '^stamp-target:' "${brief}" 2>/dev/null | sed 's/^stamp-target:[[:space:]]*//;s/[[:space:]]*$//' | sort -u)"
  _st_n="$(printf '%s\n' "${_st_all}" | grep -c '.' || true)"
  if [ "${_st_n}" -eq 0 ]; then
    echo "ERROR: brief-kind=stamp 缺 stamp-target: 欄" >&2
    exit 2
  fi
  if [ "${_st_n}" -gt 1 ]; then
    echo "ERROR: stamp-target 有多個【不一致】宣告: $(printf '%s' "${_st_all}" | tr '\n' ' ')" >&2
    exit 2
  fi
  stamp_target="$(printf '%s\n' "${_st_all}" | head -1)"
  case "${stamp_target}" in
    handoffs/*) : ;;
    *) echo "ERROR: stamp-target 須 handoffs/ 前綴: ${stamp_target}" >&2; exit 2 ;;
  esac
  case "${stamp_target}" in
    *"/../"*|"../"*|*".."*)
      echo "ERROR: stamp-target 不得含 ..: ${stamp_target}" >&2
      exit 2
      ;;
  esac
  [ -f "${stamp_target}" ] || { echo "ERROR: stamp-target 檔不存在: ${stamp_target}" >&2; exit 2; }
fi

# ---------------------------------------------------------------------------
# Task 1.2 — finding ID 樣板驗證（三限縮：findings-kind ＋ active ＋ placeholder-aware ＋ canonical）
# CANONICAL_ID_RE 引用 completeness_check.sh，禁重寫。
# COMPOSER-R1-P1-03：_is_active 須含任務區反引號內 FAMILY-SEG-P token（非僅宣告行）。
# ---------------------------------------------------------------------------
_canon_re() {
  grep -m1 '^CANONICAL_ID_RE=' "${SCRIPT_DIR}/completeness_check.sh" | cut -d"'" -f2
}

_is_findings_kind() {
  # $1=brief-kind 值
  case "$1" in
    review|consult|closure) return 0 ;;
    *) return 1 ;;
  esac
}

_strip_code_fences() {
  # stdin → stdout：去掉 ``` … ``` 區塊（邊界②：fence 內不掃）
  # 閉合標記允許前置空白（/^[[:space:]]*```/）；未閉合 → exit 2（fail-closed，禁吞至 EOF）
  # 策略 (a)：未閉合即視為格式錯，呼叫端須 rc≠0 並輸出可辨識訊息（不得靜默放行）
  awk '
    BEGIN { fence = 0 }
    /^[[:space:]]*```/ { fence = !fence; next }
    !fence { print }
    END {
      if (fence) exit 2
    }
  '
}

_strip_code_fences_file() {
  # $1=src_path $2=dst_path → rc 0=ok；2=未閉合 fence（stdout 已寫 ERROR）
  if ! _strip_code_fences < "$1" > "$2"; then
    echo "ERROR: unclosed code fence (\`\`\`) — fail-closed"
    echo "  說明: 未閉合 fence 不得吞掉其後所有 active 宣告（禁吞至 EOF）"
    echo "  修法: 補上閉合 \`\`\`（閉合列允許前置空白），或刪除未閉合的起始 fence"
    return 2
  fi
  return 0
}

_is_placeholder_token() {
  # $1=token；placeholder-aware：角括號／字面 FAMILY／YOUR／xxx 等
  case "$1" in
    *'<'*|*'>'*|*…*|*'...'*) return 0 ;;
    FAMILY-*|YOUR-*|*PLACEHOLDER*|*xxx*|*XXX*) return 0 ;;
  esac
  return 1
}

# 自 brief 抽出「active」ID-like token（去 fence；反引號內 ＋ 行首 ## 標題）
# 樣板族：FAMILY-SEG-P[0-3]-NN（SEG 可為 B0R／R1 等，後續再套 canonical）
# 未閉合 fence → rc=2（與 _select_fact_verified_decl_lines 同 fail-closed）
_active_id_tokens() {
  # $1=brief_path → stdout=tokens；rc 0=ok；2=未閉合 fence
  _src="$1"
  _tmp="$(mktemp "${TMPDIR:-/tmp}/bcc_id.XXXXXX")"
  if ! _strip_code_fences_file "${_src}" "${_tmp}"; then
    rm -f "${_tmp}"
    return 2
  fi
  awk '
    # 反引號內 token
    {
      line = $0
      while (match(line, /`[A-Z]+-[A-Za-z0-9]+-P[0-3]-[0-9]{2,}`/)) {
        tok = substr(line, RSTART + 1, RLENGTH - 2)
        print tok
        line = substr(line, RSTART + RLENGTH)
      }
    }
    # 行首 ## FAMILY-… 標題（canonical finding heading）
    /^##[[:space:]]+[A-Z]+-[A-Za-z0-9]+-P[0-3]-[0-9]{2,}([[:space:]]|$)/ {
      if (match($0, /[A-Z]+-[A-Za-z0-9]+-P[0-3]-[0-9]{2,}/)) {
        print substr($0, RSTART, RLENGTH)
      }
    }
  ' "${_tmp}"
  rm -f "${_tmp}"
  return 0
}

_check_id_pattern() {
  # $1=brief_path → rc 0=ok；非 0=不合規（訊息走 stdout，與既有 ERROR 同通道）
  # 無 active token 時不讀 completeness_check.sh（隔離 fixture 常不拷該檔；邊界①）
  _brief_p="$1"
  _bk_val="$(grep -E '^brief-kind:' "${_brief_p}" 2>/dev/null | head -1 \
    | sed 's/^brief-kind:[[:space:]]*//;s/[[:space:]]*$//')"
  _is_findings_kind "${_bk_val}" || return 0

  if ! _toks="$(_active_id_tokens "${_brief_p}")"; then
    # 未閉合 fence：ERROR 可能被 command substitution 吸入 _toks — 轉出 stdout
    [ -n "${_toks}" ] && printf '%s\n' "${_toks}"
    return 1
  fi
  [ -n "${_toks}" ] || return 0

  _re="$(_canon_re)"
  [ -n "${_re}" ] || {
    echo "ERROR: 無法自 completeness_check.sh 讀取 CANONICAL_ID_RE"
    return 1
  }

  _bad=0
  while IFS= read -r _tok; do
    [ -n "${_tok}" ] || continue
    _is_placeholder_token "${_tok}" && continue
    # canonical 全字匹配（_re 已含 ^$）
    if ! printf '%s\n' "${_tok}" | grep -qE "${_re}"; then
      echo "ERROR: brief 內 finding ID 樣板不合規"
      echo "  違規 token: ${_tok}"
      echo "  期望樣式:   ${_re}"
      # 修法：指出中間段（第二欄）
      _mid="$(printf '%s' "${_tok}" | awk -F- '{print $2}')"
      echo "  修法:       把 ${_mid} 改為 R<數字>（例：B0R → R1；須符合 R[0-9]+）"
      _bad=1
    fi
  done <<EOF
${_toks}
EOF

  [ "${_bad}" -eq 0 ]
}

# ---------------------------------------------------------------------------
# Task 1.4 — fact-verified: 兩機械規則
# 規則①：count: 宣稱不得含截斷運算子（先抽反引號指令再 token 化；禁照抄 TODO _has_trunc）
# 規則②：rc 會被派工改變之指令集合有界——debt_ledger --has-open、gate_check token 新鮮度
#         須標「派工後預期值」
# ---------------------------------------------------------------------------
# 🔴 二分封閉判準〔CODEX-R2-P1-04／STAMP-R4／review-r3 NEW-CLASS〕——禁第三種分支、禁列舉變體：
#   A) 抽出 ≥1 個良構指令（成對、非巢狀、單行內閉合、段間僅分隔符、trim 後非空）⇒ 逐一 _has_trunc
#   B) 其餘（未成對／巢狀／跨行／零抽取／段間含詞元／純空白段）⇒ 明確拒絕
# 段間分隔符有界集合（禁開放式「非英數皆分隔符」）：[[:space:]] | ； | ; | 、 | ,
_extract_cmds() {
  # $1=含 count: 之列 → stdout=所有反引號內指令（一行一則）
  # rc=0：良構且 ≥1；rc=2：非良構或零抽取（呼叫端須 FAIL）
  _line="$1"
  # 反引號個數（字節計）
  _nbt="$(printf '%s' "${_line}" | tr -cd '`' | wc -c | tr -d ' ')"
  if [ "${_nbt}" -eq 0 ]; then
    return 2
  fi
  if [ $((_nbt % 2)) -ne 0 ]; then
    return 2
  fi
  # 以 ` 切開：奇數欄=指令段、偶數欄(≥2)=段間文字。
  # 段間必須為純分隔符；指令段 trim 後不得為空（關閉 `` `   ` `` 假綠）。
  # 偶數巢狀反例 `` `echo outer `date` more` ``：段間=`date` 含詞元 ⇒ 拒。
  _cmds="$(
    printf '%s' "${_line}" | awk '
      BEGIN { FS = "`" }
      {
        nbt = NF - 1
        if (nbt <= 0 || nbt % 2 != 0) exit 2
        ncmd = 0
        out = ""
        for (i = 2; i <= NF; i += 2) {
          cmd = $i
          gsub(/^[[:space:]]+/, "", cmd)
          gsub(/[[:space:]]+$/, "", cmd)
          if (cmd == "") exit 2
          if (ncmd > 0) {
            inter = $(i - 1)
            tmp = inter
            gsub(/[[:space:]；;、,]/, "", tmp)
            if (tmp != "") exit 2
          }
          ncmd++
          if (out != "") out = out "\n"
          out = out $i
        }
        if (ncmd == 0 || ncmd != nbt / 2) exit 2
        print out
        exit 0
      }
    '
  )" || return 2
  [ -n "${_cmds}" ] || return 2
  _ncmd="$(printf '%s\n' "${_cmds}" | grep -c . || true)"
  [ "${_ncmd}" -eq $((_nbt / 2)) ] || return 2
  printf '%s\n' "${_cmds}"
  return 0
}

_has_trunc() {
  # $1=已抽出之指令（非整行）。截斷 token：head｜tail｜-mN｜-m N
  # 白名單排除：python -m｜python3 -m｜pytest -m（模組／標記，非截斷）
  _cmd="$1"
  [ -n "${_cmd}" ] || return 1
  # 白名單：整段視為非截斷（先剔除再判）
  _norm="$(printf '%s' "${_cmd}" \
    | sed -E \
      -e 's/(^|[[:space:]])python3?[[:space:]]+-m([[:space:]]|$)/ /g' \
      -e 's/(^|[[:space:]])pytest[[:space:]]+-m([[:space:]]|$)/ /g')"
  # head / tail 作為獨立 token（允許指令以 head 起頭，含 backtick 已剝）
  if printf '%s' "${_norm}" | grep -qE '(^|[[:space:]|])(head|tail)([[:space:]|]|$)'; then
    return 0
  fi
  # -mN 或 -m N（grep -m1 必須擋；空白可選）
  if printf '%s' "${_norm}" | grep -qE '(^|[[:space:]])-m[[:space:]]*[0-9]+'; then
    return 0
  fi
  return 1
}

# 選列判準（review-r4 NEW-CLASS ＋ review-r5 REGRESSION 修）——決定哪些列進解析器；**不得**改動 _extract_cmds。
# ① 先剝 fenced code（```…```；閉合可前置空白；未閉合 fail-closed）
# ② 錨定行首宣告：前置符號為**有界集合**（可重複、可夾空白；禁開放式「任意非字母」）
#    集合：- / * / + / > ／ 有序清單 N. ／ N) ／ 粗體 ** ／ 前置空白
# ③ count: 觸發改獨立 token（禁子字串誤匹配 max_count:／foo_count: 等）
# ERE：(([-*+>]|[0-9]+[.)]|\*\*)[[:space:]]*)*  — 有界，非「任意非字母」
_FACT_VERIFIED_DECL_RE='^[[:space:]]*(([-*+>]|[0-9]+[.)]|\*\*)[[:space:]]*)*fact-verified:'
_COUNT_TOKEN_RE='(^|[^[:alnum:]_])count:'

_select_fact_verified_decl_lines() {
  # $1=brief_path → stdout=active 宣告列（已去 fence、已錨定行首）
  # rc 0=ok；2=未閉合 fence（ERROR 已寫 stdout）
  _src="$1"
  _tmp="$(mktemp "${TMPDIR:-/tmp}/bcc_fv.XXXXXX")"
  if ! _strip_code_fences_file "${_src}" "${_tmp}"; then
    rm -f "${_tmp}"
    return 2
  fi
  grep -E "${_FACT_VERIFIED_DECL_RE}" "${_tmp}" || true
  rm -f "${_tmp}"
  return 0
}

_line_has_count_token() {
  # $1=line；count: 為獨立 token（前為行首或非 alnum/_）
  printf '%s' "$1" | grep -qE "${_COUNT_TOKEN_RE}"
}

_check_fact_verified() {
  # $1=brief_path → rc 0=ok
  _brief_p="$1"
  _bad=0
  _lines_tmp="$(mktemp "${TMPDIR:-/tmp}/bcc_sel.XXXXXX")"
  if ! _select_fact_verified_decl_lines "${_brief_p}" > "${_lines_tmp}"; then
    # 未閉合 fence：ERROR 被重導進 _lines_tmp — 轉出 stdout（fail-closed）
    cat "${_lines_tmp}"
    rm -f "${_lines_tmp}"
    return 1
  fi
  while IFS= read -r _line || [ -n "${_line}" ]; do
    [ -n "${_line}" ] || continue
    # 規則①：僅明示 count: 標記（獨立 token，非子字串）
    if _line_has_count_token "${_line}"; then
      _cmds=""
      if ! _cmds="$(_extract_cmds "${_line}")"; then
        echo "ERROR: count: 宣稱之指令段須為成對反引號且不得為空"
        echo "  違規列: ${_line}"
        echo "  修法: 以成對反引號包住完整指令（單行、非巢狀），且至少一組"
        _bad=1
      else
        while IFS= read -r _cmd || [ -n "${_cmd}" ]; do
          [ -n "${_cmd}" ] || continue
          if _has_trunc "${_cmd}"; then
            echo "ERROR: fact-verified 計數宣稱含截斷運算子（head/tail/-mN）"
            echo "  違規列: ${_line}"
            echo "  抽出指令: ${_cmd}"
            echo "  修法: 改用不截斷指令重算 count，或去掉 count: 標記（改為非計數宣稱）"
            _bad=1
            break
          fi
        done <<EOF
${_cmds}
EOF
      fi
    fi
    # 規則②：有界集合——派工會改 rc 者須標「派工後預期值」
    if printf '%s' "${_line}" | grep -qE 'debt_ledger.*--has-open|gate_check.*token|token.*新鮮'; then
      if ! printf '%s' "${_line}" | grep -q '派工後預期值'; then
        echo "ERROR: fact-verified 引用派工會改變之 rc，須標註「派工後預期值」"
        echo "  違規列: ${_line}"
        echo "  判定集合（有界）: debt_ledger --has-open｜gate_check token 新鮮度"
        echo "  修法: 在同一 fact-verified 列加上「派工後預期值: <rc 或狀態>」"
        _bad=1
      fi
    fi
  done < "${_lines_tmp}"
  rm -f "${_lines_tmp}"

  [ "${_bad}" -eq 0 ]
}

if [ -n "${emit_file}" ]; then
  # 兩行固定格式；第 2 行恆存在（非 stamp 為空行），呼叫端可用 sed -n '2p' 穩定取值
  printf '%s\n%s\n' "${_bk}" "${stamp_target}" > "${emit_file}" || {
    echo "ERROR: 無法寫入 --emit 檔: ${emit_file}" >&2; exit 2; }
fi

# Task 1.2：ID 樣板（findings-kind 限縮內）
_check_id_pattern "${brief}" || exit 2

# Task 1.4：fact-verified 兩機械規則
_check_fact_verified "${brief}" || exit 2

# Task 1.3：EXPECTED-DELTA（impl 必填非空；非 impl 跳過）
_check_expected_delta "${brief}" || exit 2

exit 0
