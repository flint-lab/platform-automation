// utils/login-helper.js
require('dotenv').config();

class LoginHelper {
  static async login(page, email = null, password = null) {
    const testEmail = email || process.env.TEST_EMAIL;
    const testPassword = password || process.env.TEST_PASSWORD;
    
    await page.goto(process.env.BASE_URL);
    await page.getByRole('button', { name: 'Log in to your account' }).click();
    await page.getByRole('textbox', { name: 'Email' }).fill(testEmail);
    await page.getByRole('textbox', { name: 'Password' }).fill(testPassword);
    await page.getByRole('button', { name: 'Log In' }).click();
    await page.waitForURL('**/platform.development.flintlab.io/**');
    
    console.log(`✓ Logged in as: ${testEmail}`);
  }
  
  static async logout(page) {
    await page.getByRole('button', { name: 'Profile' }).click();
    await page.getByRole('button', { name: 'Logout' }).click();
    console.log('✓ Logged out successfully');
  }
}

module.exports = { LoginHelper };
