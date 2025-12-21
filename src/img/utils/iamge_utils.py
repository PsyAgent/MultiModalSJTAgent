from __future__ import annotations

from PIL import Image
from PIL import ImageOps


def make_sequence(
    image_list: list,
    border_width=10,
    border_color='white',
) -> Image:
    """
    Concatenate images horizontally.

    Parameters:
    -----------
    image_list: list
        A list of images to concatenate.
    border_width: int
        The width of the border.
    border_color: str
        The color of the border.

    Returns:
    --------
    new_im: Image
        The concatenated image.
    """
    bordered_images = [
        ImageOps.expand(im, border=border_width, fill=border_color) for im in image_list
    ]

    total_width = sum(im.width for im in bordered_images)
    max_height = max(im.height for im in bordered_images)

    new_im = Image.new('RGBA', (total_width, max_height), border_color)

    x_offset = 0
    for im in bordered_images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.width

    return new_im
