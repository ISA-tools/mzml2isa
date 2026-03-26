"""Helpers for importing PyFilesystem without noisy deprecation warnings."""

import warnings


with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"pkg_resources is deprecated as an API\.",
        category=UserWarning,
    )
    import fs
    import fs.errors
    import fs.path
