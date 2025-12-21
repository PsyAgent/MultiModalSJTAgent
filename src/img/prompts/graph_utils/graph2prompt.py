from __future__ import annotations

from string import Template

system = """
# Graph to Image Generation Prompt

## Objective

This work aims to systematically translate an input scene graph into a JSON-formatted prompt directly usable by generative image models (e.g., gpt-5, Midjourney) without losing the graph’s structural or semantic information. By precisely mapping entities, attributes, and relationships, we ensure that the generated images faithfully reproduce the source data’s visual details, spatial composition, and atmospheric qualities.

## Background

- **Graph Structure**: A scene graph consists of nodes (object_node and attribute_node) and edges (relation_edge) that describe relationships between entities.
- **Attribute Annotations**: Attribute nodes (e.g., `_body`, `_face`, `_scene`) record directly renderable visual features in their `annot` field.
- **Prompt Template**: A structured field template is employed to map graph information uniformly, improving prompt readability and consistency.

## Methodology

1. **Graph Parsing**
   - Extract all object nodes to identify primary and secondary visual entities.
   - Extract `annot` annotations from attribute nodes and categorize them into facial expressions, body poses, and scene descriptions.
   - Infer interaction verbs between characters and objects based on relation edges, forming semantically coherent action descriptions.

2. **Structured Mapping**
   Define the following core fields:
   - `character_interaction_with_scene`: Describes the character’s position and behavior in the scene (e.g., “Ye seated in a crowded movie theater watching a film”).
   - `facial_expression`: The annotation describing the character’s facial expression.
   - `gesture`: The annotation describing the character’s body pose.
   - `scene_description`: Describes viewpoint, composition, lighting, color palette, and atmosphere.
   - `object_description`: A concise description of key objects and their attributes (e.g., “the film on screen is wrong—a misplayed reel showing unintended content”).
   - `action`: The character’s current action or realization (e.g., “realizes he is watching the wrong film”).

3. **JSON Prompt Generation**
   Insert the above fields into a unified template to produce the final executable JSON prompt.

4. Make output clear and smooth, if there is no information from input about Structured Mapping keys, ignore these keys, NO need to add any information like 'N/A' or 'unknown'.
## JSON Template

```json
{
  "prompt": "Create a {size} {style} image of {character_interaction_with_scene}, {character}'s facial expression: {facial_expression}, {character}'s gesture: {gesture}, scene's description: {scene_description}, {objects}'s description: {object_description}, {character}'s action: {action}"
}
```

## Constraints

- Strictly preserve the original graph’s nodes and edges structure; additions or deletions of semantic information are prohibited.
- The `character`, `objects`, and attribute fields must exactly match the `value` entries in the graph; synonyms or omissions are not allowed.
- Do not introduce any unannotated visual elements or subjective modifiers.
- Use simple present tense and third-person perspective consistently; each sentence should convey a single point with concise structure.
- Ensure that the generated JSON string is properly escaped and can be directly embedded into image generation scripts.
"""
one_shot_paragraph = """
{'nodes': [['object_1', {'type': 'object_node', 'value': 'Ye'}],
  ['object_3', {'type': 'object_node', 'value': 'film'}],
  ['attribute|3|1', {'type': 'attribute_node', 'value': 'wrong'}],
  ['attribute|1|1',
   {'type': 'attribute_node',
    'value': '_body',
    'annot': "Ye's body is visibly stiff and tense, with shoulders raised. He leans slightly forward, hands clasped tightly together or gripping the armrests, possibly fidgeting or tapping fingers on his knees with quick, shallow breaths."}],
  ['attribute|1|2',
   {'type': 'attribute_node',
    'value': '_face',
    'annot': "Ye's eyes are wide and alert, eyebrows raised and straight across, mouth slightly open in a tense shape, and his face appears pale or flushed with worry."}],
  ['attribute|3|2',
   {'type': 'attribute_node',
    'value': '_scene',
    'annot': {'film': {'view': 'Close-up with a slight tilt (Dutch angle) on the rows of heads in front',
      'composition': 'Oppressive central alignment, running a tunnel through the composition',
      'lighting': 'Low-key lighting with a harsh spotlight effect from the screen casting shadows',
      'color Palette': 'Muted, desaturated tones with emphasis on dark reds and deep blacks',
      'Mood/Atmosphere': 'Claustrophobic atmosphere with dim outlines of seats creating texture',
      'Focus': 'Shallow focus on seat fabric details with surrounding heads soft blurred',
      'framing': 'Tight framing using surrounding heads and seatbacks to confine space'}}}]],
 'edges': [['object_1',
   'object_3',
   {'type': 'relation_edge', 'value': 'watched'}],
  ['attribute|3|1', 'object_3', {'type': 'attribute_edge'}],
  ['attribute|1|1', 'object_1', {'type': 'attribute_edge'}],
  ['attribute|1|2', 'object_1', {'type': 'attribute_edge'}],
  ['attribute|3|2', 'object_3', {'type': 'attribute_edge'}]]}
"""

size = '1024x1024'
style = 'realistic'

one_shot_output = """
{
  "prompt": "Create a 1024x1024 realistic image of Ye seated in a crowded movie theater watching a film, Ye's facial expression: Ye's eyes are wide and alert, eyebrows raised and straight across, mouth slightly open in a tense shape, and his face appears pale or flushed with worry, Ye's gesture: Ye's body is visibly stiff and tense, with shoulders raised. He leans slightly forward, hands clasped tightly together or gripping the armrests, possibly fidgeting or tapping fingers on his knees with quick, shallow breaths, scene's description: Close-up with a slight Dutch angle on the rows of heads in front, oppressive central alignment running a tunnel through the composition, low-key lighting with a harsh spotlight effect from the screen casting shadows, muted desaturated tones emphasizing dark reds and deep blacks, a claustrophobic atmosphere with dim outlines of seats creating texture, shallow focus on seat fabric details with surrounding heads softly blurred, tight framing using surrounding heads and seatbacks to confine space, film's description: the film on screen is wrong—a misplayed reel showing unintended content."
}

"""

conditioned_frame = """
GRAPH:
$passage

IMAGE SIZE
$size

STYLE
$style
"""

prompt_template = [
    {'role': 'system', 'content': system},
    {'role': 'user', 'content': Template(conditioned_frame).substitute(passage=one_shot_paragraph, size = size, style = style)},
    {'role': 'assistant', 'content': one_shot_output},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]
