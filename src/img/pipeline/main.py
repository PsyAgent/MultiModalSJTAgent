from __future__ import annotations

from itertools import chain
import networkx as nx
import pandas as pd
from tqdm.auto import tqdm
from lmitf import TemplateLLM
from lmitf.template_lvm import StoryBoard
import os
import json
import pickle as pkl
from ..utils.graph_utils import (
    build_G,
    dic_G,
    extract_knowledge,
    find_node_by_value,
    get_max_attribute,
)
from .cues_enrich import (
    enrich_characters,
    enrich_objects,
    enrich_scenes,
)
from .utils import (
    _replace_pronouns,
    find_key_in_result,
    identify_cue_type,
)

from ..annotator import Annotator
import os.path as op
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

class PicSJTAgent:
    """A processor for generating and analyzing situation graphs."""
    # ✅
    def __init__(
        self, 
        situ, 
        trait, 
        ref_viz: str | Image.Image = "A portrait photo of an yong man",
        ref_name = 'Ye',
        model='gpt-5', 
        debug=False,
        prompt_dir = op.join(op.dirname(__file__), '..', 'prompts'),
        output_dir = 'output',
        output_fname = 'output',
        ):
        """Initialize the processor with a specific model.
        
        Parameters:
        ----------
        situ: str
            The situation description.
        trait: str
            The target trait for analysis.
        model: str, optional
            The language model to use (default is 'gpt-5').
        ref_name: str, optional
            The reference character name (default is 'Ye').
        ref_viz: str or PIL.Image.Image, optional
            The reference visualization, either as a text description or an image (default is a portrait description).
        debug: bool, optional
            If True, runs in debug mode with simplified outputs (default is False).
        """
        assert isinstance(ref_viz, (str, Image.Image)), "ref_viz should be a string or PIL.Image.Image"
        self.llms = {
            'sg': TemplateLLM(op.join(prompt_dir, 'graph_utils', 'sg_generation.py')),
            'cls_node': TemplateLLM(op.join(prompt_dir, 'graph_utils', 'classfy_node.py')),
            'G2str': TemplateLLM(op.join(prompt_dir, 'graph_utils', 'graph2prompt.py')),
            
            'cue_ext':  TemplateLLM(op.join(prompt_dir, 'cues_find', 'cues_extraction.py')),
            'vng': TemplateLLM(op.join(prompt_dir, 'vng', 'vng_from_graph.py')),
            
            'vng_polisher': TemplateLLM(op.join(prompt_dir, 'vng', 'vng_polisher.py')),
        }
        self.cue_types = ['att|obj', 'obj-obj', 'att|obj-obj', 'obj-att|obj', 'att|obj-att|obj']
        self.debug = debug
        self.ref_name = ref_name
        self.situ = _replace_pronouns(situ['situation'], ref_name)
        self.situ_all = {'situation': self.situ, 'options': situ.get('options', [])}
        self.original_situ = situ
        self.trait = trait
        self.ref_viz = ref_viz
        self.model = model
        self.output_dir = op.abspath(output_dir)
        self.output_fname = output_fname

        for _, llm in self.llms.items():
            llm.model = model
    # ✅
    def situ_graph(self):
        """Generate a situation graph based on the given situation."""
        if self.debug:
            self.G = 'nx.Graph'
            return 'nx.Graph'

        res = self.llms['sg'].call(passage = self.situ, model = self.model)
        res_sg = find_key_in_result(res, 'SceneGraph')['SceneGraph']
        G = build_G(res_sg)

        self.G:nx.Graph = G

    # ✅
    def Gs_from_situ(self):
        """Design visual narrative graphs based on the situation and situation graph."""
        if self.debug:
            self.Gs = 'dict[str, nx.Graph]'
            return 'dict[str, nx.Graph]'
        str_G = dic_G(self.G)
        res = self.llms['vng'].call(passage = self.situ_all, graph=str_G, model=self.model)
        res_vng = find_key_in_result(res, 'VNG')['VNG']
        res_Gs = {
            vng: build_G(content) for vng, content in res_vng.items()
        }

        self.Gs:dict[str, nx.Graph] = res_Gs

    # ✅
    def extract_cues_from_Gs(self):
        """对每个VNG进行它的cue的提取,返回一个字典, key为VNG的id, value为提取的cues
        这里的cues是"""
        if self.debug:
            self.cues = 'dict[str, list[dict[str, list[str]]]]'
            return 'dict[str, list[dict[str, list[str]]]]'

        Gs_klg = {vng_idx: self._get_knowledge(G) for vng_idx, G in self.Gs.items()}
        res = self.llms['cue_ext'].call(
            passage = self.situ, trait=self.trait, graphs = Gs_klg, model=self.model
        )
        cues = find_key_in_result(res, 'cues')['cues']
        self.cues:dict[str:list[dict[str, list[str]]]] = cues

    # ✅
    def enrich_Gs_by_cues(self):
        if self.debug:
            self.enriched_Gs = 'dict[str, nx.Graph]'
            return 'dict[str, nx.Graph] -> each VNG_G is enriched by its cues'
        enriched_Gs_cues = {}
        for vng_idx, cues in self.cues.items():
            if cues == []:
                continue
            else:
                enriched_Gs_cues[vng_idx] = self._enrich_G_cues(
                situ = self.situ, trait=self.trait, cues=cues, ref_name=self.ref_name,
                )

        self.enriched_Gs_cues:dict[str, dict] = enriched_Gs_cues
        self.enriched_Gs:dict[str, nx.Graph] = self._add_cues_to_Gs(
            enriched_Gs_cues=enriched_Gs_cues,
            Gs=self.Gs,
            G=self.G,
        )

    # ✅
    def intergrate_enriched_Gs(self) -> dict[str, nx.Graph]:
        if self.debug:
            self.intergerated_Gs = 'dict[str, nx.Graph]'
            return 'dict[str, nx.Graph]'

        intergerated_Gs = {}
        for vng_idx, G in self.Gs.items():
            if vng_idx not in self.enriched_Gs:
                intergerated_Gs[vng_idx] = G
            else:
                intergerated_Gs[vng_idx] = self.enriched_Gs[vng_idx]

        self.intergerated_Gs:dict[str, nx.Graph] = intergerated_Gs
    
    # ✅
    def Gs2prompt(
        self,
        Gs:dict[str, nx.Graph] = None,
        size = '1024*1024',
        style = 'realistic',
    ):
        if self.debug:
            self.Gs_prompt = 'dict[str, str]'
            return 'dict[str, str]'
        """Convert the graphs to string format."""
        Gs_str = {}
        for vng_idx, G in Gs.items():
            res = self.llms['G2str'].call(passage = dic_G(G), size=size, style=style, model=self.model)
            res_str = find_key_in_result(res, 'prompt')['prompt']
            Gs_str[vng_idx] = res_str

        self.Gs_prompt: dict[str, str] = Gs_str
    
    # ✅
    def prompt_polish(self):
        if self.debug:
            self.Gs_prompt_polished = 'dict[str, str]'
            return 'dict[str, str]'
        """Polish the prompts for better image generation."""
        res = self.llms['vng_polisher'].call(
            passage=self.situ_all,
            trait=self.trait,
            vng = self.Gs_prompt,
            active_character=self.ref_name,
            model=self.model,
            )
        res_str = find_key_in_result(res, 'VNG')['VNG']

        self.Gs_prompt_polished:dict[str, str] = res_str
    
    # ✅
    def story_gen(
        self,
        verbose:bool=True,
        ):
        if self.debug:
            self.storyboards = 'dict[str, PIL.Image.Image]'
            return 'dict[str, PIL.Image.Image]'
        """Generate storyboards based on the polished prompts."""
        ref_viz = self.ref_viz
        self.sb = StoryBoard(
            cha_name=self.ref_name,
            description=ref_viz if isinstance(ref_viz, str) else None,
            ref_img=ref_viz if isinstance(ref_viz, Image.Image) else None,
        )
        res = self.sb.create(
            list(self.Gs_prompt_polished.values()), 
            model='gpt-image-1',
            verbose=verbose,
            desc='T2I',
            leave=False,
        )
        self.storyboards = res
    
    # ✅
    def annotate(
        self,
        verbose:bool=True,
        run_bubble:bool=True,
        ):
        self.annotator = Annotator(
            ref_name=self.ref_name,
            ref_img=self.ref_viz if isinstance(self.ref_viz, Image.Image) else None,
            situation_item=self.situ_all,
            trait=self.trait,
            image_sequence=self.storyboards[0],
            panels=self.storyboards[1],
            model=self.model,
        )
        self.annotations =  self.annotator.run(verbose=verbose, run_bubble=run_bubble)
        

    def run(
        self, 
        size = '1024x1024',
        style = 'realistic', 
        verbose=True,
        verbose_leave=True,
        outdir: str = 'outputs',
        out_basename: str = 'img',
        save: bool=True,
        save_overwrite: bool=True,
        run_bubble:bool=True,
        return_details:bool=False,
        ):
        """Fit the model to the situation and trait.
        如果run_bubble为True, 则会调用本地计算资源进行对话气泡的生成（高并行的异步处理中容易崩溃）, 
        否则只返回annotate的结果
        
        Parameters:
        ----------
        size: str
            Image size (default '1024x1024')
        style: str
            Image style (default 'realistic')
        verbose: bool
            Show progress (default True)
        verbose_leave: bool
            Leave progress bar after completion (default True)
        save: bool
            Whether to save results (default True)
        save_overwrite: bool
            If False, skip saving if output already exists (default True)
        run_bubble: bool
            Whether to run bubble generation (default True)
        """
        steps = [
            ('Generating situation graph', self.situ_graph),
            ('Creating visual narrative graphs', self.Gs_from_situ),
            ('Extracting cues from graphs', self.extract_cues_from_Gs),
            ('Enriching graphs with cues', self.enrich_Gs_by_cues),
            ('Integrating enriched graphs', self.intergrate_enriched_Gs),
            ('Converting graphs to prompt', lambda: self.Gs2prompt(self.intergerated_Gs, size, style)),
            ('Polishing the prompt', self.prompt_polish),
            ('Generating Images', lambda: self.story_gen(verbose=verbose)),
            ('Annotating Images', lambda: self.annotate(verbose=verbose, run_bubble=run_bubble)),
        ]

        pbar = tqdm(steps, disable=not verbose, leave=verbose_leave)
        for desc, step_func in pbar:
            pbar.set_postfix_str(f'{desc}')
            step_func()
        if out_basename is not None:
            self.output_fname = out_basename
        if save:
            self.save(overwrite=save_overwrite, output_dir=outdir)
        if return_details:
            return {
                'G': self.G,
                'Gs': self.Gs,
                'cues': self.cues,
                'enriched_cues': self.enriched_Gs_cues,
                'enriched_Gs': self.enriched_Gs,
                'intergrated_Gs': self.intergerated_Gs,
                'Gs_prompt': self.Gs_prompt,
                'Gs_prompt_polished': self.Gs_prompt_polished,
                'storyboards': self.storyboards,
                'annotated_storyboards': self.annotations,
            }
        else:
            self.annotations['bubbled_sequence'].save(op.join(outdir, f"{self.output_fname}_situation_seq.png"))
            return {
                'situation': op.join(outdir, f"{self.output_fname}_situation_seq.png"),
                'options': self.original_situ.get('options', []),
            }

    def save(
        self,
        output_dir: str = None,
        fname: str = None,
        overwrite: bool = True,
        )-> None:
        """Save all.
        
        Parameters:
        ----------
        output_dir: str, optional
            Output directory path
        fname: str, optional
            Output filename
        overwrite: bool, optional
            If False, skip saving if _details.pkl already exists (default is True)
        """
        if not hasattr(self, 'storyboards') or not hasattr(self, 'annotations'):
            raise ValueError("No storyboards or annotations to save. Please run the pipeline first.")
        output_dir = op.abspath(output_dir) if output_dir is not None else self.output_dir
        fname = self.output_fname if fname is None else fname
        os.makedirs(output_dir, exist_ok=True)

        details_path = op.join(output_dir, f"{fname}_details.pkl")
        if not overwrite and op.exists(details_path):
            return
        

        if hasattr(self, 'annotations') and 'bubbled_sequence' in self.annotations:
            final_output = {}
            dir_imgs = op.join(output_dir, f'{fname}_imgs')
            os.makedirs(dir_imgs, exist_ok=True)
            pth_sequence = op.join(dir_imgs, 'situation_seq.png')
            self.annotations['bubbled_sequence'].save(pth_sequence)
            final_output['situation'] = pth_sequence
            final_output['options'] = self.original_situ.get('options', [])
            with open(op.join(output_dir, f"{fname}.json"), 'w') as f:
                json.dump(final_output, f, indent=4, ensure_ascii=False)
            for idx, panel in enumerate(self.annotations['bubbled_panels']):
                path_panel = op.join(dir_imgs, f'panel_{idx}.png')
                panel.save(path_panel)
            
        output_details = {
            'G': self.G,
            'Gs': self.Gs,
            'cues': self.cues,
            'enriched_cues': self.enriched_Gs_cues,
            'enriched_Gs': self.enriched_Gs,
            'intergrated_Gs': self.intergerated_Gs,
            'Gs_prompt': self.Gs_prompt,
            'Gs_prompt_polished': self.Gs_prompt_polished,
            'storyboards': self.storyboards,
            'annotated_storyboards': self.annotations,
        }
        
        with open(op.join(output_dir, f"{fname}_details.pkl"), 'wb') as f:
            pkl.dump(output_details, f)
            
    def _enrich_G_cues(
        self,
        cues: list[dict[str, list[str]]],
        situ: str,
        trait: str,
        ref_name: str,
    ) -> dict[str, list[dict[str, list[str]]]]:
        """Enrich cues based on the situation graph and trait."""
        node_types = self._cls_cues_nodes(situ, cues)
        all_characters = [node_type.get('character', []) for node_type in node_types]
        all_scenes = [node_type.get('scene', []) for node_type in node_types]
        all_objects = [node_type.get('object', []) for node_type in node_types]

        uniuqe_characters = list(set(chain.from_iterable(all_characters)))
        uniuqe_scenes = list(set(chain.from_iterable(all_scenes)))
        uniuqe_objects = list(set(chain.from_iterable(all_objects)))

        if uniuqe_characters != []:
            enriched_characters = enrich_characters(
                situ, trait,
                ana_characters=uniuqe_characters,
                act_character=ref_name,
            )
        else:
            enriched_characters = {}

        if uniuqe_scenes != []:
            enriched_scenes = enrich_scenes(
                situ, trait,
                scenes=uniuqe_scenes,
                act_character=ref_name,
            )
        else:
            enriched_scenes = {}
        if uniuqe_objects != []:
            enriched_objects = enrich_objects(
                situ, trait,
                objects=uniuqe_objects,
                act_character=ref_name,
            )
        else:
            enriched_objects = {}

        enriched_cues = {
            'character': enriched_characters,
            'scene': enriched_scenes,
            'object': enriched_objects,
        }
        return enriched_cues

    def _add_cues_to_Gs(
        self,
        enriched_Gs_cues:dict[str, dict],
        Gs:dict[str, nx.Graph],
        G:nx.Graph,
    ) -> dict[str, nx.Graph]:
        enriched_Gs = {}
        for idx, G in Gs.items():
            if idx not in enriched_Gs_cues:
                continue

            new_G = G.copy()
            cues = enriched_Gs_cues[idx]

            # Define mapping for different cue types
            cue_configs = {
                'character': {'value_suffix': '_body', 'facial_key': 'facial'},
                'scene': {'value_suffix': '_scene'},
                'object': {'value_suffix': '_object'},
            }

            for cue_type, items in cues.items():
                if not items or cue_type not in cue_configs:
                    continue

                config = cue_configs[cue_type]

                for item_name, item_data in items.items():
                    node = find_node_by_value(G, item_name, 'object_node')
                    if not node:
                        continue

                    obj_num = node.split('_')[1]
                    max_attr_idx = get_max_attribute(G, node)

                    # Handle character's body and facial attributes
                    if cue_type == 'character':
                        # Add body attribute
                        body_attr = f'attribute|{obj_num}|{max_attr_idx+1}'
                        new_G.add_node(body_attr, type='attribute_node', value='_body', annot=item_data['body'])
                        new_G.add_edge(body_attr, node, type='attribute_edge')

                        # Add facial attribute
                        face_attr = f'attribute|{obj_num}|{max_attr_idx+2}'
                        new_G.add_node(face_attr, type='attribute_node', value='_face', annot=item_data['facial'])
                        new_G.add_edge(face_attr, node, type='attribute_edge')
                    else:
                        # Add single attribute for scene or object
                        attr = f'attribute|{obj_num}|{max_attr_idx+1}'
                        new_G.add_node(attr, type='attribute_node', value=config['value_suffix'], annot=item_data)
                        new_G.add_edge(attr, node, type='attribute_edge')

            enriched_Gs[idx] = new_G
        return enriched_Gs

    def _get_knowledge(self, G: nx.Graph) -> dict[str, list[str]]:
        """Extract knowledge patterns from the graph."""
        cues = {
            cue_type: extract_knowledge(G, cue_type=cue_type)
            for cue_type in self.cue_types
        }
        return cues

    def _cls_cue_nodes(self, situ: str, words: list[str]) -> dict[str, list[str]]:
        """Classify nodes based on the situation and words."""
        res = self.llms['cls_node'].call(passage=situ, words=words, model=self.model)
        res_nodes = find_key_in_result(res, 'classification')['classification']
        return res_nodes

    def _cls_cues_nodes(self, situ: str, cues: list[dict[str, list[str]]]) -> list[dict[str, list[str]]]:
        """Classify cue nodes based on the situation and cues."""
        words = [identify_cue_type(cue)['nodes'] for cue in cues]
        clss = [self._cls_cue_nodes(situ, words) for words in words]
        return clss

    def _repr_html_(self):
        pipline = {
            'G': 'self.G' if hasattr(self, 'G') else 'not generated',
            'Gs': 'self.Gs' if hasattr(self, 'Gs') else 'not generated',
            'cues': 'self.cues' if hasattr(self, 'cues') else 'not generated',
            'enriched_cues': 'self.enriched_Gs' if hasattr(self, 'enriched_Gs') else 'not generated',
            'intergrated_Gs': 'self.intergerated_Gs' if hasattr(self, 'intergerated_Gs') else 'not generated',
            'Gs_prompt': 'self.Gs_prompt' if hasattr(self, 'Gs_prompt') else 'not generated',
            'Gs_prompt_polished': 'self.Gs_prompt_polished' if hasattr(self, 'Gs_prompt_polished') else 'not generated',
            'storyboards': 'self.storyboards' if hasattr(self, 'storyboards') else 'not generated',
            'annotated_storyboards': 'self.annotated_storyboards' if hasattr(self, 'annotated_storyboards') else 'not generated',
        }

        df = pd.DataFrame(pipline.items(), columns=['Step', 'Result'])
        df_html = df.to_html(index=False)
        df_html = f"""
            <h3 style="color: #9FE2BF;">Pipeline Results</h3>
            {df_html}
        """
        return df_html
