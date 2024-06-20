import pytest

from xarray_eop import EOPath
from xarray_eop.credentials import get_credentials, get_s3filesystem


@pytest.mark.unit
def test_credentials() -> None:
    url = EOPath("s3://buc-acaw-dpr/")

    creds = get_credentials(url)
    assert "key" in creds["s3"].keys()
    assert "secret" in creds["s3"].keys()
    assert "endpoint_url" in creds["s3"].keys()

    s3fs = get_s3filesystem(url)
    assert s3fs
    assert s3fs.exists(url.path)
