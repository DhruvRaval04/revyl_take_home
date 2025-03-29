import { test, expect } from '@playwright/test';

test.describe('ZeroStep Automation Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the target website before each test
    await page.goto('https://example.com'); // Replace with your target URL
  });

  test('should perform basic automation', async ({ page }) => {
    // Your test steps here
    await expect(page).toHaveTitle(/Example Domain/); // Replace with your expected title
  });
}); 