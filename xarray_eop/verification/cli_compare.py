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
from io import TextIOWrapper
from typing import Any, TextIO

import click
import xarray as xr
from click.testing import CliRunner

from xarray_eop import EOPath, open_datatree
from xarray_eop.utils import filter_flags
from xarray_eop.verification.compare import (
    _get_failed_formatted_string_flags,
    _get_failed_formatted_string_vars,
    _get_passed_formatted_string_flags,
    bitwise_statistics,
    filter_datatree,
    parse_cmp_vars,
    product_exists,
    sort_datatree,
    variables_statistics,
)
from xarray_eop.verification.logger import (
    get_failed_logger,
    get_logger,
    get_passed_logger,
)


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
    "--cmp-grps",
    type=str,
    help="Compare only specific groups, defined as: path/to/grp_ref:path/to/grp_new,... ",
)
@click.option(
    "-s",
    "--secret",
    type=str,
    default=None,
    help="Secret alias of credentials to access cloud-storage",
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
    cmp_grps: str,
    secret: str,
    verbose: bool,
    relative: bool,
    threshold: float,
    flags_only: bool,
    output: str,
) -> None:
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
    stream: TextIOWrapper | TextIO
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
    if not product_exists(reference, secret):
        logger.error(f"{reference} cannot be found.")
        exit(1)
    if not product_exists(new, secret):
        logger.error(f"{new} cannot be found.")
        exit(1)
    logger.info(
        f"Compare the new product {new} to the reference product {reference}",
    )

    # Check if specific variables/groups
    if cmp_vars:
        list_ref_new_vars = parse_cmp_vars(reference, new, cmp_vars)
    if cmp_grps:
        list_ref_new_grps = parse_cmp_vars(reference, new, cmp_grps)

    # Open reference product
    kwargs: dict[str, Any] = {}
    kwargs["decode_times"] = False
    kwargs["fs_copy"] = True
    if secret:
        kwargs["secret_alias"] = secret
    dt_ref = open_datatree(reference, **kwargs)
    dt_ref.name = "ref"
    logger.debug(dt_ref)

    # Open new product
    dt_new = open_datatree(new, **kwargs)
    dt_new.name = "new"
    logger.debug(dt_new)

    # Sort datatree
    dt_ref = sort_datatree(dt_ref)
    dt_new = sort_datatree(dt_new)

    # Filter datatree
    if cmp_vars:
        dt_ref = filter_datatree(
            dt_ref,
            [var[0] for var in list_ref_new_vars],
            type="variables",
        )
        dt_new = filter_datatree(
            dt_new,
            [var[1] for var in list_ref_new_vars],
            type="variables",
        )
    if cmp_grps:
        dt_ref = filter_datatree(
            dt_ref,
            [var[0] for var in list_ref_new_grps],
            type="groups",
        )
        dt_new = filter_datatree(
            dt_new,
            [var[1] for var in list_ref_new_grps],
            type="groups",
        )

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
            err = dt_new - dt_ref  # type: ignore

        results: dict[str, Any] = variables_statistics(err, threshold)

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

    res: dict[str, xr.Dataset] = bitwise_statistics(err_flags)
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
    cmp_vars: str | None = None,
    cmp_grps: str | None = None,
    secret: str | None = None,
) -> None:
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
    if cmp_vars:
        args.extend(["--cmp-vars", cmp_vars])
    if cmp_grps:
        args.extend(["--cmp-grps", cmp_grps])
    if secret:
        args.extend(["--secret", secret])
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

    path = EOPath("s3://buc-acaw-dpr/Samples/Zarr/")
    ref = path / "S03OLCERR_20191227T124211_0059_A109_S000.zarr"
    new = path / "S03OLCERR_20191227T124211_0059_A109_S001.zarr"

    # call_compare(ref,new,verbose=False,relative=True,threshold=2.e-5,cmp_grps="/measurements:/measurements")
    call_compare(
        str(ref),
        str(new),
        verbose=False,
        relative=True,
        threshold=2.0e-5,
        cmp_vars="/measurements/oa01_radiance:/measurements/oa01_radiance",
    )

    # call_compare(
    #     ref,
    #     new,
    #     verbose=False,
    #     # relative=True,
    #     threshold=2.0e-5,
    #     # flags_only=False,
    #     # cmp_vars="/measurements/oa01_radiance:/measurements/oa01_radiance"
    #     secret="acaw-dpr"
    # )
