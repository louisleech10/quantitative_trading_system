"""
Task 4.2 測試執行器

執行 XGBoost 分析引擎的所有測試

Author: AI Agent
Date: 2026-01-10
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger

logger = get_logger(__name__)


def run_test_file(test_file: str) -> bool:
    """執行單個測試檔案"""
    test_path = project_root / test_file
    
    if not test_path.exists():
        logger.error(f"測試檔案不存在: {test_path}")
        return False
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"執行測試: {test_file}")
    logger.info(f"{'=' * 80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=str(project_root),
            capture_output=False,
            text=True
        )
        
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"執行測試失敗: {str(e)}", exc_info=True)
        return False


def main():
    """執行所有 Task 4.2 測試"""
    logger.info("=" * 80)
    logger.info("Task 4.2 XGBoost Analysis Engine 測試套件")
    logger.info("=" * 80)
    
    test_files = [
        "test_xgboost_analyzer.py",
        "test_pattern_extractor.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        success = run_test_file(test_file)
        results[test_file] = success
    
    # 總結
    logger.info("\n" + "=" * 80)
    logger.info("測試結果總結")
    logger.info("=" * 80)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status}: {test_file}")
    
    logger.info("=" * 80)
    logger.info(f"總計: {passed}/{total} 測試通過")
    logger.info("=" * 80)
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
