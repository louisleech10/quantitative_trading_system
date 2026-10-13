#!/usr/bin/env bash
# PROBEWINSOR Task 1.3 分段續跑：同 affected_run.sh，但①沿用既有 <label>.progress（首行 head 須等於 repo 目前 HEAD，
# 否則拒跑）②跳過 progress 已記 rc 0／1 且 junit 存在之檔（同一 HEAD 之完成紀錄才算）③超過預算秒數即不再啟動新檔、
# 記 paused 後結束（每段 ≤2 小時）。被中斷之檔（無 rc 行）整檔重跑。
# 用法：bash affected_chunk.sh <label> <repo_dir> <out_dir> <budget_seconds>
set -u
label="${1:?label}"; repo="${2:?repo_dir}"; out="${3:?out_dir}"; budget="${4:?budget_seconds}"
PY=/Users/louis/Desktop/quantitative_trading_system/venv/bin/python
# 清單預設本目錄 affected_list.txt；他票可以 AFFECTED_LIST 指定（每行一檔、手寫不用 glob），AFFECTED_COUNT 為預期檔數
LIST="${AFFECTED_LIST:-$(cd "$(dirname "$0")" && pwd)/affected_list.txt}"
COUNT="${AFFECTED_COUNT:-35}"
files=()
while IFS= read -r f; do [ -n "${f}" ] && files+=("${f}"); done < "${LIST}"
[ "${#files[@]}" -eq "${COUNT}" ] || { echo "清單應 ${COUNT} 檔，實得 ${#files[@]}"; exit 2; }
cd "${repo}" || exit 2
head_now="$(git rev-parse HEAD)"
progress="${out}/${label}.progress"
mkdir -p "${out}/${label}"
if [ -f "${progress}" ]; then
  head_rec="$(head -1 "${progress}" | tr ' ' '\n' | sed -n 's/^head=//p')"
  [ "${head_rec}" = "${head_now}" ] || { echo "progress 之 head ${head_rec} ≠ 目前 HEAD ${head_now}，拒續跑"; exit 2; }
else
  echo "label=${label} head=${head_now} start=$(date +%s)" > "${progress}"
fi
t_start=$(date +%s)
i=0
for f in "${files[@]}"; do
  i=$((i + 1))
  key="$(printf '%s' "${f}" | tr '/' '_')"
  if grep -qE "^[0-9]+/${COUNT} ${f} rc=(0|1) " "${progress}" && [ -f "${out}/${label}/${key}.xml" ]; then
    continue
  fi
  if [ $(( $(date +%s) - t_start )) -ge "${budget}" ]; then
    echo "paused at=${i} t=$(date +%s)" >> "${progress}"
    exit 0
  fi
  kargs=()
  [ "${f}" = "tests/feature_engineering/test_failopen_correctness.py" ] && kargs=(-k "not test_v6_")
  t0=$(date +%s)
  if [ "${#kargs[@]}" -gt 0 ]; then
    "${PY}" -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=short -rA \
      "${kargs[@]}" --junitxml="${out}/${label}/${key}.xml" "${f}" > "${out}/${label}/${key}.log" 2>&1
  else
    "${PY}" -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=short -rA \
      --junitxml="${out}/${label}/${key}.xml" "${f}" > "${out}/${label}/${key}.log" 2>&1
  fi
  rc=$?
  echo "${i}/${COUNT} ${f} rc=${rc} seconds=$(( $(date +%s) - t0 )) $(tail -1 "${out}/${label}/${key}.log" | tr -d '=')" >> "${progress}"
done
echo "done end=$(date +%s)" >> "${progress}"
