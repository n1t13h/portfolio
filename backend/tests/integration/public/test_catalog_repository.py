"""Repository contract for the public read side: what visitors may see."""

from app.models import Status
from app.uow import AbstractUnitOfWork
from tests.support.builders import make_chapter, make_collection, make_photo, published


def seed(uow: AbstractUnitOfWork) -> None:
    """A published collection (pub) and a draft one (hidden), plus loose photos."""
    with uow:
        uow.collections.add(make_collection("pub", slug="pub", sort_position=1, **published()))
        uow.collections.add(make_collection("first", slug="first", sort_position=0, **published()))
        uow.collections.add(make_collection("hidden", slug="hidden", sort_position=2))
        uow.collections.add_chapter(make_chapter("b", "pub", position=1))
        uow.collections.add_chapter(make_chapter("a", "pub", position=0))
        uow.collections.add_chapter(make_chapter("h", "hidden"))
        for photo in (
            make_photo("loose-pub", sort_position=0, **published()),
            make_photo("loose-draft", sort_position=1),
            make_photo(
                "in-a-2", chapter_id="a", position_in_chapter=1, sort_position=2, **published()
            ),
            make_photo(
                "in-a-1", chapter_id="a", position_in_chapter=0, sort_position=3, **published()
            ),
            make_photo("in-a-draft", chapter_id="a", position_in_chapter=2, sort_position=4),
            make_photo("in-b", chapter_id="b", sort_position=5, **published(allow_download=True)),
            make_photo(
                "in-hidden", chapter_id="h", sort_position=6, **published(allow_download=True)
            ),
            make_photo("loose-dl", sort_position=7, **published(allow_download=True)),
        ):
            uow.photos.add(photo)
        uow.commit()


def test_public_photos_are_published_ones_outside_draft_collections_in_order(
    uow: AbstractUnitOfWork,
) -> None:
    seed(uow)
    with uow:
        ids = [p.id for p in uow.catalog.list_public_photos()]
        assert ids == ["loose-pub", "in-a-2", "in-a-1", "in-b", "loose-dl"]


def test_only_public_photos_with_downloads_enabled_are_downloadable(
    uow: AbstractUnitOfWork,
) -> None:
    seed(uow)
    with uow:
        assert uow.catalog.get_downloadable_photo("loose-dl") is not None
        assert uow.catalog.get_downloadable_photo("in-b") is not None
        assert uow.catalog.get_downloadable_photo("loose-pub") is None  # downloads off
        assert uow.catalog.get_downloadable_photo("in-hidden") is None  # draft collection
        assert uow.catalog.get_downloadable_photo("nope") is None


def test_a_draft_photo_is_not_downloadable_even_with_the_flag_on(uow: AbstractUnitOfWork) -> None:
    with uow:
        uow.photos.add(make_photo("d", allow_download=True))
        uow.commit()
    with uow:
        assert uow.catalog.get_downloadable_photo("d") is None


def test_published_collections_in_order_and_lookup_by_slug(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        assert [c.id for c in uow.catalog.list_published_collections()] == ["first", "pub"]
        found = uow.catalog.get_published_collection("pub")
        assert found is not None and found.id == "pub"
        assert uow.catalog.get_published_collection("hidden") is None
        assert uow.catalog.get_published_collection("nope") is None


def test_chapters_of_a_collection_in_display_order(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        assert [c.id for c in uow.catalog.list_chapters("pub")] == ["a", "b"]


def test_published_photos_by_chapter_skip_drafts_and_keep_display_order(
    uow: AbstractUnitOfWork,
) -> None:
    seed(uow)
    with uow:
        grouped = uow.catalog.published_photos_by_chapter(["a", "b", "empty"])
        assert {k: [p.id for p in v] for k, v in grouped.items()} == {
            "a": ["in-a-1", "in-a-2"],
            "b": ["in-b"],
            "empty": [],
        }
        assert uow.catalog.published_photos_by_chapter([]) == {}


def test_published_photos_by_collection_skip_drafts(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        grouped = uow.catalog.published_photos_by_collection(["pub", "first"])
        assert {k: sorted(p.id for p in v) for k, v in grouped.items() if v} == {
            "pub": ["in-a-1", "in-a-2", "in-b"]
        }
        assert uow.catalog.published_photos_by_collection([]) == {}


def test_status_enum_round_trips(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        photo = uow.photos.get("in-b")
        assert photo is not None and photo.status is Status.PUBLISHED
