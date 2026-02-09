import { useCallback, useEffect, useRef, useState } from 'react';
import { AutoResearchStatus, AutoResearchLogEntry } from '@/lib/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

interface StartResearchPayload {
  objective: { metric: string; target: number };
  constraints: { max_iterations: number; max_time_minutes: number };
}

export function useAutoResearch() {
  const [status, setStatus] = useState<AutoResearchStatus | null>(null);
  const [logs, setLogs] = useState<AutoResearchLogEntry[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback((researchId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/features/research/${researchId}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as AutoResearchLogEntry | AutoResearchStatus;
        if ('iteration' in data) {
          setLogs((prev) => [data, ...prev]);
        } else {
          setStatus(data);
          setIsRunning(data.status === 'running');
        }
      } catch (err) {
        console.error('[useAutoResearch] Invalid message', err);
      }
    };

    ws.onerror = () => {
      console.error('[useAutoResearch] WebSocket error');
    };

    wsRef.current = ws;
  }, []);

  const startResearch = useCallback(async (payload: StartResearchPayload) => {
    const response = await fetch(`${API_BASE_URL}${API_PREFIX}/research/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error('啟動研究失敗');
    }

    const data = await response.json();
    setStatus({ status: 'running', research_id: data.research_id });
    setIsRunning(true);
    connect(data.research_id);
  }, [connect]);

  const stopResearch = useCallback(async () => {
    if (!status?.research_id) {
      return;
    }

    await fetch(`${API_BASE_URL}${API_PREFIX}/research/${status.research_id}/stop`, {
      method: 'POST',
    });

    setIsRunning(false);
  }, [status]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    status,
    logs,
    isRunning,
    startResearch,
    stopResearch,
  };
}
