from unittest import TestCase

from archive_diff.archive_diff import DirArchiveHandler, FileHasher, HashRecord, ZipArchiveHandler, TarArchiveHandler, \
    SevenZipArchiveHandler, path_parts, compute_listing_diff, DiffRecord, DiffState
import pathlib as pl


class TestArchiveHandler(TestCase):
    test_file_root = pl.Path(__file__).parent / 'test_files'

    def exercise_ArchiveHandler(self, handler, path):
        expected_result = [
            HashRecord(None, 'simple_archive'),
            HashRecord(None, 'simple_archive/dir_in_archive'),
            HashRecord('4de84c100c44d1192d815515bfa7d95e', 'simple_archive/dir_in_archive/file_in_dir.txt'),
            HashRecord('25057e0905daa7e55d180a279565cb61', 'simple_archive/file_in_root.txt'),
        ]
        self.assertTrue(handler.check_file(path))

        listing = sorted(handler.compute_listing(path), key=lambda x: x.relpath)
        self.assertEqual(expected_result, listing)

    def test_dir_handler(self):
        self.exercise_ArchiveHandler(
            DirArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive'
        )

    def test_zip_handler(self):
        self.exercise_ArchiveHandler(
            ZipArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.zip'
        )

    def test_tar_handler(self):
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar'
        )

    def test_tgz_handler(self):
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar.gz'
        )
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tgz'
        )

    def test_tbz2_handler(self):
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar.bz2'
        )
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tbz2'
        )

    def test_txz_handler(self):
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.tar.xz'
        )
        self.exercise_ArchiveHandler(
            TarArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.txz'
        )

    def test_7z_handler(self):
        self.exercise_ArchiveHandler(
            SevenZipArchiveHandler(hasher=FileHasher(hash_algorithm='md5')),
            self.test_file_root / 'simple_archive.7z'
        )


class TestDiffAlgorithm(TestCase):
    # def test_build_diff_tree(self):
    #     self.fail()

    def test_compute_listing_diff_simple(self):
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
        left = [HashRecord(None, 'root')]
        right = [HashRecord('hash_file', 'root')]
        expected_result = [DiffRecord('root', DiffState.DIFFERENT)]

        self.assertEqual(expected_result, compute_listing_diff(left, right))


class TestUtilityFunctions(TestCase):

    def test_path_parts(self):
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
