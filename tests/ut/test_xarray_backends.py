import dask as da
import pytest
import xarray as xr

from xarray_eop.path import EOPath


@pytest.mark.unit
def test_open_s3_legacy_dataset() -> None:
    ds = xr.open_dataset(
        "tests/ut/data/S3B_OL_1_ERR_sample.SEN3",
        file_or_group="instrument_data.nc",
        engine="sentinel-3",
    )
    assert ds is not None
    assert isinstance(ds.lambda0.data, da.array.core.Array)
    assert ds.relative_spectral_covariance.dims == ("bands1", "bands2")

    ds = xr.open_dataset(
        "tests/ut/data/S3B_OL_1_ERR_sample.SEN3",
        file_or_group="/conditions/instrument",
        engine="sentinel-3",
    )

    assert ds is not None
    assert isinstance(ds.lambda0.data, da.array.core.Array)
    assert ds.relative_spectral_covariance.dims == ("bands1", "bands2")

    buc_name = EOPath("s3://buc-acaw-dpr")
    ds = xr.open_dataset(
        buc_name
        / "Samples/SAFE"
        / "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3",
        file_or_group="instrument_data.nc",
        engine="sentinel-3",
    )
    assert ds is not None
    assert isinstance(ds.lambda0.data, da.array.core.Array)
    assert ds.relative_spectral_covariance.dims == ("bands1", "bands2")
