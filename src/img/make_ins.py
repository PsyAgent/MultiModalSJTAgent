# We'll implement make_ins as requested and demo it with the provided screenshot
# found at /mnt/data/截屏2025-10-08 22.43.25.png

from PIL import Image, ImageDraw, ImageFont
import re
import textwrap
from pathlib import Path
import os
DEFAULT_FONT_PATH = str((Path(__file__).resolve().parent / "annotator" / "No.384-ShangShouTuanYuanTi-2.ttf").resolve())
def _get_font(size=20, preferred=None):
    """
    Try to load a font that can render CJK if available.
    If `preferred` is given and exists, use it.
    Falls back to a basic PIL font.
    """
    cand_paths = []
    if preferred:
        cand_paths.append(preferred)
    # Common CJK-capable fonts (paths vary by system; this is best-effort)
    cand_paths += [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",
        "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # latin only but decent fallback
    ]
    for p in cand_paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()

def _wrap_text_by_width(text, draw, font, max_width):
    """
    Wrap text so that each line fits within max_width using the given draw+font.
    Returns list of lines.
    """
    # Fast path for very short strings
    if not text:
        return []
    # We'll do greedy wrapping by increasing length until exceeding width
    lines = []
    buf = ""
    for ch in text:
        test = buf + ch
        w = draw.textlength(test, font=font)
        if w <= max_width or not buf:
            buf = test
        else:
            lines.append(buf)
            buf = ch
    if buf:
        lines.append(buf)
    # Collapse overly long sequences by splitting at whitespace punctuation when possible
    normalized = []
    for line in lines:
        # Further split long lines using textwrap if they still exceed width (for long tokens)
        if draw.textlength(line, font=font) <= max_width:
            normalized.append(line)
        else:
            # fallback: chop by characters
            tmp = ""
            for ch in line:
                if draw.textlength(tmp + ch, font=font) <= max_width or not tmp:
                    tmp += ch
                else:
                    normalized.append(tmp)
                    tmp = ch
            if tmp:
                normalized.append(tmp)
    return normalized

def make_ins(
    s: str, 
    *, 
    column_width=420, 
    image_target_height=220, 
    padding=24, 
    margin=24, 
    bg_color=(255,255,255), 
    font_path=DEFAULT_FONT_PATH, 
    font_size=22,
    image_position='center',
    text_align='center'
    ) -> Image.Image:
    """
    Parse string with one image path enclosed in { } and render a composite image:
    [left text]  [image]  [right text].
    
    Args:
        s: Text with image path in {path}
        column_width: Width of text columns
        image_target_height: Target height for image
        padding: Space between elements
        margin: Canvas margin
        bg_color: Background color
        font_path: Path to font file
        font_size: Font size
        image_position: 'left', 'center', or 'right'
        text_align: 'left', 'right', 'center', or 'towards_image'
    
    Returns a PIL.Image.
    """
    # 1) Extract image path
    m = re.search(r"\{([^}]+)\}", s)
    if not m:
        raise ValueError("No image path found in braces like {path/to.png}.")
    img_path = m.group(1).strip()
    left_text = s[:m.start()]
    right_text = s[m.end():]

    # 2) Load and scale the image
    img = Image.open(img_path).convert("RGBA")
    scale = image_target_height / img.height
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # 3) Prepare fonts and drawing
    # We'll create a temp canvas just to measure text
    temp = Image.new("RGB", (10,10), bg_color)
    draw = ImageDraw.Draw(temp)
    font = _get_font(font_size, preferred=font_path)

    # 4) Wrap text for two columns
    left_lines  = _wrap_text_by_width(left_text, draw, font, column_width)
    right_lines = _wrap_text_by_width(right_text, draw, font, column_width)

    # 5) Compute heights
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (font_size, 0)
    line_h = ascent + descent + 4
    left_h  = max(0, len(left_lines)  * line_h)
    right_h = max(0, len(right_lines) * line_h)
    col_h = max(left_h, right_h, new_h)

    # 6) Canvas size based on image position
    if image_position == 'center':
        canvas_w = margin*2 + column_width + padding + new_w + padding + column_width
    elif image_position == 'left':
        canvas_w = margin*2 + new_w + padding + column_width
    else:
        canvas_w = margin*2 + column_width + padding + new_w
    canvas_h = margin*2 + col_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    d = ImageDraw.Draw(canvas)

    # 7) Y-coordinates for vertical centering
    left_y  = margin + (col_h - left_h)  // 2
    img_y   = margin + (col_h - new_h)   // 2
    right_y = margin + (col_h - right_h) // 2

    # 8) X coordinates based on image position
    if image_position == 'left':
        img_x = margin
        left_x = None
        right_x = margin + new_w + padding
    elif image_position == 'right':
        left_x = margin
        img_x = margin + column_width + padding
        right_x = None
    else:
        left_x = margin
        img_x = margin + column_width + padding
        right_x = img_x + new_w + padding

    # 9) Draw text with alignment
    if left_x is not None and left_lines:
        y = left_y
        left_space_width = column_width
        if image_position == 'center' and text_align == 'towards_image':
            for line in left_lines:
                line_w = draw.textlength(line, font=font)
                x = left_x + (left_space_width - line_w)
                d.text((x, y), line, fill=(0,0,0), font=font)
                y += line_h
        elif text_align == 'right' or (image_position == 'left' and text_align == 'towards_image'):
            for line in left_lines:
                line_w = draw.textlength(line, font=font)
                x = left_x + (left_space_width - line_w)
                d.text((x, y), line, fill=(0,0,0), font=font)
                y += line_h
        elif text_align == 'center':
            for line in left_lines:
                line_w = draw.textlength(line, font=font)
                x = left_x + (left_space_width - line_w) // 2
                d.text((x, y), line, fill=(0,0,0), font=font)
                y += line_h
        else:
            for line in left_lines:
                d.text((left_x, y), line, fill=(0,0,0), font=font)
                y += line_h

    if right_x is not None and right_lines:
        y = right_y
        right_space_width = column_width
        if image_position == 'center' and text_align == 'towards_image':
            for line in right_lines:
                d.text((right_x, y), line, fill=(0,0,0), font=font)
                y += line_h
        elif text_align == 'right' or (image_position == 'left' and text_align == 'towards_image'):
            for line in right_lines:
                line_w = draw.textlength(line, font=font)
                x = right_x + (right_space_width - line_w)
                d.text((x, y), line, fill=(0,0,0), font=font)
                y += line_h
        elif text_align == 'center':
            for line in right_lines:
                line_w = draw.textlength(line, font=font)
                x = right_x + (right_space_width - line_w) // 2
                d.text((x, y), line, fill=(0,0,0), font=font)
                y += line_h
        else:
            for line in right_lines:
                d.text((right_x, y), line, fill=(0,0,0), font=font)
                y += line_h

    # 10) Paste image (handle alpha)
    canvas.paste(img, (img_x, img_y), img)

    return canvas

def combine_ins(
    ref_img_path: str,
    sjt_img_path: str,
    loc: str = "lower",  # "upper" -> img_ins above original, "lower" -> img_ins below (default)
) -> Image.Image:
    picsitu = Image.open(sjt_img_path)
    img_ins = make_ins(
        f"如果你是{{{ref_img_path}}}, 你会怎么做？",
        column_width=1044,
        image_target_height=250,
        font_size=90,
        padding=34,
        margin=10,
        image_position='center',
        text_align='towards_image'
    )
    img1 = picsitu.convert("RGB")
    img2 = img_ins.convert("RGB")
    width = max(img1.width, img2.width)
    height = img1.height + img2.height
    concatted = Image.new("RGB", (width, height), (255, 255, 255))
    loc = (loc or "lower").lower()
    if loc == "upper":
        # img_ins above original image
        concatted.paste(img2, ((width - img2.width) // 2, 0))
        concatted.paste(img1, ((width - img1.width) // 2, img2.height))
    elif loc == "lower":
        # original image above, img_ins below (existing behavior)
        concatted.paste(img1, ((width - img1.width) // 2, 0))
        concatted.paste(img2, ((width - img2.width) // 2, img1.height))
    else:
        raise ValueError("loc must be 'upper' or 'lower'")

    return concatted

def combine_situ_ins(
    ref_img_path: str,
    sjt_img_path: str,
    situation: str,
    loc: str = "lower",  # "upper" -> img_ins above original, "lower" -> img_ins below (default)
) -> Image.Image:
    picsitu = Image.open(sjt_img_path)
    picsitu_width = picsitu.size[0]
    img_height = 350
    final_width = max(0, picsitu_width - img_height)
    img_ins = make_ins(
        f"{situation}如果你是右图角色, 你会怎么做?{{{ref_img_path}}}",
        column_width=final_width,
        image_target_height=img_height,
        font_size=90,
        padding=0,
        margin=0,
        image_position='right',
        text_align='left'
    )
    img1 = picsitu.convert("RGB")
    img2 = img_ins.convert("RGB")
    width = max(img1.width, img2.width)
    height = img1.height + img2.height

    concatted = Image.new("RGB", (width, height), (255, 255, 255))

    loc = (loc or "lower").lower()
    if loc == "upper":
        # img_ins above original image
        concatted.paste(img2, ((width - img2.width) // 2, 0))
        concatted.paste(img1, ((width - img1.width) // 2, img2.height))
    elif loc == "lower":
        # original image above, img_ins below (existing behavior)
        concatted.paste(img1, ((width - img1.width) // 2, 0))
        concatted.paste(img2, ((width - img2.width) // 2, img1.height))
    else:
        raise ValueError("loc must be 'upper' or 'lower'")

    return concatted