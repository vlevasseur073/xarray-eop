import datatree
import json
import numpy as np
import xarray as xr
import zarr
from numcodecs import Blosc
from pathlib import Path
from typing import Optional, Any

from xarray_eop.eop import open_eop_datatree
from xarray_eop.eop import datatree_to_uml
from xarray_eop.conversion.update_attrs import update_attributes
from xarray_eop.conversion.utils import convert_mapping
from xarray_eop.conversion.utils import MAPPINGS, SIMPL_MAPPING_PATH, DEFAULT_COMPRESSOR

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

def check_duplicate_set(items):
    hash_bucket = set()
    for item in items:
        if item in hash_bucket:
            print(item)
            return True
        hash_bucket.add(item)
    return False

def product_converter(
    sample_path:Path,
    output_path:Path,
    product_type:Optional[str],
    simplified_mapping:Optional[bool] = False,
    zip:Optional[bool] = True
    ) -> datatree.DataTree:

    if not product_type:
        product_type = sample_path.name[:8]

    # Convert CS mapping or use a specific simplified mapping
    if simplified_mapping:
        with open ( SIMPL_MAPPING_PATH / MAPPINGS[product_type]) as f:
            map_safe = json.load(f)
    else:
        map_safe = convert_mapping(MAPPINGS[product_type])
    
    prod=zarr.open(output_path, mode="w")
    open_groups( output_path, map_safe)

    shortnames:list =[]
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
            if v in shortnames:
                # new_shortname = "_".join([v,zarr_path.split("/")[-1]])
                tmp=zarr_path.split("/")[2:]
                tmp.insert(0,v)
                new_shortname = "_".join(tmp)
                if new_shortname in shortnames:
                    print(f"Warning: {new_shortname} already exists in shornames list")
                    print(f"Warning: variables {v} will not have short_name")
                    print("Warning: continue")
                    continue
                ds[v].attrs.update({"short_name":new_shortname})
                shortnames.append(new_shortname)
            else:
                ds[v].attrs.update({"short_name":v})
                shortnames.append(v)
        ds.to_zarr(
            store = output_path / zarr_path.lstrip("/"),
            mode = "a",
        )
    
    # Verification of unicity of shortnames
    if len(set(shortnames)) < len(shortnames):
        print("Error in shortnames: Items appear twice ...")
        # print(shortnames)
        check_duplicate_set(shortnames)
        exit(0)

    print("Updating and consolidate metadata")
    typ_eop = output_path.name[:9]
    prod.attrs.update(update_attributes(typ_eop))
    zarr.consolidate_metadata(output_path)
    
    # Check to open with datatree and zip
    print("Checking product")
    decode_times=True
    if typ_eop in ["S03SYNVGK","S03SYNVG1","S03SYNV10"]:
        decode_times=False
    dt: datatree.DataTree = open_eop_datatree(output_path,decode_times=decode_times)
    if zip: 
        with zarr.ZipStore(str(output_path)+".zip") as store:
            dt.to_zarr(store)

    return dt

if __name__ == "__main__":
    SAMPLE_PATH = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products/SAFE")
    OUTPUT_PATH = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products/Zarr_DDR")
    # SAMPLE_PATH = Path("/tmp")
    # OUTPUT_PATH = Path("/tmp")

    PRODUCTS ={
        "OL_1_EFR" : [
            "S3B_OL_1_EFR____20230506T015316_20230506T015616_20230711T065802_0180_079_117______LR1_D_NR_003.SEN3",
            f"S03OLCEFR_20230506T015316_0180_B117_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "OL_1_ERR" : [
            "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3",
            f"S03OLCERR_20230506T015316_0180_B117_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "OL_2_LFR": [
            "S3A_OL_2_LFR____20191227T124111_20191227T124411_20221209T133032_0179_053_109______PS1_D_NR_002.SEN3",
            f"S03OLCLFR_20191227T124111_0179_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_1_RBT" : [
            "S3B_SL_1_RBT____20230315T095847_20230315T100147_20230316T030042_0179_077_150_4320_PS2_O_NT_004.SEN3",
            f"S03SLSRBT_20230315T095847_0179_B150_S{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_2_LST": [
            "S3A_SL_2_LST____20191227T124111_20191227T124411_20221209T133218_0179_053_109______PS1_D_NR_004.SEN3",
            f"S03SLSLST_20191227T124111_0179_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SL_2_FRP": [
            # "S3A_SL_2_FRP____20191227T131711_20191227T132011_20221209T133305_0180_053_109______PS1_O_NR_004.SEN3",
            # f"S03SLSFRP_20191227T131711_0180_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
            "S3A_SL_2_FRP____20200908T182648_20200908T182948_20220120T090409_0179_062_298______LR1_O_NT_001.SEN3",
            f"S03SLSFRP_20200908T182648_0179_A298_S{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_SYN": [
            "S3A_SY_2_SYN____20191227T124211_20191227T124311_20230403T130523_0059_053_109______PS1_D_NR_002.SEN3",
            f"S03SYNSDR_20191227T124211_0059_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_VGP": [
            "S3A_SY_2_VGP____20191227T124211_20191227T124311_20230403T130523_0059_053_109______PS1_D_NR_002.SEN3",
            f"S03SYNVGP_20191227T124211_0059_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_VGK": [
            "S3A_SY_2_VGK____20191227T124211_20191227T124311_20230403T130523_0059_053_109______PS1_D_NR_002.SEN3",
            f"S03SYNVGK_20191227T124211_0059_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
        "SY_2_VG1": [
            "S3A_SY_2_VG1____20231221T000000_20231221T235959_20231223T201855_EUROPE____________PS1_O_NT_002.SEN3",
            f"S03SYNVG1_20191227T124211_0000_A000_T{np.random.randint(0,999,1)[0]:03d}_VG1.zarr",
        ],
        "SY_2_V10": [
            "S3A_SY_2_V10____20231221T000000_20231231T235959_20240102T232539_EUROPE____________PS1_O_NT_002.SEN3",
            f"S03SYNV10_20231221T000000_0000_A000_T{np.random.randint(0,999,1)[0]:03d}_V10.zarr",
        ],
        "SY_2_AOD": [
            "S3A_SY_2_AOD____20191227T124211_20191227T124311_20230616T170045_0060_053_109______PS1_D_NR_002.SEN3",
            f"S03SYNAOD_20191227T124211_0060_A109_T{np.random.randint(0,999,1)[0]:03d}.zarr",
        ],
    }

    PRODUCTS_TO_PROCESSED = [
        # "OL_1_EFR",
        # "OL_1_ERR",
        # "OL_2_LFR",
        # "SL_1_RBT",
        # "SL_2_LST",
        "SL_2_FRP",
        # "SY_2_SYN",
        # "SY_2_AOD",
        # "SY_2_VGP",
        # "SY_2_VGK",
        # "SY_2_VG1",
        # "SY_2_V10"
    ]
    # PRODUCTS_TO_PROCESSED = ["SL_1_RBT","OL_1_EFR"]
    # PRODUCTS_TO_PROCESSED = ["OL_1_ERR"]
    for p in PRODUCTS_TO_PROCESSED:
        use_custom_simpl_mapping = False
        # In the cases of OLCI L1, lat/lon are duplicated in the /conditions/image_grid and /quality/image groups
        if p in [
            "OL_1_EFR",
            "OL_1_ERR",
            "OL_2_LFR",
            "SY_2_AOD",
            "SY_2_VGP",
            "SY_2_VGK",
            "SY_2_VG1",
            "SY_2_V10"
            ]:
            use_custom_simpl_mapping = True
        print(f" ===== Convert {p} product, using custom simpl. mapping={use_custom_simpl_mapping}") 
        dt = product_converter(
            SAMPLE_PATH / PRODUCTS[p][0],
            OUTPUT_PATH / PRODUCTS[p][1],
            product_type = p,
            simplified_mapping=use_custom_simpl_mapping
        )
        pattern:str = PRODUCTS[p][1][:9]
        uml_filename = "_".join([pattern,"product","structure"])+".puml"
        uml = datatree_to_uml(dt,name=pattern)
        with open(OUTPUT_PATH / uml_filename,"w") as f:
            f.write(uml)