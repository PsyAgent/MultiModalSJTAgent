from .agents.Tools import (
    get_cues, reflect_cues, generate_storyboard,
    reflect_storyboard, generate_video_prompt,
    reflect_video_prompt)
from .agents.vioce_autospeed import generate_narration
from .agents.Hailuo import run_hailuo_pipeline
from .test.merge_two_files import AVMerger
from .agents.prompts import PROMPT_CUE, PROMPT_STORYBOARD, PROMPT_VIDEO

import os
import json
import time
import uuid
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool, create_swarm
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

from ..config import CONFIG
from ..retry import RETRY_DELAY

_VIDEO_CFG = CONFIG.get('video', {})
VID_AGENT_MODEL = _VIDEO_CFG.get('agent_model', 'gpt-4o')
VID_DURATION = int(_VIDEO_CFG.get('duration', 10))
VID_RESOLUTION = _VIDEO_CFG.get('resolution', '768P')
# LangGraph 默认 recursion_limit=25，而 swarm 里三个 agent 各自还有反思循环，
# 正常一次生成就要 20+ 步，稍有反复就会撞上限并整题失败。
VID_RECURSION_LIMIT = int(_VIDEO_CFG.get('recursion_limit', 60))
VID_AGENT_ATTEMPTS = int(_VIDEO_CFG.get('agent_attempts', 2))


def _extract_video_prompt(messages):
    """从消息流中取出视频提示词；拿不到就退回用 handoff 里的 storyboard 现算一个。"""
    if not messages:
        return None

    video_prompts = next(
        (m.content for m in messages
         if getattr(m, "name", "") == "generate_video_prompt" and getattr(m, "content", None)),
        None
    )
    if video_prompts:
        return video_prompts

    # 回退 1：Storyboard 已经 handoff 给 Video，但 Video 还没来得及产出提示词
    for _msg in messages:
        addkw = getattr(_msg, "additional_kwargs", {}) or {}
        tool_calls = addkw.get("tool_calls") if isinstance(addkw, dict) else None
        for tc in tool_calls or []:
            fn = ((tc.get("function") or {}).get("name") if isinstance(tc, dict) else None)
            if fn != "transfer_to_video":
                continue
            try:
                parsed = json.loads((tc.get("function") or {}).get("arguments"))
                sb = parsed.get("storyboard_data")
                if sb:
                    return generate_video_prompt(sb)
            except Exception:  # noqa: BLE001 - 回退路径，解析失败就继续找下一个
                pass

    # 回退 2：连 handoff 都没走到，但分镜已经生成过
    storyboard = next(
        (m.content for m in reversed(messages)
         if getattr(m, "name", "") == "generate_storyboard" and getattr(m, "content", None)),
        None
    )
    if storyboard:
        return generate_video_prompt(storyboard)

    return None


def _run_swarm(app, config, question_content, character_seed, trait=None):
    """跑一次多智能体流程并取回视频提示词；撞到步数上限时从检查点里捞已有成果。"""
    # 反思工具会先自行推断待测特质，推断结果与题干不符时就反复重来（步数的主要消耗），
    # 所以把特质直接写进输入，让反思有明确的对齐标准。
    stem = f"题目：{question_content}\n特质：{trait}" if trait else question_content
    inputs = {
        "messages": [
            {"role": "user", "content": stem},
            {"role": "user", "content": f"角色特征JSON: {json.dumps(character_seed, ensure_ascii=False)}"}
        ]
    }
    try:
        turn = app.invoke(inputs, config)
        return _extract_video_prompt(turn.get("messages", []))
    except GraphRecursionError as e:
        # 步数用尽不代表没有产出：分镜/提示词往往已经生成，只是 agent 没能正常收尾。
        print(f"[vid] 多智能体流程达到步数上限（{config.get('recursion_limit')}），尝试从中间结果恢复：{e}")
        try:
            state = app.get_state(config)
            messages = (state.values or {}).get("messages", [])
        except Exception:  # noqa: BLE001
            messages = []
        return _extract_video_prompt(messages)

class VidSJTAgent:
    def __init__(self, trait, situ):
        self.trait = trait
        self.situ = situ

    def run(
        self,
        character_seed_json=None,
        duration=VID_DURATION,
        resolution=VID_RESOLUTION,
        model_name=VID_AGENT_MODEL,
        outdir=None,
        out_basename=None,
    ):
        return api_generate_video_sjt(
            trait=self.trait,
            situ=self.situ,
            outdir=outdir,
            out_basename=out_basename,
            character_seed_json=character_seed_json,
            duration=duration,
            resolution=resolution,
            model_name=model_name
    )

def api_generate_video_sjt(
        trait, 
        situ,
        character_seed_json=None, 
        outdir=None,
        out_basename=None,
        duration=VID_DURATION,
        resolution=VID_RESOLUTION,
        model_name=VID_AGENT_MODEL
        ):
    """
    核心API：生成视频SJT
    
    Returns:
        dict: {
            "situation": str,  # 最终合并后的视频绝对路径
            "options": dict,   # SJT的选项内容
            "meta": dict       # 其他元数据(prompts, raw_text等)
        }
    """
    # 1. 数据验证与加载
    
    # 提取情境文本
    question_content = None
    if 'stem' in situ:
        question_content = situ['stem']
    elif 'situation' in situ:
        question_content = situ['situation']
    elif 'context' in situ:
        question_content = situ['context']
    else:
        # 尝试查找任何长字符串值
        for key, value in situ.items():
            if key not in ['options', 'scoring'] and isinstance(value, str):
                question_content = value
                break
    
    if not question_content:
        raise ValueError("未找到有效的情境描述字段")

    # 提取选项 (用于返回)
    options = situ.get('options', {})

    # 2. 解析角色特征
    try:
        if not character_seed_json or not isinstance(character_seed_json, str) or character_seed_json.strip() == "":
            character_seed = {"age": 23, "gender": "女", "group": "大学生", "nationality": "中国", "occupation": "默认"}
        else:
            character_seed = json.loads(character_seed_json)
    except json.JSONDecodeError:
        # 如果解析失败，使用默认值
        character_seed = {"age": 23, "gender": "女", "group": "大学生", "nationality": "中国", "occupation": "默认"}

    # 3. 初始化 LangGraph 多智能体系统
    model = ChatOpenAI(model=model_name, temperature=0.4)

    cue_retrieval_agent = create_react_agent(model, [get_cues, reflect_cues, create_handoff_tool(agent_name="Storyboard")], prompt=PROMPT_CUE, name="Cue")
    storyboard_reason_agent = create_react_agent(model, [generate_storyboard, reflect_storyboard, create_handoff_tool(agent_name="Video")], prompt=PROMPT_STORYBOARD, name="Storyboard")
    video_prompt_agent = create_react_agent(model, [generate_video_prompt, reflect_video_prompt], prompt=PROMPT_VIDEO, name="Video")

    workflow = create_swarm([cue_retrieval_agent, storyboard_reason_agent, video_prompt_agent], default_active_agent="Cue")

    # 4. 执行工作流（失败或空产出时整段重跑，每次都用干净的检查点与 thread_id）
    video_prompts = None
    last_exc = None
    for attempt in range(1, max(1, VID_AGENT_ATTEMPTS) + 1):
        app = workflow.compile(checkpointer=InMemorySaver())
        config = {
            "configurable": {"thread_id": uuid.uuid4().hex},
            "recursion_limit": VID_RECURSION_LIMIT,
        }
        try:
            video_prompts = _run_swarm(app, config, question_content, character_seed, trait=trait)
        except Exception as e:  # noqa: BLE001 - 网络/网关抖动等，重跑一次通常就好
            last_exc = e
            print(f"[vid] 多智能体流程第 {attempt} 次失败：{e}")

        if video_prompts:
            break
        if attempt < VID_AGENT_ATTEMPTS:
            print(f"[vid] 未拿到视频提示词，{RETRY_DELAY:.0f}s 后重跑多智能体流程（第 {attempt + 1} 次）")
            time.sleep(RETRY_DELAY)

    if not video_prompts:
        raise ValueError(f"未能生成有效的视频提示词{f'（最后一次错误：{last_exc}）' if last_exc else ''}")

    # 6. 生成视频 (Hailuo)
    hailuo_results = run_hailuo_pipeline(
        video_prompts,
        duration=duration,
        resolution=resolution,
        auto_download=True,
        trait=trait
    )
    
    if not isinstance(hailuo_results, dict):
        # 创建失败 / 轮询超时 / 下载失败，具体原因已打印在日志里
        raise RuntimeError("视频生成失败：出片接口未返回结果（详见日志）")
    saved_dir = hailuo_results.get("saved_dir")
    if not saved_dir:
        raise RuntimeError("视频生成失败，未返回保存目录")

    # 7. 生成音频 (TTS)
    audio_output_dir = saved_dir
    # 简单的文本截断逻辑，防止旁白过长
    narration_text = question_content
    speed = 1.5 if len(narration_text) > 54 else 1.0

    generate_narration(
        text=narration_text,
        target_duration=float(duration),
        output_dir=audio_output_dir,
        speed=speed
    )

    # 8. 合并音视频
    merger = AVMerger(video_folder=saved_dir, audio_folder=saved_dir, output_folder=saved_dir)
    env_name = saved_dir.split(os.sep)[-1] if saved_dir else "env"
    merger.merge(num_files=1, only_first_pair=True, output_basename=env_name)

    # 查找最终生成的合并文件
    final_video_path = None
    for file in os.listdir(saved_dir):
        # 通常合并后的文件会包含 'merged' 字样或者就是我们指定的 basename
        if file.endswith('.mp4') and ('merged' in file or file.startswith(env_name)):
            final_video_path = os.path.abspath(os.path.join(saved_dir, file))
            # 找到一个即可，优先找合并后的，如果只有一个视频文件也认为是它
            if 'merged' in file:
                break
    
    if not final_video_path:
        # 如果没找到特定命名的，找目录里任意一个mp4
        mp4s = [f for f in os.listdir(saved_dir) if f.endswith('.mp4')]
        if mp4s:
            final_video_path = os.path.abspath(os.path.join(saved_dir, mp4s[0]))
    # 将视频保存到指定目录并清理生成文件
    target_dir = outdir or saved_dir
    os.makedirs(target_dir, exist_ok=True)

    if final_video_path:
        target_basename = os.path.basename(final_video_path)
        target_path = os.path.abspath(os.path.join(target_dir, target_basename))
        if os.path.abspath(final_video_path) != target_path:
            os.replace(final_video_path, target_path)
    else:
        target_path = None

    if saved_dir and os.path.abspath(saved_dir) != os.path.abspath(target_dir):
        for root, dirs, files in os.walk(saved_dir, topdown=False):
            for file in files:
                try:
                    os.remove(os.path.join(root, file))
                except FileNotFoundError:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        try:
            os.rmdir(saved_dir)
        except OSError:
            pass

    final_video_path = target_path
    if not final_video_path:
        # 走到这里说明合成/下载环节没落盘，交给上层重试而不是抛 TypeError
        raise RuntimeError(f"视频生成失败：{saved_dir} 下没有可用的 mp4 文件")
    if out_basename is not None:
        new_final_path = os.path.join(target_dir, f"{out_basename}.mp4")
        if final_video_path != new_final_path:
            os.replace(final_video_path, new_final_path)
            final_video_path = new_final_path
    # 9. 返回标准结果
    return {
        "situation": final_video_path, # 视频路径
        "options": options,            # 原始选项
        "meta": {                      # 元数据
            "trait": trait,
            "prompts": video_prompts,
            "text": question_content
        }
    }