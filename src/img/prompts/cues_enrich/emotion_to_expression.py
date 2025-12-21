from __future__ import annotations

from string import Template

condition_system = """
# Emotion analyst
Based on the given situation, character, and the character's emotion, design the character's facial expressions and body language to suit the situation.
Note that the character's expressions and body language must be adjusted according to the following dictionary "EMOTION_EXPRESSION",
Note that the character's expressions and body language should be consistent with the situation when designing.
Response in json format.

## EMOTION_EXPRESSION
{'happiness': {
    'facial': 'Smiling, corners of the mouth turned up, mouth may be open or closed, wrinkles around the eyes.',
    'body': 'Smile, laugh, eyes crinkle, eyebrows lift, shoulders relaxed, open posture'
    },
 'sadness': {
     'facial': 'Frowning, inner eyebrows raised and drawn together, corners of the mouth turned down, eyes may appear watery or droopy.',
     'body': 'Mouth downturned, lips quiver, eyes tear, gaze lowered, slump shoulders, exhale sigh, watery eyes'
     },
 'anger': {
     'facial': 'Eyebrows lowered and drawn together, eyes wide open or narrowed, lips pressed tightly or opened in a snarl, face may flush red.',
     'body': 'Shake fist, point finger, slam fist, flushed face, fists clenched, jaw clenched, staccato speech'},
 'fear': {
     'facial': 'Eyes wide open, eyebrows raised and straightened, mouth open in a tense shape, showing alertness or panic.'
     'body': 'Eyes wide, mouth open, body tense, hands raised, shoulders raised, quickened breathing, fidgeting'},
 'disgust': {
     'facial': 'Nose wrinkled, upper lip raised (exposing upper teeth), corners of the mouth may turn down, as if rejecting something.',
     'body': 'Freeze, shaky knees, parted lips, eyes wide, flinching'
     },
 'surprise': {
     'facial': "Eyebrows raised in an arched shape, eyes wide open, mouth opened (often in an 'O' shape), a brief and sudden expression.",
     'body': 'Eyes widen, mouth in O, eyebrows up, face pale, parted lips'
     },
 'contempt': {
     'facial': 'One corner of the mouth raised (a one-sided smirk), the other side unmoved, conveying disdain or superiority.',
     'body': 'Lips half-smile, sneer, stretch or turn away dismissively'},
 'neutral': {
     'facial': 'Relaxed face, no strong expression, mouth closed or slightly open, eyes relaxed.',
     'body': 'Relaxed posture, no tension in the body, neutral stance'
     }
}

## Workflows

1. Grasp the overall situation.
2. Analyse how the character's emotion is expressed in the given situation.
3. Design the character's body and facial expressions, descriptions should be visually explicit statements that focus solely on observable, external features, AVOIDING internal states or inferred emotions..
3. Ensure that the expressions and movements are appropriate to the situation, it is allowed to make interaction with situation.
4. Output the emotion in json format.

## Output
Response in json format.
{"expression": {
    "character": "", # follow the input character
    "emotion": "", # follow the input emotion
    "body": "",
    "facial": ""
    }
}
"""

conditioned_frame = """Generate the observable body and facial expression of given character and emotion and situation:
Situation:
$passage

Character:
$character

Emotion:
$emotion
"""

one_shot_situation = 'Ye is sitting in the middle of a crowded movie theater. Shortly after the film has started, Ye realize that Ye made a mistake in the cinema and ended up in the wrong film.'
one_shot_emotion = 'fear'
one_shot_character = 'Ye'

one_shot_output = """
{"expression":{
    "character": "Ye",
    "emotion": "fear",
    "body": "Ye sits hunched with raised shoulders, fingers tapping his knees, feet shifting subtly, chest rising rapidly with short breaths, body visibly tense and compact.",
    "facial": "Ye's eyes are wide open, eyebrows lifted and stretched straight, mouth slightly agape with lips pulled tight, jaw tense, and cheeks slightly raised."
    },
}
"""
prompt_template = [
    {'role': 'system', 'content': condition_system},
    {
        'role': 'user', 'content': Template(conditioned_frame).substitute(
        passage=one_shot_situation,
        emotion=one_shot_emotion,
        character=one_shot_character,
        ),
    },
    {'role': 'assistant', 'content': one_shot_output},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]
