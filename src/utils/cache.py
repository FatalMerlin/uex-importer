import json
import os
import re
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic.v1.json import pydantic_encoder
from structlog.stdlib import get_logger

from models.base.uex_base_model import UEXBaseModel
from models.update import Update, UpdateList

log = get_logger()
cache_dir = os.path.join(os.getcwd(), 'cache')
screenshot_path = os.path.abspath(os.path.join(cache_dir, 'screenshot.png'))

T = TypeVar('T', bound=UEXBaseModel)


def ensure_cache_dir():
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)


def get_cache_file_for_updates_by_model(modelType: T):
    ensure_cache_dir()

    cache_file_name = modelType.__name__ + '_updates' + '.json'

    return os.path.join(cache_dir, cache_file_name)


def get_cache_file(url: str):
    ensure_cache_dir()

    cache_file_name = url.split('/')[-1] or url.split('/')[-2]
    cache_file_name = re.sub(r'\W', '_', cache_file_name)

    if not cache_file_name.endswith('.json'):
        cache_file_name += '.json'

    return os.path.join(cache_dir, cache_file_name)


def write_cache_updates(contents: list[UpdateList[T]]):
    write_cache(T, contents)


def write_cache(url_or_model_type: str | T, contents: str | Any):

    if isinstance(contents, BaseModel):
        contents = contents.model_dump_json(exclude_none=True)
    else:
        contents = json.dumps(contents)

    file = get_cache_file(url_or_model_type) \
        if isinstance(url_or_model_type, str) \
        else get_cache_file_for_updates_by_model(url_or_model_type)

    with open(file, 'w') as f:
        f.write(contents)
        f.flush()
        f.close()


def read_cache(url_or_model_type: str | type[T]):
    file = get_cache_file(url_or_model_type) \
        if isinstance(url_or_model_type, str) \
        else get_cache_file_for_updates_by_model(url_or_model_type)

    if not os.path.exists(file):
        return None

    try:
        with open(file, 'r') as f:
            contents = f.read()
            f.close()

        if not contents:
            return None

        return json.loads(contents)
    except json.JSONDecodeError or OSError:
        os.remove(file)
        log.warn(f"Removed corrupted cache file", file=file)
        return None
