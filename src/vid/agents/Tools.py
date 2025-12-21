from dotenv import load_dotenv
import json
from langchain_openai import ChatOpenAI
import os
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from .prompts import generate_video_prompt as VIDEO_PROMPT_SYSTEM_TEXT
import re

load_dotenv()

# LLM（供 cues 提取与反思工具使用）
tool_model = ChatOpenAI(model="gpt-4o", temperature=0.4)

def get_cues(text: str) -> str:
    """使用 LLM 作为工具，从输入中提取线索（cues）。返回 JSON（见系统提示）。"""
    try:
        print(f"[TOOL get_cues:llm]")
        system_prompt = (
            "你是一名人格情境判断测验的分析专家。"
            "核心任务：基于输入的人格情境判断测文本，提取关键线索（cue）包括环境、事件、冲突、人物状态等，不得遗漏"
            "【约束要求】\n"
            "A. **来源限制**：所有线索必须直接来源于题干文本，禁止添加任何未出现的细节或推测。\n"
            "B. **禁止演绎**：不要生成行为解决方案或额外背景解释。\n"
            "C. **情境情绪**：若题干描述了主角或配角的心理/情绪状态（如：紧张、拥挤、不适），必须提取为 cue，用于指导后续表演基调。\n"
            "D. **结构化输出**：输出必须为合法 JSON，需符合以下示例。\n\n"
            "E. **原因说明**：每个 cue 必须包含原因说明，说明这个cue来自于原题干什么部分。\n"
            "【输出 JSON 格式】\n"
            "{\n"
            "  \"cues\": [\n"
            "    {\n"
            "      \"cue_id\": \"cue1\",\n"
            "      \"type\": \"环境\",\n"
            "      \"content\": \"<线索文本内容>\",\n"
            "      \"importance\": \"高/中/低\"\n"
            "      \"reason\": \"题目中说明：\"\n"
            "    },\n"
            "    {\n"
            "      \"cue_id\": \"cue2\",\n"
            "      \"type\": \"核心事件/背景\",\n"
            "      \"content\": \"<线索文本内容>\",\n"
            "      \"importance\": \"高/中/低\"\n"
            "      \"reason\": \"题目中说明：\"\n"
            "    },\n"
            "    {\n"
            "      \"cue_id\": \"cue3\",\n"
            "      \"type\": \"主要冲突\",\n"
            "      \"content\": \"<线索文本内容>\",\n"
            "      \"importance\": \"高/中/低\"\n"
            "      \"reason\": \"题目中说明：\"\n"
            "    },\n"
            "    {\n"
            "      \"cue_id\": \"cue4\",\n"
            "      \"type\": \"主角状态/压力\",\n"
            "      \"content\": \"<线索文本内容>\",\n"
            "      \"importance\": \"高/中/低\"\n"
            "      \"reason\": \"题目中说明：\"\n"
            "    },\n"
            "    {\n"
            "      \"cue_id\": \"cue5\",\n"
            "      \"type\": \"配角信息/反应\",\n"
            "      \"content\": \"<线索文本内容>\",\n"
            "      \"importance\": \"高/中/低\"\n"
            "      \"reason\": \"题目中说明：\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]
        resp = tool_model.invoke(messages)
        content = getattr(resp, "content", None)
        if not content:
            return "(cues 提取失败: 空响应)"

        raw = str(content).strip()

        # 解析模型输出 → cues 数组 → 返回 {source_text, cues}
        try:
            # 剥离可能的代码块围栏
            if raw.startswith("```"):
                import re
                m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
                if m:
                    raw = m.group(1).strip()

            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return json.dumps({"source_text": text, "cues": parsed}, ensure_ascii=False)
            if isinstance(parsed, dict):
                cues_val = parsed.get("cues")
                if isinstance(cues_val, list):
                    return json.dumps({"source_text": text, "cues": cues_val}, ensure_ascii=False)
                # 无 cues 字段则兜底为空数组
                return json.dumps({"source_text": text, "cues": []}, ensure_ascii=False)
        except Exception:
            # 解析失败则兜底返回原文与原始输出
            return json.dumps({"source_text": text, "cues_raw": raw}, ensure_ascii=False)
    except Exception as e:
        return f"(cues 提取失败: {e})"

def generate_storyboard(cues_data: str) -> str:
    """基于 cues 数据生成分镜脚本。输入 cues JSON，输出分镜 JSON。"""
    try:
        print("[TOOL generate_storyboard:llm]")
        system_prompt = """
        你是一名人格情境判断测验（PSJT）的专家，熟悉五大人格理论和特质激活理论。你的核心任务是：根据输入的原始情境题目和线索（cues）以及客观特质信号，生成一段连续的分镜描述。
        该提示词将用于直接指导 AI 视频生成，必须融合所有关键视觉元素，并锚定10秒时长。
        **【特质激活理论知识】**
        情境对人格表现的激活作用,某些情景线索会激活对应的人格特质表现。
        人的行为是“特质+情境” 共同作用的结果,当一个情境中包含与某特质相关的激活线索时,该特质就更有可能通过行为表达出来。
        **【硬性约束：标准化与信度】**
        1.  **主角固定：** 使用用户输入的角色特征JSON来确定。必须是中国人，亚洲面孔
        2.  **客观描述：** 采用第三人称，严格禁止任何主角的心理活动、内心独白或引导性的情绪（例如：禁止使用"委屈"、"强装"、"忍不住"）。
        3.  **信息整合：** 描述必须整合所有关键线索。
        4.  **逻辑顺畅：** 描述不一定非得按照题目顺序呈现，视频呈现怎么合理怎么写。
        5.  **特质激活：** 基于特质激活理论进行。
        **【内容结构：单段连贯叙事】
        你的输出必须是一段连贯的中文描述，融合以下视觉元素：
        1.  **主体：** 根据输入角色特征JSON确定主角的外观。
        2.  **场景：** 根据线索准确描述情境背景。
        3.  **动作：** 准确描述线索中的角色的具体动作。
        4.  **事件：** 准确描述线索中的具体事件。
        5.  **决策定格：** 描述必须在关键选择的瞬间结束。**严禁替角色做出任何行动选择**。
        **【输出格式】**
        严格输出JSON 对象，其中只包含一个键：`core_video_prompt`。不要输出任何额外文本或结构。
        """
        # 读取上游角色特征（含发型/衣物），注入到用户输入中
        role_ctx = {}
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            role_path = os.path.join(current_dir, "results", "role_features.json")
            if os.path.exists(role_path):
                with open(role_path, "r", encoding="utf-8") as f:
                    role_ctx = json.load(f)
        except Exception:
            role_ctx = {}

        merged_input = json.dumps({
            "role_features": role_ctx,
            "cues_data": cues_data
        }, ensure_ascii=False)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": merged_input},
        ]
        resp = tool_model.invoke(messages)  # type: ignore
        content = getattr(resp, "content", None)
        if not content:
            return "(分镜生成失败: 空响应)"

        # 解析输入：从 cues_data 中提取 source_text 与 cues
        def _strip_fences(s: str) -> str:
            s = s.strip()
            if s.startswith("```"):
                import re
                m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
                if m:
                    return m.group(1).strip()
            return s

        inp_raw = _strip_fences(str(cues_data))
        source_text: str = ""
        cues_list = []
        try:
            inp_obj = json.loads(inp_raw)
            if isinstance(inp_obj, dict):
                if isinstance(inp_obj.get("source_text"), str):
                    source_text = inp_obj.get("source_text") or ""
                if isinstance(inp_obj.get("cues"), list):
                    cues_list = inp_obj.get("cues") or []
        except Exception:
            pass

        # 解析模型输出：期望为 {"core_video_prompt": "..."}
        out_raw = _strip_fences(str(content).strip())
        storyboard_obj: dict
        try:
            out_obj = json.loads(out_raw)
            if isinstance(out_obj, dict) and "core_video_prompt" in out_obj:
                storyboard_obj = {"core_video_prompt": out_obj.get("core_video_prompt")}
            else:
                storyboard_obj = {"core_video_prompt": out_raw}
        except Exception:
            storyboard_obj = {"core_video_prompt": out_raw}

        combined = {
            "source_text": source_text,
            "cues": cues_list,
            "storyboard": storyboard_obj,
        }
        return json.dumps(combined, ensure_ascii=False)
    except Exception as e:
        return f"(分镜生成失败: {e})"


def generate_video_prompt(storyboard_data: str) -> str:
    """基于分镜数据生成视频制作提示词。输入分镜 JSON，输出视频提示词。"""
    try:
        print("[TOOL generate_video_prompt:llm]")
        system_prompt = VIDEO_PROMPT_SYSTEM_TEXT
        # 仅向模型提供 core_video_prompt
        core_prompt = None
        try:
            raw = str(storyboard_data).strip()
            if raw.startswith("```"):
                import re
                m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
                if m:
                    raw = m.group(1).strip()
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                if isinstance(parsed.get("core_video_prompt"), str):
                    core_prompt = parsed.get("core_video_prompt")
                elif isinstance(parsed.get("storyboard"), dict) and isinstance(parsed["storyboard"].get("core_video_prompt"), str):
                    core_prompt = parsed["storyboard"]["core_video_prompt"]
        except Exception:
            pass

        # 注入角色特征（含发型/衣物）
        role_ctx = {}
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            role_path = os.path.join(current_dir, "results", "role_features.json")
            if os.path.exists(role_path):
                with open(role_path, "r", encoding="utf-8") as f:
                    role_ctx = json.load(f)
        except Exception:
            role_ctx = {}

        effective_input = json.dumps({
            "role_features": role_ctx,
            "core_video_prompt": core_prompt if core_prompt else storyboard_data
        }, ensure_ascii=False)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": effective_input},
        ]
        resp = tool_model.invoke(messages)  # type: ignore
        content = getattr(resp, "content", None)
        if not content:
            return "(视频提示词生成失败: 空响应)"
        return str(content).strip()
    except Exception as e:
        return f"(视频提示词生成失败: {e})"

def reflect_cues(cues_text: str) -> str:
    """对 cues 与检索结果进行评分与改进建议，必要时返回 revised_cues（JSON）。
    """
    try:
        print("[TOOL reflect_cues:llm]")
        system_prompt = (
            "你是一名 PSJT 构念一致性评审专家，你熟悉大五人格理论**。"
            "你的任务是确保输入的 cues JSON 在视频化过程中保持构念的信效度。\n\n"
            "知识" 
            "###大五人格理论  "
            "开放性:评估一个人对新经验的开放程度、想象力与探索未知的倾向。"
            "责任心:评估一个人在计划性、自我管理和目标导向方面的表现。"
            "外向性:评估一个人在社交互动中表现出的活力、主动性与参与程度。"
            "宜人性:评估一个人在他人互动中展现出的合作性、同理心与信任倾向。"
            "神经质:评估一个人情绪稳定性的程度及对压力和消极情绪的敏感性。"
            "【评审维度】\n"
            "1. **解析构念**：判断题干隐含的大五人格特质。\n"
            "2. **构念对齐性**：逐条检查 cues 是否涵盖了题干中必须在视频中显现的关键元素。\n"
            "3. **线索充分性反思**：思考当前线索集合是否已经覆盖了支撑该特质的所有必要文本线索，若有遗漏需指出。\n\n"
            "4. **线索与特质**：线索是否能够准确表达当前待测特质"
            "【输出要求】严格使用一个 JSON 对象：\n"
            "{\n"
            "  \"trait\": \"<大五人格特质：解释原因>\",\n"
            "  \"alignment_check\": [\n"
            "     {\"cue_id\": \"cue1\", \"aligned\": true/false, \"reason\": \"<解释>\"}, ...\n"
            "  ],\n"
            "  \"coverage_reflection\": \"<说明该特质需要的线索是否已全部解析出来，若不足指出缺口>\",\n"
            "  \"pass\": <bool>  # 若特质错误、存在关键未对齐或线索不足，则为 false\n"
            "  \"correct\":  \"<说明解析线索能准确表达该特质，解释原因>\"。\n"
            "}\n"
            "禁止输出任何额外文字。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": cues_text},
        ]
        resp = tool_model.invoke(messages)  # type: ignore
        content = getattr(resp, "content", None)
        if not content:
            return "(cues 反思失败: 空响应)"
        return str(content).strip()
    except Exception as e:
        return f"(cues 反思失败: {e})"


def reflect_storyboard(storyboard_data: str) -> str:
    """对分镜脚本进行评分与改进建议，必要时返回 revised_storyboard。"""
    try:
        print("[TOOL reflect_storyboard:llm]")
        system_prompt = (
            "你是PSJT 构念一致性评审专家,你熟悉大五人格理论**\n"
            "你的任务是根据知识和source_text还有cues，确保输入的 storyboard JSON 在视频化过程中保持构念的信效度"
            "知识" 
            "###大五人格理论  "
            "开放性:评估一个人对新经验的开放程度、想象力与探索未知的倾向。"
            "责任心:评估一个人在计划性、自我管理和目标导向方面的表现。"
            "外向性:评估一个人在社交互动中表现出的活力、主动性与参与程度。"
            "宜人性:评估一个人在他人互动中展现出的合作性、同理心与信任倾向。"
            "神经质:评估一个人情绪稳定性的程度及对压力和消极情绪的敏感性。"
            "【评审维度】\n"
            "1. **构念正确性**：根据 storyboard JSON 判断题干隐含的人格特质。\n"
            "2. **构念对齐性**：是否与reflect_cues解析的特质保持一致。\n"
            "3.  **线索充分性反思**：思考当前分镜是否已经覆盖了支撑该特质的所有必要文本线索，若有遗漏需指出。\n\n"
            "4. **线索与特质**：分镜是否能够准确表达当前待测特质"
            "5. **分镜标准性**：是否进行了额外的添加与补充，影响到了待测特质的稳定性。"
            "\n【判定规则（严格）】\n"
            "- 若与 reflect_cues 的特质不一致，则 \"consistency_with_cues\"=false 且 \"pass\"=false，并在 \"correct\" 中说明原因与修正方向。\n"
            "- 若分镜出现心理活动/内心独白/主观情绪词（非客观可观察行为），或使用第一人称叙述，视为违规，\"pass\"=false，并在 \"correct\" 中指出具体违规片段与修正建议。\n"
            "- 仅当：与 cues 一致、线索覆盖充分、无标准性违规时，\"pass\" 才能为 true。\n"
            "【输出要求】严格使用一个 JSON 对象：\n"
            "其中 \"correct\" 字段必须分两部分：1) 线索与特质表达是否准确（维度4，给出依据）；2) 分镜标准性是否合规，若不合规则逐点列出违规与修正建议（维度5）。\n"
            "{\n"
            "  \"trait\": \"<大五人格特质：解释原因>\",\n"
            "  \"consistency_with_cues\": true/false,  # 是否与 reflect_cues 解析的特质保持一致\n"
            "  \"alignment_check\": [\n"
            "     {\"cue_id\": \"cue1\", \"aligned\": true/false, \"reason\": \"<解释>\"}, ...\n"
            "  ],\n"
            "  \"coverage_reflection\": \"<说明该特质需要的线索是否已全部解析出来，若不足指出缺口>\",\n"
            "  \"pass\": <bool>  # 若特质错误、存在关键未对齐或线索不足，则为 false\n"
            "  \"correct\":  \"<第1段：表达准确性评估；第2段：标准性合规/若违规列点及修正建议>\"。\n"
            "}\n"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": storyboard_data},
        ]
        resp = tool_model.invoke(messages)
        content = getattr(resp, "content", None)
        if not content:
            return "(分镜反思失败: 空响应)"
        return str(content).strip()
    except Exception as e:
        return f"(分镜反思失败: {e})"


def reflect_video_prompt(video_prompt_data: str) -> str:
    """对视频提示词进行评分与改进建议，必要时返回 revised_video_prompt。同时将高质量prompt保存到JSON文件。"""
    try:
        print("[TOOL reflect_video_prompt:llm]")
        system_prompt = (
            "你是PSJT 构念一致性评审专家,你熟悉大五人格理论**你的任务：\n"
            "你的任务是确保输入的 video_prompt JSON 保持构念的信效度。\n\n"
            "【重要提醒】\n"
            "如果输入数据中包含明确的特质信息（如'特质：开放性'），请优先使用该特质信息进行判断，而不是仅根据视频提示词内容推断。\n\n"
            "知识" 
            "###大五人格理论  "
            "开放性:评估一个人对新经验的开放程度、想象力与探索未知的倾向。"
            "责任心:评估一个人在计划性、自我管理和目标导向方面的表现。"
            "外向性:评估一个人在社交互动中表现出的活力、主动性与参与程度。"
            "宜人性:评估一个人在他人互动中展现出的合作性、同理心与信任倾向。"
            "神经质:评估一个人情绪稳定性的程度及对压力和消极情绪的敏感性。"
            "【评审维度】\n"
            "1. **构念正确性**：根据 video_prompt_data JSON 判断隐含的人格特质。优先使用输入中明确标注的特质信息。\n"
            "2. **构念对齐性**：是否与reflect_cues解析的特质保持一致。\n"
            "3. **线索充分性反思**：思考当前提示词是否已经覆盖了支撑该特质的所有必要文本线索，若有遗漏需指出。\n"
            "4. **线索与特质**：提示词是否能够准确表达当前待测特质，为什么。\n"
            "5. **分镜标准性**：是否进行了额外的添加与补充，影响了待测特质的稳定性。\n"
            "【输出要求】严格使用一个 JSON 对象，必须对应上述5个评审维度：\n"
            "{\n"
            "  \"trait\": \"<识别出的人格特质：解释原因>\",  # 对应维度1：构念正确性\n"
            "  \"consistency_with_cues\": true/false,  # 对应维度2：构念对齐性\n"
            "  \"alignment_check\": [\n"
            "     {\"cue_id\": \"cue1\", \"aligned\": true/false, \"reason\": \"<解释>\"}, ...\n"
            "  ],\n"
            "  \"coverage_reflection\": \"<说明该特质需要的线索是否已全部解析出来，若不足指出缺口>\",  # 对应维度3：线索充分性反思\n"
            "  \"trait_expression\": \"<说明提示词如何准确表达当前待测特质，解释原因>\",  # 对应维度4：线索与特质\n"
            "  \"storyboard_standard\": \"<评估是否进行了额外的添加与补充，是否影响了待测特质的稳定性>\",  # 对应维度5：分镜标准性\n"
            "  \"pass\": <bool>  # 综合评估：若特质错误、存在关键未对齐或线索不足，则为 false\n"
            "}\n"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": video_prompt_data},
        ]
        resp = tool_model.invoke(messages)  # type: ignore
        content = getattr(resp, "content", None)
        if not content:
            return "(视频提示词反思失败: 空响应)"
        return str(content).strip()
    except Exception as e:
        return f"(视频提示词反思失败: {e})"

def pretty_print_turn(turn, output_dir: str | None = None):
    """打印并保存输出内容为JSON文件。
    如果提供 output_dir，则保存到该目录；否则保存到 agents/results/output_json。
    """
    # 收集所有输出内容
    output_content = []

    for msg in turn["messages"]:
        if isinstance(msg, HumanMessage):
            print(f"[Human]: {msg.content}")
        elif isinstance(msg, AIMessage):
            # 如果AIMessage里包含工具调用，可以提取
            if msg.additional_kwargs.get("tool_calls"):
                print(f"[AI-tool-call]: {msg.additional_kwargs['tool_calls']}")
            else:
                print(f"[AI]: {msg.content}")
                # 只保存AI的输出内容
                if msg.content:
                    output_content.append(msg.content)
        elif isinstance(msg, ToolMessage):
            print(f"[Tool-{msg.name}]: {msg.content}")
            # 只保存工具的输出内容
            if msg.content:
                output_content.append(msg.content)
        else:
            print(f"[Other]: {msg}")

    # 保存输出内容为JSON文件
    if output_content:
        try:
            # 选择输出目录
            if output_dir:
                results_dir = output_dir
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                results_dir = os.path.join(current_dir, "results", "output_json")
            os.makedirs(results_dir, exist_ok=True)

            # 生成文件名
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"output_content_{timestamp_str}.json"
            json_filepath = os.path.join(results_dir, json_filename)

            # 创建简化的数据结构
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "output_content": output_content
            }

            # 保存到JSON文件
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"\n✅ 输出内容已保存到: {json_filepath}")
            return json_filepath

        except Exception as e:
            print(f"⚠️ 保存JSON文件时出错: {e}")
            return None
    else:
        print("\n⚠️ 没有找到输出内容")
        return None

