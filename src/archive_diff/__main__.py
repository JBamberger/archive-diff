import argparse
import pathlib as pl

from archive_diff.archive_diff import compute_hash_listing, compute_diff, print_diff


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
    args = parser.parse_args()

    listing1 = compute_hash_listing(args.file1)
    listing2 = compute_hash_listing(args.file2)

    archive_diff = compute_diff(listing1, listing2)

    print_diff(archive_diff)


if __name__ == '__main__':
    main()
