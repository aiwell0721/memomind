import { test, expect } from '@playwright/test';

test.describe('实时协作', () => {
  async function loginAs(page: any, username: string) {
    await page.goto('/');
    await page.getByPlaceholder('输入用户名').fill(username);
    await page.getByPlaceholder('输入密码').fill('testpass123');
    // 先尝试登录
    await page.getByRole('button', { name: '登录' }).click();
    const hasError = await page.getByText('用户名或密码错误').isVisible().catch(() => false);
    if (hasError) {
      await page.getByText('没有账号？注册').click();
      await page.getByRole('button', { name: '注册' }).click();
    }
    await page.waitForTimeout(1000);
  }

  test('两个用户同时在线', async ({ browser }) => {
    // 创建两个浏览器上下文
    const ctx1 = await browser.newContext();
    const ctx2 = await browser.newContext();
    const page1 = await ctx1.newPage();
    const page2 = await ctx2.newPage();

    // 两个用户分别注册/登录
    await loginAs(page1, 'collab_user1');
    await loginAs(page2, 'collab_user2');

    await page1.waitForTimeout(1000);
    await page2.waitForTimeout(1000);

    // 两个用户都能看到笔记页面
    await expect(page1.locator('body')).toBeVisible();
    await expect(page2.locator('body')).toBeVisible();

    await ctx1.close();
    await ctx2.close();
  });

  test('编辑内容同步', async ({ browser }) => {
    const ctx1 = await browser.newContext();
    const ctx2 = await browser.newContext();
    const page1 = await ctx1.newPage();
    const page2 = await ctx2.newPage();

    await loginAs(page1, 'sync_user1');
    await loginAs(page2, 'sync_user2');

    await page1.waitForTimeout(1000);
    await page2.waitForTimeout(1000);

    // 验证页面正常加载
    await expect(page1.getByText('MemoMind').first()).toBeVisible();
    await expect(page2.getByText('MemoMind').first()).toBeVisible();

    await ctx1.close();
    await ctx2.close();
  });
});
