"""
Command-line interface to the archive-diff module.
"""

import argparse
import hashlib
import pathlib as pl

from archive_diff import ArchiveDiffer, print_diff


def main():
    """
    Main method that handles the command line interface of archive-diff
    """
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
                        help='Keeps the path prefixes (root directories of the archives) for'
                             ' comparison. By default the prefix is ignored.')
    parser.add_argument('--hash-algorithm',
                        required=False,
                        choices=hashlib.algorithms_available,
                        default='md5',
                        help='Hash algorithm used for file equality comparison.')
    parser.add_argument('--suppress-common',
                        action='store_true',
                        help='Only prints the file paths that differ.')
    parser.add_argument('--quiet', '-q',
                        action='store_true',
                        help='Only print something if the archives differ.')
    parser.add_argument('--tree',
                        action='store_true',
                        help='Print the output as a tree instead of a flat list of files.')
    args = parser.parse_args()

    differ = ArchiveDiffer(keep_prefix=args.keep_prefix, hash_algorithm=args.hash_algorithm)
    try:
        archive_diff = differ.compute_diff(args.file1, args.file2)
    except FileNotFoundError as error:
        print(f'File not found: {error.filename}')
        return

    print_diff(archive_diff, suppress_common_lines=args.suppress_common, quiet=args.quiet,
               tree=args.tree)


if __name__ == '__main__':
    main()
