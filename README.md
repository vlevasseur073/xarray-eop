# xarray_eop

xarray_eop is an xarray backend to open and manipulate EO data products from the Copernicus Sentinel mission, in the legacy SAFE format as well as the new zarr format used by the Re-engineered python processors.

## Installation

```shell
pip install xarray-eop
```

## Features

- specific xarray backends : ["sentinel-3","eop"] to be used with  `xarray.open_dataset` function
  - **sentinel-3**: handles Sentinel-3 SAFE product (.SEN3)
  - **eop**: Generic zarr product (.zarr) following the EOPF Product Structure Format
- Use of experimental xarray-datatree to represent the overall hierarchical data
- Conversion of products from SAFE to EOP Zarr
- Create empty products based on zmetadata template

## Get Started

### Open Sentinel-3 SAFE product

The `sentinel3` backend mainly consists of organizing the structure following the new EOP zarr Product Structure specification.
Simple datasets can be created from a specific netcdf file or a group corresponding to a valid EOP zarr path.
The whole product can be represented by the experimental DataTree hierarchical structure.

#### Dataset

```shell
import xarray as xr
from pathlib import Path

SAMPLE_PATH = Path("/Samples/Products/SAFE")
product = SAMPLE_PATH / "S3B_OL_1_EFR____20230506T015316_20230506T015616_20230711T065802_0180_079_117______LR1_D_NR_003.SEN3"

# Open a dataset from a specific netcdf file
ds = xr.open_dataset(product,file_or_group="instrument_data.nc",engine="sentinel-3")

# Open a dataset corresponding to a zarr group in the EOP structure
ds = xr.open_dataset(
    product,
    file_or_group="/measurements/image",
    engine="sentinel-3")
# or
ds = xr.open_dataset(
    product,
    file_or_group="/conditions/meteo",
    engine="sentinel-3",
    simplified_mapping=True
)
```

#### DataTree

```shell
from xarray_eop.sentinel3 import open_safe_datatree

dt = open_safe_datatree("prod",product,simplified_mapping=False)
```


### Open Sentinel-3 zarr product

#### Dataset

```shell
product = SAMPLE_PATH / "S3OLCEFR_20230506T015316_0180_B117_T931.zarr"
group = "measurements/image"
# Open with xarray zarr engine
ds=xr.open_dataset(SAMPLE_PATH / product / group, engine="zarr",chunks={})
# Open with custom engine="eop"
ds=xr.open_dataset(SAMPLE_PATH / product, group=group, engine="eop")
rad = ds.oa01_radiance
```

#### DataTree

```shell
dt = open_eop_datatree(product)
```

### Create empty product following template

```shell
ds = create_dataset_from_zmetadata(" SAMPLE_PATH / "S3OLCEFR_20230506T015316_0180_B117_T931.zarr"/.zmetadata")
```