from unittest import TestCase

from archive_diff.archive_diff import DirArchiveHandler, FileHasher, HashRecord, ZipArchiveHandler, TarArchiveHandler, \
    SevenZipArchiveHandler
import pathlib as pl


class Test(TestCase):
    test_file_root = pl.Path(__file__).parent / 'test_files'

    # def test_build_diff_tree(self):
    #     self.fail()

    def exercise_ArchiveHandler(self, handler, path):
        expected_result = [
            HashRecord(None, 'simple_archive'),
            HashRecord(None, 'simple_archive/dir_in_archive'),
            HashRecord('4de84c100c44d1192d815515bfa7d95e', 'simple_archive/dir_in_archive/file_in_dir.txt'),
            HashRecord('25057e0905daa7e55d180a279565cb61', 'simple_archive/file_in_root.txt'),
        ]
        self.assertTrue(handler.check_file(path))

        listing = sorted(handler.compute_listing(path), key=lambda x: x.relpath)
        self.assertEqual(listing, expected_result)

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


"""
MD5             2FD9829A9EB52F9F631AEAD603380E55                                       test_left/different.txt
MD5             AB01D8557C269BF2086F6D341061E994                                       test_left/only_left.txt
MD5             87EED8A89A67FC20C740C125F2AF7D82                                       test_left/same.txt
MD5             E82A5E70EBACADF263F41FEF36ED12C2                                       test_right/different.txt
MD5             E72277F92E25A87704150596DB2EF54D                                       test_right/only_right.txt
MD5             87EED8A89A67FC20C740C125F2AF7D82                                       test_right/same.txt
SHA256          FC84AC773B477963FCD273B8C8E105075EEBEE6CB585456A4B8EA8876C6C3203       test_left/different.txt
SHA256          E32D2C0C6417505595A1C65272DAB8373359135753D76211B90C10E51B6ED312       test_left/only_left.txt
SHA256          9457D486692E7112CCB88EFB62F7680CB0DF8F2B94961CE402EF1ED7C6AA45A8       test_left/same.txt
SHA256          17B08F5E93DC975DA1077F18EB1474111665E1519E6C05B7290D71BF448FFE3D       test_right/different.txt
SHA256          30DCBF1D34D128226633DD2529CA84CC79CB3AFF16E24323718632FE2E3C01FA       test_right/only_right.txt
SHA256          9457D486692E7112CCB88EFB62F7680CB0DF8F2B94961CE402EF1ED7C6AA45A8       test_right/same.txt
"""
