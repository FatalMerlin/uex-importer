import os
import urllib.parse
from enum import StrEnum
from textwrap import dedent

from patchright.sync_api import sync_playwright, Playwright, BrowserContext, Locator
from structlog.stdlib import get_logger

from models.update import Update, UpdateStatus
from utils.cache import screenshot_path

BROWSER_USER_DATA_PATH = os.getenv('LOCALAPPDATA') + r"\Google\Chrome\User Data"

EDIT_URL_TEMPLATE = ("https://uexcorp.space"
                     "/data/submit/type/request?resource={resource}&request_action=edit&id_reference={id}")
WIKI_API_URL_TEMPLATE = ("https://api.star-citizen.wiki"
                         "/api/v2/{resource}/{name}?locale=en_EN")
UPDATE_REASON_TEMPLATE = ("UUID was not set, updating from Wiki => {wiki_api_url}"
                          " # Source: https://github.com/FatalMerlin/uex-uuid-updater")


class UEXUpdater:
    class ResourceType(StrEnum):
        VEHICLE = "vehicles"
        ITEM = "items"

    def __init__(self, use_cache: bool = True):
        self.main_page = None
        self.browser = None
        self.context = None
        self.log = get_logger()
        self.use_cache = use_cache

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        self.context = self.setup_context()
        self.browser = self.setup_browser()
        self.main_page = self.setup_pages()

        return self

    def stop(self):
        self.browser.close()
        self.context.stop()

    def setup_context(self) -> Playwright:
        return sync_playwright().start()

    def setup_browser(self) -> BrowserContext:
        return self.context.chromium.launch_persistent_context(
            BROWSER_USER_DATA_PATH,
            channel="chrome", headless=False, slow_mo=0
        )

    def setup_pages(self):
        page, discard = self.browser.pages[0], self.browser.pages[1:]
        for excess in discard:
            excess.close()

        page.goto("about:blank")
        return page

    def scroll_hover_click(self, locator: Locator):
        locator.scroll_into_view_if_needed()
        locator.hover()
        locator.click()

    def fill_field(self, locator: str, value: str):
        # self.main_page.fill(locator, value)
        input_element = self.main_page.locator(f'input[name="{locator}"]')

        self.scroll_hover_click(input_element)
        input_element.fill(value)

    def get_wiki_proof(self, wiki_api_url: str) -> bool:
        """
        Takes a screenshot of the Wiki API response and returns it as a base64 encoded string.
        :param wiki_api_url: The URL of the Wiki API endpoint
        :return: The screenshot as a base64 encoded string
        """
        try:
            with self.browser.new_page() as page:
                page.goto(wiki_api_url)
                page.evaluate(
                    dedent(
                        """
                        let text = document.querySelector('pre').childNodes[0];
                        let match = text.textContent.match(/"uuid": "[\w-]+",/);
                        window
                            .getSelection()
                            .setBaseAndExtent(
                                text, match.index,
                                text, match.index + match[0].length
                            );
                        document.body.style.zoom=2.5;
                        """
                    )
                )

                page.screenshot(type='png', path=screenshot_path)
        except Exception as e:
            self.log.error("Failed to get screenshot", wiki_api_url=wiki_api_url, exception=e)
            return False

        return True

    def add_screenshot(self):
        with self.main_page.expect_file_chooser() as file_chooser_info:
            screenshot_input = self.main_page.locator('#btn_screenshot_attach')
            self.scroll_hover_click(screenshot_input)

        file_chooser = file_chooser_info.value
        file_chooser.set_files(screenshot_path)

    def agree(self):
        # agree to possible request modification by UEX Staff
        checkbox_input = self.main_page.locator('label[for="agreement1"]')
        self.scroll_hover_click(checkbox_input)

    def submit(self):
        submit_button = self.main_page.locator(
            'button[title="Click to submit this report and go back to the reports list"]'
        )
        self.scroll_hover_click(submit_button)

    def update(self, resource_type: ResourceType, update: Update) -> bool:
        if update.status != UpdateStatus.PENDING:
            self.log.warn("Skipped update", id=update.id, status=update.status)
            return False

        changed_keys = [key for key, value in update.changes.__dict__.items() if value is not None]

        self.log.info("Updating", resource_type=resource_type.value, id=update.id,
                      changed_keys=", ".join(changed_keys))

        edit_url = EDIT_URL_TEMPLATE.format(resource=resource_type.value, id=update.id)
        wiki_api_url = WIKI_API_URL_TEMPLATE.format(resource=resource_type.value, name=urllib.parse.quote_plus(update.name))

        self.main_page.goto(edit_url)

        if not self.get_wiki_proof(wiki_api_url):
            return False

        for key in changed_keys:
            self.fill_field(f"request_data[{key}]", str(update.changes.__dict__[key]))
        self.fill_field("details", UPDATE_REASON_TEMPLATE.format(wiki_api_url=wiki_api_url))


        self.add_screenshot()
        self.agree()
        self.submit()

        try:
            self.main_page.wait_for_url("https://uexcorp.space/data/home/type/request/ids_highlighted//")
        except Exception as e:
            self.log.error("Submission failed", unexpected_url=self.main_page.url, exception=e)
            return False

        return True
