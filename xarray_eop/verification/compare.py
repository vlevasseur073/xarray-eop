# Copyright 2024 ACRI-ST
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Any

import datatree
import numpy as np
import pandas as pd
import xarray as xr

from xarray_eop import EOPath, get_s3filesystem


# Formatted string when test fails
def _get_failed_formatted_string_vars(
    name: str,
    values: list[Any],
    threshold: float,
    relative: bool = True,
) -> str:
    if relative:
        return (
            f"{name}: "
            f"min={values[0]*100:8.4f}%, "
            f"max={values[1]*100:8.4f}%, "
            f"mean={values[2]*100:8.4f}%, "
            f"stdev={values[3]*100:8.4f}% -- "
            f"eps={threshold*100}% "
            f"outliers={values[4]} ({values[4]/values[-2]*100:5.2f}%) "
            f"samples={values[-2]}/{values[-1]}({values[-2]/values[-1]*100:5.2f}%)"
        )
    else:
        return (
            f"{name}: "
            f"min={values[0]:9.6f}, "
            f"max={values[1]:9.6f}, "
            f"mean={values[2]:9.6f}, "
            f"stdev={values[3]:9.6f} -- "
            f"eps={threshold} "
            f"outliers={values[4]} ({values[4]/values[-2]*100:5.2f}%) "
            f"samples={values[-2]}/{values[-1]}({values[-2]/values[-1]*100:5.2f}%)"
        )


def _get_failed_formatted_string_flags(
    name: str,
    ds: xr.Dataset,
    bit: int,
    eps: float,
) -> str:
    return (
        f"{name} ({ds.bit_position.data[bit]})({ds.bit_meaning.data[bit]}): "
        f"equal_pix={ds.equal_percentage.data[bit]:8.4f}%, "
        f"diff_pix={ds.different_percentage.data[bit]:8.4f}% -- "
        f"eps={eps:8.4f}% "
        f"outliers={ds.different_count.data[bit]} "
        f"samples=({ds.total_bits.data[bit]})"
    )


def _get_passed_formatted_string_flags(name: str, ds: xr.Dataset, bit: int) -> str:
    return f"{name} ({ds.bit_position.data[bit]})({ds.bit_meaning.data[bit]})"


# Function to get leaf paths
def get_leaf_paths(paths: list[str]) -> list[str]:
    """Given a list of tree paths, returns leave paths

    Parameters
    ----------
    paths
        list of tree structure path

    Returns
    -------
        leaf paths
    """
    leaf_paths = []
    for i in range(len(paths)):
        if i == len(paths) - 1 or not paths[i + 1].startswith(paths[i] + "/"):
            leaf_paths.append(paths[i])
    return leaf_paths


def sort_datatree(tree: datatree.DataTree[Any]) -> datatree.DataTree[Any]:
    """Alphabetically sort datatree.DataTree nodes by tree name

    Parameters
    ----------
    tree
        input `datatree.DataTree`

    Returns
    -------
        Sorted `datatree.DataTree`
    """
    logger = logging.getLogger()
    paths = tree.groups
    sorted_paths = sorted(paths)

    if tuple(sorted_paths) == paths:
        logger.debug(f"No need to sort {tree.name}")
        return tree
    else:
        logger.debug(f"Sorting {tree.name}")
        sorted_tree: datatree.DataTree[Any] = datatree.DataTree()
        sorted_paths = get_leaf_paths(sorted_paths)
        for p in sorted_paths[1:]:
            sorted_tree[p] = tree[p]

        sorted_tree.attrs.update(tree.attrs)
        return sorted_tree


def encode_time_dataset(ds: xr.Dataset) -> xr.Dataset:
    for name, var in ds.data_vars.items():
        if var.dtype == np.dtype("timedelta64[ns]") or var.dtype == np.dtype(
            "datetime64[ns]",
        ):
            ds[name] = var.astype(int)
    return ds


def encode_time_datatree(dt: datatree.DataTree[Any]) -> datatree.DataTree[Any]:
    for tree in dt.subtree:
        for name, var in tree.data_vars.items():
            if var.dtype == np.dtype("timedelta64[ns]") or var.dtype == np.dtype(
                "datetime64[ns]",
            ):
                tree[name] = var.astype(int)
        for name, coord in tree.coords.items():
            if coord.dtype == np.dtype("timedelta64[ns]") or coord.dtype == np.dtype(
                "datetime64[ns]",
            ):
                tree[name] = coord.astype(int)
                # tree[name].drop_duplicates(name)
    return dt


@datatree.map_over_subtree
def encode_time(ds: xr.Dataset) -> xr.Dataset:
    for name, var in ds.data_vars.items():
        if var.dtype == np.dtype("timedelta64[ns]") or var.dtype == np.dtype(
            "datetime64[ns]",
        ):
            ds[name] = var.astype(int)
    return ds


@datatree.map_over_subtree
def drop_duplicates(ds: xr.Dataset) -> xr.Dataset:
    """Drop duplicate values

    Parameters
    ----------
    ds
        input `xarray.Dataset` or `datatree.DataTree`

    Returns
    -------
        `xarray.Dataset` or `datatree.DataTree`
    """
    return ds.drop_duplicates(dim=...)


@datatree.map_over_subtree
def count_outliers(err: xr.Dataset, threshold: float) -> xr.Dataset:
    """For all variables of a `xarray.Dataset/datatree.DataTree`, count the number of outliers, exceeding the
    threshold value

    Parameters
    ----------
    err
        input `xarray.Dataset` or `datatree.DataTree`
    threshold
        Threshold value

    Returns
    -------
        reduced count `xarray.Dataset` or `datatree.DataTree`
    """
    return err.where(abs(err) >= threshold, np.nan).count(keep_attrs=True)


@datatree.map_over_subtree
def drop_coordinates(ds: xr.Dataset) -> xr.Dataset:
    """Remove all coordinates of a `datatree.DataTree

    Parameters
    ----------
    ds
        input `xarray.Dataset` or `datatree.DataTree`

    Returns
    -------
        `xarray.Dataset` or `datatree.DataTree`
    """
    return ds.drop_vars(ds.coords)


def _compute_reduced_datatree(
    tree: datatree.DataTree[Any],
    results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not results:
        results = {}

    for tree in tree.subtree:
        for name, var in tree.variables.items():
            key = "/".join([tree.path, str(name)])
            if key in results:
                results[key].append(var.compute().data)
            else:
                results[key] = [var.compute().data]
            # results[name]=[var.compute().data]

    return results


def _get_coverage(
    tree: datatree.DataTree[Any],
    results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not results:
        results = {}

    for tree in tree.subtree:
        for name, var in tree.variables.items():
            key = "/".join([tree.path, str(name)])
            if key in results:
                results[key].append(var.size)
                results[key].append(np.prod(var.shape))
            else:
                results[key] = [var.size, np.prod(var.shape)]

    return results


def variables_statistics(
    dt: datatree.DataTree[Any],
    threshold: float,
) -> dict[str, Any]:
    """Compute statistics on all the variables of a `datatree.DataTree`
    Note that this function triggers the `dask.array.compute()`

    Parameters
    ----------
    dt
        input `datatree.DataTree`
    threshold
        Threshold to be used to count a number of outliers, especially in the case where `dt` represents
        an absolute or relative difference

    Returns
    -------
        A dictionary with keys the name of the variable (including its tree path) and the list a computed statistics
    """
    min_dt = dt.min(skipna=True)
    max_dt = dt.max(skipna=True)
    mean_dt = dt.mean(skipna=True)
    std_dt = dt.std(skipna=True)
    count = count_outliers(dt, threshold)

    results = _compute_reduced_datatree(min_dt)
    results = _compute_reduced_datatree(max_dt, results)
    results = _compute_reduced_datatree(mean_dt, results)
    results = _compute_reduced_datatree(std_dt, results)
    results = _compute_reduced_datatree(count, results)
    # Coordinates are not accounted for after reduction operation as min,max...
    # So remove the coordintes from dt to get coverage
    results = _get_coverage(drop_coordinates(dt), results)

    return results


def bitwise_statistics_over_dataarray(array: xr.DataArray) -> xr.Dataset:
    """Compute bitwise statistics over a dataarray

    Parameters
    ----------
    array
        input dataarray. It is assumed to represent the difference between 2 bitwise flag values for instance
        flag1 ^ flag2

    Returns
    -------
        returns a `xarray.dataset` indexed by the bit range with the following variables
        "bit_position",
        "bit_meaning",
        "total_bits":,
        "equal_count",
        "different_count",
        "equal_percentage",
        "different_percentage"
    """
    flag_meanings = array.attrs["flag_meanings"]
    flag_masks = list(array.attrs["flag_masks"])

    # num_bits = len(flag_masks)
    key: list[str] = []
    if isinstance(flag_meanings, str):
        key = flag_meanings.split(" ")

    bit_stats: list[dict[str, Any]] = []

    for bit_mask in flag_masks:
        # get bit position aka log2(bit_mask)
        bit_pos = 0
        m = bit_mask
        while m > 1:
            m >>= 1
            bit_pos += 1
        # for bit_pos in range(num_bits):
        # bit_mask = 1 << bit_pos
        diff = (array & bit_mask) >> bit_pos
        equal_bits = diff == 0

        try:
            idx = flag_masks.index(bit_mask)
            # idx = np.where(flag_masks == bit_mask)
        except ValueError:
            print(
                f"Encounter problem while retrieving the bit position for value {bit_mask}",
            )

        flag_name = key[idx]

        total_bits = equal_bits.size
        equal_count = equal_bits.sum().compute().data
        diff_count = total_bits - equal_count

        bit_stats.append(
            {
                "bit_position": bit_pos,
                "bit_meaning": flag_name,
                "total_bits": total_bits,
                "equal_count": equal_count,
                "different_count": diff_count,
                "equal_percentage": equal_count / total_bits * 100,
                "different_percentage": diff_count / total_bits * 100,
            },
        )

    return xr.Dataset.from_dataframe(pd.DataFrame(bit_stats))


def bitwise_statistics(dt: datatree.DataTree[Any]) -> dict[str, xr.Dataset]:
    """Compute bitwise statistics on all the variables of a `datatree.DataTree`.
    The variables should represent flags/masks variables as defined by the CF conventions, aka including
    "flags_meanings" and "flags_values" as attributes
    Note that this function triggers the `dask.array.compute()`

    Parameters
    ----------
    dt
        input `datatree.DataTree

    Returns
    -------
        Dictionary of `xarray.Dataset` with keys being the variable name.
        The `xarray.Dataset` is indexed by the bit range and contains the following variables
        "bit_position",
        "bit_meaning",
        "total_bits":,
        "equal_count",
        "different_count",
        "equal_percentage",
        "different_percentage"
    """
    # TODO test if dt only contains flags variables
    # call to filter_flags for instance

    res: dict[str, xr.Dataset] = {}
    for tree in dt.subtree:
        # if tree.is_leaf:
        if tree.ds:
            for var in tree.data_vars:
                res[var] = bitwise_statistics_over_dataarray(tree.data_vars[var])

    return res


def product_exists(input_path: str, secret: str | None = None) -> bool:
    """Check if input product exists wheter it is on filesystem or object-storage"""
    url = EOPath(input_path)

    if url.protocol == "s3":
        s3fs = get_s3filesystem(url, profile=secret)
        return s3fs.exists(url.path)
    else:
        return url.exists()


def parse_cmp_vars(reference: str, new: str, cmp_vars: str) -> list[tuple[str, str]]:
    """Parse command-line option cmp-vars"""
    list_prods: list[tuple[str, str]] = []

    for vars in cmp_vars.split(","):
        var = vars.split(":")
        if len(var) != 2:
            raise ValueError(f"{cmp_vars} is not a valid --cmp-var option syntax")
        list_prods.append(
            # (str(ref_url / var[0].lstrip("/")), str(new_url / var[1].lstrip("/"))),
            (var[0], var[1]),
        )

    return list_prods
