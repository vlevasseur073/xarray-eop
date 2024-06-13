from pathlib import Path
from typing import KeysView

import zarr


def open_zarr_groups_from_dict(url: Path, group_list: list[str] | KeysView[str]):
    list_of_groups = []
    for zarr_path in group_list:
        p = Path(zarr_path)
        for r in p.parents:
            if r not in list_of_groups and str(r) != ".":
                zarr.open_group(url, path=r)
                list_of_groups.append(r)


def convert_dict_to_plantuml(dictionary, name, direction=0):
    """Convert a dictionary to a UML diagram based on plantUML

    Parameters
    ----------
    dictionary
        input dictionary
    name: str
        Title of the diagram
    direction, optional: bool
        diagram direction, 0 means top-to-bottom, 1 left-to-right. Default 0

    Returns
    -------
        string containing the plantUML description
    """
    plantuml_code = "@startuml\n"
    if direction == 0:
        plantuml_code += "top to bottom direction\n"
    else:
        plantuml_code += "left to right direction\n"

    plantuml_code += f"object {name}\n"
    for key, value in dictionary.items():
        plantuml_code += f"object {key}\n"
        if isinstance(value, dict):
            for sub_key in value:
                plantuml_code += f'object "{sub_key}" as {key}_{sub_key}\n'
                plantuml_code += f"{key} -- {key}_{sub_key}\n"
                if isinstance(value[sub_key], dict):
                    for sub_sub_key in value[sub_key]:
                        plantuml_code += (
                            f'object "{sub_sub_key}" as {key}_{sub_key}_{sub_sub_key}\n'
                        )
                        plantuml_code += (
                            f"{key}_{sub_key} -- {key}_{sub_key}_{sub_sub_key}\n"
                        )
        plantuml_code += "\n"

    for key in dictionary:
        plantuml_code += f"{name} -- {key}\n"

    plantuml_code += "@enduml\n"

    return plantuml_code
