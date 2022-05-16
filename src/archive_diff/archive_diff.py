import argparse
import math
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum, auto
import hashlib as hl
import os
import pathlib as pl
import tarfile
import zipfile
from dataclasses import dataclass
from typing import NamedTuple, Iterator, List, Optional, Callable, Union, Tuple, Dict


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

    def stats(self) -> Dict[DiffState, int]:
        counts = {s: 0 for s in DiffState}
        for r in self.records:
            counts[r.result] += 1

        return counts


class FileHasher:
    def __init__(self, hash_algorithm: str, hash_buffer_size=128 * 1024):
        self.hash_algorithm = hash_algorithm
        self.hash_buffer_size = hash_buffer_size

    def compute_hash(self, io):
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


class ArchiveFormatError(Exception):
    """
    Error class thrown by archive file hashing functions if the input file format is not supported.
    """
    pass


class ArchiveFormatHandler(ABC):

    def __init__(self, hasher: FileHasher):
        self._hasher = hasher

    def _compute_file_hash(self, file) -> str:
        return self._hasher.compute_hash(file)

    @abstractmethod
    def check_file(self, path: pl.Path) -> bool:
        """
        Checks if the given path can be processed by this handler.

        :param path: Input path
        :return: True, if the path is a valid archive for this handler.
        """
        raise NotImplementedError()

    @abstractmethod
    def compute_listing(self, path: pl.Path) -> Iterator[HashRecord]:
        """
        Lists the files and folders in the given archive and computes hash values for each of the files.

        :param path: Input path
        :raises ArchiveFormatError: If the input is not supported by this handler.
        :return: Hashed contents of the archive in no particular order.
        """
        raise NotImplementedError()


class ZipArchiveHandler(ArchiveFormatHandler):

    def check_file(self, path: pl.Path) -> bool:
        return path.is_file() and zipfile.is_zipfile(path)

    def compute_listing(self, path: pl.Path) -> Iterator[HashRecord]:

        if not self.check_file(path):
            raise ArchiveFormatError('Not a zip file.')

        with zipfile.ZipFile(path, "r") as archive:
            for m in archive.infolist():
                if not m.is_dir():
                    with archive.open(m, 'r') as file:
                        h = self._compute_file_hash(file)
                    yield HashRecord(h, m.filename)
                else:
                    yield HashRecord(None, m.filename)


class TarArchiveHandler(ArchiveFormatHandler):

    def check_file(self, path: pl.Path) -> bool:
        return path.is_file() and tarfile.is_tarfile(path)

    def compute_listing(self, path: pl.Path) -> Iterator[HashRecord]:
        if not self.check_file(path):
            raise ArchiveFormatError('Not a tar file.')

        with tarfile.open(path, mode='r', ) as archive:
            for m in archive.getmembers():
                if m.isfile():
                    with archive.extractfile(m) as file:
                        h = self._compute_file_hash(file)
                    yield HashRecord(h, m.name)
                else:
                    yield HashRecord(None, m.name)


class DirArchiveHandler(ArchiveFormatHandler):

    def check_file(self, path: pl.Path) -> bool:
        return path.is_dir()

    def compute_listing(self, path: pl.Path) -> Iterator[HashRecord]:
        if not self.check_file(path):
            raise ArchiveFormatError('File is not a directory.')

        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                yield HashRecord(None, os.path.relpath(os.path.join(root, dir_name), path))

            for file_name in files:
                file_path = os.path.join(root, file_name)
                with open(file_path, 'rb') as reader:
                    h = self._compute_file_hash(reader)
                yield HashRecord(h, os.path.relpath(file_path, path))


class ArchiveDiffer:
    def __init__(self, keep_prefix: bool, hash_algorithm: str, hash_buffer_size=128 * 1024):
        self.keep_prefix = keep_prefix
        self._file_hasher = FileHasher(hash_algorithm, hash_buffer_size)

    def compute_hash_listing(self, in_file: pl.Path) -> List[HashRecord]:
        """
        Enumerates and hashes the contents of the provided input archive or directory.

        :param in_file: Input path.
        :raises ArchiveFormatError: If the input file type is not supported or accessible.
        :return: List of hashed content objects.
        """

        def type_independent_listing(archive_path: pl.Path) -> Iterator[HashRecord]:
            for handler in format_handlers:
                if handler.check_file(archive_path):
                    return handler.compute_listing(archive_path)

            raise ArchiveFormatError('Could not find handler that supports the given archive type.')

        format_handlers = [
            ZipArchiveHandler(self._file_hasher),
            TarArchiveHandler(self._file_hasher),
            DirArchiveHandler(self._file_hasher),
        ]

        # Canonical input path with all links and relative parts resolved.
        in_file = in_file.absolute().resolve(strict=True)

        return list(filter(lambda x: x.hash is not None, type_independent_listing(in_file)))

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

            list_no_prefix = []
            for record in lst:
                if len(record.relpath) <= prefix_len:
                    # This filters out the directory entries forming the prefix path.
                    continue

                canonical_path = '/'.join(record.relpath[prefix_len:])
                list_no_prefix.append(CanonicalHashRecord(canonical_path, record.hash))

            list_no_prefix.sort(key=lambda x: x.relpath)

            return prefix, list_no_prefix

        # This sorts the listings by their canonical path.
        prefix1, listing1 = to_canonical_listing(listing1)
        prefix2, listing2 = to_canonical_listing(listing2)

        # Since the listings are sorted by their path we can simply traverse the listings in parallel, always proceeding
        # with the listing where the next record has the lexicographically smaller path. Where we proceed determines
        # the diff output for the given record.
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

        # When the first pass is completed, one of the lists might not have been traversed fully. These loops deal with
        # the remaining items.
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
