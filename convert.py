import json
import numpy as np
import xarray as xr
import zarr
from numcodecs import Blosc
from pathlib import Path
from typing import Optional, Any

from xarray_eop.utils import convert_mapping
from xarray_eop.utils import MAPPINGS, SIMPL_MAPPING_PATH

default_alg = "zstd"
default_comp = 3
default_shuffle = Blosc.BITSHUFFLE
DEFAULT_COMPRESSOR = Blosc(cname=default_alg, clevel=default_comp, shuffle=default_shuffle)


def open_groups(
    product_path: Path,
    map_safe: dict[str,Any]
    ):

    list_of_groups = []
    for zarr_path in map_safe["data_mapping"].keys():
        p=Path(zarr_path)
        for r in p.parents:
            if r not in list_of_groups:
                zarr.open_group(product_path,path=r)
                list_of_groups.append(r)


def product_converter(
    sample_path:Path,
    output_path:Path,
    product_type:Optional[str],
    simplified_mapping:Optional[bool] = False
    ):

    if not product_type:
        product_type = sample_path.name[:8]

    # Convert CS mapping or use a specific simplified mapping
    if simplified_mapping:
        with open ( SIMPL_MAPPING_PATH / MAPPINGS[product_type]) as f:
            map_safe = json.load(f)
    else:
        map_safe = convert_mapping(MAPPINGS[product_type])
    
    zarr.open(output_path, mode="w")
    open_groups( output_path, map_safe)

    for zarr_path in map_safe["data_mapping"].keys():
        # if zarr_path != "/quality":
        #     continue
        print("Creating ",zarr_path)
        ds = xr.open_dataset(
            sample_path,
            file_or_group=zarr_path,
            engine="sentinel-3",
            simplified_mapping=simplified_mapping)
        for v in ds.variables:
            ds[v].encoding["compressor"] = DEFAULT_COMPRESSOR
        ds.to_zarr(
            store = output_path / zarr_path.lstrip("/"),
            mode = "a",
        )
    
    zarr.consolidate_metadata(output_path)

if __name__ == "__main__":
    SAMPLE_PATH = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products/SAFE")
    OUTPUT_PATH = Path("/tmp")
    SAMPLE_PATH = Path("./")
    OUTPUT_PATH = Path("./")

    PRODUCTS ={
        "OL_1_EFR" : [
            "S3B_OL_1_EFR____20230506T015316_20230506T015616_20230711T065802_0180_079_117______LR1_D_NR_003.SEN3",
            f"S3OLCEFR_20230506T015316_0180_B117_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "OL_1_ERR" : [
            "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3",
            f"S3OLCERR_20230506T015316_0180_B117_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "OL_2_LFR": [
            "S3A_OL_2_LFR____20191227T124111_20191227T124411_20221209T133032_0179_053_109______PS1_D_NR_002.SEN3",
            f"S3OLCLFR_20191227T124111_0179_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_1_RBT" : [
            "S3B_SL_1_RBT____20230315T095847_20230315T100147_20230316T030042_0179_077_150_4320_PS2_O_NT_004.SEN3",
            f"S3SLSRBT_20230315T095847_0179_B150_S{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_2_LST": [
            "S3A_SL_2_LST____20191227T124111_20191227T124411_20221209T133218_0179_053_109______PS1_D_NR_004.SEN3",
            f"S3SLSLST_20191227T124111_0179_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_2_FRP": [
            "S3A_SL_2_FRP____20191227T131711_20191227T132011_20221209T133305_0180_053_109______PS1_O_NR_004.SEN3",
            f"S3SLSFRP_20191227T131711_0180_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
            # "S3A_SL_2_FRP____20200908T182648_20200908T182948_20220120T090409_0179_062_298______LR1_O_NT_001.SEN3",
            # f"S3SLSFRP_20200908T182648_0179_A298_S{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_SYN": [
            "S3A_SY_2_SYN____20191227T124211_20191227T124311_20230403T130523_0059_053_109______PS1_D_NR_002.SEN3",
            f"S3SYNSDR_20191227T124211_0059_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_VGP": [
            "S3A_SY_2_VGP____20191227T124211_20191227T124311_20230403T130523_0059_053_109______PS1_D_NR_002.SEN3",
            f"S3SYNVGP_20191227T124211_0059_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_VGK": [
            "S3A_SY_2_VGK____20191227T124211_20191227T124311_20230403T130523_0059_053_109______PS1_D_NR_002.SEN3",
            f"S3SYNVGK_20191227T124211_0059_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_VG1": [
            "S3A_SY_2_VG1____20231221T000000_20231221T235959_20231223T201855_EUROPE____________PS1_O_NT_002.SEN3",
            f"S3SYNVG1_20191227T124211_0000_A000_T{np.random.randint(0,999,1)[0]:03d}_VG1.zarr",
        ],
        "SY_2_V10": [
            "S3A_SY_2_V10____20231221T000000_20231231T235959_20240102T232539_EUROPE____________PS1_O_NT_002.SEN3",
            f"S3SYNV10_20231221T000000_0000_A000_T{np.random.randint(0,999,1)[0]:03d}_V10.zarr",
        ],
        "SY_2_AOD": [
            "S3A_SY_2_AOD____20191227T124211_20191227T124311_20230616T170045_0060_053_109______PS1_D_NR_002.SEN3",
            f"S3SYNAOD_20191227T124211_0060_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
    }

    PRODUCTS_TO_PROCESSED = ["OL_1_EFR","OL_1_ERR","SL_1_RBT","SL_2_LST","SL_2_FRP","SY_2_SYN"]
    PRODUCTS_TO_PROCESSED = ["SY_2_AOD"]
    for p in PRODUCTS_TO_PROCESSED:
        use_custom_simpl_mapping = False
        # In the cases of OLCI L1, lat/lon are duplicated in the /conditions/image_grid and /quality/image groups
        if p == "OL_1_EFR" or p == "OL_1_ERR" or p == "SY_2_AOD":
            use_custom_simpl_mapping = True
        print(f" ===== Convert {p} product, using custom simpl. mapping={use_custom_simpl_mapping}") 
        product_converter(
            SAMPLE_PATH / PRODUCTS[p][0],
            OUTPUT_PATH / PRODUCTS[p][1],
            product_type = p,
            simplified_mapping=use_custom_simpl_mapping
        )