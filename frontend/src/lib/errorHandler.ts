/**
 * frontend/src/lib/errorHandler.ts
 * 統一錯誤處理工具
 * 
 * 提供錯誤分類、重試邏輯、用戶友好的錯誤訊息
 */

import toast from 'react-hot-toast';

/**
 * 錯誤類型枚舉
 */
export enum ErrorType {
  NETWORK = 'network',           // 網絡錯誤（可重試）
  TIMEOUT = 'timeout',           // 超時錯誤（可重試）
  RATE_LIMIT = 'rate_limit',     // 速率限制（可重試，需延遲）
  UNAUTHORIZED = 'unauthorized', // 未授權（不可重試）
  NOT_FOUND = 'not_found',       // 資源不存在（不可重試）
  VALIDATION = 'validation',     // 驗證錯誤（不可重試）
  SERVER = 'server',             // 服務器錯誤（可重試）
  UNKNOWN = 'unknown',           // 未知錯誤（可重試）
}

/**
 * 錯誤信息接口
 */
export interface ErrorInfo {
  type: ErrorType;
  message: string;
  originalError?: Error;
  retryable: boolean;
  retryDelay?: number; // 毫秒
}

function toError(error: unknown): Error {
  if (error instanceof Error) {
    return error;
  }
  if (typeof error === 'string') {
    return new Error(error);
  }
  return new Error('發生未知錯誤');
}

/**
 * 分類錯誤類型
 */
export function classifyError(error: unknown): ErrorInfo {
  const normalizedError = toError(error);

  // 網絡錯誤
  if (normalizedError instanceof TypeError && normalizedError.message.includes('fetch')) {
    return {
      type: ErrorType.NETWORK,
      message: '網絡連接失敗，請檢查您的網絡連接',
      originalError: normalizedError,
      retryable: true,
      retryDelay: 1000,
    };
  }

  // HTTP 錯誤
  if (normalizedError.message) {
    const msg = normalizedError.message.toLowerCase();

    // 超時
    if (msg.includes('timeout') || msg.includes('timed out')) {
      return {
        type: ErrorType.TIMEOUT,
        message: '請求超時，請稍後重試',
        originalError: normalizedError,
        retryable: true,
        retryDelay: 2000,
      };
    }

    // 速率限制
    if (msg.includes('429') || msg.includes('rate limit')) {
      return {
        type: ErrorType.RATE_LIMIT,
        message: '請求過於頻繁，請稍後再試',
        originalError: normalizedError,
        retryable: true,
        retryDelay: 5000,
      };
    }

    // 未授權
    if (msg.includes('401') || msg.includes('unauthorized')) {
      return {
        type: ErrorType.UNAUTHORIZED,
        message: '未授權訪問，請重新登入',
        originalError: normalizedError,
        retryable: false,
      };
    }

    // 資源不存在
    if (msg.includes('404') || msg.includes('not found')) {
      return {
        type: ErrorType.NOT_FOUND,
        message: '請求的資源不存在',
        originalError: normalizedError,
        retryable: false,
      };
    }

    // 驗證錯誤
    if (msg.includes('400') || msg.includes('validation')) {
      return {
        type: ErrorType.VALIDATION,
        message: '請求參數錯誤，請檢查輸入',
        originalError: normalizedError,
        retryable: false,
      };
    }

    // 服務器錯誤
    if (msg.includes('500') || msg.includes('502') || msg.includes('503')) {
      return {
        type: ErrorType.SERVER,
        message: '服務器錯誤，請稍後重試',
        originalError: normalizedError,
        retryable: true,
        retryDelay: 3000,
      };
    }
  }

  // 未知錯誤
  return {
    type: ErrorType.UNKNOWN,
    message: normalizedError.message || '發生未知錯誤',
    originalError: normalizedError,
    retryable: true,
    retryDelay: 2000,
  };
}

/**
 * 顯示錯誤 Toast
 */
export function showErrorToast(error: unknown, customMessage?: string) {
  const errorInfo = classifyError(error);
  const message = customMessage || errorInfo.message;
  
  toast.error(message, {
    duration: errorInfo.retryable ? 4000 : 5000,
  });
  
  return errorInfo;
}

/**
 * 顯示成功 Toast
 */
export function showSuccessToast(message: string) {
  toast.success(message);
}

/**
 * 顯示載入 Toast（返回 toastId 用於後續更新）
 */
export function showLoadingToast(message: string) {
  return toast.loading(message);
}

/**
 * 更新 Toast 狀態
 */
export function updateToast(toastId: string, type: 'success' | 'error', message: string) {
  if (type === 'success') {
    toast.success(message, { id: toastId });
  } else {
    toast.error(message, { id: toastId });
  }
}

/**
 * 關閉 Toast
 */
export function dismissToast(toastId?: string) {
  if (toastId) {
    toast.dismiss(toastId);
  } else {
    toast.dismiss();
  }
}

/**
 * 帶重試的異步函數包裝器
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    retryDelay?: number;
    onRetry?: (attempt: number) => void;
  } = {}
): Promise<T> {
  const { maxRetries = 3, retryDelay = 1000, onRetry } = options;
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const errorInfo = classifyError(error);

      // 如果錯誤不可重試，直接拋出
      if (!errorInfo.retryable) {
        throw error;
      }

      // 如果已達最大重試次數，拋出錯誤
      if (attempt === maxRetries) {
        throw error;
      }

      // 調用重試回調
      onRetry?.(attempt);

      // 等待後重試
      const delay = errorInfo.retryDelay || retryDelay;
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

/**
 * API 調用包裝器（帶錯誤處理和 Toast）
 */
export async function withErrorHandling<T>(
  fn: () => Promise<T>,
  options: {
    loadingMessage?: string;
    successMessage?: string;
    errorMessage?: string;
    showToast?: boolean;
    retry?: boolean;
    maxRetries?: number;
  } = {}
): Promise<T> {
  const {
    loadingMessage,
    successMessage,
    errorMessage,
    showToast = true,
    retry = false,
    maxRetries = 3,
  } = options;

  let toastId: string | undefined;

  try {
    // 顯示載入 Toast
    if (showToast && loadingMessage) {
      toastId = showLoadingToast(loadingMessage);
    }

    // 執行函數（帶或不帶重試）
    const result = retry
      ? await withRetry(fn, { maxRetries })
      : await fn();

    // 顯示成功 Toast
    if (showToast && successMessage) {
      if (toastId) {
        updateToast(toastId, 'success', successMessage);
      } else {
        showSuccessToast(successMessage);
      }
    } else if (toastId) {
      dismissToast(toastId);
    }

    return result;
  } catch (error) {
    // 顯示錯誤 Toast
    if (showToast) {
      if (toastId) {
        dismissToast(toastId);
      }
      showErrorToast(error, errorMessage);
    }

    throw error;
  }
}
