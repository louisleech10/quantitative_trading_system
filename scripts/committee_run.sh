#!/usr/bin/env bash
# committee_run.sh — 一次完成「開 gate token → 開債 → 平行派 N 家委員 → 等全部完成 → 逐家回報」。
#
# 為何存在(2026-07-25):每輪派工原需 gate.sh + cx_run×N + 逐檔讀 = 4~6 個動作;
#   本 session 跑了 ~10 輪。收斂成單一命令,且**家族數完全動態**(2/3/4…N 家皆可)。
#
# 家族**不寫死**:逐個對 SoT `scripts/governance_families.json` 驗證 →
#   未來在 SoT 加一家,本腳本一字不用改。
#   (誠實邊界:新家族仍須在 cx_run.sh 補該 CLI 的呼叫配方——各 CLI 參數不同,無法通用化。)
#
# P1-6 Task 1.2：gate 成功後、cx_run 前寫 committee_round_open（audit_append
#   --require-absent-session）；round_id 由本腳本 mint，主委不得指定。
#
# 用法:
#   bash scripts/committee_run.sh --session <name> <brief> <out前綴> <fam1,fam2,...> -- <gate.sh dispatch 的 flags...>
#   （--session 必須在 -- 之前；-- 之後整段透傳 gate.sh，須含 --task-id）
# 例:
#   bash scripts/committee_run.sh --session 20260729-p16-b3 \
#     handoffs/X-BRIEF.md handoffs/20260725-xreview codex,composer,grok -- \
#     --intent "..." --risk low --facts-asked "..." --review-role "..." \
#     --template "n/a: 用 brief" --task-id "P16-B3-R1"
#
# 產出:<out前綴>-<family>.md(檔名帶家族後綴 → reconcile_build.sh 可直接吃)
#      <out前綴>-<family>.runlog(該家執行 log;失敗時自動印 tail)
# Claude 用法:以 Bash run_in_background:true 執行本腳本(勿自行加 `&`);全部跑完會一次通知。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

usage() {
  echo "用法: bash scripts/committee_run.sh --session <name> <brief> <out前綴> <fam1,fam2,...> -- <gate dispatch flags...>" >&2
  echo "  --session  必填；之後 reconcile_build.sh <name> 使用的 session 名（寫入 committee_round_open）" >&2
  echo "  -- 之後須含 gate 的 --task-id（本腳本不另發明同名旗標）" >&2
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

# ── 參數：--session 可在 -- 之前任意位置；三個位置參數 + gate flags ──
session=""
brief=""
out_prefix=""
fams_csv=""
gate_args=()
pos_count=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session)
      [ "$#" -ge 2 ] || { echo "ERROR: --session 需要參數" >&2; usage; exit 2; }
      session="${2}"
      shift 2
      ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do
        gate_args+=("$1")
        shift
      done
      break
      ;;
    -*)
      echo "ERROR: 未知旗標: $1（--session 須在 -- 之前；gate flags 須在 -- 之後）" >&2
      usage
      exit 2
      ;;
    *)
      pos_count=$((pos_count + 1))
      case "${pos_count}" in
        1) brief="$1" ;;
        2) out_prefix="$1" ;;
        3) fams_csv="$1" ;;
        *)
          echo "ERROR: 多餘位置參數: $1" >&2
          usage
          exit 2
          ;;
      esac
      shift
      ;;
  esac
done

[ -n "${session}" ] || { echo "ERROR: 缺必填 --session <name>" >&2; usage; exit 2; }
[ -n "${brief}" ] && [ -n "${out_prefix}" ] && [ -n "${fams_csv}" ] || { usage; exit 2; }
[ "${#gate_args[@]}" -ge 1 ] || { echo "ERROR: 缺 gate.sh dispatch flags(-- 之後)" >&2; usage; exit 2; }

[ -f "${brief}" ] || { echo "ERROR: brief 不存在: ${brief}" >&2; exit 2; }
case "${out_prefix}" in handoffs/*) : ;; *) echo "ERROR: out前綴須在 handoffs/: ${out_prefix}" >&2; exit 2 ;; esac

# ---------------------------------------------------------------------------
# GOV-STAMP-TASKID-INJECT / D-001 §D3：brief-kind 與 stamp-target 驗證
# 必須在 gate.sh dispatch 之前 → 失敗時 audit 真正零新增。
# 缺 brief-kind:／未知 brief-kind 一律 exit 2（與 cx_run.sh:53-79 對齊，防 γ 陷阱）。
# stamp 另驗 stamp-target；其餘 kind 不強制 stamp-target。
# ---------------------------------------------------------------------------
# ⚠️ **本處不得自行 parse brief**（CODEX-R1-P1-01，2026-08-02 實證）：
#   舊版在此有第二份 parser（`_cr_bk_all`／`_cr_st_all`），與 cx_run 那份**各驗一半**——
#   本處只驗「brief-kind 存不存在／值合不合法」，而「範本引用 + fact-verified/assumed 前提宣告」
#   只有 cx_run 那份驗。但 cx_run 在**開債之後**才跑 ⇒ 不完整的 brief 會先留下 OPEN debt 再被拒派。
#   **這不是理論**：本 repo audit sequence 367 就是這樣來的
#   （「閉合輪首次派工：brief 合規閘拒派（brief-kind=closure 須引用委員範本，主委漏寫）」→ 只能 abandon）。
# 修法＝在此呼叫**同一個** checker 做**完整**檢查，且仍在 gate.sh dispatch 之前 → 失敗時 audit 真正零新增。
# 本處只需「通過/不通過」，不需解析值（舊 parser 的 _cr_bk/_cr_st 後續從未被使用），
# 故不傳 --emit：少一個暫存檔、少一個 EXIT trap（trap 是覆寫非疊加，多一個就是坑）。
bash "${SCRIPT_DIR}/brief_conformance_check.sh" "${brief}" || exit $?

# task_id 從透傳 gate argv 解析 --task-id（不另發明同名旗標）
task_id=""
_prev=""
for _a in "${gate_args[@]}"; do
  if [ "${_prev}" = "--task-id" ]; then
    task_id="${_a}"
    break
  fi
  _prev="${_a}"
done
[ -n "${task_id}" ] || { echo "ERROR: gate flags 缺 --task-id（開債必填；請在 -- 之後加上 --task-id <id>）" >&2; exit 2; }

# ---------------------------------------------------------------------------
# GOVFLOW Task 3.1 / R8 移交：task_id 白名單須在 gate.sh dispatch **之前**
# （與 cx_run 第⑦道同一 regex；SSOT＝scripts/_role_gate.sh）。
# 非法非空 task_id 若過 gate 再開債 → 留下無 family result 的 OPEN 債 → 全域阻塞。
# 不通過 ⇒ exit 2，不發 token、不開債、不派工，audit 真正零新增。
# ---------------------------------------------------------------------------
bash "${SCRIPT_DIR}/_role_gate.sh" check-task-id "${task_id}" || exit 2

# ---------------------------------------------------------------------------
# 命名規約（2026-08-06 使用者：「任務名長很像，到時候每個人都混亂」）
# 同樣須在 gate.sh dispatch **之前** ⇒ 不合規時 audit 零新增。
# 規約與理由見 scripts/session_name_check.sh 檔頭；**只適用新輪次，舊 session 不溯及既往**。
# ---------------------------------------------------------------------------
# 🔴 「腳本不存在則跳過」的理由（2026-08-06，勿當成鬆綁）：
#   governance 測試以**精選腳本清單**建隔離 repo（見 tests/governance/test_debt_emit.py 的 _harness），
#   且刻意使用合成 session 名（`sess-b3`／`mut-comp`／`idem`…）。
#   把規約強加於測試需改 11 個測試檔的合成名稱——**溯及既往且零收益**
#   （那些名字永遠不會進真實 audit），違反使用者 2026-08-06「既有釘死不動」。
#   ⇒ 真 repo 一定有此檔故一定強制；隔離 repo 沒有故自然跳過。
#   **刪檔即失效的風險由 `tests/governance/test_session_name_guard_wired.py` 擋**
#   （斷言：檔案存在、可執行、且 committee_run.sh 確實呼叫它）。
if [ -f "${SCRIPT_DIR}/session_name_check.sh" ]; then
  bash "${SCRIPT_DIR}/session_name_check.sh" --session "${session}" --task-id "${task_id}" || {
    echo "ERROR: 命名規約未過 → 不發 token、不開債、不派工(fail-closed)" >&2
    exit 2
  }
fi

# --- 家族驗證(對 SoT,非硬編) ---
# shellcheck source=/dev/null
. "${SCRIPT_DIR}/governance_families.sh" || { echo "ERROR: 無法載入 family SoT(fail-closed)" >&2; exit 1; }
valid_fams="$(families_get families ' ')" || { echo "ERROR: 讀 SoT families 失敗(fail-closed)" >&2; exit 1; }
advisory="$(families_get advisory_only ' ' 2>/dev/null || echo "")"

fams="$(printf '%s' "${fams_csv}" | tr ',' ' ')"
n_fams=0
for f in ${fams}; do
  case " ${valid_fams} " in
    *" ${f} "*) : ;;
    *) echo "ERROR: 未知家族 '${f}'(SoT 合法值: ${valid_fams})。新增家族請改 scripts/governance_families.json + cx_run.sh 配方" >&2; exit 2 ;;
  esac
  case " ${advisory} " in
    *" ${f} "*) echo "[committee_run] ⚠️ ${f} 為 advisory_only:諮詢性質,**不計入 quorum**" ;;
  esac
  n_fams=$((n_fams + 1))
done
[ "${n_fams}" -ge 1 ] || { echo "ERROR: 家族清單為空" >&2; exit 2; }

# ---------------------------------------------------------------------------
# GOVFLOW Task 3.1 / A-3：角色 preflight 前移到 gate.sh dispatch **之前**
# 呼叫共用 _role_gate.sh（與 cx_run 同一份）；任一家族不相容 ⇒ 整批拒、audit 零新增。
# ---------------------------------------------------------------------------
echo "[committee_run] === role gate preflight (before gate.sh dispatch) ==="
bash "${SCRIPT_DIR}/_role_gate.sh" check-families "${brief}" "${fams_csv}" || {
  echo "ERROR: 角色閘拒派 → 不發 token、不開債、不派工(fail-closed；audit 零新增)" >&2
  exit 2
}

echo "[committee_run] session=${session} brief=${brief}  families=${fams_csv}(${n_fams} 家)  out=${out_prefix}-<family>.md"

# --- helpers（Task 1.2）---
_mint_round_id() {
  python3 -c 'import uuid; print(uuid.uuid4())'
}

# raw sha256 of brief file bytes
_brief_sha256() {
  local path="$1"
  shasum -a 256 "${path}" | awk '{print $1}'
}

# registry brief_sha256_norm_algo：unify_newline 後逐行 rstrip 行尾空白，LF 連接再 sha256
_brief_sha256_norm() {
  python3 - "$1" <<'PY'
import hashlib
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_bytes()
text = raw.decode("utf-8", errors="surrogateescape")
text = text.replace("\r\n", "\n").replace("\r", "\n")
lines = [ln.rstrip(" \t") for ln in text.split("\n")]
norm = "\n".join(lines)
print(hashlib.sha256(norm.encode("utf-8", errors="surrogateescape")).hexdigest())
PY
}

# 組 participants / quorum_eligible / expected_outputs JSON（欄位名對齊 registry）
_build_open_json_fields() {
  # stdout: 三行 = participants_json / quorum_json / outputs_json
  # advisory 名單經 env COMMITTEE_ADVISORY（空白分隔）傳入
  python3 - "$out_prefix" $fams <<'PY'
import json
import os
import sys

prefix = sys.argv[1]
fams = sys.argv[2:]
advisory = {x for x in os.environ.get("COMMITTEE_ADVISORY", "").split() if x}
participants = list(fams)
quorum = [f for f in participants if f not in advisory]
outputs = {f: f"{prefix}-{f}.md" for f in participants}
print(json.dumps(participants, ensure_ascii=False))
print(json.dumps(quorum, ensure_ascii=False))
print(json.dumps(outputs, ensure_ascii=False))
PY
}

_open_debt() {
  # 唯一容許形態：audit_append --require-absent-session（鎖內判定+寫入）
  # 本函式不得自行掃 audit 再 append，也不得自行取鎖。
  local round_id="$1"
  local brief_sha brief_sha_n
  local participants_json quorum_json outputs_json
  local tmp

  brief_sha="$(_brief_sha256 "${brief}")" || return 1
  brief_sha_n="$(_brief_sha256_norm "${brief}")" || return 1

  COMMITTEE_ADVISORY="${advisory}" \
  tmp="$(_build_open_json_fields)" || return 1
  participants_json="$(printf '%s\n' "${tmp}" | sed -n '1p')"
  quorum_json="$(printf '%s\n' "${tmp}" | sed -n '2p')"
  outputs_json="$(printf '%s\n' "${tmp}" | sed -n '3p')"

  # 不得在開債時建立 session 目錄
  bash "${SCRIPT_DIR}/audit_append.sh" \
    --require-absent-session "${session}" \
    --event committee_round_open \
    --field "round_id=${round_id}" \
    --field "task_id=${task_id}" \
    --field "brief_path=${brief}" \
    --field "brief_sha256=${brief_sha}" \
    --field "brief_sha256_norm=${brief_sha_n}" \
    --field "lock_mode=discovery" \
    --field "participants=@${participants_json}" \
    --field "quorum_eligible=@${quorum_json}" \
    --field "expected_outputs=@${outputs_json}" \
    --field "session_name=${session}" \
    --field "actor=committee_run" \
    --field "origin_script=committee_run.sh"
}

# --- 1) 開 gate token(fail-closed:沒過就不派、不開債) ---
# Task 1.3 (e)：EXPECTED-DELTA 閘輸入 — 強制把 session brief 傳入 gate
# （無此接線則 --brief 掛點空轉；票 B-29 / GROK-R13-P1-03）
gate_args+=(--brief "${brief}")
echo "[committee_run] === gate.sh dispatch ==="
bash "${SCRIPT_DIR}/gate.sh" dispatch "${gate_args[@]}" || {
  echo "ERROR: gate 未放行 → 不開債、不派工(fail-closed)" >&2; exit 1; }

# --- 1b) 開債（gate 成功之後、cx_run 之前；失敗不得啟動任何 cx_run）---
round_id="$(_mint_round_id)" || die "mint round_id 失敗"
echo "[committee_run] === open debt round_id=${round_id} session=${session} ==="
if ! _open_debt "${round_id}"; then
  echo "ERROR: 開債失敗（session 重複或 audit 寫入失敗）→ 不啟動 cx_run" >&2
  exit 1
fi
echo "[committee_run] 開債完成 round_id=${round_id}"

# --- 2) 平行派 N 家(索引陣列配對 pid↔family;bash 3.2 相容) ---
# ROUND_ID 以 env 傳給每家 cx_run（Task 1.2 改法⑤）
PIDS=()
FAMS=()
for f in ${fams}; do
  out="${out_prefix}-${f}.md"
  log="${out_prefix}-${f}.runlog"
  echo "[committee_run] → 派 ${f}(out=${out})"
  ROUND_ID="${round_id}" bash "${SCRIPT_DIR}/cx_run.sh" "${f}" "${brief}" "${out}" >"${log}" 2>&1 &
  PIDS+=("$!")
  FAMS+=("${f}")
done

# --- 3) 等全部完成 + 逐家回報 ---
rc_all=0
idx=0
while [ "${idx}" -lt "${#PIDS[@]}" ]; do
  pid="${PIDS[${idx}]}"
  fam="${FAMS[${idx}]}"
  idx=$((idx + 1))
  if wait "${pid}"; then
    out="${out_prefix}-${fam}.md"
    if [ -s "${out}" ]; then
      echo "[committee_run] ✅ ${fam} 完成 → ${out}"
    else
      echo "[committee_run] ⚠️ ${fam} rc=0 但產出缺/空: ${out}(檢查 ${out_prefix}-${fam}.runlog)" >&2
      rc_all=1
    fi
  else
    echo "[committee_run] ❌ ${fam} 失敗(見下 log tail)" >&2
    tail -15 "${out_prefix}-${fam}.runlog" 2>/dev/null | sed 's/^/    /' >&2
    rc_all=1
  fi
done

if [ "${rc_all}" -eq 0 ]; then
  echo "[committee_run] ✅ ${n_fams} 家全數完成。接著:bash scripts/reconcile_build.sh <session> ${out_prefix}-*.md"
  echo "[committee_run] round_id=${round_id} session=${session}"
else
  echo "[committee_run] ⚠️ 有家族未正常完成 — 勿當作已收齊(見上) round_id=${round_id}" >&2
fi
exit "${rc_all}"
