from pathlib import Path

import datatree
import xarray as xr
from netCDF4 import Dataset

from xarray_eop.conversion.utils import (
    extract_legacy, gen_static_adf_name,
    generate_datatree_from_legacy_adf,
)

in_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3",
)
out_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/SL2",
)
tmp_path = Path("/tmp")
_LOG_GENERATING_ADF = "*** Generating ADF "


def generate(adf_type: str) -> None:

    if adf_type == "SLLCC":
        for legacy_adf in ["S3A_SL_1_LCC_AX", "S3B_SL_1_LCC_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="land cloud coefficient data file",
            )
            dt.to_zarr(out_file)

    if adf_type == "LSTCD":
        for legacy_adf in ["S3A_SL_2_LSTCAX", "S3B_SL_2_LSTCAX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="lst coefficient data file",
                group="",
                var_to_attr={
                    "skip_biomes": ["long_name", "flag_meanings"],
                },  # "time_bounds": []}
            )
            dt.to_zarr(out_file)

    if adf_type == "LSTED":
        for legacy_adf in ["S3A_SL_2_LSTEAX", "S3B_SL_2_LSTEAX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="lst error data file",
                group="",
                coordinates_variable={  # variable : (dimention,coordinate)
                    "u_ran_emis": ("n_biome", "biome"),
                },
            )
            dt.attrs["latitude resolution"] = 1
            dt.attrs["longitude resolution"] = 1
            dt.to_zarr(out_file)

    if adf_type == "SLIRE":
        # Here the old zarr ADF has been updated to remove the coordinates variables
        old_zarr_path = Path(
            "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr/SL2",
        )
        files = [f for f in old_zarr_path.glob("S3*IRE*.zarr")]
        # print(files)
        for adf in files:
            out_file = gen_static_adf_name(adf.name[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.open_datatree(files[0], engine="zarr", chunks={})
            # print(dt)
            coordinates = {
                "latitude": dt.coordinates.latitude,
                "longitude": dt.coordinates.longitude,
                "month": dt.coordinates.month,
            }
            emis_s7 = dt.maps.emis_s7.assign_coords(coordinates)
            emis_s8 = dt.maps.emis_s8.assign_coords(coordinates)
            emis_s9 = dt.maps.emis_s9.assign_coords(coordinates)

            maps = xr.merge([emis_s7, emis_s8, emis_s9])
            dt_new = datatree.DataTree(name="maps", data=maps)
            for att in dt.attrs:
                if isinstance(dt.attrs[att], str):
                    dt_new.attrs[att] = dt.attrs[att].lower()
                else:
                    dt_new.attrs[att] = dt.attrs[att]
            # print(dt_new)
            dt_new.to_zarr(out_file)

    if adf_type == "TIRND":
        legacy_ADF = {
            "S3A": [
                "S3A_SL_2_S7N_AX",
                "S3A_SL_2_S8N_AX",
                "S3A_SL_2_S9N_AX",
                "S3A_SL_2_F1N_AX",
                "S3A_SL_2_S7O_AX",
                "S3A_SL_2_S8O_AX",
                "S3A_SL_2_S9O_AX",
            ],
            "S3B": [
                "S3B_SL_2_S7N_AX",
                "S3B_SL_2_S8N_AX",
                "S3B_SL_2_S9N_AX",
                "S3B_SL_2_F1N_AX",
                "S3B_SL_2_S7O_AX",
                "S3B_SL_2_S8O_AX",
                "S3B_SL_2_S9O_AX",
            ],
        }
        for sat in ["S3A", "S3B"]:
            out_file = gen_static_adf_name(sat, adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root_adf")
            for adf in legacy_ADF[sat]:
                safe = extract_legacy(in_path, adf, tmp_path)
                group = adf[9:12].lower()
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    title="thermal infrared noise data file",
                    group=group,
                    dt=dt,
                )
            dt.to_zarr(out_file)

    if adf_type == "IMSCD":
        for legacy_adf in [
            "S3__SL_2_IMSCAX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="lst ims coordinates data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "LSTVF":
        # Here the old zarr ADF has been updated to remove the coordinates variables
        old_zarr_path = Path(
            "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr/SL2",
        )
        files = [f for f in old_zarr_path.glob("S3*LSTVF*.zarr")]
        # print(files)
        for adf in files:
            out_file = gen_static_adf_name(adf.name[0:3], adf_type, format="zarr")
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
                "x": -c.x,
                "y": -c.y,
            }
            # print(coordinates)
            vf = maps.vegetation_fraction.assign_coords(coordinates)
            dt_new = datatree.DataTree(
                name="maps",
                # parent=dt_new,
                data=vf,
            )
            for att in ds.attrs:
                if isinstance(ds.attrs[att], str):
                    dt_new.attrs[att] = ds.attrs[att].lower()
                else:
                    dt_new.attrs[att] = ds.attrs[att]
            # print(dt_new)
            dt_new.to_zarr(out_file)

    if adf_type == "LSTWV":
        # Here the old zarr ADF has been updated to remove the coordinates variables
        old_zarr_path = Path(
            "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr/SL2",
        )
        files = [f for f in old_zarr_path.glob("S3*LSTWV*.zarr")]
        # print(files)
        for adf in files:
            out_file = gen_static_adf_name(adf.name[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.open_datatree(
                files[0],
                engine="zarr",
                chunks={},
                decode_times=False,
            )
            # maps = xr.open_dataset(files[0]/"maps",engine="zarr",chunks={},consolidated=False)
            # c = xr.open_dataset(files[0]/"coordinates",engine="zarr",chunks={},consolidated=False)
            # ds = xr.open_dataset(files[0],engine="zarr",chunks={},consolidated=False)
            # print(dt)
            # dt_new = datatree.DataTree(name="root_adf")
            coordinates = {
                "month": dt.coordinates.month,
                "time": dt.coordinates.times,
                "latitudes": dt.coordinates.latitudes,
                "longitudes": dt.coordinates.longitudes,
            }
            # print(coordinates)
            dt = dt.maps.assign_coords(coordinates)

            dt_new = datatree.DataTree(
                name="maps",
                # parent=dt_new,
                data=dt.tcwv,
            )
            for att in dt.attrs:
                if isinstance(dt.attrs[att], str):
                    dt_new.attrs[att] = dt.attrs[att].lower()
                else:
                    dt_new.attrs[att] = dt.attrs[att]
            # print(dt_new)
            dt_new.to_zarr(out_file)


if __name__ == "__main__":
    # generate("SL2PP") # json
    generate("SLLCC")
    generate("LSTCD")
    generate("LSTED")
    generate("SLIRE")
    generate("TIRND")
    generate("IMSCD")
    generate("LSTVF")
    generate("LSTWV")
