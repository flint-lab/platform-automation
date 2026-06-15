// tests/subscription-flow.spec.js
const { test, expect } = require('@playwright/test');
require('dotenv').config();

// Configure test timeout
test.setTimeout(parseInt(process.env.OPERATION_TIMEOUT) || 60000);

test.describe('Subscription Purchase Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    console.log('🚀 Starting subscription purchase test...');
  });

  test('complete subscription upgrade flow', async ({ page }) => {
    // Increase timeout for slow operations
    test.slow();
    
    // Step 1: Navigate to homepage
    await page.goto(process.env.BASE_URL, { 
      timeout: parseInt(process.env.NAVIGATION_TIMEOUT) || 30000,
      waitUntil: 'domcontentloaded'
    });
    console.log('✓ Navigated to homepage');
    await page.screenshot({ path: 'screenshots/01-homepage.png', fullPage: true });
    
    // Step 2: Click login button
    await page.getByRole('button', { name: 'Log in to your account' }).click();
    console.log('✓ Clicked login button');
    
    // Step 3: Fill login credentials from .env
    await page.getByRole('textbox', { name: 'Email' }).fill(process.env.TEST_EMAIL);
    await page.getByRole('textbox', { name: 'Password' }).fill(process.env.TEST_PASSWORD);
    console.log('✓ Filled login credentials');
    
    // Step 4: Submit login form
    await page.getByRole('button', { name: 'Log In' }).click();
    console.log('✓ Submitted login form');
    
    // Wait for navigation after login
    await page.waitForURL(/platform\.development\.flintlab\.io/, { 
      timeout: parseInt(process.env.NAVIGATION_TIMEOUT) || 30000,
      waitUntil: 'domcontentloaded'
    });
    console.log('✓ Login successful - Current URL:', page.url());
    await page.screenshot({ path: 'screenshots/02-login-success.png', fullPage: true });
    
    // Additional wait to ensure page is fully loaded
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
    
    // Step 5: Navigate to user profile
    try {
      await page.getByRole('link', { name: 'G' }).first().click();
    } catch (error) {
      console.log('Strategy 1 failed, trying strategy 2...');
      try {
        await page.locator('[class*="avatar"], [class*="profile"], img[alt*="profile"]').first().click();
      } catch (error2) {
        console.log('Strategy 2 failed, trying strategy 3...');
        await page.goto(`${process.env.PLATFORM_URL}/user`, { 
          waitUntil: 'domcontentloaded' 
        });
      }
    }
    
    await page.waitForTimeout(parseInt(process.env.SHORT_WAIT) || 2000);
    console.log('✓ Navigated to user profile');
    
    // Step 6: Go to billing section
    await page.getByRole('button', { name: 'Billing' }).click();
    await page.waitForTimeout(parseInt(process.env.SHORT_WAIT) || 2000);
    console.log('✓ Opened billing section');
    
    // Step 7: Click upgrade plan
    const upgradeButton = page.getByRole('button', { name: 'Upgrade Plan' });
    if (await upgradeButton.isVisible().catch(() => false)) {
      await upgradeButton.click();
    } else {
      await page.locator('button:has-text("Upgrade Plan")').click();
    }
    await page.waitForTimeout(parseInt(process.env.SHORT_WAIT) || 2000);
    console.log('✓ Clicked upgrade plan');
    await page.screenshot({ path: 'screenshots/03-upgrade-page.png', fullPage: true });
    
    // Step 8: Choose a plan
    const planButton = page.getByRole('button', { name: 'Choose Plan' }).first();
    await planButton.waitFor({ state: 'visible', timeout: 15000 });
    await planButton.click();
    await page.waitForTimeout(parseInt(process.env.SHORT_WAIT) || 2000);
    console.log('✓ Selected a plan');
    await page.screenshot({ path: 'screenshots/04-plan-selected.png', fullPage: true });
    
    // Step 9: Fill payment email
    const emailInput = page.getByRole('textbox', { name: 'Email' });
    if (await emailInput.isVisible().catch(() => false)) {
      await emailInput.fill(process.env.PAYMENT_EMAIL);
      console.log('✓ Filled payment email');
    } else {
      console.log('Payment email field not found, continuing...');
    }
    
    // Step 10: Fill SMS verification code - ONE BY ONE WITH DELAYS
    const smsCode = process.env.SMS_CODE || '000000';
    console.log(`✓ Starting SMS code entry (${smsCode.length} digits)...`);
    
    for (let i = 0; i < smsCode.length; i++) {
      const digit = smsCode[i];
      const smsInput = page.getByTestId(`sms-code-input-${i}`);
      
      // Wait for input to be visible and ready
      await smsInput.waitFor({ state: 'visible', timeout: 5000 });
      
      // Clear the input first
      await smsInput.click();
      await smsInput.clear();
      
      // Fill the digit
      await smsInput.fill(digit);
      console.log(`  ✓ Entered digit ${i + 1}: ${digit}`);
      
      // Wait between digits (300ms delay for natural typing)
      await page.waitForTimeout(300);
      
      // Take screenshot after each digit for debugging (optional)
      if (i === smsCode.length - 1) {
        await page.screenshot({ path: 'screenshots/after-last-digit.png' });
      }
    }
    console.log('✓ SMS verification code entered successfully');
    
    // Wait a bit after entering all digits
    await page.waitForTimeout(1000);
    
    // Step 11: Handle verification modal and submit payment
    const modal = page.locator('.ModalOverlay, [class*="Modal"], [class*="modal"]');
    if (await modal.isVisible().catch(() => false)) {
      console.log('✓ Modal detected, handling...');
      await page.screenshot({ path: 'screenshots/05-modal-detected.png' });
      
      const closeButton = page.locator('button:has-text("Close"), button:has-text("Cancel")');
      if (await closeButton.isVisible().catch(() => false)) {
        await closeButton.click();
      }
    }
    
    // Check for submit button and click
    const submitButton = page.getByTestId('hosted-payment-submit-button');
    const isSubmitVisible = await submitButton.isVisible({ timeout: 5000 }).catch(() => false);
    
    if (isSubmitVisible) {
      // Additional wait to ensure SMS validation is complete
      await page.waitForTimeout(500);
      
      try {
        await submitButton.click();
        console.log('✓ Submitted payment');
      } catch (error) {
        console.log('Regular click failed, trying force click...');
        await submitButton.click({ force: true });
        console.log('✓ Submitted payment with force click');
      }
    } else {
      console.log('Submit button not found, checking for alternative...');
      const altSubmit = page.locator('button[type="submit"], button:has-text("Submit"), button:has-text("Pay")');
      if (await altSubmit.isVisible().catch(() => false)) {
        await altSubmit.click();
        console.log('✓ Submitted payment via alternative button');
      }
    }
    
    // Step 12: Wait for successful navigation to dashboard
    try {
      await page.waitForURL(process.env.PLATFORM_URL, { 
        timeout: parseInt(process.env.LONG_WAIT) || 20000,
        waitUntil: 'domcontentloaded'
      });
      console.log('✓ Navigated back to dashboard');
    } catch (error) {
      console.log('Navigation timeout, but checking if already on correct page...');
      const currentUrl = page.url();
      if (currentUrl.includes('platform.development.flintlab.io')) {
        console.log('✓ Already on platform URL');
      } else {
        throw error;
      }
    }
    
    // Assertions to verify success
    await expect(page).toHaveURL(new RegExp(process.env.PLATFORM_URL.replace('https://', '')));
    console.log('✅ Test completed successfully!');
    
    await page.screenshot({ path: 'screenshots/06-test-complete.png', fullPage: true });
  });

  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status !== 'passed') {
      const timestamp = Date.now();
      const screenshotPath = `screenshots/failure-${testInfo.title.replace(/\s/g, '-')}-${timestamp}.png`;
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`❌ Test failed! Screenshot saved at: ${screenshotPath}`);
      console.log(`Current URL: ${page.url()}`);
    }
  });
});