import pathlib

import pytest

from xarray_eop.path import EOPath


@pytest.mark.unit
def test_eopath() -> None:
    a = EOPath("/path/to/product")

    assert isinstance(a, EOPath)
    assert a.name == "product"
    assert a.parent == EOPath("/path/to")
    assert a.parent.path == "/path/to"
    assert a.protocol == ""
    assert a.zip == ""

    a = EOPath("path/to/product")
    assert a.absolute() == EOPath.cwd() / "path/to/product"

    a = EOPath("s3://bucket/product/")
    assert a.name == "product"
    assert a.protocol == "s3"
    assert a.as_posix() == "s3://bucket/product"

    a = EOPath("zip::s3://bucket/product.zip")
    assert a.name == "product.zip"
    assert a.zip == "zip"

    b = EOPath(a)
    assert isinstance(b, EOPath)
    assert str(b) == str(a)
    assert b.protocol == a.protocol
    assert b.zip == a.zip

    c = EOPath(pathlib.Path("/path/to/product"))
    assert isinstance(c, EOPath)

    d = EOPath("/path/to") / "product"
    assert str(d) == "/path/to/product"
