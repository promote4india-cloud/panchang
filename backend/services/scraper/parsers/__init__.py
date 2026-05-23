"""
Per-template parsers. Importing this package triggers registration of all
parsers via @register_parser side-effects in each submodule.
"""

from . import festival as _festival  # noqa: F401  (registers festival_top|leaf|leaf_3d)
from . import muhurat as _muhurat   # noqa: F401  (registers muhurat_detail)
