"""Repository contract for collections and chapters (SQL and in-memory fake)."""

from app.uow import AbstractUnitOfWork
from tests.support.builders import make_chapter, make_collection, make_photo


def seed(uow: AbstractUnitOfWork) -> None:
    with uow:
        uow.collections.add(make_collection("c2", slug="two", sort_position=1))
        uow.collections.add(make_collection("c1", slug="one", sort_position=0))
        uow.collections.add_chapter(make_chapter("ch2", "c1", position=1))
        uow.collections.add_chapter(make_chapter("ch1", "c1", position=0))
        uow.collections.add_chapter(make_chapter("ch3", "c2"))
        uow.commit()


def test_collections_come_back_in_the_admins_order(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        assert [c.id for c in uow.collections.list_ordered()] == ["c1", "c2"]


def test_get_and_slug_owner(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        found = uow.collections.get("c1")
        assert found is not None and found.slug == "one"
        assert uow.collections.get("nope") is None
        assert uow.collections.slug_owner("two") == "c2"
        assert uow.collections.slug_owner("free") is None


def test_new_collections_default_to_draft_with_no_covers(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        c = uow.collections.get("c1")
        assert c is not None
        assert c.status.value == "draft"
        assert c.cover_photo_ids == []
        assert (c.place, c.year, c.intro) == ("", "", "")


def test_next_positions_start_at_zero_and_follow_the_highest(uow: AbstractUnitOfWork) -> None:
    with uow:
        assert uow.collections.next_sort_position() == 0
        assert uow.collections.next_chapter_position("c1") == 0
    seed(uow)
    with uow:
        assert uow.collections.next_sort_position() == 2
        assert uow.collections.next_chapter_position("c1") == 2
        assert uow.collections.next_chapter_position("c2") == 1


def test_chapters_are_listed_in_display_order_including_empty_collections(
    uow: AbstractUnitOfWork,
) -> None:
    seed(uow)
    with uow:
        assert [c.id for c in uow.collections.list_chapters("c1")] == ["ch1", "ch2"]
        grouped = uow.collections.chapters_by_collection(["c1", "c2", "ghost"])
        assert {k: [c.id for c in v] for k, v in grouped.items()} == {
            "c1": ["ch1", "ch2"],
            "c2": ["ch3"],
            "ghost": [],
        }
        assert uow.collections.chapters_by_collection([]) == {}


def test_get_chapter_and_collection_ids_of_chapters(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        chapter = uow.collections.get_chapter("ch3")
        assert chapter is not None and chapter.collection_id == "c2"
        assert uow.collections.get_chapter("nope") is None
        assert uow.collections.collection_ids_of_chapters(["ch1", "ch3"]) == {"c1", "c2"}
        assert uow.collections.collection_ids_of_chapters([]) == set()


def test_deleting_a_chapter_frees_its_photos(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        uow.photos.add(make_photo("p1", chapter_id="ch1"))
        uow.commit()
    with uow:
        chapter = uow.collections.get_chapter("ch1")
        assert chapter is not None
        uow.collections.delete_chapter(chapter)
        uow.commit()
    with uow:
        assert uow.collections.get_chapter("ch1") is None
        photo = uow.photos.get("p1")
        assert photo is not None and photo.chapter_id is None


def test_deleting_a_collection_removes_its_chapters_but_not_its_photos(
    uow: AbstractUnitOfWork,
) -> None:
    seed(uow)
    with uow:
        uow.photos.add(make_photo("p1", chapter_id="ch1"))
        uow.commit()
    with uow:
        collection = uow.collections.get("c1")
        assert collection is not None
        uow.collections.delete(collection)
        uow.commit()
    with uow:
        assert uow.collections.get("c1") is None
        assert uow.collections.get_chapter("ch1") is None
        assert uow.collections.get_chapter("ch2") is None
        assert uow.collections.get_chapter("ch3") is not None  # another collection's chapter
        photo = uow.photos.get("p1")
        assert photo is not None and photo.chapter_id is None


def test_a_collection_loads_with_its_chapters_and_their_photos_in_display_order(
    uow: AbstractUnitOfWork,
) -> None:
    """Both implementations must hand back rows ready to turn into models with model_validate."""
    seed(uow)
    with uow:
        uow.photos.add(make_photo("late", chapter_id="ch1", position_in_chapter=2))
        uow.photos.add(make_photo("early", chapter_id="ch1", position_in_chapter=0))
        uow.photos.add(make_photo("tie-b", chapter_id="ch1", position_in_chapter=1))
        uow.photos.add(make_photo("tie-a", chapter_id="ch1", position_in_chapter=1))
        uow.commit()
    with uow:
        collection = uow.collections.get("c1")
        assert collection is not None
        assert [ch.id for ch in collection.chapters] == ["ch1", "ch2"]
        assert [p.id for p in collection.chapters[0].photos] == ["early", "tie-a", "tie-b", "late"]
        assert collection.chapters[0].photo_ids == ["early", "tie-a", "tie-b", "late"]
        assert collection.chapters[1].photo_ids == []

        everything = {c.id: [ch.id for ch in c.chapters] for c in uow.collections.list_ordered()}
        assert everything == {"c1": ["ch1", "ch2"], "c2": ["ch3"]}

        chapter = uow.collections.get_chapter("ch1")
        assert chapter is not None and chapter.photo_ids == ["early", "tie-a", "tie-b", "late"]


def test_rereading_after_photos_move_shows_the_new_membership(uow: AbstractUnitOfWork) -> None:
    seed(uow)
    with uow:
        uow.photos.add(make_photo("p1", chapter_id="ch1"))
        uow.commit()
    with uow:
        photo = uow.photos.get("p1")
        assert photo is not None
        photo.chapter_id = "ch2"
        uow.commit()
        first, second = uow.collections.get_chapter("ch1"), uow.collections.get_chapter("ch2")
        assert first is not None and second is not None
        assert (first.photo_ids, second.photo_ids) == ([], ["p1"])
