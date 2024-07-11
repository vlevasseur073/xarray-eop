from pathlib import Path
from typing import Any, KeysView, Literal

import datatree
import xarray as xr
import zarr


def open_zarr_groups_from_dict(
    url: Path,
    group_list: list[str] | KeysView[str],
) -> None:
    list_of_groups = []
    for zarr_path in group_list:
        p = Path(zarr_path)
        for r in p.parents:
            if r not in list_of_groups and str(r) != ".":
                zarr.open_group(url, path=r)
                list_of_groups.append(r)


def convert_dict_to_plantuml(
    dictionary: dict[str, Any],
    name: str,
    direction: int = 0,
) -> str:
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


def collect_flags_from_datatree(
    dt: datatree.DataTree,
    variable_pattern: list[str] = ["flag", "mask"],
    isomorphic: bool = False,
) -> datatree.DataTree:
    """Collect all flag variables from a datatree.
    Pre-selection of dataset is done via a list of variable patterns.
    Finalization using the variable attributes, which should contain "flag_masks" as specified by CF convention

    Parameters
    ----------
    dt
        input datatree
    variable_pattern
        list of variable patterns
    isomorphic
        if True, returns datatree isomorphic to the original one, possibly with empty nodes.
        if False, returns only subtrees which include flags or masks.
        Default is False

    Returns
    -------
        datatree with only flag variables within the same tree structure as input
    """
    if isomorphic:
        is_var_flag = lambda var: next(  # noqa: E731
            (s for s in var.attrs.keys() if any(p in s for p in variable_pattern)),
            None,
        )
        node_contains_flag = lambda node: (  # noqa: E731
            is_var_flag(node.data_vars[var]) for var in node.data_vars
        )

        return dt.filter(node_contains_flag).filter_by_attrs(
            flag_masks=lambda v: v is not None,
        )
    else:
        return dt.filter(
            lambda node: next(
                (s for s in node.variables if any(p in s for p in variable_pattern)),
                None,
            ),
        ).filter_by_attrs(flag_masks=lambda v: v is not None)


@datatree.map_over_subtree
def filter_flags(ds: xr.Dataset) -> xr.Dataset:
    """Filter only flags variable while preserving the whole structure
    Following the CF convention, flag variables are filtered based on the presence of "flag_masks" attribute

    Parameters
    ----------
    ds
        input xarray.Dataset or datatree.DataTree

    Returns
    -------
        xarray.Dataset or datatree.DataTree
    """
    return xr.merge(
        [
            ds.filter_by_attrs(flag_masks=lambda v: v is not None),
            ds.filter_by_attrs(flag_values=lambda v: v is not None),
        ],
    )


def filter_datatree(
    dt: datatree.DataTree[Any],
    vars_grps: list[str],
    type: Literal["variables", "groups"],
) -> datatree.DataTree[Any]:
    """Filter datatree by selecting a list of given variables or groups

    Parameters
    ----------
    dt
        input datatree.DataTree
    vars_grps
        List of variable or group paths
    type
        Defines if the list is made of variables or groups ("variables" or "groups")

    Returns
    -------
        Filtered datatree.DataTree

    Raises
    ------
    ValueError
        if incorrect type is provided
    """
    if type == "variables":
        dt = dt.filter(
            lambda node: any(
                "/".join([node.path, var]) in vars_grps for var in node.variables  # type: ignore[list-item]
            ),
        )
        for tree in dt.subtree:
            grp = tree.path
            variables = list(tree.data_vars)
            drop_variables = [
                v for v in variables if "/".join([grp, v]) not in vars_grps
            ]
            if drop_variables:
                dt[grp] = dt[grp].drop_vars(drop_variables)
    elif type == "groups":
        dt = dt.filter(
            lambda node: next((s for s in node.groups if s in vars_grps), False),
        )
    else:
        raise ValueError("type as incorrect value: ", type)

    return dt
