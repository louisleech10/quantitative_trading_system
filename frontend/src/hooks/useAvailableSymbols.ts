/**
 * useAvailableSymbols Hook
 * 
 * 從後端 /api/v1/case/list 動態載入可用的交易對列表
 * 用於交易對多選選擇器，支援加密貨幣、台股、美股等任意資產類型
 * 
 * @returns {Object} symbols - 可用交易對陣列
 * @returns {boolean} isLoading - 載入狀態
 * @returns {string|null} error - 錯誤訊息
 * @returns {Function} refetch - 重新載入函式
 */

import { useState, useEffect, useCallback } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UseAvailableSymbolsReturn {
  symbols: string[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useAvailableSymbols(): UseAvailableSymbolsReturn {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSymbols = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/case/list`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: 無法載入交易對列表`);
      }

      const data = await response.json();

      // 檢查資料格式
      if (!data.symbols || !Array.isArray(data.symbols)) {
        throw new Error("API 回傳格式錯誤：缺少 symbols 欄位");
      }

      // 過濾空值並排序
      const validSymbols = data.symbols
        .filter((s: unknown) => typeof s === "string" && s.trim().length > 0)
        .sort();

      setSymbols(validSymbols);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "未知錯誤";
      setError(errorMessage);
      console.error("Failed to fetch available symbols:", err);
      
      // 降級處理：載入失敗時提供預設交易對
      setSymbols([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 初始載入
  useEffect(() => {
    fetchSymbols();
  }, [fetchSymbols]);

  return {
    symbols,
    isLoading,
    error,
    refetch: fetchSymbols,
  };
}
