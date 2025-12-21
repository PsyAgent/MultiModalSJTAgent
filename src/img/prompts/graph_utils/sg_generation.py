from __future__ import annotations

from string import Template

sg_condition_system = """
# You are a scene graph generation master.

## GOAL
Your task is to generate a scene graph from the provided narrative.

## INPUT
You will be given a narrative.

## WORKFLOW
1. Identify the objects in the narrative.
2. Identify the attributes of the objects.
3. Identify the relations between the objects.
4. Settle the objects, attributes, and relations in graph.

## CONSTRAINTS
- The objects should be unique and not repeated.
- The attributes should be unique and not repeated.
- The relations should be unique and not repeated.
- The graph only have 2 types of nodes: object_node and attribute_node.
- The graph only have 2 types of edges: relation_edge and attribute_edge.
- The node and edge content should be clear and short.
- DO NOT confuse the node's value with its identifier. For example, object_1's value is its corresponding content like "Ye", not "object_1".

## OUTPUT
A JSON dict with the following structure:
{
    "SceneGraph": {
        "nodes":[
            ["object_id", {"type": "object_node", "value": "..."}],
            ...
        ],
        "edges":[
            ["object_id", "object_id", {"type": "relation_edge", "value": "..."}],
            ...
            ["attribute|id|id", "object_id", {"type": "attribute_edge"}],
            ...
        ]
    }
}
"""

conditioned_frame = """Convert the following narrative to scene graph.

Narrative:
$passage
"""

few_shots_narrative_1 = """Radio City is India's first private FM radio station and was started on 3 July 2001.
It plays Hindi, English and regional songs.
Radio City recently forayed into New Media in May 2008 with the launch of a music portal - PlanetRadiocity.com that offers music related news, videos, songs, and other music-related features.
"""

few_shots_output_1 = """
{
    "SceneGraph": {
        "nodes": [
            ["object_1", {"type": "object_node", "value": "Radio City"}],
            ["object_2", {"type": "object_node", "value": "PlanetRadiocity.com"}],
            ["attribute|1|1", {"type": "attribute_node", "value": "India's first private FM radio station"}],
            ["attribute|1|2", {"type": "attribute_node", "value": "Started on 3 July 2001"}],
            ["attribute|1|3", {"type": "attribute_node", "value": "Plays Hindi, English and regional songs"}],
            ["attribute|1|4", {"type": "attribute_node", "value": "Forayed into New Media in May 2008"}],
            ["attribute|2|1", {"type": "attribute_node", "value": "Music portal"}],
            ["attribute|2|2", {"type": "attribute_node", "value": "Offers music related news, videos, songs, and other music-related features"}]
        ],
        "edges": [
            ["object_1", "object_2", {"type": "relation_edge", "value": "launched"}],
            ["attribute|1|1", "object_1", {"type": "attribute_edge"}],
            ["attribute|1|2", "object_1", {"type": "attribute_edge"}],
            ["attribute|1|3", "object_1", {"type": "attribute_edge"}],
            ["attribute|1|4", "object_1", {"type": "attribute_edge"}],
            ["attribute|2|1", "object_2", {"type": "attribute_edge"}],
            ["attribute|2|2", "object_2", {"type": "attribute_edge"}]
        ]
    }
}
"""

few_shots_narrative_2 = """
Shortly after sending a private email with holiday pictures, Ye realize that Ye sent the email to the wrong address.
By mistake, Ye's bank advisor is the email recipient.
The next day, Ye happen to meet Ye's bank advisor across the stree
"""
few_shots_output_2 = """{
    'SceneGraph':
        {'nodes': [
            ['object_1', {'type': 'object_node', 'value': 'Ye'}],
            ['object_2', {'type': 'object_node', 'value': 'bank advisor'}],
            ['object_3', {'type': 'object_node', 'value': 'email'}],
            ['object_4', {'type': 'object_node', 'value': 'street'}],
            ['attribute|3|1', {'type': 'attribute_node', 'value': 'private'}],
            ['attribute|3|2', {'type': 'attribute_node', 'value': 'contains holiday pictures'}],
            ['attribute|3|3', {'type': 'attribute_node', 'value': 'sent to wrong address'}]],
        'edges': [
            ['object_1', 'object_3', {'type': 'relation_edge', 'value': 'sent'}],
            ['object_3', 'object_2', {'type': 'relation_edge', 'value': 'received by'}],
            ['object_1', 'object_2', {'type': 'relation_edge', 'value': 'met'}],
            ['object_1', 'object_4', {'type': 'relation_edge', 'value': 'across'}],
            ['object_2', 'object_4', {'type': 'relation_edge', 'value': 'across'}],
            ['attribute|3|1', 'object_3', {'type': 'attribute_edge'}],
            ['attribute|3|2', 'object_3', {'type': 'attribute_edge'}],
            ['attribute|3|3', 'object_3', {'type': 'attribute_edge'}]
        ]
    }
}
"""

prompt_template = [
    {'role': 'system', 'content': sg_condition_system},
    {
        'role': 'user', 'content': Template(
            conditioned_frame,
        ).substitute(passage=few_shots_narrative_1),
    },
    {'role': 'assistant', 'content': few_shots_output_1},
    {
        'role': 'user', 'content':  Template(
            conditioned_frame,
        ).substitute(passage=few_shots_narrative_2),
    },
    {'role': 'assistant', 'content': few_shots_output_2},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]
