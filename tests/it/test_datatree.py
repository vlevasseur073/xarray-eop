from typing import Any

import dask as da
import datatree
import pytest

from xarray_eop.api import open_datatree
from xarray_eop.path import EOPath


def check_datatree_sample(dt: datatree.DataTree[Any]) -> None:
    assert "other_metadata" in dt.attrs  # nosec
    assert "measurements" in dt  # nosec
    assert "coarse" in dt["measurements"]  # nosec
    assert "fine" in dt["measurements"]  # nosec
    assert "var1" in dt["measurements/coarse"].variables  # nosec
    var1 = dt["measurements/coarse/var1"]
    assert var1.shape == (2, 3)  # nosec


@pytest.mark.integration
def test_load_dataset() -> None:
    dt = open_datatree("s3://buc-acaw-dpr/testdata/sentineltoolbox/ut/data/sample.zarr")
    check_datatree_sample(dt)

    dt = open_datatree(
        "zip::s3://buc-acaw-dpr/testdata/sentineltoolbox/ut/data/sample.zarr.zip",
    )
    check_datatree_sample(dt)


@pytest.mark.integration
def test_open_safe_legacy_datatree_without_fscopy() -> None:
    buc_name = EOPath("s3://buc-acaw-dpr")
    dt = open_datatree(
        buc_name
        / "Samples/SAFE"
        / "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3",
        fs_copy=False,
    )
    assert "measurements" in dt
    assert isinstance(dt.measurements, datatree.DataTree)
    assert isinstance(dt.measurements.oa01_radiance.data, da.array.core.Array)
    assert dt.conditions.instrument.relative_spectral_covariance.dims == (
        "bands1",
        "bands2",
    )


@pytest.mark.integration
def test_open_safe_legacy_datatree_with_fscopy() -> None:
    buc_name = EOPath("s3://buc-acaw-dpr")
    dt = open_datatree(
        buc_name
        / "Samples/SAFE"
        / "S3B_OL_1_ERR____20230506T015316_20230506T015616_20230711T065804_0179_079_117______LR1_D_NR_003.SEN3",
        fs_copy=True,
    )
    assert "measurements" in dt
    assert isinstance(dt.measurements, datatree.DataTree)
    assert isinstance(dt.measurements.oa01_radiance.data, da.array.core.Array)
    assert dt.conditions.instrument.relative_spectral_covariance.dims == (
        "bands1",
        "bands2",
    )
