"""
Archive diff tool
"""

from .__version__ import (
    __author__,
    __author_email__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)

from .diff_data import (
    DiffState,
    DiffRecord,
    DiffTreeNode,
    DiffTreeDirNode,
    DiffTreeFileNode,
    ArchiveDiff,
    build_diff_tree,
)

from .archive_format_handler import (
    DispatchingArchiveHandler,
    ArchiveFormatError,
    HashRecord,
    FileHasher,
)

from .archive_diff import (
    ArchiveDiffer,
    compute_listing_diff,
    strip_prefix_from_records,
    find_common_prefix,
)

from .cli_output import (
    print_diff,
    DiffPrinter,
)
