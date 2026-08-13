#!/usr/bin/env bash
# factkey_write_guard.sh — fact-key 機制之「產出端」檢查（GOV-FACTKEY-CHECK-AT-WRITE，2026-08-13）。
#
# 病根（使用者 2026-08-13 逐字）：
#   「到 git push 才做等於全部都可以廢掉不需要，所有的上百項治理問題，全部都是在產出就發生問題，
#     這連留到下一節點派工都已經是摩擦，所有在產出完成前沒辦法擋的都等於沒意義」
#
#   `票 B-25` 三段（WL-01/02/03）交付後，其**全部**檢查只掛在 `gov_check.sh` 第 3 段，
#   而該段只由 pre-push 觸發 ⇒ 檢查點在**消費端**。這違反使用者 2026-08-02 定死的
#   治理三原則第 3 條「檢查點放產出端非消費端」（記憶 feedback_tools_must_enforce）。
#
#   實證代價（本 session 親身）：`tests/governance/fixtures/govb1/factkey_drifted` 的竄改列
#   被 `--write` 洗掉 **5 次**，每次都是事後才想起來補；戳記貼錯收斂檔一路活到被人工查出。
#   兩者都是「產出當下就錯，但要到很後面才發現」。
#
# 強制機制（三層，體例同 `doc_format_precheck.sh`）：
#   ① `.claude/settings.json` 的 **PostToolUse `Edit|Write`**：寫檔當下自動跑，exit 2 回灌 context
#   ② `scripts/gov_check.sh` 第 3 段：pre-push 全掃（既有，不動）
#   ③ 派工／freeze 時之 fail-closed（既有，不動）
#   本腳本是第 ① 層。**它不取代 ②③**——defense-in-depth，任一層都不得因本層存在而放寬。
#
# 🔴 誠實邊界（逐條講清楚，不誇大）：
#   1. PostToolUse 在寫入**之後**跑 ⇒ 這是**早期警告，不是硬閘**，擋不掉已落地的內容。
#      它把「發現時機」從 push 前移到寫檔當下，**不改變**任何判定的寬嚴。
#   2. **只涵蓋 Edit|Write 工具**。經 Bash 重導寫出的檔（含本專案的 `gen_fact_key_blocks.sh --write`
#      自己）、外部編輯器、git 操作，**都不會觸發**。那些仍由第 ②③ 層接。
#      ⇒ 因此「跑完 --write 之後 fixture 被洗掉」這件事本層**抓不到**，
#        要靠下一次有人 Edit 受管檔時才順帶發現。已知缺口，不宣稱已封。
#   3. 受管集合**由註冊表機械導出**（target ∪ mechanism_scope ∪ status_scope ∪ 註冊表自身），
#      新增 key／宿主自動納入，不需改本腳本。這是刻意的——寫死清單就是下一個過期副本。
#   4. 路徑判不出、jq 缺、註冊表不可讀 ⇒ **靜默放行**（rc=0）。hook 絕不能因自己失敗而擋住工作；
#      🔴 這是**本層刻意的 fail-open**，其代價由第 ②③ 層承接（那兩層是 fail-closed）。
#   5. 檔案編到一半必然不合規（例如改了 `fact_keys.json` 還沒跑 `--write`）⇒ 會報紅。
#      **預期行為**，訊息已標明修法一行。
#
# 用法：
#   bash scripts/factkey_write_guard.sh <file>   # 直接檢查某檔
#   bash scripts/factkey_write_guard.sh          # hook 模式：從 stdin 的 JSON 取 file_path
# rc: 0=合規／不適用；2=不合規（訊息在 stderr，hook 回灌 context）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REG="${SCRIPT_DIR}/fact_keys.json"
GEN="${SCRIPT_DIR}/gen_fact_key_blocks.sh"

target="${1:-}"

# hook 模式：PostToolUse 以 stdin 餵 JSON，取 tool_input.file_path。
# 取不到就靜默放行（見邊界 4）。
if [ -z "${target}" ]; then
  if [ -t 0 ]; then
    exit 0
  fi
  target="$(python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
ti = d.get("tool_input") or {}
p = ti.get("file_path") or ti.get("path") or ""
print(p if isinstance(p, str) else "")' 2>/dev/null || true)"
fi

[ -n "${target}" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0        # 邊界 4
[ -f "${REG}" ] && [ -x "${GEN}" ] || exit 0   # 邊界 4

# 絕對路徑轉 repo 相對；repo 外一律不管
case "${target}" in
  "${REPO_ROOT}"/*) rel="${target#"${REPO_ROOT}"/}" ;;
  /*)               exit 0 ;;
  *)                rel="${target}" ;;
esac

# 受管集合：由註冊表導出（邊界 3）。輸出一行一筆；以 `/` 結尾者為目錄前綴。
_managed() {
  printf '%s\n' "scripts/fact_keys.json"
  LC_ALL=C jq -r 'to_entries[] | select(.key != "_schema")
                  | .value.target | if type == "array" then .[] else . end' "${REG}" 2>/dev/null
  LC_ALL=C jq -r '._schema.mechanism_scope[]? // empty' "${REG}" 2>/dev/null
  LC_ALL=C jq -r '._schema.status_scope[]? // empty' "${REG}" 2>/dev/null
}

# fixture 底下的同名宿主也受管（改 fixture 一樣要驗）——前綴由 GOVB1_FACTKEY_ROOT 慣例導出
_FIXTURE_PREFIX='tests/governance/fixtures/govb1/'

_is_managed() {   # $1=rel → rc=0 表示受管
  case "$1" in "${_FIXTURE_PREFIX}"*) return 0 ;; esac
  while IFS= read -r m; do
    [ -n "${m}" ] || continue
    case "${m}" in
      */) case "$1" in "${m}"*) return 0 ;; esac ;;
      *)  [ "$1" = "${m}" ] && return 0 ;;
    esac
  done <<EOF
$(_managed)
EOF
  return 1
}

_is_managed "${rel}" || exit 0

# ── 受管檔被改 ⇒ 跑與 pre-push **同一支**檢查 ────────────────────────────
# 🔴 刻意不另寫精簡版判定：兩份判定邏輯必然漂移，那正是本 epic 反覆吃虧的形態。
#    代價＝本層約 1.6 秒（僅在命中受管檔時），相對於「push 前才發現要重寫 commit」是划算的。
out="$(cd "${REPO_ROOT}" && env -u GOVB1_FACTKEY_ROOT bash "${GEN}" --check 2>&1)"
rc=$?

# fixture 鑑別力守衛：drifted 必須與 clean 有差異，否則正反對照失去意義。
# 🔴 本 session 實測：`--write` 會把 drifted 的竄改列洗回與 clean 相同，已發生 5 次。
_clean="${REPO_ROOT}/tests/governance/fixtures/govb1/factkey_clean/docs/GOVERNANCE_EXECUTION_ORDER.md"
_drift="${REPO_ROOT}/tests/governance/fixtures/govb1/factkey_drifted/docs/GOVERNANCE_EXECUTION_ORDER.md"
fixture_msg=""
if [ -f "${_clean}" ] && [ -f "${_drift}" ] && cmp -s "${_clean}" "${_drift}"; then
  fixture_msg="FIXTURE 鑑別力已失：factkey_drifted 與 factkey_clean 的 GOVERNANCE_EXECUTION_ORDER.md 完全相同
  ⇒ 正反對照測試變成兩個 clean，drifted 那條恆綠（空心）。
  修：把 drifted 的序 140 那列票號改回不存在的值（如 B-99（竄改）），詳見該目錄 README。"
fi

[ "${rc}" = "0" ] && [ -z "${fixture_msg}" ] && exit 0

{
  echo "[factkey_write_guard] 🔴 產出端檢查未過（你剛改了受管檔 ${rel}）"
  [ "${rc}" = "0" ] || {
    printf '%s\n' "${out}" | sed 's/^/  /'
    echo "  修：改完 scripts/fact_keys.json 要跑 bash scripts/gen_fact_key_blocks.sh --write"
    echo "  （若正在編輯中尚未跑 --write，此紅屬預期，跑完即消失）"
  }
  [ -z "${fixture_msg}" ] || printf '  %s\n' "${fixture_msg}"
  echo "  本層只是早期警告；真正的 fail-closed 在 gov_check 第 3 段與派工閘。"
} >&2
exit 2
