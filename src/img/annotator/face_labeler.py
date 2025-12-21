from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
import insightface
import contextlib
import io


def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    """Convert a PIL image into a BGR ndarray for InsightFace."""
    if image.mode != "RGB":
        image = image.convert("RGB")
    rgb = np.array(image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _bgr_to_pil(bgr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


class FaceLabeler:
    """Detect faces, assign incremental labels, and store annotations."""

    def __init__(
        self,
        model_name: str = "buffalo_l",
        provider: Optional[List[str]] = None,
        det_size: Tuple[int, int] = (640, 640),
        root: Optional[str] = None,
        text_font_scale: float = 0.8,
        text_thickness: int = 2,
        score_threshold: float = 0.5,
    ) -> None:
        import onnxruntime as ort
        available = ort.get_available_providers()
        if "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
            
        kwargs: Dict[str, object] = {
            "name": model_name,
            "allowed_modules": ["detection"],
            "providers": providers,
        }
        if provider is not None:
            kwargs["providers"] = provider
        if root is not None:
            kwargs["root"] = root

        # Redirect stdout to suppress non-error prints
        with contextlib.redirect_stdout(io.StringIO()):
            self.app = insightface.app.FaceAnalysis(**kwargs)
            self.app.prepare(ctx_id=0, det_size=det_size)

        self.text_font_scale = float(text_font_scale)
        self.text_thickness = int(text_thickness)
        self.score_threshold = float(score_threshold)
        self._next_label = 0
        self._records: List[Dict[str, object]] = []

    def label(
        self, 
        image: Image.Image,
        reset: bool=False
        ) -> Dict[str, object]:
        """Detect faces in ``image`` and assign new labels starting from the last used index."""
        if reset:
            self.reset()
        bgr = _pil_to_bgr(image)
        with contextlib.redirect_stdout(io.StringIO()):
            detections = self.app.get(bgr)
        annotated = bgr.copy()
        image_index = len(self._records)

        faces: List[Dict[str, object]] = []
        for face in detections:
            bbox = np.asarray(face.bbox, dtype=np.int32).tolist()
            score = float(getattr(face, "det_score", getattr(face, "score", 0.0)))
            if score < self.score_threshold:
                continue
            label = self._next_label
            self._next_label += 1

            cv2.rectangle(annotated, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            text = str(label)
            (tw, th), _ = cv2.getTextSize(
                text,
                cv2.FONT_HERSHEY_SIMPLEX,
                self.text_font_scale,
                self.text_thickness,
            )
            top = max(0, bbox[1] - th - 6)
            cv2.rectangle(annotated, (bbox[0], top), (bbox[0] + tw + 6, bbox[1]), (0, 255, 0), -1)
            cv2.putText(
                annotated,
                text,
                (bbox[0] + 3, bbox[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.text_font_scale,
                (0, 0, 0),
                self.text_thickness,
                cv2.LINE_AA,
            )

            faces.append(
                {
                    "label": label,
                    "bbox": bbox,
                    "score": score,
                    "image_index": image_index,
                }
            )

        annotated_image = _bgr_to_pil(annotated)
        record = {"faces": faces, "annotated": annotated_image, "image_index": image_index}
        self._records.append(record)
        return record

    def reset(self) -> None:
        """Clear all cached faces and reset numbering."""
        self._records.clear()
        self._next_label = 0

    def get_labels(
        self,
        reorganize_by: str = "image",
        ) -> List[Dict[str, object]] | Dict[str, object]:
        """Return the per-image annotation records."""
        if reorganize_by == "face":
            all_faces: List[Dict[str, object]] = []
            annotated_images: List[Image.Image] = []
            for record in self._records:
                all_faces.extend(record["faces"])
                annotated_images.append(record["annotated"])
            return {"faces": all_faces, "annotated": annotated_images}
        elif reorganize_by == "image":
            to_return = {}
            for re in self._records:
                re_ = re.copy()
                del re_["image_index"]
                to_return[re["image_index"]] = re_
            return to_return
