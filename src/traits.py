"""NEO-PI-R 面（facet）与大五维度（domain）之间的描述工具。

图像 / 视频流水线里的提示词都以大五人格为知识框架，要求“待测特质”是五大
维度之一。而量表元数据里的 `facet_name` 是面级名称（如「价值观」「忧虑」），
直接传进去时模型有时会拒答并返回类似「"价值观"不在5种特质之一」的内容，
导致整题生成失败。

`format_trait` 把面级信息补全成「维度 + 面」的完整描述，既保证模型能落到
五大维度上，又不丢掉面级的针对性。
"""
from __future__ import annotations

# NEO-PI-R 题目编号首字母 -> (英文维度, 中文维度)
DOMAIN_BY_CODE = {
    'N': ('Neuroticism', '神经质'),
    'E': ('Extraversion', '外向性'),
    'O': ('Openness', '开放性'),
    'A': ('Agreeableness', '宜人性'),
    'C': ('Conscientiousness', '责任心'),
}

# 中文维度名 -> 英文维度名（元数据里 domain 字段用的是中文）
DOMAIN_EN_BY_ZH = {
    '神经质': 'Neuroticism',
    '外向性': 'Extraversion',
    '外倾性': 'Extraversion',
    '开放性': 'Openness',
    '经验开放性': 'Openness',
    '宜人性': 'Agreeableness',
    '责任心': 'Conscientiousness',
    '尽责性': 'Conscientiousness',
}


def domain_of(trait_id: str | None, trait_meta: dict | None = None) -> tuple[str, str]:
    """返回 (英文维度, 中文维度)。trait_id 形如 'O6'，元数据里的 domain 作为兜底。"""
    code = (trait_id or '').strip()[:1].upper()
    if code in DOMAIN_BY_CODE:
        return DOMAIN_BY_CODE[code]

    zh = ((trait_meta or {}).get('domain') or '').strip()
    if zh in DOMAIN_EN_BY_ZH:
        return DOMAIN_EN_BY_ZH[zh], zh
    return '', zh


def format_trait(trait_id: str | None, trait_meta: dict | None) -> str:
    """把面级特质拼成提示词友好的描述。

    例如 ('O6', {...}) -> "O (Openness) / 开放性 —— 子维度 O6：价值观"

    若无法识别维度，则退回单独的面名称，行为与改动前一致。
    """
    trait_meta = trait_meta or {}
    facet = (trait_meta.get('facet_name') or '').strip()
    en, zh = domain_of(trait_id, trait_meta)

    if not en and not zh:
        return facet or (trait_id or '')

    code = (trait_id or '').strip()[:1].upper()
    head = f"{code} ({en})" if en and code in DOMAIN_BY_CODE else (en or zh)
    if en and zh:
        head = f"{head} / {zh}"

    if not facet:
        return head
    facet_label = f"子维度 {trait_id}：{facet}" if trait_id else f"子维度：{facet}"
    return f"{head} —— {facet_label}"
