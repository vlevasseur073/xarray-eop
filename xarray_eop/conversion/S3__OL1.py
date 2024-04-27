import datatree
import netCDF4 as nc
import pandas as pd
from pathlib import Path
import rioxarray as rio
import xarray as xr
from xarray_eop.conversion.utils import extract_legacy
from xarray_eop.conversion.utils import gen_static_adf_name
from xarray_eop.conversion.utils import generate_datatree_from_legacy_adf
from xarray_eop.conversion.utils import lower
from xarray_eop.conversion.utils import DEFAULT_COMPRESSOR

in_path = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/SAFE/S3")
out_path = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Auxiliary/Zarr_new/OL1")
tmp_path =  Path("/tmp")
_LOG_GENERATING_ADF="*** Generating ADF "

def generate(adf_type: str)->None:

    if adf_type == "OLLUT":
        for legacy_adf in ["S3A_OL_1_CLUTAX","S3B_OL_1_CLUTAX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            for ncgroup in ["bright_reflectance","sun_glint_risk"]:
                dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol1 classification thresholds luts data file contains",
                    ncgroup=ncgroup,
                    dt=dt
                )
            dt.to_zarr(out_file)
    
    if adf_type == "OLINS":
        for legacy_adf in ["S3A_OL_1_INS_AX","S3B_OL_1_INS_AX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            nc_ds = nc.Dataset(safe/"OL_1_INS_AX.nc")
            ncgroups = nc_ds.groups.keys()
            for ncgroup in ncgroups:
                dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol1 characterisation and models data file",
                    ncgroup=ncgroup,
                    dt=dt
                )
            dt.attrs.update({attr:nc_ds.getncattr(attr) for attr in nc_ds.ncattrs()})
            dt.to_zarr(out_file)
    
    if adf_type == "OLCAL":
        for legacy_adf in ["S3A_OL_1_CAL_AX","S3B_OL_1_CAL_AX"]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            nc_ds = nc.Dataset(safe/"OL_1_CAL_AX.nc")
            ncgroups = nc_ds.groups.keys()
            for ncgroup in ncgroups:
                dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol1 calibration data file",
                    ncgroup=ncgroup,
                    dt=dt
                )
            dt.attrs.update({attr:nc_ds.getncattr(attr) for attr in nc_ds.ncattrs()})
            dt.to_zarr(out_file)
    
    if adf_type == "OLPRG":
        for legacy_adf in ["S3A_OL_1_PRG_AX","S3B_OL_1_PRG_AX",]:
            safe = extract_legacy(in_path,legacy_adf,tmp_path)
            out_file = gen_static_adf_name(legacy_adf[0:3],adf_type,format="zarr")
            print(_LOG_GENERATING_ADF+out_file)
            out_file = out_path / out_file
            dt = datatree.DataTree(name="root")
            nc_ds = nc.Dataset(safe/"OL_1_PRG_AX.nc")
            ncgroups = nc_ds.groups.keys()
            for ncgroup in ncgroups:
                dt:datatree.DataTree = generate_datatree_from_legacy_adf(
                    safe,
                    title="ol1 programmation data file",
                    ncgroup=ncgroup,
                    dt=dt
                )
            dt.attrs.update({attr:nc_ds.getncattr(attr) for attr in nc_ds.ncattrs()})
            dt.to_zarr(out_file)
    


if __name__ == "__main__":
    generate("OLLUT")
    generate("OLINS")
    generate("OLCAL")
    generate("OLPRG")

