# %%
from src import DataLoader, TxtAgent, ImgAgent, VidAgent
from src import ref_viz
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()
# %%
data_loader = DataLoader()
sjts_data = data_loader.load("PSJT-Mussel", "zh")
neopir = data_loader.load("NEO-PI-R")
neopir_meta = data_loader.load_meta("NEO-PI-R")
trait_names = list(neopir_meta.keys())

outdir = Path("./outputs")
outdir.mkdir(exist_ok=True, parents=True)
# %%
test_trait = 'N4'
test_idx = '1'
ref_cha = 'male'

txt_agent = TxtAgent(
    situation_theme='大学生活',
    target_population='中国大学生',
)

img_agent = ImgAgent(
    situ=sjts_data[test_trait][test_idx],
    trait = neopir_meta[test_trait]['facet_name'],
    ref_viz=ref_viz[ref_cha]
)

vid_agent = VidAgent(
    situ=sjts_data[test_trait][test_idx],
    trait = neopir_meta[test_trait]['facet_name'],
)
# %%
txt_res = txt_agent.run(
    trait_name=neopir_meta[test_trait]['facet_name'],
    trait_description=neopir_meta[test_trait]['description'],
    low_score=neopir_meta[test_trait]['low_score'],
    high_score=neopir_meta[test_trait]['high_score'],
    item=list(neopir[test_trait]['items'].values())[0]['item'],
    n_item=1,
    outdir=outdir,
    out_basename=f"SJT_{test_trait}_{test_idx}"
    )['items']
# %%
img_res = img_agent.run(
    run_bubble=True, 
    outdir=outdir,
    out_basename=f"SJT_{test_trait}_{test_idx}"
    )
# %%
vid_res = vid_agent.run(
    outdir=outdir,
    out_basename=f"SJT_{test_trait}_{test_idx}"
    )
# %%
