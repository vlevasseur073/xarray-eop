import datatree
from netCDF4 import Dataset
from pathlib import Path
import xarray as xr
from xarray_eop.conversion.utils import extract_legacy
from xarray_eop.conversion.utils import gen_static_adf_name
from xarray_eop.conversion.utils import generate_datatree_from_legacy_adf

in_path = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3")
out_path = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/SY2")
tmp_path =  Path("/tmp")
_LOG_GENERATING_ADF="*** Generating ADF "

def generate(adf_type: str)->None:
    
    if adf_type == "SDRRT":
        for legacy_adf in ["S3A_SY_2_RAD_AX","S3B_SY_2_RAD_AX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="syn l2 radiative transfer simulation data file",
                group="")
            dt.to_zarr(out_file)
    
    if adf_type == "VGTRT":
        for legacy_adf in ["S3A_SY_2_RADPAX","S3B_SY_2_RADPAX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="vgt-p radiative transfer simulation data file",
                group="")
            dt.to_zarr(out_file)
    
    if adf_type == "VGSRT":
        for legacy_adf in ["S3A_SY_2_RADSAX","S3B_SY_2_RADSAX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="vgt-s radiative transfer simulation data file",
                group="")
            dt.to_zarr(out_file)
    
    if adf_type == "SYGCP":
        for legacy_adf in ["S3A_SY_1_GCPBAX","S3B_SY_1_GCPBAX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="ground control points data base",
                ncgroup = "OGPP_L1c_Tie_Points_Database")
            dt.to_zarr(out_file)
    
    if adf_type == "SYCLP":
        for legacy_adf in ["S3A_SY_2_PCP_AX","S3B_SY_2_PCP_AX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                safe_file = ["OL_2_CLP_AX.nc"],
                title="sy2 climatology data file",
                group=""
            )
            dt.to_zarr(out_file)
    
    if adf_type == "SYPPP":
        for legacy_adf in ["S3A_SY_2_PCP_AX","S3B_SY_2_PCP_AX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            dt = generate_datatree_from_legacy_adf(
                safe,
                safe_file=["OL_2_PPP_AX.nc"],
                title="sy2 pre-processing data file",
                dt=dt
            )
            for ncgroup in ["classification_1","classification_2"]:
                dt = generate_datatree_from_legacy_adf(
                    safe,
                    safe_file=["OL_2_PPP_AX.nc"],
                    title="sy2 pre-processing data file",
                    ncgroup=ncgroup,
                    dt=dt
                )
            # print(dt)
            dt.to_zarr(out_file)
   
    if adf_type == "SYSRF":
        for legacy_adf in ["S3A_SY_2_SPCPAX","S3B_SY_2_SPCPAX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                safe,
                title="vgt-p spectral response function data file",
                group=""
            )
            dt.to_zarr(out_file)
    


if __name__ == "__main__":
    generate("SDRRT")
    generate("VGTRT")
    generate("VGSRT")
    generate("SYGCP")
    generate("SYCLP")
    generate("SYPPP")
    generate("SYSRF")

