import os
import requests
import time
from typing import Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv

from ...config import CONFIG

load_dotenv()

# DMXAPI 已迁移到 OpenAI 风格的视频接口：
#   创建: POST {base_url}/videos
#   查询: GET  {base_url}/videos/{task_id}   -> status/progress, 完成后 metadata.url 为下载链接
#   下载: GET  {base_url}/videos/{task_id}/content
# 旧的 /v1/video_generation、/v1/query/video_generation、/v1/files/retrieve 已下线（404）。
_VIDEO_CFG = CONFIG.get('video', {})
BASE_URL = str(CONFIG.get('base_url', 'https://www.dmxapi.cn/v1')).rstrip('/')
VIDEO_MODEL = _VIDEO_CFG.get('video_model', 'MiniMax-Hailuo-02')
VIDEO_DURATION = int(_VIDEO_CFG.get('duration', 10))
VIDEO_RESOLUTION = _VIDEO_CFG.get('resolution', '768P')

VIDEO_CREATE_URL = f"{BASE_URL}/videos"
VIDEO_QUERY_URL = BASE_URL + "/videos/{}"
VIDEO_CONTENT_URL = BASE_URL + "/videos/{}/content"

api_key = os.getenv("OPENAI_API_KEY") or os.getenv("MINIMAX_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}


def create_video_task(
    prompt: str,
    *,
    model: str | None = None,
    duration: int | None = None,
    resolution: str | None = None,
) -> Optional[str]:
    payload = {
        "model": model or VIDEO_MODEL,
        "prompt": prompt,
        "duration": duration if duration is not None else VIDEO_DURATION,
        "resolution": resolution or VIDEO_RESOLUTION,
    }
    resp = requests.post(VIDEO_CREATE_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print("创建失败:", resp.status_code, resp.text)
        return None
    resp_json = resp.json()
    task_id = resp_json.get("task_id") or resp_json.get("id")
    print("创建成功 task_id:", task_id)
    return task_id


def query_video_task(task_id: str) -> Optional[Dict[str, Any]]:
    resp = requests.get(VIDEO_QUERY_URL.format(task_id), headers=headers)
    if resp.status_code != 200:
        print("查询失败:", resp.status_code, resp.text)
        return None
    return resp.json()


def download_video(task_id: str, info: Dict[str, Any], output_dir: str) -> Optional[str]:
    """任务完成后下载视频：优先用查询结果里的下载链接，否则走 /content 接口。"""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"hailuo_video_{timestamp}.mp4")

    download_url = (
        (info.get("metadata") or {}).get("url")
        or info.get("download_url")
        or info.get("url")
    )
    if download_url:
        resp = requests.get(download_url)
    else:
        resp = requests.get(VIDEO_CONTENT_URL.format(task_id), headers=headers)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(resp.content)
    print(f"视频已成功保存至 {filepath}")
    return filepath


def _trait_to_output_subdir(trait: str) -> str:
    """根据用户输入的特质映射到 Video_SJT 下的子目录名。
    你可以在这里自定义五类映射规则。
    """
    key = (trait or "").strip().lower()
    mapping = {
        # 示例：按大五人格或自定义标签分类
        "外向性": "Extraversion",
        "外倾性": "Extraversion",
        "extraversion": "Extraversion",
        "开放": "Openness",
        "开放性": "Openness",
        "openness": "Openness",
        "责任心": "Conscientiousness",
        "尽责性": "Conscientiousness",
        "conscientiousness": "Conscientiousness",
        "宜人": "Agreeableness",
        "宜人性": "Agreeableness",
        "agreeableness": "Agreeableness",
        "神经质": "Neuroticism",
        "情绪不稳定": "Neuroticism",
        "neuroticism": "Neuroticism",
    }
    if key in mapping:
        return mapping[key]
    # 传进来的往往是「O (Openness) / 开放性 —— 子维度 O6：价值观」这类完整描述，
    # 精确匹配不到时按子串再找一次。
    for name, subdir in mapping.items():
        if name in key:
            return subdir
    # 默认兜底目录
    return "Misc"


def _ensure_next_env_subdir(base_dir: str) -> str:
    """在 base_dir 下创建按顺序递增的 env 子目录（env1, env2, ...），返回新建的子目录路径。"""
    try:
        os.makedirs(base_dir, exist_ok=True)
        existing = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        indices = []
        for name in existing:
            if name.startswith("env"):
                suffix = name[3:]
                if suffix.isdigit():
                    indices.append(int(suffix))
        next_idx = (max(indices) + 1) if indices else 1
        subdir = os.path.join(base_dir, f"env{next_idx}")
        os.makedirs(subdir, exist_ok=True)
        return subdir
    except Exception:
        # 回退到 base_dir，自身可写
        return base_dir


def run_hailuo_pipeline(
    prompt: str,
    *,
    model: str | None = None,
    duration: int | None = None,
    resolution: str | None = None,
    poll_interval: int = 8,
    max_polls: int = 100,
    auto_download: bool = True,
    output_dir: str = "results/video",
    trait: str | None = None,
) -> Optional[Dict[str, Any]]:
    """一键执行：创建→轮询→下载（可选）。返回最终查询结果（含保存路径）。"""
    task_id = create_video_task(prompt, model=model, duration=duration, resolution=resolution)
    if not task_id:
        return None

    info: Optional[Dict[str, Any]] = None
    for i in range(max_polls):
        info = query_video_task(task_id)
        if not info:
            time.sleep(poll_interval)
            continue
        status = (info.get("status") or "").lower()
        progress = info.get("progress")
        print(f"轮询 {i+1}/{max_polls}: status={status}, progress={progress}")
        if status == "completed":
            break
        if status in ("failed", "cancelled", "error"):
            print("视频生成失败:", info)
            return None
        time.sleep(poll_interval)

    if not info or (info.get("status") or "").lower() != "completed":
        print("轮询超时，任务未完成。task_id:", task_id)
        return None

    if auto_download:
        # 如果提供了 trait，则输出到 agents/results/CIBOL_Video_SJT/<Trait>/<envN>
        if trait is not None:
            vsjt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "CIBOL_Video_SJT")
            trait_dir_name = _trait_to_output_subdir(trait)
            trait_dir = os.path.join(vsjt_dir, trait_dir_name)
            output_dir = _ensure_next_env_subdir(trait_dir)
        else:
            # 保持原有默认目录（相对 Hailuo.py 所在目录）
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
            os.makedirs(base_dir, exist_ok=True)
            output_dir = base_dir

        try:
            filepath = download_video(task_id, info, output_dir)
            if filepath:
                info["saved_video_path"] = filepath
                info["saved_dir"] = output_dir
        except Exception as e:
            print("视频下载失败:", e)

    return info
