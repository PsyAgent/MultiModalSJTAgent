import asyncio
from .workflow.main import SJTAgent
from typing import Optional
from tqdm.auto import tqdm


class SJTRunner:
    """
    A class to handle SJT (Situational Judgment Test) item generation workflow.
    
    This class encapsulates the functionality for extracting items from scales,
    preparing trait data, and generating new items using the SJTAgent.
    """
    
    def __init__(
        self, 
        generator: Optional[SJTAgent] = None,
        situation_theme: Optional[str] = None,
        target_population: Optional[str] = None,
        scale: Optional[dict] = None,
        meta: Optional[dict] = None,
        ):
        """
        Initialize the SJTRunner.
        
        Parameters
        ----------
        generator : SJTAgent, optional
            An instance of the SJTAgent class used to generate items.
            If not provided, must be set before calling generation methods.
        """
        assert not (generator is not None and situation_theme is not None), \
            "generator and situation_theme cannot both be provided"
        assert not (generator is None and situation_theme is None), \
            "Either generator or situation_theme must be provided"
            
        if generator is None:
            self.generator = SJTAgent(
                situation_theme=situation_theme,
                target_population=target_population,
                show_progress=False, # will be handled in SJTRunner
            )
        else:
            self.generator = generator
        
        if scale is not None:
            self.scale = scale
        if meta is not None:
            self.meta = meta
        if scale is not None and meta is not None:
            self.self_prep()

    def self_prep(self):
        """
        Prepares internal scale and meta data if not already set.
        """
        self.items = self.get_items(list(self.scale.keys()), self.scale)
        self.confs = self.prep_data(list(self.meta.keys()), self.meta)

    def get_items(self, traits: list, scale: dict) -> dict:
        """
        Extracts item text for specified traits from a scale dictionary.
        Parameters
        ----------
        traits : list
            A list of trait names (strings) for which to retrieve items.
        scale : dict
            A dictionary containing the full scale information, structured with trait
            names as keys. Each trait's value should be a dictionary containing an
            'items' key, which in turn holds a dictionary of item details.
            Example structure: 
            {'trait_name': {'items': {'item_1': {'item': 'text'}}}}
        Returns
        -------
        dict
            A dictionary where keys are the trait names from the input list and
            values are lists of the corresponding item texts.
        """
        to_return = {}
        for trait in traits:
            to_return[trait] = [
                scale[trait]['items'][key]["item"] for key in scale[trait]['items']
            ]
        return to_return

    def prep_data(self, traits: list, metadata: dict) -> dict:
        """
        Prepares the data for each trait by extracting relevant information from the metadata.
        Parameters
        ----------
        traits : list
            A list of trait names (strings) for which to prepare data.
        metadata : dict
            A dictionary containing metadata for each trait, structured with trait
            names as keys. Each trait's value should be a dictionary containing
            keys such as 'domain', 'facet_name', 'low_score', and 'high_score'.
        Returns
        -------
        dict
            A dictionary where keys are the trait names from the input list and
            values are dictionaries containing the prepared data for each trait.
        """
        to_return = {}
        
        for trait in traits:
            trait_desc = metadata[trait]
            to_return[trait] = {
                'trait_name': f"{trait_desc['domain']}-{trait_desc['facet_name']}",
                'description': trait_desc,
                'low_score': trait_desc['low_score'],
                'high_score': trait_desc['high_score'],
            }
        return to_return

    def cook(
        self, 
        traits: list, 
        items: dict | None = None, 
        confs: dict | None = None, 
        n_item: int = 3, 
        model: str = 'gpt-5-mini',
        save_results: Optional[bool] = False,
        results_dir: str | None = None,
        detailed_fname: str = 'results_detailed',
        fname:str = 'results',
        ) -> dict:
        """
        Generates items for each trait using the specified generator.
        Parameters
        ----------
        traits : list
            A list of trait names (strings) for which to generate items.
        items : dict
            A dictionary where keys are trait names and values are lists of item texts.
        confs : dict
            A dictionary where keys are trait names and values are dictionaries containing
            configuration data for each trait.
        n_item : int, optional
            The number of items to generate for each source item (default is 3).
        model : str, optional
            The model to use for generation (default is 'gpt-5-mini').
        Returns
        -------
        dict
            A dictionary where keys are trait names and values are lists of generated items.
        """
        if hasattr(self, 'items') and hasattr(self, 'confs') and items is None and confs is None:
            confs = self.confs
            items = self.items
        else:
            if items is None or confs is None:
                raise ValueError("Either both items and confs must be provided, or neither.")
            
        all_items = {}
        for trait in tqdm(traits, desc="Generating"):
            all_items[trait] = []
            for item in items[trait]:
                res = self.generator.run(
                    trait_name=confs[trait]['trait_name'],
                    trait_description=confs[trait]['description'],
                    low_score=confs[trait]['low_score'],
                    high_score=confs[trait]['high_score'],
                    item=item,
                    n_item=n_item,
                    model=model,
                )
                all_items[trait].append(res)
        
        if save_results:
            self.save_result(
                all_items=all_items,
                results_dir=results_dir,
                detailed_fname=detailed_fname,
                fname=fname,
            )
        return all_items

    async def _cook_async(
        self,
        traits: list,
        items: dict,
        confs: dict,
        n_item: int = 3,
        model: str = 'gpt-5-mini',
        trait_concurrency: Optional[int] = None,
        show_progress: bool = True,
        progress_callback: Optional[callable] = None,
    ):
        """
        Asynchronously generates items by scheduling each trait-item pair concurrently.

        Parameters are the same as ``cook`` with two additions:
        trait_concurrency : int, optional
            Maximum number of trait-item tasks to process at once. Defaults to the
            total number of tasks (``len(traits) * len(items[trait])``), i.e. no throttling.
        show_progress : bool, optional
            Whether to display tqdm progress bars. Defaults to True.
        progress_callback : callable, optional
            A callback function to report progress. Should accept (current, total, details) parameters.
        """
        if self.generator is None:
            raise ValueError("Generator must be set before calling _cook_async method")
            
        if not traits:
            return {}

        trait_counts = {trait: len(items[trait]) for trait in traits}
        total_tasks = sum(trait_counts.values())

        if total_tasks == 0:
            return {trait: [] for trait in traits}

        if trait_concurrency is None:
            concurrency_limit = total_tasks
        else:
            concurrency_limit = max(1, min(trait_concurrency, total_tasks))

        task_semaphore = asyncio.Semaphore(concurrency_limit)
        all_items = {trait: [None] * trait_counts[trait] for trait in traits}
        completed_tasks = 0

        async def process_trait_item(trait_key: str, item_index: int, source_item):
            nonlocal completed_tasks

            async with task_semaphore:
                trait_conf = confs[trait_key]
                try:
                    result = await self.generator._generate_items(
                        trait_name=trait_conf['trait_name'],
                        trait_description=trait_conf['description'],
                        low_score=trait_conf['low_score'],
                        high_score=trait_conf['high_score'],
                        item=source_item,
                        n_item=n_item,
                        model=model,
                    )
                    completed_tasks += 1
                    if progress_callback:
                        progress_callback(
                            completed_tasks,
                            total_tasks,
                            f"已完成 {trait_key} 特质的第 {item_index + 1} 个题目"
                        )
                except Exception as exc:  # pragma: no cover - surface trait context
                    raise RuntimeError(
                        f"Failed to generate items for trait {trait_key} at index {item_index}"
                    ) from exc
            return trait_key, item_index, result

        tasks = [
            asyncio.create_task(process_trait_item(trait, idx, source_item))
            for trait in traits
            for idx, source_item in enumerate(items[trait])
        ]

        pending_items = asyncio.as_completed(tasks)
        if show_progress:
            pending_items = tqdm(pending_items, total=len(tasks), desc="Generating")

        try:
            for fut in pending_items:
                trait_key, item_index, item_result = await fut
                all_items[trait_key][item_index] = item_result
        except Exception:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        return {
            trait: [item for item in results if item is not None]
            for trait, results in all_items.items()
        }

    def cook_async(
        self,
        traits: list,
        items: dict | None = None,
        confs: dict | None = None,
        n_item: int = 3,
        model: str = 'gpt-5-mini',
        trait_concurrency: Optional[int] = None,
        show_progress: bool = True,
        progress_callback: Optional[callable] = None,

        save_results: Optional[bool] = False,
        results_dir: str | None = None,
        detailed_fname: str = 'results_detailed',
        fname:str = 'results',
    ) -> dict:
        """Synchronous helper that executes :func:`_cook_async` in any environment.
        Parameters
        ----------
        traits : list
            A list of trait names (strings) for which to generate items.
        items : dict
            A dictionary where keys are trait names and values are lists of item texts.
        confs : dict
            A dictionary where keys are trait names and values are dictionaries containing
            configuration data for each trait.
        n_item : int, optional
            The number of items to generate for each source item (default is 3).
        model : str, optional
            The model to use for generation (default is 'gpt-5-mini').
        trait_concurrency : int, optional
            Maximum number of trait-item tasks to process at once. Defaults to the
            total number of tasks (``len(traits) * len(items[trait])``), i.e. no throttling.
        show_progress : bool, optional
            Whether to display tqdm progress bars. Defaults to True.
        progress_callback : callable, optional
            A callback function to report progress. Should accept (current, total, details) parameters.
        Returns
        -------
        dict
            A dictionary where keys are trait names and values are lists of generated items.

        """
        if hasattr(self, 'items') and hasattr(self, 'confs') and items is None and confs is None:
            confs = self.confs
            items = self.items
        else:
            if items is None or confs is None:
                raise ValueError("Either both items and confs must be provided, or neither.")
        
        async def _run():
            return await self._cook_async(
                traits=traits,
                items=items,
                confs=confs,
                n_item=n_item,
                model=model,
                trait_concurrency=trait_concurrency,
                show_progress=show_progress,
                progress_callback=progress_callback,
            )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            res = asyncio.run(_run())
        else:
            import nest_asyncio
            nest_asyncio.apply()
            res = loop.run_until_complete(_run())
        if save_results:
            self.save_result(
                all_items=res,
                results_dir=results_dir,
                detailed_fname=detailed_fname,
                fname=fname,
            )
        return res

    def save_result(
        self,
        all_items: dict,
        results_dir: str | None = None,
        detailed_fname: str = 'results_detailed',
        fname:str = 'results',
    ) -> None:
        import os.path as op
        import json
        import os
        from .res2doc import res_to_doc
        
        final_item = {
            trait: {
                str(i): sjt
                for i, sjt in enumerate(
                    (s for data in res for s in data['items']), 1
                )
            }
            for trait, res in all_items.items()
        }
        os.makedirs(results_dir, exist_ok=True)
        p_detailed = op.join(results_dir, f'{detailed_fname}.json')
        p = op.join(results_dir, f'{fname}.json')
        p_docx = op.join(results_dir, f'{fname}.docx')
        
        with open(p_detailed, 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        print(f"Detailed results saved to {p_detailed}")
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(final_item, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {p}")
        res_to_doc(final_item, p_docx)
        print(f"Results document saved to {p_docx}")