import json
import numpy as np
import xarray as xr
import zarr
from numcodecs import Blosc
from pathlib import Path
from typing import Optional, Any

from xarray_safe.utils import convert_mapping
from xarray_safe.utils import MAPPINGS, SIMPL_MAPPING_PATH

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

    PRODUCTS ={
        "OL_1_EFR" : [
            "S3B_OL_1_EFR____20230506T015316_20230506T015616_20230711T065802_0180_079_117______LR1_D_NR_003.SEN3",
            f"S3OLCEFR_20230506T015316_0180_B117_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_1_RBT" : [
            "S3B_SL_1_RBT____20230315T095847_20230315T100147_20230316T030042_0179_077_150_4320_PS2_O_NT_004.SEN3",
            f"S3SLSRBT_20230315T095847_0179_B150_S{np.random.randint(0,999,1)[0]:03d}.zarr",
        ]
    }

    PRODUCTS_TO_PROCESSED = ["OL_1_EFR","SL_1_RBT"]
    for p in PRODUCTS_TO_PROCESSED:
        use_custom_simpl_mapping = False
        if p == "OL_1_EFR":
            use_custom_simpl_mapping = True
        print(f" ===== Convert {p} product, using custom simpl. mapping={use_custom_simpl_mapping}") 
        product_converter(
            SAMPLE_PATH / PRODUCTS[p][0],
            OUTPUT_PATH / PRODUCTS[p][1],
            product_type = p,
            simplified_mapping=use_custom_simpl_mapping
        )