'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export interface CollapsibleSectionProps {
  /** localStorage key for expanded preference */
  storageKey: string;
  title: ReactNode;
  description?: ReactNode;
  leading?: ReactNode;
  /** Sibling control slot to the right of the toggle button (not nested inside it) */
  headerTrailing?: ReactNode;
  children: ReactNode;
  titleHeadingLevel?: 'h2' | 'h3';
  expandedClassName?: string;
  collapsedClassName?: string;
  contentClassName?: string;
  headerClassName?: string;
}

function readExpandedPreference(storageKey: string): boolean {
  if (typeof window === 'undefined') return true;
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored === 'false') return false;
    if (stored === 'true') return true;
  } catch {
    // ignore storage errors
  }
  return true;
}

export default function CollapsibleSection({
  storageKey,
  title,
  description,
  leading,
  headerTrailing,
  children,
  titleHeadingLevel = 'h2',
  expandedClassName = 'glass-panel rounded-2xl p-5 border border-white/10 space-y-4',
  collapsedClassName = 'glass-panel rounded-xl border border-white/10 px-4 py-3',
  contentClassName,
  headerClassName,
}: CollapsibleSectionProps) {
  // 初值固定 true 保持 SSR/CSR 一致(避免 Next hydration mismatch);持久化偏好於 mount 後載入。
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    setExpanded(readExpandedPreference(storageKey));
  }, [storageKey]);

  const toggleExpanded = () => {
    setExpanded((current) => {
      const next = !current;
      try {
        localStorage.setItem(storageKey, String(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  const TitleTag = titleHeadingLevel;

  return (
    <section className={expanded ? expandedClassName : collapsedClassName}>
      <div
        className={`flex w-full items-center gap-3${headerClassName ? ` ${headerClassName}` : ''}`}
      >
        <button
          type="button"
          onClick={toggleExpanded}
          className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
          aria-expanded={expanded}
        >
          <div className="flex min-w-0 flex-1 items-center gap-3">
            {leading}
            <div className="min-w-0">
              <TitleTag className="text-sm font-semibold text-slate-100">{title}</TitleTag>
              {description ? (
                <p className="mt-0.5 text-xs text-slate-400">{description}</p>
              ) : null}
            </div>
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
          ) : (
            <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
          )}
        </button>
        {headerTrailing ? (
          <div className="flex shrink-0 items-center">{headerTrailing}</div>
        ) : null}
      </div>

      {expanded ? (
        <div className={contentClassName}>{children}</div>
      ) : null}
    </section>
  );
}
