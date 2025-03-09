from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError
from structlog.stdlib import get_logger, BoundLogger

_logger = get_logger()

TModel = TypeVar('TModel', bound=BaseModel)


def try_parse(model_type: Type[TModel], data: dict, log: BoundLogger = _logger) -> TModel | None:
    try:
        return model_type(**data)
    except ValidationError as e:
        log.error(f"Failed to parse {model_type.__name__}", data=data, error=e, unexpected=True)
    return None


def try_parse_all(model_type: Type[TModel], data: list[dict], log: BoundLogger = _logger) -> list[TModel]:
    return [
        parsed for entry in data
        if (parsed := try_parse(model_type, entry, log)) is not None
    ]
