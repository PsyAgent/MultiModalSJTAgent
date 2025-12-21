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
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool, create_swarm
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

class VidSJTAgent:
    def __init__(self, trait, situ):
        self.trait = trait
        self.situ = situ

    def run(
        self,
        character_seed_json=None,
        duration=10,
        resolution="768P",
        model_name="gpt-4o",
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
        duration=10, 
        resolution="768P", 
        model_name="gpt-4o"
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
    checkpointer = InMemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "1"}}

    # 4. 执行工作流
    turn = app.invoke(
        {
            "messages": [
                {"role": "user", "content": question_content},
                {"role": "user", "content": f"角色特征JSON: {json.dumps(character_seed, ensure_ascii=False)}"}
            ]
        },
        config,
    )

    # 5. 提取视频提示词
    video_prompts = next(
        (m.content for m in turn["messages"] if getattr(m, "name", "") == "generate_video_prompt" and getattr(m, "content", None)),
        None
    )

    # 回退逻辑
    if not video_prompts:
        for _msg in turn["messages"]:
            addkw = getattr(_msg, "additional_kwargs", {}) or {}
            tool_calls = addkw.get("tool_calls") if isinstance(addkw, dict) else None
            if tool_calls:
                for tc in tool_calls:
                    fn = ((tc.get("function") or {}).get("name") if isinstance(tc, dict) else None)
                    if fn == "transfer_to_video":
                        args = ((tc.get("function") or {}).get("arguments"))
                        try:
                            parsed = json.loads(args)
                            sb = parsed.get("storyboard_data")
                            if sb:
                                video_prompts = generate_video_prompt(sb)
                        except:  # noqa: E722
                            pass

    if not video_prompts:
        raise ValueError("未能生成有效的视频提示词")

    # 6. 生成视频 (Hailuo)
    hailuo_results = run_hailuo_pipeline(
        video_prompts,
        duration=duration,
        resolution=resolution,
        auto_download=True,
        trait=trait
    )
    
    saved_dir = hailuo_results.get("saved_dir") if isinstance(hailuo_results, dict) else None
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