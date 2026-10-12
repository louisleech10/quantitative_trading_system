#!/usr/bin/env bash
# PROBEWINSOR 偵察：完整生成比對（串行）。用法：bash run_gen.sh <scratch_root> <case:mode> ...
# 每格輸出落 <scratch_root>/<case>.<mode>/，跑完即刪（只留 out/gen.<case>.<mode>.json 指紋）。
set -u
D="$(cd "$(dirname "${0}")" && pwd)"
ROOT="$(cd "${D}/../../.." && pwd)"
cd "${ROOT}" || exit 2
source venv/bin/activate
scratch="${1}"; shift
mkdir -p "${D}/out" "${scratch}"
for spec in "$@"; do
  c="${spec%%:*}"; m="${spec##*:}"
  work="${scratch}/${c}.${m}"
  rm -rf "${work}"
  log="${D}/out/gen.${c}.${m}.log"
  /usr/bin/time -l python "${D}/gen_compare.py" "${c}" "${m}" "${D}/out/gen.${c}.${m}.json" "${work}" > "${log}" 2>&1
  rc=$?
  echo "== ${c} ${m} rc=${rc}"
  grep -E '^\{"case"|^warmup_insufficient' "${log}" | cut -c1-500
  grep -E 'maximum resident set size' "${log}"
  du -sh "${work}" 2>/dev/null
  rm -rf "${work}"
done
df -h . | tail -1
