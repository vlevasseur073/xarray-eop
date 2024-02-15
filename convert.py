import json
import numpy as np
import xarray as xr
import zarr
from pathlib import Path
from typing import Optional, Any

from xarray_safe.utils import convert_mapping
from xarray_safe.utils import MAPPINGS, SIMPL_MAPPING_PATH

def open_groups(
    product_path: Path,
    map_safe: dict[str,Any]
    ):

    list_of_groups = []
    for zarr_path in map_safe.keys():
        p=Path(zarr_path)
        for r in p.parents:
            if r not in list_of_groups:
                zarr.open_group(product_path,path=r)
                list_of_groups.append(r)


def product_converter(
    sample_path:Path,
    output_path:Optional[Path] = "/tmp",
    simplified_mapping:Optional[bool] = False
    ):
    PRODUCTS ={
        "OL_1_EFR" : [
            "S3B_OL_1_EFR____20230506T015316_20230506T015616_20230711T065802_0180_079_117______LR1_D_NR_003.SEN3",
            f"S3OLCEFR_20230506T015316_0180_B117_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ]
    } 

    for product_type in PRODUCTS.keys():
        # Convert CS mapping or use a specific simplified mapping
        if simplified_mapping:
            with open ( SIMPL_MAPPING_PATH / MAPPINGS[product_type]) as f:
                map_safe = json.load(f)
        else:
            map_safe = convert_mapping(MAPPINGS[product_type])
        
        safe_product = PRODUCTS[product_type][0]
        zarr_product = PRODUCTS[product_type][1]

        zarr.open(output_path / zarr_product, mode="w")
        open_groups( output_path / zarr_product, map_safe)

        for zarr_path in map_safe.keys():
            if zarr_path == "/coordinates/tiepoint_subgrid":
                continue
            
            print("Creating ",zarr_path)
            ds = xr.open_dataset(
                sample_path / safe_product,
                file_or_group=zarr_path,
                engine="sentinel-3",
                simplified_mapping=simplified_mapping)
            ds.to_zarr(
                store = output_path / zarr_product / zarr_path.lstrip("/"),
                mode = "a")
            # break
        
        zarr.consolidate_metadata(output_path / zarr_product)

if __name__ == "__main__":
    SAMPLE_PATH = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products/SAFE")
    OUTPUT_PATH = Path("/tmp")
    product_converter(SAMPLE_PATH,OUTPUT_PATH,simplified_mapping=True)