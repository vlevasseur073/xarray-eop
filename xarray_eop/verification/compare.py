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
import sys
from typing import Any, Dict, List

import click
import datatree
import numpy as np
import pandas as pd
import xarray as xr
from click.testing import CliRunner

from xarray_eop import EOPath, get_s3filesystem, open_datatree
from xarray_eop.utils import filter_flags
from xarray_eop.verification.logger import (
    get_failed_logger,
    get_logger,
    get_passed_logger,
)


# Formatted string when test fails
def _get_failed_formatted_string_vars(
    name: str,
    values: List[Any],
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
            f"eps={threshold}% "
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
def get_leaf_paths(paths):
    """Given a list of tree paths, returns leave paths

    Parameters
    ----------
    paths
        list of tree structure path

    Returns
    -------
        leaf patsh
    """
    leaf_paths = []
    for i in range(len(paths)):
        if i == len(paths) - 1 or not paths[i + 1].startswith(paths[i] + "/"):
            leaf_paths.append(paths[i])
    return leaf_paths


def sort_datatree(tree: datatree.DataTree) -> datatree.DataTree:
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
    paths: tuple = tree.groups
    sorted_paths: tuple = tuple(sorted(paths))

    if sorted_paths == paths:
        logger.debug(f"No need to sort {tree.name}")
        return tree
    else:
        logger.debug(f"Sorting {tree.name}")
        sorted_tree = datatree.DataTree()
        # print(sorted_paths)
        # print(get_leaf_paths(sorted_paths))
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


def encode_time_datatree(dt: datatree.DataTree) -> datatree.DataTree:
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


def _compute_reduced_datatree(tree: datatree.DataTree, results=None) -> Dict[str, Any]:
    if not results:
        results = {}

    for tree in tree.subtree:
        for name, var in tree.variables.items():
            key = "/".join([tree.path, name])
            if key in results:
                results[key].append(var.compute().data)
            else:
                results[key] = [var.compute().data]
            # results[name]=[var.compute().data]

    return results


def _get_coverage(tree: datatree.DataTree, results: None) -> Dict[str, Any]:
    if not results:
        results = {}

    for tree in tree.subtree:
        for name, var in tree.variables.items():
            key = "/".join([tree.path, name])
            if key in results:
                results[key].append(var.size)
                results[key].append(np.prod(var.shape))
            else:
                results[key] = [var.size, np.prod(var.shape)]

    return results


def variables_statistics(dt: datatree.DataTree, threshold: float) -> Dict[str, Any]:
    """Compute statistics on all the variables of a `datatree.DataTree`
    Note that this function triggers the `dask.array.compute()`

    Parameters
    ----------
    dt
        input `dataree.DataTree
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


def bitwise_statistics_over_dataarray(array: xr.DataArray):
    flag_meanings = array.attrs["flag_meanings"]
    flag_masks = list(array.attrs["flag_masks"])
    # print(type(flag_masks),flag_masks)

    # num_bits = len(flag_masks)
    key: List[str] = []
    if isinstance(flag_meanings, str):
        key = flag_meanings.split(" ")

    bit_stats: List[Dict[str, Any]] = []

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


def bitwise_statistics(dt: datatree.DataTree) -> Dict[str, xr.Dataset]:
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

    res: Dict[str, xr.Dataset] = {}
    for tree in dt.subtree:
        # if tree.is_leaf:
        if tree.ds:
            for var in tree.data_vars:
                res[var] = bitwise_statistics_over_dataarray(tree.data_vars[var])

    return res


def product_exists(input_path: str) -> bool:
    """Check if input product exists wheter it is on filesystem or object-storage"""
    url = EOPath(input_path)

    if url.protocol == "s3":
        s3fs = get_s3filesystem(url)
        return s3fs.exists(url.path)
    else:
        return url.exists()


def parse_cmp_vars(reference: str, new: str, cmp_vars: str) -> List[tuple[str, str]]:
    """Parse command-line option cmp-vars"""
    list_prods: List[tuple[str, str]] = []

    ref_url = EOPath(reference)
    new_url = EOPath(new)

    for vars in cmp_vars.split(","):
        var = vars.split(":")
        if len(var) != 2:
            raise ValueError(f"{cmp_vars} is not a valid --cmp-var option syntax")
        list_prods.append(
            (str(ref_url / var[0].lstrip("/")), str(new_url / var[1].lstrip("/"))),
        )

    return list_prods


@click.command()
@click.option(
    "-ref",
    "--reference",
    required=True,
    # type=click.Path(exists=True, path_type=Path),
    type=str,
    help="reference product ",
)
@click.option(
    "-new",
    "--new",
    required=True,
    # type=click.Path(exists=True, path_type=Path),
    type=str,
    help="new product ",
)
@click.option(
    "--cmp-vars",
    type=str,
    help="Compare only specific variables, defined as: path/to/var_ref:path/to/var_new,... ",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    show_default=True,
    help="increased verbosity",
)
@click.option(
    "--relative",
    is_flag=True,
    default=False,
    show_default=True,
    help="Compute relative error",
)
@click.option(
    "--threshold",
    required=False,
    type=float,
    default=1.0e-6,
    show_default=True,
    help="Error Threshold defining the PASSED/FAILED result",
)
@click.option(
    "--flags-only",
    required=False,
    is_flag=True,
    default=False,
    show_default=True,
    help="Compute comparison only for flags/masks variables",
)
@click.option("-o", "--output", required=False, help="output file")
def compare(
    reference: str,
    new: str,
    cmp_vars: str,
    verbose: bool,
    relative: bool,
    threshold,
    flags_only: bool,
    output: str,
):
    """CLI tool to compare two products Zarr or SAFE

    Parameters
    ----------
    reference: Path
        Reference product path
    new: Path
        New product path
    verbose: bool
        2-level of verbosity (INFO or DEBUG)
    relative: bool
        Compute relative or absolute error, default is True
    threshold
        Threshold to determine wheter the comparison is PASSED or FAILED
    """
    # Initialize stream
    if output:
        stream = open(output, mode="w")
    else:
        stream = sys.stderr

    # Initialize logging
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    logger = get_logger("compare", level=level, stream=stream)
    logger.setLevel(level)

    passed_logger = get_passed_logger("passed", stream=stream)
    failed_logger = get_failed_logger("failed", stream=stream)

    # Check input products
    if not product_exists(reference):
        logger.error(f"{reference} cannot be found.")
        exit(1)
    if not product_exists(new):
        logger.error(f"{new} cannot be found.")
        exit(1)
    logger.info(
        f"Compare the new product {new} to the reference product {reference}",
    )

    # Check if specific variables
    if cmp_vars:
        list_ref_new_prods = parse_cmp_vars(reference, new, cmp_vars)
    else:
        list_ref_new_prods = [
            (reference, new),
        ]

    # Loop over input products
    for ref_prod, new_prod in list_ref_new_prods:
        # Open reference product
        dt_ref = open_datatree(ref_prod, decode_times=False, fs_copy=True)
        dt_ref.name = "ref"
        logger.debug(dt_ref)

        # Open new product
        dt_new = open_datatree(new_prod, decode_times=False, fs_copy=True)
        dt_new.name = "new"
        logger.debug(dt_new)

        # Sort datatree
        dt_ref = sort_datatree(dt_ref)
        dt_new = sort_datatree(dt_new)

        # Check if datatrees are isomorphic
        if not dt_new.isomorphic(dt_ref):
            logger.error("Reference and new products are not isomorphic")
            logger.error("Comparison fails")
            return

        # dt_ref = drop_duplicates(dt_ref)
        # dt_new = drop_duplicates(dt_new)
        # dt_new = encode_time_datatree(dt_new)
        # dt_ref = encode_time_datatree(dt_ref)

        # Variable statistics
        if not flags_only:
            if relative:
                dt_ref_tmp = dt_ref.where(dt_ref != 0)
                dt_new_tmp = dt_new.where(dt_ref != 0)
                err = (dt_new_tmp - dt_ref_tmp) / dt_ref_tmp
            else:
                err = dt_new - dt_ref

            results: Dict[str, Any] = variables_statistics(err, threshold)

            logger.info("-- Verification of variables")
            for name, val in results.items():
                if all(v < threshold for v in val[:-2]):
                    passed_logger.info(f"{name}")
                else:
                    failed_logger.info(
                        _get_failed_formatted_string_vars(
                            name,
                            val,
                            threshold,
                            relative=relative,
                        ),
                    )

        # Flags statistics
        flags_ref = filter_flags(dt_ref)
        flags_new = filter_flags(dt_new)

        with xr.set_options(keep_attrs=True):
            err_flags = flags_ref ^ flags_new

        res: Dict[str, xr.Dataset] = bitwise_statistics(err_flags)
        eps = 100.0 * (1.0 - threshold)
        logger.info(f"-- Verification of flags: threshold = {eps}%")
        for name, ds in res.items():
            # ds_outlier = ds.where(ds.equal_percentage < eps, other=-1, drop=True)
            for bit in ds.index.data:
                if ds.equal_percentage[bit] < eps:
                    failed_logger.info(
                        _get_failed_formatted_string_flags(name, ds, bit, eps),
                    )
                else:
                    passed_logger.info(
                        _get_passed_formatted_string_flags(name, ds, bit),
                    )

        logger.info("Exiting compare")

    if output:
        stream.close()


# Function to call the Click command programmatically
def call_compare(
    reference: str,
    new: str,
    verbose: bool = True,
    relative: bool = True,
    threshold: float = 1.0e-6,
    flags_only: bool = False,
):
    """Callable function to compare two products Zarr or SAFE

    Parameters
    ----------
    reference: Path
        Reference product path
    new: Path
        New product path
    """
    runner = CliRunner()
    args = ["--reference", reference, "--new", new, "--threshold", threshold]
    if verbose:
        args.append("--verbose")
    if flags_only:
        args.append("--flags-only")
    if relative:
        args.append("--relative")
    result = runner.invoke(
        compare,
        args,
    )
    if result.exit_code != 0:
        print(f"Error: {result.output}")
    else:
        print(result.output)


if __name__ == "__main__":
    # Test
    internal_path = EOPath(
        # "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products",
        # "/mount/internal/work-st/projects/cs-412/2078-dpr/workspace/vlevasseur",
        "s3://buc-acaw-dpr/Samples/SAFE/",
    )
    ref = (
        internal_path
        # / "SAFE"
        # / "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3"
        # / "S3B_SL_1_RBT____20230315T095847_20230315T100147_20230316T030042_0179_077_150_4320_PS2_O_NT_004.SEN3"
        / "S3A_OL_1_ERR____20191227T124211_20191227T124311_20230616T083918_0059_053_109______LR1_D_NT_003.SEN3"
    )
    # new = internal_path / "Zarr_DDR" / "S03OLCERR_20230506T015316_0180_B117_T978.zarr"
    # new = internal_path / "Zarr_DDR" / "S03SLSRBT_20230315T095847_0179_B150_S015.zarr"
    new = (
        internal_path
        / "S3A_OL_1_ERR____20191227T124211_20191227T124311_20240405T144909_0059_053_109______LR1_D_NT_003.SEN3"
    )

    call_compare(
        ref,
        new,
        verbose=False,
        # relative=True,
        threshold=2.0e-5,
        flags_only=False,
    )
