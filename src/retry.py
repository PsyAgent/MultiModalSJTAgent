"""统一的失败重试工具。

生成流程里的每一步几乎都依赖 LLM，偶发失败（不按格式输出、空响应、网关抖动）
是常态而不是异常。这里提供一个最小的重试封装，重试次数与等待时间统一由
config.yaml 的 `retry:` 段控制。
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from .config import CONFIG

_RETRY_CFG = CONFIG.get('retry', {}) or {}

STEP_ATTEMPTS = int(_RETRY_CFG.get('step_attempts', 3))
TASK_ATTEMPTS = int(_RETRY_CFG.get('task_attempts', 2))
RETRY_DELAY = float(_RETRY_CFG.get('delay', 2))
RETRY_BACKOFF = float(_RETRY_CFG.get('backoff', 2))

T = TypeVar('T')


def retry_call(
    fn: Callable[[], T],
    attempts: int = STEP_ATTEMPTS,
    delay: float = RETRY_DELAY,
    backoff: float = RETRY_BACKOFF,
    label: str = '',
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """执行 `fn`，失败则重试，最终仍失败时抛出最后一次的异常。

    Parameters
    ----------
    fn : callable
        无参可调用对象；必须可以安全地重复执行。
    attempts : int
        总尝试次数（含首次），小于 1 时按 1 处理。
    delay : float
        首次重试前的等待秒数。
    backoff : float
        每次重试后等待时间的放大倍数。
    label : str
        日志里显示的步骤名。
    exceptions : tuple
        触发重试的异常类型。
    """
    attempts = max(1, int(attempts))
    wait = delay
    last_exc: BaseException | None = None

    for i in range(1, attempts + 1):
        try:
            return fn()
        except exceptions as e:  # noqa: PERF203
            last_exc = e
            if i == attempts:
                break
            print(f"[retry] {label or fn!r} 第 {i}/{attempts} 次失败：{e}；{wait:.0f}s 后重试")
            if wait > 0:
                time.sleep(wait)
            wait *= backoff

    assert last_exc is not None
    raise last_exc
