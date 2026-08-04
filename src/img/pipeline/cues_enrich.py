from __future__ import annotations

from lmitf import TemplateLLM
from .utils import find_key_in_result
from ...retry import STEP_ATTEMPTS, retry_call
from dotenv import load_dotenv
load_dotenv()
import os.path as op
prompt_dir = op.join(op.dirname(__file__), '..', 'prompts', 'cues_enrich')

emo_llm = TemplateLLM(op.join(prompt_dir, 'emotion_analysis.py'))
exp_llm = TemplateLLM(op.join(prompt_dir, 'emotion_to_expression.py'))
se_llm = TemplateLLM(op.join(prompt_dir, 'scene_enrich.py'))
oe_llm = TemplateLLM(op.join(prompt_dir, 'object_enrich.py'))

def make_expression(situation, trait, ana_character, act_character):
    # 1. Emotion Analysis
    def _emotion():
        res = emo_llm.call(
            passage=situation, trait=trait,
            analyze_character=ana_character,
            activate_character=act_character,
        )
        return find_key_in_result(res, 'emotion')['emotion']

    emotion = retry_call(_emotion, attempts=STEP_ATTEMPTS, label=f'emotion({ana_character})')

    # 2. Emotion to Expression
    def _expression():
        res = exp_llm.call(passage=situation, emotion=emotion, character=ana_character)
        return find_key_in_result(res, 'expression')['expression']

    return retry_call(_expression, attempts=STEP_ATTEMPTS, label=f'expression({ana_character})')

def make_scene(situation, character, trait, scene):
    """Generate the observable description of scene in situation to activate character's trait."""
    def _scene():
        res = se_llm.call(
            passage=situation, character=character,
            trait=trait, scene=scene,
        )
        return find_key_in_result(res, 'scene')['scene']

    return retry_call(_scene, attempts=STEP_ATTEMPTS, label=f'scene({scene})')

def make_object(situation, character, trait, object_):
    """Generate the observable description of object in situation to activate character's trait."""
    def _object_desc():
        res = oe_llm.call(
            passage=situation, character=character,
            trait=trait, object=object_,
        )
        return find_key_in_result(res, 'object')['object']

    return retry_call(_object_desc, attempts=STEP_ATTEMPTS, label=f'object({object_})')

def enrich_characters(situation, trait, ana_characters, act_character):
    """"""
    expressions = {
        ana_character: make_expression(situation, trait, ana_character, act_character)
        for ana_character in ana_characters
    }
    return expressions

def enrich_scenes(situation, trait, scenes, act_character):
    """"""
    expressions = {
        scene: make_scene(situation, act_character, trait, scene)
        for scene in scenes
    }
    return expressions

def enrich_objects(situation, trait, objects, act_character):
    """"""
    expressions = {
        object_: make_object(situation, act_character, trait, object_)
        for object_ in objects
    }
    return expressions
