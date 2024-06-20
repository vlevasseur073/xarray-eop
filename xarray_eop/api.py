from pathlib import Path
from typing import Any

import datatree

from xarray_eop.conversion.utils import use_custom_mapping
from xarray_eop.credentials import get_credentials_from_env
from xarray_eop.eop import open_eop_datatree
from xarray_eop.path import EOPath
from xarray_eop.sentinel3 import open_safe_datatree


def open_datatree(
    product_urlpath: str | Path,
    *,
    engine: str | None = None,
    **kwargs: Any,
) -> datatree.DataTree[Any]:
    """Open a tree data (zarr sentinel product) from bucket or local file system, based on :obj:`datatree.DataTree`

    Parameters
    ----------
    product_urlpath
        Product path. It could be local path such as "/path/to/product/", S3 bucket location as "s3://bucket/product"
        or fsspec-like chained url as "zip::s3://bucket/product.zip"
    engine, optional
        engine to be used by xarray among ["zarr","SAFE"], by default None. It will try to guess the engine given the
        product extension

    Returns
    -------
        :obj:`datatree.DataTree`

    Raises
    ------
    ValueError
        if chunks is explicitely set to None
    NotImplementedError
        if engine not in ["zarr","SAFE"]
    """

    url = EOPath(product_urlpath)

    creds: dict[str, Any] | None = None
    if url.protocol:
        creds = get_credentials_from_env(url)

    if "chunks" not in kwargs:
        kwargs["chunks"] = {}
    else:
        if kwargs["chunks"] is None:
            raise ValueError(
                "open_datatree(chunks=None) is not allowed. Use load_datatree instead to avoid lazy loading data",
            )

    if engine:
        kwargs["engine"] = engine
    else:
        ext = url.suffixes
        if ".zarr" in ext:
            kwargs["engine"] = "zarr"
        elif ".SEN3" in ext:
            kwargs["engine"] = "SAFE"
        else:
            raise NotImplementedError(f"Engine {engine} not implemented")

    if kwargs["engine"] == "zarr":
        if creds:
            creds["s3"].pop("region_name", None)
            kwargs["backend_kwargs"] = {"storage_options": creds}
        return open_eop_datatree(url, **kwargs)
    else:
        if creds:
            creds["s3"].pop("region_name", None)
            kwargs["backend_kwargs"] = {"storage_options": creds}
        simplified_mapping = use_custom_mapping(url)
        return open_safe_datatree(url, simplified_mapping=simplified_mapping, **kwargs)
