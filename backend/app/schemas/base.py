"""Base classes for wire models: snake_case in Python, camelCase on the wire.

Models are built straight from loaded rows with `Model.model_validate(row)`. Anything a row does
not hold itself arrives through the validation context, e.g. the CDN address of stored images:

    PhotoOut.model_validate(photo, context={"public_url": storage.public_url})
"""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationInfo
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


def storage_keys_to_urls(keys: dict[str, str], info: ValidationInfo) -> dict[str, str]:
    """Turn {edge: storage key} into {edge: public URL} when the context supplies `public_url`."""
    context: dict[str, Any] = info.context or {}
    public_url: Callable[[str], str] | None = context.get("public_url")
    return {edge: public_url(key) for edge, key in keys.items()} if public_url else keys
