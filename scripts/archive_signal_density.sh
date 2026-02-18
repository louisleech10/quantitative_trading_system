#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_FILE="${ROOT_DIR}/momentum/Optimization/objectives/signal_density.py"
ARCHIVE_DIR="${ROOT_DIR}/archived/momentum/Optimization/objectives"
ARCHIVE_FILE="${ARCHIVE_DIR}/signal_density.py"
README_FILE="${ARCHIVE_DIR}/README.md"

mkdir -p "${ARCHIVE_DIR}"

if [[ -f "${SRC_FILE}" ]]; then
  mv "${SRC_FILE}" "${ARCHIVE_FILE}"
  echo "Moved ${SRC_FILE} -> ${ARCHIVE_FILE}"
else
  echo "Source not found (already archived): ${SRC_FILE}"
fi

cat > "${README_FILE}" <<'EOF'
# Archived Objectives

`signal_density.py` has been archived in Phase 4.0.

## Restore Instruction

Run:

```bash
mv archived/momentum/Optimization/objectives/signal_density.py momentum/Optimization/objectives/signal_density.py
```
EOF

echo "Archive status ready at ${ARCHIVE_FILE}"
