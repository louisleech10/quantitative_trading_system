'use client';

import { useEffect, useState } from 'react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const btnBase =
  'inline-flex items-center justify-center rounded-lg border px-3 py-2 text-sm transition disabled:opacity-40 disabled:cursor-not-allowed';

export default function RunRetentionDialog() {
  const item = useFeatureFactoryStore((state) => state.completionQueue[0]);
  const run = item && item.source !== 'batch' ? item : null;
  const shiftCompletion = useFeatureFactoryStore((state) => state.shiftCompletion);
  const updateRunAlias = useFeatureFactoryStore((state) => state.updateRunAlias);
  const deleteRun = useFeatureFactoryStore((state) => state.deleteRun);

  const [alias, setAlias] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<'alias' | 'delete' | null>(null);

  useEffect(() => {
    setAlias('');
    setError(null);
    setBusy(null);
  }, [run?.symbol, run?.timeframe, run?.config_hash]);

  const dismiss = () => {
    shiftCompletion();
    setAlias('');
    setError(null);
  };

  const saveWithAlias = async () => {
    if (!run) return;
    setBusy('alias');
    setError(null);
    const result = await updateRunAlias(
      run.symbol,
      run.timeframe,
      run.config_hash,
      alias.trim(),
    );
    setBusy(null);
    if (!result.ok) {
      setError(result.error ?? '命名失敗');
      return;
    }
    dismiss();
  };

  const remove = async () => {
    if (!run) return;
    setBusy('delete');
    setError(null);
    const result = await deleteRun(run.symbol, run.timeframe, run.config_hash);
    setBusy(null);
    if (!result.ok) {
      setError(result.error ?? '刪除失敗');
      return;
    }
    dismiss();
  };

  return (
    <Dialog
      open={run != null}
      onOpenChange={(isOpen) => {
        if (!isOpen && run) dismiss();
      }}
    >
      <DialogContent className="max-w-md gap-4 p-5" aria-label="Run retention">
        {run && (
          <>
            <DialogHeader>
              <DialogTitle className="text-sm font-semibold text-slate-100">
                保留這次產生的 Run？
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-400 font-mono">
                {run.symbol} / {run.timeframe}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-2">
              <label htmlFor="run-retention-alias" className="block text-xs font-medium text-slate-300">
                別名
              </label>
              <input
                id="run-retention-alias"
                aria-label="Run alias"
                value={alias}
                onChange={(event) => setAlias(event.target.value)}
                placeholder="輸入名稱(可留空)"
                className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-300/40"
                autoFocus
              />
            </div>

            {error && (
              <p
                role="alert"
                className="text-xs text-rose-300 border border-rose-400/30 bg-rose-400/10 rounded-lg px-3 py-2"
              >
                {error}
              </p>
            )}

            <DialogFooter className="flex flex-col gap-2 sm:flex-col sm:space-x-0">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => void saveWithAlias()}
                className={`${btnBase} w-full border-cyan-400/30 bg-cyan-400/10 text-cyan-100 hover:border-cyan-300/50`}
              >
                {busy === 'alias' ? '儲存中…' : '命名並保留'}
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={dismiss}
                className={`${btnBase} w-full border-white/15 text-slate-200 hover:bg-white/5`}
              >
                保留未命名
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => void remove()}
                className={`${btnBase} w-full border-rose-400/30 text-rose-200 hover:border-rose-300/50 hover:bg-rose-400/10`}
              >
                {busy === 'delete' ? '刪除中…' : '立即刪除'}
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={dismiss}
                className={`${btnBase} w-full border-white/10 text-slate-400 hover:bg-white/5`}
              >
                關閉
              </button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
