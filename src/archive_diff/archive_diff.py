import argparse
import math
from collections import defaultdict
from enum import Enum, auto
import hashlib as hl
import os
import pathlib as pl
import tarfile
import zipfile
from dataclasses import dataclass
from typing import NamedTuple, Iterator, List, Optional, Callable, Union, Tuple


@dataclass
class HashRecord:
    hash: Optional[str]
    relpath: List[str]

    def __init__(self, hash, relpath: Union[str, List[str]]) -> None:
        self.hash = hash

        if isinstance(relpath, str):
            self.relpath = []
            rest = relpath
            while True:
                rest, part = os.path.split(rest)
                self.relpath.append(part)
                if not rest:
                    break
            self.relpath.reverse()
        else:
            self.relpath = list(relpath)


class DiffState(Enum):
    """
    Enumeration that describes possible difference states for a single file path in the archive.
    """

    EQUAL = auto()
    DIFFERENT = auto()
    ONLY_LEFT = auto()
    ONLY_RIGHT = auto()


@dataclass
class DiffRecord:
    """
    This record represents an archive file path with the associated difference state between the two inputs.
    """
    relpath: str
    result: DiffState


@dataclass
class ArchiveDiff:
    """
    This class contains the full results of an archive diff.
    """
    prefix_left: str
    prefix_right: str
    records: List[DiffRecord]


class ArchiveFormatError(Exception):
    """
    Error class thrown by archive file hashing functions if the input file format is not supported.
    """
    pass


class ArchiveDiffer:
    def __init__(self, keep_prefix: bool, hash_algorithm: str, hash_buffer_size=128 * 1024):
        self.keep_prefix = keep_prefix
        self.hash_algorithm = hash_algorithm
        self.hash_buffer_size = hash_buffer_size

    def compute_file_hash(self, io):
        """
        Computes the hash sum for an input io object.
        :param io: input io object
        :return: string with the hex representation of the hash
        """
        m = hl.new(self.hash_algorithm)
        while True:
            data = io.read(self.hash_buffer_size)
            if not data:
                break
            m.update(data)
        return m.hexdigest()

    def compute_hash_listing(self, in_file: pl.Path) -> List[HashRecord]:
        """
        Enumerates and hashes the contents of the provided input archive or directory.

        The function first dispatches to a concrete archive format handler by file extension and tries each handler as a
        fallback if the extension-based handler failed. If all handlers fail, the method raises a ValueError.

        :param in_file: Input path.
        :raises ValueError: If the input file type is not supported or accessible.
        :return: List of hashed content objects.
        """

        def compute_listing_zip(in_file: pl.Path) -> Iterator[HashRecord]:
            """
            Lists the files and folders in the given zip file and computes hash values for each of the files.
            :param in_file: Input file
            :raises ArchiveFormatError: If the input is not a valid zip file.
            :return: Hashed contents of the archive in no particular order.
            """
            if not zipfile.is_zipfile(in_file):
                raise ArchiveFormatError('Not a zip file.')

            with zipfile.ZipFile(in_file, "r") as archive:
                for m in archive.infolist():
                    if not m.is_dir():
                        with archive.open(m, 'r') as file:
                            h = self.compute_file_hash(file)
                        yield HashRecord(h, m.filename)
                    else:
                        yield HashRecord(None, m.filename)

        def compute_listing_tar(in_file: pl.Path) -> Iterator[HashRecord]:
            """
            Lists the files and folders in the given tar file and computes hash values for each of the files. This function
            supports tar files with gzip, xz, bz2 and without compression.
            :param in_file: Input file
            :raises ArchiveFormatError: If the input is not a valid tar file.
            :return: Hashed contents of the archive in no particular order.
            """
            if not tarfile.is_tarfile(in_file):
                raise ArchiveFormatError('Not a tar file.')

            with tarfile.open(in_file, mode='r', ) as archive:
                for m in archive.getmembers():
                    if m.isfile():
                        with archive.extractfile(m) as file:
                            h = self.compute_file_hash(file)
                        yield HashRecord(h, m.name)
                    else:
                        yield HashRecord(None, m.name)

        def compute_listing_dir(in_file: pl.Path) -> Iterator[HashRecord]:
            """
            Lists the files and folders in the given directory and computes hash values for each of the files.
            :param in_file: Input directory
            :raises ArchiveFormatError: If the input is not a directory.
            :return: Hashed contents of the archive in no particular order.
            """
            if not in_file.is_dir():
                raise ArchiveFormatError('File is not a directory.')

            for root, dirs, files in os.walk(in_file):
                for dir_name in dirs:
                    yield HashRecord(None, os.path.relpath(os.path.join(root, dir_name), in_file))

                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    with open(file_path, 'rb') as reader:
                        h = self.compute_file_hash(reader)
                    yield HashRecord(h, os.path.relpath(file_path, in_file))

        class FormatHandler(NamedTuple):
            handle: Callable[[pl.Path], Iterator[HashRecord]]
            extensions: List[str]

        # Available archive format handlers
        format_handlers = [
            FormatHandler(compute_listing_tar, ['.tar', '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2', '.txz']),
            FormatHandler(compute_listing_zip, ['.zip']),
        ]

        # Mapping from file extension to format handler
        extension_map = {ext: h.handle for h in format_handlers for ext in h.extensions}
        fallback_handlers = [h.handle for h in format_handlers]

        # Canonical input path with all links and relative parts resolved.
        in_file = in_file.absolute().resolve(strict=True)

        if in_file.is_dir():
            return list(compute_listing_dir(in_file))
        elif in_file.is_file():
            f = extension_map.get(in_file.suffix, None)
            handlers = ([f] if f is not None else []) + fallback_handlers

            for handler_function in handlers:
                try:
                    return list(handler_function(in_file))
                except ArchiveFormatError:
                    # The handler could not deal with the given file format, try the next handler
                    continue

        raise ValueError('File path does not point to a valid archive file or directory.')

    def compute_diff_impl(self, listing1: List[HashRecord], listing2: List[HashRecord]) -> ArchiveDiff:
        """
        Computes the difference between two archive content listings.

        :param listing1: Listing of the left archive
        :param listing2: Listing of the right archive
        :return: Diff descriptor
        """

        class CanonicalHashRecord(NamedTuple):
            relpath: str
            hash: str

        def find_common_prefix(lst: List[HashRecord]) -> List[str]:

            # Empty and single-item lists have no common prefix
            if len(lst) < 2:
                return []

            prefix = lst[0].relpath
            for record in lst:
                relpath = record.relpath

                new_prefix = []
                for a, b in zip(prefix, relpath):
                    if a == b:
                        new_prefix.append(a)
                    else:
                        break

                if len(new_prefix) == 0:
                    return []

                prefix = new_prefix

            return prefix

        def to_canonical_listing(lst: List[HashRecord]) -> Tuple[List[str], List[CanonicalHashRecord]]:
            if self.keep_prefix:
                prefix = []
            else:
                prefix = find_common_prefix(lst)

            prefix_len = len(prefix)

            list_no_prefix = [CanonicalHashRecord('/'.join(r.relpath[prefix_len:]), r.hash) for r in lst]
            list_no_prefix.sort(key=lambda x: x.relpath)

            return prefix, list_no_prefix

        prefix1, listing1 = to_canonical_listing(listing1)
        prefix2, listing2 = to_canonical_listing(listing2)

        records = []
        i, j = 0, 0
        while i < len(listing1) and j < len(listing2):
            v1 = listing1[i]
            v2 = listing2[j]
            if v1.relpath == v2.relpath:
                records.append(DiffRecord(v1.relpath, DiffState.EQUAL if v1.hash == v2.hash else DiffState.DIFFERENT))
                i += 1
                j += 1
            elif v1.relpath < v2.relpath:
                records.append(DiffRecord(v1.relpath, DiffState.ONLY_LEFT))
                i += 1
            else:
                records.append(DiffRecord(v2.relpath, DiffState.ONLY_RIGHT))
                j += 1

        while i < len(listing1):
            records.append(DiffRecord(listing1[i].relpath, DiffState.ONLY_LEFT))
            i += 1
        while j < len(listing2):
            records.append(DiffRecord(listing2[j].relpath, DiffState.ONLY_RIGHT))
            j += 1

        return ArchiveDiff(
            '/'.join(prefix1),
            '/'.join(prefix2),
            records
        )

    def compute_diff(self, left_archive: pl.Path, right_archive: pl.Path) -> ArchiveDiff:
        listing1 = self.compute_hash_listing(left_archive)
        listing2 = self.compute_hash_listing(right_archive)

        return self.compute_diff_impl(listing1, listing2)


def print_diff(archive_diff: ArchiveDiff, *, suppress_common_lines=False) -> None:
    """
    Prints the diff object as in a human-readable format to the standard output.

    :param archive_diff: diff object
    """
    divider = '*' * 80

    print(divider)

    if archive_diff.prefix_left != archive_diff.prefix_right:
        print('Prefixes differ:')
        print('Prefix 1:', archive_diff.prefix_left)
        print('Prefix 2:', archive_diff.prefix_right)
        print(divider)

    state_to_name = {
        DiffState.EQUAL: 'Equal',
        DiffState.DIFFERENT: 'Different',
        DiffState.ONLY_LEFT: 'Only left',
        DiffState.ONLY_RIGHT: 'Only right',
    }
    state_to_symbol = {
        DiffState.EQUAL: ' ',
        DiffState.DIFFERENT: '|',  # The actual diff tool uses '/' for the last line of each differing block.
        DiffState.ONLY_LEFT: '<',
        DiffState.ONLY_RIGHT: '>',
    }
    longest_path = max(len(r.relpath) for r in archive_diff.records)
    record_template = f'{{rel_path:{longest_path}s}} {{state_sym:s}} {{state_name:s}}'

    counts_per_state = defaultdict(lambda: 0)
    for record in archive_diff.records:
        counts_per_state[record.result] += 1

        if (not suppress_common_lines) or (record.result != DiffState.EQUAL):
            print(record_template.format(
                rel_path=record.relpath,
                state_sym=state_to_symbol[record.result],
                state_name=state_to_name[record.result]))

    print(divider)

    max_count = int(math.ceil(math.log10(max(counts_per_state.values()))))
    pattern = f'{{state_name:11s}} {{state_count:{max_count:d}d}}'
    for state in DiffState:
        print(pattern.format(state_name=state_to_name[state] + ":", state_count=counts_per_state[state]))

    print(divider)
