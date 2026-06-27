#!/usr/bin/env bash
# reconcile_stamps_check.sh — 機器強制:reconcile 必須被委員核可才可派實作。
#
# 根因:Claude 產 reconcile,實作者直接信;中間無「委員確認 reconcile 忠實、未被誤寫」的關卡。
# 解法:每個被 reconcile 的委員(家族)須在 reconcile 檔留戳記;全數 APPROVED 才算核可。
#       gate.sh 對「對 SPEC 派實作」要求 --adversarial 指向的 reconcile 已核可,否則拒發 token。
#       實作端合約亦規定:看到 reconcile 未全數 APPROVED → STATUS: BLOCKED 不執行(defense-in-depth)。
#
# 戳記格式(委員審完 reconcile 後各自 append 一行):
#   RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD>
#   RECONCILE-STAMP: <family> REJECTED — <理由>
#   <family> ∈ {codex, composer}(雙家族;單家族任務見 REQUIRED_FAMILIES 覆寫)
#
# 用法:bash scripts/reconcile_stamps_check.sh <reconcile_file> [family1,family2,...]
# 退出:0=全數 APPROVED;1=缺戳記/有 REJECTED/檔不存在。
# 誠實邊界:只驗「戳記存在且 APPROVED」,不驗委員是否真讀(那靠委員獨立性);防的是「Claude 自產 reconcile 無人複核就派工」。

set -u
file="${1:-}"
required="${2:-codex,composer}"
[ -n "${file}" ] || { echo "用法: reconcile_stamps_check.sh <reconcile_file> [families]"; exit 1; }
[ -f "${file}" ] || { echo "RECONCILE-STAMP FAIL: 檔不存在: ${file}"; exit 1; }

fail=""
IFS=',' read -ra fams <<< "${required}"
for fam in "${fams[@]}"; do
  fam_trim="$(echo "${fam}" | tr -d '[:space:]')"
  [ -z "${fam_trim}" ] && continue
  if grep -qiE "RECONCILE-STAMP:[[:space:]]*${fam_trim}[[:space:]]+REJECTED" "${file}"; then
    fail="${fail}  · ${fam_trim}: REJECTED(reconcile 未獲核可,須修後重審)\n"
  elif ! grep -qiE "RECONCILE-STAMP:[[:space:]]*${fam_trim}[[:space:]]+APPROVED" "${file}"; then
    fail="${fail}  · ${fam_trim}: 缺 APPROVED 戳記\n"
  fi
done

if [ -n "${fail}" ]; then
  echo "RECONCILE-STAMP FAIL: ${file} 未獲全數委員核可:"
  printf "%b" "${fail}"
  echo "  → 須委員(${required})各審 reconcile 並 append 'RECONCILE-STAMP: <family> APPROVED <date>' 才可派實作。"
  exit 1
fi
echo "RECONCILE-STAMP PASS: ${file} 已獲 ${required} 全數 APPROVED。"
