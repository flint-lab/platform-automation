// playwright.config.js
const { defineConfig, devices } = require('@playwright/test');
require('dotenv').config();

module.exports = defineConfig({
  testDir: './tests',
  timeout: parseInt(process.env.OPERATION_TIMEOUT) || 60000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : (parseInt(process.env.RETRIES) || 0),
  workers: process.env.CI ? 1 : (parseInt(process.env.PARALLEL_WORKERS) || 1),
  
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }],
    ['line'],
    ['allure-playwright']
  ],
  
  use: {
    baseURL: process.env.BASE_URL || 'https://development.flintlab.io',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: parseInt(process.env.NAVIGATION_TIMEOUT) || 30000,
    headless: process.env.HEADLESS === 'true' ? true : false,
    launchOptions: {
      slowMo: parseInt(process.env.SLOW_MO) || 0,
    },
  },

  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
        launchOptions: {
          args: ['--disable-dev-shm-usage'],
        },
      },
    },
    {
      name: 'firefox',
      use: { 
        ...devices['Desktop Firefox'],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'webkit',
      use: { 
        ...devices['Desktop Safari'],
        viewport: { width: 1280, height: 720 },
      },
    },
  ],
});
