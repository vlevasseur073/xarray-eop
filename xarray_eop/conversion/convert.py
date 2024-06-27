from pathlib import Path
from typing import Optional
import click

import datatree
import zarr

from xarray_eop.api import open_datatree
from xarray_eop.conversion.update_attrs import update_attributes
from xarray_eop.conversion.utils import DEFAULT_COMPRESSOR


def _check_duplicate_set(items):
    hash_bucket = set()
    for item in items:
        if item in hash_bucket:
            print(item)
            return True
        hash_bucket.add(item)
    return False


def product_converter(
    sample_path: str | Path,
    output_path: str | Path,
    zip: Optional[bool] = True,
) -> datatree.DataTree:
    """Convert Sentinel-3 SAFE product to the EOP zarr structure.
    See the `Product Structure and Format Definition <https://cpm.pages.eopf.copernicus.eu/eopf-cpm/main/PSFDjan2024.html>`__

    Parameters
    ----------
    sample_path
        input Sentinel-3 SAFE product path
    output_path
        output Zarr product path
    zip, optional
        output the zipped product in addition (zero compression), by default True

    Returns
    -------
        Converted Zarr product
    """

    sample_path = Path(sample_path)
    output_path = Path(output_path)

    prod = open_datatree(sample_path)
    shortnames: list = []
    for tree in prod.subtree:
        for var in tree.variables:
            tree[var].encoding["compressor"] = DEFAULT_COMPRESSOR
            # Check if coordinates do exist
            if "coordinates" in tree[var].encoding:
                coords = [
                    c
                    for c in tree[var].encoding["coordinates"].split(" ")
                    if c in tree.variables
                ]
                if coords:
                    tree[var].encoding["coordinates"] = " ".join(coords)
                else:
                    tree[var].encoding.pop("coordinates")
            # Set shortnames
            if var in shortnames:
                tmp = tree.path.split("/")[2:]
                tmp.insert(0, var)
                new_shortname = "_".join(tmp)
                if new_shortname in shortnames:
                    print(f"Warning: {new_shortname} already exists in shornames list")
                    print(f"Warning: variables {var} will not have short_name")
                    print("Warning: continue")
                    continue
                tree[var].attrs.update({"short_name": new_shortname})
                shortnames.append(new_shortname)
            else:
                tree[var].attrs.update({"short_name": var})
                shortnames.append(var)

    prod.to_zarr(store=output_path, consolidated=True)

    # Verification of unicity of shortnames
    if len(set(shortnames)) < len(shortnames):
        print("Error in shortnames: Items appear twice ...")
        # print(shortnames)
        _check_duplicate_set(shortnames)
        exit(0)

    print("Updating and consolidate metadata")
    typ_eop = output_path.name[:9]
    prod.attrs.update(update_attributes(typ_eop))
    zarr.consolidate_metadata(output_path)

    # Check to open with datatree and zip
    # print("Checking product")
    # decode_times = True
    # if typ_eop in ["S03SYNVGK", "S03SYNVG1", "S03SYNV10"]:
    #     decode_times = False
    # dt: datatree.DataTree = open_datatree(output_path, decode_times=decode_times)
    if zip:
        print("Zipping product")
        with zarr.ZipStore(str(output_path) + ".zip") as store:
            prod.to_zarr(store)

    return prod


@click.command()
@click.argument(
    "input",
    type=str,
    nargs=1,
)
@click.argument(
    "output",
    type=str,
    nargs=1,
)
@click.option(
    "--zip",
    is_flag=True,
    default=False,
    show_default=True,
    help="Zip the output product",
)
def convert(input: str, output: str, zip: bool = False):
    product_converter(input, output, zip)
