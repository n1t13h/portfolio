"""CatalogService (what visitors see) against the in-memory unit of work."""

import pytest

from app.core.errors import NotFound
from app.integrations.storage import Bucket
from app.models import Photo
from app.services.catalog import CatalogService
from tests.fakes import FakeStorage, FakeUnitOfWork
from tests.support.builders import make_chapter, make_collection, make_photo, published


@pytest.fixture
def service(fake_uow: FakeUnitOfWork, storage: FakeStorage) -> CatalogService:
    return CatalogService(lambda: fake_uow, storage)


def photo(pid: str, **kw: object) -> Photo:
    return make_photo(
        pid,
        variant_keys={"800": f"photos/{pid}/800.webp", "1600": f"photos/{pid}/1600.webp"},
        download_key=f"downloads/{pid}.jpg",
        original_key=f"originals/{pid}.jpg",
        **kw,
    )


def seed(uow: FakeUnitOfWork) -> None:
    """goa (published): chapters a, b; hidden (draft): chapter h; plus loose photos."""
    with uow as work:
        work.collections.add(
            make_collection(
                "goa",
                slug="goa",
                title="Goa",
                place="India",
                year="2024",
                intro="Rain",
                sort_position=1,
                cover_photo_ids=["g2", "g-draft", "gone"],
                **published(),
            )
        )
        work.collections.add(make_collection("first", slug="first", sort_position=0, **published()))
        work.collections.add(make_collection("hidden", slug="hidden", sort_position=2))
        work.collections.add_chapter(
            make_chapter("b", "goa", title="Beaches", note="Sun", position=1)
        )
        work.collections.add_chapter(
            make_chapter("a", "goa", title="Arrival", note="Rain", position=0)
        )
        work.collections.add_chapter(
            make_chapter("empty", "goa", title="Nothing visible", position=2)
        )
        work.collections.add_chapter(make_chapter("h", "hidden"))
        for p in (
            photo(
                "loose",
                sort_position=0,
                exif={"camera": "Sony", "focal_length": 38.0, "iso": 640},
                **published(),
            ),
            photo("loose-draft", sort_position=1),
            photo("g2", chapter_id="a", position_in_chapter=1, sort_position=2, **published()),
            photo("g1", chapter_id="a", position_in_chapter=0, sort_position=3, **published()),
            photo("g-draft", chapter_id="a", position_in_chapter=2, sort_position=4),
            photo("g3", chapter_id="b", sort_position=5, **published(allow_download=True)),
            photo("only-draft-here", chapter_id="empty", sort_position=6),
            photo("in-hidden", chapter_id="h", sort_position=7, **published(allow_download=True)),
        ):
            work.photos.add(p)
        work.commit()


def test_the_photo_list_has_only_public_photos_in_the_admins_order(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    assert [p.id for p in service.photos()] == ["loose", "g2", "g1", "g3"]


def test_a_photo_is_described_for_the_frontend_with_cdn_urls_and_camel_case_exif(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    [loose, *_] = service.photos()
    assert loose.variants == {
        "800": "https://cdn.test/photos/loose/800.webp",
        "1600": "https://cdn.test/photos/loose/1600.webp",
    }
    assert loose.exif.model_dump(by_alias=True, exclude_none=True) == {
        "camera": "Sony",
        "focalLength": 38.0,
        "iso": 640,
    }
    assert (loose.allow_download, loose.download_url) == (False, None)


def test_a_photo_that_may_be_downloaded_points_at_the_download_route(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    g3 = next(p for p in service.photos() if p.id == "g3")
    assert (g3.allow_download, g3.download_url) == (True, "/photos/g3/download")


def test_collections_list_published_ones_in_order_with_only_visible_covers(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    listed = service.collections()
    assert [c.slug for c in listed] == ["first", "goa"]
    goa = listed[1]
    assert [p.id for p in goa.covers] == ["g2"]  # the draft and the missing id are skipped
    assert (goa.title, goa.place, goa.year, goa.intro) == ("Goa", "India", "2024", "Rain")


def test_a_collection_has_chapters_in_order_with_their_published_photos(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    goa = service.collection("goa")
    assert [(c.title, c.note, [p.id for p in c.photos]) for c in goa.chapters] == [
        ("Arrival", "Rain", ["g1", "g2"]),
        ("Beaches", "Sun", ["g3"]),
    ]  # the chapter with nothing visible is left out
    assert [p.id for p in goa.photos] == ["g1", "g2", "g3"]
    assert [p.id for p in goa.covers] == ["g2"]


@pytest.mark.parametrize("slug", ["hidden", "nope"])
def test_draft_and_unknown_collections_are_not_found(
    service: CatalogService, fake_uow: FakeUnitOfWork, slug: str
) -> None:
    seed(fake_uow)
    with pytest.raises(NotFound, match="collection"):
        service.collection(slug)


def test_nothing_private_appears_in_any_public_response(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    bodies = [
        *(p.model_dump_json(by_alias=True) for p in service.photos()),
        *(c.model_dump_json(by_alias=True) for c in service.collections()),
        service.collection("goa").model_dump_json(by_alias=True),
    ]
    for text in bodies:
        for forbidden in (
            "originals/",
            "downloads/",
            "fake-r2",
            "sortPosition",
            "status",
            "chapterId",
        ):
            assert forbidden not in text


def test_a_download_link_is_a_short_lived_private_link_to_the_download_copy(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    assert service.download_url("g3") == "https://fake-r2/private/downloads/g3.jpg?get&expires=300"


@pytest.mark.parametrize("photo_id", ["loose", "loose-draft", "in-hidden", "nope"])
def test_downloads_are_refused_when_off_for_drafts_in_draft_collections_and_unknown_ids(
    service: CatalogService, fake_uow: FakeUnitOfWork, photo_id: str
) -> None:
    seed(fake_uow)
    with pytest.raises(NotFound):
        service.download_url(photo_id)


def test_a_draft_photo_with_downloads_on_is_still_not_downloadable(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    with fake_uow as uow:
        uow.photos.add(photo("d", allow_download=True))
        uow.commit()
    with pytest.raises(NotFound):
        service.download_url("d")


def test_a_photo_without_a_download_copy_cannot_be_downloaded(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    with fake_uow as uow:
        uow.photos.add(make_photo("x", download_key=None, **published(allow_download=True)))
        uow.commit()
    with pytest.raises(NotFound):
        service.download_url("x")


def test_reading_the_catalog_never_commits(
    service: CatalogService, fake_uow: FakeUnitOfWork
) -> None:
    seed(fake_uow)
    before = fake_uow.commits
    service.photos()
    service.collections()
    service.collection("goa")
    service.download_url("g3")
    assert fake_uow.commits == before


def test_the_private_bucket_is_used_for_downloads_only(
    service: CatalogService, fake_uow: FakeUnitOfWork, storage: FakeStorage
) -> None:
    seed(fake_uow)
    service.download_url("g3")
    assert storage.objects == {} and Bucket.PRIVATE.value in service.download_url("g3")
