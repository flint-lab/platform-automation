from playwright.sync_api import expect
from framework.locators.login_locators import LoginLocators
from framework.core.config import BASE_URL, EMAIL, PASSWORD
from framework.helpers.logger import get_logger

import re

logger = get_logger("TestLoginFlow")

def test_login_flow(page):
    logger.info(f"Navigating to BASE_URL: {BASE_URL}")
    page.goto(BASE_URL)
    
    page.wait_for_timeout(2000)
    
    logger.info("Clicking on landing page Login button.")
    page.locator(LoginLocators.LANDING_LOGIN_BUTTON).click()
    
    page.wait_for_timeout(2000)

    logger.info("Waiting for redirect to Auth0/Login page.")
    expect(page).to_have_url(re.compile(r"(auth0|login|flintlab)", re.IGNORECASE))
    
    logger.info(f"Attempting to fill email with {EMAIL}.")
    email_input = page.get_by_placeholder(LoginLocators.EMAIL_PLACEHOLDER)
    if email_input.count() == 0:
        email_input = page.locator(LoginLocators.EMAIL_INPUT)
    email_input.fill(EMAIL)
    logger.info("Email filled successfully.")
    page.wait_for_timeout(2000)

    logger.info("Attempting to fill password.")
    password_input = page.get_by_placeholder(LoginLocators.PASSWORD_PLACEHOLDER)
    if password_input.count() == 0:
        password_input = page.locator(LoginLocators.PASSWORD_INPUT)
    password_input.fill(PASSWORD)
    logger.info("Password filled successfully.")
    page.wait_for_timeout(2000)

    logger.info("Attempting to click submit button.")
    clicked = False
    for submit_text in LoginLocators.SUBMIT_BUTTON_TEXTS:
        submit_btn = page.get_by_text(submit_text, exact=True)
        if submit_btn.count() > 0:
            submit_btn.click()
            logger.info(f"Clicked submit button with text: '{submit_text}'")
            clicked = True
            break
            
    if not clicked:
        logger.info("No submit button found. Falling back to pressing Enter on password input.")
        password_input.press("Enter")
        
    page.wait_for_timeout(2000)

    logger.info("Validating final redirect to application dashboard.")
    expect(page).to_have_url(re.compile(r"flintlab", re.IGNORECASE), timeout=15000)
    logger.info("Login flow test completed successfully.")
    page.wait_for_timeout(4000)