#!/usr/bin/env bash
# reconcile_stamps_check.sh — 機器強制:reconcile 必須被委員核可才可派實作。
#
# 根因:Claude 產 reconcile,實作者直接信;中間無「委員確認 reconcile 忠實、未被誤寫」的關卡。
# 解法:每個被 reconcile 的委員(家族)須在 reconcile 檔留戳記;全數 APPROVED + 內容雜湊相符才算核可。
#       gate.sh 對「對 SPEC 派實作」要求 --adversarial 指向的 reconcile 已核可,否則拒發 token。
#       實作端合約亦規定:看到 reconcile 未全數 APPROVED → STATUS: BLOCKED 不執行(defense-in-depth)。
#
# 戳記格式(委員審完後各自 append 一行;v2 須帶內容雜湊 + task-id):
#   RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>
#   RECONCILE-STAMP: <family> REJECTED <YYYY-MM-DD> — <理由>
#   <family> ∈ {codex, composer}
#   <body-hash> = sha256 of 「## 戳記」之前的全部內容(即 reconcile 本體,不含戳記區)。
#
# 為何要 sha256(2026-06-27 使用者抓出):光帶日期擋不住偽造——同一天可重用、且 Claude 有寫入權可自寫假戳記。
#   綁定內容雜湊 → ① 同一天不同版內容不同雜湊,戳記不可跨版重用;② 戳完再改本體 → 雜湊對不上 → 失效(tamper-evident)。
# 誠實邊界:此為 tamper-evident,非「密碼學上不可偽」。Claude 若決意偽造仍可自算雜湊自寫戳記。
#   真正的反偽造後盾 = **獨立佐證(Claude 不經手)**:委員 agent 自己的輸出檔(codex -o / cursor 輸出)+
#   harness task log(tasks/<id>.output)+ .claude/gate/audit.log 的 task-id。使用者可稽核「該 task-id 的委員是否真跑、真 APPROVED」。
#   故戳記須帶 task:<id>,讓使用者一鍵對照 harness 紀錄。
#
# 用法:bash scripts/reconcile_stamps_check.sh <reconcile_file> [family1,family2,...]
# 退出:0=全數 APPROVED 且雜湊相符;1=缺戳記/REJECTED/雜湊不符/檔不存在。

set -u
file="${1:-}"
required="${2:-codex,composer}"
[ -n "${file}" ] || { echo "用法: reconcile_stamps_check.sh <reconcile_file> [families]"; exit 1; }
[ -f "${file}" ] || { echo "RECONCILE-STAMP FAIL: 檔不存在: ${file}"; exit 1; }

# 本體雜湊用共用 canonical 腳本(委員 stamp 時與此處同法,避免換行慣例不一致致假失敗)。
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${REPO_ROOT}/venv/bin/python"
[ -x "${VENV_PY}" ] || VENV_PY="python"
if ! grep -qE '^##[[:space:]]*戳記' "${file}"; then
  echo "RECONCILE-STAMP FAIL: ${file} 缺『## 戳記』區段標題(無法界定本體雜湊範圍)"; exit 1
fi
body_hash="$(bash "${SCRIPT_DIR}/reconcile_body_hash.sh" "${file}")"

fail=""
IFS=',' read -ra fams <<< "${required}"
for fam in "${fams[@]}"; do
  fam_trim="$(echo "${fam}" | tr -d '[:space:]')"
  [ -z "${fam_trim}" ] && continue
  # 真戳記:行首 ^RECONCILE-STAMP:(排除 checklist '- [ ]'、-RESOLVED);REJECTED 立即擋。
  if grep -qiE "^RECONCILE-STAMP:[[:space:]]*${fam_trim}[[:space:]]+REJECTED" "${file}"; then
    fail="${fail}  · ${fam_trim}: REJECTED(reconcile 未獲核可,須修後重審)\n"
    continue
  fi
  # APPROVED 行須帶日期 + 正確 body sha256。
  stamp_line="$(grep -iE "^RECONCILE-STAMP:[[:space:]]*${fam_trim}[[:space:]]+APPROVED[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}" "${file}" | tail -1)"
  if [ -z "${stamp_line}" ]; then
    fail="${fail}  · ${fam_trim}: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: ${fam_trim} APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')\n"
  elif ! printf '%s' "${stamp_line}" | grep -qE "sha256:${body_hash}"; then
    claimed="$(printf '%s' "${stamp_line}" | grep -oE 'sha256:[0-9a-f]+' | head -1)"
    fail="${fail}  · ${fam_trim}: 雜湊不符(本體已變動或戳記跨版重用)。戳記=${claimed:-無} 實際 body=sha256:${body_hash}\n"
  else
    # W2:戳記 task:<id> 須有 committee_dispatch 審計 + 輸出 hash(2026-07-01 前 grandfather)
    prov_msg="$("${VENV_PY}" "${SCRIPT_DIR}/verify_task_provenance.py" check-stamp "${stamp_line}" --file "${file}" 2>&1)"
    prov_rc=$?
    if [ "${prov_rc}" -ne 0 ]; then
      fail="${fail}  · ${fam_trim}: provenance 不符 — ${prov_msg}\n"
    fi
  fi
done

if [ -n "${fail}" ]; then
  echo "RECONCILE-STAMP FAIL: ${file} 未獲全數委員核可:"
  printf "%b" "${fail}"
  echo "  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:${body_hash} task:<harness-task-id>'。"
  echo "  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。"
  exit 1
fi
echo "RECONCILE-STAMP PASS: ${file} 已獲 ${required} 全數 APPROVED 且本體雜湊相符(sha256:${body_hash})。"
echo "  使用者反偽造稽核:核對各戳記 task:<id> 對應的 harness 輸出確為該委員真跑真 APPROVED。"
