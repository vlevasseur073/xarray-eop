from .api import open_datatree
from .credentials import get_credentials, get_s3filesystem
from .eop import (
    create_dataset_from_zmetadata,
    create_datatree_from_zmetadata,
    datatree_to_uml,
)
from .path import EOPath

try:
    # NOTE: the `_version.py` file must not be present in the git repository
    #   as it is generated by setuptools at install time
    from ._version import __version__
except ImportError:  # pragma: no cover
    # Local copy or not installed with setuptools
    __version__ = "999"

__all__ = [
    "open_datatree",
    "EOPath",
    "datatree_to_uml",
    "create_dataset_from_zmetadata",
    "create_datatree_from_zmetadata",
    "get_credentials",
    "get_s3filesystem",
]
