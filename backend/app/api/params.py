"""Path-parameter types shared by routers."""

from typing import Annotated

from fastapi import Path

# Photos, collections and chapters all use 32-char hex ids.
ResourceId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
