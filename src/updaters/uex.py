import os
import re
import shutil
from enum import StrEnum
from textwrap import dedent

from patchright.sync_api import sync_playwright, Playwright, BrowserContext, Locator, Page
from structlog.stdlib import get_logger

from models.update import Update, UpdateStatus
from utils.cache import cache_dir

BROWSER_USER_DATA_PATH = os.getenv('LOCALAPPDATA') + r"\Google\Chrome\User Data"

EDIT_URL_TEMPLATE = ("https://uexcorp.space"
                     "/data/submit/type/request?resource={resource}&request_action=edit&id_reference={id}")
WIKI_API_URL_TEMPLATE = ("https://api.star-citizen.wiki"
                         "/api/v2/{resource}/{name}?locale=en_EN")
# UPDATE_REASON_TEMPLATE = ("UUID was not set, updating from Wiki => {wiki_api_url}"
#                           " # Source: https://github.com/FatalMerlin/uex-uuid-updater")

UPDATE_REASON_TEMPLATE = ("[AUTOMATED UPDATE] Updated Fields: {changed_fields}"
                          " - Data Source: {wiki_api_url}"
                          " # GitHub: https://github.com/FatalMerlin/uex-uuid-updater")

SCREENSHOT_DIR_NAME = "screenshots"
SCREENSHOT_DIR = os.path.join(cache_dir, SCREENSHOT_DIR_NAME)


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

    @staticmethod
    def setup_context() -> Playwright:
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

    @staticmethod
    def scroll_hover_click(locator: Locator):
        locator.scroll_into_view_if_needed()
        locator.hover()
        locator.click()

    def fill_field(self, locator: str, value: str):
        # self.main_page.fill(locator, value)
        input_element = self.main_page.locator(f'input[name="{locator}"]')

        self.scroll_hover_click(input_element)
        input_element.fill(value)

    def get_wiki_proof_for_change(self, page: Page, changed_key: str, source_path: str) -> str | None:
        try:
            offset_start = 0
            last_match_length = 0
            text_content = page.locator('pre').text_content()
            offset_text = text_content

            for path in source_path.split('.'):
                match = re.search(rf'"{path}":', offset_text)
                if match is None:
                    return None

                offset_start += match.end()
                last_match_length = match.end() - match.start()
                offset_text = text_content[offset_start:]

            offset_end_match = re.search(r'\n', offset_text)
            if offset_end_match is None:
                return None

            offset_end = offset_end_match.start() + offset_start
            offset_start -= last_match_length

            page.evaluate(
                dedent(
                    f"""
                    let text = document.querySelector('pre').childNodes[0];
                    let selection = window.getSelection();
                    selection
                        .setBaseAndExtent(
                            text, {offset_start},
                            text, {offset_end}
                        );
                    document.body.style.zoom=2.5;
                    let range = selection.getRangeAt(0);
                    let rect = range.getBoundingClientRect();
                    let absoluteTop = rect.top + window.scrollY;
                    window.scrollTo({{top: Math.min(absoluteTop - 200, 0)}});
                    """
                )
            )

            screenshot_path = os.path.join(SCREENSHOT_DIR, f"{changed_key}.png")
            page.screenshot(type='png', path=screenshot_path)

            return screenshot_path
        except Exception as e:
            self.log.error("Failed to get proof", changed_key=changed_key, source_path=source_path, exc_info=e)
            return None

    def get_wiki_proof(self, wiki_api_url: str, update: Update, changed_keys: list[str]) -> list[str] | None:
        """
        Takes a screenshot of the Wiki API response and returns it as a base64 encoded string.
        :param wiki_api_url: The URL of the Wiki API endpoint
        :return: The screenshot as a base64 encoded string
        """
        screenshot_paths: list[str] = []

        try:
            if os.path.exists(SCREENSHOT_DIR):
                shutil.rmtree(SCREENSHOT_DIR)
            if not os.path.exists(SCREENSHOT_DIR):
                os.makedirs(SCREENSHOT_DIR)

            with self.browser.new_page() as page:
                page.goto(wiki_api_url)

                for changed_key in changed_keys:
                    screenshot = self.get_wiki_proof_for_change(
                        page, changed_key,
                        update.change_source_mapping[changed_key])

                    if screenshot is None:
                        return None

                    screenshot_paths.append(screenshot)
        except Exception:
            self.log.exception("Failed to get screenshots", wiki_api_url=wiki_api_url)
            return None

        return screenshot_paths

    def add_screenshots(self, screenshot_paths: list[str]):
        with self.main_page.expect_file_chooser() as file_chooser_info:
            screenshot_input = self.main_page.locator('#btn_screenshot_attach')
            self.scroll_hover_click(screenshot_input)

        file_chooser = file_chooser_info.value
        file_chooser.set_files(screenshot_paths)

    def agree(self):
        # agree to possible request modification by UEX Staff
        checkbox_input = self.main_page.locator('label[for="agreement1"]')
        self.scroll_hover_click(checkbox_input)

    def submit(self, dry_run: bool = False):
        if dry_run:
            return

        submit_button = self.main_page.locator(
            'button[title="Click to submit this report and go back to the reports list"]'
        )
        self.scroll_hover_click(submit_button)

    def update(self, resource_type: ResourceType, update: Update, dry_run: bool = False) -> bool:
        if update.status != UpdateStatus.PENDING:
            self.log.warn("Skipped update", id=update.id, status=update.status)
            return False

        changes = dict([
            (key, value) for key, value in update.changes.__dict__.items() if value is not None
        ])
        changed_keys = list(changes.keys())

        if len(changed_keys) == 0:
            self.log.info("No changes found", id=update.id)
            return True

        self.log.info("Updating", resource_type=resource_type.value, id=update.id,
                      changed_keys=changed_keys, changes=changes)

        edit_url = EDIT_URL_TEMPLATE.format(resource=resource_type.value, id=update.id)
        # wiki_api_url = WIKI_API_URL_TEMPLATE.format(resource=resource_type.value, name=urllib.parse.quote_plus(update.name))
        wiki_api_url = update.source_link

        self.main_page.goto(edit_url)

        try:
            screenshot_paths = self.get_wiki_proof(wiki_api_url, update, changed_keys)
            if screenshot_paths is None or len(screenshot_paths) != len(changed_keys):
                return False
        except Exception as e:
            self.log.exception("Failed to get screenshot", wiki_api_url=wiki_api_url, exc_info=e)
            return False

        for key in changed_keys:
            self.fill_field(f"request_data[{key}]", str(update.changes.__dict__[key]))
        self.fill_field("details", UPDATE_REASON_TEMPLATE.format(
            changed_fields=", ".join(changed_keys), wiki_api_url=wiki_api_url))

        self.add_screenshots(screenshot_paths)
        self.agree()

        if dry_run:
            return True

        self.submit()

        try:
            self.main_page.wait_for_url("https://uexcorp.space/data/home/type/request/ids_highlighted//")
        except Exception as e:
            self.log.exception("Submission failed", unexpected_url=self.main_page.url, exc_info=e)
            return False

        return True
