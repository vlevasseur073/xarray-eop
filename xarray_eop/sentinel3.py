import datatree
import json
import warnings
import xarray as xr

from collections import Counter
from itertools import count
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union, List

from xarray_eop.utils import convert_mapping
from xarray_eop.utils import MAPPINGS, SIMPL_MAPPING_PATH

EOP_TREE_STRUC=[
    "measurements",
    "conditions",
    "quality",
    ]


from collections import Counter
from itertools import count

def _modify_duplicate_elements(input_list):
    c = Counter(input_list)

    iters = {k: count(1) for k, v in c.items() if v > 1}
    output_list = [x+str(next(iters[x])) if x in iters else x for x in input_list]
    return output_list

def _create_dataset_from_ncfiles(
    input_list: List[Path],
    chunk_sizes: Dict[str,int]
    ) -> dict[str,xr.Dataset]:

    safe_ds = {}
    decode_times = True
    for f in input_list:
        if f.name.startswith("xfdumanifest"):
            continue
        # In xarray >2024, warning is added when opening a dataset in case of duplicate dimensions
        # (for instance a correlation matrix)
        # ValueError is raised when trying to chunk in such a case
        if f.name == "tg.nc":
            decode_times = False
        try:
            safe_ds[f.name]  = xr.open_dataset(f,chunks=chunk_sizes,decode_times=decode_times)
        except ValueError as e:
            safe_ds[f.name]  = xr.open_dataset(f,decode_times=decode_times)
            fixed = False
            for v in safe_ds[f.name]:
                array = safe_ds[f.name][v]
                if len(set(array.dims)) < len(array.dims):
                    new_dims = _modify_duplicate_elements(array.dims)
                    new_array = xr.DataArray(array.data,coords=array.coords,dims=new_dims)
                    safe_ds[f.name][v] = new_array
                    safe_ds[f.name] = safe_ds[f.name].chunk(chunk_sizes)
                    fixed=True
            if not fixed:
                print(e)
                raise ValueError

    return safe_ds

def _merge_dataset(
        safe_ds:dict[str,xr.Dataset],
        data_map:dict[str,Any],
        group:str
) -> xr.Dataset:
    if group not in data_map:
        print(f"{group} not found in data mapping")
        raise KeyError

    init=True
    for file in data_map[group]:
        # rename coordinates in safe_ds[file] if needed
        for var in data_map[group][file]:
            if var[0] in safe_ds[file].coords.keys() and var[1] != var[0]:
                safe_ds[file] = safe_ds[file].rename({var[0]:var[1]})
        for var in data_map[group][file]:
            try:
                array = safe_ds[file][var[0]]
            except:
                array = safe_ds[file][var[1]]
            # print(array)
            # print(array.name,array.dims)
            if not init:
                # Case where name of var is a dimension => automatically read as a coordinate
                if array.name in array.dims:
                    continue
                elif var[1] in ds.dims or var[1] in ds.coords.keys():
                    ds = ds.assign_coords({var[1]:array})
                    # print(f"{var[1]} is a coordinate")
                elif var[1] in ["latitude","longitude","time_stamp","x","y"]:
                    ds = ds.assign_coords({var[1]:array})
                else:
                    try:
                        ds=xr.merge([ds,array.rename(var[1])])
                    except ValueError as e:
                        print(e)
                        print(f"{file}:{group}")# - {data_map[group][file]}")
                        print(var[0],var[1])
                        raise(e)
            else:
                if var[1] in array.coords.keys():
                    ds = array.coords.to_dataset()
                elif  var[1] in ["latitude","longitude","time_stamp","x","y"]:
                    ds = xr.Dataset()
                    ds = ds.assign_coords({var[1]:array})
                else:
                    ds = array.to_dataset(name=var[1])
                init=False

    return ds


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

    chunk_sizes = {}
    data_map = {}
    
    # Create the mapping to organise the new dataset
    if dataset == "zarr":
        product_type = url.name[4:12]
        if simplified_mapping:
            with open ( SIMPL_MAPPING_PATH / MAPPINGS[product_type]) as f:
                map_safe = json.load(f)
        else:
            map_safe = convert_mapping(MAPPINGS[product_type])
        data_map = map_safe["data_mapping"]

        chunk_sizes = map_safe["chunk_sizes"] 
    
        selected_files = [ f for f in files if f.name in data_map[ncfile_or_zarrgroup].keys()]
    
    else:
        selected_files = [ product_urlpath / ncfile_or_zarrgroup ]

    # open dataset for each selecte files
    safe_ds = _create_dataset_from_ncfiles(selected_files,chunk_sizes)

    # merge the different dataset into a single one
    if dataset == "netcdf":
        return safe_ds[(product_urlpath / ncfile_or_zarrgroup).name]
    else:
        return _merge_dataset(safe_ds,data_map,ncfile_or_zarrgroup)


def open_safe_datatree(
    name: str,
    product_urlpath: Union[str,Path],
    simplified_mapping: Optional[bool] = False
)->datatree.DataTree:

    if isinstance(product_urlpath,str):
        url = Path(product_urlpath)
    else:
        url = product_urlpath
    files = [f for f in url.iterdir() if f.is_file()]

    product_type = url.name[4:12]
    if simplified_mapping:
        with open ( SIMPL_MAPPING_PATH / MAPPINGS[product_type]) as f:
            map_safe = json.load(f)
    else:
        map_safe = convert_mapping(MAPPINGS[product_type])
    data_map = map_safe["data_mapping"]
    chunk_sizes = map_safe["chunk_sizes"]

    # open dataset for each selecte files
    safe_ds = _create_dataset_from_ncfiles(files,chunk_sizes)
    
    
    # dt_struct = {n:datatree.DataTree(name=n) for n in EOP_TREE_STRUC}
    # dt = datatree.DataTree(name=name,children=dt_struct)
    # for grp,ds in safe_ds.items():
    #     dt[grp] = ds
    
    eop_ds = {}
    for grp_path in data_map:
        eop_ds[grp_path] = _merge_dataset(safe_ds,data_map,grp_path)

    dt = datatree.DataTree.from_dict(eop_ds)
    
    
    # for grp_path,grp_files in data_map.items():
    #     ds =  xr.open_dataset(chunks=map_safe["chunk_sizes"])
    #     for files in grp_files:

    return dt
    # return safe_ds

    