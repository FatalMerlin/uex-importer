import json
import os
from textwrap import dedent

from models.uex_vehicle import UEX_Vehicle
from patchright.sync_api import sync_playwright, Page
import logging

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s')
log = logging.getLogger(__name__)

file_dir = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(file_dir, 'cache')
update_json_file = os.path.join(cache_dir, 'uex_vehicles_updated.json')
submitted_json_file = os.path.join(cache_dir, 'uex_vehicles_submitted.json')
screenshot_path = os.path.abspath(os.path.join(file_dir, 'screenshot.png'))

browser_user_data_path = os.getenv('LOCALAPPDATA') + r"\Google\Chrome\User Data"

edit_url_template = "https://uexcorp.space/data/submit/type/request?resource=vehicles&request_action=edit&id_reference={id}"
wiki_api_url_template = "https://api.star-citizen.wiki/api/v3/vehicles/{name}?locale=en_EN"
update_reason_template = "UUID was not set, updating from Wiki => {wiki_api_url} # Source: https://github.com/FatalMerlin/uex-uuid-updater"


def main():
    with open(update_json_file, 'r') as f:
        contents = f.read()
        f.close()

    parsed = json.loads(contents)

    submitted: dict[str, str] = {}
    if os.path.exists(submitted_json_file):
        with open(submitted_json_file, 'r') as f:
            contents = f.read()
            f.close()

        submitted = json.loads(contents)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            browser_user_data_path,
            channel="chrome", headless=False, slow_mo=250)

        page, discard = browser.pages[0], browser.pages[1:]
        for excess in discard:
            excess.close()

        for entry in parsed:
            vehicle = UEX_Vehicle(**entry)

            try:
                if str(vehicle.id) in submitted:
                    log.info(f'SKIP: UUID for {vehicle.name} has already been updated ({vehicle.uuid})')
                    continue

                edit_url_with_id = edit_url_template.format(id=vehicle.id)
                wiki_api_url = wiki_api_url_template.format(name=vehicle.name)

                # https://github.com/FatalMerlin/uex-uuid-updater

                page.goto(edit_url_with_id)

                # fill UUID
                uuid_input = page.locator('input[name="request_data[uuid]"]')

                if uuid_input.input_value() == vehicle.uuid:
                    log.warning(f'UNEXPECTED SKIP: UUID for {vehicle.name} has already been updated ({vehicle.uuid})'
                                f' - but not by this script')
                    update_submitted(vehicle, submitted)
                    continue

                uuid_input.scroll_into_view_if_needed()
                uuid_input.hover()
                uuid_input.click()
                uuid_input.fill(vehicle.uuid)

                # fill request details / reason
                details_input = page.locator('input[name="details"]')
                details_input.scroll_into_view_if_needed()
                details_input.hover()
                details_input.click()
                details_input.fill(update_reason_template.format(wiki_api_url=wiki_api_url))

                # attach screenshot with proof
                with browser.new_page() as wiki_page:
                    get_wiki_api_screenshot(wiki_page, wiki_api_url)

                with page.expect_file_chooser() as file_chooser_info:
                    screenshot_input = page.locator('#btn_screenshot_attach')
                    screenshot_input.scroll_into_view_if_needed()
                    screenshot_input.hover()
                    screenshot_input.click()

                file_chooser = file_chooser_info.value
                file_chooser.set_files(screenshot_path)

                # agree to possible request modification by UEX Staff
                checkbox_input = page.locator('label[for="agreement1"]')
                checkbox_input.scroll_into_view_if_needed()
                checkbox_input.hover()
                checkbox_input.click()

                submit_button = page.locator('button[title="Click to submit this report and go back to the reports list"]')
                submit_button.scroll_into_view_if_needed()
                submit_button.hover()
                submit_button.click()

                page.wait_for_url("https://uexcorp.space/data/home/type/request/ids_highlighted//")

                log.info(f'Updated UUID for {vehicle.name} ({vehicle.uuid})')
                update_submitted(vehicle, submitted)

            except Exception as e:
                log.error(f'Failed to update UUID for {vehicle.name} ({vehicle.uuid})', exc_info=e)

        browser.close()


def update_submitted(vehicle: UEX_Vehicle, submitted: dict[str, str]):
    submitted[str(vehicle.id)] = vehicle.uuid

    with open(submitted_json_file, 'w') as f:
        f.write(json.dumps(submitted))
        f.flush()
        f.close()


def get_wiki_api_screenshot(page: Page, wiki_api_url: str):
    """
    Takes a screenshot of the Wiki API response and returns it as a base64 encoded string.
    :param wiki_api_url: The URL of the Wiki API endpoint
    :param page: The Playwright page object
    :return: The screenshot as a base64 encoded string
    """
    page.goto(wiki_api_url)
    page.evaluate(
        dedent(
            """
            let text = document.querySelector('pre').childNodes[0];
            window
                .getSelection()
                .setBaseAndExtent(
                    text, text.textContent.indexOf('"uuid":'),
                    text, text.textContent.indexOf('"slug":') - 9
                );
            document.body.style.zoom=2.5;
            """
        )
    )

    page.screenshot(type='png', path=screenshot_path)


if __name__ == '__main__':
    main()
