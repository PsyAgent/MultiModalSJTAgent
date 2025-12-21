from __future__ import annotations

import json
import os
import pickle
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict

import pandas as pd
base_path = os.path.dirname(os.path.abspath(__file__))


@dataclass
class DatasetMetadata:
    description: str
    author: str
    source: str
    url: str
    data_source: str
    data: dict[str, dict[str, Any]] = field(default_factory=dict)


meta_SceneGraph = DatasetMetadata(
    description='A wide range of SceneGraph elements, including attributes, relations, objects, scene_attributes.',
    author='Ziqi Gao et., al.(2024)',
    source='arXiv:2412.08221 [cs.CV]',
    url='https://arxiv.org/abs/2412.08221',
    data_source='https://github.com/RAIVNLab/GenerateAnyScene/tree/main/metadata',
    data={
        'attributes': {
            'description': 'A list of attributes describing objects.',
            'path': os.path.join(base_path, 'any_scene_graph', 'attributes.json'),
        },
        'relations': {
            'description': 'A list of relations between objects.',
            'path': os.path.join(base_path, 'any_scene_graph', 'relations.json'),
        },
        'objects': {
            'description': 'A list of objects in the scene.',
            'path': os.path.join(base_path, 'any_scene_graph', 'objects.json'),
        },
        'scene_attributes': {
            'description': 'A list of attributes describing the scene.',
            'path': os.path.join(base_path, 'any_scene_graph', 'scene_attributes.json'),
        },
    },
)

situation_DIAMONDS = DatasetMetadata(
    description='A scale for evalute situation.',
    author='null',
    source='null',
    url='null',
    data_source='null',
    data={
        'DIAMONDS': {
            'description': '8 dims, 3 items per dim.',
            'path': os.path.join(base_path, 'scale', 'DIAMONDS.json'),
        },
        'DIAMONDS_zh': {
            'description': '8 dims, 3 items per dim. Chinese version.',
            'path': os.path.join(base_path, 'scale', 'DIAMONDS_zh.json'),
        },
    },
)

situation_judgment_test = DatasetMetadata(
    description='Situation judgement tests for personality.',
    author='null',
    source='null',
    url='null',
    data_source='null',
    data={
        'SJTs': {
            'description': 'Situation judgement tests for personality.',
            'path': os.path.join(base_path, 'scale', 'SJTs.json'),
        },
        'SJTs_zh': {
            'description': 'Situation judgement tests for personality. Chinese version.',
            'path': os.path.join(base_path, 'scale', 'SJTs_zh.json'),
        },
    },
)

G = DatasetMetadata(
    description="SJS's Graph",
    author='null',
    source='null',
    url='null',
    data_source='null',
    data={
        'Gs': {
            'description': 'G after VNG.',
            'path': os.path.join(base_path, 'example_graph', 'Gs.pkl'),
        },
        'G': {
            'description': 'original G.',
            'path': os.path.join(base_path, 'example_graph', 'G.pkl'),
        },
        'clean_G': {
            'description': 'G after trait-relavant cues extraction.',
            'path': os.path.join(base_path, 'example_graph', 'clean_G.pkl'),
        },
    },
)

image_schema = DatasetMetadata(
    description='Image schema for Image Generation.',
    author='null',
    source='null',
    url='null',
    data_source='null',
    data={
        'image_schema': {
            'description': 'Image schema with on content.',
            'path': os.path.join(base_path, 'image_schema', 'image_schema.json'),
        },
        'emotion_experssion': {
            'description': 'Body and facial expression under experssion.',
            'path': os.path.join(base_path, 'image_schema', 'emotion_expression.json'),
        },
        'scene_schema': {
            'description': 'Scene schema with content.',
            'path': os.path.join(base_path, 'image_schema', 'scene_expression.json'),
        },
        'object_schema': {
            'description': 'Object schema with content.',
            'path': os.path.join(base_path, 'image_schema', 'object_expression.json'),
        },
    },
)
class DataManager():
    def __init__(self):
        self.metadata = json.loads(
            json.dumps(
                {
                    'any_scene_graph': meta_SceneGraph.__dict__,
                    'situation_DIAMONDS': situation_DIAMONDS.__dict__,
                    'situation_judgment_test': situation_judgment_test.__dict__,
                    'situation_judgement_test_G': G.__dict__,
                    'image_schema': image_schema.__dict__,
                }, default=lambda o: o.__dict__,
            ),
        )

    def _repr_html_(self):
        """
        Returns a string representation of the metadata in HTML format.
        """
        flattened_metadata = {
            key: {
                'data_head': key,
                'data_name': value.get('data', {}).keys(),
                'description': value.get('description', ''),
                'author': value.get('author', ''),
                'source': value.get('source', ''),
            }

            for key, value in self.metadata.items()
        }
        df = pd.DataFrame.from_dict(flattened_metadata, orient='index')
        return df.to_html(index=False, header=True, escape=True)

    def read(
        self, data_head, data_name, extract_stiu=False,replace_you = False,
    ):

        if extract_stiu and data_head != 'situation_judgment_test':
            raise ValueError(
                f'Data head {data_head} does not support extraction.',
            )

        if data_head not in self.metadata:
            raise ValueError(f'Data head {data_name} not found in metadata.')

        data_path = self.metadata[data_head]['data'][data_name]['path']
        if data_path.endswith('.json'):
            with open(data_path, encoding='utf-8') as f:
                data = json.load(f)
        elif data_path.endswith('.pkl'):
            with open(data_path, 'rb') as f:
                data = pickle.load(f)
        else:
            raise ValueError(f'Unsupported file format: {data_path}')

        if extract_stiu or replace_you:
            situs = {
            triat: {
                i: '.'.join(
                data[triat][i]['situ']
                .replace('your', "Ye's")
                .replace('you', 'Ye')
                .replace('are', 'is')
                .replace('You', 'Ye')
                .replace('Your', "Ye's")
                .split('.')[:-1] if extract_stiu else data[triat][i]['situ'],
                ) if replace_you else '.'.join(data[triat][i]['situ'].split('.')[:-1])
                for i in data[triat]
            }
            for triat in data
            }
            return situs


        return data
