import os
from typing import Any

import s3fs

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
    """Get credentials from environment variable
    For S3 protocol, it looks for the AWS-like (``AWS_ACCESS_KEY_ID``,``AWS_SECRET_ACCESS_KEY``,``AWS_ENDPOINT_URL``)
    or S3-like (``S3_KEY``,``S3_SECRET``,``S3_URL``) environment variables.


    Parameters
    ----------
    url: EOPath
        object-storage path

    Returns
    -------
        dictionary of secrets parameter to be used in storage_options parameters for xarray/datatree functions

    Raises
    ------
    NotImplementedError
        Currently, only S3 protocol is handled
    """
    if url.protocol != "s3":
        raise NotImplementedError(f"Protocol {url.protocol} not yet implemented")

    if url.protocol == "s3":
        storage_options = _s3_from_env()

    return storage_options


def get_credentials(url: EOPath | str, profile: str | None = None) -> dict[str, Any]:
    """Get credentials given an url path
    For S3 protocol, it looks first for the AWS-like (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``,
    ``AWS_ENDPOINT_URL``) or S3-like (``S3_KEY``, ``S3_SECRET``, ``S3_URL``) environment variables, or if a profile
    is given

    Note that only S3 protocol is implemented and the use of a profile name is not yet implemented

    Parameters
    ----------
    url
        cloud-storage path
    profile, optional
        profile name to get the correct credentials, by default None. Not yet implemented

    Returns
    -------
        dictionary of secret variables to be used in storage_options parameters for xarray/datatree functions

    Raises
    ------
    NotImplementedError
        * cloud-storage different from S3
        * use of profile name
    """
    if isinstance(url, str):
        url = EOPath(url)

    if url.protocol != "s3":
        raise NotImplementedError(f"Protocol {url.protocol} not yet implemented")

    if not profile:
        return get_credentials_from_env(EOPath(url))
    else:
        raise NotImplementedError(
            "Use of a profile for the credentials is not yet implemented",
        )


def get_s3filesystem(
    url: EOPath | str,
    profile: str | None = None,
    anon: bool = False,
) -> s3fs.S3FileSystem:
    """Get S3 File System from an url.
    Credentials are automatically retrieved from environment variables or profile name

    Parameters
    ----------
    url
        s3 path
    profile, optional
        profile name to get the correct credentials, by default None. Not yet implemented
    anon, optional
        by default False

    Returns
    -------
        `s3fs.S3FileSystem` object

    Raises
    ------
    NotImplementedError
        if profile is not None
    ValueError
        if url is not a S3 path
    """
    if profile:
        raise NotImplementedError(
            "Use of a profile for the credentials is not yet implemented",
        )

    if isinstance(url, str):
        s3_path = EOPath(url)
    else:
        s3_path = url
    if s3_path.protocol != "s3":
        raise ValueError(f"Path {str(s3_path)} is not a S3 path")

    creds = get_credentials(s3_path)
    if not creds or anon:
        return s3fs.S3FileSystem(anon=True)
    else:
        try:
            endpoint_url = creds["s3"]["endpoint_url"]
        except KeyError:
            endpoint_url = creds["s3"]["client_kwargs"]["endpoint_url"]
        return s3fs.S3FileSystem(
            key=creds["s3"]["key"],
            secret=creds["s3"]["secret"],
            endpoint_url=endpoint_url,
        )
