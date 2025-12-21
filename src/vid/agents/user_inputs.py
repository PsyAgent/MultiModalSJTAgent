from __future__ import annotations

import os
import json
from typing import Dict, Tuple


def collect_sjt_user_inputs() -> Tuple[str, Dict[str, str], str]:
    """
    收集 SJT 题目与角色特征输入，并将角色特征 JSON 持久化到 `agents/results/role_features.json`。

    Returns:
        question_content: 形如 "题目：{stem}  A. xxx  B. yyy\n特质：{trait}"
        character_seed: 角色设定字典
    """

    print("\n📝 请输入SJT题目信息:")
    print("=" * 50)

    # 输入题干
    print("请输入题干（情境描述）:")
    stem = input("题干: ").strip()

    # 输入选项
    print("\n请输入选项（每行一个选项，输入空行结束）：")
    options = []
    while True:
        option = input(f"选项 {chr(65 + len(options))}: ").strip()
        if not option:
            break
        options.append(option)

    # 输入特质
    print("\n请输入待测人格特质:")
    trait = input("特质: ").strip()

    options_text = "  ".join([f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)])
    question_content = f"题目：{stem}  {options_text}\n特质：{trait}"

    print(f"\n✅ 题目信息确认:")
    print(f"题干: {stem}")
    print(f"选项: {options_text}")
    print(f"特质: {trait}")
    print("=" * 50)

    # 收集角色特征信息，用于视觉主体一致性
    print("\n📝 请提供角色特征信息（用于确保视觉主体一致性）:")
    age = input("年龄: ").strip() or "25"
    gender = input("性别 (男/女): ").strip() or "男"
    group = input("群体 (如: 大学生/上班族/等): ").strip() or "大学生"
    hairstyle = input("发型 (如: 短发/长发/马尾/卷发/光头 等): ").strip() or "短发"
    clothing = input("衣物 (如: 校园风/正装/休闲装/运动装 等): ").strip() or "休闲装"
    nationality = input("国籍 (如: 中国/美国/日本/英国 等): ").strip() or "中国"

    character_seed = {
        "age": age,
        "gender": gender,
        "group": group,
        "hairstyle": hairstyle,
        "clothing": clothing,
        "nationality": nationality,
        "description": f"一位来自{nationality}、{age}岁的{gender}性{group}，发型为{hairstyle}，穿着{clothing}",
    }

    print(f"✅ 角色设定: {character_seed['description']}")
    print("=" * 50)

    # 将角色特征持久化，供下游工具显式读取
    try:
        _current_dir = os.path.dirname(os.path.abspath(__file__))
        _results_dir = os.path.join(_current_dir, "results")
        os.makedirs(_results_dir, exist_ok=True)
        _role_path = os.path.join(_results_dir, "role_features.json")
        with open(_role_path, "w", encoding="utf-8") as _f:
            json.dump(character_seed, _f, ensure_ascii=False, indent=2)
    except Exception as _e:
        print(f"⚠️ 角色特征持久化失败: {_e}")

    return question_content, character_seed, trait, stem


