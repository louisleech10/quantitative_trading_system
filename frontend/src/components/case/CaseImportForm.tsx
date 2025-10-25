"use client";

import { useState } from "react";

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

  const handleUpload = async () => {
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
        `/api/v1/case/import?default_timeframe=${defaultTimeframe}&validate_only=${validateOnly}`,
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
            errorMessage = errorData.detail || JSON.stringify(errorData);
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
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <h3 className="text-lg font-bold text-gray-900 mb-4">案例CSV導入</h3>

      {/* File Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          選擇CSV/Excel文件
        </label>
        <input
          type="file"
          accept=".csv,.xlsx,.xls,.txt"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-700
            file:mr-4 file:py-2 file:px-4
            file:rounded file:border-0
            file:text-sm file:font-bold
            file:bg-blue-100 file:text-blue-800
            hover:file:bg-blue-200 cursor-pointer"
          disabled={uploading}
        />
        {file && (
          <p className="mt-2 text-sm font-medium text-gray-700">
            已選擇: {file.name} ({(file.size / 1024).toFixed(2)} KB)
          </p>
        )}
      </div>

      {/* Options */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            預設時間框架
          </label>
          <select
            value={defaultTimeframe}
            onChange={(e) => setDefaultTimeframe(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
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
              className="mr-2 w-4 h-4"
              disabled={uploading}
            />
            <span className="text-sm font-medium text-gray-700">僅驗證（不導入）</span>
          </label>
        </div>
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className={`w-full py-3 px-4 rounded-lg font-bold text-white transition-colors ${
          !file || uploading
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 shadow-md"
        }`}
      >
        {uploading ? "上傳中..." : validateOnly ? "驗證CSV" : "上傳並導入"}
      </button>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-300 rounded">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div
          className={`mt-4 p-4 border rounded ${
            result.success
              ? "bg-green-50 border-green-300"
              : "bg-yellow-50 border-yellow-300"
          }`}
        >
          <h4 className={`font-bold mb-3 ${
            result.success ? "text-green-900" : "text-yellow-900"
          }`}>
            {result.success ? "✅ 導入成功" : "⚠️ 部分成功"}
          </h4>

          <div className="grid grid-cols-2 gap-2 text-sm font-medium text-gray-900 mb-3">
            <div>總行數: <span className="font-bold">{result.total_rows}</span></div>
            <div>有效案例: <span className="font-bold text-green-700">{result.valid_cases}</span></div>
            <div>無效案例: <span className="font-bold text-red-700">{result.invalid_cases}</span></div>
            <div>已導入: <span className="font-bold text-blue-700">{result.imported_cases}</span></div>
          </div>

          {result.warnings.length > 0 && (
            <div className="mb-3">
              <p className="text-sm font-bold text-yellow-900 mb-1">警告:</p>
              <ul className="list-disc list-inside text-sm font-medium text-yellow-800">
                {result.warnings.slice(0, 5).map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
                {result.warnings.length > 5 && (
                  <li className="text-gray-700">
                    ...還有 {result.warnings.length - 5} 個警告
                  </li>
                )}
              </ul>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-sm font-bold text-red-900 mb-1">錯誤:</p>
              <ul className="list-disc list-inside text-sm font-medium text-red-800">
                {result.errors.slice(0, 5).map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
                {result.errors.length > 5 && (
                  <li className="text-gray-700">
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
