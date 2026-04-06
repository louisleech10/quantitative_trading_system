#!/usr/bin/env bash
# ============================================================
# Decoupling Compliance Scanner
# Checks all 7 architecture rules and reports violations.
# Usage: bash scripts/check_decoupling.sh
# Exit code 0 = all pass, 1 = violations found
# ============================================================
set -euo pipefail

cd "$(dirname "$0")/.."
FAIL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo "========================================"
echo " Decoupling Compliance Scanner"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# ── Rule 1: momentum/ must NOT import api/ ──────────────────
R1=$(grep -rn --include='*.py' -E '^from api\.|^import api\.' momentum/ 2>/dev/null | grep -v '__pycache__' || true)
R1_COUNT=$([ -z "$R1" ] && echo 0 || echo "$R1" | wc -l | tr -d ' ')
if [ "$R1_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 1 FAIL${NC}: momentum/ imports api/ ($R1_COUNT violations)"
  echo "$R1"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 1 PASS${NC}: momentum/ does not import api/"
fi
echo ""

# ── Rule 2: momentum/ cross-domain concrete imports ─────────
R2=$(grep -rn --include='*.py' '^from momentum\.' momentum/ \
  | grep -v '__pycache__' \
  | grep -v 'from momentum\.core\.' \
  | grep -v 'from momentum\.factories' \
  | grep -v '/tests/' \
  | grep -v 'momentum/core/contracts\.py' \
  | python3 -c "
import sys, re
for line in sys.stdin:
    line = line.strip()
    m = re.match(r'momentum/([^/]+)/.+:\d+:from momentum\.([^. ]+)', line)
    if m and m.group(1) != m.group(2):
        print(line)
" 2>/dev/null || true)
R2_COUNT=$([ -z "$R2" ] && echo 0 || echo "$R2" | wc -l | tr -d ' ')
if [ "$R2_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 2 FAIL${NC}: momentum/ cross-domain concrete imports ($R2_COUNT violations)"
  echo "$R2"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 2 PASS${NC}: no cross-domain concrete imports in momentum/"
fi
echo ""

# ── Rule 3: api/ must not directly import momentum concrete ─
# Top-level imports in services
R3_SVC=$(grep -rn --include='*.py' '^from momentum\.' api/services/ \
  | grep -v '__pycache__' \
  | grep -v 'from momentum\.factories' \
  | grep -v 'from momentum\.core\.' || true)
# Lazy/deferred imports in services
R3_SVC_LAZY=$(grep -rn --include='*.py' '    from momentum\.' api/services/ \
  | grep -v '__pycache__' \
  | grep -v 'from momentum\.factories' \
  | grep -v 'from momentum\.core\.' || true)
# Routes
R3_ROUTES=$(grep -rn --include='*.py' '^from momentum\.' api/routes/ \
  | grep -v '__pycache__' \
  | grep -v 'from momentum\.factories' \
  | grep -v 'from momentum\.core\.' || true)
# Websocket
R3_WS=$(grep -rn --include='*.py' '^from momentum\.' api/websocket/ \
  | grep -v '__pycache__' \
  | grep -v 'from momentum\.factories' \
  | grep -v 'from momentum\.core\.' || true)

R3_ALL=$(printf '%s\n%s\n%s\n%s' "$R3_SVC" "$R3_SVC_LAZY" "$R3_ROUTES" "$R3_WS" | grep -v '^$' || true)
R3_COUNT=$([ -z "$R3_ALL" ] && echo 0 || echo "$R3_ALL" | wc -l | tr -d ' ')
if [ "$R3_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 3 FAIL${NC}: api/ directly imports momentum concrete ($R3_COUNT violations)"
  echo "$R3_ALL"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 3 PASS${NC}: api/ only imports via factories/core"
fi
echo ""

# ── Rule 4: api/services/ must not import each other or routes ─
# Zero tolerance: catch both top-level and lazy (indented) imports
# Filter out comments: lines where the import is inside a # comment
R4_SVC=$(grep -rn --include='*.py' 'from api\.services\.' api/services/ \
  | grep -v '__pycache__' \
  | grep -v '#.*from api\.services\.' || true)
R4_ROUTES=$(grep -rn --include='*.py' 'from api\.routes\.' api/services/ \
  | grep -v '__pycache__' \
  | grep -v '#.*from api\.routes\.' || true)
R4_ALL=$(printf '%s\n%s' "$R4_SVC" "$R4_ROUTES" | grep -v '^$' || true)
R4_COUNT=$([ -z "$R4_ALL" ] && echo 0 || echo "$R4_ALL" | wc -l | tr -d ' ')
if [ "$R4_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 4 FAIL${NC}: service cross-imports ($R4_COUNT violations)"
  echo "$R4_ALL"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 4 PASS${NC}: no service-to-service imports"
fi
echo ""

# ── Rule 5 (strict): momentum must not import api.core.config ─
R5=$(grep -rn --include='*.py' 'from api\.core\.config' momentum/ 2>/dev/null \
  | grep -v '__pycache__' || true)
R5_COUNT=$([ -z "$R5" ] && echo 0 || echo "$R5" | wc -l | tr -d ' ')
if [ "$R5_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 5 FAIL${NC}: momentum imports api.core.config ($R5_COUNT violations)"
  echo "$R5"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 5 PASS${NC}: momentum does not import api.core.config"
fi
echo ""

# ── Rule 6: no lambda monkeypatch across boundaries ─────────
R6=$(grep -rn --include='*.py' -E '\._[A-Za-z_][A-Za-z0-9_]*\s*=\s*lambda|\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*lambda' api/services/ \
  | grep -v '__pycache__' \
  | grep -v 'test' || true)
R6_COUNT=$([ -z "$R6" ] && echo 0 || echo "$R6" | wc -l | tr -d ' ')
if [ "$R6_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 6 FAIL${NC}: lambda monkeypatch in services ($R6_COUNT violations)"
  echo "$R6"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 6 PASS${NC}: no lambda monkeypatch found"
fi
echo ""

# ── Rule 7: api/models ↔ momentum/core no bidirectional ─────
R7_A=$(grep -rn --include='*.py' '^from momentum\.core\.' api/models/ 2>/dev/null \
  | grep -v '__pycache__' || true)
R7_B=$(grep -rn --include='*.py' '^from api\.models\.' momentum/core/ 2>/dev/null \
  | grep -v '__pycache__' || true)
R7_ALL=$(printf '%s\n%s' "$R7_A" "$R7_B" | grep -v '^$' || true)
R7_COUNT=$([ -z "$R7_ALL" ] && echo 0 || echo "$R7_ALL" | wc -l | tr -d ' ')
if [ "$R7_COUNT" -gt 0 ]; then
  echo -e "${RED}❌ Rule 7 FAIL${NC}: bidirectional api/models ↔ momentum/core ($R7_COUNT violations)"
  echo "$R7_ALL"
  FAIL=1
else
  echo -e "${GREEN}✅ Rule 7 PASS${NC}: no bidirectional dependency"
fi
echo ""

# ── Summary ──────────────────────────────────────────────────
echo "========================================"
if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}ALL RULES PASS — Ready to freeze${NC}"
else
  echo -e "${RED}VIOLATIONS FOUND — Fix before merging${NC}"
fi
echo "========================================"

exit $FAIL
