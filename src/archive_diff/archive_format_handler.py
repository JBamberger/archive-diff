from __future__ import annotations

import os
import pathlib as pl
import tarfile
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Optional, Union, List

from archive_diff.file_comparison import FileHasher
from archive_diff.utils import path_parts


@dataclass
class HashRecord:
    hash: Optional[str]

    def __init__(self, hash, relpath: Union[str, List[str]]) -> None:
        self.hash = hash.lower() if hash is not None else None
        self._path_parts = path_parts(relpath) if isinstance(relpath, str) else list(relpath)
        self._relpath = '/'.join(self._path_parts)

    @property
    def path_parts(self) -> List[str]:
        return self._path_parts

    @property
    def relpath(self) -> str:
        return self._relpath


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

        # The parent dir is always defined. If we are in the actual file system root, e.g. '/', 'D:\'..., calling parent
        # returns the file system root again.
        archive_root = path.parent

        yield HashRecord(None, os.path.relpath(path, archive_root))

        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                yield HashRecord(None, os.path.relpath(os.path.join(root, dir_name), archive_root))

            for file_name in files:
                file_path = os.path.join(root, file_name)
                with open(file_path, 'rb') as reader:
                    h = self._compute_file_hash(reader)
                yield HashRecord(h, os.path.relpath(file_path, archive_root))


try:
    import py7zr


    class SevenZipArchiveHandler(ArchiveFormatHandler):

        def check_file(self, path: pl.Path) -> bool:
            return path.is_file() and py7zr.is_7zfile(path)

        def compute_listing(self, path: pl.Path) -> Iterator[HashRecord]:
            if not self.check_file(path):
                raise ArchiveFormatError('Not a 7z file.')

            with py7zr.SevenZipFile(path, "r") as archive:
                file_contents = archive.readall()

                for fi in archive.list():
                    if fi.is_directory:
                        yield HashRecord(None, fi.filename)
                    else:
                        h = self._compute_file_hash(file_contents[fi.filename])
                        yield HashRecord(h, fi.filename)

except ImportError:
    py7zr = None


class DispatchingArchiveHandler(ArchiveFormatHandler):

    def __init__(self, hasher: FileHasher):
        super(DispatchingArchiveHandler, self).__init__(hasher)
        self._format_handlers = [
            ZipArchiveHandler(hasher),
            TarArchiveHandler(hasher),
            DirArchiveHandler(hasher),
        ]
        if py7zr is not None:
            self._format_handlers.append(
                SevenZipArchiveHandler(hasher)
            )

    def _get_handler_for_file(self, path: pl.Path) -> ArchiveFormatHandler:
        for handler in self._format_handlers:
            if handler.check_file(path):
                return handler

        raise ArchiveFormatError('Could not find handler that supports the given archive type.')

    def check_file(self, path: pl.Path) -> bool:
        try:
            handler = self._get_handler_for_file(path)
            return handler is not None
        except ArchiveFormatError:
            return False

    def compute_listing(self, path: pl.Path) -> Iterator[HashRecord]:
        handler = self._get_handler_for_file(path)
        return handler.compute_listing(path)
