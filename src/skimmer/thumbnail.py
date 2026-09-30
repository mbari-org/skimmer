"""JPEG thumbnail decoding and rendering."""

from io import BytesIO

from PIL import Image

# Modes JPEG can encode directly; anything else is converted first
_JPEG_MODES = ("RGB", "L")


def decode_for_thumbnail(data: bytes, max_edge: int) -> Image.Image:
    """
    Decode image bytes for thumbnailing, as cheaply as the format allows.

    For JPEG sources, draft mode lets libjpeg decode directly at a reduced
    scale (1/2, 1/4, 1/8), which is much faster and lighter on memory than a
    full-resolution decode. Other formats are decoded normally.

    Args:
        data (bytes): The encoded source image.
        max_edge (int): The longest edge of the intended thumbnail in pixels.

    Returns:
        Image.Image: The decoded image, at least max_edge on its longest side
        (unless the source is smaller).
    """
    with BytesIO(data) as buffer:
        image = Image.open(buffer)
        # No-op for non-JPEG formats
        image.draft("RGB", (max_edge, max_edge))
        image.load()
    return image


def render_thumbnail(image: Image.Image, max_edge: int, quality: int) -> bytes:
    """
    Downscale an image to fit within max_edge and encode it as JPEG.

    Preserves aspect ratio and never upscales. Does not modify the input, so
    it is safe to pass a cached image.

    Args:
        image (Image.Image): The source image.
        max_edge (int): The longest edge of the thumbnail in pixels.
        quality (int): The JPEG quality (1-95).

    Returns:
        bytes: The JPEG-encoded thumbnail.
    """
    if image.mode not in _JPEG_MODES:
        image = image.convert("L" if image.mode in ("LA", "1") else "RGB")

    width, height = image.size
    scale = min(1.0, max_edge / max(width, height))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    if size != image.size:
        # reducing_gap does a fast integer-factor reduce before the Lanczos pass
        image = image.resize(size, Image.Resampling.LANCZOS, reducing_gap=3.0)

    with BytesIO() as buffer:
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()


__all__ = ["decode_for_thumbnail", "render_thumbnail"]
