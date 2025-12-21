from PIL import Image, ImageDraw, ImageFont

def number_images(
    images,
    font_size=36,
    prefix="",
    font_path=None,              # 可选：传入你自己的 .ttf/.otf
    text_color="white",
    outline_color="black",
    add_bar=True,               # 顶部加一条条幅提升对比度
    bar_opacity=160             # 条幅不透明度（0-255）
):
    """
    给每张图顶部加编号（从 0 开始），可选前缀和自适应字号/描边。

    Args:
        images (list[PIL.Image.Image])
        font_size (int): 字号
        prefix (str): 例如 'img'，会渲染成 'img-0'
        font_path (str|None): 指定字体路径（推荐）
        text_color, outline_color: 文字颜色与描边颜色
        add_bar (bool): 是否在顶部留白处绘制一条（半透明）色条以提升可读性
        bar_opacity (int): 色条不透明度（0~255）
    Returns:
        list[PIL.Image.Image]
    """

    # 1) 准备字体：优先用户字体；否则尝试常见字体；最后退回默认但给出提示
    def _load_font(size):
        tried = []
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception as e:
                tried.append(font_path)
        # 常见可用字体（不同平台）
        candidates = [
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial.ttf",
            "Arial.ttf",
            "NotoSans-Regular.ttf",
        ]
        for c in candidates:
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                tried.append(c)
                continue
        return ImageFont.load_default()

    font = _load_font(font_size)
    uses_bitmap_fallback = isinstance(font, ImageFont.ImageFont) and not hasattr(font, "getmask2")

    numbered_images = []
    for i, img in enumerate(images):
        # 2) 计算顶部预留高度（与字号相关）
        padding = int(font_size * 1.4)

        # 3) 统一处理模式，保留透明通道则用 RGBA
        has_alpha = img.mode in ("LA", "RGBA") or ("A" in img.getbands())
        base_mode = "RGBA" if has_alpha else "RGB"
        if img.mode != base_mode:
            work_img = img.convert(base_mode)
        else:
            work_img = img

        # 背景
        if base_mode == "RGBA":
            background = (255, 255, 255, 0)
        else:
            background = (255, 255, 255)

        # 4) 画布加高
        new_img = Image.new(base_mode, (work_img.width, work_img.height + padding), background)
        new_img.paste(work_img, (0, padding))

        draw = ImageDraw.Draw(new_img)

        # 5) 文字内容（prefix 为空时不加连字符）
        text = f"{prefix}{i}" if prefix else f"{i}"

        # 6) 计算文字尺寸（优先 textbbox）
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            try:
                text_w, text_h = font.getsize(text)
            except Exception:
                # 极端兜底估算
                text_w = int(len(text) * font_size * 0.6)
                text_h = font_size

        # 7) 顶部条：提升对比度（可选）
        if add_bar:
            if base_mode == "RGBA":
                bar_fill = (0, 0, 0, bar_opacity)
            else:
                # 无透明时用深灰色条
                bar_fill = (30, 30, 30)
            draw.rectangle([(0, 0), (new_img.width, padding)], fill=bar_fill)

        # 8) 文字位置（置中）
        x = (new_img.width - text_w) // 2
        y = (padding - text_h) // 2

        # 9) 描边宽度随字号自适应
        outline_w = max(1, font_size // 12)
        # 若退回位图字体（不可缩放），适当加粗描边
        if uses_bitmap_fallback:
            outline_w = max(outline_w, 2)

        # 10) 绘制描边（简单 8 邻域）
        for dx in range(-outline_w, outline_w + 1):
            for dy in range(-outline_w, outline_w + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

        # 11) 正文
        draw.text((x, y), text, font=font, fill=text_color)

        numbered_images.append(new_img)

    return numbered_images