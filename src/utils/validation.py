import inspect
from functools import reduce
from types import UnionType, NoneType
from typing import Type, Union, get_args

from pydantic import BaseModel
from pydantic.fields import FieldInfo


def is_union(t: Type):
    return t is Union or isinstance(t,UnionType)

def filter_none_type(t: list[Type]):
    return [x for x in t if x is not NoneType]

def get_model_fields(t: Type | list[Type]):
    if not isinstance(t, list):
        t = [t]

    model_fields: dict[str, Type] = {}



def resolve_annotations(annotation: Type | None) -> list[Type]:
    if not is_union(annotation):
        return [annotation]

    union_types = filter_none_type(list(get_args(annotation)))
    result = []

    for union_type in union_types:
        result.extend(resolve_annotations(union_type))

    return result

def validate_path(path: str, model_fields: dict[str, FieldInfo]) -> (bool, list[dict[str, FieldInfo]]):
    if path in model_fields and isinstance(model_fields[path], FieldInfo):
        annotation = model_fields[path].annotation
        type_list = resolve_annotations(annotation)

        return True, [
            type_.model_fields
            for type_ in type_list
            if inspect.isclass(type_) and issubclass(type_, BaseModel)
        ]

    return False, []

def validate_value_path(key: str, value_path: str, model: Type[BaseModel]):
    value_paths = value_path.split(".")
    valid_paths: list[str] = []
    # noinspection PyTypeChecker
    model_fields_list: list[dict[str, FieldInfo]] = [model.model_fields]

    for path in value_paths:
        has_valid = False
        new_model_fields_list: list[dict[str, FieldInfo]] = []

        for model_fields in model_fields_list:
            valid, new_model_fields = validate_path(path, model_fields)
            if valid:
                has_valid = True
                new_model_fields_list.extend(new_model_fields)

        if has_valid:
            valid_paths.append(path)
            model_fields_list = new_model_fields_list
            continue

        raise ValueError(f"Invalid mapping for key '{key}':"
                         f" Invalid Path '{value_path}' for model '{model.__name__}' -"
                         f" '{path}' missing in '{model_fields_list}' -"
                         f" Current path: {'.'.join([*valid_paths, value_path])}")


def get_attr_by_path(obj: object, path: str):
    for p in path.split('.'):
        if obj == None:
            return None
        obj = getattr(obj, p, None)
    return obj