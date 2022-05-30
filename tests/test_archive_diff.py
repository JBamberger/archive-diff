"""
Test cases.
"""
import pathlib as pl
from unittest import TestCase

from archive_diff.archive_diff import compute_listing_diff, find_common_prefix, \
    strip_prefix_from_records
from archive_diff.archive_format_handler import ZipArchiveHandler, TarArchiveHandler, \
    DirArchiveHandler, SevenZipArchiveHandler, HashRecord
from archive_diff.diff_data import DiffState, DiffRecord
from archive_diff.file_comparison import FileHasher
from archive_diff.utils import path_parts


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

    def test_7z_handler(self):
        """
        Tests the `SevenZipArchiveHandler`.
        """
        self.exercise_archive_handler(
            SevenZipArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.7z'
        )


class TestDiffAlgorithm(TestCase):
    """
    Tests the diffing algorithm.
    """

    def test_compute_listing_diff_simple(self):
        """
        Simple diff with all diff states.
        """
        left = [
            HashRecord('hash_left', 'root/only_left'),
            HashRecord('hash_left', 'root/different'),
            HashRecord('hash_same', 'root/same'),
        ]
        right = [
            HashRecord('hash_right', 'root/only_right'),
            HashRecord('hash_right', 'root/different'),
            HashRecord('hash_same', 'root/same'),
        ]
        expected_result = [
            DiffRecord('root/different', DiffState.DIFFERENT),
            DiffRecord('root/only_left', DiffState.ONLY_LEFT),
            DiffRecord('root/only_right', DiffState.ONLY_RIGHT),
            DiffRecord('root/same', DiffState.EQUAL),
        ]

        self.assertEqual(expected_result, compute_listing_diff(left, right))

    def test_compute_listing_diff_simple_unordered(self):
        """
        Simple diff with all diff states, unsorted listings.
        """
        left = [
            HashRecord('hash_same', 'root/same'),
            HashRecord('hash_left', 'root/different'),
            HashRecord('hash_left', 'root/only_left'),
        ]
        right = [
            HashRecord('hash_right', 'root/only_right'),
            HashRecord('hash_same', 'root/same'),
            HashRecord('hash_right', 'root/different'),
        ]
        expected_result = [
            DiffRecord('root/different', DiffState.DIFFERENT),
            DiffRecord('root/only_left', DiffState.ONLY_LEFT),
            DiffRecord('root/only_right', DiffState.ONLY_RIGHT),
            DiffRecord('root/same', DiffState.EQUAL),
        ]

        self.assertEqual(expected_result, compute_listing_diff(left, right))

    def test_compute_listing_diff_multi_root(self):
        """
        Diff with differing archive roots.
        """
        left = [
            HashRecord('hash_left', 'only_left'),
            HashRecord('hash_left', 'different'),
            HashRecord('hash_same', 'same'),
        ]
        right = [
            HashRecord('hash_right', 'only_right'),
            HashRecord('hash_right', 'different'),
            HashRecord('hash_same', 'same'),
        ]
        expected_result = [
            DiffRecord('different', DiffState.DIFFERENT),
            DiffRecord('only_left', DiffState.ONLY_LEFT),
            DiffRecord('only_right', DiffState.ONLY_RIGHT),
            DiffRecord('same', DiffState.EQUAL),
        ]

        self.assertEqual(expected_result, compute_listing_diff(left, right))

    def test_compute_listing_diff_with_dirs(self):
        """
        Diff containing directory records.
        """
        left = [
            HashRecord(None, 'root'),
            HashRecord('hash_left', 'root/only_left'),
            HashRecord('hash_left', 'root/different'),
            HashRecord('hash_same', 'root/same'),
        ]
        right = [
            HashRecord(None, 'root'),
            HashRecord('hash_right', 'root/only_right'),
            HashRecord('hash_right', 'root/different'),
            HashRecord('hash_same', 'root/same'),
        ]
        expected_result = [
            DiffRecord('root', DiffState.EQUAL),
            DiffRecord('root/different', DiffState.DIFFERENT),
            DiffRecord('root/only_left', DiffState.ONLY_LEFT),
            DiffRecord('root/only_right', DiffState.ONLY_RIGHT),
            DiffRecord('root/same', DiffState.EQUAL),
        ]

        self.assertEqual(expected_result, compute_listing_diff(left, right))

    def test_compute_listing_diff_dir_to_file(self):
        """
        Diff between directory and file
        """
        left = [HashRecord(None, 'root')]
        right = [HashRecord('hash_file', 'root')]
        expected_result = [DiffRecord('root', DiffState.DIFFERENT)]

        self.assertEqual(expected_result, compute_listing_diff(left, right))


class TestUtilityFunctions(TestCase):
    """
    Tests the utility functions.
    """

    def test_find_common_prefix(self):
        """
        Simple prefix detection.
        """
        listing = [
            HashRecord(None, 'root/hello'),
            HashRecord('hash', 'root/foo'),
            HashRecord('hash', 'root/hello/world'),
        ]
        expected_prefix = ['root']

        self.assertEqual(expected_prefix, find_common_prefix(listing))

    def test_find_common_prefix_with_dir(self):
        """
        Prefix detection with prefix dir.
        """
        listing = [
            HashRecord(None, 'root'),
            HashRecord(None, 'root/hello'),
            HashRecord('hash', 'root/foo'),
            HashRecord('hash', 'root/hello/world'),
        ]
        expected_prefix = ['root']

        self.assertEqual(expected_prefix, find_common_prefix(listing))

    def test_find_common_prefix_no_common(self):
        """
        Prefix detection without common prefix.
        """
        listing = [
            HashRecord(None, 'hello'),
            HashRecord('hash', 'hello/world'),
            HashRecord('hash', 'root/foo'),
            HashRecord('hash', 'root/bar'),
        ]
        expected_prefix = []

        self.assertEqual(expected_prefix, find_common_prefix(listing))

    def test_find_common_prefix_with_dirs(self):
        """
        Prefix detection with partial prefix dir.
        """
        listing = [
            HashRecord(None, 'root'),
            HashRecord(None, 'root/hello'),
            HashRecord('hash', 'root/hello/world'),
            HashRecord('hash', 'root/hello/foo'),
            HashRecord('hash', 'root/hello/bar'),
        ]
        expected_prefix = ['root', 'hello']

        self.assertEqual(expected_prefix, find_common_prefix(listing))

    def test_find_common_prefix_only_dirs(self):
        """
        Prefix detection without files.
        :return:
        """
        listing = [
            HashRecord(None, 'root'),
            HashRecord(None, 'root/hello'),
            HashRecord(None, 'root/hello/foo'),
            HashRecord(None, 'root/hello/bar'),
        ]
        expected_prefix = ['root', 'hello']

        self.assertEqual(expected_prefix, find_common_prefix(listing))

    def test_find_common_prefix_mixed(self):
        """
        Prefix detection with mixed files and dirs.
        :return:
        """
        listing = [
            HashRecord(None, 'root'),
            HashRecord(None, 'root/hello'),
            HashRecord(None, 'root/world'),
            HashRecord('hash', 'root/hello/foo'),
            HashRecord('hash', 'root/hello/bar'),
        ]
        expected_prefix = ['root']

        self.assertEqual(expected_prefix, find_common_prefix(listing))

    def test_strip_prefix_from_records(self):
        """
        Tests prefix stripping.
        """
        listing = [
            HashRecord(None, 'root'),
            HashRecord(None, 'root/hello'),
            HashRecord('hash_2', 'root/hello/world'),
            HashRecord('hash_3', 'root/foo'),
            HashRecord('hash_4', 'root/bar'),
        ]
        expected_prefix = ['root']
        expected_listing = [
            HashRecord(None, 'hello'),
            HashRecord('hash_2', 'hello/world'),
            HashRecord('hash_3', 'foo'),
            HashRecord('hash_4', 'bar'),
        ]

        result_prefix, result_listing = strip_prefix_from_records(listing)

        self.assertEqual(expected_prefix, result_prefix)
        self.assertEqual(expected_listing, result_listing)

    def test_path_parts(self):
        """
        Tests path splitting.
        """
        # Unix-style
        self.assertEqual([], path_parts('/'))
        self.assertEqual(['hello'], path_parts('/hello'))
        self.assertEqual(['hello', 'world'], path_parts('/hello/world'))
        self.assertEqual(['hello', 'world'], path_parts('/hello/world/'))

        # Windows-style
        self.assertEqual([], path_parts('C:\\'))
        self.assertEqual(['hello'], path_parts('C:\\hello'))
        self.assertEqual(['hello', 'world'], path_parts('C:\\hello\\world'))
        self.assertEqual(['hello', 'world'], path_parts('C:\\hello\\world\\'))

        # Mixed / and \
        self.assertEqual(['hello', 'world'], path_parts('C:\\hello\\world/'))

        # How should we handle network paths?
        # self.assertEqual(['192.168.0.1', 'world'], path_parts('\\\\192.168.0.1\\world\\'))
