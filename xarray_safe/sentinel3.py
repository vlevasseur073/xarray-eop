import json
import warnings
import xarray as xr

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from xarray_safe.utils import convert_mapping
from xarray_safe.utils import MAPPINGS, SIMPL_MAPPING_PATH

def open_sentinel3_dataset(
    product_urlpath: Union[str,Path],
    ncfile_or_zarrgroup: Union[str,Path],
    *,
    drop_variables: Optional[Tuple[str]] = None,
    group: Optional[str] = None,
    storage_options: Optional[Dict[str, Any]] = None,
    check_files_exist: bool = False,
    override_product_files: Optional[str] = None,
    parse_geospatial_attrs: bool = True,
    simplified_mapping: Optional[bool] = False
    ) -> xr.Dataset:
    if drop_variables is not None:
        warnings.warn("'drop_variables' is currently ignored")
    
    if isinstance(product_urlpath,str):
        url = Path(product_urlpath)
    else:
        url = product_urlpath
    files = [f for f in url.iterdir() if f.is_file()]

    # check the ncfile or zarr group
    if ncfile_or_zarrgroup.endswith(".nc"):
        dataset = "netcdf"
    else:
        dataset = "zarr"

    # Create the mapping to organise the new dataset
    if dataset == "zarr":
        product_type = url.name[4:12]
        if simplified_mapping:
            with open ( SIMPL_MAPPING_PATH / MAPPINGS[product_type]) as f:
                map_safe = json.load(f)
        else:
            map_safe = convert_mapping(MAPPINGS[product_type])
        data_map = map_safe["data_mapping"]

    # if dataset=="netcdf" open dataset from nc file and return
    if dataset == "netcdf":
        return xr.open_dataset(product_urlpath / ncfile_or_zarrgroup)
            
    # else browse the selected nc files, open dataset and merge into a single one
    safe_ds = {}
    
    selected_files = [ f for f in files if f.name in data_map[ncfile_or_zarrgroup].keys()]
    
    for f in selected_files:
        if f.name.startswith("xfdumanifest"):
            continue
        safe_ds[f.name]  = xr.open_dataset(f,chunks=map_safe["chunk_sizes"])

    for grp in data_map:
        if grp != ncfile_or_zarrgroup:
            continue
        init=True
        for file in data_map[grp]:
            for var in data_map[grp][file]:
                array = safe_ds[file][var[0]]
                # print(array)
                # print(array.name,array.dims)
                if not init:
                    # Case where name of var is a dimension => automatically read as a coordinate
                    if array.name in array.dims:
                        continue
                    elif var[1] in ds.dims:
                        ds = ds.assign_coords({var[1]:array})
                        # print(f"{var[1]} is a coordinate")
                    else:
                        try:
                            ds=xr.merge([ds,array.rename(var[1])])
                        except ValueError as e:
                            print(e)
                            print(f"{file}:{grp}")# - {data_map[grp][file]}")
                            print(var[0],var[1])
                            raise(e)
                else:
                    ds = array.to_dataset(name=var[1])
                    init=False


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
    
