"""The in-memory fake's own behaviour (it must be trustworthy to unit-test services with it)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Status
from tests.fakes import FakeUnitOfWork
from tests.support.builders import make_collection, make_photo


def test_commits_are_counted_and_persist(fake_uow: FakeUnitOfWork) -> None:
    with fake_uow as uow:
        uow.photos.add(make_photo("p1"))
        uow.commit()
    assert fake_uow.commits == 1
    with fake_uow as uow:
        assert uow.photos.get("p1") is not None


def test_leaving_a_block_without_commit_discards_additions_and_edits(
    fake_uow: FakeUnitOfWork,
) -> None:
    with fake_uow as uow:
        uow.photos.add(make_photo("keep", title="before", status=Status.DRAFT))
        uow.commit()
    with fake_uow as uow:
        uow.photos.add(make_photo("ghost"))
        photo = uow.photos.get("keep")
        assert photo is not None
        photo.title = "after"
        photo.status = Status.PUBLISHED
    with fake_uow as uow:
        kept = uow.photos.get("keep")
        assert kept is not None and (kept.title, kept.status) == ("before", Status.DRAFT)
        assert uow.photos.get("ghost") is None


def test_changes_made_after_a_commit_in_the_same_block_are_still_discarded(
    fake_uow: FakeUnitOfWork,
) -> None:
    with fake_uow as uow:
        uow.photos.add(make_photo("p1"))
        uow.commit()
        uow.photos.add(make_photo("p2"))  # after the commit, never committed
    with fake_uow as uow:
        assert uow.photos.get("p1") is not None and uow.photos.get("p2") is None


def test_a_failing_commit_can_be_injected_and_rolls_everything_back(
    fake_uow: FakeUnitOfWork,
) -> None:
    fake_uow.fail_next_commit(RuntimeError("disk full"))
    with pytest.raises(RuntimeError, match="disk full"), fake_uow as uow:
        uow.photos.add(make_photo("p1"))
        uow.commit()
    assert fake_uow.commits == 0
    with fake_uow as uow:
        assert uow.photos.get("p1") is None
        uow.photos.add(make_photo("p2"))
        uow.commit()  # the failure was one-shot
    assert fake_uow.commits == 1


def test_unique_constraints_are_enforced_at_commit_like_the_database(
    fake_uow: FakeUnitOfWork,
) -> None:
    with pytest.raises(IntegrityError), fake_uow as uow:
        uow.photos.add(make_photo("a", unsplash_id="u"))
        uow.photos.add(make_photo("b", unsplash_id="u"))
        uow.commit()
    with pytest.raises(IntegrityError), fake_uow as uow:
        uow.collections.add(make_collection("x", slug="same"))
        uow.collections.add(make_collection("y", slug="same"))
        uow.commit()


def test_audit_actions_are_exposed_for_assertions(fake_uow: FakeUnitOfWork) -> None:
    from app.models import AuditLog

    with fake_uow as uow:
        uow.audit.add(AuditLog(action="photo.publish", target="p1"))
        uow.commit()
    assert fake_uow.audit_actions == ["photo.publish"]
