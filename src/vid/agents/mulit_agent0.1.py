from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool, create_swarm
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from agents.prompts import PROMPT_CUE, PROMPT_STORYBOARD, PROMPT_VIDEO
from agents.Tools import (get_cues,reflect_cues,generate_storyboard,reflect_storyboard,generate_video_prompt,reflect_video_prompt,pretty_print_turn)
from agents.user_inputs import collect_sjt_user_inputs
from agents.vioce_autospeed import generate_narration
from agents.Hailuo import run_hailuo_pipeline
from test.merge_two_files import AVMerger
import os
import json


load_dotenv()
model = ChatOpenAI(model="gpt-4o", temperature=0.4)

# cue 提取 Agent
cue_retrieval_agent = create_react_agent(
    model,
    [
        get_cues,
        reflect_cues,
        create_handoff_tool(agent_name="Storyboard")  # handoff 工具
    ],
    prompt=PROMPT_CUE,
    name="Cue",
)

# 分镜生成 Agent
storyboard_reason_agent = create_react_agent(
    model,
    [
        generate_storyboard,  # 分镜生成工具
        reflect_storyboard,   # 分镜反思工具
        create_handoff_tool(agent_name="Video")
    ],
    prompt=PROMPT_STORYBOARD,
    name="Storyboard",
)

# 视频提示词生成 Agent
video_prompt_agent = create_react_agent(
    model,
    [
        generate_video_prompt,  # 视频提示词生成工具
        reflect_video_prompt
    ],
    prompt=PROMPT_VIDEO,
    name="Video",
)
checkpointer = InMemorySaver()
workflow = create_swarm(
    [cue_retrieval_agent, storyboard_reason_agent, video_prompt_agent],
    default_active_agent="Cue"
)
app = workflow.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}
print("🚀 开始执行多智能体工作流...")
print("=" * 50)
# 收集用户输入信息
question_content, character_seed, trait ,stem= collect_sjt_user_inputs()

# 执行完整的工作流
turn = app.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": question_content
            },
            {
                "role": "user",
                "content": f"角色特征JSON: {json.dumps(character_seed, ensure_ascii=False)}"
            }
        ]
    },
    config,
)
pretty_print_turn(turn)

gp = next(
    (m.content for m in turn["messages"]
     if getattr(m, "name", "") == "generate_video_prompt" and getattr(m, "content", None)),
    None
)
video_prompts = gp

# 回退逻辑：若 Video 智能体未成功调用生成工具，则从 handoff 的参数里提取 storyboard，直接生成 video_prompt
if not video_prompts:
    try:
        storyboard_payload = None
        for _msg in turn["messages"]:
            # 提取 AI 消息中的 tool_calls（handoff 参数在这里）
            addkw = getattr(_msg, "additional_kwargs", {}) or {}
            tool_calls = addkw.get("tool_calls") if isinstance(addkw, dict) else None
            if not tool_calls:
                continue
            for tc in tool_calls:
                fn = ((tc.get("function") or {}).get("name") if isinstance(tc, dict) else None)
                if fn == "transfer_to_video":
                    args = ((tc.get("function") or {}).get("arguments"))
                    if isinstance(args, str) and args.strip():
                        import json as _json
                        try:
                            parsed = _json.loads(args)
                            # 期望结构：{"storyboard_data": "{...}"}
                            sb = parsed.get("storyboard_data") if isinstance(parsed, dict) else None
                            if isinstance(sb, str) and sb.strip():
                                storyboard_payload = sb
                                break
                        except Exception:
                            pass
            if storyboard_payload:
                break

        if storyboard_payload:
            # 直接调用工具函数生成 video_prompt（保证后续流程可继续）
            fallback_prompt = generate_video_prompt(storyboard_payload)
            if fallback_prompt:
                # 统一为列表形式供后续流程使用
                video_prompts = [fallback_prompt]
    except Exception as _e:
        print(f"回退生成 video_prompt 失败: {_e}")

if video_prompts:
    # 是否生成视频（仅 Hailuo）
    saved_dir = None
    choice = input("\n是否生成视频? (y/n): ").strip().lower()
    if choice == "y":
        print("\n创建 Hailuo 视频任务...")
        try:
            hailuo_results = run_hailuo_pipeline(video_prompts, duration=10, resolution="768P", auto_download=True, trait=trait)
            print(json.dumps(hailuo_results, ensure_ascii=False, indent=2))
            try:
                if isinstance(hailuo_results, dict):
                    saved_dir = hailuo_results.get("saved_dir")
            except Exception:
                saved_dir = None
        except RuntimeError as e:
            print(f"aiohttp 不可用或出错: {e}")
        except Exception as e:
            print(f"Hailuo 生成异常: {e}")

    print("\n🎤 生成旁白语音...")
    audio_output_dir = saved_dir or "results/audio"
    if len(stem) > 54:
        speed = 1.5
    else:
        speed = 1.0
    audio_path = generate_narration(text=stem, target_duration=10.0, output_dir=audio_output_dir, speed=speed)
    if not audio_path:
        print("❌ 语音生成失败（可手动提供音频路径以继续）")

    # 自动调用合并：将当前 envN 下首个视频与首个音频合并
    try:
        if saved_dir:
            print("\n🎬 调用 merge_two_files 合并视频和音频...")
            merger = AVMerger(video_folder=saved_dir, audio_folder=saved_dir, output_folder=saved_dir)
            env_name = None
            try:
                env_name = saved_dir.split(os.sep)[-1]
            except Exception:
                env_name = "env"
            merger.merge(num_files=1, only_first_pair=True, output_basename=env_name)
    except Exception as _e:
        print(f"自动合并失败: {_e}")
    print("\n过程保存...")
    pretty_print_turn(turn, output_dir=saved_dir)
else:
    print("未提供视频提示词。")

