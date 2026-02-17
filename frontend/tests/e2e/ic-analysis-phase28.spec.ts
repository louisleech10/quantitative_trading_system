import { expect, test } from '@playwright/test';

const MOCK_TASK_ID = 'phase28-e2e-task';

test('Phase 2.8 - IC 分析頁面深度分析流程 E2E', async ({ page }) => {
  await page.route('**/api/v1/ic/features/list**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total: 3,
        features: [
          { feature_name: 'feature_a', category: 'momentum', data_source: 'close', family: 'ema', layer: 1 },
          { feature_name: 'feature_b', category: 'volatility', data_source: 'volume', family: 'atr', layer: 1 },
          { feature_name: 'feature_c', category: 'momentum', data_source: 'close', family: 'rsi', layer: 2 },
        ],
      }),
    });
  });

  await page.route('**/api/v1/ic/analyze', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ task_id: MOCK_TASK_ID, status: 'running' }),
    });
  });

  await page.route(`**/api/v1/ic/deep-analysis/${MOCK_TASK_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ task_id: MOCK_TASK_ID, status: 'running' }),
    });
  });

  await page.route(`**/api/v1/ic/deep-analysis/${MOCK_TASK_ID}/result`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: MOCK_TASK_ID,
        status: 'completed',
        progress: 1,
        current_step: 'completed',
        summary: {
          total_modules: 10,
          completed_count: 8,
          skipped_count: 2,
          failed_count: 0,
          total_execution_time_s: 1.25,
        },
        module_status: [
          { module_name: 'factor_return', status: 'completed' },
          { module_name: 'factor_orthogonalization', status: 'skipped' },
        ],
        results: {
          deep_analysis_errors: [
            {
              module_name: 'factor_orthogonalization',
              reason: '因子數 < 3',
              error_type: 'INSUFFICIENT_DATA',
            },
          ],
          factor_returns: {
            feature_a: {
              quantile_returns_summary: { Q1: -0.03, Q2: 0.01, Q3: 0.03 },
            },
          },
          factor_centrality: {
            pca_summary: {
              explained_variance_ratio: [0.58, 0.24],
              crowded_threshold: 0.3,
            },
            features: {
              feature_a: { centrality: 0.41 },
            },
          },
          trend_analysis: {
            feature_a: {
              combined_signal: {
                recommendation: '警告',
                reason: 'IC 下降 + half_life 偏短',
                action: '提高監控頻率',
              },
            },
          },
          parameter_sensitivity: {
            families: {
              ema_close: {
                sensitivity_table: [
                  { variant: 'ema_close_10', param_value: 10, ic_mean: 0.06, icir: 1.2 },
                ],
                stability_metrics: { overfitting_risk: 'low' },
              },
            },
          },
          rolling_oos: {
            features: {
              feature_a: {
                oos_stability: { mean_oos_ic: 0.05, std_oos_ic: 0.02 },
              },
            },
          },
          long_short_analysis: {
            feature_a: {
              long_analysis: { mean_return: 0.04 },
              short_analysis: { mean_return: 0.02 },
            },
          },
          factor_exposure: {
            portfolio_exposure: { momentum: 0.32, value: 0.21 },
          },
          feature_quality_diagnostics: {
            summary: { stationary_rate: 0.82, mean_coverage: 0.93, low_quality_count: 1 },
            quality_flags: {
              non_stationary: ['feature_b'],
              high_autocorrelation: [],
              low_coverage: [],
              drifted: [],
            },
          },
          net_ic_analysis: {
            features: {
              feature_a: {
                gross_ic: 0.09,
                net_ic: 0.07,
                turnover: 0.32,
                cost_sensitivity: [{ cost_bps: 5, net_ic: 0.07 }],
              },
            },
          },
        },
      }),
    });
  });

  await page.goto('/ic-analysis', { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('IC 分析儀表板')).toBeVisible();
  await expect(page.getByRole('tab', { name: '基礎分析' })).toBeVisible();
  await expect(page.getByRole('tab', { name: '深度分析' })).toHaveCount(0);

  await page.getByPlaceholder('data_cache/features/{symbol}_{tf}_factory.h5').fill('data_cache/features/mock.h5');
  await page.getByRole('button', { name: '啟動 IC 分析' }).click();

  await page.getByRole('button', { name: 'Feature 預過濾' }).click();
  await page.getByRole('button', { name: '套用預過濾' }).click();

  await expect(page.getByRole('button', { name: /分析 \d+ 個因子 × \d+ 個模組/ })).toBeEnabled();
  await page.getByRole('button', { name: /分析 \d+ 個因子 × \d+ 個模組/ }).click();

  await expect(page.getByRole('tab', { name: '深度分析' })).toBeVisible();
  await page.getByRole('tab', { name: '深度分析' }).click();

  await expect(page.getByText('深度分析部分完成')).toBeVisible();
  await expect(page.getByText('C13 Factor Return')).toBeVisible();
  await expect(page.getByText('C14 Factor Centrality')).toBeVisible();
  await expect(page.getByText('C15 PCA Explained Variance')).toBeVisible();
  await expect(page.getByText('C16 Trend Dashboard')).toBeVisible();
  await expect(page.getByText('C17 Parameter Sensitivity')).toBeVisible();
  await expect(page.getByText('C18 OOS Distribution')).toBeVisible();
  await expect(page.getByText('C19 Long/Short Comparison')).toBeVisible();
  await expect(page.getByText('C20 Factor Exposure Radar')).toBeVisible();
  await expect(page.getByText('C21 Feature Quality Dashboard')).toBeVisible();
  await expect(page.getByText('C22 Net IC Chart')).toBeVisible();
});
