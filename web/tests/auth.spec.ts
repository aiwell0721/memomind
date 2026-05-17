import { test, expect } from '@playwright/test';

test.describe('登录/注册', () => {
  test('登录页面正常加载', async ({ page }) => {
    await page.goto('/');
    // 页面应该包含 MemoMind 标题
    await expect(page.getByText('MemoMind')).toBeVisible();
  });

  test('登录失败显示错误', async ({ page }) => {
    await page.goto('/');
    await page.getByPlaceholder('输入用户名').fill('nonexistent');
    await page.getByPlaceholder('输入密码').fill('wrong');
    await page.getByRole('button', { name: '登录' }).click();
    // 应该显示错误提示
    await expect(page.getByText(/用户不存在|用户名或密码错误/)).toBeVisible();
  });

  test('注册成功后自动登录', async ({ page }) => {
    await page.goto('/');
    // 切换到注册模式
    await page.getByText('没有账号？注册').click();
    await page.getByPlaceholder('输入用户名').fill(`testuser_${Date.now()}`);
    await page.getByPlaceholder('输入密码').fill('testpass123');
    await page.getByRole('button', { name: '注册' }).click();
    // 注册成功后跳转到首页
    await expect(page.locator('h1')).toHaveText(/MemoMind/, { timeout: 5000 });
  });
});
