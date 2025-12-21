# %%
from lmitf import TemplateLLM
import os.path as op
import asyncio
from tqdm import tqdm


class SJTAgent:
    def __init__(
        self, 
        situation_theme="大学校园里的日常生活",
        target_population="大学生",
        max_concurrency: int = 100,
        show_progress: bool = True,
        ):
        """
        situation_theme: 场景主题
        max_concurrency: 最大并发度（根据你的接口限速能力调整）
        """
        self.situation_theme = situation_theme
        self.target_population = target_population
        self.max_concurrency = max_concurrency
        self.show_progress = show_progress

        # Get the directory where this module is located
        current_dir = op.dirname(op.abspath(__file__))
        
        ba_prompt = op.join(current_dir, "prompts", "behavior_adapter.py")
        sb_prompt_a = op.join(current_dir, "prompts", "scenario_builder_a.py")
        sb_prompt_b = op.join(current_dir, "prompts", "scenario_builder_b.py")
        td_prompt = op.join(current_dir, "prompts", "trait_decoder.py")
        tp_prompt = op.join(current_dir, "prompts", "trait_polisher.py")

        self.ba = TemplateLLM(ba_prompt)
        self.sb_a = TemplateLLM(sb_prompt_a)
        self.sb_b = TemplateLLM(sb_prompt_b)
        self.td = TemplateLLM(td_prompt)
        self.tp = TemplateLLM(tp_prompt)

    async def _generate_items(
        self, 
        trait_name,
        trait_description,
        low_score,
        high_score,
        item, 
        n_item,
        model = 'gpt-4o',
        ):
        final_item = {}
        final_item['source'] = item

        # 放线程池，避免阻塞事件循环
        res_td = await asyncio.to_thread(
            self.td.call,
            trait_name=trait_name,
            target_population=self.target_population,
            trait_description=trait_description,
            low_score=low_score,
            high_score=high_score,
            item=item,
            response_format="json",
            model=model
        )
        res_tp = await asyncio.to_thread(
            self.tp.call,
            trait_name=trait_name,
            target_population=self.target_population,
            trait_description=trait_description,
            low_score=res_td['low_score'],
            high_score=res_td['high_score'],
            response_format="json",
            model=model
        )

        cues = await asyncio.to_thread(
            self.sb_a.call,
            trait_name=trait_name,
            target_population=self.target_population,
            situation_theme=self.situation_theme,
            n_cue=n_item,
            low_score=res_tp['low_score'],
            high_score=res_tp['high_score'],
            response_format="json",
            model=model
        )
        self.res_td = res_td
        self.res_tp = res_tp
        self.res_sb_a = cues

        cue_list = cues.get("cues", [])
        sem = asyncio.Semaphore(self.max_concurrency)

        async def process_cue(cue):
            async with sem:
                try:
                    res_sb_b = await asyncio.to_thread(
                        self.sb_b.call,
                        trait_name=trait_name,
                        target_population=self.target_population,
                        cue=cue,
                        n_situ=1,
                        low_score=res_tp['low_score'],
                        high_score=res_tp['high_score'],
                        response_format="json",
                        model=model
                    )

                    res_ba = await asyncio.to_thread(
                        self.ba.call,
                        situation=res_sb_b["situation"][0],
                        trait_name=trait_name,
                        target_population=self.target_population,
                        low_score=res_tp['low_score'],
                        high_score=res_tp['high_score'],
                        response_format="json",
                        model=model
                    )

                    return {
                        "situation": res_sb_b["situation"][0],
                        "options": res_ba["options"],
                    }
                except Exception as e:
                    return {
                        "error": repr(e),
                        "cue": cue,
                    }

        tasks = [process_cue(cue) for cue in cue_list]

        results = []
        if self.show_progress:
            for fut in tqdm(
                asyncio.as_completed(tasks),
                total=len(tasks),
                desc=f"Generating {trait_name}'s {n_item} sjts from source item",
                leave=False
            ):
                results.append(await fut)
        else:
            for fut in asyncio.as_completed(tasks):
                results.append(await fut)

        final_item['n_item'] = n_item
        final_item['trait_decoder'] = res_td
        final_item['trait_polisher'] = res_tp
        final_item['cues'] = cue_list
        if n_item == 1:
            final_item['items'] = results[0]
        else:
            final_item['items'] = results

        self.generated_items = final_item

        return final_item

    def run(
        self, 
        trait_name, 
        trait_description, 
        low_score,
        high_score,
        item, 
        n_item, 
        model = 'gpt-4o',
        outdir=None,
        out_basename=None,
        ):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            result = asyncio.run(self._generate_items(
                trait_name,
                trait_description,
                low_score,
                high_score,
                item, n_item, model=model))
        else:
            import nest_asyncio

            nest_asyncio.apply()
            result = loop.run_until_complete(self._generate_items(trait_name, trait_description, low_score, high_score, item, n_item, model=model))
        if outdir is not None:
            import json
            if out_basename is not None:
                trait_name = out_basename
            fname = f"{trait_name}_txt.json"
            with open(op.join(outdir, fname), "w", encoding="utf-8") as f:
                json.dump(result['items'], f, ensure_ascii=False, indent=4)
        return result
    
    def _repr_html_(self):
        if not hasattr(self, 'res_td') or not hasattr(self, 'res_sb_a'):
            return "<p>No generation results available. Please run <code>run</code> first.</p>"
        import pandas as pd
        # Create DataFrame for trait decoder results
        td_df = pd.DataFrame([self.res_td]).T
        td_df.columns = [f'特质解析结果']
        td_df.index.name = '维度'

        # Create DataFrame for scenario builder A results (cues)
        cues_data = self.res_sb_a.get("cues", [])
        sb_a_df = pd.DataFrame(cues_data, columns=['情境线索'])
        sb_a_df.index.name = '序号'
        sb_a_df.index = sb_a_df.index + 1

        # Combine both DataFrames into HTML
        html_output = f"""
        <h3>特质解析结果</h3>
        {td_df.to_html(escape=False)}
        <h3>情境线索生成结果 (共{len(cues_data)}个)</h3>
        {sb_a_df.to_html(escape=False)}
        """

        return html_output

#%%
