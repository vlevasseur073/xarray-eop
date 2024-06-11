from typing import Any

import datatree
import pytest

from xarray_eop.api import open_datatree


def check_datatree_sample(dt: datatree.DataTree[Any]) -> None:
    assert "other_metadata" in dt.attrs  # nosec
    assert "measurements" in dt  # nosec
    assert "coarse" in dt["measurements"]  # nosec
    assert "fine" in dt["measurements"]  # nosec
    assert "var1" in dt["measurements/coarse"].variables  # nosec
    var1 = dt["measurements/coarse/var1"]
    assert var1.shape == (2, 3)  # nosec


@pytest.mark.unit
def test_open_datatree() -> None:
    dt = open_datatree("tests/ut/data/sample.zarr")
    check_datatree_sample(dt)
    assert dt["measurements/coarse/var1"].chunks is not None

    dt = open_datatree("tests/ut/data/sample.zip", engine="zarr")
    check_datatree_sample(dt)
    assert dt["measurements/coarse/var1"].chunks is not None
