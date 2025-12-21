from __future__ import annotations

from string import Template

ner_system = """Your task is to extract named entities from the given paragraph and perform coreference resolution.
Identify all named entities such as people, organizations, locations, dates, and other relevant entities.
Note that pronouns like "you" must also be identified as named entities.
For entities that share the same meaning (for example, "cinema" and "movie theater"), consolidate them into a single entry without repetition.
Respond with a JSON list of unique named entities.
"""

one_shot_ner_paragraph = """Radio City is India's first private FM radio station and was started on 3 July 2001.
It plays Hindi, English and regional songs.
Radio City recently forayed into New Media in May 2008 with the launch of a music portal - PlanetRadiocity.com that offers music related news, videos, songs, and other music-related features."""

one_shot_ner_output = """{"named_entities":
    ["Radio City", "India", "3 July 2001", "Hindi", "English", "May 2008", "PlanetRadiocity.com"]
}
"""

ner_conditioned_frame = """$passage"""

prompt_template = [
    {'role': 'system', 'content': ner_system},
    {'role': 'user', 'content': one_shot_ner_paragraph},
    {'role': 'assistant', 'content': one_shot_ner_output},
    {'role': 'user', 'content': ner_conditioned_frame},
]
