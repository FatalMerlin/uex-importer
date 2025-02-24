from abc import ABC, abstractmethod

import requests
from requests import Response
from structlog.stdlib import get_logger

from utils.cache import write_cache, read_cache


class BaseSync(ABC):

    def __init__(self, use_cache: bool = True):
        self.log = get_logger()
        self.use_cache = use_cache

    @abstractmethod
    def sync(self, modelType: type):
        raise NotImplementedError

    def validate_response(self, response: Response) -> bool:
        return response.status_code == 200

    def validate_parsed(self, parsed: dict) -> bool:
        return True

    def fetch(self, url: str) -> dict | None:

        if self.use_cache:
            cached = read_cache(url)

            if cached is not None:
                return cached

        response = requests.get(url)

        if not self.validate_response(response):
            self.log.error(f"Fetching failed", url=url, status_code=response.status_code)
            return None

        parsed = response.json()

        if not self.validate_parsed(parsed):
            self.log.error(f"Invalid response", url=url, parsed=parsed)
            return None

        if self.use_cache:
            write_cache(url, parsed)

        return parsed
