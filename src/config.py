"""读取项目根目录 config.yaml 的统一模型配置。

API 密钥仍放在 .env 中，此处只管理模型 ID、接口地址等非敏感设置。
"""
from __future__ import annotations

import os.path as op

import yaml

CONFIG_PATH = op.abspath(op.join(op.dirname(__file__), '..', 'config.yaml'))


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


CONFIG = load_config()
