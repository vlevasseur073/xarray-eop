import json
import tempfile
import warnings
from collections import Counter
from itertools import count
from pathlib import Path
from typing import Any, Literal, Tuple

import datatree
import s3fs
import xarray as xr

from xarray_eop.conversion.utils import (
    MAPPINGS,
    SIMPL_MAPPING_PATH,
    convert_mapping,
    use_custom_mapping,
)
from xarray_eop.path import EOPath

EOP_TREE_STRUC = [
    "measurements",
    "conditions",
    "quality",
]


def _modify_duplicate_elements(input_list: tuple[Any, ...]) -> list[str]:
    c = Counter(input_list)

    iters = {k: count(1) for k, v in c.items() if v > 1}
    output_list = [x + str(next(iters[x])) if x in iters else x for x in input_list]
    return output_list


def _fix_dataset(
    url: EOPath,
    ds: dict[str, xr.Dataset],
    key: str,
    chunk_sizes: dict[str, int] | None = None,
    fs: s3fs.S3FileSystem = None,
    decode_times: bool = True,
    **kwargs: Any,
) -> bool:
    if url.protocol and url.protocol != "s3":
        print(f"Error, {url.protocol} protocol not implemented yet")
        exit(0)
    cloud_storage: bool = url.protocol == "s3"
    if cloud_storage and fs:
        fileObj = fs.open(url.as_posix())
    else:
        fileObj = url
    ds[key] = xr.open_dataset(
        fileObj,
        decode_times=decode_times,
        engine="h5netcdf",
        **kwargs,
    )

    fixed = False
    for v in ds[key]:
        array = ds[key][v]
        if len(set(array.dims)) < len(array.dims):
            new_dims = _modify_duplicate_elements(array.dims)
            ds[key] = xr.open_dataset(
                fileObj,
                decode_times=decode_times,
                engine="h5netcdf",
                **kwargs,
            )
            new_array = xr.DataArray(array.data, coords=array.coords, dims=new_dims)
            ds[key][v] = new_array
            ds[key] = ds[key].chunk(chunk_sizes)
            fixed = True

    if cloud_storage:
        fileObj.close()

    return fixed


def _create_dataset_from_ncfiles(
    input_list: list[EOPath],
    chunk_sizes: dict[str, int] | None,
    storage_options: dict[str, Any] | None = None,
    decode_times: bool = True,
    **kwargs: Any,
) -> dict[str, xr.Dataset]:

    safe_ds = {}
    for f in input_list:
        if f.name.startswith("xfdumanifest"):
            continue
        if f.name in ["tg.nc", "met_tx.nc"]:
            decode_times = False
        if f.protocol == "s3":
            fs = _get_s3filesystem_from_storage_options(storage_options)
            try:
                with fs.open(f.as_posix()) as fileObj:
                    safe_ds[f.name] = xr.open_dataset(
                        fileObj,
                        chunks=chunk_sizes,
                        decode_times=decode_times,
                        engine="h5netcdf",
                        **kwargs,
                    )
                    safe_ds[f.name] = safe_ds[f.name].compute()
                safe_ds[f.name] = safe_ds[f.name].chunk(chunk_sizes)
            except ValueError as e:
                fixed = _fix_dataset(
                    f,
                    safe_ds,
                    f.name,
                    chunk_sizes=chunk_sizes,
                    decode_times=decode_times,
                    fs=fs,
                    **kwargs,
                )
                if not fixed:
                    print(e)
                    raise ValueError
        else:
            try:
                # In xarray >2024, warning is added when opening a dataset in case of duplicate dimensions
                # (for instance a correlation matrix)
                # ValueError is raised when trying to chunk in such a case
                safe_ds[f.name] = xr.open_dataset(
                    f,
                    chunks=chunk_sizes,
                    decode_times=decode_times,
                    engine="h5netcdf",
                    **kwargs,
                )
            except ValueError as e:
                fixed = _fix_dataset(
                    f,
                    safe_ds,
                    f.name,
                    chunk_sizes=chunk_sizes,
                    decode_times=decode_times,
                    **kwargs,
                )
                if not fixed:
                    print(e)
                    raise ValueError

    return safe_ds


def _merge_dataset(
    safe_ds: dict[str, xr.Dataset],
    data_map: dict[str, Any],
    group: str | EOPath,
) -> xr.Dataset:
    if group not in data_map:
        print(f"{group} not found in data mapping")
        raise KeyError

    init = True
    ds: xr.Dataset
    grp = str(group)
    for file in data_map[grp]:
        # rename coordinates in safe_ds[file] if needed
        for var in data_map[grp][file]:
            if var[0] in safe_ds[file].coords.keys() and var[1] != var[0]:
                safe_ds[file] = safe_ds[file].rename({var[0]: var[1]})
        for var in data_map[grp][file]:
            try:
                array = safe_ds[file][var[0]]
            except:  # noqa: E722
                array = safe_ds[file][var[1]]
            # print(array)
            # print(array.name,array.dims)
            if not init:
                # Case where name of var is a dimension => automatically read as a coordinate
                if array.name in array.dims:
                    continue
                elif var[1] in ds.dims or var[1] in ds.coords.keys():  # noqa: F821
                    ds = ds.assign_coords({var[1]: array})  # noqa: F821
                    # print(f"{var[1]} is a coordinate")
                elif var[1] in ["latitude", "longitude", "time_stamp", "x", "y"]:
                    ds = ds.assign_coords({var[1]: array})
                else:
                    try:
                        ds = xr.merge([ds, array.rename(var[1])])
                    except ValueError as e:
                        print(e)
                        print(f"{file}:{grp}")  # - {data_map[group][file]}")
                        print(var[0], var[1])
                        raise (e)
            else:
                if var[1] in array.coords.keys():
                    ds = array.coords.to_dataset()
                elif var[1] in ["latitude", "longitude", "time_stamp", "x", "y"]:
                    ds = xr.Dataset()
                    ds = ds.assign_coords({var[1]: array})
                else:
                    ds = array.to_dataset(name=var[1])
                init = False

    return ds


def _get_s3filesystem_from_storage_options(
    storage_options: dict[str, Any] | None = None,
) -> s3fs.S3FileSystem:
    if storage_options is None:
        return s3fs.S3FileSystem(anon=True)
    else:
        try:
            endpoint_url = storage_options["s3"]["endpoint_url"]
        except KeyError:
            endpoint_url = storage_options["s3"]["client_kwargs"]["endpoint_url"]
        return s3fs.S3FileSystem(
            key=storage_options["s3"]["key"],
            secret=storage_options["s3"]["secret"],
            endpoint_url=endpoint_url,
        )


def _get_info_from_sentinel3_legacy_product_path(
    product_urlpath: str | Path | EOPath,
    storage_options: dict[str, Any] | None = None,
    fs_copy: bool | None = None,
) -> tuple[EOPath, str, list[str | Path], tempfile.TemporaryDirectory[Any] | None]:
    """ "Get some information given a path

    Returns
    -------
    tuple:
     - url: str | Path : full url
     - product_type: str
     - files: list of all files in the product
     - is_cloud_path: boolean
    """
    url: EOPath = EOPath(product_urlpath)
    product_type: str
    files: list[EOPath]
    temp_path: tempfile.TemporaryDirectory[Any] | None = None

    if url.protocol == "s3":
        fs = _get_s3filesystem_from_storage_options(storage_options)
        if fs_copy:
            temp_path = tempfile.TemporaryDirectory(prefix="stb_")
            # fs.get(product_urlpath.rstrip("/"), temp_path.name, recursive=True)
            # url = EOPath("/".join([temp_path.name, product_urlpath.rstrip("/").split("/")[-1]]))
            fs.get(url.as_posix(), temp_path.name, recursive=True)
            url = EOPath("/".join([temp_path.name, url.name]))
            product_type = url.name[4:12]
            files = [f for f in url.iterdir() if f.is_file()]
        else:
            product_type = url.name[4:12]
            files = [EOPath(f"s3://{f}") for f in fs.glob((url / "*").as_posix())]

    else:
        url = EOPath(product_urlpath)
        product_type = url.name[4:12]
        files = [f for f in url.iterdir() if f.is_file()]

    return url, product_type, files, temp_path


def _get_data_mapping(
    dataset: Literal["eogroup", "netcdf"],
    url: EOPath,
    product_type: str,
    files: list[EOPath],
    ncfile_or_eogroup: str | None = None,
    simplified_mapping: bool | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[EOPath]]:
    data_map = {}
    chunk_sizes = {}
    if dataset == "eogroup":
        if simplified_mapping is None:
            simplified_mapping = use_custom_mapping(url)

        if simplified_mapping:
            mapfile = SIMPL_MAPPING_PATH / MAPPINGS[product_type]
            with mapfile.open() as f:
                map_safe = json.load(f)
        else:
            map_safe = convert_mapping(MAPPINGS[product_type])
        data_map = map_safe["data_mapping"]

        chunk_sizes = map_safe["chunk_sizes"]

        if ncfile_or_eogroup is None:
            selected_files = files
        else:
            selected_files = [
                f for f in files if f.name in data_map[ncfile_or_eogroup].keys()
            ]
    else:
        if ncfile_or_eogroup is None:
            selected_files = [url]
        else:
            ncfile_path: EOPath = url / ncfile_or_eogroup
            selected_files = [ncfile_path]

    return data_map, chunk_sizes, selected_files


def open_sentinel3_dataset(
    product_urlpath: str | Path,
    ncfile_or_eogroup: str | Path,
    *,
    drop_variables: Tuple[str] | None = None,
    storage_options: dict[str, Any] | None = None,
    simplified_mapping: bool | None = None,
    fs_copy: bool | None = None,
) -> xr.Dataset:
    if drop_variables is not None:
        warnings.warn("'drop_variables' is currently ignored")

    if fs_copy is not None and not str(product_urlpath).startswith("s3://"):
        warnings.warn("Option fs_copy is only valid with product url on S3 bucket")
        warnings.warn("Ignoring fs_copy")
        fs_copy = None

    if str(product_urlpath).startswith("s3://") and fs_copy is None:
        fs_copy = False

    temp_path: tempfile.TemporaryDirectory[Any] | None = None
    url, product_type, files, temp_path = _get_info_from_sentinel3_legacy_product_path(
        product_urlpath,
        storage_options=storage_options,
        fs_copy=fs_copy,
    )
    # check the ncfile or eogroup
    dataset: Literal["netcdf", "eogroup"]
    if str(ncfile_or_eogroup).endswith(".nc"):
        dataset = "netcdf"
    else:
        dataset = "eogroup"

    # Create the mapping to organise the new dataset
    chunk_sizes: dict[str, Any] | None
    data_map, chunk_sizes, selected_files = _get_data_mapping(
        dataset,
        url,
        product_type,
        files,
        ncfile_or_eogroup=str(ncfile_or_eogroup),
        simplified_mapping=simplified_mapping,
    )

    if fs_copy is False:
        chunk_sizes = {}

    # open dataset for each selecte files
    safe_ds = _create_dataset_from_ncfiles(
        selected_files,
        chunk_sizes,
        storage_options=storage_options,
    )

    if temp_path:
        temp_path.cleanup()
    # merge the different dataset into a single one
    if dataset == "netcdf":
        return safe_ds[str(ncfile_or_eogroup)]
    else:
        return _merge_dataset(safe_ds, data_map, ncfile_or_eogroup)


def open_safe_datatree(
    product_urlpath: EOPath,
    simplified_mapping: bool | None = None,
    fs_copy: bool | None = None,
    **kwargs: Any,
) -> datatree.DataTree[Any]:
    """Opens a Sentinel-3 SAFE product as a full datatree

    Parameters
    ----------
    name: str
        Name of the datatree product
    product_urlpath: str, Path
        Path in the filesystem to the product to be opened.
    simplified_mapping, optional
        Use a custom simplified mapping, by default it is set given the product type
    fs_copy: bool
        when data is stored in the cloud, lazy loading requires to copy the product on the local filesystem.
        If data cannot be copied locally, it will be fully loaded in memory. Default, fs_copy=False

    Returns
    -------
        datatree.DataTree
    """
    storage_options = None
    if "backend_kwargs" in kwargs:
        if "storage_options" in kwargs["backend_kwargs"]:
            storage_options = kwargs["backend_kwargs"]["storage_options"]

    if fs_copy is not None and not str(product_urlpath).startswith("s3://"):
        warnings.warn("Option fs_copy is only valid with product url on S3 bucket")
        warnings.warn("Ignoring fs_copy")
        fs_copy = None

    if product_urlpath.protocol == "s3" and fs_copy is None:
        fs_copy = False

    temp_path: tempfile.TemporaryDirectory[Any] | None = None
    url, product_type, files, temp_path = _get_info_from_sentinel3_legacy_product_path(
        product_urlpath,
        storage_options=storage_options,
        fs_copy=fs_copy,
    )
    # Create the mapping to organise the new dataset
    chunk_sizes: dict[str, Any] | None
    data_map, chunk_sizes, selected_files = _get_data_mapping(
        "eogroup",
        url,
        product_type,
        files,
        simplified_mapping=simplified_mapping,
    )

    if fs_copy is False:
        chunk_sizes = {}

    # open dataset for each selecte files
    safe_ds = _create_dataset_from_ncfiles(
        selected_files,
        chunk_sizes,
        storage_options=storage_options,
        decode_times=kwargs["decode_times"] if "decode_times" in kwargs else True,
    )

    eop_ds = {}
    for grp_path in data_map:
        eop_ds[grp_path] = _merge_dataset(safe_ds, data_map, grp_path)

    dt = datatree.DataTree.from_dict(eop_ds)

    if temp_path:
        temp_path.cleanup()
    return dt
