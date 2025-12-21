# MultiModal SJT Agent

多模态情境判断测验（SJT）生成平台，支持文本、图像、视频三种形态。

<p align="center">
  <img src="resources/Intro.png" alt="MultiModal SJT Agent Intro" width="900" />
</p>

| 研究流程 | 生成结果 |
| --- | --- |
| ![Research Flow](resources/research.png) | ![Results](resources/results.png) |

## 快速开始

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆并启动
git clone https://github.com/PsyAgent/MultiModalSJTAgent.git
cd MultiModalSJTAgent
cp .env.example .env  # 配置 OPENAI_API_KEY

uv sync && uv run python app.py
```

访问 http://localhost:4399

<details>
<summary>其他部署方式</summary>

**Docker**
```bash
docker build -t multimodal-sjt-agent .
docker run -d -p 4399:4399 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/.env:/app/.env \
  --name sjt-agent multimodal-sjt-agent
```
</details>

## API 示例

```bash
# 获取维度列表
curl http://localhost:4399/api/traits

# 生成文本 SJT
curl -X POST http://localhost:4399/api/generate/text \
  -H "Content-Type: application/json" \
  -d '{"trait_id": "N1", "item_id": "1", "situation_theme": "大学生活"}'
```

<details>
<summary>更多 API</summary>

```bash
# 生成图像 SJT
curl -X POST http://localhost:4399/api/generate/image \
  -H "Content-Type: application/json" \
  -d '{"trait_id": "N1", "item_id": "1", "ref_character": "male"}'

# 生成视频 SJT
curl -X POST http://localhost:4399/api/generate/video \
  -H "Content-Type: application/json" \
  -d '{"trait_id": "N1", "item_id": "1"}'
```
</details>

---

**技术栈**: Flask · LangChain · LangGraph · OpenCV · InsightFace · MoviePy
**GitHub**: https://github.com/PsyAgent | **Issues**: https://github.com/PsyAgent/MultiModalSJTAgent/issues
