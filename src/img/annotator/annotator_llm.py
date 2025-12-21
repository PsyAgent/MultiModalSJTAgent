# %%
from __future__ import annotations
import json
import os.path as op
from string import Template
from textwrap import dedent
from typing import Sequence

from dotenv import load_dotenv

from PIL import Image
from tqdm.auto import tqdm

from lmitf.agent_llm import AgentLLM
from lmitf.base_llm import extract_json

if __name__ == "__main__":
    from utils import number_images
else:
    from .utils import number_images
import ast

load_dotenv()
# %%
# ---------------------------------------------------------------------------
# Prompt templates and reusable text snippets
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = dedent(
    """
# 图像情景旁白/对话气泡设计专家

你是一个给图像情景判断测验增加对话气泡或旁白的专家。
请基于情景判断测验的原则， 所有内容应该是测量被试，而非替被试做出心理活动或行为决策。
所有内容不应该与反应项冲突，也不应该暗示某一个反应项。
对话气泡可以是人物间的对话，也可以是人物的内心独白。
旁白内容使用第二人称视角描述，即以“你”为主语。
所有内容能够有效补充图像情景的表达，突出情景的核心主题，测量被试的心理构念。

## Background
### Visual Narrative Grammar (VNG)**：
VNG 是一种分析和构建视觉叙事的框架，描述了人类能够理解的，基于图像序列的视觉叙事。VNG 将视觉叙事分解为四种基本单元：
- **Establisher (E)**：引入角色与场景，建立语境与中性基调。
- **Initial (I)**：启动冲突或动作，呈现早期张力。
- **Prolongation (Pr)**：延缓至高潮的过渡与铺垫，通过细节与节奏增强紧张感。
- **Peak (P)**：高潮或转折点，呈现核心认知或决策瞬间。
### 输入图片序列与VNG单元对应关系
输入的图片序列如果长度为2，则说明序列1为E，序列2为P；
如果长度为3，则说明序列1为E，序列2为I，序列3为P或Pr；
如果长度为4，则说明序列1为E，序列2为I，序列3为Pr，序列4为P。

## GOAL
你的目标是基于用户输入的文字情景与对应的图像情景序列，理解情景主题，并设计出能够让图像序列被良好理解的对话气泡或旁白。
每张图片最多可以同时存在一个对话气泡或旁白，你需要仔细斟酌对话/旁白内容以最大化表达原始情景的叙事功能。
确保对话气泡或旁白不应暗示任何特定的反应选项，而是应保持中立和开放，以便被试能够根据自己的判断选择反应选项。

## INPUT
- 文字情景判断测验题目（Situation Item）：包括情景判断测验题干(situation)与反应项(options)
- 测量构念（Construct）：情景判断测验所测量的心理构念
- 图像情景序列（Image Sequence）：一组从左到右发展，遵循VNG语法的图像，展示了情景判断测验的题干情景。
- 情景判断测验主角姓名（ActivateCharacterName）：情景判断测验主角的姓名
- 情景判断测验主角图像（AnalyzeCharacterImage）：情景判断测验主角的单人肖像

## WORKFLOW
1. 理解文字情景判断测验题目与其反应项，抓住情景的核心主题。
2. 观察图像情景序列，理解每张图像所表达的内容与标记出的人脸编号。
3. 针对每张图像（E, I, Pr, P），基于其在VNG的叙事功能，设计对话或旁白。
3.1 E：对话或旁白应该阐述清晰情景起点，使得图片与文字结合后，被试能够清晰理解情景背景。
3.2 I：对话或旁白应该表达清楚情景中的冲突或动作的起因，使得图片与文字结合后，情景中的冲突或动作的起因清晰明确。
3.3 Pr：对话或旁白应该延续I中的冲突或动作，使得图片与文字结合后，情景中的冲突或动作的延续更加清晰明确。
3.4 P：对话或旁白应该突出情景的高潮或转折点，使得图片与文字结合后，情景的高潮或转折能够被良好理解。
4. 反思对话气泡或旁白，确保其能够补充图像情景对文本情景的语义表达，且不与反应项冲突。
4. 确保对话气泡或旁白简洁明了，易于理解。
5. 输出设计好的对话气泡或旁白。

## Constraints
- 如果旁白需要提及情景判断测验主角，使用第二人称视角描述，即“你”，而不是情景判断测验主角姓名（ActivateCharacterName）。
- 如果对话来自情景判断测验主角，使用第一人称视角描述，即“我”，而不是情景判断测验主角姓名（ActivateCharacterName）。
- 情景判断测验主角是整个情景判断测验的核心代指，在文本中会提及它的名字。
- 仅需要对情景涉及到的关键角色进行对话设计。
- 语言应简洁明了，在15个字以内，避免复杂句式，且语法正确。
- 每张图片可以有三种情况：只能有一个对话气泡，只有一个旁白，或同时拥有一个对话气泡和一个旁白。
- 若是对话气泡，请将对话内容与图像中的人脸编号对应起来，确保对话内容与人物角色一致。
- 如果单一对话或单一旁白难以让人理解图像情景，才选择对话与旁白同时存在的情况。
- 在对话与旁白同时存在的情况下，二者不得冲突，需要从不同的角度良好表达出原始文字情景的叙事。
- 对话气泡或旁白不应暗示任何特定的反应选项，而是应保持中立和开放，以便被试能够根据自己的判断选择反应选项。

## KNOWLEDGE
- 对话气泡不一定是人物间的对话，也可以是人物的内心独白。
- 图像情景序列是从左到右发展的时间序列
- 情景序列中的每张图片的人脸均已被标记编号，但是不同图片的人脸编号不具备跨图片的一致性，以每张图片中的编号为准。
- 输出人脸编号请基于当前图片中的编号
- 图片序列按照视觉叙事语法进行编排，通常每张图片都承载着情节发展的某个关键节点，按照E（Establisher），I（Initial），P（Peak），R（Release）的顺序发展。



## OUTPUT
- 如果是对话气泡，请输出如下格式：
[{
    "annotation_type": "dialogue",
    content: {"face_id": 1, "text": "..." }
}]

- 如果是旁白，请输出如下格式：
[{
    "annotation_type": "narration",
    content: {"text": "..." }
}]

- 如果同时有对话气泡和旁白，，请输出如下格式：
[
    {
        "annotation_type": "dialogue",
        content: {"face_id": 1, "text": "..." }
    },
    {
        "annotation_type": "narration",
        content: {"text": "..." }
    }
]

‼️请严格以JSON格式输出，不要有任何多余的文本。
‼️你的输出有且只能如下有三种情况：
    1. 只有一个对话气泡
    2. 只有一个旁白
    3. 同时有一个对话气泡和一个旁白（不可2个对话气泡或2个旁白）
‼️你的输出严禁出现其他任何内容，必须严格遵守上述格式要求。
    """
).strip()

CONDITIONED_FRAME_1_TEXT = dedent(
    """
    请基于如下信息，首先构思对话气泡或旁白。
    我在接下来会向你从左往右依次输入每个pannel， 共 $n_pannel 个pannel：

    Situation Item:
    $SituationItem
    
    Construct:
    $Construct

    Image Sequence:
    上传的图片序列

    Activate Character Name:
    $ActivateCharacterName

    Activate Character Image:
    上传的单人肖像
    """
).strip()

CONDITIONED_FRAME_2_TEXT = dedent(
    """
    现在是panel $panel_id， 如果是对话气泡，请基于该图片的face id进行回答：
    请严格以JSON格式输出，不要有任何多余的文本。
    """
).strip()

DEFAULT_SITUATION = dedent(
    """
    {
        'situation': "Ye're on the tram with a friend. At one stop, an attractive woman gets on. As she passes Ye, Ye's friend whistles after her.\xa0\xa0The woman turns irritated and looks at Ye",
        'options': {'A': 'I embarrassingly look to the side and avoid eye contact.',
                    'B': 'I embarrassingly look to the side and later tell my friend that I found his action quite stupid.',
                    'C': 'I compliment her.',
                    'D': 'I laugh and point my finger at my friend.'}
    }
    """
).strip()

DEFAULT_CONSTRUCT = "Neuroticism: Self-consciousness"
DEFAULT_ACTIVATE_CHARACTER_NAME = "Ye"
INITIAL_ASSISTANT_RESPONSE = (
    "好的，我理解了情景描述和图像序列。现在请依次输入每个pannel的图片，我会为每张图片设计对话气泡或旁白。"
)

DEFAULT_ONE_SHOT_OUTPUT = [
    [{"annotation_type": "narration", "content": {"text": "你和朋友一起坐在电车上"}}],
    [{"annotation_type": "narration", "content": {"text": "此时，一位漂亮的女士上了车"}}],
    [{"annotation_type": "dialogue", "content": {"face_id": 5, "text": "（吹口哨）：美女～"}},
     {"annotation_type": "narration", "content": {"text": "女士经过你身边时，你的朋友对她吹了口哨"}}],
    [{"annotation_type": "narration", "content": {"text": "女士生气地看着你"}}],
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def img_path(filename: str) -> str:
    """Construct an absolute path for demo assets bundled with the annotator."""

    return op.join(op.dirname(__file__), "annotator_example", filename)


def load_demo_panels() -> list[Image.Image]:
    """Load the default panel images used for one-shot priming and demos."""

    return [Image.open(img_path(f"scene_{idx}.png")) for idx in range(4)]


def number_panels(panels: Sequence[Image.Image]) -> list[Image.Image]:
    """Add numeric overlays to panels to help the LLM reference face ids consistently."""

    return number_images(
        panels,
        30,
        prefix="panel_",
        text_color="black",
        outline_color="white",
        add_bar=True,
    )


# ---------------------------------------------------------------------------
# Annotator core
# ---------------------------------------------------------------------------
class AnnotatorLLM:
    """LLM-driven annotator that designs dialogue bubbles or narrations for image panels."""

    def __init__(
        self,
        ref_name: str | None = None,
        ref_img: Image.Image | None = None,
        model: str = "gpt-5-nano",
    ) -> None:
        self.agent = AgentLLM(model=model)
        self.ref_name = ref_name
        self.ref_img = ref_img

        self.conditioned_frame_1 = Template(CONDITIONED_FRAME_1_TEXT)
        self.conditioned_frame_2 = Template(CONDITIONED_FRAME_2_TEXT)

        self.one_shot_situation = DEFAULT_SITUATION
        self.one_shot_construct = DEFAULT_CONSTRUCT
        self.one_shot_activate_character_name = DEFAULT_ACTIVATE_CHARACTER_NAME
        self.one_shot_activate_character_image = Image.open(img_path("ActivateCharacter.png"))
        self.one_shot_image_sequence = Image.open(img_path("vng.png"))
        self.one_shot_panels = load_demo_panels()
        self.one_shot_output = DEFAULT_ONE_SHOT_OUTPUT
        self.initialized = False

    def initialize(self) -> None:
        """Prime the agent with the system prompt and one-shot conversation history."""

        if self.initialized:
            return

        self.agent.add_system_prompt(SYSTEM_PROMPT)
        self.agent.add_user_text(
            self.conditioned_frame_1.substitute(
                SituationItem=self.one_shot_situation,
                ActivateCharacterName=self.one_shot_activate_character_name,
                n_pannel=len(self.one_shot_panels),
                Construct=self.one_shot_construct,
            )
        )
        self.agent.add_user_image(self.one_shot_activate_character_image)
        self.agent.add_user_image(self.one_shot_image_sequence)
        self.agent.add_assistant_text(INITIAL_ASSISTANT_RESPONSE)

        numbered_panels = number_panels(self.one_shot_panels)
        for panel_id, panel in enumerate(numbered_panels):
            self.agent.add_user_text(
                self.conditioned_frame_2.substitute(panel_id=panel_id)
            )
            self.agent.add_user_image(panel)
            self.agent.add_assistant_text(
                json.dumps(self.one_shot_output[panel_id], ensure_ascii=False)
            )

        self.initialized = True

    def call(
        self,
        situation_item: str,
        construct: str,
        image_sequence: Image.Image,
        panels: Sequence[Image.Image],
        initialize: bool = True,
        verbose: bool = True,
    ) -> list[dict]:
        """基于情景描述与图像序列，逐张图像设计对话气泡或旁白。"""

        if initialize and not self.initialized:
            self.initialize()

        self.agent.add_user_text(
            self.conditioned_frame_1.substitute(
                SituationItem=situation_item,
                ActivateCharacterName=self.ref_name,
                n_pannel=len(panels),
                Construct=construct,
            )
        )
        self.agent.add_user_image(self.ref_img)
        self.agent.add_user_image(image_sequence)
        self.agent.add_assistant_text(INITIAL_ASSISTANT_RESPONSE)

        responses: list[dict] = []
        numbered_panels = number_panels(panels)
        progress_bar = tqdm(numbered_panels, desc="Annotating panels", disable=not verbose, leave=False)

        for panel_id, panel in enumerate(progress_bar):
            self.agent.add_user_text(
                self.conditioned_frame_2.substitute(panel_id=panel_id)
            )
            self.agent.add_user_image(panel)

            response_text = self.agent.call()
            try:
                response_content = json.loads(response_text)
            except json.JSONDecodeError:
                try:
                    # Try to evaluate as a Python literal (can handle single quotes)
                    response_content = ast.literal_eval(response_text)
                except (ValueError, SyntaxError):
                    # If that fails too, fall back to extract_json
                    response_content = extract_json(response_text)

            responses.append(response_content)
            self.agent.add_assistant_text(str(response_content))
            progress_bar.set_postfix({"Latest": str(response_content)})

        return responses

# %%
# ---------------------------------------------------------------------------
# Demo / ad-hoc execution helpers
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    DEFAULT_ACTIVATE_CHARACTER_IMAGE = Image.open(img_path("ActivateCharacter.png"))
    DEFAULT_IMAGE_SEQUENCE = Image.open(img_path("vng.png"))
    DEFAULT_PANELS = load_demo_panels()

    agent = AnnotatorLLM(
        ref_name=DEFAULT_ACTIVATE_CHARACTER_NAME,
        ref_img=DEFAULT_ACTIVATE_CHARACTER_IMAGE,
        model="gpt-5",
    )
    res = agent.call(
        situation_item=DEFAULT_SITUATION,
        image_sequence=DEFAULT_IMAGE_SEQUENCE,
        panels=DEFAULT_PANELS,
        construct=DEFAULT_CONSTRUCT,
        verbose=True,
        
    )
#%%
