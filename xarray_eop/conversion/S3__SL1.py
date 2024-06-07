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
    "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/SL1",
)
tmp_path = Path("/tmp")
_LOG_GENERATING_ADF = "*** Generating ADF "


def generate(adf_type: str) -> None:

    if adf_type == "SLANC":
        for legacy_adf in ["S3A_SL_1_ANC_AX", "S3B_SL_1_ANC_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            nc_file = [f for f in safe.glob("*.nc")]
            ds = Dataset(nc_file[0])
            dt = datatree.DataTree(name="root_adf")
            for group in ds.groups:
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    title="ancillary data file",
                    ncgroup=group,
                    dt=dt,
                )
            dt.attrs["title"] = "ancillary data file"
            dt.to_zarr(out_file)

    if adf_type == "SLGEC":
        merged_variables = [
            "quaternions_1",
            "quaternions_2",
            "quaternions_3",
            "quaternions_4",
        ]
        merged_mapping = {
            "quaternions": (
                merged_variables,
                "n_quaternions",
                {
                    "long_name": "Quaternions components. The thermo-elastic deformations are provided as quaternions covering one orbital revolution for a number of days in the year. The quaternions are derived from rotation angles from Instrument to Satellite.",
                },
            ),
        }
        # coordinates_variables = ['julian_days','on_orbit_positions_angle']

        for legacy_adf in ["S3A_SL_1_GEC_AX", "S3B_SL_1_GEC_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)

            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="geometric calibration data file",
                merged_variables=merged_variables,
                merged_mapping=merged_mapping,
                group="",
            )  # if group=None, by default subgroup maps is created if group=="" no subgroup
            dt.to_zarr(out_file)

    if adf_type == "SLGEO":
        for legacy_adf in ["S3A_SL_1_GEO_AX", "S3B_SL_1_GEO_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="geometry data file",
                group="",
            )
            dt.scans_cone_angle.attrs["long_name"] = (
                "Cone angle for each scan (nadir first, then oblique)"
            )
            dt.to_zarr(out_file)

    if adf_type == "SLCLO":
        for legacy_adf in ["S3A_SL_1_CLO_AX", "S3B_SL_1_CLO_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt: datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="cloud  lut data file",
                group="",
            )
            dt.to_zarr(out_file)

    if adf_type == "SLCDP":
        for legacy_adf in ["S3A_SL_1_CDP_AX", "S3B_SL_1_CDP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="probability look-up tables associated to cloudy conditions data file",
                group="",
            )
            # Add some attributes
            dt.c110.attrs["long_name"] = "Brigthness temperature at 11\u03BCm channel"
            dt.sst.attrs["long_name"] = "sea surface salinity"
            dt.sec_satz.attrs["long_name"] = "secant of Satellite Zenith Angle"
            dt.solz.attrs["long_name"] = "Solar Zenith Angle (reduced resolution)"
            dt.d110sst.attrs["long_name"] = "Difference between BT (11\u03BCm) and SST"
            dt.d110120.attrs["long_name"] = (
                "Difference between BT (11\u03BCm) and BT (12\u03BCm)"
            )
            dt.d037110.attrs["long_name"] = (
                "Difference between BT (3.7\u03BCm) and BT (11\u03BCm)"
            )
            dt.t110.attrs["long_name"] = "textural BT 11\u03BCm channel"
            dt.solz_1.attrs["long_name"] = "Solar Zenith Angle"
            dt.sst_1.attrs["long_name"] = "sea surface salinity (reduced resolution)"
            dt.c016.attrs["long_name"] = (
                "Reflectances on 1.6\u03BCm channel in cloudy conditions"
            )
            dt.c008.attrs["long_name"] = (
                "Reflectances on 0.87\u03BCm channel in cloudy conditions"
            )
            dt.c006.attrs["long_name"] = (
                "Reflectances on 0.66\u03BCm channel in cloudy conditions"
            )
            dt.d006008.attrs["long_name"] = (
                "Differences betwen R(0.66\u03BCm) and R(0.87\u03BCm)"
            )
            dt.tir_110_120.attrs["long_name"] = (
                "Spectral Probability density LUT for Thermal daytime (11\u03BCm, 12\u03BCm)"
            )
            dt.txt_110.attrs["long_name"] = (
                "Probability density LUT for day- and night-time thermal texture (LSD 11\u03BCm)"
            )
            dt.tir_037_110_120.attrs["long_name"] = (
                "Probability density LUT for Thermal nighttime (3.7\u03BCm, 11\u03BCm, 12\u03BCm)"
            )
            dt.vis_006_008.attrs["long_name"] = (
                "Spectral Probability density LUT associated with Joint daytime reflectance in cloudy conditions"
            )
            dt.to_zarr(out_file)

    if adf_type == "SLCLP":
        for legacy_adf in ["S3A_SL_1_CLP_AX", "S3B_SL_1_CLP_AX"]:
            safe = extract_legacy(in_path, legacy_adf, tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3], adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = generate_datatree_from_legacy_adf(
                safe,
                title="probability look-up tables associated to clear conditions data file",
                group="",
            )
            # Add some attributes
            dt.sec_satz.attrs["long_name"] = "secant of Satellite Zenith Angle"
            dt.solz.attrs["long_name"] = "Solar Zenith Angle (reduced resolution)"
            dt.t110.attrs["long_name"] = "textural BT 11\u03BCm channel"
            dt.txt_110.attrs["long_name"] = (
                "Probability density LUT for thermal texture (LSD 11\u03BCm)"
            )
            dt.to_zarr(out_file)

    if adf_type == "TIRCD":
        legacy_ADF = {
            "S3A": [
                "S3A_SL_1_N_S7AX",
                "S3A_SL_1_N_S8AX",
                "S3A_SL_1_N_S9AX",
                "S3A_SL_1_N_F1AX",
                "S3A_SL_1_N_F2AX",
                "S3A_SL_1_O_S7AX",
                "S3A_SL_1_O_S8AX",
                "S3A_SL_1_O_S9AX",
                "S3A_SL_1_O_F1AX",
                "S3A_SL_1_O_F2AX",
            ],
            "S3B": [
                "S3B_SL_1_N_S7AX",
                "S3B_SL_1_N_S8AX",
                "S3B_SL_1_N_S9AX",
                "S3B_SL_1_N_F1AX",
                "S3B_SL_1_N_F2AX",
                "S3B_SL_1_O_S7AX",
                "S3B_SL_1_O_S8AX",
                "S3B_SL_1_O_S9AX",
                "S3B_SL_1_O_F1AX",
                "S3B_SL_1_O_F2AX",
            ],
        }
        for sat in ["S3A", "S3B"]:
            out_file = gen_static_adf_name(sat, adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root_adf")
            for adf in legacy_ADF[sat]:
                safe = extract_legacy(in_path, adf, tmp_path)
                group = adf[9:13].lower()
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    title="thermal infrared characterisation data file",
                    coordinates_variable={  # variable : (dimention,coordinate)
                        "radiances": ("radiances_lut", "temperatures"),
                        "cal_uncertainty_uncertainty": (
                            "uncertainty_lut",
                            "cal_uncertainty_temperature",
                        ),
                        "non_linearities": ("non_linearities_lut", "detectors_count"),
                        "coffsets": ("offsets_lut", "voffsets"),
                    },
                    group=group,
                    dt=dt,
                )
            dt.to_zarr(out_file)

    if adf_type == "VSWCD":
        legacy_ADF = {
            "S3A": [
                "S3A_SL_1_N_S1AX",
                "S3A_SL_1_N_S2AX",
                "S3A_SL_1_N_S3AX",
                "S3A_SL_1_O_S1AX",
                "S3A_SL_1_O_S2AX",
                "S3A_SL_1_O_S3AX",
                "S3A_SL_1_NAS4AX",
                "S3A_SL_1_NAS5AX",
                "S3A_SL_1_NAS6AX",
                "S3A_SL_1_NBS4AX",
                "S3A_SL_1_NBS5AX",
                "S3A_SL_1_NBS6AX",
                "S3A_SL_1_OAS4AX",
                "S3A_SL_1_OAS5AX",
                "S3A_SL_1_OAS6AX",
                "S3A_SL_1_OBS4AX",
                "S3A_SL_1_OBS5AX",
                "S3A_SL_1_OBS6AX",
            ],
            "S3B": [
                "S3B_SL_1_N_S1AX",
                "S3B_SL_1_N_S2AX",
                "S3B_SL_1_N_S3AX",
                "S3B_SL_1_O_S1AX",
                "S3B_SL_1_O_S2AX",
                "S3B_SL_1_O_S3AX",
                "S3B_SL_1_NAS4AX",
                "S3B_SL_1_NAS5AX",
                "S3B_SL_1_NAS6AX",
                "S3B_SL_1_NBS4AX",
                "S3B_SL_1_NBS5AX",
                "S3B_SL_1_NBS6AX",
                "S3B_SL_1_OAS4AX",
                "S3B_SL_1_OAS5AX",
                "S3B_SL_1_OAS6AX",
                "S3B_SL_1_OBS4AX",
                "S3B_SL_1_OBS5AX",
                "S3B_SL_1_OBS6AX",
            ],
        }
        for sat in ["S3A", "S3B"]:
            out_file = gen_static_adf_name(sat, adf_type, format="zarr")
            print(_LOG_GENERATING_ADF + out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root_adf")
            for adf in legacy_ADF[sat]:
                safe = extract_legacy(in_path, adf, tmp_path)
                group = adf[9:13].lower()
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    title="visible and shortwave infrared characterisation data file",
                    coordinates_variable={  # variable : (dimention,coordinate)
                        "cal_uncertainty_uncertainty": (
                            "uncertainty_lut",
                            "cal_uncertainty_radiance",
                        ),
                        "non_linearities": ("lut", "detectors_count"),
                        "coffsets": ("channels", "voffsets"),
                    },
                    group=group,
                    dt=dt,
                )
            dt.to_zarr(out_file)

    if adf_type == "SLBDF":
        # Here the old zarr ADF has been updated to remove the coordinates variables
        old_zarr_path = Path(
            "/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr/SL1",
        )
        files = [f for f in old_zarr_path.glob("S3*SLBDF*.zarr")]
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
            # dt = datatree.open_datatree(files[0],engine="zarr",chunks={})
            dt_new = datatree.DataTree(name="root_adf")
            coordinates = {
                "x": -c.x,
                "y": -c.y,
            }
            # print(coordinates)
            biome = maps.biome.assign_coords(coordinates)
            datatree.DataTree(name="maps", parent=dt_new, data=biome)
            # print(dt_new)
            dt_new.to_zarr(out_file)


if __name__ == "__main__":
    # generate('SL1PP') #json
    generate("SLADF")
    generate("SLANC")
    generate("SLGEO")
    generate("SLGEC")
    generate("SLCLO")
    generate("SLCDP")
    generate("SLCLP")
    generate("TIRCD")
    generate("VSWCD")
    generate("SLBDF")
    # generate('SLADJ') # json
