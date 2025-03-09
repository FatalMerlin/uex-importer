import json
import os
import re
from typing import Any, TypeVar

from pydantic import BaseModel
from pydantic.v1.json import pydantic_encoder
from structlog.stdlib import get_logger

from models.base.uex_base_model import UEXBaseModel
from models.update import Update, UpdateList

_log = get_logger()
cache_dir = os.path.join(os.getcwd(), 'cache')

T = TypeVar('T', bound=UEXBaseModel)


def ensure_cache_dir(*, prefix: str | None = None) -> str:
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    if prefix:
        prefix_cache_dir = os.path.join(cache_dir, prefix)
        if not os.path.exists(prefix_cache_dir):
            os.makedirs(prefix_cache_dir)
        return prefix_cache_dir

    return cache_dir


def get_cache_file_for_updates_by_model(modelType: T, *, prefix: str | None = None):
    cache_dir = ensure_cache_dir(prefix=prefix)

    cache_file_name = modelType.__name__ + '_updates' + '.json'

    return os.path.join(cache_dir, cache_file_name)


def get_cache_file(url: str, *, prefix: str | None = None):
    cache_dir = ensure_cache_dir(prefix=prefix)

    cache_file_name = url.split('/')[-1] or url.split('/')[-2]
    cache_file_name = re.sub(r'\W', '_', cache_file_name)

    if not cache_file_name.endswith('.json'):
        cache_file_name += '.json'

    return os.path.join(cache_dir, cache_file_name)


def write_cache_updates(contents: list[UpdateList[T]], *, prefix: str | None = None):
    write_cache(T, contents, prefix=prefix)


def write_cache(url_or_model_type: str | T, contents: str | Any, *, prefix: str | None = None):
    if isinstance(contents, BaseModel):
        contents = contents.model_dump_json(exclude_none=True)
    else:
        contents = json.dumps(contents)

    file = get_cache_file(url_or_model_type, prefix=prefix) \
        if isinstance(url_or_model_type, str) \
        else get_cache_file_for_updates_by_model(url_or_model_type, prefix=prefix)

    with open(file, 'w') as f:
        f.write(contents)
        f.flush()
        f.close()


def read_cache(url_or_model_type: str | type[T], *, prefix: str | None = None):
    file = get_cache_file(url_or_model_type, prefix=prefix) \
        if isinstance(url_or_model_type, str) \
        else get_cache_file_for_updates_by_model(url_or_model_type, prefix=prefix)

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
        _log.warn(f"Removed corrupted cache file", file=file)
        return None
