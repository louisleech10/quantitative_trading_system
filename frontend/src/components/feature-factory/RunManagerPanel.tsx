'use client';

import { useEffect, useState } from 'react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const API = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/features`;

export default function RunManagerPanel() {
  const { runs, runsLoading, runsError, fetchRuns } = useFeatureFactoryStore();
  const [error, setError] = useState<string | null>(null);
  const [aliases, setAliases] = useState<Record<string, string>>({});
  useEffect(() => { void fetchRuns(); }, [fetchRuns]);
  const remove = async (index: number) => {
    const run = runs[index];
    if (!confirm(`刪除 ${run.size_bytes ?? 0} bytes（含 CGSA）？`)) return;
    const response = await fetch(`${API}/runs/${run.symbol}/${run.timeframe}/${run.config_hash}`, { method: 'DELETE' });
    if (!response.ok) {
      const body = await response.json();
      setError(response.status === 409 ? 'Run 正在使用中' : (body.detail?.errors || ['delete_partial']).join(', '));
      return;
    }
    await fetchRuns();
  };
  const saveAlias = async (index: number) => {
    const run = runs[index];
    const key = `${run.symbol}-${run.timeframe}-${run.config_hash}`;
    const response = await fetch(`${API}/runs/${run.symbol}/${run.timeframe}/${run.config_hash}/alias`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ alias: aliases[key] ?? run.alias ?? '' }),
    });
    if (!response.ok) { setError(response.status === 422 ? '名稱已被使用' : '命名失敗'); return; }
    await fetchRuns();
  };
  if (runsLoading) return <p>載入 Runs…</p>;
  if (runsError) return <div><p role="alert">{runsError}</p><button onClick={() => void fetchRuns()}>重試</button></div>;
  return <section><h2>Run 管理</h2>{error && <p role="alert">{error}</p>}
    {runs.length === 0 ? <p>尚無 Runs</p> : runs.map((run, index) => { const key = `${run.symbol}-${run.timeframe}-${run.config_hash}`; return <div key={key}>
      <span>{run.config_hash}</span><input aria-label={`Alias ${run.config_hash}`} value={aliases[key] ?? run.alias ?? ''} onChange={(event) => setAliases((current) => ({ ...current, [key]: event.target.value }))} />
      <button onClick={() => void saveAlias(index)}>儲存名稱</button><button disabled={run.active} onClick={() => void remove(index)}>刪除</button>
    </div>; })}</section>;
}
