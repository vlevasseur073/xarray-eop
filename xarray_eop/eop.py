import datatree
import json
import shutil
import warnings
import xarray as xr
import zarr

from pathlib import Path
from upath import UPath
from typing import Any, Dict, Optional, Tuple, Union

from xarray_eop.utils import convert_mapping
from xarray_eop.utils import MAPPINGS, SIMPL_MAPPING_PATH
from xarray_eop.utils import open_zarr_groups_from_dict
from xarray_eop.utils import convert_dict_to_plantuml

def open_eop_dataset(
    product_urlpath: Union[str,Path],
    *,
    drop_variables: Optional[Tuple[str]] = None,
    group: Optional[str] = None,
    storage_options: Optional[Dict[str, Any]] = None,
    check_files_exist: bool = False,
    override_product_files: Optional[str] = None,
    parse_geospatial_attrs: bool = True,
    ) -> xr.Dataset:
    if drop_variables is not None:
        warnings.warn("'drop_variables' is currently ignored")
    
    if isinstance(product_urlpath,str):
        url = UPath(product_urlpath)
    else:
        url = product_urlpath

    if group:
        url = url / group

    backend_kwargs={}
    if storage_options:
        backend_kwargs["storage_options"] = storage_options
    ds = xr.open_dataset( url, engine="zarr",chunks={},backend_kwargs=backend_kwargs)

    return ds


def create_dataset_from_zmetadata(
    zmetadata:Union[str,Path]
)->dict[str,xr.Dataset]:

    zfile = zmetadata
    if isinstance(zmetadata,str):
        zfile = Path(zmetadata)
    if not zfile.is_file():
        print("Metadata file does not exist: ",str(zmetadata))
        raise(Exception)
    
    with open(zfile) as f:
        zdict = json.load(f)
    
    
    list_of_variables = []
    list_of_groups = []
    list_of_leaf_groups = set()
    dataset_info = {}
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
                dataset_info[grp] = {var : zdict["metadata"]["/".join([glob_var,".zattrs"])]}
            else:
                dataset_info[grp][var] = zdict["metadata"]["/".join([glob_var,".zattrs"])]
            list_of_leaf_groups.add("/".join(parts[:-2]))

    # print(list_of_groups)
    # print(list_of_leaf_groups)
    # print(len(list_of_groups),len(list_of_leaf_groups))

    # print(dataset_info)

    ds = {}
    for grp in list_of_leaf_groups:
        # print("group: ",grp)
        array = []#list[xr.DataArray]
        for var,attrs in dataset_info[grp].items():
            # print(var,attrs)
            array.append(xr.DataArray(None,attrs=attrs,name=var))
            # print(array)
        ds[grp] = xr.merge(array)


    return ds


def open_eop_datatree(
    product_urlpath: Union[str,Path],
    **kwargs,
)->datatree.DataTree:
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
        zds = zarr.open_group(product_urlpath, mode="r",**storage_options)
    else:
        zds = zarr.open_group(product_urlpath, mode="r")
    ds = xr.open_dataset(product_urlpath, engine="zarr", **kwargs)
    tree_root = datatree.DataTree.from_dict({"/": ds})
    for path in datatree.io._iter_zarr_groups(zds):
        try:
            subgroup_ds = xr.open_dataset(product_urlpath, engine="zarr", group=path, **kwargs)
        except zarr.errors.PathNotFoundError:
            subgroup_ds = datatree.Dataset()

        # TODO refactor to use __setitem__ once creation of new nodes by assigning Dataset works again
        node_name = datatree.treenode.NodePath(path).name
        new_node: datatree.DataTree = datatree.DataTree(name=node_name, data=subgroup_ds)
        tree_root._set_item(
            path,
            new_node,
            allow_overwrite=False,
            new_nodes_along_path=True,
        )
    return tree_root


def create_datatree_from_zmetadata(
    zmetadata:Union[str,Path]
)->datatree.DataTree:
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
    zmetadata:Union[str,Path],
    product_urlpath:Path,
    use_datatree:Optional[bool] = False,
    consolidated:Optional[bool] = True
):
    if isinstance(product_urlpath,str):
        url = Path(product_urlpath)
    else:
        url = product_urlpath
    
    
    if use_datatree:
        dt=create_datatree_from_zmetadata(zmetadata)
        dt.to_zarr(url,consolidated=consolidated)
    
    else:
        ds = create_dataset_from_zmetadata(zmetadata)

        zarr.open(url,mode="w")
        open_zarr_groups_from_dict( url, ds.keys())

        for group in ds.keys():
            ds[group].to_zarr(url / group,mode="w")

        if consolidated:
            zarr.consolidate_metadata(url)

def _add_path_to_tree(tree, path):
    current = tree
    for part in path.split("/")[1:]:
        current = current.setdefault(part, {})
    return tree

def datatree_to_uml(
        product:datatree.DataTree,
        name:Optional[str] = None,
        direction:Optional[int]=0)->str:
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
    d={}
    for group in product.groups:
        if group=="/":
            offset = 1
            continue
        _add_path_to_tree(d,group)

    print(d)
    if name is None:
        n = product.name
    else:
        n = name
    uml = convert_dict_to_plantuml(d,n,direction)

    # print(uml)
    return uml