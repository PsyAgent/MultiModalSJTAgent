import os
import json
import requests
import time
from typing import Optional, Dict, Any
from datetime import datetime


VIDEO_CREATE_URL = "https://www.dmxapi.cn/v1/video_generation"
VIDEO_QUERY_URL = "https://www.dmxapi.cn/v1/query/video_generation"
FILES_RETRIEVE_URL = "https://www.dmxapi.cn/v1/files/retrieve"
DOWNLOAD_URL = FILES_RETRIEVE_URL
api_key = os.getenv("MINIMAX_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}


def create_video_task(prompt: str, *, model: str = "MiniMax-Hailuo-02", duration: int = 10, resolution: str = "768P") -> Optional[str]:
    payload =json.dumps ({
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
    })
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.request("POST", VIDEO_CREATE_URL, headers=headers, data=payload)
    if resp.status_code != 200:
        print("创建失败:", resp.status_code, resp.text)
        return None
    resp_json = resp.json()
    task_id = resp_json.get("task_id")
    print("创建成功 task_id:", task_id)
    return task_id


def query_video_task(task_id: str) -> Optional[Dict[str, Any]]:
    url = f"{VIDEO_QUERY_URL}?task_id={task_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("查询失败:", resp.status_code, resp.text)
        return None
    return resp.json()


def retrieve_video_file(file_id: str, task_id: str) -> Optional[Dict[str, Any]]:
    url = f"{FILES_RETRIEVE_URL}?file_id={file_id}&task_id={task_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print("检索失败:", resp.status_code, resp.text)
        return None
    return resp.json()


def fetch_video(file_id: str, output_dir: str = "results/video", task_id: str | None = None):
    """根据 file_id(可携带 task_id) 从 DMX files/retrieve 获取下载链接并保存。"""
    os.makedirs(output_dir, exist_ok=True)
    params = {"file_id": file_id}
    if task_id:
        params["task_id"] = task_id
    resp = requests.get(DOWNLOAD_URL, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    # 兼容多种返回结构
    download_url = (
        (data.get("file") or {}).get("download_url")
        or data.get("download_url")
        or (data.get("data") or {}).get("download_url")
        or data.get("url")
        or (data.get("data") or {}).get("url")
    )
    if not download_url:
        raise RuntimeError(f"未在检索结果中找到下载链接: {data}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hailuo_video_{timestamp}.mp4"
    filepath = os.path.join(output_dir, filename)

    vr = requests.get(download_url)
    vr.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(vr.content)
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
        "开放": "Openness",
        "开放性": "Openness",
        "责任心": "Conscientiousness",
        "尽责性": "Conscientiousness",
        "宜人": "Agreeableness",
        "宜人性": "Agreeableness",
        "神经质": "Neuroticism",
        "情绪不稳定": "Neuroticism",
    }
    # 默认兜底目录
    return mapping.get(key, "Misc")


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
    duration: int = 10,
    resolution: str = "768P",
    poll_interval: int = 8,
    max_polls: int = 100,
    auto_download: bool = True,
    output_dir: str = "results/video",
    trait: str | None = None,
) -> Optional[Dict[str, Any]]:
    """一键执行：创建→查询→检索（可选自动下载）。返回最终检索结果。"""
    task_id = create_video_task(prompt, duration=duration, resolution=resolution)
    if not task_id:
        return None

    file_id: Optional[str] = None
    for i in range(max_polls):
        info = query_video_task(task_id)
        if not info:
            time.sleep(poll_interval)
            continue
        file_id = info.get("file_id") or (info.get("data") or {}).get("file_id")
        status = (info.get("status") or (info.get("base_resp") or {}).get("status_msg") or "").lower()
        print(f"轮询 {i+1}/{max_polls}: status={status}, file_id={file_id}")
        if file_id:
            break
        time.sleep(poll_interval)

    if not file_id:
        print("暂未获得 file_id，请稍后重试。task_id:", task_id)
        return None

    retrieve = retrieve_video_file(file_id, task_id)
    if not retrieve:
        return None

    # 可选自动下载
    if auto_download:
        # 如果提供了 trait，则输出到 agents/results/Video_SJT/<Trait>/<envN>
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
        
        # 优先使用检索结果中的下载链接
        download_url = (
            retrieve.get("download_url")
            or (retrieve.get("data") or {}).get("download_url")
            or retrieve.get("url")
            or (retrieve.get("data") or {}).get("url")
        )
        if download_url:
            try:
                # 确保输出目录存在
                os.makedirs(output_dir, exist_ok=True)
                
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"hailuo_video_{timestamp}.mp4"
                filepath = os.path.join(output_dir, filename)
                
                r = requests.get(download_url)
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(r.content)
                print(f"视频已成功保存至 {filepath}")
                # 在返回对象中带回保存位置
                try:
                    if isinstance(retrieve, dict):
                        retrieve["saved_video_path"] = filepath
                        retrieve["saved_dir"] = output_dir
                except Exception:
                    pass
            except Exception as e:
                print("直接下载失败，尝试通过 fetch_video: ", e)
                try:
                    p = fetch_video(file_id, output_dir, task_id)
                    try:
                        if isinstance(retrieve, dict) and p:
                            retrieve["saved_video_path"] = p
                            retrieve["saved_dir"] = output_dir
                    except Exception:
                        pass
                except Exception as ee:
                    print("fetch_video 也失败:", ee)
        else:
            try:
                p = fetch_video(file_id, output_dir, task_id)
                try:
                    if isinstance(retrieve, dict) and p:
                        retrieve["saved_video_path"] = p
                        retrieve["saved_dir"] = output_dir
                except Exception:
                    pass
            except Exception as ee:
                print("fetch_video 失败:", ee)

    return retrieve