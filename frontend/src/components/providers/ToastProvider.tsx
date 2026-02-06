/**
 * frontend/src/components/providers/ToastProvider.tsx
 * Toast 通知提供者 - 使用 react-hot-toast
 * 
 * 提供全域 Toast 通知功能，用於成功/錯誤/警告訊息
 */

'use client';

import { Toaster } from 'react-hot-toast';

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      reverseOrder={false}
      gutter={8}
      toastOptions={{
        // 默認選項
        duration: 4000,
        style: {
          background: '#1a233a',
          color: '#fff',
          fontSize: '14px',
          borderRadius: '8px',
          padding: '12px 16px',
        },
        // 成功訊息
        success: {
          duration: 3000,
          iconTheme: {
            primary: '#34d399',
            secondary: '#fff',
          },
          style: {
            background: '#34d399',
            color: '#fff',
          },
        },
        // 錯誤訊息
        error: {
          duration: 5000,
          iconTheme: {
            primary: '#fb7185',
            secondary: '#fff',
          },
          style: {
            background: '#fb7185',
            color: '#fff',
          },
        },
        // 載入訊息
        loading: {
          iconTheme: {
            primary: '#60a5fa',
            secondary: '#fff',
          },
          style: {
            background: '#60a5fa',
            color: '#fff',
          },
        },
      }}
    />
  );
}
