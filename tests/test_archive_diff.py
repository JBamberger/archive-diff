"""
Test cases.
"""
import unittest
from unittest import TestCase

from archive_diff.archive_diff import compute_listing_diff, find_common_prefix, \
    strip_prefix_from_records
from archive_diff.archive_format_handler import HashRecord
from archive_diff.diff_data import DiffState, DiffRecord


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


if __name__ == '__main__':
    unittest.main()
