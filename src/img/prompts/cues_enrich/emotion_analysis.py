from __future__ import annotations

from string import Template

condition_system = """
# Emotion analyst

Analysis emotion that best ACTIVATE [activate character] the specified Big Five personality trait from the given situation.
Response in json.

## Emotions
'happiness',
'sadness',
'anger',
'fear',
'disgust',
'surprise',
'contempt',
'neutral'

## BACKGROUND
- Trait Activation Theory and Big Five Personality
    Trait Activation Theory (TAT) suggests that whether a personality trait is expressed depends on whether the situation provides cues that activate the trait.
    Below is a brief overview of how each of the Big Five traits is typically activated.
        - O(Openness):Curious, imaginative, open to new experiences; Activating Cues: Novel, creative, or complex events and so on.
        - C(Conscientiousnesss): Organized, responsible, and goal-oriented; Activating Cues: Situations requiring planning, rule-following, or task completion and so on.
        - E(Extraversion): Sociable, talkative, and energetic; Activating Cues: Social settings or contexts that involve interaction or leadership and so on.
        - A(Agreeableness): Compassionate, cooperative, and empathetic; Activating Cues: Interpersonal conflict, opportunities for empathy or helping and so on.
        - N(Neuroticism): Emotionally unstable, anxious, reactive to stress; Activating Cues: Threatening, evaluative, or uncertain situations and so on.

## Workflows

1. Grasp the overall situation.
2. Analyse which kind of emotion of the [analyze character] in situation will best activate target trait of [activate character] the situation.
3. select the emotion that best satisfy the requirement from Emotions.
4. Output the emotion in json format.

## Constraints
the output emotion MUST be one of the following in EMOTIONS:
'happiness', 'sadness', 'anger', 'fear', 'disgust', 'surprise', 'contempt', 'neutral'

## OUTPUT
A JSON dict with the following structure, the only keys are "emotion", and only has two value: "character" and "emotion":
{
    "character": "...",
    "emotion": "...",
}

## EXAMPLE
-Input
Target trait: N
Situation: Ye're on the tram with a friend. At one stop, an attractive woman gets on. As she passes Ye, Ye's friend whistles after her.\xa0\xa0The woman turns irritated and looks at Ye.
Activate character: Ye
Analyze character: friend
-Output
{
    "character": "friend",
    "emotion": "contempt"
}

### note
Ye's friend should make Ye feel anxious to activate Neuroticism,
so the his emotion should be "contempt".
"""

conditioned_frame = """Select the emotion of [analyze character] that best activate the target trait of [activate character] from the given situation and target trait:
Target trait:
$trait

Situation:
$passage

Activate character:
$activate_character

Analyze character:
$analyze_character
"""

few_shot_narrative_1 = 'Ye is sitting in the middle of a crowded movie theater. Shortly after the film has started, Ye realize that Ye made a mistake in the cinema and ended up in the wrong film.'
few_shot_trait_1= 'N'
few_shot_activate_character_1 = 'Ye'
few_shot_analyze_character_1 = 'Ye'

few_shot_output_1 = """
{
    "character": "Ye",
    "emotion": "fear"
}
"""

few_shot_narrative_2 = "Ye're on the tram with a friend. At one stop, an attractive woman gets on. As she passes Ye, Ye's friend whistles after her.\xa0\xa0The woman turns irritated and looks at Ye"
few_shot_trait_2= 'N'
few_shot_activate_character_2 = 'Ye'
few_shot_analyze_character_2 = 'friend'

few_shot_output_2 = """
{
    "character": "friend",
    "emotion": "contempt"
}
"""

prompt_template = [
    {'role': 'system', 'content': condition_system},

    {
        'role': 'user', 'content': Template(conditioned_frame).substitute(
        passage=few_shot_narrative_1,
        trait=few_shot_trait_1,
        activate_character=few_shot_activate_character_1,
        analyze_character=few_shot_analyze_character_1,
        ),
    },
    {'role': 'assistant', 'content': few_shot_output_1},

    {
        'role': 'user', 'content': Template(conditioned_frame).substitute(
        passage=few_shot_narrative_2,
        trait=few_shot_trait_2,
        activate_character=few_shot_activate_character_2,
        analyze_character=few_shot_analyze_character_2,
        ),
    },
    {'role': 'assistant', 'content': few_shot_output_2},
    {'role': 'user', 'content': 'good, keep it up!'},
    {'role': 'assistant', 'content': 'ok, I will follow our previous conversation.'},
    {'role': 'user', 'content': conditioned_frame},
]