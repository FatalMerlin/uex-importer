from typing import TypeVar, Type

from rich.progress import Progress, track

from models.base.wiki_base_model import WikiBaseModel, WikiPaginatedModel
from models.responses.wiki_paginated import PaginatedResponse
from models.wiki.item import WikiItem
from sync.base import BaseSync
from utils.cache import read_cache
from utils.model import try_parse, try_parse_all

T = TypeVar('T', bound=WikiBaseModel)


class WikiSync(BaseSync):
    def __init__(self, use_cache: bool = True, pagination_limit: int = 500):
        super().__init__(use_cache)
        self.pagination_limit = pagination_limit

    def sync(self, modelType: Type[T]) -> list[T]:
        fetch_url = f"{modelType.BASE_URL}{modelType.ENDPOINT_PATH}"

        self.log.info(
            f"Synchronizing Wiki",
            model=modelType.__name__,
            source=fetch_url)

        if modelType.IS_PAGINATED:
            if modelType.PAGINATION_MODEL is None:
                return self.sync_paginated(modelType, fetch_url)

            pagination_results = self.sync_paginated(modelType.PAGINATION_MODEL, fetch_url)
            return self.sync_details(modelType, pagination_results)
        else:
            self.log.error(f"Model {modelType.__name__} is not paginated")
            pass

        return []

    def sync_paginated(self, modelType: Type[T], fetch_url: str = None) -> list[T]:
        self.log.info("Synchronizing paginated Wiki model", model=modelType.__name__, source=fetch_url)
        next_url = f"{fetch_url}?limit={self.pagination_limit}"
        is_first_iteration = True
        results: list[T] = []

        with Progress() as progress:
            task = progress.add_task(f"Syncing {modelType.__name__}", total=None)

            while next_url:
                response = self.fetch(next_url, prefix=modelType.__name__)

                parsed = PaginatedResponse(**response)
                next_url = parsed.links.next

                results.extend(
                    try_parse_all(modelType, parsed.data, self.log)
                )

                if is_first_iteration:
                    is_first_iteration = False
                    progress.columns[2].text_format = '[progress.percentage][{task.completed}/{task.total}]'

                progress.update(task, total=parsed.meta.last_page, completed=parsed.meta.current_page)

        return results

    def sync_details(self,
                     modelType: Type[T], pagination_results: list[WikiPaginatedModel]) -> list[T]:
        self.log.info("Synchronizing Wiki model details", model=modelType.__name__)
        results: list[T] = []

        for result in track(pagination_results, description=f"Syncing {modelType.__name__} details"):
            response = self.fetch(result.link, prefix=modelType.__name__)

            if response is None or not "data" in response:
                continue

            # copy fields from paginated model, e.g. UUID
            # for vehicles, UUID is not available on the details page
            # in some cases, and the details page has very different fields.
            # By specifying the paginated model fields first, we can override them
            # with the details page results, if they are present
            parsed = try_parse(modelType.model_as_partial(), {**result.__dict__, **response['data']}, self.log)
            if parsed is None: # error handled and logged in `try_parse`
                continue
            results.append(parsed)

        return results


if __name__ == "__main__":
    WikiSync().sync(WikiItem)
