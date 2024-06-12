import json
import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import datatree
import xarray as xr
import zarr

from xarray_eop.path import EOPath
from xarray_eop.utils import convert_dict_to_plantuml, open_zarr_groups_from_dict


def open_eop_dataset(
    product_urlpath: Union[str, Path],
    *,
    drop_variables: Optional[Tuple[str]] = None,
    group: Optional[str] = None,
    storage_options: Optional[Dict[str, Any]] = None,
    decode_times: bool | None = None,
) -> xr.Dataset:
    if drop_variables is not None:
        warnings.warn("'drop_variables' is currently ignored")

    if isinstance(product_urlpath, str):
        url = EOPath(product_urlpath)
    else:
        url = product_urlpath

    if group:
        url = url / group

    backend_kwargs = {}
    if storage_options:
        backend_kwargs["storage_options"] = storage_options
    ds = xr.open_dataset(
        url,
        engine="zarr",
        chunks={},
        decode_times=decode_times,
        backend_kwargs=backend_kwargs,
    )

    return ds


def create_dataset_from_zmetadata(zmetadata: Union[str, Path]) -> dict[str, xr.Dataset]:

    if isinstance(zmetadata, str):
        zfile = Path(zmetadata)
    else:
        zfile = zmetadata
    if not zfile.is_file():
        print("Metadata file does not exist: ", str(zmetadata))
        raise (Exception)

    with open(zfile) as f:
        zdict = json.load(f)

    list_of_variables = []
    list_of_groups = []
    list_of_leaf_groups = set()
    dataset_info: Dict[str, Any] = {}
    for k in zdict["metadata"].keys():
        parts = k.split("/")
        if parts[-1] == ".zgroup":
            list_of_groups.append("/".join(parts[:-1]))
        if parts[-1] == ".zarray":
            list_of_variables.append("/".join(parts[:-1]))
            glob_var = "/".join(parts[:-1])
            var = parts[-2]
            grp = "/".join(parts[:-2])
            if grp not in dataset_info.keys():
                dataset_info[grp] = {
                    var: zdict["metadata"]["/".join([glob_var, ".zattrs"])],
                }
            else:
                dataset_info[grp][var] = zdict["metadata"][
                    "/".join([glob_var, ".zattrs"])
                ]
            list_of_leaf_groups.add("/".join(parts[:-2]))

    # print(list_of_groups)
    # print(list_of_leaf_groups)
    # print(len(list_of_groups),len(list_of_leaf_groups))

    # print(dataset_info)

    ds = {}
    for grp in list_of_leaf_groups:
        # print("group: ",grp)
        array = []  # list[xr.DataArray]
        for var, attrs in dataset_info[grp].items():
            # print(var,attrs)
            array.append(xr.DataArray(None, attrs=attrs, name=var))
            # print(array)
        ds[grp] = xr.merge(array)

    return ds


def open_eop_datatree(
    product_urlpath: Union[str, Path],
    **kwargs,
) -> datatree.DataTree:
    """Open and decode a EOPF-like Zarr product

    Parameters
    ----------
    product_urlpath: str, Path
        Path to directory in file system or name of zip file.
        It supports passing URLs directly to fsspec and having it create the "mapping" instance automatically.
        This means, that for all of the backend storage implementations supported by fsspec, you can skip importing and
        configuring the storage explicitly.

    kwargs: dict

    Returns
    -------
        datatree.DataTree
    """

    if "chunks" not in kwargs:
        kwargs["chunks"] = {}

    if "backend_kwargs" in kwargs:
        storage_options = kwargs["backend_kwargs"]
        zds = zarr.open_group(product_urlpath, mode="r", **storage_options)
    else:
        zds = zarr.open_group(product_urlpath, mode="r")
    ds = xr.open_dataset(product_urlpath, **kwargs)
    tree_root = datatree.DataTree.from_dict({"/": ds})
    for path in datatree.io._iter_zarr_groups(zds):
        try:
            subgroup_ds = xr.open_dataset(
                product_urlpath,
                group=path,
                **kwargs,
            )
        except zarr.errors.PathNotFoundError:
            subgroup_ds = datatree.Dataset()

        # TODO refactor to use __setitem__ once creation of new nodes by assigning Dataset works again
        node_name = datatree.treenode.NodePath(path).name
        new_node: datatree.DataTree = datatree.DataTree(
            name=node_name,
            data=subgroup_ds,
        )
        tree_root._set_item(
            path,
            new_node,
            allow_overwrite=False,
            new_nodes_along_path=True,
        )
    return tree_root


def create_datatree_from_zmetadata(zmetadata: Union[str, Path]) -> datatree.DataTree:
    """Create a datatree from a template ``zmetadata`` structure

    Parameters
    ----------
    zmetadata: str,Path
        input ``zmetadata`` file

    Returns
    -------
        datatree.DataTree
    """

    ds = create_dataset_from_zmetadata(zmetadata)
    return datatree.DataTree.from_dict(ds)


def save_template_eop(
    zmetadata: Union[str, Path],
    product_urlpath: Path,
    use_datatree: Optional[bool] = False,
    consolidated: Optional[bool] = True,
):
    if isinstance(product_urlpath, str):
        url = Path(product_urlpath)
    else:
        url = product_urlpath

    if use_datatree:
        dt = create_datatree_from_zmetadata(zmetadata)
        dt.to_zarr(url, consolidated=consolidated)

    else:
        ds = create_dataset_from_zmetadata(zmetadata)

        zarr.open(url, mode="w")
        open_zarr_groups_from_dict(url, ds.keys())

        for group in ds.keys():
            ds[group].to_zarr(url / group, mode="w")

        if consolidated:
            zarr.consolidate_metadata(url)


def _add_path_to_tree(tree, path):
    current = tree
    for part in path.split("/")[1:]:
        current = current.setdefault(part, {})
    return tree


def datatree_to_uml(
    product: datatree.DataTree,
    name: Optional[str] = None,
    direction: Optional[int] = 0,
) -> str:
    """Generate a simplified UML diagram from a datatree

    Parameters
    ----------
    product: datatree.DataTree
        input DataTree structure
    name, optional
        Title given to the UML diagram. If not set, the product name will be used. Default None
    direction, optional
        top_to_bottom (0) or left_to_right (1), by default 0

    Returns
    -------
        plantUML string
    """
    d: dict[Any, Any] = {}
    for group in product.groups:
        if group == "/":
            continue
        _add_path_to_tree(d, group)

    print(d)
    if name is None:
        n = product.name
    else:
        n = name
    uml = convert_dict_to_plantuml(d, n, direction)

    # print(uml)
    return uml
