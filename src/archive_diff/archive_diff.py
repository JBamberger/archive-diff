"""
Diffing implementation.
"""

from __future__ import annotations

import pathlib as pl
from typing import List, Tuple

from archive_diff.archive_format_handler import DispatchingArchiveHandler, HashRecord
from archive_diff.diff_data import DiffState, DiffRecord, ArchiveDiff
from archive_diff.file_comparison import FileHasher


def compute_listing_diff(
        listing1: List[HashRecord], listing2: List[HashRecord]) -> List[DiffRecord]:
    """
    Computes a simple diff between the two listings. The diff only compares files and directories
    with the same path.

    :param listing1: First archive listing
    :param listing2: Second archive listing
    :return: List of diff records, one for each path present in at least one of the two listings.
    """
    listing1.sort(key=lambda x: x.path_parts)
    listing2.sort(key=lambda x: x.path_parts)

    # Since the listings are sorted by their path we can simply traverse the listings in parallel,
    # always proceeding with the listing where the next record has the lexicographically smaller
    # path. Where we proceed determines the diff output for the given record.
    records = []
    i, j = 0, 0
    while i < len(listing1) and j < len(listing2):
        left = listing1[i]
        right = listing2[j]
        if left.relpath == right.relpath:
            records.append(DiffRecord(
                left.relpath, DiffState.EQUAL if left.hash == right.hash else DiffState.DIFFERENT))
            i += 1
            j += 1
        elif left.relpath < right.relpath:
            records.append(DiffRecord(left.relpath, DiffState.ONLY_LEFT))
            i += 1
        else:
            records.append(DiffRecord(right.relpath, DiffState.ONLY_RIGHT))
            j += 1
    # When the first pass is completed, one of the lists might not have been traversed fully. These
    # loops deal with the remaining items.
    while i < len(listing1):
        records.append(DiffRecord(listing1[i].relpath, DiffState.ONLY_LEFT))
        i += 1
    while j < len(listing2):
        records.append(DiffRecord(listing2[j].relpath, DiffState.ONLY_RIGHT))
        j += 1

    return records


def find_common_prefix(lst: List[HashRecord]) -> List[str]:
    """
    Function finds the longest common prefix between all the records. The function ignores directory
     records that are fully contained within the prefix. The function identifies directories that
     contain all files in the listing.

    :param lst: Archive listing.
    :return: prefix common to all records in the archive listing.
    """
    root = {}
    for record in lst:
        parts = record.path_parts if record.hash is None else record.path_parts[:-1]

        tree = root
        for part in parts:
            if part not in tree:
                tree[part] = {}
            tree = tree[part]

        if record.hash is not None:
            try:
                tree[record.path_parts[-1]] = '__file__'
            except TypeError as error:
                raise ValueError(f'The record structure is not valid. '
                                 f'The same path is reused multiple times: '
                                 f'{"/".join(record.path_parts[:-1])}') from error

    prefix = []
    tree = root
    while True:
        keys = tree.keys()
        if len(keys) == 1:
            key = next(iter(keys))
            val = tree[key]
            if isinstance(val, dict):
                prefix.append(key)
                tree = val
            else:
                break
        else:
            break
    return prefix


def strip_prefix_from_records(lst: List[HashRecord]) -> Tuple[List[str], List[HashRecord]]:
    """
    Finds and removes a prefix common to all records in an archive listing. A new archive listing is
    returned where all prefix directories are filtered out and the paths of each record don't
    contain the path prefix anymore.

    For details on the prefix computation see `find_common_prefix()`.

    :param lst: Input archive listing
    :return: New listing without prefix records and path segments.
    """
    prefix = find_common_prefix(lst)

    prefix_len = len(prefix)
    list_no_prefix = []
    for record in lst:
        if len(record.path_parts) <= prefix_len:
            # This filters out the directory entries forming the prefix path.
            continue

        list_no_prefix.append(HashRecord(record.hash, record.path_parts[prefix_len:]))

    return prefix, list_no_prefix


class ArchiveDiffer:
    """
    Basic archive diffing tool.
    """

    def __init__(self, keep_prefix: bool, hash_algorithm: str, hash_buffer_size=128 * 1024):
        """
        :param keep_prefix: True to keep the archive path prefixes, i.e. compare as they are.
        :param hash_algorithm:  String describing a hash algorithm supported by `hashlib`
        :param hash_buffer_size: Size of the read buffer used by stream hashing implementation
        """
        self.keep_prefix = keep_prefix
        self._file_hasher = FileHasher(hash_algorithm, hash_buffer_size)
        self._format_handler = DispatchingArchiveHandler(self._file_hasher)

    def compute_hash_listing(self, in_file: pl.Path) -> List[HashRecord]:
        """
        Enumerates and hashes the contents of the provided input archive or directory.

        :param in_file: Input path.
        :raises ArchiveFormatError: If the input file type is not supported or accessible.
        :return: List of hashed content objects.
        """

        # Canonical input path with all links and relative parts resolved.
        in_file = in_file.absolute().resolve(strict=True)

        return list(
            filter(lambda x: x.hash is not None, self._format_handler.compute_listing(in_file)))

    def compute_diff(self, left_archive: pl.Path, right_archive: pl.Path) -> ArchiveDiff:
        """
        Computes a full diff between the archives located at the given paths.
        :param left_archive: Path to the first archive.
        :param right_archive: Path to the second archive.
        :return: Diff between the archives.
        """
        listing1 = self.compute_hash_listing(left_archive)
        listing2 = self.compute_hash_listing(right_archive)

        if not self.keep_prefix:
            # This sorts the listings by their canonical path.
            prefix1, listing1 = strip_prefix_from_records(listing1)
            prefix2, listing2 = strip_prefix_from_records(listing2)
        else:
            prefix1 = []
            prefix2 = []

        records = compute_listing_diff(listing1, listing2)

        return ArchiveDiff(
            prefix_left='/'.join(prefix1),
            prefix_right='/'.join(prefix2),
            records=records
        )
