import argparse
import hashlib
import pathlib as pl

import archive_diff
from archive_diff.archive_diff import ArchiveDiffer, print_diff


def main():
    parser = argparse.ArgumentParser("Archive-diff", description='''Diff tool for archive files.''')
    parser.add_argument('file1',
                        type=pl.Path,
                        metavar='FILE_1',
                        help='First archive file.')
    parser.add_argument('file2',
                        type=pl.Path,
                        metavar='FILE_2',
                        help='Second archive file.')
    parser.add_argument('--keep-prefix',
                        action='store_true',
                        help='Keeps the path prefixes (root directories of the archives) for comparison. By default the'
                             ' prefix is ignored.')
    parser.add_argument('--hash-algorithm',
                        required=False,
                        choices=hashlib.algorithms_available,
                        default='md5',
                        help='Hash algorithm used for file equality comparison.')
    args = parser.parse_args()

    differ = ArchiveDiffer(keep_prefix=args.keep_prefix, hash_algorithm=args.hash_algorithm)
    print_diff(differ.compute_diff(args.file1, args.file2))


if __name__ == '__main__':
    main()
