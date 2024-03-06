import datatree
import json
import warnings
import xarray as xr

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from xarray_eop.utils import convert_mapping
from xarray_eop.utils import MAPPINGS, SIMPL_MAPPING_PATH

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
        url = Path(product_urlpath)
    else:
        url = product_urlpath

    ds = xr.open_dataset( url / group, engine="zarr",chunks={})

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
    
    dt = datatree.open_datatree(product_urlpath,engine="zarr",**kwargs)

    return dt