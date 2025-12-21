# %%
from __future__ import annotations

import os
import os.path as op

from PIL import Image
from PIL import ImageOps

def make_sequence(image_list, border_width=10, border_color='white', vertical=False):
    """
    Concatenate images horizontally or vertically.

    Parameters:
    -----------
    image_list: list of PIL Image
        A list of images to concatenate.
    border_width: int
        The width of the border around each image.
    border_color: str or tuple
        The color of the border.
    vertical: bool
        If True, stack images vertically; otherwise, concatenate horizontally.

    Returns:
    --------
    new_im: PIL Image
        The concatenated image.
    """
    # Add border to each image
    bordered_images = [
        ImageOps.expand(im, border=border_width, fill=border_color)
        for im in image_list
    ]

    if vertical:
        # Vertical concatenation
        total_height = sum(im.height for im in bordered_images)
        max_width = max(im.width for im in bordered_images)
        new_im = Image.new('RGBA', (max_width, total_height), border_color)
        y_offset = 0
        for im in bordered_images:
            new_im.paste(im, (0, y_offset))
            y_offset += im.height
    else:
        # Horizontal concatenation
        total_width = sum(im.width for im in bordered_images)
        max_height = max(im.height for im in bordered_images)
        new_im = Image.new('RGBA', (total_width, max_height), border_color)
        x_offset = 0
        for im in bordered_images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.width

    return new_im

def load_vng_pics(trait, itemID, res_dir):
    des_dir = f'{res_dir}/{trait}/{trait}_{itemID}'
    fs = os.listdir(des_dir)
    pics = [i for i in fs if i.endswith('.png')]
    vng_order = ['E', 'I', 'Pr', 'P']
    vng_pics = {}
    for vng_type in vng_order:
        for pic in pics:
            if pic.startswith(vng_type + '.'):
                vng_pics[vng_type] = Image.open(op.join(des_dir, pic))
                break

    return vng_pics