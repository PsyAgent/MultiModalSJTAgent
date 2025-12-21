## 项目简介

Video_SJT 是一个基于情境判断测试（SJT）的视频分析项目，结合多智能体流程与提示工程，对“大五人格”维度（CIBOL：Conscientiousness、Agreeableness、Extraversion、Neuroticism、Openness）进行分析与结构化输出，并可生成旁白音频。

### 主要特性
- **多智能体流程**：在 `agents/mulit_agent0.1.py`。
- **提示工程与模板**： `agents/prompts.py`。
- **音频旁白与语速控制**：`agents/vioce_autospeed.py`。
- **结构化结果输出**：按维度 存放于`gents/results/`。
- **音频和视频合成**：`test/merge_two_files.py` 
- **用户输入**：`agents/user_inputs.py` 

## 目录结构

```text
Video_SJT/
  agents/
    Hailuo.py                  # 调用hailuo生成视频
    mulit_agent0.1.py          # 多智能体主流程（v0.1）main函数
    prompts.py                 # 提示模板与文本配置   智能体提示词
    Tools.py                   # 通用工具函数       智能体调用工具函数
    user_inputs.py             # 用户输入配置
    vioce_autospeed.py         # 语速/音频处理
    results/
      audio/                   # 生成的音频（中间产物）
      CIBOL_Video_SJT/         # 五大人格维度结果
        Agreeableness/
        Conscientiousness/
        Extraversion/
        Neuroticism/
        Openness/
      output_json/             # 结构化 JSON 输出
  test/
    merge_two_files.py         # 视频音频合成
  README.md
  requirements.txt
```

## 环境要求
- **Python**：建议 3.9–3.11

安装依赖：
```bash
pip install -r requirements.txt
```

## 快速开始

```bash
python agents/mulit_agent0.1.py
```
1) 准备输入
- 调用` agents/user_inputs.py`，要求输入素材。
返回question_content, character_seed, trait, stem
完整题目（包含选项）、角色、特质、题目

2) 调用langgraph-swarm框架
配置智能体，进行步骤解析

3) 调用hailuo.py
进行视频生成

4) 查看输出
- 音频旁白与中间音频：`agents/results/audio/` 
- 结构化结果 JSON：`agents/results/output_json/` 
- 分维度产出：`agents/results/CIBOL_Video_SJT/*`

## 使用说明（要点）

- **多智能体协同**：`agents/mulit_agent0.1.py`
  - 负责组织视频/文本理解、问答生成、证据抽取、维度评分与解释。
  - 可在脚本顶部或配置区调整：是否生成音频、是否保存中间产物、运行维度等。

- **提示与模板**：`agents/prompts.py`
  - 维护 CIBOL 维度的定义、评分规则、解释模板。
  - 若需定制粒度或语言风格，从此处修改最为集中高效。

- **用户输入参数**：`agents/user_inputs.py`
  - 配置单次任务所需的动态输入（素材路径、受测者信息、语言开关、输出路径等）。

- **视频与音频处理**：`agents/Hailuo.py`、`agents/vioce_autospeed.py`
  - `Hailuo.py` 负责视频生成；`vioce_autospeed.py` 可调整语速与简单后处理。


## 常见问题（FAQ）

- **旁白生成失败或鉴权报错**
  - 检查 `Hailuo.py` 的服务/密钥配置；如使用网络代理，确保 Python 进程已放行。

- **结果目录未生成或为空**
  - 核对 `agents/user_inputs.py` 的输入路径与视频标识；确认主流程是否正常结束（无异常退出）。

- **如何新增或定制维度**
  - 在 `agents/prompts.py` 中增加维度定义与评分/解释规则；并在 `results/CIBOL_Video_SJT/` 下新增同名目录用于归档。

- **中英文切换**
  - 可在 `user_inputs.py` 或主脚本参数区增加语言开关；在 `prompts.py` 中维护对应语言的模板。
  
- **报错不存在moviepy包**
  - pip install moviepy==1.0.3