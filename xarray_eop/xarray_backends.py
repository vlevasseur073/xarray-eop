import os
from typing import Any, Dict, Optional, Tuple

import xarray as xr

from xarray_eop import eop, sentinel3
from xarray_eop.credentials import get_credentials_from_env
from xarray_eop.path import EOPath


class Sentinel3Backend(xr.backends.common.BackendEntrypoint):
    def open_dataset(
        self,
        filename_or_obj: str,
        *,
        file_or_group: str,
        drop_variables: Optional[Tuple[str]] = None,
        storage_options: Optional[Dict[str, Any]] = None,
        simplified_mapping: Optional[bool] = None,
        fs_copy: Optional[bool] = None,
    ) -> xr.Dataset:
        url: EOPath = EOPath(filename_or_obj)
        if url.protocol and not storage_options:
            creds = get_credentials_from_env(url)
            if url.protocol == "s3":
                creds["s3"].pop("region_name", None)
                storage_options = creds

        return sentinel3.open_sentinel3_dataset(
            filename_or_obj,
            file_or_group,
            drop_variables=drop_variables,
            storage_options=storage_options,
            simplified_mapping=simplified_mapping,
            fs_copy=fs_copy,
        )

    def guess_can_open(self, filename_or_obj: Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".safe", ".safe/"}


class EOPBackend(xr.backends.common.BackendEntrypoint):
    def open_dataset(  # type: ignore
        self,
        filename_or_obj: str,
        *,
        drop_variables: Optional[Tuple[str]] = None,
        group: Optional[str] = None,
        storage_options: Optional[Dict[str, Any]] = None,
        decode_times: bool | None = None,
    ) -> xr.Dataset:
        return eop.open_eop_dataset(
            filename_or_obj,
            drop_variables=drop_variables,
            group=group,
            storage_options=storage_options,
            decode_times=decode_times,
        )

    def guess_can_open(self, filename_or_obj: Any) -> bool:
        try:
            _, ext = os.path.splitext(filename_or_obj)
        except TypeError:
            return False
        return ext.lower() in {".zarr", ".zarr/"}
