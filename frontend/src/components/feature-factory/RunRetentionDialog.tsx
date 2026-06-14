'use client';

import { useState } from 'react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const API = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/features`;

export default function RunRetentionDialog() {
  const run = useFeatureFactoryStore((state) => state.completionQueue[0]);
  const shift = useFeatureFactoryStore((state) => state.shiftCompletion);
  const [alias, setAlias] = useState('');
  const [error, setError] = useState<string | null>(null);
  if (!run) return null;
  const path = `${API}/runs/${run.symbol}/${run.timeframe}/${run.config_hash}`;
  const saveAlias = async () => {
    const response = await fetch(`${path}/alias`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ alias }) });
    if (!response.ok) { setError(response.status === 422 ? '名稱已被使用' : '命名失敗'); return; }
    shift(); setAlias(''); setError(null);
  };
  const deleteRun = async () => {
    const response = await fetch(path, { method: 'DELETE' });
    if (!response.ok) { setError(response.status === 409 ? 'Run 正在使用中' : '刪除失敗'); return; }
    shift(); setError(null);
  };
  return <div role="dialog" aria-label="Run retention" className="glass-panel p-4">
    <p>保留這次產生的 Run？</p>
    <input aria-label="Run alias" value={alias} onChange={(event) => setAlias(event.target.value)} />
    {error && <p role="alert">{error}</p>}
    <button onClick={saveAlias}>命名保留</button>
    <button onClick={shift}>保留未命名</button>
    <button onClick={() => void deleteRun()}>立即刪除</button>
    <button onClick={shift}>關閉</button>
  </div>;
}
