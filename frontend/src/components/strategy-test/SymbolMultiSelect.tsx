/**
 * SymbolMultiSelect - 多選交易對選擇器
 * 
 * 功能:
 * 1. 支援多選交易對（Checkbox 列表）
 * 2. 固定第一選項 "全部交易對"（ALL_SYMBOLS）
 * 3. 搜尋過濾功能（debounce 300ms）
 * 4. 全選/反選按鈕
 * 5. 已選標籤顯示（可刪除）
 * 6. 統計資訊顯示
 */

import { useState, useMemo, useDeferredValue } from "react";
import { Search, X, CheckSquare, Square } from "lucide-react";

interface SymbolMultiSelectProps {
  value: string[];
  onChange: (symbols: string[]) => void;
  availableSymbols: string[];
  isLoading?: boolean;
  error?: string | null;
}

export function SymbolMultiSelect({
  value,
  onChange,
  availableSymbols,
  isLoading = false,
  error = null,
}: SymbolMultiSelectProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const deferredSearchTerm = useDeferredValue(searchTerm);

  // 確保 value 是有效的陣列
  const safeValue = Array.isArray(value) ? value : [];

  // 過濾搜尋結果
  const filteredSymbols = useMemo(() => {
    if (!deferredSearchTerm.trim()) return availableSymbols;
    const term = deferredSearchTerm.toLowerCase();
    return availableSymbols.filter((symbol) =>
      symbol.toLowerCase().includes(term)
    );
  }, [availableSymbols, deferredSearchTerm]);

  // 檢查是否已選
  const isSelected = (symbol: string) => safeValue.includes(symbol);
  const isAllSymbolsSelected = safeValue.includes("ALL_SYMBOLS");

  // 切換選擇
  const toggleSymbol = (symbol: string) => {
    if (isSelected(symbol)) {
      onChange(safeValue.filter((s) => s !== symbol));
    } else {
      onChange([...safeValue, symbol]);
    }
  };

  // 全選（不包含 ALL_SYMBOLS）
  const selectAll = () => {
    const allWithoutSpecial = availableSymbols.filter((s) => s !== "ALL_SYMBOLS");
    onChange([...safeValue, ...allWithoutSpecial.filter((s) => !safeValue.includes(s))]);
  };

  // 反選（清空所有選擇）
  const deselectAll = () => {
    onChange([]);
  };

  // 移除已選標籤
  const removeSymbol = (symbol: string) => {
    onChange(safeValue.filter((s) => s !== symbol));
  };

  return (
    <div className="space-y-3">
      {/* 快捷操作按鈕 */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={selectAll}
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
        >
          全選
        </button>
        <button
          type="button"
          onClick={deselectAll}
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-medium text-slate-200 transition hover:bg-white/10"
        >
          清空
        </button>
      </div>

      {/* 搜尋框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="搜尋交易對..."
          className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-10 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/30"
        />
      </div>

      {/* 載入狀態 */}
      {isLoading && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-4 text-center text-sm text-slate-400">
          載入交易對中...
        </div>
      )}

      {/* 錯誤訊息 */}
      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      {/* 交易對列表 */}
      {!isLoading && !error && (
        <div className="max-h-64 overflow-y-auto rounded-lg border border-white/10 bg-white/5">
          {/* 固定第一項：全部交易對 */}
          <label
            className={`flex cursor-pointer items-center gap-3 border-b border-white/10 px-4 py-3 transition hover:bg-sky-500/10 ${
              isAllSymbolsSelected ? "bg-sky-500/10" : ""
            }`}
          >
            <input
              type="checkbox"
              checked={isAllSymbolsSelected}
              onChange={() => toggleSymbol("ALL_SYMBOLS")}
              className="h-4 w-4 rounded border-white/20 text-sky-400 focus:ring-sky-400"
            />
            <div className="flex flex-1 items-center gap-2">
              <span className="text-lg">🌐</span>
              <span className="font-semibold text-sky-200">
                全部交易對
              </span>
              <span className="ml-auto text-xs text-slate-400">
                ({availableSymbols.length} 個)
              </span>
            </div>
          </label>

          {/* 動態交易對列表 */}
          {filteredSymbols.length === 0 ? (
            <div className="p-4 text-center text-sm text-slate-400">
              {availableSymbols.length === 0
                ? "尚無可用交易對，請先匯入案例"
                : "找不到符合的交易對"}
            </div>
          ) : (
            filteredSymbols.map((symbol) => (
              <label
                key={symbol}
                className={`flex cursor-pointer items-center gap-3 border-b border-white/10 px-4 py-2.5 transition hover:bg-white/5 ${
                  isSelected(symbol) ? "bg-white/10" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected(symbol)}
                  onChange={() => toggleSymbol(symbol)}
                  className="h-4 w-4 rounded border-white/20 text-sky-400 focus:ring-sky-400"
                />
                <div className="flex flex-1 items-center justify-between">
                  <span className="text-sm font-medium text-slate-200">
                    {symbol}
                  </span>
                </div>
              </label>
            ))
          )}
        </div>
      )}

      {/* 已選標籤區域 */}
      {safeValue.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-300">
            <span>
              已選擇：
              {isAllSymbolsSelected
                ? `全部 ${availableSymbols.length} 個`
                : `${safeValue.length} 個`}
            </span>
            {searchTerm && (
              <span className="text-slate-500">
                搜尋結果：{filteredSymbols.length} 個
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {safeValue.map((symbol) => (
              <span
                key={symbol}
                className="inline-flex items-center gap-1 rounded-md bg-sky-500/20 px-2 py-1 text-xs font-medium text-sky-200"
              >
                {symbol === "ALL_SYMBOLS" ? (
                  <>
                    <span>🌐</span>
                    <span>全部</span>
                  </>
                ) : (
                  symbol
                )}
                <button
                  type="button"
                  onClick={() => removeSymbol(symbol)}
                  className="ml-0.5 rounded hover:bg-sky-500/30"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 空狀態提示 */}
      {safeValue.length === 0 && !isLoading && (
        <div className="rounded-lg border border-dashed border-white/10 bg-white/5 p-4 text-center text-xs text-slate-400">
          請選擇至少一個交易對以開始測試或優化
        </div>
      )}
    </div>
  );
}
