import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useAccordionContext } from './Accordion';

interface AccordionItemProps {
  id: string;
  title: React.ReactNode;
  children: React.ReactNode;
  badge?: React.ReactNode;
  disabled?: boolean;
  className?: string;
}

export function AccordionItem({
  id,
  title,
  children,
  badge,
  disabled = false,
  className = '',
}: AccordionItemProps) {
  const { expandedIds, toggleItem } = useAccordionContext('AccordionItem');
  const isExpanded = expandedIds.includes(id);
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState('0px');

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    const newHeight = isExpanded ? `${el.scrollHeight}px` : '0px';
    setHeight(newHeight);
  }, [isExpanded, children]);

  const handleToggle = () => {
    if (disabled) return;
    toggleItem(id);
  };

  return (
    <div className={`border border-white/10 rounded-xl bg-white/5 ${className}`}>
      <button
        type="button"
        className={`w-full flex items-center justify-between px-4 py-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-controls={`${id}-content`}
        disabled={disabled}
      >
        <div className="flex items-center gap-2">
          <span className="text-base font-medium text-slate-100">{title}</span>
          {badge && (
            <span className="inline-flex items-center rounded-full bg-blue-400/10 px-2 py-0.5 text-xs font-semibold text-blue-300">
              {badge}
            </span>
          )}
        </div>
        <ChevronDown
          className={`h-5 w-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>
      <div
        id={`${id}-content`}
        role="region"
        aria-hidden={!isExpanded}
        style={{ height }}
        className="overflow-hidden transition-[height] duration-250 ease-out"
      >
        <div ref={contentRef} className="px-4 pb-4 pt-1 text-sm text-slate-400">
          {children}
        </div>
      </div>
    </div>
  );
}