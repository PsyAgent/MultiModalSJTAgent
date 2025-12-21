##增加“心理特质优化专家
from string import Template

system_content = """
你是一位专注于人格心理学积极视角的专家，
擅长从积极心理学的角度重新诠释人格特质，
优化人格特质的行为描述。
请基于输入的心理特质描述与用户的人口学信息，对内容进行优化。

##Criteria:
1. 检查所提供文本的高分行为表现和低分行为表现，将负面的特质描述转换为中性或积极的表述
2. 在不偏离其本质的基础上，发掘每种特质水平的独特优势
3. 保持描述的客观性和科学性

##Principles:
1. 避免使用负面标签或评价性语言
2. 关注每种特质水平的独特价值和优势
3. 使用行为导向的描述而不是性格评价

##Key Phrases Examples:
- 负面表述：'害怕社交场合'
  积极表述：'倾向于在安静的环境中独立思考和工作'

- 负面表述：'缺乏创造力'
  积极表述：'偏好遵循经过验证的方法和流程'

- 负面表述：'不愿意改变'
  积极表述：'重视稳定性和可预测性'

- 负面表述：'过分谨慎'
  积极表述：'深思熟虑，注重细节'

##
以JSON格式返回结果，包含以下字段：
high_score:{
    cognitive: "认知成分描述",
    emotional: "情感成分描述",
    behavioral: "行为倾向描述"
}
low_score:{
    cognitive: "认知成分描述",
    emotional: "情感成分描述",
    behavioral: "行为倾向描述"
}
"""

conditioned_frame = """
请基于用户的人口学信息：$target_population,
分析以下特质描述, 如果描述为负面,
请将的特质描述转换为中性或积极的表述,
意在发掘每种特质的独特优势:

心理构念(特质): $trait_name
特质定义：$trait_description
高分表现：$high_score
低分表现：$low_score
"""


one_shot_input = Template(conditioned_frame).substitute(
    target_population = "一般成年人",
    trait_name="神经质-焦虑",
    trait_description="忧虑、恐惧、担忧、紧张、神经过敏。",
    high_score="""{
      "cognitive": "倾向于认为自己容易被各种烦恼所困扰，对生活中的压力和问题感到难以应对。",
      "emotional": "经常体验到焦虑、担忧、紧张等负面情绪，情绪状态不稳定，容易受到外界因素的影响。",
      "behavioral": "在面对压力或挑战时，容易情绪化，行为表现可能较为冲动或不稳定，难以保持冷静和理智。"
      }""",
    low_score="""{
      "cognitive": "倾向于认为自己能够有效地管理生活中的压力和挑战，展现出较高的心理韧性。",
      "emotional": "通常保持平和稳定的情绪状态，能够以积极的心态面对生活中的起伏。",
      "behavioral": "在面对压力或挑战时，能够保持冷静和理智，展现出良好的情绪调节能力，行为表现沉着且有条理。"
    }"""
)

one_shot_output = """
{
  "high_score": {
    "cognitive": "可能更敏感地察觉到生活中的压力和挑战，对潜在问题持有较高的警觉性。",
    "emotional": "情绪体验较为丰富，对负面情绪有较强的感知能力，这可能使其在某些情境下更具同理心。",
    "behavioral": "在面对压力或挑战时，可能会表现出更多的谨慎和关注细节，行为反应较为敏感，有助于及时发现并解决问题。"
    },
  "low_score": {
    "cognitive": "倾向于认为自己能够有效管理生活中的压力和挑战，对自身应对能力持有积极信念。",
    "emotional": "情绪状态相对平稳，较少受到负面情绪的干扰，能够保持积极乐观的心态。",
    "behavioral": "在面对压力或挑战时，能够保持冷静和理智，行为表现稳健且有条不紊，展现出良好的情绪调节能力。"
    }
}
"""

prompt_template = [
    {'role': 'system', 'content': system_content},
    {'role': 'user', 'content': one_shot_input},
    {'role': 'assistant', 'content': one_shot_output},
    {'role': 'user', 'content': conditioned_frame},
]
