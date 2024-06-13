import csv
from pathlib import Path

import datatree
import netCDF4 as nc
import numpy as np
import xarray as xr

from xarray_eop.conversion.utils import (
    DEFAULT_COMPRESSOR,
    extract_legacy,
    gen_static_adf_name,
    generate_datatree_from_legacy_adf,
    str_to_number,
)

in_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3",
)
out_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/SL2_FRP",
)
tmp_path = Path("/tmp")
_LOG_GENERATING_ADF = "*** Generating ADF "


def generate(adf_type: str) -> None:

    if adf_type == "FRPAC":
        for legacy_adf in [
            "S3A_SL_2_FRPTAX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            baseline_collection = 1
            out_file = gen_static_adf_name("S3_", adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            # dt = datatree.DataTree(name="root_adf")

            uh2o = []
            thickness = {"MWIR": [], "SWIR": []}
            varA = {"MWIR": [], "SWIR": []}
            varB = {"MWIR": [], "SWIR": []}
            varC = {"MWIR": [], "SWIR": []}

            # Read SL_2_ATMCOR.csv
            in_csv = safe / "SL_2_ATMCOR.csv"
            with open(str(in_csv), newline="") as csvfile:
                reader = csv.reader(csvfile, delimiter=",")
                next(reader)
                for row in reader:
                    row_num = list(map(lambda s: str_to_number(s)[0], row))
                    if row_num:
                        uh2o.append(row_num[0])
                        thickness["MWIR"].append(row_num[1])
                        varA["MWIR"].append(row_num[2])
                        varB["MWIR"].append(row_num[3])
                        varC["MWIR"].append(row_num[4])

            # Read SL_2_ATMCOR_SWIR.csv
            in_csv = safe / "SL_2_ATMCOR_SWIR.csv"
            with open(str(in_csv), newline="") as csvfile:
                reader = csv.reader(csvfile, delimiter=",")
                next(reader)
                for row in reader:
                    row_num = list(map(lambda s: str_to_number(s)[0], row))
                    if row_num:
                        # uh2o.append(row[0])
                        thickness["SWIR"].append(row_num[1])
                        varA["SWIR"].append(row_num[2])
                        varB["SWIR"].append(row_num[3])
                        varC["SWIR"].append(row_num[4])

            data1 = np.stack([thickness["MWIR"], thickness["SWIR"]])
            data2 = np.stack([varA["MWIR"], varA["SWIR"]])
            data3 = np.stack([varB["MWIR"], varB["SWIR"]])
            data4 = np.stack([varC["MWIR"], varC["SWIR"]])
            ds = xr.Dataset(
                data_vars=dict(
                    thickness=(["band", "uh2o"], data1),
                    coef_a=(["band", "uh2o"], data2),
                    coef_b=(["band", "uh2o"], data3),
                    coef_c=(["band", "uh2o"], data4),
                ),
                coords=dict(band=[0, 1], uh2o=uh2o),
            )
            ds.coords["band"].attrs = {"long_name": "MWIR (0) or SWIR (1)"}
            ds.coords["uh2o"].attrs = {"long_name": "water vapor", "units": ""}
            for var in ds.data_vars:
                ds[var].encoding["compressor"] = DEFAULT_COMPRESSOR
            dt = datatree.DataTree(
                name="maps",
                # parent=dt,
                data=ds,
            )
            dt.attrs = {
                "title": "frp atmospheric correction data file",
                "baseline collection": f"{baseline_collection:03d}",
            }
            dt.to_zarr(out_file)

    if adf_type == "FRPLC":
        # Here the old zarr ADF has been updated to remove the coordinates variables
        old_zarr_path = Path(
            "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr/SL2_FRP",
        )
        files = [f for f in old_zarr_path.glob("S3*FRPLC*.zarr")]
        for adf in files:
            out_file = gen_static_adf_name(adf.name[0:3], "FRPLC", format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            maps = xr.open_dataset(
                files[0] / "maps",
                engine="zarr",
                chunks={},
                consolidated=False,
            )
            c = xr.open_dataset(
                files[0] / "coordinates",
                engine="zarr",
                chunks={},
                consolidated=False,
            )
            ds = xr.open_dataset(files[0], engine="zarr", chunks={}, consolidated=False)
            # dt_new = datatree.DataTree(name="root_adf")
            coordinates = {
                "x": c.x,
                "y": c.y,
            }
            glc = maps.glc2000.assign_coords(coordinates)
            dt_new = datatree.DataTree(
                name="maps",
                # parent=dt_new,
                data=glc,
            )
            for att in ds.attrs:
                if isinstance(ds.attrs[att], str):
                    dt_new.attrs[att] = ds.attrs[att].lower()
                else:
                    dt_new.attrs[att] = ds.attrs[att]
            dt_new.to_zarr(out_file)

    if adf_type == "FRPCM":
        for legacy_adf in ["S3__SL_2_CFM_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            baseline_collection = int(safe.name[-8:-5])
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root_adf")

            nc_file = "Gas_Flare_List.nc"
            in_file = safe / nc_file
            ds = nc.Dataset(in_file)
            lat = ds.variables["Latitude"][:]
            lon = ds.variables["Longitude"][:]

            gas_flare = xr.Dataset(
                {"latitude": lat, "longitude": lon},
            )
            gas_flare.latitude.attrs["long_name"] = "Latitude"
            gas_flare.latitude.attrs["units"] = "degrees_north"
            gas_flare.latitude.attrs["valid_max"] = 90.0
            gas_flare.latitude.attrs["valid_min"] = -90.0
            gas_flare.longitude.attrs["long_name"] = "Longitude"
            gas_flare.longitude.attrs["units"] = "degrees_east"
            gas_flare.longitude.attrs["valid_max"] = 180.0
            gas_flare.longitude.attrs["valid_min"] = -180.0

            nc_file = "Volcano_list.nc"
            in_file = safe / nc_file
            ds = nc.Dataset(in_file)
            lat = ds.variables["Latitude"][:]
            lon = ds.variables["Longitude"][:]

            volcano = xr.Dataset({"latitude": lat, "longitude": lon})
            volcano.latitude.attrs["long_name"] = "Latitude"
            volcano.latitude.attrs["units"] = "degrees_north"
            volcano.latitude.attrs["valid_max"] = 90.0
            volcano.latitude.attrs["valid_min"] = -90.0
            volcano.longitude.attrs["long_name"] = "Longitude"
            volcano.longitude.attrs["units"] = "degrees_east"
            volcano.longitude.attrs["valid_max"] = 180.0
            volcano.longitude.attrs["valid_min"] = -180.0

            for var in gas_flare.data_vars:
                gas_flare[var].encoding["compressor"] = DEFAULT_COMPRESSOR
            for var in volcano.data_vars:
                volcano[var].encoding["compressor"] = DEFAULT_COMPRESSOR

            datatree.DataTree(name="gas_flare", parent=dt, data=gas_flare)
            datatree.DataTree(name="volcano", parent=dt, data=volcano)
            dt.attrs = {
                "title": "frp classification fire mask data file",
                "baseline collection": f"{baseline_collection:03d}",
            }
            dt.to_zarr(out_file)

    if adf_type == "FRPPA":
        for legacy_adfs in [
            ["S3A_SL_2_SXPAAX", "S3A_SL_2_FXPAAX"],
            ["S3B_SL_2_SXPAAX", "S3B_SL_2_FXPAAX"],
        ]:
            out_file = gen_static_adf_name(legacy_adfs[0][0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            baseline_collection = 1  # int(input_paths[0].name[-8:-5])

            dt = datatree.DataTree(name="root_adf")
            for legacy_adf in legacy_adfs:
                safe = extract_legacy(in_path, legacy_adf, tmp_path)

                for nc_file in safe.glob("*.nc"):
                    band = nc_file.name.split("_")[1].lower()
                    view = nc_file.name.split("_")[2].lower()
                    ds = xr.open_dataset(nc_file, chunks={})
                    ds = ds.rename({var: var.lower() for var in ds.variables})
                    for var in ds.variables:
                        ds[var].encoding["compressor"] = DEFAULT_COMPRESSOR
                        ds[var].attrs = {
                            k.lower(): v.lower() for k, v in ds[var].attrs.items()
                        }

                    datatree.DataTree(name=band + view[0], parent=dt, data=ds)
            dt.attrs = {
                "title": "frp pixel area data file",
                "baseline collection": f"{baseline_collection:03d}",
            }
            dt.to_zarr(out_file)


if __name__ == "__main__":
    generate("FRPAC")
    generate("FRPLC")
    generate("FRPCM")
    generate("FRPPA")
