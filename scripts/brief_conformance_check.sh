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
#     --emit <kv_file>：成功時把解析結果寫入該檔，第 1 行 = brief-kind，第 2 行 = stamp-target（非 stamp 為空行）
#                       （**不用 stdout 回傳**：既有錯誤訊息就走 stdout，呼叫端若重導 stdout 會把訊息吃掉）
#   rc: 0=合規；2=不合規/用法錯。
#
# ⚠️ 訊息輸出通道與抽出前**逐字相同**（brief-kind 段走 stdout、stamp-target 段走 stderr）。
#    既有測試 tests/governance/test_stamp_taskid_inject.py 對兩者分別斷言，改通道＝弄紅既有測試。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
_LIFECYCLE_JSON="${SCRIPT_DIR}/govflow_lifecycle.json"
_LIFECYCLE_EMBED_B64='ewogICJfZG9jIjogIkdPVkIxIFRhc2sgMS4xIOKAlCBicmllZi1raW5kIGxpZmVjeWNsZSBtYXRyaXjvvIjllq7kuIDnnJ/nm7jmupDvvInjgIJcblxuc2luZ2xlLXdyaXRlciDlpZHntITvvJpcbiAgLSBUYXNrIDEuMSDnjajljaDlu7rnq4vpoILlsaQgc2NoZW1h77yI5pys5qqU5LmLIGtpbmRz77yPc3RhZ2Vz77yPX2RvY++8ieOAglxuICAtIFRhc2sgMS4zIOWPquW+l+aWsOWinuWFt+WQjeevgCBleHBlY3RlZF9kZWx0Ye+8m+emgeaUueaXouacieevgOOAglxuICAtIFRhc2sgNC4yIOWPquW+l+aWsOWinuWFt+WQjeevgCB6ZXJvX2ZpbmRpbmdzX2NvbnRyYWN077yb56aB5pS55pei5pyJ56+A44CCXG4gIC0g5b6M57qMIFRhc2sg5a6M5oiQ5b6M6aCIIGpxIC1yICdrZXlzW10nIOmpl+eCuuWJjeS4gCBUYXNrIOe1kOaenOS5i+i2hembhuOAglxuXG7mnproiInpgornlYzvvIjli7/mt7fvvInvvJpcbiAgLSDmnKzmqpQga2luZHMg55qEIGtleSDvvJ0gYnJpZWYta2luZO+8iHJldmlld3xjb25zdWx0fGNsb3N1cmV8aW1wbHxzdGFtcO+8ieOAglxuICAtIGRlYnRfY2xlYXIg5qyE77yd6KmyIGJyaWVmLWtpbmQg55qE44CM6Yq35biz5YmN572u5qKd5Lu244CN5o+P6L+w77yM5LiN5pivIENMSSDml5fmqJnjgIJcbiAgLSBzY3JpcHRzL2RlYnRfY2xlYXIuc2ggLS1raW5kIOaYryBhYmFuZG9uX2tpbmTvvIhuby1maW5kaW5ncy1leHBlY3RlZHxjb2xsZWN0aW9uLWZhaWxlZO+8ie+8jFxuICAgIOaemuiIiea6kOiHqiBzY3JpcHRzL2F1ZGl0X2V2ZW50cy5qc29uIGVudW1zLmFiYW5kb25fa2luZOKAlOKAlOiIhyBicmllZi1raW5kIOaYr+S4jeWQjOaemuiIieOAglxuXG7mtojosrvnq6/vvJpzY3JpcHRzL2JyaWVmX2NvbmZvcm1hbmNlX2NoZWNrLnNo44CBc2NyaXB0cy9jeF9ydW4uc2gg5Y+q5YeG6K6A5pys5qqU5Y+WIGtpbmQg6ZuG5ZCI6IiH6ZqO5q615peX5qiZ77ybXG7npoHlnKjohbPmnKzlhaflho3noaznt6jnorwga2luZCDnmb3lkI3llq7miJYgZmFsbGJhY2vjgIJKU09OIOe8uiBraW5k77yP6Kqe5rOV6YyvIOKHkiBmYWlsLWNsb3NlZCByY+KJoDDvvIzoqIrmga/lkKvmnKzmqpTlkI3jgIIiLAogICJzdGFnZXMiOiB7CiAgICAiX2RvYyI6ICJicmllZiDnlJ/lkb3pgLHmnJ/pmo7mrrXpoIbluo/jgILmnKwgbWF0cml4IOimhuiTi+WIsCByZWNvbmNpbGUg5LmL5YmN55qE5rS+5bel6Y+I77ybcmVjb25jaWxlIC0tbW9kZSDoiIcgYnJpZWYta2luZCDmnproiInlsI3pvYrlsaznpaggQi0xM++8jOS4jeWcqOacrCBUYXNr44CCIiwKICAgICJvcmRlciI6IFsKICAgICAgInByZWNoZWNrIiwKICAgICAgImN4X3J1biIsCiAgICAgICJyZWNvbmNpbGUiLAogICAgICAiZGVidF9jbGVhciIKICAgIF0KICB9LAogICJraW5kcyI6IHsKICAgICJyZXZpZXciOiB7CiAgICAgICJyZXF1aXJlc190ZW1wbGF0ZV9hbmRfcHJlbWlzZXMiOiB0cnVlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiB0cnVlLAogICAgICAic3RhbXBfcHJvbXB0X2luamVjdCI6IGZhbHNlLAogICAgICAiY29tcGxldGVuZXNzX3NlbGZjaGVjayI6IHRydWUsCiAgICAgICJkZWJ0X2NsZWFyIjogewogICAgICAgICJfZG9jIjogIumKt+W4s+WJjee9ruaineS7tu+8iOmdniBhYmFuZG9uX2tpbmTvvInjgILmraPopo/pirfluLPpoIjlkITlrrbml48gcmVzdWx0X3N0YXRlPXN1Y2Nlc3Mg5LiUIHNvdXJjZXMubG9jayDlj6/mlLbmloLvvJvnhKEgZmluZGluZ3Mg5pyf5pyb5pmC6LWwIGRlYnRfY2xlYXIgLS1raW5kIGFiYW5kb24g55qEIGFiYW5kb25fa2luZCDmnproiInvvIjkuI3lkIzlkb3lkI3nqbrplpPvvInjgIIiLAogICAgICAgICJwcmVjb25kaXRpb25zIjogWwogICAgICAgICAgImFsbF9mYW1pbGllc190ZXJtaW5hbCIsCiAgICAgICAgICAiZm9ybWF0X29rX3doZW5fZmluZGluZ3Nfa2luZCIsCiAgICAgICAgICAic291cmNlc19sb2NrX2NvbnZlcmdlZF9vcl9hYmFuZG9uIgogICAgICAgIF0KICAgICAgfSwKICAgICAgInN0YWdlcyI6IHsKICAgICAgICAicHJlY2hlY2siOiAiYnJpZWZfY29uZm9ybWFuY2XvvJrnr4TmnKzlvJXnlKggKyBmYWN0LXZlcmlmaWVkL2Fzc3VtZWTvvJtyb2xlX2dhdGXvvJpmYW1pbHkgIT0gaW1wbGVtZW50ZXIiLAogICAgICAgICJjeF9ydW4iOiAiZm9ybWF0IGNoZWNrICsgY29tcGxldGVuZXNzIOiHquaqoiBwcm9tcHTvvJvkuI3ms6jlhaUgUkVDT05DSUxFLVNUQU1QIiwKICAgICAgICAicmVjb25jaWxlIjogIuaUtumbhiBmaW5kaW5nc++8m2NvbXBsZXRlbmVzcyAvIHNvdXJjZXMubG9jayIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfSwKICAgICJjb25zdWx0IjogewogICAgICAicmVxdWlyZXNfdGVtcGxhdGVfYW5kX3ByZW1pc2VzIjogdHJ1ZSwKICAgICAgInByb2R1Y2VzX2ZpbmRpbmdzIjogdHJ1ZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiBmYWxzZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiB0cnVlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICLlkIwgcmV2aWV377yaZmluZGluZ3Mta2luZCDmraPopo/pirfluLPmop3ku7bvvJthYmFuZG9uX2tpbmQg5Y+m5YaK44CCIiwKICAgICAgICAicHJlY29uZGl0aW9ucyI6IFsKICAgICAgICAgICJhbGxfZmFtaWxpZXNfdGVybWluYWwiLAogICAgICAgICAgImZvcm1hdF9va193aGVuX2ZpbmRpbmdzX2tpbmQiLAogICAgICAgICAgInNvdXJjZXNfbG9ja19jb252ZXJnZWRfb3JfYWJhbmRvbiIKICAgICAgICBdCiAgICAgIH0sCiAgICAgICJzdGFnZXMiOiB7CiAgICAgICAgInByZWNoZWNrIjogImJyaWVmX2NvbmZvcm1hbmNl77ya56+E5pys5byV55SoICsgZmFjdC12ZXJpZmllZC9hc3N1bWVk77ybcm9sZV9nYXRl77ya5LiN6ZmQ5Yi2IGltcGxlbWVudGVyIiwKICAgICAgICAiY3hfcnVuIjogImZvcm1hdCBjaGVjayArIGNvbXBsZXRlbmVzcyDoh6rmqqIgcHJvbXB077yb5LiN5rOo5YWlIFJFQ09OQ0lMRS1TVEFNUCIsCiAgICAgICAgInJlY29uY2lsZSI6ICLmlLbpm4YgZmluZGluZ3PvvJtjb21wbGV0ZW5lc3MgLyBzb3VyY2VzLmxvY2siLAogICAgICAgICJkZWJ0X2NsZWFyIjogIuimiyBkZWJ0X2NsZWFyLnByZWNvbmRpdGlvbnMiCiAgICAgIH0KICAgIH0sCiAgICAiY2xvc3VyZSI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IHRydWUsCiAgICAgICJwcm9kdWNlc19maW5kaW5ncyI6IHRydWUsCiAgICAgICJzdGFtcF9wcm9tcHRfaW5qZWN0IjogdHJ1ZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiB0cnVlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICJjbG9zdXJlIOeUoiBmaW5kaW5ncyDkuJQgcHJvbXB0IOWQq+aIs+iomOaMh+ekuu+8m+mKt+W4s+S7jeS+nSBzdWNjZXNz77yPYWJhbmRvbiDot6/lvpHvvIzpnZ4gYWJhbmRvbl9raW5kIOa3t+WFpSBraW5kc+OAgiIsCiAgICAgICAgInByZWNvbmRpdGlvbnMiOiBbCiAgICAgICAgICAiYWxsX2ZhbWlsaWVzX3Rlcm1pbmFsIiwKICAgICAgICAgICJmb3JtYXRfb2tfd2hlbl9maW5kaW5nc19raW5kIiwKICAgICAgICAgICJzb3VyY2VzX2xvY2tfY29udmVyZ2VkX29yX2FiYW5kb24iCiAgICAgICAgXQogICAgICB9LAogICAgICAic3RhZ2VzIjogewogICAgICAgICJwcmVjaGVjayI6ICJicmllZl9jb25mb3JtYW5jZe+8muevhOacrOW8leeUqCArIGZhY3QtdmVyaWZpZWQvYXNzdW1lZO+8m3JvbGVfZ2F0Ze+8muS4jemZkOWItiIsCiAgICAgICAgImN4X3J1biI6ICJmb3JtYXQgY2hlY2sgKyDoh6rmqqIgcHJvbXB0ICsgUkVDT05DSUxFLVNUQU1QIOazqOWFpeWPpSIsCiAgICAgICAgInJlY29uY2lsZSI6ICLmlLbpm4YgZmluZGluZ3PvvJvlj6/lkKvmiLPoqJjopIfpqZciLAogICAgICAgICJkZWJ0X2NsZWFyIjogIuimiyBkZWJ0X2NsZWFyLnByZWNvbmRpdGlvbnMiCiAgICAgIH0KICAgIH0sCiAgICAiaW1wbCI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IGZhbHNlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiBmYWxzZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiBmYWxzZSwKICAgICAgImNvbXBsZXRlbmVzc19zZWxmY2hlY2siOiBmYWxzZSwKICAgICAgImRlYnRfY2xlYXIiOiB7CiAgICAgICAgIl9kb2MiOiAiaW1wbCDkuI3nlKIgY2Fub25pY2FsIGZpbmRpbmcgSUTvvJvpirfluLPliY3nva7ngrrlrrbml48gc3VjY2Vzc++8iOaIliBhYmFuZG9uX2tpbmQg5piO56S677yJ77yM5LiN6LeRIGZpbmRpbmdzIOaUtuaWguOAgiIsCiAgICAgICAgInByZWNvbmRpdGlvbnMiOiBbCiAgICAgICAgICAiYWxsX2ZhbWlsaWVzX3Rlcm1pbmFsIiwKICAgICAgICAgICJub19maW5kaW5nc19mb3JtYXRfZ2F0ZSIKICAgICAgICBdCiAgICAgIH0sCiAgICAgICJzdGFnZXMiOiB7CiAgICAgICAgInByZWNoZWNrIjogImJyaWVmX2NvbmZvcm1hbmNl77ya5YOFIGtpbmQg55m95ZCN5Zau77ybcm9sZV9nYXRl77yaZmFtaWx5ID09IGltcGxlbWVudGVyIiwKICAgICAgICAiY3hfcnVuIjogIueEoSBmb3JtYXQgY2hlY2vvvI/nhKEgUkVDT05DSUxFLVNUQU1QIOazqOWFpSIsCiAgICAgICAgInJlY29uY2lsZSI6ICLpgJrluLjnhKEgZmluZGluZ3Mg5pS25paC77yIbm8tZmluZGluZ3MtZXhwZWN0ZWQg5bGsIGFiYW5kb25fa2luZO+8iSIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfSwKICAgICJzdGFtcCI6IHsKICAgICAgInJlcXVpcmVzX3RlbXBsYXRlX2FuZF9wcmVtaXNlcyI6IGZhbHNlLAogICAgICAicHJvZHVjZXNfZmluZGluZ3MiOiBmYWxzZSwKICAgICAgInN0YW1wX3Byb21wdF9pbmplY3QiOiB0cnVlLAogICAgICAiY29tcGxldGVuZXNzX3NlbGZjaGVjayI6IGZhbHNlLAogICAgICAiZGVidF9jbGVhciI6IHsKICAgICAgICAiX2RvYyI6ICJzdGFtcCDovKrms6jlhaUgUkVDT05DSUxFLVNUQU1Q77yb6Yq35biz55yL5a625pePIHN1Y2Nlc3PvvIzkuI3ntpMgZmluZGluZ3MgZm9ybWF0IGdhdGXjgIIiLAogICAgICAgICJwcmVjb25kaXRpb25zIjogWwogICAgICAgICAgImFsbF9mYW1pbGllc190ZXJtaW5hbCIsCiAgICAgICAgICAibm9fZmluZGluZ3NfZm9ybWF0X2dhdGUiCiAgICAgICAgXQogICAgICB9LAogICAgICAic3RhZ2VzIjogewogICAgICAgICJwcmVjaGVjayI6ICJicmllZl9jb25mb3JtYW5jZe+8mmtpbmQgKyBzdGFtcC10YXJnZXQg6Lev5b6R77yP5a2Y5Zyo5oCn77ybcm9sZV9nYXRl77ya5LiN6ZmQ5Yi2IiwKICAgICAgICAiY3hfcnVuIjogIlJFQ09OQ0lMRS1TVEFNUCDms6jlhaXvvJtyZWdpc3Rlci1vdXRwdXQg5qKd5Lu26Lev5b6R77yIX21heWJlX3JlZ2lzdGVyX3N0YW1wX291dHB1dO+8jEctNiDlh43ntZDvvIkiLAogICAgICAgICJyZWNvbmNpbGUiOiAi5oiz6KiY6KSH6amX77yIcmVjb25jaWxlX3N0YW1wc19jaGVja++8iSIsCiAgICAgICAgImRlYnRfY2xlYXIiOiAi6KaLIGRlYnRfY2xlYXIucHJlY29uZGl0aW9ucyIKICAgICAgfQogICAgfQogIH0KfQo='

_lifecycle_resolve() {
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
  # 缺檔：只回傳 temp 路徑（唯讀物化）。禁止 cp 回 repo／隔離目錄（靜默寫檔＝假綠源）。
  # 「缺 JSON fail-closed」落在 govb1_final_gate lifecycle_embed 閘，不在此執行期。
  printf '%s\n' "${_tmp}"
  return 0
}

_lifecycle_json_ok() {
  _lifecycle_resolve >/dev/null
}

_valid_kinds() {
  _p="$(_lifecycle_resolve)" || return 1
  jq -r '.kinds | keys[]' "${_p}"
}

_bk_ok() {
  _valid_kinds | grep -qx "$1"
}


brief="${1:-}"
emit_file=""
shift 2>/dev/null || true
while [ "$#" -gt 0 ]; do
  case "$1" in
    --emit)
      [ "$#" -ge 2 ] || { echo "ERROR: --emit 需要參數" >&2; exit 2; }
      emit_file="$2"; shift 2 ;;
    *) echo "ERROR: 未知旗標: $1" >&2; exit 2 ;;
  esac
done

[ -n "${brief}" ] || {
  echo "用法: bash scripts/brief_conformance_check.sh <brief_path> [--emit <kv_file>]" >&2; exit 2; }
[ -f "${brief}" ] || { echo "ERROR: brief 檔不存在: ${brief}" >&2; exit 2; }

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

if [ -n "${emit_file}" ]; then
  # 兩行固定格式；第 2 行恆存在（非 stamp 為空行），呼叫端可用 sed -n '2p' 穩定取值
  printf '%s\n%s\n' "${_bk}" "${stamp_target}" > "${emit_file}" || {
    echo "ERROR: 無法寫入 --emit 檔: ${emit_file}" >&2; exit 2; }
fi
exit 0
