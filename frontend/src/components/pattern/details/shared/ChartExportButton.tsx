"use client";

import React, { useState } from 'react';
import html2canvas from 'html2canvas';

interface ChartExportButtonProps {
  targetRef: React.RefObject<HTMLElement | null>;
  filename?: string;
  className?: string;
}

export default function ChartExportButton({ targetRef, filename = 'chart', className }: ChartExportButtonProps) {
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    if (!targetRef.current || exporting) return;
    setExporting(true);
    try {
      const canvas = await html2canvas(targetRef.current, {
        backgroundColor: '#0A0F1C',
        scale: 2,
        logging: false
      });
      const link = document.createElement('a');
      link.download = `${filename}_${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } finally {
      setExporting(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={exporting}
      className={className || 'px-3 py-1 bg-emerald-500 text-white text-sm rounded hover:bg-emerald-400 disabled:opacity-60'}
    >
      {exporting ? '匯出中...' : '匯出 PNG'}
    </button>
  );
}
