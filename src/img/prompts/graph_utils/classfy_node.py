from __future__ import annotations

from string import Template

condition_system = """
# node type analyst
Based on the given situation, and the words from it.
Indentify if the words belong to 'character', 'scene', 'object'.
Response in json, key is 'classification', value is 'character', 'scene', 'object'.
Only these three types of objects ['character', 'scene', 'object'] are identified, and the rest should be ignored.
"""

conditioned_frame = """
Generate the node type,
response in json!


Situation:
$passage

Words:
$words
"""

one_shot_situation = """
Ye're on the tram with a friend.
At one stop, an attractive woman gets on.
The woman has a nice phone.
As she passes Ye, Ye's friend whistles after her.
The woman turns irritated and looks at Ye"""

one_shot_words = """
['woman', 'tram', 'friend', 'phone', 'Ye', 'attractive', 'nice', 'whistles after', 'irritated']
"""

one_shot_output = """
{
    'classification': {
        'character': ['Ye', 'friend', 'woman'],
        'scene': ['tram'],
        'object': ['phone'],
    }
}
"""
prompt_template = [
    {'role': 'system', 'content': condition_system},
    {'role': 'user', 'content': Template(conditioned_frame).substitute(passage=one_shot_situation, words=one_shot_words)},
    {'role': 'assistant', 'content': one_shot_output},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]
