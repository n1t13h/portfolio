import io
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import ExifTags, Image

from app.services.images import InvalidImage, process_jpeg
from tests.images import make_jpeg, rich_exif


def test_rejects_png_renamed_to_jpg() -> None:
    with pytest.raises(InvalidImage):
        process_jpeg(make_jpeg((100, 100), fmt="PNG"))


def test_rejects_corrupt_jpeg() -> None:
    data = make_jpeg((400, 300))
    with pytest.raises(InvalidImage):
        process_jpeg(data[: len(data) // 2])


def test_rejects_garbage_bytes() -> None:
    with pytest.raises(InvalidImage):
        process_jpeg(b"not an image at all")


def test_rejects_image_over_pixel_limit_before_decoding() -> None:
    with pytest.raises(InvalidImage, match="too large"):
        process_jpeg(make_jpeg((200, 200)), max_pixels=10_000)


def test_variants_have_expected_long_edges() -> None:
    result = process_jpeg(make_jpeg((3000, 2000)))
    assert set(result.variants) == {800, 1600, 2400}
    for edge, data in result.variants.items():
        with Image.open(io.BytesIO(data)) as img:
            assert img.format == "WEBP"
            assert max(img.size) == edge
    with Image.open(io.BytesIO(result.download_jpeg)) as dl:
        assert dl.format == "JPEG"
        assert max(dl.size) == 2400


def test_small_image_is_not_upscaled() -> None:
    result = process_jpeg(make_jpeg((500, 300)))
    for data in result.variants.values():
        with Image.open(io.BytesIO(data)) as img:
            assert img.size == (500, 300)


def test_aspect_ratio_of_portrait_image() -> None:
    assert process_jpeg(make_jpeg((2000, 3000))).aspect_ratio == 0.667


def test_exif_orientation_is_applied_to_outputs_and_ratio() -> None:
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 6  # rotate 90° on display
    result = process_jpeg(make_jpeg((3000, 2000), exif=exif))
    assert result.aspect_ratio == 0.667
    with Image.open(io.BytesIO(result.variants[800])) as img:
        assert img.size[1] == 800


def test_exif_fields_extracted() -> None:
    result = process_jpeg(make_jpeg(exif=rich_exif()))
    assert result.exif == {
        "camera": "Sony ZV-E10",
        "focal_length": 38.0,
        "aperture": 3.6,
        "shutter": "1/250",
        "iso": 640,
    }
    assert result.taken_at is not None
    assert (result.taken_at.year, result.taken_at.month, result.taken_at.day) == (2024, 3, 5)


def test_missing_exif_gives_empty_fields() -> None:
    result = process_jpeg(make_jpeg())
    assert result.exif == {}
    assert result.taken_at is None


def test_gps_stripped_from_all_outputs() -> None:
    result = process_jpeg(make_jpeg(exif=rich_exif()))
    outputs = [*result.variants.values(), result.download_jpeg]
    for data in outputs:
        with Image.open(io.BytesIO(data)) as img:
            assert not img.getexif().get_ifd(ExifTags.IFD.GPSInfo)
            assert len(img.getexif()) == 0


def make_mpo(size: tuple[int, int] = (400, 300)) -> bytes:
    """A multi-picture JPEG, as many phones write for portrait/depth shots."""
    buf = io.BytesIO()
    first, second = Image.new("RGB", size, (10, 90, 160)), Image.new("RGB", size, (200, 30, 30))
    first.save(buf, "MPO", save_all=True, append_images=[second])
    return buf.getvalue()


def test_accepts_multi_picture_jpeg_from_phones() -> None:
    data = make_mpo()
    assert data.startswith(b"\xff\xd8\xff")
    with Image.open(io.BytesIO(data)) as probe:
        assert probe.format == "MPO"  # Pillow's name for it; it is still a JPEG file

    result = process_jpeg(data)

    assert result.aspect_ratio == 1.333
    with Image.open(io.BytesIO(result.download_jpeg)) as out:
        assert out.format == "JPEG" and out.size == (400, 300)


def test_large_photo_does_not_need_a_gigabyte(tmp_path: Path) -> None:
    """A 60 MP JPEG used ~820 MB when decoded in full; the server has 512 MB-1 GB."""
    src = tmp_path / "big.jpg"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from PIL import Image; import sys;"
            "Image.new('RGB',(9000,6700),(90,120,60)).save(sys.argv[1],'JPEG',quality=70)",
            str(src),
        ],
        check=True,
    )
    probe = (
        "import resource, sys\n"
        "from app.services.images import process_jpeg\n"
        "data = open(sys.argv[1], 'rb').read()\n"
        "before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "process_jpeg(data)\n"
        "after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "print(after - before)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe, str(src)],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
    )
    unit = 1 if sys.platform == "darwin" else 1024  # ru_maxrss is bytes on macOS, KB on Linux
    growth_mb = int(out.stdout) * unit / 1_000_000
    assert growth_mb < 350, f"decoding grew memory by {growth_mb:.0f} MB"
