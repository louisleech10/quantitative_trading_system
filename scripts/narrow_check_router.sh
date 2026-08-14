#!/usr/bin/env bash
# narrow_check_router.sh — 窄觸發檢查之產出端路由器（PostToolUse:Edit|Write）。
#
# ── 為何存在（使用者 2026-08-14T18:40+08:00 逐字）──────────────────────
#   「全部的票和腳本，該掛哪／為何沒掛／能不能掛，可以掛的就要掛上去，
#     只有掛和不掛兩種結果，不掛就要有原因，耗費時間太多也是原因。
#     沒有什麼可能、推理、想看看——你用推理都全錯。不是表格列出，是實際上線。」
#
#   152 支腳本分流後，有一類是「**有判定、很便宜、但只在少數幾個檔被改時才有意義**」。
#   這類每支各掛一個 hook 條目的話：①`.claude/settings.json` 條目無限增生
#   ②每次 Edit/Write 都多 fork 一個行程去做「這次跟我無關」的判斷。
#   ⇒ 收成單一路由器：**一個 hook 條目、一張對照表**，新增檢查只改表不動掛載。
#
# ── 對照表在哪 ────────────────────────────────────────────────────────
#   `_routes()`。每列 `<repo 相對路徑或目錄前綴>|<檢查命令>`。
#   路徑以 `/` 結尾者視為目錄前綴，其餘為完整路徑相等比對。
#   🔴 **刻意不用萬用字元 glob**：glob 會靜默擴大範圍，
#      而本路由器的成本模型建立在「命中率低」上（見下方成本節）。
#
# ── 成本（實測，2026-08-14）────────────────────────────────────────────
#   未命中：只做字串比對，無 fork，微秒級。
#   命中 check_agent_contract_sync.sh：~1 秒。命中 extract_phase2 --check：~0 秒。
#   🔴 成本是掛不掛的**合法判準**（使用者明示「耗費時間太多也是原因」）。
#      本表刻意排除 `check_doc_anchors.sh`（3.6 秒／次）——改掛 pre-commit，
#      理由寫在 `docs/GOV_ACTIVE_MECHANISMS.md`「§七 腳本級掛載判定」。
#      🔴 GROK-R1-P2-02／COMPOSER-R1-P1-02：本行原引用 `E-023`，**該列不存在**（虛引用）。
#      不進 enforcement 表是刻意取捨：該表對應票欄由 S1.1 封閉集合鎖死。
#
# 🔴 **對照表禁止目錄前綴列**（GROK-R1-P2-03）：碼支援 `/` 結尾之目錄前綴，
#    但加入 `scripts/` 這類列會使每次 Edit 皆命中，上面的成本模型當場失效。
#    由 `tests/governance/test_narrow_check_router.py::test_routes_have_no_directory_prefix` 鎖住。
#
# ── 誠實邊界（不誇大，體例同 factkey_write_guard.sh）───────────────────
#   1. PostToolUse 在寫入**之後**跑 ⇒ **早期警告，不是硬閘**。它把發現時機從 push
#      前移到寫檔當下，**不改變**任何判定的寬嚴。
#   2. **只涵蓋 Edit|Write 工具**。經 Bash 重導、外部編輯器、git 操作寫出的檔不觸發。
#   3. payload 解析失敗／路徑判不出 ⇒ **靜默放行**（rc=0）。hook 不得因自己失敗而擋住工作；
#      這是刻意的 fail-open，代價由 pre-push 之 gov_check 承接。
#   4. 🔴 **但「檢查腳本不存在」不是 fail-open**：那代表表列的檢查被刪或改名，
#      屬**表本身腐爛**，rc=2 大聲報。（S1.2 教訓：`rc=2 略過` 是 fail-open 的溫床。）
#   5. 本路由器不判斷檢查的**語意對不對**，只負責「有改到就跑」。語意屬 review 職責。
#
# 用法：
#   bash scripts/narrow_check_router.sh <file>   # 直接對某檔跑
#   bash scripts/narrow_check_router.sh          # hook 模式：自 stdin JSON 取 file_path
# rc: 0=通過／不適用；2=有檢查未過（訊息在 stderr，hook 回灌 context）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── 對照表（唯一需要維護的地方）──────────────────────────────────────
# 🔴 新增列時務必同步 `docs/GOV_ENFORCEMENT_REGISTRY.md`，否則登記表與實況不符。
_routes() {
  # 四源執行合約：改一處忘了同步其他 ⇒ 執行端讀到不一致合約
  printf '%s\n' "AGENTS.md|bash scripts/check_agent_contract_sync.sh"
  printf '%s\n' ".cursorrules|bash scripts/check_agent_contract_sync.sh"
  printf '%s\n' "CLAUDE.md|bash scripts/check_agent_contract_sync.sh"
  printf '%s\n' "docs/MULTI_AGENT_ORCHESTRATION.md|bash scripts/check_agent_contract_sync.sh"
  # Phase 2 預期轉向 fixture：TODO 改了而 fixture 沒重生成 ⇒ 測試斷言變成對舊語料
  printf '%s\n' "docs/GOVB0_FRICTION_TODO.md|python3 scripts/extract_phase2_expected_flips.py --check"
  printf '%s\n' "tests/governance/fixtures/phase2_expected_flips.txt|python3 scripts/extract_phase2_expected_flips.py --check"
  printf '%s\n' "tests/governance/fixtures/phase2_expected_flips.txt.sha256|python3 scripts/extract_phase2_expected_flips.py --check"
  # 票 B-49 閉合證據之靜態子集（E-007 之重新收案前置）：六格 selector 被掏空／改名
  # ⇒ 關票證據被抽掉。純 AST，不跑測試不碰 git ⇒ 寫檔當下就判得出來
  printf '%s\n' "tests/governance/test_govb49_path_grant.py|python3 scripts/b49_closure_static_check.py"
  printf '%s\n' "scripts/b49_closure_static_check.py|python3 scripts/b49_closure_static_check.py"
}
# 🔴 上線實證（2026-08-14T21:0x+08:00，非推理）：曾臨時加一列
#   `.claude/tmp/ncr_live_probe.txt|bash .claude/tmp/ncr_fail_stub.sh`（樁 rc=1），
#   以 Write 工具寫該檔 ⇒ PostToolUse 當場擋下並把訊息回灌 context。
#   ⇒ 掛載點確實會觸發、rc=2 確實會回灌。臨時列已移除。

target="${1:-}"

# hook 模式：PostToolUse 以 stdin 餵 JSON，取 tool_input.file_path（邊界 3）
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

# 絕對路徑轉 repo 相對；repo 外一律不管（邊界 3）
case "${target}" in
  "${REPO_ROOT}"/*) rel="${target#"${REPO_ROOT}"/}" ;;
  /*)               exit 0 ;;
  *)                rel="${target}" ;;
esac

cd "${REPO_ROOT}" || exit 0

_fail=0
_seen_cmds=""

while IFS='|' read -r pat cmd; do
  [ -n "${pat}" ] || continue
  case "${pat}" in
    */) case "${rel}" in "${pat}"*) : ;; *) continue ;; esac ;;
    *)  [ "${rel}" = "${pat}" ] || continue ;;
  esac

  # 同一個檢查被多列命中時只跑一次（避免對照表擴張後重複 fork）
  case "${_seen_cmds}" in
    *"<${cmd}>"*) continue ;;
  esac
  _seen_cmds="${_seen_cmds}<${cmd}>"

  # 邊界 4：表列的腳本不存在 ⇒ 表腐爛，大聲報，不得靜默略過
  # shellcheck disable=SC2086
  set -- ${cmd}
  _script="${2:-}"
  if [ -z "${_script}" ] || [ ! -f "${_script}" ]; then
    echo "[narrow_check_router] 🔴 對照表腐爛：命中 ${rel} 之檢查腳本不存在或表列格式錯誤：${cmd}" >&2
    echo "  修：更新 scripts/narrow_check_router.sh 之 _routes()，並同步 docs/GOV_ENFORCEMENT_REGISTRY.md" >&2
    _fail=1
    continue
  fi

  # 🔴 GROK-R1-P1-03（實構命中）：原版寫 `mktemp … || continue`，
  #   TMPDIR 不可寫時**跳過該檢查且 _fail 仍為 0** ⇒ 整支路由器 rc=0 假綠。
  #   「暫存檔開不了」屬環境異常，必須大聲報，不得當成「這條檢查通過」。
  _out="$(mktemp "${TMPDIR:-/tmp}/ncr.XXXXXXXX" 2>/dev/null)"
  if [ -z "${_out}" ] || [ ! -f "${_out}" ]; then
    echo "[narrow_check_router] 🔴 無法建立暫存檔（TMPDIR=${TMPDIR:-/tmp} 不可寫？）⇒ 檢查 ${cmd} 未執行" >&2
    echo "  這不是通過：環境異常時本路由器 fail-closed，不得靜默略過檢查。" >&2
    _fail=1
    continue
  fi
  # 🔴 rc 直接取，中間不得經 pipe（CLAUDE.md 明載；本 epic 已犯三次）
  eval "${cmd}" > "${_out}" 2>&1
  _rc=$?
  if [ "${_rc}" -ne 0 ]; then
    echo "[narrow_check_router] 🔴 你剛改了 ${rel}，其對應檢查未過（rc=${_rc}）：" >&2
    echo "  命令：${cmd}" >&2
    sed -n '1,25p' "${_out}" >&2
    _fail=1
  fi
  rm -f "${_out}"
done <<EOF
$(_routes)
EOF

[ "${_fail}" -eq 0 ] || exit 2
exit 0
