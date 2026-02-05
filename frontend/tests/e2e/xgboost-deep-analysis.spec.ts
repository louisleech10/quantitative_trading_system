import { test, expect } from '@playwright/test';

const TASK_ID = '1247e4f6-5c67-4778-94ab-4873928da653';

test('XGBoost 深度分析頁面 E2E', async ({ page }) => {
  await page.goto(`/patterns/xgboost-analysis/${TASK_ID}/details`, { waitUntil: 'domcontentloaded' });

  await expect(page.getByText('XGBoost 深度分析儀表板')).toBeVisible({ timeout: 60000 });

  await expect(page.getByRole('tab', { name: '模型驗證' })).toBeVisible();
  await expect(page.getByRole('tab', { name: '特徵分析' })).toBeVisible();
  await expect(page.getByRole('tab', { name: '時序監控' })).toBeVisible();
  await expect(page.getByRole('tab', { name: '錯誤診斷' })).toBeVisible();

  await page.getByRole('tab', { name: '模型驗證' }).click();
  await expect(page.getByText('校準曲線')).toBeVisible({ timeout: 60000 });
  await expect(page.getByText('PR 曲線')).toBeVisible();
  await expect(page.getByText('機率分佈密度')).toBeVisible();

  await page.getByRole('tab', { name: '特徵分析' }).click();
  await expect(page.getByText('特徵重要性對比 (Gain/Cover/Weight)')).toBeVisible({ timeout: 60000 });
  await expect(page.getByText('特徵飄移分析 (PSI)')).toBeVisible();

  await page.getByRole('tab', { name: '時序監控' }).click();
  await expect(page.getByText('滾動 AUC 監控')).toBeVisible({ timeout: 60000 });
  await expect(page.getByText('策略權益曲線')).toBeVisible();
  await expect(page.getByText('市場體制表現')).toBeVisible();

  await page.getByRole('tab', { name: '錯誤診斷' }).click();
  await expect(page.getByText('Top False Positives')).toBeVisible({ timeout: 60000 });
  await expect(page.getByText('案例 SHAP 分析')).toBeVisible();
});
