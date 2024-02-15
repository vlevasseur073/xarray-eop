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

    if dataset == "netcdf":
        return xr.open_dataset(product_urlpath / ncfile_or_zarrgroup)
            
    safe_ds = {}
    
    selected_files = [ f for f in files if f.name in map_safe[ncfile_or_zarrgroup].keys()]
    
    for f in selected_files:
        if f.name.startswith("xfdumanifest"):
            continue
        safe_ds[f.name]  = xr.open_dataset(f)

    for grp in map_safe:
        if grp != ncfile_or_zarrgroup:
            continue
        init=True
        for file in map_safe[grp]:
            for var in map_safe[grp][file]:
                array = safe_ds[file][var[0]]
                if not init:
                    if var[1] in ds.dims:
                        ds = ds.assign_coords({var[1]:array})
                    else:
                        ds=xr.merge([ds,array.rename(var[1])])
                else:
                    ds = array.to_dataset(name=var[1])
                    init=False


    return ds
    
