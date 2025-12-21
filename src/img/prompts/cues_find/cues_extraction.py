from __future__ import annotations

from string import Template

system = """
# Cues Recognition Assistant

## GOAL

帮助从给定的情境知识图谱中提取并识别能够激活目标人格特质的核心线索，并以结构化、可机器读取的 JSON 格式输出每个分段中最具代表性的线索。

## BACKGROUND

- **特质激活理论（Trait Activation Theory, TAT）**: 该理论认为，只有当情境线索能激活某一人格特质时，该特质才会被表达。核心任务是识别情境中最能激活目标特质的要素。
- **知识图谱结构**:
  场景被划分为多个阶段分段（如 E、I、P），每段由以下五种元组模式之一表示：
  1. `att|obj`: attribute → object
  2. `obj-obj`: object → relation → object
  3. `att|obj-obj`: attribute → object → relation → object
  4. `obj-att|obj`: object → relation → attribute → object
  5. `att|obj-att|obj`: attribute → object → relation → attribute → object

## INPUT

- **Situation Text**: 场景的原始叙事描述。
- **Knowledge Graphs**: 将分段（键）映射到遵循上述模式的元组列表。
- **Target Trait**: 需要激活和识别的人格特质。

## WORKFLOW

1. **Parse Input**: 读取并校验情境文本、知识图谱与目标特质。
2. **Segment-wise Analysis**: 对于每个分段键（例如 E、I、P）：
   1. 检索该分段中的所有元组。
   2. 评估每个元组与目标特质的激活相关性。
   3. 做出决策，判断该分段是否包含能激活目标特质的线索。
   4. 如果存在激活线索，选择其中最具代表性的一个元组。
   5. 如果没有相关线索，明确输出一个空列表 (`[]`)
3. **Aggregate Results**: 按键收集每个分段的选定线索。
4. **Format Output**: 生成一个顶层的 `"cues"` 键，将每个分段映射到其线索对象列表。

## CONSTRAINTS

- 你的任务不是简单挑选“与特质有关”的元组，而是选择能够激活该特质的线索。
- 确保所有输出中的节点与边均来源于输入的知识图谱。
- 分析每个分段时要独立进行；不要跨键匹配。
- 每个分段输出恰好一个最具代表性的线索；如果某个分段没有激活线索，明确输出一个空列表 (`[]`)。
- 不一定每个分段都包含线索，一定要仔细斟酌。
- 不同分段均有线索的情况下，确保线索不与VNG的叙事功能冲突，如激活特质的关键在P时，E与I往往不包含线索。
- 输出的线索必须使用原始元组模式之一，并保留元素的顺序。
- 最终结果必须是结构化的、可机器读取的 JSON。
- 至少有一个分段具有线索。

## OUTPUT

返回如下结构的 JSON 对象：
```json
{
  "cues": {
    "E": [ { "type": "att|obj", "content": ["exampleAttribute", "exampleObject"] } ],
    "I": [],
    "P": [ { "type": "obj-att|obj", "content": ["exampleObject", "exampleRelation", "exampleAttribute", "exampleObject"] } ]
  }
}
```
"""

one_shot_trait = 'Neuroticism'

one_shot_paragraph = """
You are sitting in the middle of a crowded movie theater.
Shortly after the film has started, you realize that you made a mistake in the cinema and ended up in the wrong film.
"""

one_shot_graph = """
{'E': {'att|obj': [('crowded', 'movie theater')],
  'obj-obj': [('Ye', 'sitting in', 'movie theater')],
  'att|obj-obj': [],
  'obj-att|obj': [('Ye', 'sitting in', 'crowded', 'movie theater')],
  'att|obj-att|obj': []},
 'I': {'att|obj': [],
  'obj-obj': [('film', 'started in', 'movie theater')],
  'att|obj-obj': [],
  'obj-att|obj': [],
  'att|obj-att|obj': []},
 'P': {'att|obj': [('wrong', 'film')],
  'obj-obj': [('Ye', 'ended up in', 'film')],
  'att|obj-obj': [],
  'obj-att|obj': [('Ye', 'ended up in', 'wrong', 'film')],
  'att|obj-att|obj': []}
}
"""

one_shot_output = """
{
  "cues": {
    "E": [ { "type": "att|obj", "content": ["crowded","movie theater"] } ],
    "I": [],
    "P": [ { "type": "obj-att|obj", "content": ["Ye","ended up in","wrong","film"] } ]
  }
}
"""

two_shot_trait = 'Agreeableness'

two_shot_paragraph = """
Ye argue with Ye's partner about a detail in a film Ye watched together.
Ye is absolutely sure that Ye's partner is wrong and Ye is right
"""

two_shot_graph = """
{'E': {'att|obj': [],
  'obj-obj': [('Ye', 'watched', 'film'), ('partner', 'watched', 'film')],
  'att|obj-obj': [],
  'obj-att|obj': [],
  'att|obj-att|obj': []},
 'I': {'att|obj': [],
  'obj-obj': [('Ye', 'argue with', 'partner'),
   ('Ye', 'about', 'detail'),
   ('partner', 'about', 'detail')],
  'att|obj-obj': [],
  'obj-att|obj': [],
  'att|obj-att|obj': []},
 'P': {'att|obj': [('absolutely sure', 'Ye'),
   ('believes right', 'Ye'),
   ('believes wrong', 'partner')],
  'obj-obj': [('Ye', 'argue with', 'partner')],
  'att|obj-obj': [('absolutely sure', 'Ye', 'argue with', 'partner'),
   ('believes right', 'Ye', 'argue with', 'partner')],
  'obj-att|obj': [('Ye', 'argue with', 'believes wrong', 'partner')],
  'att|obj-att|obj': [('absolutely sure',
    'Ye',
    'argue with',
    'believes wrong',
    'partner'),
   ('believes right', 'Ye', 'argue with', 'believes wrong', 'partner')]}}
"""

two_shot_output = """
{
  "cues": {
    "E": [],
    "I": [
      {
        "type": "obj-obj",
        "content": ["Ye", "argue with", "partner"]
      }
    ],
    "P": [
      {
        "type": "att|obj-att|obj",
        "content": ["believes right", "Ye", "argue with", "believes wrong", "partner"]
      }
    ]
  }
}

"""

four_shot_trait = 'Conscientiousnesss'

four_shot_paragraph = """
Ye watch TV in the evening and Ye is very tired.
Just as Ye is about to turn off the TV, Ye realize that one of Ye's favorite shows has just started.
Tomorrow Ye have a long working day ahead of Ye and have to get up early
"""

four_shot_graph = """
{'E': {'att|obj': [('in the evening', 'TV'), ('tired', 'Ye')],
  'obj-obj': [('Ye', 'watch', 'TV')],
  'att|obj-obj': [('tired', 'Ye', 'watch', 'TV')],
  'obj-att|obj': [('Ye', 'watch', 'in the evening', 'TV')],
  'att|obj-att|obj': [('tired', 'Ye', 'watch', 'in the evening', 'TV')]},
 'I': {'att|obj': [],
  'obj-obj': [('Ye', 'realize has started', 'favorite show')],
  'att|obj-obj': [],
  'obj-att|obj': [],
  'att|obj-att|obj': []},
 'P': {'att|obj': [('long', 'working day'),
   ('have to get up early', 'working day')],
  'obj-obj': [('Ye', 'have', 'working day')],
  'att|obj-obj': [],
  'obj-att|obj': [('Ye', 'have', 'long', 'working day'),
   ('Ye', 'have', 'have to get up early', 'working day')],
  'att|obj-att|obj': []
  }
}
"""

four_shot_output = """
{
  "cues": {
    "E": [],
    "I": [],
    "P": [
      {
        "type": "att|obj",
        "content": ["have to get up early", "working day"]
      }
    ]
  }
}

"""

conditioned_frame = """
SITUATION TEXT:
$passage

TARGET TRAIT:
$trait

KNOWLEDGE GRAPHS:
$graphs


MAKE SURE ALL THE OUT PUT NODES AND EDGES FROM THE INPUT KNOWLEDGE graphs AND RESPONSE IN JSON FORMAT!
"""

prompt_template = [
    {'role': 'system', 'content': system},
    {'role': 'user', 'content': Template(conditioned_frame).substitute(passage=one_shot_paragraph, graphs=one_shot_graph, trait=one_shot_trait)},
    {'role': 'assistant', 'content': one_shot_output},
    {'role': 'user', 'content': Template(conditioned_frame).substitute(passage=two_shot_paragraph, graphs=two_shot_graph, trait=two_shot_trait)},
    {'role': 'assistant', 'content': two_shot_output},
    {'role': 'user', 'content': Template(conditioned_frame).substitute(passage=four_shot_paragraph, graphs=four_shot_graph, trait=four_shot_trait)},
    {'role': 'assistant', 'content': four_shot_output},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]
