import importlib.resources
import json
import re
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

import dask.array as da
import datatree
import numpy as np
import xarray as xr
import zarr
from numcodecs import Blosc

from xarray_eop.path import EOPath

default_alg = "zstd"
default_comp = 3
default_shuffle = Blosc.BITSHUFFLE
DEFAULT_COMPRESSOR = Blosc(
    cname=default_alg,
    clevel=default_comp,
    shuffle=default_shuffle,
)

MAPPING_PATH = importlib.resources.files("xarray_eop.conversion.conf") / "mappings"
SIMPL_MAPPING_PATH = (
    importlib.resources.files("xarray_eop.conversion.conf") / "simplified_mappings"
)
REMAPPING_FILE = MAPPING_PATH / "remap.json"

MAPPINGS = {
    "OL_1_EFR": "S3_OL_1_mapping.json",
    "OL_1_ERR": "S3OLCERR_mapping.json",
    "OL_2_LFR": "S3_OL_2_mapping.json",
    "SL_1_RBT": "S3_SL_1_RBT_mapping.json",
    "SL_2_LST": "S3_SL_2_LST_mapping.json",
    "SL_2_FRP": "S3SLSFRP_mapping.json",
    "SY_2_SYN": "S3_SY_2_SYN_mapping.json",
    "SY_2_AOD": "S3SYNAOD_mapping.json",
    "SY_2_VGK": "S3SYNVGK_mapping.json",
    "SY_2_VGP": "S3SYNVGP_mapping.json",
    "SY_2_VG1": "S3SYNVG1_mapping.json",
    "SY_2_V10": "S3SYNV10_mapping.json",
}


def use_custom_mapping(product: EOPath | Path | str) -> bool:
    custom_map = False
    if isinstance(product, Path) or isinstance(product, EOPath):
        pattern = product.name[4:12]
    elif isinstance(product, str):
        pattern = product.rstrip("/").split("/")[-1][4:12]
    if pattern in [
        "OL_1_EFR",
        "OL_1_ERR",
        "OL_2_LFR",
        "SY_2_AOD",
        "SY_2_VGP",
        "SY_2_VGK",
        "SY_2_VG1",
        "SY_2_V10",
    ]:
        custom_map = True

    return custom_map


def lower(v: str | float | int) -> str | float | int:
    if isinstance(v, str):
        return v.lower()
    else:
        return v


def str_to_number(s: str) -> Any:
    try:
        vi = int(s)
        return (vi, str(np.dtype(type(vi))))
    except ValueError:
        try:
            vf: float = float(s)
            return (vf, str(np.dtype(type(vf))))
        except ValueError:
            try:
                v_list = s.split(",")

                v = []
                for l in v_list:  # noqa: E741
                    t = str_to_number(l)
                    if t is None:
                        return None
                    else:
                        v.append(t[0])
                return (v, str(np.dtype(type(v[0]))))
            except:  # noqa: E722
                return None


def gen_static_adf_name(
    sat: str,
    pattern: str,
    start: str | None = None,
    stop: str | None = None,
    format: str = "zarr",
) -> str:
    """Generate a static ADF name"""
    now = datetime.now()
    date_frmt = now.strftime("%Y%m%dT%H%M%S")

    if not start:
        if sat == "S3B":
            start = "20180425T000000"
        else:
            start = "20160216T000000"
    if not stop:
        stop = "20991231T235959"

    adf_name = "_".join([sat, "ADF", pattern, start, stop, date_frmt])

    return f"{adf_name}.{format}"


def extract_all_files(tar_file: str, extract_to: str | Path) -> None:
    with tarfile.open(tar_file, "r") as tar:
        tar.extractall(extract_to)


def extract_legacy(
    input_path: str | Path,
    legacy_adf: str,
    output_path: str | Path | None = None,
) -> Path:
    if isinstance(input_path, str):
        input_path = Path(input_path)
    # Loop to find the legacy ADF
    for in_tarball in input_path.glob(legacy_adf + "*.SEN3.tgz"):
        if output_path:
            temp = Path(output_path)
        else:
            temp = Path("/tmp")
        adf_name = in_tarball.with_suffix("").name
        if temp / adf_name not in temp.iterdir():
            extract_all_files(in_tarball, str(temp))
            (temp / adf_name).chmod(0o777)

    return temp / adf_name


def variable_to_attr(da: xr.DataArray, enabled_attr: list[Any] = []) -> dict[str, Any]:
    if da.data.size == 1:
        var_attr = {"type": da.dtype.name, "value": da.data.item()}
    else:
        var_attr = {"type": da.dtype.name, "value": [f for f in da.values.flatten()]}
    for at in da.attrs:
        if enabled_attr and at not in enabled_attr:
            continue
        at_orig = da.attrs[at]
        if isinstance(at_orig, str):
            at_orig = at_orig.lower()
        var_attr[at.lower()] = at_orig

    return var_attr


def generate_datatree_from_legacy_adf(
    safe: Path,
    title: str = "",
    safe_file: list[str] = None,
    group: (
        str | None
    ) = None,  # if group=None, by default subgroup maps is created if group=="" no subgroup
    ncgroup: str | None = None,
    merged_variables: list[Any] = [],
    merged_mapping: dict[str, Any] = {},
    # files_to_group: Optional[dict] = {},
    coordinates_variable: list[Any] = [],  # variable : (dimension,coordinate)
    var_to_attr: dict[str, Any] = {},
    dt: datatree.DataTree[Any] | None = None,
) -> datatree.DataTree[Any]:

    if group and ncgroup:
        print("Error, cannot specify group and ncgroup")
        exit(0)

    if dt is None and group != "":
        dt = datatree.DataTree(name="root_adf")

    for nc_file in safe.glob("*.nc*"):
        if safe_file and nc_file.name not in safe_file:
            continue
        try:
            ds = xr.open_dataset(nc_file, chunks={}, group=ncgroup)
        except ValueError:
            ds = xr.open_dataset(nc_file, chunks={}, group=ncgroup, decode_times=False)

        ds = ds.rename({c: c.lower() for c in ds.coords})
        ds = ds.rename({v: v.lower() for v in ds.data_vars})

        ds_new = xr.Dataset()
        coords = set()

        # Loop over variables which are not coordinates, not to be merged
        for var in ds.variables:
            if var in merged_variables:
                continue
            if var in ds.coords:
                coords.add(var.lower())
                continue

            # if variable is scalar, put it in attribute
            if not ds[var].shape:
                ds_new.attrs[ds[var].name.lower()] = variable_to_attr(ds[var])
            elif var in var_to_attr:
                enabled_attr = var_to_attr[var]
                ds_new.attrs[ds[var].name.lower()] = variable_to_attr(
                    ds[var],
                    enabled_attr=enabled_attr,
                )
            else:
                # print(ds[var].rename({c:c.lower() for c in ds[var].coords}))
                arr = xr.DataArray(
                    ds[var],
                    name=var.lower(),
                    # coords=ds[var].rename({c:c.lower() for c in ds[var].coords}).coords,
                    coords=ds[var].coords,
                    dims=[d.lower() for d in ds[var].dims],
                    attrs=ds[var].attrs,  # [a.lower() for a in ds[var].attrs]
                )
                arr.encoding["compressor"] = DEFAULT_COMPRESSOR
                ds_new = xr.merge([ds_new, arr])

        # Verify if a coord has really been used
        for c in coords:
            if c not in ds_new.coords:
                if c in var_to_attr:
                    print(f"Warning coords {c} not used. It is set as an attribute")
                    enabled_attr = var_to_attr[c]
                    ds_new.attrs[ds[c].name.lower()] = variable_to_attr(
                        ds[c],
                        enabled_attr=enabled_attr,
                    )
                else:
                    print(f"Warning coords {c} not used. It is kept anyway")
                    ds_new = ds_new.assign_coords({c: ds.coords[c]})

        # Add specific coordinates if not automatic
        for var in coordinates_variable:
            (dim, coord) = coordinates_variable[var]
            if coord not in ds_new[var].coords:
                print(f"Add specific coordinates {coord} to variable {var}")
                if coord not in ds_new.variables:
                    print(
                        f"Impossible to add specific coordinates {coord} to variable {var}",
                    )
                    print("The coordinate has not yet been defined as a variable")
                    exit(0)
                ds_new = ds_new.assign_coords({coord: ds_new[coord]})
                ds_new = ds_new.rename({dim: coord})

        # Loop over variables to be merged
        for var in merged_mapping:
            merged_vars = merged_mapping[var][0]

            axis = len(ds[merged_vars[0]].dims)
            data = da.stack([ds[f] for f in merged_vars], axis=axis)
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
                attrs=attrs,
            ).rename(var)
            arr.encoding["compressor"] = DEFAULT_COMPRESSOR

            ds_new = xr.merge([ds_new, arr])

        group_name = "maps"
        if group == "":
            dt = datatree.DataTree(name="root", data=ds_new)
        else:
            if ncgroup:
                group_name = ncgroup.lower()
            elif group:
                group_name = group
            datatree.DataTree(name=group_name, parent=dt, data=ds_new)
        if group or ncgroup:
            for k, v in ds.attrs.items():
                dt[group_name].attrs[k.lower()] = lower(v)
            dt[group_name].attrs["baseline collection"] = safe.name[-8:-5]
            dt[group_name].attrs["title"] = title
        else:
            dt.attrs.update({k.lower(): lower(v) for k, v in ds.attrs.items()})
            dt.attrs["baseline collection"] = safe.name[-8:-5]
            dt.attrs["title"] = title

    return dt


def get_simplified_mapping():
    """Generates a simplified mapping from EOPF mapping
    The resulting file is store under conf/simplified_mappings/ref
    """

    for _, mapping in MAPPINGS.items():
        print("Convert ", mapping)
        ds = convert_mapping(mapping)

        with open(
            str(SIMPL_MAPPING_PATH / "ref" / mapping), "w", encoding="utf-8"
        ) as f:
            json.dump(ds, f, indent=4)


def convert_mapping(mapping_file: str) -> dict[str, dict[str, tuple[str, str]]]:
    """Convert original EOPF mapping into a simplified mapping, applying a configurable remapping
    Returns a dictionary of the mapping data
    """
    with open(str(MAPPING_PATH / mapping_file)) as f:
        eopf_mapping = json.load(f)

    new_mapping = {"chunk_sizes": eopf_mapping["chunk_sizes"]}
    data_map = new_mapping["data_mapping"] = {}
    for map in eopf_mapping["data_mapping"]:
        if map["item_format"] == "netcdf-dimension":
            continue
        src: str = map["source_path"]
        dest: str = map["target_path"]

        if not (src and dest):
            continue
        if src.startswith("xfdumanifest"):
            continue

        # Check for any specific remapping
        if REMAPPING_FILE.is_file():
            with open(str(REMAPPING_FILE)) as rf:
                remap = json.load(rf)
            if mapping_file in remap:
                # if dest in remap[mapping_file]:
                #     dest = remap[mapping_file][dest]
                for d in remap[mapping_file]:
                    r = re.search(d, dest)
                    if r:
                        if r.re.pattern == dest:
                            dest = remap[mapping_file][dest]
                        else:
                            v = dest.split("/")[-1]
                            dest = remap[mapping_file][d]
                            l = dest.split("/")[:-1]  # noqa: E741
                            l.append(v)
                            dest = "/".join(l)
        if not dest:
            continue

        try:
            file = src.split(":")[0]
            var = src.split(":")[1]
        except IndexError:
            print(f"Error in src path: {src}")
            print(map)
            raise (IndexError)

        group = str(Path(dest).parents[0])
        variable = str(Path(dest).name)

        if "coordinates" in group:  # and variable not in ["latitude","longitude"]:
            group = group.replace("coordinates", "conditions")

        if group not in data_map:
            data_map[group] = {}

        if file not in data_map[group]:
            data_map[group][file] = []
        data_map[group][file].append((var, variable))

    return new_mapping
