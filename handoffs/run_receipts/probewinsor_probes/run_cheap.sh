#!/usr/bin/env bash
# PROBEWINSOR 偵察：便宜格串行（只探測、不生成）。用法：bash run_cheap.sh <case:mode> ...
set -u
D="$(cd "$(dirname "${0}")" && pwd)"
ROOT="$(cd "${D}/../../.." && pwd)"
cd "${ROOT}" || exit 2
source venv/bin/activate
for spec in "$@"; do
  c="${spec%%:*}"; m="${spec##*:}"
  log="${D}/out/${c}.${m}.log"
  mkdir -p "${D}/out"
  python "${D}/probe_depth.py" "${c}" "${m}" "${D}/out/${c}.${m}.json" > "${log}" 2>&1
  rc=$?
  echo "== ${c} ${m} rc=${rc}"
  grep -E '^\{"case"' "${log}" | cut -c1-600
done
