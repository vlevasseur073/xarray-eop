import xarray as xr
from pathlib import Path
from xarray_safe.sentinel3 import create_dataset_from_zmetadata

SAMPLE_PATH = Path("/mount/internal/work-st/projects/cs-412/2078-dpr/workspace/vlevasseur/SYN")
product = SAMPLE_PATH / "S3A_OL_1_EFR____20191227T124111_20191227T124411_20221125T100245_0179_053_109______LR1_D_NT_003.SEN3/"

# ds = xr.open_dataset(product,file_or_group="instrument_data.nc",engine="sentinel-3")
# ds = xr.open_dataset(
#     product,
#     file_or_group="/measurements/image",
#     engine="sentinel-3")
ds = xr.open_dataset(
    product,
    file_or_group="/conditions/meteo",
    engine="sentinel-3",
    simplified_mapping=True
)

# ds = create_dataset_from_zmetadata("/mount/internal/work-st/projects/cs-412/2078-dpr/Samples/Products/Zarr_Beta/S3OLCEFR_20230506T015316_0180_B117_T740.zarr/.zmetadata")