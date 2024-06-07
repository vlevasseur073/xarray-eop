from pathlib import Path

import datatree
import pandas as pd
import rioxarray as rio
import xarray as xr
from netCDF4 import Dataset

from xarray_eop.conversion.utils import (
    DEFAULT_COMPRESSOR, extract_legacy,
    gen_static_adf_name,
    generate_datatree_from_legacy_adf,
    lower,
)

in_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3",
)
out_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/SY2_AOD",
)
tmp_path = Path("/tmp")
_LOG_GENERATING_ADF = "*** Generating ADF "


def generate(adf_type: str) -> None:

    if adf_type == "AODRT":
        for legacy_adf in [
            "S3__SY_2_ART_AX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="synergy l2 ntc atmospheric radiative transfer lut data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "AODOR":
        for legacy_adf in [
            "S3__SY_2_OSR_AX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="synergy l2 ntc ocean surface reflectance lut data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "AODLR":
        for legacy_adf in [
            "S3__SY_2_LSR_AX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="synergy l2 ntc land spectral reflectance lut data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "AODAC":
        for legacy_adf in [
            "S3__SY_2_ACLMAX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="synergy l2 ntc aerosol climatology data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "SYAOD":
        for legacy_adf in [
            "S3__SY_2_AODCAX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            baseline_collection = int(safe.name[-8:-5])
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file

            # data:list[xr.DataArray]=[]
            data: list[xr.Dataset] = []
            for envi_file in sorted(safe.glob("*.img")):
                print(envi_file)
                rds = rio.open_rasterio(envi_file)
                # ds = xr.open_dataset(envi_file,engine="rasterio")
                # print(rds)
                data.append(
                    rds.sel(band=1).drop_vars("band").rename("aod550"),
                )  # .rename({"band_data":"aod550"}))

            da = xr.concat(data, pd.Index(range(12), name="month"))
            da.encoding["compressor"] = DEFAULT_COMPRESSOR
            global_attr = dict(
                {
                    "title": "CAMS AOD climatology Data File",
                    "baseline collection": f"{baseline_collection:03d}",
                    "resolution": "0.125x0.125 degrees",
                    "number_of_grid_points_in_longitude": 2280,
                    "number_of_grid_points_in_latitude": 1440,
                    "first_longitude_value": -180.0,
                    "last_longitude_value": 180.0,
                    "grid_step_in_longitude": 0.125,
                    "first_latitude_value": 90.0,
                    "last_latitude_value": -90.0,
                    "grid_step_in_latitude": 0.125,
                },
            )
            for gattr in global_attr:
                da.attrs[gattr] = lower(global_attr.get(gattr))
            # print(da)
            da.to_zarr(out_file, consolidated=True)


if __name__ == "__main__":
    generate("AODRT")
    generate("AODOR")
    generate("AODLR")
    generate("AODAC")
    generate("SYAOD")
