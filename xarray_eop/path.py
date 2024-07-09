import os
import pathlib
import re

# Regular expression to match fsspec style protocols.
# Matches single slash usage too for compatibility.
_PROTOCOL_RE = re.compile(
    r"^(?P<zip>[A-Za-z][A-Za-z0-9+]*::)*(?P<protocol>[A-Za-z][A-Za-z0-9+]+):(?P<slashes>//?)(?P<path>.*)",
)


def _match_path_regex(path: str, grp: str | None = None) -> str:
    if grp is None:
        grp = "protocol"

    if m := _PROTOCOL_RE.match(path):
        # path = path.split("://")[1:]
        return m.group(grp)
    return ""


def _get_protocol(path: str) -> str:
    return _match_path_regex(path)


def _get_zip(path: str) -> str:
    zipped = _match_path_regex(path, "zip")
    if zipped:
        zipped = zipped[:-2]
    return zipped


def _strip_pattern(path: str, pattern: str) -> str:
    return path.replace(pattern, "")


class EOPath(pathlib.Path):
    """Classe deriving from pathlib.Path supporting object-storage path and fsspec-like URL chains.
    Currently it only zupport AWS *S3* protocol and *zip* storage, which means addresses like for instance:
    s3://bucket/prod/file or zip::s3://bucket/prod/file.zip

    Attributes
    ----------
    protocol: str
        empty for local file system, "s3" for S3 paths
    zip: str
        empty or "zip" if address starts with "zip::"

    Returns
    -------
        EOPath object
    """

    _flavour = pathlib._windows_flavour if os.name == "nt" else pathlib._posix_flavour

    def __new__(cls, *args, **kwargs):
        part0, *parts = args
        _protocol = _get_protocol(str(part0))
        _zip = _get_zip(str(part0))

        if cls is EOPath:
            if _protocol:
                part0 = _strip_pattern(str(part0), f"{_protocol}://")
                if _zip:
                    part0 = _strip_pattern(str(part0), f"{_zip}::")
            obj: EOPath = super().__new__(cls, part0, *parts)
            obj._protocol = _protocol
            obj._zip = _zip
            pathlib.Path.home()
            return obj

    @property
    def protocol(self) -> str:
        """Protocol of the path"""
        return self._protocol

    @property
    def zip(self) -> str:
        """Returns "zip" or empty string"""
        return self._zip

    @property
    def path(self) -> str:
        """Path without the protocole"""
        return super().__str__()

    @property
    def parent(self):
        """The logical parent of the path."""
        obj = super().parent
        obj._protocol = self.protocol
        obj._zip = self.zip
        return obj

    def absolute(self):
        """Return an absolute version of this path by prepending the current
        working directory. No normalization or symlink resolution is performed.

        Use resolve() to get the canonical path to a file.
        """
        if self.is_absolute():
            return self
        else:
            obj: EOPath = super()._from_parts([self.cwd()] + self._parts)
            obj._protocol = self.protocol
            obj._zip = self.zip
            return obj

    def _make_child(self, args):
        drv, root, parts = self._parse_args(args)
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv,
            self._root,
            self._parts,
            drv,
            root,
            parts,
        )
        obj: EOPath = self._from_parsed_parts(drv, root, parts)
        obj._protocol = self.protocol
        obj._zip = self.zip
        return obj

    def _make_child_relpath(self, part):
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self._parts + [part]
        obj: EOPath = self._from_parsed_parts(self._drv, self._root, parts)
        obj._protocol = self.protocol
        obj._zip = self.zip
        return obj

    def __str__(self):
        if self._protocol:
            if self._zip:
                return f"{self._zip}::{self._protocol}://{self.path}"
            else:
                return f"{self._protocol}://{self.path}"
        else:
            return self.path

    def __copy__(self):
        return EOPath(self.as_posix())

    @classmethod
    def home(cls):
        """Return a new path pointing to the user's home directory (as
        returned by os.path.expanduser('~')).
        """
        return cls("~").expanduser()

    def expanduser(self):
        """Return a new path with expanded ~ and ~user constructs
        (as returned by os.path.expanduser)
        """
        if not (self._drv or self._root) and self._parts and self._parts[0][:1] == "~":
            homedir = os.path.expanduser(self._parts[0])
            if homedir[:1] == "~":
                raise RuntimeError("Could not determine home directory.")
            obj: EOPath = super()._from_parts([homedir] + self._parts[1:])
            obj._protocol = self.protocol
            obj._zip = self.zip
            return obj
        return self
