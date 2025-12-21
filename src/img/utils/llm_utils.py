from __future__ import annotations

import json
import re
from typing import Any

from wasabi import msg

def extract_json(text: str) -> dict[Any, Any]:
    """
    从字符串中提取第一个 JSON 对象并解析为 Python 字典。
    支持 ```json ... ``` 代码块，也支持直接提取最外层的 { ... } 块。
    解析失败时抛出 json.JSONDecodeError。
    """
    # 尝试在 ```json``` 代码块中匹配
    fence_pattern = r'```json\s*(\{.*?\})\s*```'
    m = re.search(fence_pattern, text, re.DOTALL)
    if m:
        candidate = m.group(1)
    else:
        # 回退：提取第一个平衡的 { ... } 块
        brace_stack = []
        start_idx = None
        for i, ch in enumerate(text):
            if ch == '{':
                if start_idx is None:
                    start_idx = i
                brace_stack.append(ch)
            elif ch == '}' and brace_stack:
                brace_stack.pop()
                if not brace_stack and start_idx is not None:
                    candidate = text[start_idx:i+1]
                    break
        else:
            # 未找到任何 JSON 块，则抛出 JSONDecodeError
            raise json.JSONDecodeError('No JSON object found in text', text, 0)

    # 将文字中的 '\n' 转为真实换行
    candidate = candidate.replace(r'\n', '\n')

    # 直接解析，若格式不合法将抛出 JSONDecodeError
    return json.loads(candidate)


# 示例用法
if __name__ == '__main__':
    sample_text = """
    前言...
    ```json
    { "a": 1, "b": 2, }
    ```
    后记...
    """
    try:
        result = extract_json(sample_text)
        print('Parsed JSON:', result)
    except json.JSONDecodeError as e:
        print('JSON解析失败:', e)



def print_conversation(msgs):
    """
    Print the conversation in a readable format.

    Parameters:
    -----------
    msg: list
        The conversation messages to print.
    """
    for turn in msgs:
        icon = '🤖' if turn['role'] == 'assistant' else (
            '⚙️' if turn['role'] == 'system' else '👤'
        )
        msg.divider(icon)
        print(turn['content'])
