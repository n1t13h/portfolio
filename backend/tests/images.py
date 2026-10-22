"""JPEG builders shared by image and upload tests."""

import io

from PIL import ExifTags, Image


def make_jpeg(
    size: tuple[int, int] = (3000, 2000), *, exif: Image.Exif | None = None, fmt: str = "JPEG"
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 80, 40)).save(buf, fmt, **({"exif": exif} if exif else {}))
    return buf.getvalue()


def rich_exif() -> Image.Exif:
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "Sony"
    exif[ExifTags.Base.Model] = "ZV-E10"
    exif.get_ifd(ExifTags.IFD.Exif).update(
        {
            ExifTags.Base.FocalLength: 38.0,
            ExifTags.Base.FNumber: 3.6,
            ExifTags.Base.ExposureTime: 1 / 250,
            ExifTags.Base.ISOSpeedRatings: 640,
            ExifTags.Base.DateTimeOriginal: "2024:03:05 14:22:10",
        }
    )
    exif.get_ifd(ExifTags.IFD.GPSInfo).update(
        {
            ExifTags.GPS.GPSLatitudeRef: "N",
            ExifTags.GPS.GPSLatitude: (23.0, 10.0, 30.0),
            ExifTags.GPS.GPSLongitudeRef: "E",
            ExifTags.GPS.GPSLongitude: (75.0, 46.0, 12.0),
        }
    )
    return exif
