"""Repository contract: the same behaviour from the SQL repository and the in-memory fake."""

from app.models import Status
from app.uow import AbstractUnitOfWork
from tests.support.builders import at, make_chapter, make_collection, make_photo


def save(uow: AbstractUnitOfWork, *photos: object) -> None:
    with uow:
        for photo in photos:
            uow.photos.add(photo)  # type: ignore[arg-type]
        uow.commit()


def test_a_saved_photo_can_be_fetched_and_unknown_ids_are_none(uow: AbstractUnitOfWork) -> None:
    save(uow, make_photo("p1", title="Ghat"))
    with uow:
        photo = uow.photos.get("p1")
        assert photo is not None and photo.title == "Ghat"
        assert uow.photos.get("nope") is None


def test_new_photos_get_the_database_defaults(uow: AbstractUnitOfWork) -> None:
    save(uow, make_photo("p1"))
    with uow:
        photo = uow.photos.get("p1")
        assert photo is not None
        assert photo.status is Status.DRAFT
        assert photo.allow_download is False
        assert photo.exif == {} and photo.variant_keys == {}
        assert photo.created_at is not None


def test_list_ordered_uses_sort_position_then_creation_time_then_id(
    uow: AbstractUnitOfWork,
) -> None:
    save(
        uow,
        make_photo("c", sort_position=1, created_at=at(2)),
        make_photo("b", sort_position=0, created_at=at(5)),
        make_photo("a", sort_position=0, created_at=at(1)),
        make_photo("d", sort_position=1, created_at=at(2)),
    )
    with uow:
        assert [p.id for p in uow.photos.list_ordered()] == ["a", "b", "c", "d"]


def test_get_many_returns_only_the_photos_that_exist(uow: AbstractUnitOfWork) -> None:
    save(uow, make_photo("p1"), make_photo("p2"))
    with uow:
        assert {p.id for p in uow.photos.get_many(["p1", "ghost", "p2"])} == {"p1", "p2"}
        assert uow.photos.get_many([]) == []


def test_next_sort_position_is_one_past_the_highest(uow: AbstractUnitOfWork) -> None:
    with uow:
        assert uow.photos.next_sort_position() == 0
    save(uow, make_photo("a", sort_position=4), make_photo("b", sort_position=2))
    with uow:
        assert uow.photos.next_sort_position() == 5


def test_delete_removes_the_photo(uow: AbstractUnitOfWork) -> None:
    save(uow, make_photo("p1"))
    with uow:
        photo = uow.photos.get("p1")
        assert photo is not None
        uow.photos.delete(photo)
        uow.commit()
    with uow:
        assert uow.photos.get("p1") is None


def test_unsplash_id_map_lists_only_imported_photos(uow: AbstractUnitOfWork) -> None:
    save(
        uow,
        make_photo("p1", unsplash_id="u1"),
        make_photo("p2"),
        make_photo("p3", unsplash_id="u3"),
    )
    with uow:
        assert uow.photos.unsplash_id_map() == {"u1": "p1", "u3": "p3"}


def _chapters(uow: AbstractUnitOfWork) -> None:
    with uow:
        uow.collections.add(make_collection("col1"))
        uow.collections.add(make_collection("col2", slug="two"))
        uow.collections.add_chapter(make_chapter("ch1", "col1"))
        uow.collections.add_chapter(make_chapter("ch2", "col1", position=1))
        uow.collections.add_chapter(make_chapter("ch3", "col2"))
        uow.commit()


def test_photos_in_a_chapter_come_back_in_display_order(uow: AbstractUnitOfWork) -> None:
    _chapters(uow)
    save(
        uow,
        make_photo("a", chapter_id="ch1", position_in_chapter=2),
        make_photo("b", chapter_id="ch1", position_in_chapter=0),
        make_photo("c", chapter_id="ch1", position_in_chapter=1),
        make_photo("x", chapter_id="ch2", position_in_chapter=0),
        make_photo("loose"),
    )
    with uow:
        assert [p.id for p in uow.photos.list_in_chapter("ch1")] == ["b", "c", "a"]
        assert uow.photos.ids_by_chapter(["ch1", "ch2", "ch3"]) == {
            "ch1": ["b", "c", "a"],
            "ch2": ["x"],
            "ch3": [],
        }
        assert uow.photos.ids_by_chapter([]) == {}


def test_ids_in_collection_spans_all_its_chapters(uow: AbstractUnitOfWork) -> None:
    _chapters(uow)
    save(
        uow,
        make_photo("a", chapter_id="ch1"),
        make_photo("b", chapter_id="ch2"),
        make_photo("c", chapter_id="ch3"),
        make_photo("loose"),
    )
    with uow:
        assert uow.photos.ids_in_collection("col1") == {"a", "b"}
        assert uow.photos.ids_in_collection("col2") == {"c"}


def test_next_position_in_chapter(uow: AbstractUnitOfWork) -> None:
    _chapters(uow)
    save(uow, make_photo("a", chapter_id="ch1", position_in_chapter=3))
    with uow:
        assert uow.photos.next_position_in_chapter("ch1") == 4
        assert uow.photos.next_position_in_chapter("ch2") == 0


def test_unassigning_chapters_frees_their_photos_and_leaves_the_rest(
    uow: AbstractUnitOfWork,
) -> None:
    _chapters(uow)
    save(
        uow,
        make_photo("a", chapter_id="ch1"),
        make_photo("b", chapter_id="ch2"),
        make_photo("c", chapter_id="ch3"),
    )
    with uow:
        uow.photos.unassign_from_chapters(["ch1", "ch2"])
        uow.commit()
    with uow:
        assert [uow.photos.get(i).chapter_id for i in "abc"] == [None, None, "ch3"]  # type: ignore[union-attr]
        uow.photos.unassign_from_chapters([])  # nothing to do, and no error


def test_changes_are_discarded_unless_committed(uow: AbstractUnitOfWork) -> None:
    save(uow, make_photo("keep", title="before"))
    with uow:
        uow.photos.add(make_photo("ghost"))
        edited = uow.photos.get("keep")
        assert edited is not None
        edited.title = "after"
        # no commit: leaving the block must undo both
    with uow:
        assert uow.photos.get("ghost") is None
        kept = uow.photos.get("keep")
        assert kept is not None and kept.title == "before"


def test_an_exception_inside_the_block_discards_the_changes(uow: AbstractUnitOfWork) -> None:
    try:
        with uow:
            uow.photos.add(make_photo("half-done"))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    with uow:
        assert uow.photos.get("half-done") is None
