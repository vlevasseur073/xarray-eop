from pathlib import Path

import datatree
import xarray as xr

from xarray_eop.conversion.utils import (
    extract_legacy,
    gen_static_adf_name,
    generate_datatree_from_legacy_adf,
)

in_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3",
)
out_path = Path(
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/SY2",
)
tmp_path = Path("/tmp")
_LOG_GENERATING_ADF = "*** Generating ADF "


def generate(adf_type: str) -> None:

    if adf_type == "SDRRT":
        for legacy_adf in ["S3A_SY_2_RAD_AX", "S3B_SY_2_RAD_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="syn l2 radiative transfer simulation data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "VGTRT":
        for legacy_adf in ["S3A_SY_2_RADPAX", "S3B_SY_2_RADPAX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="vgt-p radiative transfer simulation data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "VGSRT":
        for legacy_adf in ["S3A_SY_2_RADSAX", "S3B_SY_2_RADSAX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="vgt-s radiative transfer simulation data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "SYGCP":
        for legacy_adf in ["S3A_SY_1_GCPBAX", "S3B_SY_1_GCPBAX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="ground control points data base",
                ncgroup="OGPP_L1c_Tie_Points_Database",
            )
            dt.to_zarr(out_file)

    if adf_type == "SYCLP":
        for legacy_adf in ["S3A_SY_2_PCP_AX", "S3B_SY_2_PCP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                safe_file=["OL_2_CLP_AX.nc"],
                title="sy2 climatology data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "SYPPP":
        for legacy_adf in ["S3A_SY_2_PCP_AX", "S3B_SY_2_PCP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            dt = generate_datatree_from_legacy_adf(
                safe,
                safe_file=["OL_2_PPP_AX.nc"],
                title="sy2 pre-processing data file",
                dt=dt,
            )
            for ncgroup in ["classification_1", "classification_2"]:
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    safe_file=["OL_2_PPP_AX.nc"],
                    title="sy2 pre-processing data file",
                    ncgroup=ncgroup,
                    dt=dt,
                )
            # print(dt)
            dt.to_zarr(out_file)

    if adf_type == "SYSRF":
        for legacy_adf in ["S3A_SY_2_SPCPAX", "S3B_SY_2_SPCPAX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="vgt-p spectral response function data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "SYCDI":
        for legacy_adf in [
            "S3__SY_1_CDIBAX",
        ]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            baseline_collection = int(safe.name[-8:-5])

            # for tif_file in sorted(safe.glob("*.tif")):
            ds: list[xr.Dataset] = []
            for j in range(8):
                var: list[xr.Dataset] = []
                for i in range(4):
                    tif_file = f"distMap_0{j}0{i}_geoTIFF.tif"
                    var.append(
                        xr.open_dataset(
                            safe / tif_file,
                            chunks={"x": 4050, "y": 4050},
                        ).squeeze(drop=True),
                    )
                ds.append(xr.concat(var, dim="y"))
            ds_concat = xr.concat(ds, dim="x")
            ds_concat.attrs.update(
                {
                    "title": "Map File of the distance to the coast",
                    "baseline collection": f"{baseline_collection:03d}",
                    "resolution": "0.0028x0.0028 degrees",
                    "number_of_tile": 32,
                    "number_of_grid_points_in_longitude_per_tile": 16200,
                    "number_of_grid_points_in_latitude_per_tile": 16200,
                    "first_longitude_value": -180.0,
                    "last_longitude_value": 180.0,
                    "grid_step_in_longitude": 0.002777777777800,
                    "first_latitude_value": 90.0,
                    "last_latitude_value": -90.0,
                    "grid_step_in_latitude": -0.002777777777800,
                },
            )

            ds_concat.rename({"band_data": "distance_to_coast"}).to_zarr(out_file)

    if adf_type == "SYMCH":
        ancillary_adf = {
            "S3A_ADF_SYMCH": (
                ["S3A_OL_1_MCHDAX", "S3A_SL_1_MCHDAX"],
                "Inter-channel Spatial Misregistration Characterization Data File",
            ),
            "S3B_ADF_SYMCH": (
                ["S3B_OL_1_MCHDAX", "S3B_SL_1_MCHDAX"],
                "Inter-channel Spatial Misregistration Characterization Data File",
            ),
        }
        for adf in ancillary_adf:
            dt = datatree.DataTree(name="root")
            out_file = gen_static_adf_name(adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file

            title = ancillary_adf[adf][1]
            for legacy_adf in ancillary_adf[adf][0]:
                safe = extract_legacy(in_path, legacy_adf, tmp_path)
                baseline_collection = int(safe.name[-8:-5])

                group = "root"
                if "_OL_" in legacy_adf:
                    group = "olci"
                if "_SL_" in legacy_adf:
                    group = "slstr"
                for nc_file in safe.glob("*.nc4"):
                    dt_legacy = datatree.open_datatree(safe / nc_file)

                    ds = [
                        dt_legacy[g].to_dataset() for g in dt_legacy.groups if g != "/"
                    ]
                    band_index = [
                        g.split("_")[-1] for g in dt_legacy.groups if g != "/"
                    ]
                    ds = xr.concat(
                        ds,
                        xr.DataArray(band_index, name=f"{group}_band", dims="band"),
                    )
                    datatree.DataTree(name=group, parent=dt, data=ds)

            dt.attrs.update(
                {"title": title, "baseline_collection": f"{baseline_collection:03d}"},
            )
            dt.to_zarr(out_file)


if __name__ == "__main__":
    # generate("SDRRT")
    # generate("VGTRT")
    # generate("VGSRT")
    # generate("SYGCP")
    # generate("SYCLP")
    # generate("SYPPP")
    # generate("SYSRF")
    # generate("SYCDI")
    generate("SYMCH")
