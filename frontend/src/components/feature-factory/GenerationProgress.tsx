'use client';

import { useEffect, useRef } from 'react';
import { FeatureTask, FeatureGenerationProgress } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

interface GenerationProgressProps {
  task: FeatureTask | null;
}

export default function GenerationProgress({ task }: GenerationProgressProps) {
  const { progress, setProgress, setCurrentTask } = useFeatureFactoryStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!task?.task_id) {
      return;
    }

    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/features/${task.task_id}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as FeatureGenerationProgress;
        setProgress(data);
        if (data.status) {
          setCurrentTask({
            ...task,
            status: data.status,
            progress: data.progress ?? task.progress,
            current_stage: data.stage ?? task.current_stage,
          });
        }
      } catch (err) {
        console.error('[GenerationProgress] Invalid message', err);
      }
    };

    ws.onerror = () => {
      console.error('[GenerationProgress] WebSocket error');
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [task, setProgress, setCurrentTask]);

  if (!task) {
    return (
      <div className="glass-panel rounded-2xl p-6 text-sm text-slate-400">
        尚未啟動生成任務。
      </div>
    );
  }

  const displayProgress = Math.round((progress?.progress ?? task.progress ?? 0) * 100);

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold text-slate-100">生成進度</div>
          <div className="text-xs text-slate-400">{task.current_stage || progress?.stage || '等待啟動'}</div>
        </div>
        <div className="text-xl font-semibold text-amber-200">{displayProgress}%</div>
      </div>

      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-amber-400/70 to-cyan-400/60 transition-all"
          style={{ width: `${displayProgress}%` }}
        />
      </div>

      <div className="text-xs text-slate-400">{progress?.message || '等待進度更新...'}</div>
    </div>
  );
}
