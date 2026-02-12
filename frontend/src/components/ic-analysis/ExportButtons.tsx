'use client';

import html2canvas from 'html2canvas';
import { ICFeatureInfo, ICReport } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

interface ExportButtonsProps {
  report?: ICReport | null;
  summaryTable?: ICFeatureInfo[];
  targetId?: string;
}

export default function ExportButtons({ report, summaryTable, targetId }: ExportButtonsProps) {
  const handleExportJSON = () => {
    if (!report) {
      return;
    }

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ic_report_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (!summaryTable || summaryTable.length === 0) {
      return;
    }

    const headers = ['rank', 'feature_name', 'ic_mean', 'icir', 'p_value', 'monotonicity_score'];
    const rows = summaryTable.map((item) => [
      item.rank ?? '',
      item.feature_name,
      item.ic_mean ?? '',
      item.icir ?? '',
      item.p_value ?? '',
      item.monotonicity_score ?? '',
    ]);

    const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ic_summary_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPNG = async () => {
    if (!targetId) {
      return;
    }
    const target = document.getElementById(targetId);
    if (!target) {
      return;
    }

    const canvas = await html2canvas(target, {
      backgroundColor: '#0A0F1C',
      scale: 2,
      useCORS: true,
    });

    const link = document.createElement('a');
    link.href = canvas.toDataURL('image/png');
    link.download = `ic_snapshot_${Date.now()}.png`;
    link.click();
  };

  return (
    <div className="flex flex-wrap gap-3">
      <Button
        variant="outline"
        className="border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10"
        onClick={handleExportJSON}
        disabled={!report}
      >
        <Download className="mr-2 h-4 w-4" />
        匯出 JSON
      </Button>
      <Button
        variant="outline"
        className="border-blue-400/30 text-blue-200 hover:bg-blue-500/10"
        onClick={handleExportCSV}
        disabled={!summaryTable || summaryTable.length === 0}
      >
        <Download className="mr-2 h-4 w-4" />
        匯出 CSV
      </Button>
      <Button
        variant="outline"
        className="border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10"
        onClick={handleExportPNG}
        disabled={!targetId}
      >
        <Download className="mr-2 h-4 w-4" />
        匯出 PNG
      </Button>
    </div>
  );
}
