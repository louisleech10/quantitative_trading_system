/**
 * frontend/src/app/optimization-result/[taskId]/page.tsx
 * 
 * ULTRA THINK 3-STEP PROCESS DOCUMENTATION:
 * ==========================================
 * 
 * STEP 1 - THINK: Requirements Analysis & Page Architecture
 * -----------------------------------------------------------
 * Purpose: Main optimization result display page - integrate all 9 components
 * 
 * Route Pattern: /optimization-result/[taskId] (Next.js 15 App Router dynamic route)
 * Data Flow: URL param (taskId) → API calls → 9 components rendering
 * 
 * Required API Calls (6 endpoints from Task 3.5):
 * 1. fetchOptimizationResult(taskId) → OptimizationResult (best params, basic info)
 * 2. fetchSignalDensity(taskId) → SignalDensityResponse (separation, p-value, Cohen's d)
 * 3. fetchStabilityAnalysis(taskId) → StabilityAnalysisResponse (monthly data, CV)
 * 4. fetchImportanceAnalysis(taskId) → ImportanceAnalysisResponse (trials, param importance)
 * 5. fetchOptimizationHistory(taskId) → Trial[] (convergence history)
 * 6. fetchParameterSpace(taskId) → ParamSpaceResponse (Pareto front - deferred to Phase 4)
 * 
 * Component Integration Order (9 components):
 * Section 1: Overview & Metrics
 *   - MetricsPanel (SignalDensityResponse)
 *   - BestParamsCard (OptimizationResult.best_params)
 * 
 * Section 2: Statistical Analysis
 *   - DensityComparisonChart (SignalDensityResponse.positive_densities/negative_densities)
 *   - StabilityChart (StabilityAnalysisResponse)
 * 
 * Section 3: Optimization Process
 *   - OptimizationHistoryChart (ImportanceAnalysisResponse.optimization_history)
 *   - ParameterImportanceChart (ImportanceAnalysisResponse.parameter_importance)
 * 
 * Section 4: Trial Details & Comparison
 *   - TrialHistoryTable (ImportanceAnalysisResponse.optimization_history)
 *   - ComparisonTool (triggered by TrialHistoryTable selection)
 * 
 * Layout Design:
 * - Responsive grid: 1 column (mobile) → 2 columns (tablet) → full width (desktop)
 * - Sticky breadcrumb navigation
 * - Loading skeleton screens
 * - Error boundaries per section
 * 
 * Technical Selection:
 * - Next.js 15 App Router (use client for interactivity)
 * - React.Suspense for data loading
 * - Error boundary for API failures
 * - TanStack Query (optional, use native fetch for now)
 * 
 * STEP 2 - REVIEW: Edge Cases & Error Handling
 * ----------------------------------------------
 * Edge Cases:
 * 1. Invalid taskId (404 Not Found)
 * 2. Task still running (no results yet)
 * 3. Task failed (optimization error)
 * 4. Partial data (some APIs succeed, some fail)
 * 5. Empty trials (no completed trials)
 * 6. Network timeout/disconnection
 * 
 * Error Handling Strategy:
 * - Per-section error boundaries (don't crash entire page)
 * - Retry button for failed API calls
 * - Graceful degradation (show available data)
 * - Loading states (skeleton screens, not spinners)
 * - Toast notifications for async errors
 * 
 * Performance Considerations:
 * - Parallel API calls (Promise.all for independent data)
 * - Component lazy loading (React.lazy for heavy components)
 * - useMemo for expensive computations
 * - Virtualization for TrialHistoryTable (1000+ trials)
 * 
 * STEP 3 - OPTIMIZE: UX & Code Quality
 * --------------------------------------
 * UX Optimizations:
 * - Breadcrumb: Home → Optimization Tasks → Task #{taskId} Results
 * - Page title: "Optimization Result - Task #{taskId}"
 * - Section headers: Collapsible with expand/collapse all
 * - Scroll restoration: Remember scroll position on navigation
 * - Export all: Batch export all charts as ZIP
 * - Share link: Copy URL to clipboard
 * 
 * Code Quality:
 * - Type safety: All API responses typed
 * - Error messages: User-friendly, actionable
 * - Console logging: Only errors, no debug spam
 * - Accessibility: ARIA labels, keyboard navigation
 * - Documentation: JSDoc for complex logic
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  MetricsPanel,
  BestParamsCard,
  DensityComparisonChart,
  StabilityChart,
  OptimizationHistoryChart,
  ParameterImportanceChart,
  TrialHistoryTable,
  ComparisonTool,
} from '@/components/results';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import {
  fetchOptimizationResult,
  fetchStabilityAnalysis,
  fetchParameterImportance,
  fetchOptimizationHistory,
} from '@/lib/api';
import {
  showErrorToast,
  showSuccessToast,
  withErrorHandling,
} from '@/lib/errorHandler';
import type {
  OptimizationResult,
  SignalDensityResponse,
  StabilityAnalysis,
  ImportanceAnalysisResponse,
  OptimizationHistoryResponse,
  TrialSummary,
} from '@/lib/types';

/**
 * Loading state enum for better type safety
 */
type LoadingState = 'idle' | 'loading' | 'success' | 'error';

/**
 * Page data structure
 */
interface PageData {
  optimizationResult: OptimizationResult | null;
  stabilityAnalysis: StabilityAnalysis | null;
  parameterImportance: ImportanceAnalysisResponse | null;
  optimizationHistory: OptimizationHistoryResponse | null;
}

/**
 * Error information structure
 */
interface ErrorInfo {
  section: string;
  message: string;
  retryable: boolean;
}

/**
 * Optimization Result Page Component
 */
export default function OptimizationResultPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskId as string;

  // State management
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [data, setData] = useState<PageData>({
    optimizationResult: null,
    stabilityAnalysis: null,
    parameterImportance: null,
    optimizationHistory: null,
  });
  const [errors, setErrors] = useState<ErrorInfo[]>([]);
  const [selectedTrials, setSelectedTrials] = useState<TrialSummary[]>([]);
  const [showComparison, setShowComparison] = useState(false);

  /**
   * Fetch all required data in parallel
   */
  const fetchAllData = useCallback(async () => {
    setLoadingState('loading');
    setErrors([]);

    try {
      // Parallel API calls for independent data with error handling
      const [
        optimizationResult,
        stabilityAnalysis,
        parameterImportance,
        optimizationHistory,
      ] = await Promise.allSettled([
        withErrorHandling(
          () => fetchOptimizationResult(taskId),
          { 
            loadingMessage: 'Loading optimization results...',
            errorMessage: 'Failed to load optimization results',
            successMessage: undefined, // Don't show success toast
          }
        ),
        withErrorHandling(
          () => fetchStabilityAnalysis(taskId),
          { 
            loadingMessage: 'Loading stability analysis...',
            errorMessage: 'Failed to load stability analysis',
            successMessage: undefined,
          }
        ),
        withErrorHandling(
          () => fetchParameterImportance(taskId),
          { 
            loadingMessage: 'Loading parameter importance...',
            errorMessage: 'Failed to load parameter importance',
            successMessage: undefined,
          }
        ),
        withErrorHandling(
          () => fetchOptimizationHistory(taskId),
          { 
            loadingMessage: 'Loading optimization history...',
            errorMessage: 'Failed to load optimization history',
            successMessage: undefined,
          }
        ),
      ]);

      // Process results and collect errors
      const newErrors: ErrorInfo[] = [];
      const newData: PageData = {
        optimizationResult: null,
        stabilityAnalysis: null,
        parameterImportance: null,
        optimizationHistory: null,
      };

      if (optimizationResult.status === 'fulfilled') {
        newData.optimizationResult = optimizationResult.value;
      } else {
        newErrors.push({
          section: 'Optimization Result',
          message: optimizationResult.reason?.message || 'Failed to load optimization result',
          retryable: true,
        });
      }

      if (stabilityAnalysis.status === 'fulfilled') {
        newData.stabilityAnalysis = stabilityAnalysis.value;
      } else {
        newErrors.push({
          section: 'Stability Analysis',
          message: stabilityAnalysis.reason?.message || 'Failed to load stability analysis',
          retryable: true,
        });
      }

      if (parameterImportance.status === 'fulfilled') {
        newData.parameterImportance = parameterImportance.value;
      } else {
        newErrors.push({
          section: 'Parameter Importance',
          message: parameterImportance.reason?.message || 'Failed to load parameter importance',
          retryable: true,
        });
      }

      if (optimizationHistory.status === 'fulfilled') {
        newData.optimizationHistory = optimizationHistory.value;
      } else {
        newErrors.push({
          section: 'Optimization History',
          message: optimizationHistory.reason?.message || 'Failed to load optimization history',
          retryable: true,
        });
      }

      setData(newData);
      setErrors(newErrors);
      
      // Show appropriate toast based on results
      if (newErrors.length === 4) {
        setLoadingState('error');
        showErrorToast('Failed to load all data');
      } else if (newErrors.length > 0) {
        setLoadingState('success');
        showErrorToast(`${newErrors.length} of 4 data sources failed to load`);
      } else {
        setLoadingState('success');
        showSuccessToast('All data loaded successfully');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      showErrorToast(errorMessage);
      setErrors([
        {
          section: 'Page',
          message: errorMessage,
          retryable: true,
        },
      ]);
      setLoadingState('error');
    }
  }, [taskId]);

  /**
   * Initial data fetch on mount
   */
  useEffect(() => {
    if (taskId) {
      fetchAllData();
    }
  }, [taskId, fetchAllData]);

  /**
   * Handle trial selection from TrialHistoryTable
   */
  const handleTrialSelection = useCallback((trials: TrialSummary[]) => {
    setSelectedTrials(trials);
    setShowComparison(trials.length >= 2);
  }, []);

  /**
   * Retry failed API calls
   */
  const handleRetry = useCallback(() => {
    fetchAllData();
  }, [fetchAllData]);

  /**
   * Loading skeleton screen
   */
  if (loadingState === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        {/* Breadcrumb Skeleton */}
        <div className="mb-6 h-6 bg-gray-200 dark:bg-gray-700 rounded w-64 animate-pulse" />

        {/* Page Title Skeleton */}
        <div className="mb-8 h-10 bg-gray-200 dark:bg-gray-700 rounded w-96 animate-pulse" />

        {/* Content Skeleton */}
        <div className="space-y-6">
          <div className="h-64 bg-white dark:bg-gray-800 rounded-lg shadow animate-pulse" />
          <div className="h-96 bg-white dark:bg-gray-800 rounded-lg shadow animate-pulse" />
          <div className="h-80 bg-white dark:bg-gray-800 rounded-lg shadow animate-pulse" />
        </div>
      </div>
    );
  }

  /**
   * Error screen with retry option
   */
  if (loadingState === 'error' && errors.length === 4) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6 flex items-center justify-center">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-red-500 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Failed to Load Data
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Unable to load optimization result for Task #{taskId}. Please check your connection and try again.
          </p>
          <div className="space-y-3">
            <button
              onClick={handleRetry}
              className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Retry
            </button>
            <Link
              href="/"
              className="block w-full px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Main content rendering
   */
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      {/* Breadcrumb Navigation */}
      <nav className="mb-6 text-sm text-gray-600 dark:text-gray-400">
        <Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400">
          Home
        </Link>
        <span className="mx-2">/</span>
        <Link href="/optimization-tasks" className="hover:text-blue-600 dark:hover:text-blue-400">
          Optimization Tasks
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 dark:text-gray-100 font-medium">
          Task #{taskId} Results
        </span>
      </nav>

      {/* Page Title */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Optimization Result - Task #{taskId}
        </h1>
        {data.optimizationResult && (
          <p className="text-gray-600 dark:text-gray-400">
            Best Separation: <span className="font-semibold text-green-600">{data.optimizationResult.best_value.toFixed(4)}</span>
            {' • '}
            Total Trials: <span className="font-semibold">{data.optimizationResult.total_trials}</span>
          </p>
        )}
      </div>

      {/* Partial Error Warnings */}
      {errors.length > 0 && errors.length < 4 && (
        <div className="mb-6 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-200 mb-1">
                Some sections failed to load
              </h3>
              <ul className="text-sm text-yellow-700 dark:text-yellow-300 list-disc list-inside space-y-1">
                {errors.map((error, index) => (
                  <li key={index}>
                    <strong>{error.section}:</strong> {error.message}
                  </li>
                ))}
              </ul>
              <button
                onClick={handleRetry}
                className="mt-3 text-sm text-yellow-800 dark:text-yellow-200 underline hover:no-underline"
              >
                Retry Failed Sections
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Section 1: Overview & Metrics */}
      <ErrorBoundary>
        <section className="mb-8 space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 border-b-2 border-gray-200 dark:border-gray-700 pb-2">
            Overview & Core Metrics
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Metrics Panel */}
            {data.optimizationResult?.density_analysis ? (
              <MetricsPanel data={data.optimizationResult.density_analysis} className="lg:col-span-2" />
            ) : (
              <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
                Signal density data unavailable
              </div>
            )}

            {/* Best Parameters Card */}
            {data.optimizationResult ? (
              <BestParamsCard
                params={data.optimizationResult.best_params}
                trialNumber={data.optimizationResult.best_trial_number}
                totalTrials={data.optimizationResult.total_trials}
                bestValue={data.optimizationResult.best_value}
                className="lg:col-span-2"
              />
            ) : (
              <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
                Best parameters unavailable
              </div>
            )}
          </div>
        </section>
      </ErrorBoundary>

      {/* Section 2: Statistical Analysis */}
      <ErrorBoundary>
        <section className="mb-8 space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 border-b-2 border-gray-200 dark:border-gray-700 pb-2">
            Statistical Analysis
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Density Comparison Chart - TODO: Extract densities from case_level_densities */}
            {data.optimizationResult?.density_analysis ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <p className="text-gray-600 dark:text-gray-400">
                  Density Comparison Chart (Coming Soon)
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Positive Avg: {(data.optimizationResult.density_analysis.positive_avg_density * 100).toFixed(2)}%
                  <br />
                  Negative Avg: {(data.optimizationResult.density_analysis.negative_avg_density * 100).toFixed(2)}%
                  <br />
                  Separation: {data.optimizationResult.density_analysis.separation.toFixed(4)}
                </p>
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
                Density comparison unavailable
              </div>
            )}

            {/* Stability Chart */}
            {data.stabilityAnalysis ? (
              <StabilityChart
                data={data.stabilityAnalysis}
                taskId={taskId}
              />
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
                Stability analysis unavailable
              </div>
            )}
          </div>
        </section>
      </ErrorBoundary>

      {/* Section 3: Optimization Process */}
      <ErrorBoundary>
        <section className="mb-8 space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 border-b-2 border-gray-200 dark:border-gray-700 pb-2">
            Optimization Process
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Optimization History Chart */}
            {data.optimizationResult?.trials_summary && data.optimizationResult.trials_summary.length > 0 ? (
              <OptimizationHistoryChart
                data={data.optimizationResult.trials_summary}
                taskId={taskId}
              />
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
                Optimization history unavailable
              </div>
            )}

            {/* Parameter Importance Chart */}
            {data.parameterImportance?.importances && data.parameterImportance.importances.length > 0 ? (
              <ParameterImportanceChart
                data={data.parameterImportance.importances}
                taskId={taskId}
              />
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
                Parameter importance unavailable
              </div>
            )}
          </div>
        </section>
      </ErrorBoundary>

      {/* Section 4: Trial Details & Comparison */}
      <ErrorBoundary>
        <section className="mb-8 space-y-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 border-b-2 border-gray-200 dark:border-gray-700 pb-2">
            Trial Details & Comparison
          </h2>

          {/* Trial History Table */}
          {data.optimizationResult?.trials_summary && data.optimizationResult.trials_summary.length > 0 ? (
            <TrialHistoryTable
              trials={data.optimizationResult.trials_summary}
              taskId={taskId}
              onSelectTrials={handleTrialSelection}
            />
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 text-center text-gray-500">
              Trial history unavailable
            </div>
          )}

          {/* Comparison Tool (conditionally rendered) */}
          {showComparison && selectedTrials.length >= 2 && (
            <ComparisonTool
              trials={selectedTrials}
              onClose={() => setShowComparison(false)}
            />
          )}
        </section>
      </ErrorBoundary>

      {/* Back to Top Button */}
      <div className="fixed bottom-8 right-8">
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg transition-colors"
          aria-label="Back to top"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      </div>
    </div>
  );
}
