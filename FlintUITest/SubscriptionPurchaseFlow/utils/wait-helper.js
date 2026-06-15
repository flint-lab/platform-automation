// utils/wait-helper.js
class WaitHelper {
  static async waitForElement(page, selector, timeout = 10000) {
    try {
      await page.waitForSelector(selector, { state: 'visible', timeout });
      return true;
    } catch (error) {
      console.log(`Element ${selector} not found after ${timeout}ms`);
      return false;
    }
  }
  
  static async waitForNavigation(page, urlPattern, timeout = 15000) {
    try {
      await page.waitForURL(urlPattern, { timeout });
      return true;
    } catch (error) {
      console.log(`Navigation to ${urlPattern} failed after ${timeout}ms`);
      return false;
    }
  }
  
  static async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = { WaitHelper };
