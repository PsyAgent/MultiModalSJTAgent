from __future__ import annotations

from string import Template

vng_condition_system = """
# Structured storyboard maker
你是一个专业的视觉叙事艺术师与心理学家，你的任务是根据给定的人格情境判断测验及其情景的知识图谱，基于视觉叙事语法（Visual Narrative Grammar, VNG）构建一个分镜脚本（storyboard）。
你需要确保分镜脚本只表达情景判断测验的情景（situation），而不要表达或暗示任何反应项（options）相关的内容。
返回的结果应为 **VNG 的 JSON 格式**，其中包含一个键 `"VNG"`，其值为一个字典。字典的键是 VNG 的各个叙事元素，值是对应的知识图谱。

## Background
### Visual Narrative Grammar (VNG)**：
VNG 是一种分析和构建视觉叙事的框架，描述了人类能够理解的，基于图像序列的视觉叙事。VNG 将视觉叙事分解为四种基本单元：
- **Establisher (E)**：引入角色与场景，建立语境与中性基调。
- **Initial (I)**：启动冲突或动作，呈现早期张力。
- **Prolongation (Pr)**：延缓至高潮的过渡与铺垫，通过细节与节奏增强紧张感。
- **Peak (P)**：高潮或转折点，呈现核心认知或决策瞬间。
上述的E，I，Pr，P单元可以组合成不同的叙事结构（如E-I-Pr-P、E-I-P、E-P等）以适应不同的叙事需求和复杂度。
> 在本任务中，可用配置：**E-I-Pr-P**、**E-I-P** 或 **E-P**（由素材复杂度决定）。你也必须遵守输入的单元类型与顺序，**不得新增、删除或重排**。

### 人格情景判断测验（SJT）：
人格情景判断测验（人格SJT）是一种心理测量工具，通过呈现能够激活目标人格特质相关的情境，通过评估个体在这些情境中的行为反应推断特质水平。
人格SJT 通常包含一个情景描述（situation）和多个反应选项（options），不同反应项揭示了不同水平的目标人格特质。
人格SJT通常需要避免情景强度（即情景对某一反应项的暗示）过高。如测量社会规范服从构念，红灯下是否过马路作为情景，其强烈暗示了“等待绿灯”的反应项，具有较高的情景强度，可能导致测量结果由情景决定而非被试特质。

## Goals
- **深度理解叙事弧结构**：掌握各个 VNG 元素的叙事功能。  
- **为每个 VNG 元素构建知识图谱**：在理解故事内容的基础上，为每个阶段创建对应的知识图谱。  
- **符合视觉叙事语法规则**：符合VNG单元的语法规则，确保输出分镜从属于“E-I-Pr-P”的顺序。

## Workflows
1. 理解整体叙事及其知识图谱。  
2. 使用知识图谱构建 VNG 结构。  
3. 检查各叙事要素的连贯性。  
4. 确保每个分镜的知识图谱的节点与关系均与输入知识图谱一致。

## Exceptions
- 若叙事非常简单，可只使用部分结构，如 **E-P**。  
- 若叙事较复杂，可使用扩展结构，如 **E-I-P-Pr-P**。

## Constraints
- 允许不同输出知识图谱中出现相同的节点和边。  
- 每个分镜的知识图谱中的节点和边，必须与输入知识图谱一致。  
- 每个分镜的节点之间必须由输入知识图谱中的边连接。  
- 输入知识图谱中的所有节点与边，必须包含在输出的知识图谱中。  
- 叙事弧必须完整；每个视觉叙事元素需具有清晰的叙事功能和逻辑衔接。  
- 除非叙事过于简单或复杂，一般应遵循 **E-I-P** 的叙事弧结构。  
- 不要混淆节点的标识符与值。例如，节点`object_1` 的值是“叶”，而非“object_1”。
- 任何视觉叙事不可暗示，或表达任何与反应项（options）相关的内容。

"""



few_shot_narrative_1 = """
{'situation': 'Ye is sitting in the middle of a crowded movie theater. Shortly after the film has started, Ye realize that Ye made a mistake in the cinema and ended up in the wrong film. How do Ye behave?',
 'options': {'A': "I don't change the cinema hall, because it's unpleasant for me if half a row has to stand up during the film.",
  'B': "I remain seated throughout the film, because I'm embarrassed if everyone else sees that I leave during the performance.",
  'C': 'I get up and go to the other cinema hall.',
  'D': 'I watch the beginning of the film and then decide whether to change the cinema hall.'}
  }
"""

few_shot_graph_1 = """
{'nodes': [
  ['object_1', {'type': 'object_node', 'value': 'Ye'}],
  ['object_2', {'type': 'object_node', 'value': 'movie theater'}],
  ['object_3', {'type': 'object_node', 'value': 'film'}],
  ['attribute|2|1', {'type': 'attribute_node', 'value': 'crowded'}],
  ['attribute|3|1', {'type': 'attribute_node', 'value': 'wrong'}],
  ['attribute|3|2', {'type': 'attribute_node', 'value': 'has started'}]],
 'edges': [
  ['object_1','object_2',{'type': 'relation_edge', 'value': 'sitting in middle'}],
  ['object_1', 'object_3', {'type': 'relation_edge', 'value': 'watching'}],
  ['attribute|2|1', 'object_2', {'type': 'attribute_edge'}],
  ['attribute|3|1', 'object_3', {'type': 'attribute_edge'}],
  ['attribute|3|2', 'object_3', {'type': 'attribute_edge'}]]}
"""
few_shot_output_1 = """
{
  "VNG": {
    "E": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_2", {"type": "object_node", "value": "movie theater"}],
        ["attribute|2|1", {"type": "attribute_node", "value": "crowded"}]
      ],
      "edges": [
        ["object_1", "object_2", {"type": "relation_edge", "value": "sitting in middle"}],
        ["attribute|2|1", "object_2", {"type": "attribute_edge"}]
      ]
    },
    "I": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_3", {"type": "object_node", "value": "film"}],
        ["attribute|3|2", {"type": "attribute_node", "value": "has started"}]
      ],
      "edges": [
        ["object_1", "object_3", {"type": "relation_edge", "value": "watching"}],
        ["attribute|3|2", "object_3", {"type": "attribute_edge"}]
      ]
    },
    "P": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_3", {"type": "object_node", "value": "film"}],
        ["attribute|3|1", {"type": "attribute_node", "value": "wrong"}]
      ],
      "edges": [
        ["object_1", "object_3", {"type": "relation_edge", "value": "watching"}],
        ["attribute|3|1", "object_3", {"type": "attribute_edge"}]
      ]
    }
  }
}
"""

few_shot_narrative_2 = """
{'situation': "Ye on the tram with a friend. At one stop, an attractive woman gets on. As she passes Ye, Ye's friend whistles after her. The woman turns irritated and looks at Ye. How do Ye behave?",
 'options': {'A': 'I embarrassingly look to the side and avoid eye contact.',
  'B': 'I embarrassingly look to the side and later tell my friend that I found his action quite stupid.',
  'C': 'I compliment her.',
  'D': 'I laugh and point my finger at my friend.'}
}
"""
few_shot_graph_2 = """
{'nodes': [['object_1', {'type': 'object_node', 'value': 'Ye'}],
  ['object_2', {'type': 'object_node', 'value': 'friend'}],
  ['object_3', {'type': 'object_node', 'value': 'woman'}],
  ['object_4', {'type': 'object_node', 'value': 'tram'}],
  ['attribute|3|1', {'type': 'attribute_node', 'value': 'attractive'}],
  ['attribute|3|2', {'type': 'attribute_node', 'value': 'irritated'}]],
 'edges': [['object_1', 'object_4', {'type': 'relation_edge', 'value': 'on'}],
  ['object_2', 'object_4', {'type': 'relation_edge', 'value': 'on'}],
  ['object_2', 'object_3', {'type': 'relation_edge', 'value': 'whistles at'}],
  ['object_3', 'object_4', {'type': 'relation_edge', 'value': 'gets on'}],
  ['object_3', 'object_1', {'type': 'relation_edge', 'value': 'looks at'}],
  ['attribute|3|1', 'object_3', {'type': 'attribute_edge'}],
  ['attribute|3|2', 'object_3', {'type': 'attribute_edge'}]]}
"""

few_shot_output_2 = """
{
  "VNG": {
    "E": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_2", {"type": "object_node", "value": "friend"}],
        ["object_4", {"type": "object_node", "value": "tram"}]
      ],
      "edges": [
        ["object_1", "object_4", {"type": "relation_edge", "value": "on"}],
        ["object_2", "object_4", {"type": "relation_edge", "value": "on"}]
      ]
    },
    "I": {
      "nodes": [
        ["object_3", {"type": "object_node", "value": "woman"}],
        ["object_4", {"type": "object_node", "value": "tram"}],
        ["attribute|3|1", {"type": "attribute_node", "value": "attractive"}]
      ],
      "edges": [
        ["object_3", "object_4", {"type": "relation_edge", "value": "gets on"}],
        ["attribute|3|1", "object_3", {"type": "attribute_edge"}]
      ]
    },
    "Pr": {
      "nodes": [
        ["object_2", {"type": "object_node", "value": "friend"}],
        ["object_3", {"type": "object_node", "value": "woman"}]
      ],
      "edges": [
        ["object_2", "object_3", {"type": "relation_edge", "value": "whistles at"}]
      ]
    },
    "P": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_3", {"type": "object_node", "value": "woman"}],
        ["attribute|3|2", {"type": "attribute_node", "value": "irritated"}]
      ],
      "edges": [
        ["object_3", "object_1", {"type": "relation_edge", "value": "looks at"}],
        ["attribute|3|2", "object_3", {"type": "attribute_edge"}]
      ]
    }
  }
}

"""

few_shot_narrative_3 = """
{'situation': 'Ye give a presentation to the colleagues in Ye's department. As Ye speak, Ye notice that two of Ye's colleagues suddenly start laughing and whispering to each other. How do Ye behave?',
 'options': {'A': 'I think about whether I said something funny and look down at myself to see if my clothes are impeccable.',
  'B': 'I let myself be put off and have to look at my notes.',
  'C': 'I proceed with my presentation.',
  'D': 'I pause briefly to ask whether something is not clear or understandable to my colleagues.'}}
"""
few_shot_graph_3 = """
{'nodes': [['object_1', {'type': 'object_node', 'value': 'Ye'}],
  ['object_2', {'type': 'object_node', 'value': 'presentation'}],
  ['object_3', {'type': 'object_node', 'value': 'two colleagues'}],
  ['object_4', {'type': 'object_node', 'value': 'department'}],
  ['attribute|3|1', {'type': 'attribute_node', 'value': 'laughing'}],
  ['attribute|3|2',{'type': 'attribute_node', 'value': 'whispering to each other'}]],
 'edges': [['object_1', 'object_2', {'type': 'relation_edge', 'value': 'gives'}],
  ['object_1', 'object_4', {'type': 'relation_edge', 'value': 'belongs to'}],
  ['object_1', 'object_3', {'type': 'relation_edge', 'value': 'notices'}],
  ['object_2', 'object_4', {'type': 'relation_edge', 'value': 'in'}],
  ['object_3', 'object_4', {'type': 'relation_edge', 'value': 'belongs to'}],
  ['attribute|3|1', 'object_3', {'type': 'attribute_edge'}],
  ['attribute|3|2', 'object_3', {'type': 'attribute_edge'}]]}
"""

few_shot_output_3 = """
{
  "VNG": {
    "E": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_2", {"type": "object_node", "value": "presentation"}],
        ["object_4", {"type": "object_node", "value": "department"}]
      ],
      "edges": [
        ["object_1", "object_2", {"type": "relation_edge", "value": "gives"}],
        ["object_1", "object_4", {"type": "relation_edge", "value": "belongs to"}],
        ["object_2", "object_4", {"type": "relation_edge", "value": "in"}]
      ]
    },
    "P": {
      "nodes": [
        ["object_1", {"type": "object_node", "value": "Ye"}],
        ["object_2", {"type": "object_node", "value": "presentation"}],
        ["object_3", {"type": "object_node", "value": "two colleagues"}],
        ["object_4", {"type": "object_node", "value": "department"}],
        ["attribute|3|1", {"type": "attribute_node", "value": "laughing"}],
        ["attribute|3|2", {"type": "attribute_node", "value": "whispering to each other"}]
      ],
      "edges": [
        ["object_1", "object_2", {"type": "relation_edge", "value": "gives"}],
        ["object_1", "object_4", {"type": "relation_edge", "value": "belongs to"}],
        ["object_1", "object_3", {"type": "relation_edge", "value": "notices"}],
        ["object_2", "object_4", {"type": "relation_edge", "value": "in"}],
        ["object_3", "object_4", {"type": "relation_edge", "value": "belongs to"}],
        ["attribute|3|1", "object_3", {"type": "attribute_edge"}],
        ["attribute|3|2", "object_3", {"type": "attribute_edge"}]
      ]
    }
  }
}
"""

conditioned_frame = """Convert the following textual narrative and its knowledge graph into an storyboard constructed by VNG panels' knowledge graph:

Textual narrative:
$passage

Knowledge graph:
$graph
"""
prompt_template = [
    {'role': 'system', 'content': vng_condition_system},
    {
        'role': 'user', 'content': Template(
            conditioned_frame,
        ).substitute(passage=few_shot_narrative_1, graph=few_shot_graph_1),
    },
    {'role': 'assistant', 'content': few_shot_output_1},
    {
        'role': 'user', 'content': Template(
            conditioned_frame,
        ).substitute(passage=few_shot_narrative_2, graph=few_shot_graph_2),
    },
    {'role': 'assistant', 'content': few_shot_output_2},
    {
        'role': 'user', 'content': Template(
            conditioned_frame,
        ).substitute(passage=few_shot_narrative_3, graph=few_shot_graph_3),
    },
    {'role': 'assistant', 'content': few_shot_output_3},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]
