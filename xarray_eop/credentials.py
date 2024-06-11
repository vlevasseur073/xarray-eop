import os
from typing import Any

from xarray_eop.path import EOPath


def _s3_env_variables_found() -> bool:
    for envvar in {"S3_KEY", "S3_SECRET", "S3_URL"}:
        if envvar not in os.environ:
            return False
    return True


def _aws_env_variables_found() -> bool:
    for envvar in {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL"}:
        if envvar not in os.environ:
            return False
    return True


def _s3_from_env() -> dict[str, Any]:
    s3_vars: dict[str, Any] = {}

    if _aws_env_variables_found():
        s3_vars["key"] = os.environ["AWS_ACCESS_KEY_ID"]
        s3_vars["secret"] = os.environ["AWS_SECRET_ACCESS_KEY"]
        s3_vars["endpoint_url"] = os.environ["AWS_ENDPOINT_URL"]
        s3_vars["region_name"] = os.environ.get("AWS_DEFAULT_REGION", "")
    elif _s3_env_variables_found():
        s3_vars["key"] = os.environ["S3_KEY"]
        s3_vars["secret"] = os.environ["S3_SECRET"]
        s3_vars["endpoint_url"] = os.environ["S3_URL"]
        s3_vars["region_name"] = os.environ.get("S3_REGION", "")

    return {"s3": s3_vars}


def get_credentials_from_env(url: EOPath) -> dict[str, Any]:
    if url.protocol != "s3":
        raise NotImplementedError(f"Protocol {url.protocol} not yet implemented")

    if url.protocol == "s3":
        storage_options = _s3_from_env()

    return storage_options
