# __version__ = "0.0.1"
try:
    # NOTE: the `_version.py` file must not be present in the git repository
    #   as it is generated by setuptools at install time
    from ._version import __version__
except ImportError:  # pragma: no cover
    # Local copy or not installed with setuptools
    __version__ = "999"