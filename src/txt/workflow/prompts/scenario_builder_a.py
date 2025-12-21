from __future__ import annotations

from string import Template

sys_prompt = """你是一个心理学家, 
请基于用户的人口学信息与输入的情景主题，
以及心理特质(构念)，及其蕴含的认知，行为与情绪特征，
思考并设计能够激活此心理特质(构念)的具体触发事件

以JSON格式返回结果，包含以下字段：
{
    cues: ["触发事件1", "触发事件2", "..."]
}
##要求
1.请确保分析准确深入，抓住题目核心测量的心理过程。
2.触发事件具有普遍适用性，适用于任何职业、任何人群。
3.只返回JSON格式数据，不要有其他文字。
"""

conditioned_frame = """
请基于用户的人口学信息: $target_population,
在情景主题的框架下，根据构念及其相关的认知，行为与情绪特征设计能够激活特质的 $n_cue 个触发事件：

情景主题: $situation_theme
心理构念(特质): $trait_name
低分特质描述: $low_score
高分特质描述: $high_score
"""

prompt_template = [
    {'role': 'system', 'content': sys_prompt},
    {'role': 'user', 'content': conditioned_frame},
]