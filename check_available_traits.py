#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查图片/视频生成可用的特质

运行此脚本查看哪些特质在 PSJT-Mussel 数据集中有可用情境
"""

# 直接导入 DataLoader 避免触发其他模块的导入
from src.txt.datasets.load_data import DataLoader

def main():
    # 加载数据
    dl = DataLoader()
    sjts_data = dl.load("PSJT-Mussel", "zh")
    neopir_meta = dl.load_meta("NEO-PI-R")

    print("=" * 70)
    print("图片和视频生成可用的特质")
    print("=" * 70)
    print()

    # 按维度分组
    domains = {
        "神经质": [],
        "外向性": [],
        "开放性": [],
        "宜人性": [],
        "尽责性": []
    }

    for trait_id in sorted(sjts_data.keys()):
        if trait_id in neopir_meta:
            trait_info = neopir_meta[trait_id]
            situation_count = len(sjts_data[trait_id])
            domain = trait_info['domain']

            if domain in domains:
                domains[domain].append({
                    'id': trait_id,
                    'name': trait_info['facet_name'],
                    'count': situation_count
                })

    # 按维度显示
    for domain, traits in domains.items():
        if traits:
            print(f"\n【{domain}】")
            print("-" * 70)
            for trait in traits:
                print(f"  {trait['id']:4s} {trait['name']:12s} - {trait['count']} 个情境")

    print()
    print("=" * 70)
    print(f"总计: {len(sjts_data)} 个特质有可用情境（共30个特质）")
    print(f"可用率: {len(sjts_data)/30*100:.1f}%")
    print("=" * 70)
    print()
    print("提示：")
    print("  - 以上特质可以在图片和视频生成页面使用")
    print("  - 其他特质请使用文字生成功能")
    print()

if __name__ == '__main__':
    main()
