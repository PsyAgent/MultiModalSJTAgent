from __future__ import annotations
from string import Template

"""
VNG Polisher Prompt Template (SJT-aware)
---------------------------------------

Exports:
- vng_condition_system: system prompt with guardrails (includes SJT construct-validity rules)
- prompt_template: few-shot conversation messages ready to send to a chat model
- conditioned_frame: user message frame template for new inputs

Few-shot examples included:
1) Movie Theater (E/I/P)
2) SJT (Agreeableness) with corrected VNG (E/I/Pr/P), respecting fixed storyboard (no added/removed units)
"""

# =========================
# 1) System protocol (UPDATED with guardrails learned from the issues)
# =========================
vng_condition_system = """
# VNG Polisher
你是一个专业的文生图提示词工程师与心理学家，专注于以 **Visual Narrative Grammar (VNG)** 为原则，构建人格情景判断测验（sjt）的分镜文生图。
你精通心理测量学，理解情景判断测验的构念效度要求，能够在不改变输入单元集合与顺序的前提下，
系统地评估和润色VNG提示词，以确保叙事结构正确、情景强度适中且符合测量目标。

## Background
### Visual Narrative Grammar (VNG)**：
VNG 是一种分析和构建视觉叙事的框架，描述了人类能够理解的，基于图像序列的视觉叙事。VNG 将视觉叙事分解为四种基本单元：
- **Establisher (E)**：引入角色与场景，建立语境与中性基调。
- **Initial (I)**：启动冲突或动作，呈现早期张力。
- **Prolongation (Pr)**：延缓至高潮的过渡与铺垫，通过细节与节奏增强紧张感。
- **Peak (P)**：高潮或转折点，呈现核心认知或决策瞬间。
上述的E，I，Pr，P单元可以组合成不同的叙事结构（如E-I-Pr-P、E-I-P、E-P等）以适应不同的叙事需求和复杂度。
> 在本任务中，可用配置：**E-I-Pr-P**、**E-I-P** 或 **E-P**（由素材复杂度决定）。你也必须遵守输入的单元类型与顺序，**不得新增、删除或重排**。

### 人格情景判断测验（SJT）：
人格情景判断测验（人格SJT）是一种心理测量工具，通过呈现能够激活目标人格特质相关的情境，通过评估个体在这些情境中的行为反应推断特质水平。
人格SJT 通常包含一个情景描述（situation）和多个反应选项（options），不同反应项揭示了不同水平的目标人格特质。
人格SJT通常需要避免情景强度（即情景对某一反应项的暗示）过高。如测量社会规范服从构念，红灯下是否过马路作为情景，其强烈暗示了“等待绿灯”的反应项，具有较高的情景强度，可能导致测量结果由情景决定而非被试特质。

## GOALS
你需要严格、系统地评估和优化以 **Visual Narrative Grammar (VNG)** 构建的图像人格情景判断测验（sjt）的分镜生图提示词，以确保：

### 叙事结构正确
- 每个叙事单元（E, I, Pr, P）在**不改变分镜顺序与数量**的前提下完成其预期功能，且不提前泄露后续情节。 
- 叙事逻辑连贯，符合VNG结构要求，各单元有明确的叙事功能区隔。
- 多单元组合后形成清晰的多场景视觉叙事，而不在早期单元提前展示高潮或结局。

### 情景强度正确
- 准确识别并修改每个VNG叙事单元冗余或冲突的描述性元素（如夸张的：面部表情、手势、道具、场景细节），以避免情景强度过高从而暗示某一反应项，进而导致测量结果由情景决定而非被试特质。
- 确保每个vng叙事单元所描述的情节不与输入SJT的options中所描述的反应项产生冲突或混淆。

### 生图提示词正确
- 主角（ActiveCharacterName）不用增加视觉描述，在生图中已有参考图像。
- 主角（ActiveCharacterName）之外的其他角色、物体、场景等视觉描述需要在各单元中完整、一致，不可指代，以实现多个单元的图片的一致性。

## Input
- **Input**  
  - SituationItem(dict)： 情景判断测验题目，包含情景判断测验的情景题干（键为Situationt）与反应项（键为options）
  - Trait(str)：目标人格特质（如“Neuroticism: Self-consciousness”）
  - VNG(dict)：基于SituationItem制作的，未经过润色的 VNG 的原始生图提示词。键属于['E', 'I', 'Pr', 'P']的子集，值为对应单元的生图提示词
  - ActivateCharacterName(str)：主角姓名，将出现在情景判断测验题目中

## Workflow
1) **分镜理解**  
   - 解析情景判断测验的SituationItem；
   - 基于输入的vng单元类型与顺序，理解每个单元的预期叙事功能。
2) **视觉叙事结构检查**
   - 逐一检查输入VNG各单元，初步标记与当前单元叙事功能不符的内容（如E中出现叙事高潮）
   - 跨各VNG单元，标记提前泄露或延迟呈现的VNG单元内容（如E/I中出现本应P的叙事高潮，或I中出现本应E的背景交代）
   注：需要检查的内容包括但不限于：角色表情、动作，场景视角、氛围、光线，物体位置、状态等
3) **视觉叙事内容重写/删除**
   - 在不改变输入单元类型与顺序的前提下，对视觉叙事检查中标记的问题进行修正
   - 你有完全的权限在各VNG单元间移动不符合VNG原则的内容、或各VNG单元内部删除或增加不符合VNG原则的内容
   - 确保整体视觉叙事连贯、符合VNG结构要求，使得各单元一起组成人类可视觉理解的图像序列描述
4) **情景强度与内容效度检查**  
   - 逐一检查各VNG单元，标记情景强度过高的内容（如夸张的面部表情、手势、道具、场景细节等）
   - 逐一检查各VNG单元，标记与输入SJT的options中各反应项产生冲突或强烈暗示任一反应项的内容
   - 逐一检查各VNG单元组合而成的整体视觉叙事是否有能够有效激活目标人格特质（Trait），从而实现测量目标
5) **情景强度与内容效度修正**
   - 在不改变输入单元类型与顺序的前提下，对情景强度与内容效度检查中标记的问题进行修正
   - 你有完全的权限改写各VNG单元中情景强度过高的内容、或与SJT反应项冲突的内容
   - 确保整体视觉叙事连贯、情景强度适中且能够依托视觉的形式有效激活特质
6) **生图提示词优化**
   - 确保主角（ActiveCharacterName）不用增加视觉描述，在下游工作中生图中已有参考图像
   - 确保主角（ActiveCharacterName）之外的其他角色、物体、场景等视觉描述在各单元中完整、一致，不可指代，以实现多个单元的图片场景与角色的一致性。
   - 若输入的VNG单元中存在模糊，难以视觉生成的描述（如抽象的心理活动），你需要进行适当的具体化和细化，以便于生成清晰的视觉图像。
   - 确保生图提示词符合安全与合规要求（不得涉及暴力、色情、歧视等），相关内容需通过在同等的特质激活效用下进行合理的转写。（如测量神经质的SJT情景：你与一对正激情接吻的情侣在一电梯内部，将激情接吻所制造的窘境转写为紧紧拥抱）
   - 确保生图提示词处于生图模型的可理解范围

## Constraints
- **输入单元类型与顺序必须原样保留**；不得新增、删除或重排。  
- 除了主角（ActivateCharacterName），其余角色在**每个单元**的视觉特征都要完整独立书写，并保持一致可识别：  
  - 发色、性别、种族为必填；服饰、道具、姿态视情况补充。
  - 除非情景明确了某一种族，否则其他角色的种族统一为东亚人（East Asian）
  - ❌ 不允许“他的朋友/一位同事”等模糊指代；  
  - ✅ 使用如“黑发、浅棕肤色的女性同事，商务休闲装”
- 所有描述须符合安全与合规要求（不得涉及暴力、色情、歧视等）。
- 不得增加对话气泡，旁白注释此二类视觉元素。
- 输出的结果必须是有效的JSON格式，最外层键为 "VNG"，值为一个对象，包含润色后的VNG单元，键为单元类型（'E', 'I', 'Pr', 'P'），值为对应的润色后生图提示词。
- 输出的生图提示词必须是英文。

## Output Format
```json
{
  "VNG": {
    "E": "Refined Establisher description",
    "I": "Refined Initial description",
    "Pr": "Refined Prolongation description",
    "P": "Refined Peak description"
  }
}
```
"""


ActiveCharacterName = "Ye"

situ_1 = """{'situation': 'Ye坐在拥挤电影院的中间。电影开始后不久，Ye意识到Ye搞错了电影院，进入了错误的电影。',
 'options': {'A': '我不换电影厅，因为电影期间让半排人站起来对我来说不舒服。',
  'B': '我在整部电影期间都坐着，因为如果其他人看到我在表演期间离开我会感到尴尬。',
  'C': '我起身去另一个电影厅。',
  'D': '我看电影的开头，然后决定是否换电影厅。'}
 }"""

trait_1 = "Neuroticism: Self-consciousness"

in_gp_1 = """
{
"E": "Create a 1024x1024 realistic image of Ye sitting in a crowded movie theater. Ye already looks confused and uneasy, glancing repeatedly at the big screen. Around Ye, other people are watching the movie and reacting with surprise. The screen shows a completely different film genre from what Ye expected, with bright colors and loud sound effects. Ye’s hands clutch the armrests tightly, and his face shows a mix of shock and embarrassment, as if realizing something went wrong.",
"I": "Create a 1024x1024 realistic image of Ye suddenly leans forward, realizing this is the wrong movie. Ye’s eyes are wide and anxious, mouth half-open as he whispers to himself. Several people nearby notice Ye’s reaction and glance toward him. The lighting is harsh, casting Ye’s face in strong contrast. The tension builds as Ye hesitates to stand up, visibly sweating under the dim flicker of the projector.",
"P": "Create a 1024x1024 realistic image of Ye jumping up from his seat in panic, accidentally bumping into another audience member. Everyone turns to look at him, their faces illuminated by the flickering screen. Ye blushes deeply, clearly mortified, as he apologizes nervously. The camera angle is low and dynamic, emphasizing Ye’s embarrassment and isolation in the middle of the crowded theater."
}
"""

output_1 = """
{
  "VNG": {
    "E": "Create a 1024x1024 realistic image of Ye seated in the middle of a fully occupied movie theater before the movie begins. Medium-wide shot from row level, showing tightly packed seats extending across the frame with no empty spots. The large screen at the front is completely black, reflecting faint shapes of the audience but showing no content yet. Overhead ceiling lights remain dim but warm, casting soft illumination across faces and seats. Ye sits in the middle row between two consistent neighbors: to Ye’s left, a black-haired, East Asian woman in a denim jacket holding a large red popcorn bucket; to Ye’s right, an East Asian man with brown hair wearing a navy hoodie resting his hands on the shared armrest. Directly in front sits a medium-brown-skinned older man with short gray hair wearing a dark cap. The air feels close and slightly stuffy, with narrow armrests and limited personal space conveying the crowded atmosphere.",
    "I": "Create a 1024x1024 realistic image of the same theater moments after the film starts. The environment has become darker, lit mainly by the flickering blue-white light from the movie screen, which now shows indistinct moving shapes and color. The audience’s faces are illuminated unevenly by the changing light, most of them focused forward in silence. Ye sits still, slightly leaning forward with eyebrows raised and lips pressed together in mild uncertainty, eyes reflecting the light from the screen. The focus is tighter around Ye, emphasizing the contrast between Ye’s subtle confusion and the absorbed stillness of the surrounding viewers. The overall tone is subdued and introspective, with deep shadows emphasizing the crowded but quiet setting.",
    "P": "Create a 1024x1024 realistic close shot from a slight high angle on Ye’s seat position. The scene is still dark except for the dim blue light from the movie screen, where a calm mountain landscape is visible. Ye sits with shoulders slightly hunched forward, one elbow resting on the armrest and the other hand holding a printed movie ticket near the lap. Ye’s chin rests lightly on the free hand, eyebrows furrowed and eyes fixed on the ticket in a puzzled expression, realizing it shows a different movie title symbolized by a bold racing car logo. The surrounding audience remains still, unaware, with blurred outlines of heads in front and faint aisle step-lights along the floor emphasizing the enclosed, introspective mood."
  }
}

"""
situ_2 = """{'situation': "You get to know a colleague who is new to the company and the region. The colleague asks you if you would like to meet him/her in the evening, as he/she does not yet feel at home and hardly knows any people. However, you don't like the colleague and you don't like his dogged nature. How do you behave?",
 'options': {'A': 'I agree to meet with him. Maybe he/she is more relaxed in private.',
  'B': "I'll invite him/her to a meeting with my friends.",
  'C': 'I tell him that I am very busy the next few weeks and therefore have no time for a private meeting.',
  'D': 'I tell him that I am not interested in meeting him/her privately.'}
  }"""
  
trait_2 = "Agreeableness: Compliance"

in_gp_2 = """
{
  "E": "Create a cinematic close-up of Ye standing in the office corridor with a frown, already looking annoyed as a new colleague approaches nervously. The colleague holds a cup of coffee and looks at Ye with pleading eyes, clearly lonely and desperate for company. The atmosphere is tense, with cold bluish office light and an awkward silence between them.",
  "I": "Create a realistic image of Ye sitting in a café with the new colleague in the evening. Both look uncomfortable. The new colleague’s eyes are watery and Ye’s expression shows visible pity. Ye leans forward slightly as if forced to listen, while the colleague talks eagerly, gesturing with both hands. The background shows a few customers turning to look, amplifying the awkward mood.",
  "P": "Create an image where Ye looks angry and dismissive while the new colleague stands stubbornly nearby. Ye’s arms are crossed tightly, eyebrows furrowed deeply, lips pressed into a thin line. The colleague’s jaw is set, and the posture is rigid. The lighting is harsh and dramatic, creating strong contrast to emphasize emotional conflict."
}
"""
output_2 = """
{
  "VNG": {
    "E": "Create a 1024x1024 realistic image of an open-plan modern office in the late afternoon. Ye stands near a shared desk area, reviewing some documents. In the background, a newly arrived colleague—an East Asian man with short dark blond hair wearing a light gray shirt—sits at his workstation. A few other employees chat in small groups near the coffee machine, while the new colleague remains seated alone, glancing occasionally toward them with a faint, uncertain smile. The lighting is bright but soft from overhead panels, creating a neutral, everyday atmosphere. The composition emphasizes social distance within a friendly workspace.",
    "I": "Create a 1024x1024 realistic image of the same office setting near closing time. The new colleague—an East Asian man with short dark blond hair wearing a light gray shirt—sits approaches Ye’s desk, holding a jacket over one arm and a messenger bag strap in the other hand. The colleague’s posture is slightly hesitant—shoulders slightly forward, head tilted as if politely asking a question. Ye stands facing the colleague, body turned halfway toward the exit, maintaining a neutral polite smile with eyebrows gently raised. The lighting from the large windows grows warmer as evening approaches, suggesting transition from work to personal time. The surrounding desks are emptying, and the mood is quiet and tentative, focused on the moment of invitation.",
    "P": "Create a 1024x1024 realistic image of Ye and the new colleague—an East Asian man with short dark blond hair wearing a light gray shirt—standing near the office entrance as the conversation concludes. Ye holds a phone loosely in one hand and the other hand in a pocket, chin slightly lowered with fingers resting lightly against the jawline in a thoughtful pose. Ye’s eyebrows are faintly furrowed, lips gently pressed together, eyes glancing downward as if considering the colleague’s request. The colleague maintains a small expectant smile, standing with relaxed arms holding the jacket. The warm indoor lighting contrasts with the cooler evening light coming through the glass doors, emphasizing Ye’s quiet hesitation and internal conflict without overt tension."
  }
}
"""

# Render helper for the conditioning frame (the user asks for this structure)
conditioned_frame = """systematically reviews and refines each VNG unit to eliminate premature plot reveals and cross-unit redundancies while preserving the original structure:

Situation:
$passage

Trait:
$trait

ActiveCharacterName: 
$active_character

VNG:
$vng
"""
# =========================
prompt_template = [
    {"role": "system", "content": vng_condition_system},
    {"role": "user", "content": Template(conditioned_frame).substitute(passage=situ_1, trait=trait_1, active_character=ActiveCharacterName, vng=in_gp_1)},
    {"role": "assistant", "content": output_1},
    {"role": "user", "content": Template(conditioned_frame).substitute(passage=situ_2, trait=trait_2, active_character=ActiveCharacterName, vng=in_gp_2)},
    {"role": "assistant", "content": output_2},
    {"role": "user", "content": "good, keep it up!"},
    {"role": "assistant", "content": "Great, I will follow our previous conversation."},
    {"role": "user", "content": conditioned_frame},
]