# MultiModal SJT Agent

多模态情境判断测验（SJT）生成与可视化平台，覆盖文本、图像、视频三种形态，服务于人格维度与情境任务的研究与应用。

<p align="center">
  <img src="resources/Intro.png" alt="MultiModal SJT Agent Intro" width="900" />
</p>

## 项目亮点

- 📝 **文本生成**：基于特质解析与情景构建，自动生成高质量文字情境判断测试
- 🖼️ **图像生成**：通过场景图网络与视觉渲染技术，生成包含人物和场景的图片测试
- 🎬 **视频生成**：利用多媒体AI与情境系统理论，创建动态视频形式的情境测试
- 🔬 **科学验证**：基于 NEO-PI-R 维度与 PSJT-Mussel 情境数据，经过大规模心理测量学验证
- 🚀 **快速部署**：支持 Docker 一键部署，使用 uv 实现极速依赖安装

## 界面与结果

| 研究流程 | 生成结果 |
| --- | --- |
| ![Research Flow](resources/research.png) | ![Results](resources/results.png) |

## 快速开始

### 方式一：Docker Compose（推荐）

最简单的部署方式，开箱即用：

```bash
# 1. 克隆项目
git clone https://github.com/PsyAgent/MultiModalSJTAgent.git
cd MultiModalSJTAgent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 3. 启动服务（使用 uv 快速构建）
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

访问：**http://localhost:4399**

> **优势**：Dockerfile 使用 `uv` 进行依赖管理，构建速度比 pip 快 **10-100倍**，支持精确的依赖锁定。

### 方式二：Docker 手动构建

```bash
# 构建镜像
docker build -t multimodal-sjt-agent .

# 运行容器
docker run -d \
  -p 4399:4399 \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/.env:/app/.env \
  --name sjt-agent \
  multimodal-sjt-agent

# 查看日志
docker logs -f sjt-agent

# 停止容器
docker stop sjt-agent
docker rm sjt-agent
```

### 方式三：本地开发

#### 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (推荐) 或 pip

#### 安装 uv

```bash
# macOS 和 Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

#### 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/PsyAgent/MultiModalSJTAgent.git
cd MultiModalSJTAgent

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 3. 使用 uv 安装依赖（推荐）
uv sync

# 或使用 pip（较慢）
pip install -r requirements.txt

# 4. 启动服务
uv run python app.py
# 或使用 python
python app.py
```

访问：**http://localhost:4399**

## 使用流程

1. **选择维度**：在首页选择 NEO-PI-R 人格维度
2. **选择模式**：文本 / 图像 / 视频
3. **配置参数**：设置情境主题、目标人群等
4. **生成测试**：点击生成按钮，自动创建 SJT
5. **下载结果**：生成结果保存在 `outputs/` 目录

## API 接口

### 获取维度列表

```bash
curl http://localhost:4399/api/traits
```

### 获取维度条目

```bash
curl http://localhost:4399/api/items/<trait_id>
```

### 生成文本 SJT

```bash
curl -X POST http://localhost:4399/api/generate/text \
  -H "Content-Type: application/json" \
  -d '{
    "trait_id": "N1",
    "item_id": "1",
    "situation_theme": "大学生活",
    "target_population": "中国大学生",
    "n_items": 1
  }'
```

### 生成图像 SJT

```bash
curl -X POST http://localhost:4399/api/generate/image \
  -H "Content-Type: application/json" \
  -d '{
    "trait_id": "N1",
    "item_id": "1",
    "ref_character": "male",
    "run_bubble": true
  }'
```

### 生成视频 SJT

```bash
curl -X POST http://localhost:4399/api/generate/video \
  -H "Content-Type: application/json" \
  -d '{
    "trait_id": "N1",
    "item_id": "1"
  }'
```

## 项目结构

```
MultiModalSJTAgent/
├── app.py                      # Flask 应用主入口
├── src/                        # 核心逻辑模块
│   ├── txt/                    # 文本 SJT 生成
│   │   ├── workflow/           # 生成工作流
│   │   └── datasets/           # 数据集加载
│   ├── img/                    # 图像 SJT 生成
│   │   ├── pipeline/           # 图像生成管道
│   │   ├── annotator/          # 对话气泡标注
│   │   └── resources/          # 参考角色图片
│   └── vid/                    # 视频 SJT 生成
│       └── agents/             # 视频生成代理
├── templates/                  # HTML 模板
│   ├── base.html              # 基础模板
│   ├── index.html             # 首页
│   ├── text_sjt.html          # 文本生成页面
│   ├── image_sjt.html         # 图像生成页面
│   └── video_sjt.html         # 视频生成页面
├── static/                     # 静态资源
│   ├── css/                   # 样式文件
│   ├── js/                    # JavaScript
│   ├── Intro.png              # 项目介绍图
│   ├── research.png           # 研究流程图
│   └── results.png            # 验证结果图
├── outputs/                    # 生成结果输出目录
├── resources/                  # 项目资源文件
├── Dockerfile                  # Docker 配置（使用 uv）
├── docker-compose.yml          # Docker Compose 配置
├── .dockerignore              # Docker 忽略文件
├── pyproject.toml             # uv 项目配置
├── uv.lock                    # uv 依赖锁文件
├── requirements.txt           # pip 依赖清单
├── .env.example               # 环境变量模板
└── README.md                  # 项目文档
```

## 配置说明

在 `.env` 文件中配置以下环境变量：

```env
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 技术栈

### 后端框架
- **Flask** - Web 应用框架
- **Python 3.12** - 编程语言

### AI & 机器学习
- **OpenAI API** - 语言模型
- **LangChain** - LLM 应用框架
- **LangGraph** - 多代理协作框架

### 图像处理
- **OpenCV** - 计算机视觉
- **Pillow** - 图像处理
- **InsightFace** - 人脸识别与分析

### 视频处理
- **MoviePy** - 视频编辑

### 部署工具
- **Docker** - 容器化
- **uv** - 快速 Python 包管理器

## 开发指南

### 添加新的 SJT 生成模式

1. 在 `src/` 下创建新模块
2. 实现生成逻辑
3. 在 `app.py` 中添加 API 路由
4. 在 `templates/` 中添加页面模板
5. 更新导航菜单

### 调试技巧

```bash
# 启用 Flask 调试模式
export FLASK_ENV=development
python app.py

# Docker 日志查看
docker-compose logs -f

# 进入容器调试
docker exec -it sjt-agent bash
```

## 常见问题

### Q: 依赖安装失败？
A: 优先使用 `uv sync`，速度更快且更可靠。如果失败，尝试：
```bash
uv sync --no-cache
```

### Q: Docker 构建很慢？
A: Dockerfile 已使用 uv 优化，构建速度比 pip 快 10-100倍。首次构建需下载依赖，后续会使用缓存。

### Q: 生成结果在哪里？
A: 所有生成结果保存在 `outputs/` 目录，可通过 `/outputs/<filename>` 访问。

### Q: 如何更换 API 密钥？
A: 编辑 `.env` 文件，修改 `OPENAI_API_KEY`，然后重启服务：
```bash
docker-compose restart
```

## 性能优化

- ⚡ **uv 包管理**：比 pip 快 10-100倍的依赖安装
- 🐳 **Docker 多阶段构建**：优化镜像大小和构建速度
- 📦 **依赖锁定**：使用 `uv.lock` 确保可复现的构建
- 🔄 **层缓存**：智能缓存策略，加速重复构建

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 许可证

© 2025 PsyAgent Team

## 联系方式

- **GitHub**: https://github.com/PsyAgent
- **Issues**: https://github.com/PsyAgent/MultiModalSJTAgent/issues
