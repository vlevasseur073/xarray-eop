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
    """
    Function to open tree data (zarr sentinel product) from bucket or local path and open it as :obj:`datatree.DataTree`

    .. note::

        Data are lazy loaded. To fully load data in memory, prefer :obj:`~sentineltoolbox.api.load_datatree`


    Optional arguments are related to the engine ("SAFE" or "zarr") and must be passed by keys

    Parameters
    ----------
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
            print(kwargs["backend_kwargs"])
        return open_eop_datatree(url, **kwargs)
    else:
        if creds:
            creds["s3"].pop("region_name", None)
            kwargs["backend_kwargs"] = {"storage_options": creds}
        simplified_mapping = use_custom_mapping(url)
        return open_safe_datatree(url, simplified_mapping=simplified_mapping, **kwargs)
