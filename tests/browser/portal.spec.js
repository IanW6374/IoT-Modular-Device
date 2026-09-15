const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

const username = process.env.IOTMD_PORTAL_USERNAME;
const password = process.env.IOTMD_PORTAL_PASSWORD;

async function signIn(page) {
  await page.goto('/login');
  if (await page.locator('#login-form').count()) {
    test.skip(!username || !password, 'Set IOTMD_PORTAL_USERNAME and IOTMD_PORTAL_PASSWORD');
    await page.getByLabel('Username').fill(username);
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', { name: 'Sign in' }).click();
  }
  await expect(page.locator('main')).toBeVisible();
}

test('authenticated portal has no serious accessibility violations', async ({ page }) => {
  await signIn(page);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(v => ['critical', 'serious'].includes(v.impact))).toEqual([]);
});

test('primary menus support keyboard navigation and escape', async ({ page }) => {
  await signIn(page);
  const status = page.getByRole('button', { name: /Status/ }).first();
  await status.focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('menuitem', { name: 'Overview' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(status).toBeFocused();
});

test('responsive portal has no horizontal page overflow', async ({ page }) => {
  await signIn(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBeFalsy();
});

test('security policy and session cookie are hardened', async ({ page }) => {
  const response = await page.goto('/login');
  const csp = response.headers()['content-security-policy'] || '';
  expect(csp).toContain("default-src 'self'");
  expect(csp).toContain("object-src 'none'");
  if (username && password) {
    await signIn(page);
    const cookies = await page.context().cookies();
    const session = cookies.find(cookie => cookie.name === '__Host-iotmd_session');
    expect(session).toBeTruthy();
    expect(session.secure).toBeTruthy();
    expect(session.httpOnly).toBeTruthy();
    expect(session.sameSite).toBe('Strict');
  }
});

test('live pages resynchronise after tab visibility changes', async ({ page, context }) => {
  await signIn(page);
  const other = await context.newPage();
  await other.goto('about:blank');
  await other.bringToFront();
  await page.waitForTimeout(1200);
  await page.bringToFront();
  await expect(page.locator('#overview-refresh')).toContainText('Live');
  await other.close();
});
