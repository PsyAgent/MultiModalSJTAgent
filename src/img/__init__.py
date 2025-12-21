from __future__ import annotations

from .datasets import DataManager
from .viz import draw_G, draw_Gs
from .pipeline import PicSJTAgent
from .make_ins import make_ins, combine_ins, combine_situ_ins
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image
load_dotenv()
base_path = Path(__file__).resolve().parent
ref_viz_paths = {
    'male': base_path / 'resources/ref_character/male.png',
    'female': base_path / 'resources/ref_character/female.png',
}
ref_viz = {
    gender: Image.open(path)
    for gender, path in ref_viz_paths.items()
}
__all__ = [
    "DataManager",
    "draw_G",
    "draw_Gs",
    "PicSJTAgent",
    "make_ins",
    "combine_ins",
    "combine_situ_ins",
]