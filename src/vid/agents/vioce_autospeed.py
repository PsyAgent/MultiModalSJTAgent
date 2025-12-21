#%%
import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

DMX_TTS_URL = "https://www.dmxapi.cn/v1/audio/speech"
DMX_API_KEY = os.getenv("OPENAI_API_KEY")


def synthesize_voice(text: str, output_path: str = "results/audio/output.mp3", voice: str = "alloy", model: str = "gpt-4o-mini-tts", speed: float = 1.0) -> str:
    """将 text 合成为语音并保存到 output_path，返回最终文件路径。"""
    try:
        if not DMX_API_KEY:
            raise RuntimeError("缺少 MINIMAX_API_KEY 环境变量")

        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "speed": speed
        }

        response = requests.post(
            DMX_TTS_URL,
            headers={"Authorization": f"Bearer {DMX_API_KEY}"},
            json=payload,
        )
        response.raise_for_status()

        if response.headers.get("Content-Type", "").lower() in ("audio/mpeg", "audio/mp3"):
            # 确保目录存在
            out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
            os.makedirs(out_dir, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"语音合成成功，已保存为 {output_path}")
            return output_path
        else:
            raise RuntimeError(f"错误响应: {response.text}")
    except Exception as e:
        print(f"请求出错: {e}")
        return ""
def generate_narration(
    text: str,
    target_duration: float = 10.0,
    output_dir: str | None = None,
    speed: float | None = None,
) -> str:
    """
    生成旁白：文案已精简，固定使用标准语速（1.0x），返回音频路径。
    """
    try:
        text_to_synthesize = (text or "").strip()
        if not text_to_synthesize:
            return ""

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = (output_dir or "results/audio").rstrip("/\\")
        os.makedirs(base_dir, exist_ok=True)
        audio_path = os.path.join(base_dir, f"hailuo_narration_{timestamp}.mp3")

        # 按文本长度自动设置语速：>54 字符使用 1.5x，否则 1.0x；也可外部显式传入 speed
        if speed is None:
            speed_val = 1.5 if len(text_to_synthesize) > 54 else 1.0
        else:
            speed_val = float(speed)

        return synthesize_voice(text=text_to_synthesize, output_path=audio_path, speed=speed_val)
    except Exception as e:
        print(f"旁白生成失败: {e}")
        return ""


if __name__ == "__main__":
    # 便捷测试入口：直接替换下面的台词文本
    demo_text ="在一个你活跃已久的聊天群里，你某次不经意的、有失精准的发言，突然被人截图重新发到了群里。大家各种调侃，还把你做成了表情包到处传。你突然发现，自己这点小糗事正被一堆人围观，你会怎么做？"
    print(len(demo_text))
    if len(demo_text)>60:
        s=1.5
    else:
        s=1.0
    generate_narration(text=demo_text, target_duration=10.0)

#%%