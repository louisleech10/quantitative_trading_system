#!/bin/bash

# Architecture Compliance Checker
# 檢查系統是否遵循 REFACTOR_ARCHITECTURE_V4 的 7 條規則

set -e

echo "========================================="
echo "架構合規性檢查 (Architecture Compliance Check)"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

total_violations=0

# Rule 1: momentum/ 不能 import api/
echo "規則 1: momentum/ 不能 import api/"
echo "-----------------------------------"
violations=$(grep -r "from api\." momentum/ --include="*.py" 2>/dev/null | grep -v "# Rule 1 Exempt" | grep -v "__pycache__" | wc -l)
if [ "$violations" -gt 0 ]; then
    echo -e "${RED}❌ 發現 $violations 處違規${NC}"
    grep -r "from api\." momentum/ --include="*.py" 2>/dev/null | grep -v "# Rule 1 Exempt" | grep -v "__pycache__" | head -10
    total_violations=$((total_violations + violations))
else
    echo -e "${GREEN}✅ 通過 (0 violations)${NC}"
fi
echo ""

# Rule 2: 跨 Domain 應使用 Protocol
echo "規則 2: 跨 Domain 應使用 Protocol"
echo "-----------------------------------"
# 檢查是否有直接跨 Domain import（不包含 Protocol）
violations=0
# 檢查 Analysis 是否直接 import DataExtraction（應該用 Protocol）
cross_imports=$(grep -r "from momentum.DataExtraction" momentum/Analysis/ --include="*.py" 2>/dev/null | grep -v "Protocol" | grep -v "__pycache__" | wc -l)
if [ "$cross_imports" -gt 0 ]; then
    violations=$((violations + cross_imports))
fi
# 檢查 Analysis 是否直接 import FeatureEngineering
cross_imports=$(grep -r "from momentum.FeatureEngineering" momentum/Analysis/ --include="*.py" 2>/dev/null | grep -v "Protocol" | grep -v "__pycache__" | wc -l)
if [ "$cross_imports" -gt 0 ]; then
    violations=$((violations + cross_imports))
fi

if [ "$violations" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  發現 $violations 處可能違規（建議使用 Protocol）${NC}"
    grep -r "from momentum.DataExtraction\|from momentum.FeatureEngineering" momentum/Analysis/ --include="*.py" 2>/dev/null | grep -v "Protocol" | grep -v "__pycache__" | head -5
    # Rule 2 violations are warnings, not hard failures
else
    echo -e "${GREEN}✅ 通過 (良好的 Protocol 使用)${NC}"
fi
echo ""

# Rule 3: api/services/ 應使用 Factory
echo "規則 3: api/services/ 應使用 Factory"
echo "-----------------------------------"
# 這個規則需要人工檢查，這裡只提示
echo -e "${YELLOW}ℹ️  需人工檢查 api/services/ 是否使用 momentum/factories.py${NC}"
factories_used=$(grep -r "from momentum.factories import" api/services/ --include="*.py" 2>/dev/null | wc -l)
direct_imports=$(grep -r "from momentum.*import.*Engine\|from momentum.*import.*Manager\|from momentum.*import.*Analyzer" api/services/ --include="*.py" 2>/dev/null | wc -l)
echo "   Factory 使用次數: $factories_used"
echo "   直接 import 次數: $direct_imports"
if [ "$direct_imports" -gt "$factories_used" ]; then
    echo -e "${YELLOW}   ⚠️  建議增加 Factory 使用${NC}"
fi
echo ""

# Rule 4: api/services/ 不互相 import
echo "規則 4: api/services/ 不互相 import"
echo "-----------------------------------"
violations=$(grep -r "from api.services" api/services/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
if [ "$violations" -gt 0 ]; then
    echo -e "${RED}❌ 發現 $violations 處違規${NC}"
    grep -r "from api.services" api/services/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | head -10
    total_violations=$((total_violations + violations))
else
    echo -e "${GREEN}✅ 通過 (0 violations)${NC}"
fi
echo ""

# Rule 5: Config 單一真相來源
echo "規則 5: Config 單一真相來源"
echo "-----------------------------------"
echo -e "${YELLOW}ℹ️  需人工檢查 momentum/ 是否只從 momentum/core/config.py 讀取配置${NC}"
momentum_config_imports=$(grep -r "from api.core.config import" momentum/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
if [ "$momentum_config_imports" -gt 0 ]; then
    echo -e "${RED}❌ momentum/ 不應該 import api.core.config${NC}"
    grep -r "from api.core.config import" momentum/ --include="*.py" 2>/dev/null | grep -v "__pycache__"
    total_violations=$((total_violations + momentum_config_imports))
else
    echo -e "${GREEN}✅ 通過 (momentum/ 無 import api.core.config)${NC}"
fi
echo ""

# Rule 7: DTOs 不跨域邊界
echo "規則 7: DTOs 不跨域邊界"
echo "-----------------------------------"
# 檢查 api/models 是否 import momentum/core
api_models_to_momentum=$(grep -r "from momentum.core" api/models/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
# 檢查 momentum/core 是否 import api/models
momentum_to_api_models=$(grep -r "from api.models" momentum/core/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | wc -l)
violations=$((api_models_to_momentum + momentum_to_api_models))
if [ "$violations" -gt 0 ]; then
    echo -e "${RED}❌ 發現 $violations 處違規${NC}"
    echo "api/models → momentum/core: $api_models_to_momentum"
    echo "momentum/core → api/models: $momentum_to_api_models"
    total_violations=$((total_violations + violations))
else
    echo -e "${GREEN}✅ 通過 (0 violations)${NC}"
fi
echo ""

# 總結
echo "========================================="
echo "檢查總結"
echo "========================================="
if [ "$total_violations" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有強制規則通過（0 violations）${NC}"
    echo ""
    echo "系統架構良好，模組可以獨立開發！"
    exit 0
else
    echo -e "${RED}❌ 發現 $total_violations 處違規${NC}"
    echo ""
    echo "請修復違規後再進行開發。"
    echo "參考文檔: docs/REFACTOR_ARCHITECTURE_V4.md"
    exit 1
fi
