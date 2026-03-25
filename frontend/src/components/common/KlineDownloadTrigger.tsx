'use client';

import { useCallback, useEffect, useState } from 'react';

type KlineStatus = 'unknown' | 'ready' | 'missing' | 'checking' | 'downloading' | 'failed';

interface KlineDownloadTriggerProps {
  symbol: string;
  timeframe: string;
  onDownloadComplete?: () => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function KlineDownloadTrigger({ symbol, timeframe, onDownloadComplete }: KlineDownloadTriggerProps) {
  const [status, setStatus] = useState<KlineStatus>('unknown');
  const [message, setMessage] = useState<string>('');

  const checkStatus = useCallback(async () => {
    if (!symbol || !timeframe) {
      setStatus('unknown');
      setMessage('請先選擇 symbol 與 timeframe');
      return;
    }

    setStatus('checking');
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/kline/status?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`
      );
      if (!response.ok) {
        throw new Error(response.statusText);
      }

      const payload = (await response.json()) as { ready?: boolean; range?: string };
      if (payload.ready) {
        setStatus('ready');
        setMessage(payload.range ? `K 線已下載 (${payload.range})` : 'K 線已下載');
      } else {
        setStatus('missing');
        setMessage('尚未下載 K 線資料');
      }
    } catch {
      setStatus('failed');
      setMessage('無法檢查 K 線狀態');
    }
  }, [symbol, timeframe]);

  const download = useCallback(async () => {
    if (!symbol || !timeframe) {
      return;
    }

    setStatus('downloading');
    setMessage('正在下載 K 線資料...');

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/kline/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol, timeframe }),
      });

      if (!response.ok) {
        throw new Error(response.statusText);
      }

      await checkStatus();
      if (onDownloadComplete) {
        onDownloadComplete();
      }
    } catch {
      setStatus('failed');
      setMessage('K 線下載失敗');
    }
  }, [checkStatus, onDownloadComplete, symbol, timeframe]);

  useEffect(() => {
    checkStatus().catch(() => undefined);
  }, [checkStatus]);

  if (status === 'ready') {
    return <div className="text-sm text-emerald-400">{message}</div>;
  }

  return (
    <div className="rounded-md border border-amber-300/40 bg-amber-500/10 p-3 text-sm text-amber-100">
      <p>{message || 'K 線狀態未知'}</p>
      <button
        type="button"
        onClick={download}
        disabled={status === 'downloading' || status === 'checking'}
        className="mt-2 rounded border border-amber-200/40 px-3 py-1 text-xs hover:bg-amber-500/20 disabled:opacity-50"
      >
        {status === 'downloading' ? '下載中...' : '立即下載'}
      </button>
    </div>
  );
}
