import importlib.util
import pathlib as pl
import unittest
from unittest import TestCase

from archive_diff.archive_format_handler import HashRecord, DirArchiveHandler, ZipArchiveHandler, \
    TarArchiveHandler
from archive_diff.file_comparison import FileHasher


class TestArchiveHandler(TestCase):
    """
    Tests the various archive format handlers.
    """
    test_file_root = pl.Path(__file__).parent / 'test_files'

    def exercise_archive_handler(self, handler, path):
        """
        Checks the results of the given handler and input path.
        :param handler: Handler to test
        :param path: Path to the test archive.
        """
        expected_result = [
            HashRecord(None, 'simple_archive'),
            HashRecord(None, 'simple_archive/dir_in_archive'),
            HashRecord('4de84c100c44d1192d815515bfa7d95e',
                       'simple_archive/dir_in_archive/file_in_dir.txt'),
            HashRecord('25057e0905daa7e55d180a279565cb61', 'simple_archive/file_in_root.txt'),
        ]
        self.assertTrue(handler.check_file(path))

        listing = sorted(handler.compute_listing(path), key=lambda x: x.relpath)
        self.assertEqual(expected_result, listing)

    def test_dir_handler(self):
        """
        Tests the `DirArchiveHandler`.
        """
        self.exercise_archive_handler(
            DirArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive'
        )

    def test_zip_handler(self):
        """
        Tests the `ZipArchiveHandler`.
        """
        self.exercise_archive_handler(
            ZipArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.zip'
        )

    def test_tar_handler(self):
        """
        Tests the `TarArchiveHandler` without compression.
        """
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar'
        )

    def test_tgz_handler(self):
        """
        Tests the `TarArchiveHandler` with gzip compression.
        """
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar.gz'
        )
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tgz'
        )

    def test_tbz2_handler(self):
        """
        Tests the `TarArchiveHandler` with bzip2 compression.
        """
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar.bz2'
        )
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tbz2'
        )

    def test_txz_handler(self):
        """
        Tests the `TarArchiveHandler` with xz compression.
        """
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar.xz'
        )
        self.exercise_archive_handler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.txz'
        )

    @unittest.skipIf(importlib.util.find_spec('py7zr') is None,
                     'py7zr is not installed, 7z support is disabled.')
    def test_7z_handler(self):
        """
        Tests the `SevenZipArchiveHandler`.
        """
        from archive_diff.archive_format_handler import SevenZipArchiveHandler

        self.exercise_archive_handler(
            SevenZipArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.7z'
        )


if __name__ == '__main__':
    unittest.main()
