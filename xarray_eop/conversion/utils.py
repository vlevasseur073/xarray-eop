import dask.array as da
import datatree
from datetime import datetime
from numcodecs import Blosc
import numpy as np
from pathlib import Path
import tarfile
from typing import Optional, Union
import xarray as xr

default_alg = "zstd"
default_comp = 3
default_shuffle = Blosc.BITSHUFFLE
DEFAULT_COMPRESSOR = Blosc(cname=default_alg, clevel=default_comp, shuffle=default_shuffle)

def lower(v:Union[str,float,int]):
    if isinstance(v,str):
        return v.lower()
    else:
        return v
    
def str_to_number(s):
    try:
        v = int(s)
        return (v, str(np.dtype(type(v))))
    except ValueError:
        try:
            v = float(s)
            return (v, str(np.dtype(type(v))))
        except ValueError:
            try:
                v_list = s.split(",")

                v = []
                for l in v_list:
                    t = str_to_number(l)
                    if t is None:
                        return None
                    else:
                        v.append(t[0])
                return (v, str(np.dtype(type(v[0]))))
            except:
                return None
            
def gen_static_adf_name(
    sat: str,
    pattern: str,
    start: Optional[str] = None,
    stop: Optional[str] = None,
    format="zarr",
):
    now = datetime.now()
    date_frmt = now.strftime("%Y%m%dT%H%M%S")
    
    if not start:
        if sat == "S3B":
            start = "20180425T000000"
        else:
            start = "20160216T000000"
    if not stop:
        stop = "20991231T235959"
        
    adf_name = "_".join([
        sat,
        "ADF",
        pattern,
        start,
        stop,
        date_frmt
        ]
    )
    
    return f"{adf_name}.{format}"

def extract_all_files(
        tar_file: str,
        extract_to: Union[str,Path]
):
    with tarfile.open(tar_file, "r") as tar:
        tar.extractall(extract_to)

def extract_legacy(
        input_path: Union[str,Path],
        legacy_adf: str,
        output_path: Optional[Union[str,Path]]
) -> Path:
    # Loop to find the legacy ADF
    for in_tarball in input_path.glob(legacy_adf+"*.SEN3.tgz"):
        if output_path:
            temp = Path(output_path)
        else:
            temp = Path('/tmp')
        adf_name = in_tarball.with_suffix('').name
        if temp / adf_name not in temp.iterdir():
            extract_all_files(in_tarball,str(temp))
            (temp / adf_name).chmod(0o777)
    
    return temp / adf_name

def variable_to_attr(
        da:xr.DataArray,
        enabled_attr:Optional[list]=[]
) -> dict:
    if da.data.size == 1:
        var_attr = {
            "type": da.dtype.name,
            "value": da.data.item()
        }
    else:
        var_attr = {
            "type": da.dtype.name,
            "value": [f for f in da.values.flatten()]
        }
    for at in da.attrs:
        if enabled_attr and at not in enabled_attr:
            continue
        at_orig = da.attrs[at]
        if isinstance(at_orig,str):
            at_orig = at_orig.lower()
        var_attr[at.lower()] = at_orig
    
    return var_attr

def generate_datatree_from_legacy_adf(
        safe: Path,
        title: Optional[str] = "",
        safe_file: Optional[list] = None,
        group: Optional[str] = None, # if group=None, by default subgroup maps is created if group=="" no subgroup
        ncgroup: Optional[str] = None,
        merged_variables: Optional[list] = [],
        merged_mapping: Optional[dict] = {},
        # files_to_group: Optional[dict] = {},
        coordinates_variable: Optional[list] = [], # variable : (dimension,coordinate)
        var_to_attr: Optional[dict] ={},
        dt:Optional[datatree.DataTree] = None,
) -> datatree.DataTree:
    
    if group and ncgroup:
        print("Error, cannot specify group and ncgroup")
        exit(0)

    if dt is None and group != "":
        dt = datatree.DataTree(name="root_adf")
    
    for nc_file in safe.glob("*.nc*"):
        if safe_file and nc_file.name not in safe_file:
            continue
        try:
            ds = xr.open_dataset(nc_file,chunks={},group=ncgroup)
        except ValueError:
            ds = xr.open_dataset(nc_file,chunks={},group=ncgroup,decode_times=False)
        
        ds=ds.rename({c:c.lower() for c in ds.coords})
        ds=ds.rename({v:v.lower() for v in ds.data_vars})

        ds_new = xr.Dataset()
        coords = set()

        # Loop over variables which are not coordinates, not to be merged
        for var in ds.variables:
            if var in merged_variables:
                continue
            if  var in ds.coords:
                coords.add(var.lower())
                continue
            
            # if variable is scalar, put it in attribute
            if not ds[var].shape:
                ds_new.attrs[ds[var].name.lower()] = variable_to_attr(ds[var])
            elif var in var_to_attr:
                enabled_attr = var_to_attr[var]
                ds_new.attrs[ds[var].name.lower()] = variable_to_attr(ds[var],enabled_attr=enabled_attr)
            else:
                # print(ds[var].rename({c:c.lower() for c in ds[var].coords}))
                arr = xr.DataArray(
                    ds[var],
                    name=var.lower(),
                    # coords=ds[var].rename({c:c.lower() for c in ds[var].coords}).coords,
                    coords=ds[var].coords,
                    dims=[d.lower() for d in ds[var].dims],
                    attrs=ds[var].attrs#[a.lower() for a in ds[var].attrs]
                )
                arr.encoding["compressor"] = DEFAULT_COMPRESSOR
                ds_new = xr.merge([ds_new,arr])

        # Verify if a coord has really been used
        for c in coords:
            if c not in ds_new.coords:
                if c in var_to_attr:
                    print(f"Warning coords {c} not used. It is set as an attribute")
                    enabled_attr = var_to_attr[c]
                    ds_new.attrs[ds[c].name.lower()] = variable_to_attr(ds[c],enabled_attr=enabled_attr)
                else:
                    print(f"Warning coords {c} not used. It is kept anyway")
                    ds_new = ds_new.assign_coords({c:ds.coords[c]})

        # Add specific coordinates if not automatic
        for var in coordinates_variable:
            (dim,coord) = coordinates_variable[var]
            if coord not in ds_new[var].coords:
                print(f"Add specific coordinates {coord} to variable {var}")
                if coord not in ds_new.variables:
                    print(f"Impossible to add specific coordinates {coord} to variable {var}")
                    print("The coordinate has not yet been defined as a variable")
                    exit(0)
                ds_new = ds_new.assign_coords({coord:ds_new[coord]})
                ds_new = ds_new.rename({dim:coord})

        # Loop over variables to be merged
        for var in merged_mapping:
            merged_vars = merged_mapping[var][0]
            
            axis = len(ds[merged_vars[0]].dims)
            data = da.stack([ds[f] for f in merged_vars],axis=axis)
            data = da.rechunk(data)

            coords = ds[merged_vars[0]].coords
            dims = ds[merged_vars[0]].dims
            dims_ext = dims + (merged_mapping[var][1],)
            # print(dims_ext)
            attrs = merged_mapping[var][2]
            
            arr = xr.DataArray(
                data,
                coords=ds[merged_vars[0]].coords,
                dims=dims_ext,
                attrs=attrs
            ).rename(var)
            arr.encoding["compressor"] = DEFAULT_COMPRESSOR

            ds_new = xr.merge([ds_new,arr])

        
        group_name = "maps"
        if group == "":
            dt=datatree.DataTree(
                    name="root",
                    data=ds_new
            )
        else:
            if ncgroup:
                group_name=ncgroup.lower()
            elif group:
                group_name=group
            datatree.DataTree(
                    name=group_name,
                    parent=dt,
                    data=ds_new
            )
        if group or ncgroup:
            for k,v in ds.attrs.items():
                dt[group_name].attrs[k.lower()] = lower(v)
            dt[group_name].attrs["baseline collection"] = safe.name[-8:-5]
            dt[group_name].attrs["title"] = title
        else:
            dt.attrs.update({k.lower():lower(v) for k,v in ds.attrs.items()})
            dt.attrs["baseline collection"] = safe.name[-8:-5]
            dt.attrs["title"] = title


    return dt