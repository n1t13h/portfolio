"""Atomic reordering: validate the whole id list first, then assign positions."""

from collections.abc import Sequence
from typing import Protocol

from app.core.errors import InvalidRequest


class HasId(Protocol):
    id: str


def apply_order(rows: Sequence[HasId], ordered_ids: Sequence[str], attr: str) -> None:
    """Set `attr` to each row's index in `ordered_ids`.

    `ordered_ids` must name every row exactly once; otherwise nothing is changed.
    """
    by_id = {row.id: row for row in rows}
    if len(set(ordered_ids)) != len(ordered_ids) or set(ordered_ids) != by_id.keys():
        raise InvalidRequest("ids must list every item exactly once")
    for position, id_ in enumerate(ordered_ids):
        setattr(by_id[id_], attr, position)
