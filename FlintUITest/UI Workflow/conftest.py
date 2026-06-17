import pytest
from framework.core.config import BASE_URL, HEADLESS

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": HEADLESS.lower() == "true",
        "args": ["--start-maximized"]
    }

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "no_viewport": True
    }

@pytest.fixture
def landing_page(page):
    page.goto(BASE_URL)
    return page