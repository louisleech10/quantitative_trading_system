'use client';

import { useState } from 'react';
import { MessageSquareText } from 'lucide-react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

interface NLInputBoxProps {
  onSubmit: (text: string) => Promise<void>;
}

export default function NLInputBox({ onSubmit }: NLInputBoxProps) {
  const [text, setText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const { lastNLResult } = useFeatureFactoryStore();

  const handleSubmit = async () => {
    if (!text.trim()) {
      return;
    }

    setIsSending(true);
    await onSubmit(text.trim());
    setIsSending(false);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-emerald-400/15 flex items-center justify-center">
          <MessageSquareText className="w-5 h-5 text-emerald-200" />
        </div>
        <div>
          <div className="text-lg font-semibold text-slate-100">自然語言控制</div>
          <div className="text-xs text-slate-400">描述需求，系統轉換為設定覆寫</div>
        </div>
      </div>

      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={4}
        placeholder="例如：幫我加入 funding rate 的 RSI 與 EMA"
        className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-300/40"
      />

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isSending}
        className="w-full rounded-xl border border-emerald-300/30 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-100 hover:bg-emerald-400/20 transition disabled:opacity-50"
      >
        {isSending ? '解析中...' : '送出需求'}
      </button>

      {lastNLResult && (
        <div className="rounded-xl border border-emerald-300/20 bg-emerald-400/10 p-3 text-xs text-emerald-100">
          <div className="font-semibold">AI 回應</div>
          <div className="mt-1 text-emerald-100/80">{lastNLResult.description}</div>
        </div>
      )}
    </div>
  );
}
