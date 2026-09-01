"use client";

import { useState } from "react";
import { httpErrorMessage } from '@/lib/httpError';

interface CaseImportFormProps {
  onImportSuccess?: (result: ImportResult) => void;
}

interface ImportResult {
  success: boolean;
  total_rows: number;
  valid_cases: number;
  invalid_cases: number;
  imported_cases: number;
  errors: string[];
  warnings: string[];
  case_ids: string[];
  need_confirmation?: boolean;
  existing_count?: number;
}

export default function CaseImportForm({ onImportSuccess }: CaseImportFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [defaultTimeframe, setDefaultTimeframe] = useState("1h");
  const [validateOnly, setValidateOnly] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async (forceClear: boolean = false) => {
    if (!file) {
      setError("Please select a file");
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `/api/v1/case/import?default_timeframe=${defaultTimeframe}&validate_only=${validateOnly}&force_clear=${forceClear}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        let errorMessage = "Upload failed";
        try {
          const contentType = response.headers.get("content-type");
          if (contentType && contentType.includes("application/json")) {
            const errorData = await response.json();
            errorMessage = httpErrorMessage(errorData, JSON.stringify(errorData));
          } else {
            const text = await response.text();
            if (text) {
              errorMessage = text;
            }
          }
        } catch (parseError) {
          // 無法解析為JSON或文字時保留預設錯誤訊息
          console.warn("Failed to parse error response", parseError);
        }
        throw new Error(errorMessage);
      }

      const data: ImportResult = await response.json();

      // 檢查是否需要用戶確認清空
      if (data.need_confirmation && data.existing_count) {
        setUploading(false);

        const confirmed = window.confirm(
          `系統已有 ${data.existing_count} 個案例。\n\n` +
          `上傳新CSV將清空所有舊案例，是否繼續？`
        );

        if (confirmed) {
          // 用戶確認，重新上傳並強制清空
          await handleUpload(true);
          return;
        } else {
          // 用戶取消
          setError("導入已取消");
          return;
        }
      }

      setResult(data);

      if (data.success && onImportSuccess) {
        onImportSuccess(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="glass-panel rounded-xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-slate-100 mb-4">案例CSV導入</h3>

      {/* File Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          選擇CSV/Excel文件
        </label>
        <input
          type="file"
          accept=".csv,.xlsx,.xls,.txt"
          onChange={handleFileChange}
          className="block w-full text-sm text-slate-300
            file:mr-4 file:py-2 file:px-4
            file:rounded file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-500/20 file:text-blue-200
            hover:file:bg-blue-500/30 cursor-pointer"
          disabled={uploading}
        />
        {file && (
          <p className="mt-2 text-sm font-medium text-slate-400">
            已選擇: {file.name} ({(file.size / 1024).toFixed(2)} KB)
          </p>
        )}
      </div>

      {/* Options */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            預設時間框架
          </label>
          <select
            value={defaultTimeframe}
            onChange={(e) => setDefaultTimeframe(e.target.value)}
            className="w-full border border-slate-700 rounded px-3 py-2 bg-slate-900/60 text-slate-100 font-medium focus:border-blue-400/40 focus:ring-1 focus:ring-blue-400/40"
            disabled={uploading}
          >
            <option value="1m">1分鐘</option>
            <option value="5m">5分鐘</option>
            <option value="15m">15分鐘</option>
            <option value="30m">30分鐘</option>
            <option value="1h">1小時</option>
            <option value="4h">4小時</option>
            <option value="12h">12小時</option>
            <option value="1d">1天</option>
          </select>
        </div>

        <div className="flex items-center">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={validateOnly}
              onChange={(e) => setValidateOnly(e.target.checked)}
              className="mr-2 w-4 h-4 accent-blue-400"
              disabled={uploading}
            />
            <span className="text-sm font-medium text-slate-300">僅驗證（不導入）</span>
          </label>
        </div>
      </div>

      {/* Upload Button */}
      <button
        onClick={() => handleUpload(false)}
        disabled={!file || uploading}
        className={`w-full py-3 px-4 rounded-lg font-semibold transition-colors ${
          !file || uploading
            ? "bg-slate-700/60 text-slate-400 cursor-not-allowed"
            : "bg-blue-500/20 text-blue-100 border border-blue-400/40 hover:bg-blue-500/30"
        }`}
      >
        {uploading ? "上傳中..." : validateOnly ? "驗證CSV" : "上傳並導入"}
      </button>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-400/30 rounded">
          <p className="text-sm font-medium text-rose-200">{error}</p>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div
          className={`mt-4 p-4 border rounded ${
            result.success
              ? "bg-emerald-500/10 border-emerald-400/30"
              : "bg-amber-500/10 border-amber-400/30"
          }`}
        >
          <h4 className={`font-bold mb-3 ${
            result.success ? "text-emerald-200" : "text-amber-200"
          }`}>
            {result.success ? "✅ 導入成功" : "⚠️ 部分成功"}
          </h4>

          <div className="grid grid-cols-2 gap-2 text-sm font-medium text-slate-100 mb-3">
            <div>總行數: <span className="font-semibold">{result.total_rows}</span></div>
            <div>有效案例: <span className="font-semibold text-emerald-300">{result.valid_cases}</span></div>
            <div>無效案例: <span className="font-semibold text-rose-300">{result.invalid_cases}</span></div>
            <div>已導入: <span className="font-semibold text-blue-300">{result.imported_cases}</span></div>
          </div>

          {result.warnings.length > 0 && (
            <div className="mb-3">
              <p className="text-sm font-semibold text-amber-200 mb-1">警告:</p>
              <ul className="list-disc list-inside text-sm font-medium text-amber-200/80">
                {result.warnings.slice(0, 5).map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
                {result.warnings.length > 5 && (
                  <li className="text-slate-400">
                    ...還有 {result.warnings.length - 5} 個警告
                  </li>
                )}
              </ul>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-rose-200 mb-1">錯誤:</p>
              <ul className="list-disc list-inside text-sm font-medium text-rose-200/80">
                {result.errors.slice(0, 5).map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
                {result.errors.length > 5 && (
                  <li className="text-slate-400">
                    ...還有 {result.errors.length - 5} 個錯誤
                  </li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
