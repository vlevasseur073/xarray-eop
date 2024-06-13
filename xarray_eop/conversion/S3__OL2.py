from pathlib import Path

import datatree
import pandas as pd
import rioxarray as rio
import xarray as xr
from netCDF4 import Dataset

from xarray_eop.conversion.utils import (
    DEFAULT_COMPRESSOR,
    extract_legacy,
    gen_static_adf_name,
    generate_datatree_from_legacy_adf,
    lower,
)

in_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3",
)
out_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/OL2",
)
tmp_path = Path("/tmp")
_LOG_GENERATING_ADF = "*** Generating ADF "


def generate(adf_type: str) -> None:

    if adf_type == "OLPPP":
        for legacy_adf in ["S3A_OL_2_PPP_AX", "S3B_OL_2_PPP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            dt = generate_datatree_from_legacy_adf(
                safe,
                safe_file=["OL_2_PPP_AX.nc"],
                title="ol2 pre-processing data file",
                dt=dt,
            )
            for ncgroup in ["classification_1", "gas_correction", "classification_2"]:
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol2 pre-processing data file",
                    ncgroup=ncgroup,
                    dt=dt,
                )
            # print(dt)
            dt.to_zarr(out_file)

    if adf_type == "OLACP":
        for legacy_adf in ["S3A_OL_2_ACP_AX", "S3B_OL_2_ACP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            for ncgroup in [
                "glint_whitecaps",
                "bright_waters_NIR",
                "standard_AC",
                "alternate_AC",
            ]:
                dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol2 atmospheric correction data file",
                    ncgroup=ncgroup,
                    dt=dt,
                )
            dt.to_zarr(out_file)

    if adf_type == "OLWVP":
        for legacy_adf in ["S3A_OL_2_WVP_AX", "S3B_OL_2_WVP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="ol2 water vapour data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "OLOCP":
        for legacy_adf in [
            "S3A_OL_2_OCP_AX",
            "S3B_OL_2_OCP_AX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="ol2 ocean colour data file",
                dt=dt,
            )
            for ncgroup in [
                "rhow_norm_nn",
            ]:
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol2 ocean colour data file",
                    ncgroup=ncgroup,
                    dt=dt,
                )
            dt.to_zarr(out_file)

    if adf_type == "OLVGP":
        for legacy_adf in [
            "S3A_OL_2_VGP_AX",
            "S3B_OL_2_VGP_AX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="ol2 vegetation data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "OLCLP":
        for legacy_adf in [
            "S3A_OL_2_CLP_AX",
            "S3B_OL_2_CLP_AX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="ol2 climatology data file",
                group="",
            )
            dt.to_zarr(out_file)


if __name__ == "__main__":
    generate("OLPPP")
    generate("OLACP")
    generate("OLWVP")
    generate("OLOCP")
    generate("OLVGP")
    generate("OLCLP")
