from pathlib import Path
import zarr

def open_zarr_groups_from_dict(
        url: Path,
        group_list: list[str]
    ):
    list_of_groups = []
    for zarr_path in group_list:
        p = Path(zarr_path)
        for r in p.parents:
            if r not in list_of_groups and str(r) != ".":
                zarr.open_group(url,path=r)
                list_of_groups.append(r)


def convert_dict_to_plantuml(dictionary, name,direction=0):
    plantuml_code = f"@startuml\n"
    if direction == 0:
        plantuml_code += "top to bottom direction\n"
    else:
        plantuml_code += "left to right direction\n"

    plantuml_code += f"object {name}\n"
    for key, value in dictionary.items():
        plantuml_code += f"object {key}\n"
        if isinstance(value, dict):
            for sub_key in value:
                plantuml_code += f"object \"{sub_key}\" as {key}_{sub_key}\n"
                plantuml_code += f"{key} -- {key}_{sub_key}\n"
                if isinstance(value[sub_key], dict):
                    for sub_sub_key in value[sub_key]:
                        plantuml_code += f"object \"{sub_sub_key}\" as {key}_{sub_key}_{sub_sub_key}\n"
                        plantuml_code += f"{key}_{sub_key} -- {key}_{sub_key}_{sub_sub_key}\n"
        plantuml_code += "\n"

    for key in dictionary:
        plantuml_code += f"{name} -- {key}\n"

    plantuml_code += "@enduml\n"

    return plantuml_code
