"""Helper utilities shared across standalone scripts.

The project keeps several large demo datasets in Git LFS.  When a clone is
performed without the binary payloads, the repository will contain tiny text
files that merely point to the real artefacts.  Attempting to load those
placeholders with pandas or xarray results in confusing parsing errors.  The
helpers below provide a single, well documented check that the requested
dataset is actually present before downstream logic tries to open it.
"""

from __future__ import annotations

from pathlib import Path

LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


class DatasetUnavailableError(RuntimeError):
    """Raised when a requested dataset is missing or replaced by a pointer."""


def ensure_materialised(path: Path | str) -> Path:
    """Return ``path`` if the referenced file contains real data.

    Parameters
    ----------
    path:
        Location of the dataset relative to the project root.

    Raises
    ------
    FileNotFoundError
        If the file does not exist on disk.
    DatasetUnavailableError
        If the file is a Git LFS pointer instead of the real payload.
    """

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"Expected dataset at {resolved} but it was not found. "
            "Fetch the required demo assets before running this script."
        )

    with resolved.open("rb") as handle:
        header = handle.read(len(LFS_POINTER_PREFIX))

    if header.startswith(LFS_POINTER_PREFIX):
        raise DatasetUnavailableError(
            "The dataset at "
            f"{resolved} is a Git LFS pointer. Run `git lfs install` followed by "
            "`git lfs pull` (or otherwise provide the dataset) before using this "
            "script."
        )

    return resolved

