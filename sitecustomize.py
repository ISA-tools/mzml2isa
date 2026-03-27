"""Repository-local interpreter customizations.

This suppresses a known warning emitted by the unmaintained `fs` dependency
when it imports `pkg_resources` on modern setuptools versions.
"""

import warnings


warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API\.",
    category=UserWarning,
)
