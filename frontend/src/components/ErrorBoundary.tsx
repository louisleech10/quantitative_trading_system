/**
 * frontend/src/components/ErrorBoundary.tsx
 * React Error Boundary - 捕獲組件樹中的 JavaScript 錯誤
 * 
 * 用於防止單個組件崩潰導致整個應用崩潰
 */

'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // 記錄錯誤到控制台
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // 調用可選的錯誤處理回調
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // 使用自定義 fallback 或默認錯誤 UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[200px] flex items-center justify-center p-6">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 max-w-md">
            <div className="flex items-start">
              <svg
                className="w-6 h-6 text-red-600 dark:text-red-400 mr-3 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-red-800 dark:text-red-200 mb-1">
                  組件渲染錯誤
                </h3>
                <p className="text-sm text-red-700 dark:text-red-300">
                  {this.state.error?.message || '發生未知錯誤'}
                </p>
                <button
                  onClick={() => this.setState({ hasError: false, error: null })}
                  className="mt-3 text-sm text-red-800 dark:text-red-200 underline hover:no-underline"
                >
                  重試
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
