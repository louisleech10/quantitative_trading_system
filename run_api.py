#!/usr/bin/env python3
"""
Case Search API 啟動腳本
用於啟動FastAPI開發服務器
"""

import sys
import os
from pathlib import Path

# 確保項目根目錄在Python路徑中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函數"""
    try:
        # 導入API模組
        from api.main import run_server
        
        print("正在啟動 Case Search API 服務器...")
        print("按 Ctrl+C 停止服務器")
        print("-" * 50)
        
        # 運行服務器
        run_server()
        
    except KeyboardInterrupt:
        print("\n服務器已停止")
    except ImportError as e:
        print(f"導入錯誤: {e}")
        print("請確保所有依賴都已安裝: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"啟動失敗: {e}")
        sys.exit(1)

def show_hardware_info():
    """啟動時顯示硬體配置"""
    cpu_count = multiprocessing.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    optimal_workers = get_optimal_workers()
    
    print("="*50)
    print("硬體配置檢測")
    print(f"CPU核心：{cpu_count}")
    print(f"總內存：{memory_gb:.1f} GB")
    print(f"優化worker數：{optimal_workers}")
    print(f"預估性能：{'標準' if cpu_count == 8 else f'{cpu_count/8:.1f}x'}")
    print("="*50)

if __name__ == "__main__": #test
    main()