from typing import TypeVar

from requests import Response
from typing_extensions import override

from models.base.uex_base_model import UEXBaseModel
from models.uex.item import UEXItem
from sync.base import BaseSync

T = TypeVar('T', bound=UEXBaseModel)


class UEXSync(BaseSync):

    def sync(self, modelType: type[T]) -> list[T]:
        endpoint_url = f"{modelType.BASE_URL}{modelType.ENDPOINT_PATH}"
        self.log.info("Synchronizing UEX", model=modelType.__name__, source=endpoint_url)

        if modelType.FOREACH is not None:
            fetch_urls = [
                endpoint_url + modelType.FOREACH_MAP(model)
                for model in self.sync(modelType.FOREACH)
            ]
        else:
            fetch_urls = [endpoint_url]

        results: list[T] = []

        for url in fetch_urls:
            result = self.fetch(url)

            if result is None or result['data'] is None:
                continue

            entries = [
                modelType(**entry)
                for entry in result['data']
            ]

            results.extend(entries)

        return results

    @override
    def validate_parsed(self, parsed: dict) -> bool:
        return super().validate_parsed(parsed) and parsed["status"] == "ok"


if __name__ == '__main__':
    UEXSync().sync(UEXItem)
