import json
import importlib.resources
import re
import xarray as xr
from pathlib import Path
from typing import Union

MAPPING_PATH = importlib.resources.files("conf") / "mappings"
SIMPL_MAPPING_PATH = importlib.resources.files("conf") / "simplified_mappings"
REMAPPING_FILE = MAPPING_PATH / "remap.json"

MAPPINGS = {
    "OL_1_EFR": "S3_OL_1_mapping.json",
    "OL_1_ERR": "S3OLCERR_mapping.json",
    "SL_1_RBT": "S3_SL_1_RBT_mapping.json",
    "SL_2_LST": "S3_SL_2_LST_mapping.json",
    "SL_2_FRP": "S3SLSFRP_mapping.json",
    "SY_2_SYN": "S3_SY_2_SYN_mapping.json",
    "SY_2_AOD": "S3SYNAOD_mapping.json",
    "SY_2_VGK": "S3SYNVGK_mapping.json",
    "SY_2_VGP": "S3SYNVGP_mapping.json",
    "SY_2_VG1": "S3SYNVG1_mapping.json",
    "SY_2_V10": "S3SYNV10_mapping.json",

}

def get_simplified_mapping():
    """Generates a simplified mapping from EOPF mapping
    The resulting file is store under conf/simplified_mappings/ref
    """
    
    for _,mapping in MAPPINGS.items():
        print("Convert ", mapping)
        ds = convert_mapping(mapping)
    
        with open( SIMPL_MAPPING_PATH / "ref" / mapping, 'w', encoding='utf-8') as f:
            json.dump(ds, f, indent=4)


def convert_mapping(mapping_file:str)->dict[str,dict[str,tuple[str,str]]]:
    with open( MAPPING_PATH / mapping_file ) as f:
        eopf_mapping=json.load(f)
    
    
    new_mapping={
        "chunk_sizes": eopf_mapping["chunk_sizes"]
    }
    data_map = new_mapping["data_mapping"] = {}
    for map in eopf_mapping["data_mapping"]:
        if map["item_format"] == "netcdf-dimension":
            continue
        src:str = map["source_path"]
        dest:str = map["target_path"]
        
        if not (src and dest):
            continue
        if src.startswith("xfdumanifest"):
            continue
        
        # Check for any specific remapping
        if REMAPPING_FILE.is_file():
            with open(REMAPPING_FILE) as rf:
                remap = json.load(rf)
            if mapping_file in remap:
                # if dest in remap[mapping_file]:
                #     dest = remap[mapping_file][dest]
                for d in remap[mapping_file]:
                    r=re.search(d,dest)
                    if r:
                        if r.re.pattern==dest:
                            dest = remap[mapping_file][dest]
                        else:
                            v=dest.split("/")[-1]
                            dest = remap[mapping_file][d]
                            l=dest.split("/")[:-1]
                            l.append(v)
                            dest="/".join(l)
        if not dest:
            continue

        try:
            file = src.split(":")[0]
            var = src.split(":")[1]
        except IndexError:
            print(f"Error in src path: {src}")
            print (map)
            raise(IndexError)
        
        group = str(Path(dest).parents[0])
        variable = str(Path(dest).name)

        

        if "coordinates" in group:# and variable not in ["latitude","longitude"]:
            group = group.replace("coordinates","conditions")
        
        if group not in data_map:
            data_map[group] = {}
        
        if file not in data_map[group]:
            data_map[group][file] = []
        data_map[group][file].append((var,variable))
        

    return new_mapping