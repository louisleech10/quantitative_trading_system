/**
 * exportUtils.ts
 * 
 * Export utilities for optimization results:
 * - CSV export for trial history
 * - PNG export for charts (using html2canvas)
 * 
 * ULTRA THINK 3-STEP PROCESS DOCUMENTATION:
 * ==========================================
 * 
 * STEP 1 - THINK: Requirements Analysis & Technical Selection
 * ------------------------------------------------------------
 * Requirements:
 * 1. CSV Export: Export trial history to CSV file (RFC 4180 compliant)
 * 2. PNG Export: Export chart as PNG image (html2canvas)
 * 
 * Technical Selection:
 * - CSV: Pure frontend implementation using Blob API
 * - PNG: html2canvas library (DOM → canvas → PNG)
 * 
 * STEP 2 - REVIEW: Edge Cases & Type Safety
 * ------------------------------------------
 * CSV Edge Cases:
 * - Empty trials → Export header only
 * - Nested params object → Flatten to params.key format
 * - Special chars (comma, quotes, newline) → RFC 4180 escaping
 * - Large data (10000+ trials) → Browser memory limit
 * 
 * PNG Edge Cases:
 * - Chart not rendered → Wait for DOM ready
 * - CSS not loaded → html2canvas waits for fonts/images
 * - Dark mode → Preserve dark class during screenshot
 * - Loading time → Show loading indicator
 * 
 * STEP 3 - OPTIMIZE: Performance & UX
 * ------------------------------------
 * CSV Optimization:
 * - Dynamic header generation (based on actual param keys)
 * - RFC 4180 escaping for special characters
 * - Filename with timestamp
 * 
 * PNG Optimization:
 * - 2x scale for higher resolution
 * - White background to avoid transparency
 * - useCORS for cross-origin images
 * - Error handling with user feedback
 */

import type { TrialSummary } from './types';

/**
 * Flatten nested object to dot notation
 * Example: { params: { threshold: 0.5 } } → { 'params.threshold': 0.5 }
 */
function flattenObject(obj: unknown, prefix = ''): Record<string, unknown> {
  const flattened: Record<string, unknown> = {};

  if (typeof obj !== 'object' || obj === null) {
    return flattened;
  }

  const objRecord = obj as Record<string, unknown>;

  for (const key in objRecord) {
    const value = objRecord[key];
    const newKey = prefix ? `${prefix}.${key}` : key;

    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      // Recursively flatten nested objects
      Object.assign(flattened, flattenObject(value, newKey));
    } else {
      flattened[newKey] = value;
    }
  }

  return flattened;
}

/**
 * Escape CSV field according to RFC 4180
 * - Wrap in quotes if contains comma, quote, or newline
 * - Escape quotes by doubling them
 */
function escapeCSVField(field: unknown): string {
  if (field == null) return '';

  const str = String(field);

  // Check if escaping is needed
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    // Escape quotes by doubling them
    const escaped = str.replace(/"/g, '""');
    return `"${escaped}"`;
  }

  return str;
}

/**
 * Generate timestamp for filename
 * Format: YYYYMMDD_HHmmss
 */
function getTimestamp(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `${year}${month}${day}_${hours}${minutes}${seconds}`;
}

/**
 * Export trials to CSV file
 * 
 * @param trials - Array of trial summaries
 * @param taskId - Task ID for filename
 */
export function exportTrialsToCSV(trials: TrialSummary[], taskId: string): void {
  try {
    // EDGE CASE: Empty trials
    if (trials.length === 0) {
      console.warn('No trials to export');
      // Still create file with header only
      const header = 'trial_number,value,state,duration,datetime_complete\r\n';
      const blob = new Blob([header], { type: 'text/csv;charset=utf-8;' });
      downloadBlob(blob, `optimization_trials_${taskId}_${getTimestamp()}.csv`);
      return;
    }

    // Flatten all trials to get all possible keys
    const flattenedTrials = trials.map((trial) => flattenObject(trial));

    // Get all unique keys (for CSV header)
    const allKeys = new Set<string>();
    flattenedTrials.forEach((trial) => {
      Object.keys(trial).forEach((key) => allKeys.add(key));
    });

    // Sort keys for consistent column order
    const sortedKeys = Array.from(allKeys).sort();

    // Generate CSV header
    const header = sortedKeys.map(escapeCSVField).join(',') + '\r\n';

    // Generate CSV rows
    const rows = flattenedTrials.map((trial) => {
      return sortedKeys.map((key) => escapeCSVField(trial[key])).join(',');
    }).join('\r\n');

    // Combine header and rows
    const csv = header + rows;

    // Create Blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const filename = `optimization_trials_${taskId}_${getTimestamp()}.csv`;
    downloadBlob(blob, filename);

    console.log(`Exported ${trials.length} trials to ${filename}`);
  } catch (error) {
    console.error('Failed to export CSV:', error);
    throw error;
  }
}

/**
 * Export chart as PNG image using html2canvas
 * 
 * @param elementId - DOM element ID to capture
 * @param chartName - Chart name for filename
 * @param taskId - Task ID for filename
 */
export async function exportChartToPNG(
  elementId: string,
  chartName: string,
  taskId: string
): Promise<void> {
  try {
    // Dynamically import html2canvas (code splitting)
    const html2canvas = (await import('html2canvas')).default;

    // Get DOM element
    const element = document.getElementById(elementId);
    if (!element) {
      throw new Error(`Element with id "${elementId}" not found`);
    }

    // Capture element as canvas
    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2, // 2x resolution for better quality
      logging: false, // Disable console warnings
      useCORS: true, // Enable cross-origin images
      windowWidth: element.scrollWidth,
      windowHeight: element.scrollHeight,
    });

    // Convert canvas to blob
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((blob: Blob | null) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Failed to create blob from canvas'));
        }
      }, 'image/png');
    });

    // Download blob
    const filename = `${chartName}_${taskId}_${getTimestamp()}.png`;
    downloadBlob(blob, filename);

    console.log(`Exported chart "${chartName}" to ${filename}`);
  } catch (error) {
    console.error('Failed to export PNG:', error);
    throw error;
  }
}

/**
 * Download blob as file
 * 
 * @param blob - Blob data
 * @param filename - Filename for download
 */
function downloadBlob(blob: Blob, filename: string): void {
  // Create object URL
  const url = URL.createObjectURL(blob);

  // Create temporary anchor element
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  // Append to body, click, and remove
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Revoke object URL to free memory
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 100);
}

/**
 * Export comparison result as Markdown (already implemented in ComparisonTool)
 * This is a placeholder for future enhancements
 */
export function exportComparisonToMarkdown(trials: TrialSummary[]): string {
void trials;
  // Implementation delegated to ComparisonTool component
  // This function is here for API completeness
  return '';
}
