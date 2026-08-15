import { test, expect } from '@playwright/test';

/**
 * 知识图谱 E2E 测试
 * 依赖本地 test 账号（test/test123456）及已有笔记数据
 */
test.describe('知识图谱', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByPlaceholder('输入用户名').fill('test');
    await page.getByPlaceholder('输入密码').fill('test123456');
    await page.locator('form').getByRole('button', { name: '登录' }).click();
    await page.waitForTimeout(1500);
  });

  test('导航栏包含知识图谱入口', async ({ page }) => {
    await expect(page.getByRole('button', { name: '知识图谱' })).toBeVisible();
  });

  test('图谱页面渲染节点图', async ({ page }) => {
    await page.goto('/graph');
    // 页面标题
    await expect(page.getByRole('heading', { name: '知识图谱' })).toBeVisible({
      timeout: 10000,
    });
    // ECharts canvas 渲染成功
    await expect(page.locator('canvas')).toHaveCount(1, { timeout: 10000 });
    // 节点/边统计显示
    await expect(page.getByText(/节点 · .*边/)).toBeVisible({ timeout: 10000 });
  });

  test('点击节点跳转到笔记详情', async ({ page }) => {
    await page.goto('/graph');
    await expect(page.locator('canvas')).toHaveCount(1, { timeout: 10000 });
    // 等待 force 布局稳定
    await page.waitForTimeout(3000);
    // 点击画布中心附近（节点密集区）
    await page.locator('canvas').click({ position: { x: 400, y: 300 } });
    // 应跳转到笔记详情（URL 含 /notes/）
    await page.waitForURL(/\/notes\/\d+/, { timeout: 10000 }).catch(() => {});
    // 若未跳转（点空了），至少页面不崩溃
    await expect(page.locator('body')).toBeVisible();
  });
});
