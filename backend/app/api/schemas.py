"""Shared API types: the camelCase payload base class and the resource-id path type."""

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# Photos, collections and chapters all use 32-char hex ids.
ResourceId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
