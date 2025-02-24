from typing import TypeVar

from rich.progress import Progress

from models.base.wiki_base_model import WikiBaseModel
from models.responses.wiki_paginated import PaginatedResponse
from models.wiki.item import WikiItem
from sync.base import BaseSync
from utils.cache import read_cache

T = TypeVar('T', bound=WikiBaseModel)

class WikiSync(BaseSync):
    def __init__(self, use_cache: bool = True, pagination_limit: int = 500):
        super().__init__(use_cache)
        self.pagination_limit = pagination_limit

    def sync(self, modelType: type[T]) -> list[T]:
        fetch_url = f"{modelType.BASE_URL}{modelType.ENDPOINT_PATH}"

        self.log.info(
            f"Synchronizing Wiki",
            model=modelType.__name__,
            source=fetch_url)

        if modelType.IS_PAGINATED:
            return self.sync_paginated(modelType, fetch_url)
        else:
            self.log.error(f"Model {modelType.__name__} is not paginated")
            pass

        return []

    def sync_paginated(self, modelType: type[T], fetch_url: str = None) -> list[T]:
        next_url = f"{fetch_url}?limit={self.pagination_limit}"
        is_first_iteration = True
        results: list[T] = []

        with Progress(transient=True) as progress:
            task = progress.add_task(f"Syncing {modelType.__name__}", total=None)

            while next_url:
                if self.use_cache:
                    response = read_cache(next_url)

                if response is None:
                    response = self.fetch(next_url)

                parsed = PaginatedResponse(**response)
                next_url = parsed.links.next

                results.extend([modelType(**entry) for entry in parsed.data])

                if is_first_iteration:
                    is_first_iteration = False
                    progress.columns[2].text_format = '[progress.percentage][{task.completed}/{task.total}]'

                progress.update(task, total=parsed.meta.last_page, completed=parsed.meta.current_page)

        return results


if __name__ == "__main__":
    WikiSync().sync(WikiItem)
