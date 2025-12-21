from .annotator_llm import AnnotatorLLM
from .face_labeler import FaceLabeler
from ..viz import make_sequence
from .bubble_it import BubbleIt
from PIL import Image
import os.path as op

FONT_PATH = op.join(op.dirname(__file__), 'No.384-ShangShouTuanYuanTi-2.ttf')
class Annotator:
    def __init__(
        self, 
        ref_name:str,
        ref_img:Image.Image,
        situation_item:str,
        trait:str,
        image_sequence:Image.Image,
        panels:list[Image.Image],
        model:str='gpt-5',
        ):
        self.ref_name = ref_name
        self.ref_img = ref_img
        self.situation_item = situation_item
        self.trait = trait
        self.image_sequence = image_sequence
        self.panels = panels
        self.annotator_llm = AnnotatorLLM(
            ref_name=ref_name,
            ref_img=ref_img,
            model=model,
        )
        self.annotator_llm.initialize()
        self.labeler = FaceLabeler()

    def face_it(self):
        for img in self.panels:
            _ = self.labeler.label(img)
        self.all_faces = self.labeler.get_labels()
        self.faced_panels = [record['annotated'] for record in list(self.all_faces.values())]
    

    def annotate(
        self,
        verbose:bool=False,
        ):
        if not hasattr(self, 'faced_panels'):
            self.face_it()
        self.faced_panels = [
            record['annotated'] for record in list(self.all_faces.values())]
        response = self.annotator_llm.call(
            situation_item=self.situation_item,
            image_sequence=self.image_sequence,
            panels=self.faced_panels,
            verbose=verbose,
            construct=self.trait,
            )
        self.annotations = response
        return response

    def get_faced_sequence(
        self,
        ):
        if not hasattr(self, 'faced_panels'):
            self.face_it()
        seq = make_sequence(self.faced_panels)
        return seq
    
    def get_faced_pos(
        self,
        ):
        if not hasattr(self, 'all_faces'):
            self.face_it()
        to_return = {}
        for panel_id, record in self.all_faces.items():
            to_return[panel_id] = {}
            for face in record['faces']:
                face_id = face['label']
                bbox = face['bbox']
                to_return[panel_id][face_id] = bbox
        return to_return

    def bubble_it(
        self,
        annotations:list[list[dict]],
        font_path:str=FONT_PATH,
        style=None,
        ):
        if not hasattr(self, 'faced_panels'):
            self.face_it()

        bubbler = BubbleIt(font_path=font_path, style=style)
        bubbled_panels = []
        face_positions = self.get_faced_pos()
        for idx, annotation in enumerate(annotations):
            if len(annotation) != 0:
                face_boxes = face_positions[idx]
                panel = self.panels[idx]
                annotation = annotation[0] if len(annotation) == 1 else annotation
                rendered = bubbler.render(panel, annotation, faces=face_boxes)
            else:
                rendered = self.panels[idx]

            bubbled_panels.append(rendered)
        final_sequence = make_sequence(bubbled_panels)
        return final_sequence, bubbled_panels
    
    def run(
        self, 
        verbose:bool=True,
        run_bubble:bool=True,
        ):
        self.annotate(verbose=verbose)
        if run_bubble:
            final_sequence, bubbled_panels = self.bubble_it(self.annotations)
            return {
                "annotations": self.annotations,
                "faced_panels": self.faced_panels,
                "face_positions": self.get_faced_pos(),
                "bubbled_panels": bubbled_panels,
                "bubbled_sequence": final_sequence,
            }
        else:
            return {
                "annotations": self.annotations,
                "faced_panels": self.faced_panels,
                "face_positions": self.get_faced_pos(),
            }
            
def standalone_bubble_it(
    panels:list[Image.Image],
    annotations:list[list[dict]],
    face_positions:list[dict]=None,
    font_path:str=FONT_PATH,
    style=None,
):
    bubbler = BubbleIt(font_path=font_path, style=style)
    bubbled_panels = []
    for idx, annotation in enumerate(annotations):
        if len(annotation) != 0:
            face_boxes = face_positions[idx] if face_positions is not None else None
            panel = panels[idx]
            annotation = annotation[0] if len(annotation) == 1 else annotation
            rendered = bubbler.render(panel, annotation, faces=face_boxes)
        else:
            rendered = panels[idx]

        bubbled_panels.append(rendered)
    final_sequence = make_sequence(bubbled_panels)
    return final_sequence, bubbled_panels