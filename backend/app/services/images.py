"""Turns an uploaded JPEG into public WebP variants, a download copy and metadata."""

import io
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

from app.core.errors import InvalidRequest

VARIANT_EDGES = (800, 1600, 2400)
DOWNLOAD_EDGE = 2400
WEBP_QUALITY = 82
JPEG_QUALITY = 88


class InvalidImage(InvalidRequest):
    """The upload is not a usable JPEG."""


@dataclass(frozen=True)
class ProcessedImage:
    aspect_ratio: float
    exif: dict[str, Any]
    taken_at: datetime | None
    variants: dict[int, bytes] = field(repr=False)  # long edge -> WebP bytes
    download_jpeg: bytes = field(repr=False)


def process_jpeg(data: bytes, *, max_pixels: int) -> ProcessedImage:
    img = _open_verified_jpeg(data, max_pixels)
    exif = img.getexif()  # read before the transpose below drops the orientation tag
    camera_info, taken_at = _read_exif(exif)
    icc = img.info.get("icc_profile")
    orientation = exif.get(ExifTags.Base.Orientation, 1)

    # Ratio from the file's real dimensions: the reduced-size decode below rounds them.
    width, height = img.size
    if orientation in (5, 6, 7, 8):  # displayed rotated by 90 degrees
        width, height = height, width
    aspect_ratio = round(width / height, 3)

    img = _decode_reduced(img)
    if orientation != 1:
        img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    variants = {
        edge: _encode(_fit(img, edge), "WEBP", icc, quality=WEBP_QUALITY) for edge in VARIANT_EDGES
    }
    download = _encode(_fit(img, DOWNLOAD_EDGE), "JPEG", icc, quality=JPEG_QUALITY, optimize=True)
    return ProcessedImage(aspect_ratio, camera_info, taken_at, variants, download)


def _open_verified_jpeg(data: bytes, max_pixels: int) -> Image.Image:
    """Open without decoding pixels yet; reject anything that is not a JPEG or is too big."""
    try:
        img = Image.open(io.BytesIO(data))
        # Phones often write multi-picture files, which Pillow names "MPO"; they are JPEGs too.
        if img.format not in ("JPEG", "MPO"):
            raise InvalidImage("not a JPEG")
        if img.width * img.height > max_pixels:
            raise InvalidImage("image too large")
    except InvalidImage:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise InvalidImage(f"unreadable image: {exc}") from exc
    return img


def _decode_reduced(img: Image.Image) -> Image.Image:
    """Decode the pixels, letting the JPEG decoder shrink by 2/4/8 when we need less than full size.

    The largest output is 2400 px, so a 60 MP photo never needs to exist in memory at full size.
    """
    try:
        img.draft("RGB", (DOWNLOAD_EDGE, DOWNLOAD_EDGE))
        img.load()
    except (OSError, SyntaxError) as exc:
        raise InvalidImage(f"unreadable image: {exc}") from exc
    return img


def _fit(img: Image.Image, edge: int) -> Image.Image:
    """Scale so the long edge is `edge`; never upscale."""
    if max(img.size) <= edge:
        return img
    return ImageOps.contain(img, (edge, edge), Image.Resampling.LANCZOS)


def _encode(img: Image.Image, fmt: str, icc: bytes | None, **options: Any) -> bytes:
    buf = io.BytesIO()
    # No exif= argument: GPS and camera details never reach a public file.
    img.save(buf, fmt, icc_profile=icc, **options)
    return buf.getvalue()


def _read_exif(exif: Image.Exif) -> tuple[dict[str, Any], datetime | None]:
    sub = exif.get_ifd(ExifTags.IFD.Exif)
    found: dict[str, Any] = {}

    make, model = exif.get(ExifTags.Base.Make), exif.get(ExifTags.Base.Model)
    if model:
        found["camera"] = (
            model if (not make or str(model).startswith(str(make))) else f"{make} {model}"
        )
    if (focal := sub.get(ExifTags.Base.FocalLength)) is not None:
        found["focal_length"] = round(float(focal), 1)
    if (fnum := sub.get(ExifTags.Base.FNumber)) is not None:
        found["aperture"] = round(float(fnum), 1)
    if (exposure := sub.get(ExifTags.Base.ExposureTime)) is not None:
        found["shutter"] = _format_shutter(float(exposure))
    if (iso := sub.get(ExifTags.Base.ISOSpeedRatings)) is not None:
        found["iso"] = int(iso[0] if isinstance(iso, tuple) else iso)

    return found, _parse_taken_at(sub.get(ExifTags.Base.DateTimeOriginal))


def _format_shutter(seconds: float) -> str:
    return f"1/{round(1 / seconds)}" if 0 < seconds < 1 else f"{seconds:g}"


def _parse_taken_at(raw: object) -> datetime | None:
    try:
        return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None
