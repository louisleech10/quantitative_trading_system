#!/usr/bin/env bash
# PROBEWINSOR Task 1.3：受影響既有測試於一個碼態跑一次（逐檔各一個 pytest 行程、單組串行、junit 收結果）。
# 用法：bash affected_run.sh <label> <repo_dir> <out_dir>
#   清單＝本目錄 affected_list.txt（manifest risk_mitigation 之 affected_tests phase=1，35 檔；手寫、不用 glob）；
#   `-k "not test_v6_"` 只施於 test_failopen_correctness.py（SPEC §N R1）；逐檔寫 <out>/<label>/<檔>.xml／.log，
#   進度寫 <out>/<label>.progress；任一檔 pytest rc 非 0／1（中斷、內部錯誤、用法、無測試）⇒ 記為未完成並繼續。
set -u
label="${1:?label}"; repo="${2:?repo_dir}"; out="${3:?out_dir}"
PY=/Users/louis/Desktop/quantitative_trading_system/venv/bin/python
LIST=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/probewinsor_probes/affected_list.txt
files=()
while IFS= read -r f; do [ -n "${f}" ] && files+=("${f}"); done < "${LIST}"
[ "${#files[@]}" -eq 35 ] || { echo "清單應 35 檔，實得 ${#files[@]}"; exit 2; }
cd "${repo}" || exit 2
for f in "${files[@]}"; do [ -f "${f}" ] || { echo "缺檔 ${f}"; exit 2; }; done
mkdir -p "${out}/${label}"
progress="${out}/${label}.progress"
: > "${progress}"
echo "label=${label} head=$(git rev-parse HEAD) start=$(date +%s)" >> "${progress}"
i=0
for f in "${files[@]}"; do
  i=$((i + 1))
  key="$(printf '%s' "${f}" | tr '/' '__')"
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
  echo "${i}/35 ${f} rc=${rc} seconds=$(( $(date +%s) - t0 )) $(tail -1 "${out}/${label}/${key}.log" | tr -d '=')" >> "${progress}"
done
echo "done end=$(date +%s)" >> "${progress}"
