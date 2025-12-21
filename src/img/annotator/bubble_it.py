"""Speech and narration bubble renderer for annotated images.

This module provides the :class:`BubbleIt` helper that places either narration
boxes or dialogue speech bubbles on top of a frame, based on face positions and
simple scene heuristics.
"""
# %%
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Mapping, Optional, Sequence, Tuple, Union
from typing_extensions import TypedDict

from PIL import Image, ImageDraw, ImageFilter, ImageFont

__all__ = [
    "DEFAULT_BUBBLE_STYLE",
    "AnnotationPayload",
    "BubbleIt",
]
# %%
# -----------------------------------------------------------------------------
# Public configuration dictionary
# -----------------------------------------------------------------------------

DEFAULT_BUBBLE_STYLE: Dict[str, Union[int, float, Tuple[int, int, int]]] = {
    "font_size": 70,
    "max_width_ratio": 0.85,  # Increased from 0.6 to 0.85 for more text width
    "line_spacing": 1.2,
    "padding": 18,
    "margin": 30,
    "corner_radius": 18,
    "border_width": 6,
    "border_color": (255, 255, 255),
    "border_opacity": 120,
    "background_color": (255, 255, 255),
    "background_opacity": 120,
    "font_color": (15, 15, 15),
    "narration_zone_ratio": 0.32,
    "tail_width": 32,
    "tail_length": 48,
    "tail_curve_factor": 0.3,  # Controls how curved the tail is (0.0-1.0)
    "shadow_offset": 3,  # Shadow offset in pixels
    "shadow_blur": 6,    # Shadow blur radius
    "shadow_color": (0, 0, 0),  # Shadow color
    "shadow_opacity": 50,  # Shadow opacity
}


# -----------------------------------------------------------------------------
# Type definitions
# -----------------------------------------------------------------------------

class NarrationContent(TypedDict):
    text: str


class DialogueContent(TypedDict):
    face_id: int
    text: str


class AnnotationPayload(TypedDict):
    annotation_type: Literal["narration", "dialogue"]
    content: Union[NarrationContent, DialogueContent]

class AnnotationPayloadV2(TypedDict):
    """A payload containing one or two annotations.

    When two are present, one must be narration and one must be dialogue.
    """
    annotations: List[AnnotationPayload]  # length 1 or 2

    @staticmethod
    def validate(payload: "AnnotationPayloadV2") -> bool:
        if not isinstance(payload, list):
            return False
        if not (1 <= len(payload) <= 2):
            return False
        if len(payload) == 2:
            types = {ann.get("annotation_type") for ann in payload}
            return types == {"narration", "dialogue"}
        return True

FaceBoxes = Mapping[int, Sequence[float]]
Rectangle = Tuple[float, float, float, float]
ColorTuple = Tuple[int, int, int, int]


@dataclass
class CandidatePlacement:
    rect: Rectangle
    direction: Optional[Literal["left", "right", "top", "bottom"]]
    score: float
    tail_anchor: Optional[Tuple[float, float]] = None
    face_anchor: Optional[Tuple[float, float]] = None


class BubbleIt:
    """Render narration boxes or dialogue bubbles on a frame.

    Parameters
    ----------
    font_path:
        Path to a ``.ttf`` file. When ``None`` the renderer tries a set of
        common fonts and finally falls back to the default bitmap font.
    style:
        Optional dictionary to override entries from :data:`DEFAULT_BUBBLE_STYLE`.
        Supported keys: ``font_size``, ``max_width_ratio``, ``line_spacing``,
        ``padding``, ``margin``, ``corner_radius``, ``border_width``,
        ``border_color``, ``border_opacity``, ``background_color``,
        ``background_opacity``, ``font_color``, ``narration_zone_ratio``,
        ``tail_width``, ``tail_length``.
    """

    def __init__(
        self, 
        font_size=70,
        font_color=(15, 15, 15),
        bubble_color=(255, 255, 255),
        bubble_opacity=120,
        outline_color=(255, 255, 255),
        outline_width=6,
        outline_opacity=120,
        font_path: Optional[str] = None, 
        style: Optional[Dict[str, Union[int, float, Tuple[int, int, int]]]] = None
        ) -> None:
        self.font_path = font_path
        self.style: Dict[str, Union[int, float, Tuple[int, int, int]]] = {
            **DEFAULT_BUBBLE_STYLE,
            **(style or {}),
        }
        self.style["font_size"] = font_size
        self.style["font_color"] = font_color
        self.style["background_color"] = bubble_color
        self.style["background_opacity"] = bubble_opacity
        self.style["border_color"] = outline_color
        self.style["border_width"] = outline_width
        self.style["border_opacity"] = outline_opacity
        
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
        # Prebuild a dummy draw instance for measurement to avoid repeated
        # canvas allocations during wrapping.
        self._measuring_image = Image.new("L", (1, 1))
        self._measure_draw = ImageDraw.Draw(self._measuring_image)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def render(
        self,
        image: Image.Image,
        annotation: Union[AnnotationPayload, AnnotationPayloadV2],
        faces: Optional[FaceBoxes] = None,
    ) -> Image.Image:
        """Return a new image with the requested bubble rendered.

        Parameters
        ----------
        image:
            Source frame. The method keeps the original untouched and returns a
            copy with an RGBA bubble overlay applied.
        annotation:
            Dictionary describing the annotation request. Supports two formats:
            - AnnotationPayload: Single annotation
            - AnnotationPayloadV2: One or two annotations (if two, one must be narration and one dialogue)

        faces:
            Mapping from ``face_id`` to bounding boxes ``[x1, y1, x2, y2]``.
            Required for dialogue bubbles so the renderer can anchor the tail.
        """

        faces = faces or {}
        # Handle AnnotationPayloadV2
        if isinstance(annotation, list):
            return self._render_v2(image, annotation, faces)
        # Handle original AnnotationPayload
        mode = annotation.get("annotation_type")
        if mode not in {"narration", "dialogue"}:
            raise ValueError(f"Unsupported annotation_type: {mode!r}")

        base = image.convert("RGBA") if image.mode != "RGBA" else image.copy()

        if mode == "narration":
            content = annotation["content"]  # type: ignore[index]
            text = content["text"]  # type: ignore[index]
            return self._draw_narration(base, text, faces)
        else:
            content = annotation["content"]  # type: ignore[index]
            try:
                face_id = content["face_id"]  # type: ignore[index]
            except KeyError as exc:  # pragma: no cover - defensive branch
                raise ValueError("dialogue annotation requires face_id") from exc
            if face_id not in faces:
                raise ValueError(f"face_id {face_id} not found in provided faces")
            text = content["text"]  # type: ignore[index]
            return self._draw_dialogue(base, text, face_id, faces)

    def _render_v2(
        self,
        image: Image.Image,
        annotations: AnnotationPayloadV2,
        faces: FaceBoxes,
    ) -> Image.Image:
        """Handle AnnotationPayloadV2 with one or two annotations."""
        if not AnnotationPayloadV2.validate(annotations):
            raise ValueError("Invalid AnnotationPayloadV2 format")
                
        # Single annotation - use existing logic
        if len(annotations) == 1:
            return self.render(image, annotations[0], faces)
        
        # Dual annotations - handle positioning conflicts
        return self._render_dual_annotations(image, annotations, faces)
    
    def _render_dual_annotations(
        self,
        image: Image.Image,
        annotations: List[AnnotationPayload],
        faces: FaceBoxes,
    ) -> Image.Image:
        """Render two annotations (narration + dialogue) with conflict resolution."""
        # Separate narration and dialogue
        narration_ann = None
        dialogue_ann = None
        
        for ann in annotations:
            if ann["annotation_type"] == "narration":
                narration_ann = ann
            elif ann["annotation_type"] == "dialogue":
                dialogue_ann = ann
        
        if not narration_ann or not dialogue_ann:
            raise ValueError("Dual annotations must contain one narration and one dialogue")
        
        base = image.convert("RGBA") if image.mode != "RGBA" else image.copy()
        
        # Get dialogue info
        dialogue_content = dialogue_ann["content"]  # type: ignore[index]
        dialogue_face_id = dialogue_content["face_id"]  # type: ignore[index]
        dialogue_text = dialogue_content["text"]  # type: ignore[index]
        
        if dialogue_face_id not in faces:
            raise ValueError(f"face_id {dialogue_face_id} not found in provided faces")
        
        # Get narration info
        narration_content = narration_ann["content"]  # type: ignore[index]
        narration_text = narration_content["text"]  # type: ignore[index]
        
        # Calculate dialogue placement first (higher priority)
        dialogue_placement = self._calculate_dialogue_placement(
            image, dialogue_text, dialogue_face_id, faces
        )
        
        # Calculate narration placement avoiding dialogue area
        narration_placement = self._calculate_narration_placement_with_avoidance(
            image, narration_text, faces, dialogue_placement.rect
        )
        
        # Create overlay for both bubbles
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        
        # Render narration first (background layer)
        self._render_narration_on_overlay(overlay, narration_text, narration_placement)
        
        # Render dialogue on top (foreground layer)
        self._render_dialogue_on_overlay(
            overlay, dialogue_text, dialogue_face_id, faces, dialogue_placement
        )
        
        # Composite and return
        return Image.alpha_composite(base, overlay)

    def _calculate_dialogue_placement(
        self,
        image: Image.Image,
        text: str,
        face_id: int,
        faces: FaceBoxes,
    ) -> CandidatePlacement:
        """Calculate dialogue placement without rendering."""
        font = self._load_font(int(self.style["font_size"]))
        padding = int(self.style["padding"])
        margin = int(self.style["margin"])
        
        # Calculate text dimensions (same logic as in _draw_dialogue)
        base_max_width = int(image.width * self.style["max_width_ratio"])
        text_length = len(text)
        if text_length <= 50:
            max_width = base_max_width
        elif text_length <= 100:
            max_width = int(image.width * min(0.9, self.style["max_width_ratio"] + 0.1))
        else:
            max_width = int(image.width * 0.95)
        
        max_width = min(max_width, image.width - 2 * margin)
        
        # Get face position
        face_box = faces[face_id]
        face_rect = (face_box[0], face_box[1], face_box[2], face_box[3])
        
        # Wrap text and calculate bubble dimensions
        wrapped_lines = self._wrap_text(text, font, max_width - 2 * padding)
        text_width, text_height = self._calculate_text_size(wrapped_lines, font)
        bubble_width = text_width + 2 * padding
        bubble_height = text_height + 2 * padding
        
        # Find best placement
        other_faces: FaceBoxes = {
            fid: box for fid, box in faces.items() if fid != face_id
        }
        return self._find_dialogue_placement(
            image, bubble_width, bubble_height, face_rect, margin, other_faces
        )
    
    def _calculate_narration_placement_with_avoidance(
        self,
        image: Image.Image,
        text: str,
        faces: FaceBoxes,
        avoid_rect: Rectangle,
    ) -> CandidatePlacement:
        """Calculate narration placement while avoiding a specific rectangle."""
        font = self._load_font(int(self.style["font_size"]))
        padding = int(self.style["padding"])
        margin = int(self.style["margin"])
        
        # Calculate text dimensions (same logic as in _draw_narration)
        base_max_width = int(image.width * self.style["max_width_ratio"])
        text_length = len(text)
        if text_length <= 50:
            max_width = base_max_width
        elif text_length <= 100:
            max_width = int(image.width * min(0.9, self.style["max_width_ratio"] + 0.1))
        else:
            max_width = int(image.width * 0.95)
        
        max_width = min(max_width, image.width - 2 * margin)
        
        # Wrap text and calculate bubble dimensions
        wrapped_lines = self._wrap_text(text, font, max_width - 2 * padding)
        text_width, text_height = self._calculate_text_size(wrapped_lines, font)
        bubble_width = text_width + 2 * padding
        bubble_height = text_height + 2 * padding
        
        # Find placement avoiding both faces and the dialogue bubble
        return self._find_narration_placement_with_avoidance(
            image, bubble_width, bubble_height, faces, margin, avoid_rect
        )
    
    def _find_narration_placement_with_avoidance(
        self,
        image: Image.Image,
        bubble_width: int,
        bubble_height: int,
        faces: FaceBoxes,
        margin: int,
        avoid_rect: Rectangle,
    ) -> CandidatePlacement:
        """Find narration placement avoiding faces and a specific rectangle."""
        img_width, img_height = image.size
        
        # Expand the avoid rectangle with margin
        expanded_avoid = self._expand_rect(avoid_rect, margin)
        
        # Calculate face centroid
        face_centroid_y = self._calculate_face_centroid_y(faces, img_height) if faces else img_height / 2
        
        # Try positions in order of preference
        center_x = (img_width - bubble_width) // 2
        
        candidates = []
        
        # Try bottom position
        bottom_y = img_height - bubble_height - margin
        if bottom_y >= 0:
            bottom_rect = (center_x, bottom_y, center_x + bubble_width, bottom_y + bubble_height)
            if (not self._rects_intersect(bottom_rect, expanded_avoid) and
                self._is_placement_valid(bottom_rect, faces, margin, image)):
                distance = self._min_rect_distance_to_faces(bottom_rect, faces)
                candidates.append(CandidatePlacement(
                    bottom_rect, "bottom", distance if not math.isinf(distance) else 1000.0
                ))
        
        # Try top position
        top_y = margin
        if top_y + bubble_height <= img_height:
            top_rect = (center_x, top_y, center_x + bubble_width, top_y + bubble_height)
            if (not self._rects_intersect(top_rect, expanded_avoid) and
                self._is_placement_valid(top_rect, faces, margin, image)):
                distance = self._min_rect_distance_to_faces(top_rect, faces)
                candidates.append(CandidatePlacement(
                    top_rect, "top", distance if not math.isinf(distance) else 800.0
                ))
        
        # Try left and right positions
        mid_y = (img_height - bubble_height) // 2
        
        # Left position
        left_x = margin
        if left_x + bubble_width <= img_width:
            left_rect = (left_x, mid_y, left_x + bubble_width, mid_y + bubble_height)
            if (not self._rects_intersect(left_rect, expanded_avoid) and
                self._is_placement_valid(left_rect, faces, margin, image)):
                distance = self._min_rect_distance_to_faces(left_rect, faces)
                candidates.append(CandidatePlacement(
                    left_rect, "left", distance if not math.isinf(distance) else 600.0
                ))
        
        # Right position
        right_x = img_width - bubble_width - margin
        if right_x >= 0:
            right_rect = (right_x, mid_y, right_x + bubble_width, mid_y + bubble_height)
            if (not self._rects_intersect(right_rect, expanded_avoid) and
                self._is_placement_valid(right_rect, faces, margin, image)):
                distance = self._min_rect_distance_to_faces(right_rect, faces)
                candidates.append(CandidatePlacement(
                    right_rect, "right", distance if not math.isinf(distance) else 600.0
                ))
        
        # Return best candidate or fallback
        if candidates:
            return max(candidates, key=lambda c: c.score)
        
        # Fallback: use original narration placement logic
        return self._find_narration_placement(image, bubble_width, bubble_height, faces, margin)
    
    def _is_placement_valid(
        self,
        rect: Rectangle,
        faces: FaceBoxes,
        margin: int,
        image: Image.Image,
    ) -> bool:
        """Check if a placement is valid (doesn't intersect with faces)."""
        # Check image bounds
        if not self._rect_within_bounds(rect, image.size, margin):
            return False
        
        # Check face intersections
        expanded_faces = [self._expand_rect(tuple(box), margin) for box in faces.values()]
        return not any(self._rects_intersect(rect, face_rect) for face_rect in expanded_faces)
    
    def _render_narration_on_overlay(
        self,
        overlay: Image.Image,
        text: str,
        placement: CandidatePlacement,
    ) -> None:
        """Render narration bubble on overlay."""
        font = self._load_font(int(self.style["font_size"]))
        padding = int(self.style["padding"])
        
        # Draw the narration bubble
        self._draw_rounded_rectangle(
            overlay, placement.rect,
            int(self.style["corner_radius"]),
            self.style["background_color"], int(self.style["background_opacity"]),
            self.style["border_color"], int(self.style["border_width"]), int(self.style["border_opacity"])
        )
        
        # Wrap and draw text
        max_text_width = int(placement.rect[2] - placement.rect[0]) - 2 * padding
        wrapped_lines = self._wrap_text(text, font, max_text_width)
        self._draw_text_in_rect(overlay, wrapped_lines, placement.rect, font, self.style["font_color"], padding)
    
    def _render_dialogue_on_overlay(
        self,
        overlay: Image.Image,
        text: str,
        face_id: int,
        faces: FaceBoxes,
        placement: CandidatePlacement,
    ) -> None:
        """Render dialogue bubble on overlay."""
        font = self._load_font(int(self.style["font_size"]))
        padding = int(self.style["padding"])
        
        # Get face rect
        face_box = faces[face_id]
        face_rect = (face_box[0], face_box[1], face_box[2], face_box[3])
        
        # Draw the dialogue bubble with tail
        self._draw_speech_bubble(
            overlay, placement.rect, face_rect, placement.direction,
            int(self.style["corner_radius"]),
            self.style["background_color"], int(self.style["background_opacity"]),
            self.style["border_color"], int(self.style["border_width"]), int(self.style["border_opacity"]),
            int(self.style["tail_width"]), int(self.style["tail_length"]),
            placement.tail_anchor, placement.face_anchor,
        )
        
        # Wrap and draw text
        max_text_width = int(placement.rect[2] - placement.rect[0]) - 2 * padding
        wrapped_lines = self._wrap_text(text, font, max_text_width)
        self._draw_text_in_rect(overlay, wrapped_lines, placement.rect, font, self.style["font_color"], padding)

    # ------------------------------------------------------------------
    # Narration bubble placement
    # ------------------------------------------------------------------
    def _draw_narration(self, image: Image.Image, text: str, faces: FaceBoxes) -> Image.Image:
        font = self._load_font(int(self.style["font_size"]))
        padding = int(self.style["padding"])
        margin = int(self.style["margin"])
        
        # Dynamic max width calculation - use more space for longer text
        base_max_width = int(image.width * self.style["max_width_ratio"])
        
        # For short text, use a smaller ratio; for long text, use more space
        text_length = len(text)
        if text_length <= 50:
            # Short text: use base ratio
            max_width = base_max_width
        elif text_length <= 100:
            # Medium text: increase ratio slightly
            max_width = int(image.width * min(0.9, self.style["max_width_ratio"] + 0.1))
        else:
            # Long text: use most of the available width
            max_width = int(image.width * 0.95)
        
        # Ensure we don't exceed image bounds considering margins
        max_width = min(max_width, image.width - 2 * margin)

        # Wrap text to fit within max width (subtract padding for actual text area)
        wrapped_lines = self._wrap_text(text, font, max_width - 2 * padding)

        # Calculate text dimensions
        text_width, text_height = self._calculate_text_size(wrapped_lines, font)

        # Calculate bubble dimensions
        bubble_width = text_width + 2 * padding
        bubble_height = text_height + 2 * padding

        # Find best placement for narration (top or bottom)
        placement = self._find_narration_placement(image, bubble_width, bubble_height, faces, margin)

        # Create overlay for the bubble
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))

        # Draw the narration bubble
        self._draw_rounded_rectangle(
            overlay, placement.rect,
            int(self.style["corner_radius"]),
            self.style["background_color"], int(self.style["background_opacity"]),
            self.style["border_color"], int(self.style["border_width"]), int(self.style["border_opacity"])
        )

        # Draw text
        self._draw_text_in_rect(overlay, wrapped_lines, placement.rect, font, self.style["font_color"], padding)

        # Composite and return
        return Image.alpha_composite(image, overlay)

    def _draw_dialogue(self, image: Image.Image, text: str, face_id: int, faces: FaceBoxes) -> Image.Image:
        font = self._load_font(int(self.style["font_size"]))
        padding = int(self.style["padding"])
        margin = int(self.style["margin"])
        
        # Dynamic max width calculation - same as narration
        base_max_width = int(image.width * self.style["max_width_ratio"])
        
        text_length = len(text)
        if text_length <= 50:
            max_width = base_max_width
        elif text_length <= 100:
            max_width = int(image.width * min(0.9, self.style["max_width_ratio"] + 0.1))
        else:
            max_width = int(image.width * 0.95)
        
        max_width = min(max_width, image.width - 2 * margin)

        # Get face position
        face_box = faces[face_id]
        face_rect = (face_box[0], face_box[1], face_box[2], face_box[3])

        # Wrap text to fit within max width
        wrapped_lines = self._wrap_text(text, font, max_width - 2 * padding)

        # Calculate text dimensions
        text_width, text_height = self._calculate_text_size(wrapped_lines, font)

        # Calculate bubble dimensions
        bubble_width = text_width + 2 * padding
        bubble_height = text_height + 2 * padding

        # Find best placement for dialogue bubble while avoiding other faces
        other_faces: FaceBoxes = {
            fid: box for fid, box in faces.items() if fid != face_id
        }
        placement = self._find_dialogue_placement(
            image,
            bubble_width,
            bubble_height,
            face_rect,
            margin,
            other_faces,
        )

        # Create overlay for the bubble
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))

        # Draw the dialogue bubble with tail
        self._draw_speech_bubble(
            overlay, placement.rect, face_rect, placement.direction,
            int(self.style["corner_radius"]),
            self.style["background_color"], int(self.style["background_opacity"]),
            self.style["border_color"], int(self.style["border_width"]), int(self.style["border_opacity"]),
            int(self.style["tail_width"]), int(self.style["tail_length"]),
            placement.tail_anchor, placement.face_anchor,
        )

        # Draw text
        self._draw_text_in_rect(overlay, wrapped_lines, placement.rect, font, self.style["font_color"], padding)

        # Composite and return
        return Image.alpha_composite(image, overlay)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load font with caching."""
        if size in self._font_cache:
            return self._font_cache[size]

        font = None
        if self.font_path:
            try:
                font = ImageFont.truetype(self.font_path, size)
            except (OSError, IOError):
                pass

        if font is None:
            # Try common system fonts
            common_fonts = [
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "C:/Windows/Fonts/arial.ttf",  # Windows
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            ]
            for font_path in common_fonts:
                try:
                    font = ImageFont.truetype(font_path, size)
                    break
                except (OSError, IOError):
                    continue

        if font is None:
            font = ImageFont.load_default()

        self._font_cache[size] = font
        return font

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wrap text to fit within specified width."""
        lines = []
        words = text.split()
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = self._measure_draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]

            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Single word is too long, break it down
                    while word:
                        for i in range(len(word), 0, -1):
                            substring = word[:i]
                            bbox = self._measure_draw.textbbox((0, 0), substring, font=font)
                            if bbox[2] - bbox[0] <= max_width:
                                lines.append(substring)
                                word = word[i:]
                                break
                        else:
                            # Even single character is too wide, just add it
                            lines.append(word[0])
                            word = word[1:]

        if current_line:
            lines.append(current_line)

        return lines

    def _calculate_text_size(self, lines: List[str], font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Calculate total text dimensions."""
        if not lines:
            return 0, 0

        max_width = 0
        total_height = 0
        line_spacing = self.style["line_spacing"]

        for i, line in enumerate(lines):
            bbox = self._measure_draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]

            max_width = max(max_width, line_width)
            total_height += line_height

            if i < len(lines) - 1:  # Add spacing between lines
                total_height += int(line_height * (line_spacing - 1))

        return max_width, total_height

    def _find_narration_placement(self, image: Image.Image, bubble_width: int, bubble_height: int,
                                faces: FaceBoxes, margin: int) -> CandidatePlacement:
        """Find best placement for narration bubble - prioritize position farthest from faces."""
        img_width, img_height = image.size
        
        # Calculate face centroid to determine where faces are located
        face_centroid_y = self._calculate_face_centroid_y(faces, img_height) if faces else img_height / 2
        
        # Simple logic: default to bottom, use top if faces are in bottom half
        center_x = (img_width - bubble_width) // 2
        
        # Try bottom first (preferred)
        bottom_y = img_height - bubble_height - margin
        if bottom_y >= 0:
            bottom_rect = (center_x, bottom_y, center_x + bubble_width, bottom_y + bubble_height)
            
            # Check if bottom placement conflicts too much with faces
            expanded_faces = [self._expand_rect(tuple(box), margin) for box in faces.values()]
            conflicts = any(self._rects_intersect(bottom_rect, face_rect) for face_rect in expanded_faces)
            
            # If no major conflicts, or if faces are in upper half, use bottom
            if not conflicts or face_centroid_y < img_height / 2:
                distance = self._min_rect_distance_to_faces(bottom_rect, faces)
                return CandidatePlacement(bottom_rect, "bottom", distance if not math.isinf(distance) else 1000.0)
        
        # Try top as fallback
        top_y = margin
        if top_y + bubble_height <= img_height:
            top_rect = (center_x, top_y, center_x + bubble_width, top_y + bubble_height)
            distance = self._min_rect_distance_to_faces(top_rect, faces)
            return CandidatePlacement(top_rect, "top", distance if not math.isinf(distance) else 800.0)
        
        # Absolute fallback: use bottom even if it causes conflicts
        fallback_rect = (center_x, max(0, bottom_y), center_x + bubble_width, 
                        min(img_height, max(0, bottom_y) + bubble_height))
        return CandidatePlacement(fallback_rect, "bottom", 500.0)

    def _find_dialogue_placement(
        self,
        image: Image.Image,
        bubble_width: int,
        bubble_height: int,
        face_rect: Rectangle,
        margin: int,
        other_faces: FaceBoxes,
    ) -> CandidatePlacement:
        """Find best placement for dialogue bubble.

        This routine samples candidate angles around the face and places the
        bubble such that its tail can directly point towards the face while the
        rectangle itself stays within frame bounds and avoids overlapping the
        face. If no radial candidate is valid, the method falls back to a
        simpler cardinal placement.
        """

        img_width, img_height = image.size
        face_x1, face_y1, face_x2, face_y2 = face_rect
        face_center = ((face_x1 + face_x2) / 2, (face_y1 + face_y2) / 2)
        half_size = (bubble_width / 2.0, bubble_height / 2.0)

        base_gap = max(int(self.style["tail_length"]), margin)
        tail_width = int(self.style["tail_width"])
        max_gap = max(img_width, img_height) * 0.75
        gap_step = max(20, tail_width)

        expanded_face = self._expand_rect(face_rect, margin)
        expanded_others = [self._expand_rect(tuple(box), margin) for box in other_faces.values()]

        radial_candidates: List[CandidatePlacement] = []

        # Sample full circle around the face to locate feasible bubble anchors.
        for angle in range(0, 360, 12):
            rad = math.radians(angle)
            dir_x = math.cos(rad)
            dir_y = math.sin(rad)

            if math.isclose(dir_x, 0.0, abs_tol=1e-6) and math.isclose(dir_y, 0.0, abs_tol=1e-6):
                continue

            direction = self._normalize_vector((dir_x, dir_y))
            if direction is None:
                continue

            face_anchor = self._intersect_ray_with_rect(face_center, direction, face_rect)
            if face_anchor is None:
                continue

            span = self._distance_to_rect_edge(half_size, direction)
            if span is None:
                continue

            for gap in self._candidate_tail_gaps(base_gap, max_gap, gap_step):
                distance = span + gap
                center_x = face_anchor[0] + direction[0] * distance
                center_y = face_anchor[1] + direction[1] * distance

                bubble_rect = (
                    center_x - half_size[0],
                    center_y - half_size[1],
                    center_x + half_size[0],
                    center_y + half_size[1],
                )

                if not self._rect_within_bounds(bubble_rect, (img_width, img_height), margin):
                    continue

                if self._rects_intersect(bubble_rect, expanded_face):
                    continue

                intersects_other = False
                for other in expanded_others:
                    if self._rects_intersect(bubble_rect, other):
                        intersects_other = True
                        break
                if intersects_other:
                    continue

                tail_anchor = self._intersect_segment_with_rect(bubble_rect, (center_x, center_y), face_anchor)
                if tail_anchor is None:
                    continue

                score = self._calculate_placement_score(bubble_rect, other_faces, image)
                score -= gap * 0.001  # prefer shorter tails

                radial_candidates.append(
                    CandidatePlacement(bubble_rect, None, score, tail_anchor=tail_anchor, face_anchor=face_anchor)
                )

        if radial_candidates:
            return max(radial_candidates, key=lambda c: c.score)

        # Fallback: use the earlier cardinal placement with tail alignment
        candidates: List[CandidatePlacement] = []
        tail_length = int(self.style["tail_length"])
        face_center_x, face_center_y = face_center

        for direction in ["left", "right", "top", "bottom"]:
            if direction == "left":
                bubble_x = max(margin, face_x1 - bubble_width - tail_length - margin)
                bubble_y = max(margin, min(face_center_y - bubble_height / 2, img_height - bubble_height - margin))
            elif direction == "right":
                bubble_x = min(img_width - bubble_width - margin, face_x2 + tail_length + margin)
                bubble_y = max(margin, min(face_center_y - bubble_height / 2, img_height - bubble_height - margin))
            elif direction == "top":
                bubble_x = max(margin, min(face_center_x - bubble_width / 2, img_width - bubble_width - margin))
                bubble_y = max(margin, face_y1 - bubble_height - tail_length - margin)
            else:  # bottom
                bubble_x = max(margin, min(face_center_x - bubble_width / 2, img_width - bubble_width - margin))
                bubble_y = min(img_height - bubble_height - margin, face_y2 + tail_length + margin)

            bubble_rect = (
                bubble_x,
                bubble_y,
                bubble_x + bubble_width,
                bubble_y + bubble_height,
            )

            if not self._rect_within_bounds(bubble_rect, (img_width, img_height), 0):
                continue

            intersects_other = False
            for other in expanded_others:
                if self._rects_intersect(bubble_rect, other):
                    intersects_other = True
                    break
            if intersects_other:
                continue

            tail_anchor = self._intersect_segment_with_rect(bubble_rect, (
                bubble_x + bubble_width / 2,
                bubble_y + bubble_height / 2,
            ), face_center)
            if tail_anchor is None:
                continue

            candidate_score = self._calculate_placement_score(bubble_rect, other_faces, image)
            candidates.append(
                CandidatePlacement(
                    bubble_rect,
                    direction,
                    candidate_score,
                    tail_anchor=tail_anchor,
                    face_anchor=face_center,
                )
            )

        if candidates:
            return max(candidates, key=lambda c: c.score)

        fallback_x = max(margin, min(face_center_x - bubble_width / 2, img_width - bubble_width - margin))
        fallback_y = max(margin, face_y1 - bubble_height - tail_length - margin)
        fallback_rect = (fallback_x, fallback_y, fallback_x + bubble_width, fallback_y + bubble_height)
        tail_anchor = self._intersect_segment_with_rect(
            fallback_rect,
            (fallback_x + bubble_width / 2, fallback_y + bubble_height / 2),
            face_center,
        )
        face_anchor = face_center
        return CandidatePlacement(
            fallback_rect,
            "top",
            0.0,
            tail_anchor=tail_anchor,
            face_anchor=face_anchor,
        )

    def _calculate_placement_score(self, rect: Rectangle, faces: FaceBoxes, image: Image.Image) -> float:
        """Calculate placement score based on face overlap and image content complexity."""
        score = 1.0

        # Penalize overlap with faces
        for face_box in faces.values():
            face_rect = (face_box[0], face_box[1], face_box[2], face_box[3])
            overlap = self._calculate_overlap(rect, face_rect)
            score -= overlap * 0.5

        # Prefer areas with less visual complexity (this is a simplified heuristic)
        # In a real implementation, you might analyze the image content

        return max(0.0, score)

    def _calculate_overlap(self, rect1: Rectangle, rect2: Rectangle) -> float:
        """Calculate overlap ratio between two rectangles."""
        x1_max = max(rect1[0], rect2[0])
        y1_max = max(rect1[1], rect2[1])
        x2_min = min(rect1[2], rect2[2])
        y2_min = min(rect1[3], rect2[3])

        if x2_min <= x1_max or y2_min <= y1_max:
            return 0.0

        overlap_area = (x2_min - x1_max) * (y2_min - y1_max)
        rect1_area = (rect1[2] - rect1[0]) * (rect1[3] - rect1[1])

        return overlap_area / rect1_area if rect1_area > 0 else 0.0

    def _append_narration_candidate(
        self,
        candidates: List[CandidatePlacement],
        rect: Rectangle,
        expanded_faces: Sequence[Rectangle],
        faces: FaceBoxes,
        image: Image.Image,
    ) -> None:
        if any(self._rects_intersect(rect, face_rect) for face_rect in expanded_faces):
            return

        distance = self._min_rect_distance_to_faces(rect, faces)
        vertical_distance = self._min_rect_vertical_distance_to_faces(rect, faces)

        if math.isinf(distance) and math.isinf(vertical_distance):
            score = self._calculate_placement_score(rect, faces, image)
        else:
            base_distance = 0.0 if math.isinf(distance) else distance
            vertical_component = 0.0 if math.isinf(vertical_distance) else vertical_distance * 1000.0
            score = vertical_component + base_distance

        candidates.append(CandidatePlacement(rect, None, score))

    def _find_narration_fallback(
        self,
        image: Image.Image,
        bubble_width: int,
        bubble_height: int,
        faces: FaceBoxes,
        margin: int,
        expanded_faces: Optional[Sequence[Rectangle]] = None,
    ) -> Optional[CandidatePlacement]:
        img_width, img_height = image.size
        expanded_faces = expanded_faces or [self._expand_rect(tuple(box), margin) for box in faces.values()]

        max_x = img_width - bubble_width - margin
        max_y = img_height - bubble_height - margin
        if max_x < margin or max_y < margin:
            return None

        step_x = max(20, bubble_width // 2)
        step_y = max(20, bubble_height // 2)

        candidates: List[CandidatePlacement] = []
        y = margin
        while y <= max_y:
            x = margin
            while x <= max_x:
                rect = (x, y, x + bubble_width, y + bubble_height)
                self._append_narration_candidate(candidates, rect, expanded_faces, faces, image)
                x += step_x
            y += step_y

        if not candidates:
            return None

        return max(candidates, key=lambda c: c.score)

    def _min_rect_distance_to_faces(self, rect: Rectangle, faces: FaceBoxes) -> float:
        if not faces:
            return float("inf")

        rect_x1, rect_y1, rect_x2, rect_y2 = rect
        min_distance = float("inf")

        for face_box in faces.values():
            face_x1, face_y1, face_x2, face_y2 = face_box

            if rect_x2 >= face_x1 and rect_x1 <= face_x2 and rect_y2 >= face_y1 and rect_y1 <= face_y2:
                return 0.0

            dx = 0.0
            if rect_x2 < face_x1:
                dx = face_x1 - rect_x2
            elif face_x2 < rect_x1:
                dx = rect_x1 - face_x2

            dy = 0.0
            if rect_y2 < face_y1:
                dy = face_y1 - rect_y2
            elif face_y2 < rect_y1:
                dy = rect_y1 - face_y2

            distance = math.hypot(dx, dy)
            min_distance = min(min_distance, distance)

        return min_distance

    def _min_rect_vertical_distance_to_faces(self, rect: Rectangle, faces: FaceBoxes) -> float:
        if not faces:
            return float("inf")

        rect_y1, rect_y2 = rect[1], rect[3]
        min_vertical = float("inf")

        for face_box in faces.values():
            face_y1, face_y2 = face_box[1], face_box[3]

            if rect_y2 >= face_y1 and rect_y1 <= face_y2:
                return 0.0

            if rect_y2 < face_y1:
                vertical_gap = face_y1 - rect_y2
            else:
                vertical_gap = rect_y1 - face_y2

            min_vertical = min(min_vertical, vertical_gap)

        return min_vertical

    def _calculate_face_centroid_y(self, faces: FaceBoxes, img_height: int) -> float:
        """Calculate the Y centroid of all faces to determine their overall position in the image."""
        if not faces:
            return img_height / 2
        
        total_y = 0.0
        total_faces = 0
        
        for face_box in faces.values():
            face_center_y = (face_box[1] + face_box[3]) / 2  # (y1 + y2) / 2
            total_y += face_center_y
            total_faces += 1
        
        return total_y / total_faces if total_faces > 0 else img_height / 2

    def _generate_horizontal_positions(
        self,
        img_width: int,
        bubble_width: int,
        margin: int,
        avoid_rects: Sequence[Rectangle],
    ) -> List[int]:
        left_limit = margin
        right_limit = img_width - bubble_width - margin
        if right_limit <= left_limit:
            center = self._clamp_horizontal_position(img_width, bubble_width, margin, (img_width - bubble_width) / 2.0)
            return [center]

        positions: set[int] = set()

        base_step = max(20, int(bubble_width * 0.4))
        pos = left_limit
        while pos <= right_limit:
            positions.add(int(pos))
            pos += base_step

        positions.add(self._clamp_horizontal_position(img_width, bubble_width, margin, (img_width - bubble_width) / 2.0))
        positions.add(self._clamp_horizontal_position(img_width, bubble_width, margin, left_limit))
        positions.add(self._clamp_horizontal_position(img_width, bubble_width, margin, right_limit))

        for rect in avoid_rects:
            left_candidate = self._clamp_horizontal_position(img_width, bubble_width, margin, rect[0] - bubble_width - margin)
            right_candidate = self._clamp_horizontal_position(img_width, bubble_width, margin, rect[2] + margin)

            if left_limit <= left_candidate <= right_limit:
                positions.add(left_candidate)

            if left_limit <= right_candidate <= right_limit:
                positions.add(right_candidate)

        return sorted(positions)

    def _clamp_horizontal_position(
        self,
        img_width: int,
        bubble_width: int,
        margin: int,
        desired: float,
    ) -> int:
        min_x = margin
        max_x = img_width - bubble_width - margin
        if max_x < min_x:
            mid = (img_width - bubble_width) / 2.0
            return int(round(max(min_x, mid)))

        return int(round(min(max(desired, min_x), max_x)))

    def _expand_rect(self, rect: Rectangle, padding: float) -> Rectangle:
        if padding <= 0:
            return rect
        return (
            rect[0] - padding,
            rect[1] - padding,
            rect[2] + padding,
            rect[3] + padding,
        )

    def _rect_within_bounds(self, rect: Rectangle, image_size: Tuple[int, int], margin: float) -> bool:
        width, height = image_size
        return (
            rect[0] >= margin and rect[1] >= margin and
            rect[2] <= width - margin and rect[3] <= height - margin
        )

    def _rects_intersect(self, rect1: Rectangle, rect2: Rectangle) -> bool:
        return not (
            rect1[2] <= rect2[0] or rect1[0] >= rect2[2] or
            rect1[3] <= rect2[1] or rect1[1] >= rect2[3]
        )

    def _normalize_vector(self, vector: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        vx, vy = vector
        length = math.hypot(vx, vy)
        if length < 1e-6:
            return None
        return vx / length, vy / length

    def _distance_to_rect_edge(self, half_size: Tuple[float, float], direction: Tuple[float, float]) -> Optional[float]:
        dx, dy = direction
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        eps = 1e-6

        tx = half_size[0] / abs_dx if abs_dx > eps else float("inf")
        ty = half_size[1] / abs_dy if abs_dy > eps else float("inf")

        distance = min(tx, ty)
        if math.isinf(distance):
            return None
        return distance

    def _candidate_tail_gaps(self, start: float, maximum: float, step: float) -> Iterable[float]:
        length = max(start, 0.0)
        maximum = max(length, maximum)
        step = max(step, 1.0)

        while length <= maximum:
            yield length
            length += step

    def _intersect_ray_with_rect(
        self,
        origin: Tuple[float, float],
        direction: Tuple[float, float],
        rect: Rectangle,
    ) -> Optional[Tuple[float, float]]:
        ox, oy = origin
        dx, dy = direction
        x1, y1, x2, y2 = rect
        eps = 1e-6

        candidates: List[Tuple[float, Tuple[float, float]]] = []

        if abs(dx) > eps:
            for x_edge in (x1, x2):
                t = (x_edge - ox) / dx
                if t <= eps:
                    continue
                y = oy + t * dy
                if y1 - eps <= y <= y2 + eps:
                    candidates.append((t, (x_edge, y)))

        if abs(dy) > eps:
            for y_edge in (y1, y2):
                t = (y_edge - oy) / dy
                if t <= eps:
                    continue
                x = ox + t * dx
                if x1 - eps <= x <= x2 + eps:
                    candidates.append((t, (x, y_edge)))

        if not candidates:
            return None

        t_min, point = min(candidates, key=lambda item: item[0])
        if t_min <= eps:
            return None
        return point

    def _intersect_segment_with_rect(
        self,
        rect: Rectangle,
        start: Tuple[float, float],
        end: Tuple[float, float],
    ) -> Optional[Tuple[float, float]]:
        direction = (end[0] - start[0], end[1] - start[1])
        ray_hit = self._intersect_ray_with_rect(start, direction, rect)
        if ray_hit is None:
            return None

        total_length = math.hypot(direction[0], direction[1])
        if total_length < 1e-6:
            return None

        segment_length = math.hypot(ray_hit[0] - start[0], ray_hit[1] - start[1])
        if segment_length > total_length + 1e-3:
            return None

        return ray_hit

    def _draw_rounded_rectangle(self, image: Image.Image, rect: Rectangle, radius: int,
                              fill_color: Tuple[int, int, int], fill_alpha: int,
                              border_color: Tuple[int, int, int], border_width: int, border_alpha: int):
        """Draw a rounded rectangle with border."""
        draw = ImageDraw.Draw(image)

        # Create fill color with alpha
        fill_rgba = (*fill_color, fill_alpha)
        border_rgba = (*border_color, border_alpha)

        # Draw filled rounded rectangle
        draw.rounded_rectangle(rect, radius=radius, fill=fill_rgba, outline=border_rgba, width=border_width)

    def _draw_speech_bubble(
        self,
        image: Image.Image,
        rect: Rectangle,
        face_rect: Rectangle,
        direction: Optional[str],
        radius: int,
        fill_color: Tuple[int, int, int],
        fill_alpha: int,
        border_color: Tuple[int, int, int],
        border_width: int,
        border_alpha: int,
        tail_width: int,
        tail_length: int,
        tail_anchor: Optional[Tuple[float, float]] = None,
        face_anchor: Optional[Tuple[float, float]] = None,
    ):
        """Draw a speech bubble with tail pointing to face."""
        draw = ImageDraw.Draw(image)

        fill_rgba = (*fill_color, fill_alpha)
        border_rgba = (*border_color, border_alpha)

        # Draw main bubble
        draw.rounded_rectangle(rect, radius=radius, fill=fill_rgba, outline=border_rgba, width=border_width)

        # Draw tail
        if tail_anchor and face_anchor:
            self._draw_speech_tail_dynamic(
                draw,
                tail_anchor,
                face_anchor,
                tail_width,
                fill_rgba,
                border_rgba,
                border_width,
            )
        elif direction:
            self._draw_speech_tail(
                draw,
                rect,
                face_rect,
                direction,
                tail_width,
                tail_length,
                fill_rgba,
                border_rgba,
                border_width,
            )

    def _draw_speech_tail_dynamic(
        self,
        draw: ImageDraw.ImageDraw,
        tail_anchor: Tuple[float, float],
        face_anchor: Tuple[float, float],
        tail_width: int,
        fill_color: ColorTuple,
        border_color: ColorTuple,
        border_width: int,
    ) -> None:
        dx = face_anchor[0] - tail_anchor[0]
        dy = face_anchor[1] - tail_anchor[1]
        length = math.hypot(dx, dy)
        if length < 1e-3:
            return

        nx = -dy / length
        ny = dx / length
        half_width = tail_width / 2.0

        base1 = (tail_anchor[0] + nx * half_width, tail_anchor[1] + ny * half_width)
        base2 = (tail_anchor[0] - nx * half_width, tail_anchor[1] - ny * half_width)
        tail_points = [base1, base2, face_anchor]

        draw.polygon(tail_points, fill=fill_color, outline=border_color)

        if border_width > 1:
            draw.line([base1, face_anchor, base2, base1], fill=border_color, width=border_width)

    def _draw_speech_tail(self, draw: ImageDraw.ImageDraw, bubble_rect: Rectangle, face_rect: Rectangle,
                         direction: str, tail_width: int, tail_length: int,
                         fill_color: ColorTuple, border_color: ColorTuple, border_width: int):
        """Draw speech bubble tail."""
        bubble_x1, bubble_y1, bubble_x2, bubble_y2 = bubble_rect
        face_center_x = (face_rect[0] + face_rect[2]) / 2
        face_center_y = (face_rect[1] + face_rect[3]) / 2

        if direction == "left":
            # Tail from right edge of bubble towards face
            tail_start_x = bubble_x2
            tail_start_y = bubble_y1 + (bubble_y2 - bubble_y1) / 2
            tail_end_x = tail_start_x + tail_length
            tail_end_y = face_center_y
        elif direction == "right":
            # Tail from left edge of bubble towards face
            tail_start_x = bubble_x1
            tail_start_y = bubble_y1 + (bubble_y2 - bubble_y1) / 2
            tail_end_x = tail_start_x - tail_length
            tail_end_y = face_center_y
        elif direction == "top":
            # Tail from bottom edge of bubble towards face
            tail_start_x = bubble_x1 + (bubble_x2 - bubble_x1) / 2
            tail_start_y = bubble_y2
            tail_end_x = face_center_x
            tail_end_y = tail_start_y + tail_length
        else:  # bottom
            # Tail from top edge of bubble towards face
            tail_start_x = bubble_x1 + (bubble_x2 - bubble_x1) / 2
            tail_start_y = bubble_y1
            tail_end_x = face_center_x
            tail_end_y = tail_start_y - tail_length

        # Draw triangular tail
        half_width = tail_width // 2

        if direction in ["left", "right"]:
            tail_points = [
                (tail_start_x, tail_start_y - half_width),
                (tail_start_x, tail_start_y + half_width),
                (tail_end_x, tail_end_y)
            ]
        else:
            tail_points = [
                (tail_start_x - half_width, tail_start_y),
                (tail_start_x + half_width, tail_start_y),
                (tail_end_x, tail_end_y)
            ]

        draw.polygon(tail_points, fill=fill_color, outline=border_color, width=border_width)

    def _draw_text_in_rect(self, image: Image.Image, lines: List[str], rect: Rectangle,
                          font: ImageFont.FreeTypeFont, color: Tuple[int, int, int], padding: int):
        """Draw text within a rectangle."""
        draw = ImageDraw.Draw(image)
        line_spacing = self.style["line_spacing"]

        # Calculate line height
        sample_bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = sample_bbox[3] - sample_bbox[1]

        current_y = rect[1] + padding

        for line in lines:
            # Get text width for centering
            text_bbox = draw.textbbox((0, 0), line, font=font)
            text_width = text_bbox[2] - text_bbox[0]

            # Center horizontally
            text_x = rect[0] + (rect[2] - rect[0] - text_width) // 2

            draw.text((text_x, current_y), line, font=font, fill=color)
            current_y += int(line_height * line_spacing)


# #%%
# bubbler = BubbleIt(
#     font_path='/Users/zgh/Desktop/workingdir/PicSJTAgent/src_img/annotator/No.384-ShangShouTuanYuanTi-2.ttf'
# )
# annotations = [
#     [{'annotation_type': 'narration', 'content': {'text': '你遇到一位新同事'}}],
#     [{'annotation_type': 'dialogue',
#       'content': {'face_id': 3, 'text': '晚上能见面吗？'}},
#      {'annotation_type': 'narration', 'content': {'text': '你得知他刚来'}}],
#     [{'annotation_type': 'dialogue',
#       'content': {'face_id': 5, 'text': '我该怎么回应？'}},
#      {'annotation_type': 'narration', 'content': {'text': '你对他请求犹豫'}}]
# ]
# annot_1 = annotations[0]
# annot_2 = annotations[1]
# #%%
# from PIL import Image
# import pickle as pkl
# pannel_1 = Image.open('/Users/zgh/Desktop/workingdir/PicSJTAgent/test_faced_1.png').convert("RGBA")
# pannel_2 = Image.open('/Users/zgh/Desktop/workingdir/PicSJTAgent/test_faced_2.png').convert("RGBA")

# with open('/Users/zgh/Desktop/workingdir/PicSJTAgent/test_face_box.pkl', 'rb') as f:
#     faces_box = pkl.load(f)

# faces1 = faces_box[0]
# faces2 = faces_box[1]
# #%%
# res1 = bubbler.render(pannel_1, annot_1, faces1)
# res2 = bubbler.render(pannel_2, annot_2, faces2)
# #%%
