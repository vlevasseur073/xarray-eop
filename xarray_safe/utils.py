import json
import importlib.resources
from pathlib import Path

MAPPING_PATH = importlib.resources.files("conf") / "mappings"
SIMPL_MAPPING_PATH = importlib.resources.files("conf") / "simplified_mappings"

MAPPINGS = {
    "OL_1_EFR": "S3_OL_1_mapping.json"
}

def get_simplified_mapping():
    for _,mapping in MAPPINGS.items():
        ds = convert_mapping(mapping)
    
        with open( SIMPL_MAPPING_PATH / mapping, 'w', encoding='utf-8') as f:
            json.dump(ds, f, indent=4)


def convert_mapping(mapping_file:str)->dict[str,dict[str,tuple[str,str]]]:
    with open( MAPPING_PATH / mapping_file ) as f:
        eopf_mapping=json.load(f)
    
    
    new_mapping={}
    for map in eopf_mapping["data_mapping"]:
        if map["item_format"] == "netcdf-dimension":
            continue
        src:str = map["source_path"]
        dest:str = map["target_path"]
        
        if src.startswith("xfdumanifest"):
            continue
        
        file = src.split(":")[0]
        var = src.split(":")[1]
        
        group = str(Path(dest).parents[0])
        variable = str(Path(dest).name)

        if "coordinates" in group:# and variable not in ["latitude","longitude"]:
            group = group.replace("coordinates","conditions")
        
        if group not in new_mapping:
            new_mapping[group] = {}
        
        if file not in new_mapping[group]:
            new_mapping[group][file] = []
        new_mapping[group][file].append((var,variable))
        
        # if file not in new_mapping:
        #     new_mapping[file] = {}
        # new_mapping[file][var] = dest

    return new_mapping

