import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

interface AccordionContextValue {
  expandedIds: string[];
  toggleItem: (id: string) => void;
  allowMultiple: boolean;
}

const AccordionContext = createContext<AccordionContextValue | null>(null);

export function useAccordionContext(componentName: string) {
  const context = useContext(AccordionContext);
  if (!context) {
    throw new Error(`${componentName} 必須包在 <Accordion> 中使用`);
  }
  return context;
}

interface AccordionProps {
  children: React.ReactNode;
  defaultExpanded?: string[];
  allowMultiple?: boolean;
  className?: string;
  onChange?: (expandedIds: string[]) => void;
}

export function Accordion({
  children,
  defaultExpanded = [],
  allowMultiple = true,
  className = '',
  onChange,
}: AccordionProps) {
  const [expandedIds, setExpandedIds] = useState<string[]>(defaultExpanded);

  const toggleItem = useCallback((id: string) => {
    setExpandedIds(prev => {
      const isExpanded = prev.includes(id);
      let next: string[];

      if (allowMultiple) {
        next = isExpanded ? prev.filter(item => item !== id) : [...prev, id];
      } else {
        next = isExpanded ? [] : [id];
      }

      onChange?.(next);
      return next;
    });
  }, [allowMultiple, onChange]);

  const contextValue = useMemo<AccordionContextValue>(
    () => ({ expandedIds, toggleItem, allowMultiple }),
    [expandedIds, toggleItem, allowMultiple],
  );

  return (
    <AccordionContext.Provider value={contextValue}>
      <div className={`space-y-3 ${className}`}>
        {children}
      </div>
    </AccordionContext.Provider>
  );
}