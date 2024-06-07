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
from pathlib import Path
from typing import Any, Dict

import click
import datatree
import numpy as np
import xarray as xr
from click.testing import CliRunner

from xarray_eop.eop import open_eop_datatree
from xarray_eop.sentinel3 import open_safe_datatree
from xarray_eop.verification.logger import (
    get_failed_logger,
    get_logger,
    get_passed_logger,
)


def use_custom_mapping(product: Path | str) -> bool:
    custom_map = False
    if isinstance(product, Path):
        pattern = product.name[4:12]
    elif isinstance(product, str):
        pattern = product.split("/")[-1][4:12]
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


# Function to get leaf paths
def get_leaf_paths(paths):
    leaf_paths = []
    for i in range(len(paths)):
        if i == len(paths) - 1 or not paths[i + 1].startswith(paths[i] + "/"):
            leaf_paths.append(paths[i])
    return leaf_paths


def sort_datatree(tree: datatree.DataTree) -> datatree.DataTree:
    logger = logging.getLogger()
    paths: tuple = tree.groups
    sorted_paths: tuple = tuple(sorted(paths))

    if sorted_paths == paths:
        logger.critical(f"No need to sort {tree.name}")
        return tree
    else:
        logger.critical(f"Sorting {tree.name}")
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
def mean(ds: xr.Dataset) -> xr.Dataset:
    return ds.mean(skipna=True)


@datatree.map_over_subtree
def max(ds: xr.Dataset) -> xr.Dataset:
    return ds.max(skipna=True)


@datatree.map_over_subtree
def min(ds: xr.Dataset) -> xr.Dataset:
    return ds.min(skipna=True)


@datatree.map_over_subtree
def std(ds: xr.Dataset) -> xr.Dataset:
    return ds.std(skipna=True)


def compute_reduced_datatree(tree: datatree.DataTree, results=None) -> Dict[str, Any]:
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


@click.command()
@click.option(
    "-ref",
    "--reference",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="reference product ",
)
@click.option(
    "-new",
    "--new",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="new product ",
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
    help="Error Threshold defining the PASSED/FAILED result",
)
def compare(reference: Path, new: Path, verbose: bool, relative: bool, threshold):

    # Initialize logging
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    logger = get_logger("compare", level=level)
    logger.setLevel(level)
    logger.info(
        f"Compare the new product {new.name} to the reference product {reference.name}",
    )

    passed_logger = get_passed_logger("passed")
    failed_logger = get_failed_logger("failed")

    # Open reference product
    if reference.suffix == ".SEN3":
        simplified_mapping = use_custom_mapping(reference)
        dt_ref = open_safe_datatree(
            "ref",
            reference,
            simplified_mapping=simplified_mapping,
        )
    elif reference.suffix == ".zarr" or ".zarr" in reference.suffixes:
        dt_ref = open_eop_datatree(reference)
    else:
        print("Reference product is neither zarr nor SAFE", reference.name)
        exit(0)
    dt_ref.name = "ref"
    logger.debug(dt_ref)

    # Open new product
    dt_new = open_eop_datatree(new)
    dt_new.name = "new"
    logger.debug(dt_ref)

    # Sort datatree
    dt_ref = sort_datatree(dt_ref)
    dt_new = sort_datatree(dt_new)

    # Check if datatrees are isomorphic
    if not dt_new.isomorphic(dt_ref):
        logger.error("Reference and new products are not isomorphic")
        logger.error("Comparison fails")
        return

    if relative:
        encode_time_datatree(dt_new)
        encode_time_datatree(dt_ref)
        err = (dt_new - dt_ref) / dt_ref
    else:
        err = dt_new - dt_ref
    min_err = min(err)
    max_err = max(err)
    mean_err = mean(err)
    # For Standard deviation need to convert datetime or timedelta to int
    std_err = std(err)
    encode_time_datatree(err)

    results = compute_reduced_datatree(min_err)
    results = compute_reduced_datatree(max_err, results)
    results = compute_reduced_datatree(mean_err, results)
    results = compute_reduced_datatree(std_err, results)
    for name, val in results.items():
        if all(v < threshold for v in val):
            passed_logger.info(f"{name}")
        else:
            failed_logger.info(
                (
                    f"{name}: "
                    f"min={val[0]}, "
                    f"max={val[1]}, "
                    f"mean={val[2]}, "
                    f"stdev={val[3]}, "
                ),
            )

    logger.info("Exiting compare")


# Function to call the Click command programmatically
def call_compare(reference: str, new: str):
    runner = CliRunner()
    result = runner.invoke(
        compare,
        [
            "--reference",
            reference,
            "--new",
            new,
            "--verbose",
            "--relative",
            "--threshold",
            1e-6,
        ],
    )
    if result.exit_code != 0:
        print(f"Error: {result.output}")
    else:
        print(result.output)


if __name__ == "__main__":
    # Test
    internal_path = Path(
        "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products",
    )
    ref = (
        internal_path
        / "SAFE"
        / "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3"
    )
    new = internal_path / "Zarr_DDR" / "S03OLCERR_20230506T015316_0180_B117_T978.zarr"

    call_compare(ref, new)
