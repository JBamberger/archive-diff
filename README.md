# Archive Diff Tool

This Python package contains a tool for archive file comparison. The main goal is to compare two archive files for their
content. The archives can be zip or tar files or alternatively the content of a directory. The primary goal of this tool
to compare the archives without extracting the content. The archives are read and compared without explicit extraction,
i.e. all operations are performed in-memory.

## The algorithm

The algorithm is quite simple. The file identity is determined by its path relative to the archive root. By default, a
prefix common to all files is ignored, i.e. if all files in the archive are in a directory the directory name is not
part of its identity. This can be changed to include such common directories.

The files of the two archives are matched based on this identity. Equality is determined by a hash function over the
file content. `MD5` is the default hash function, but any function supported by the python standard library can be used.

## Build and install

### Local install

```shell
python setup.py install
# or alternatively
python -m pip install .
```

### Supported formats

Out of the box, the tool supports zip, tar and directory archives. For additional archive additional modules need to be
installed.

| File type | Support                                                 | Notes                           |
|-----------|---------------------------------------------------------|---------------------------------|
| directory | -                                                       |                                 |
| `zip`     | -                                                       |                                 | 
| `tar`     | supports `gzip`, `bzip2`, `LZMA2/xz` and no compression |                                 |
| `7z`      | requires `py7zr` package                                | Does not work in streaming mode |

### Development and distribution

Development install:

```shell
python -m pip install -e .
```

The development install will update automatically with changes in the code base. This is useful for rapid testing
without rebuilding the package each time.

To build the package for distribution use the following commands:

```shell
python -m pip install --upgrade build
python -m build
```

### Running tests

Some test cases require generated files. First, run the script `tests/test_files/create_archives.sh`.
The tests can be run by calling `python3 -m unittest` in the project root directory.

## Usage

Simple diff between two archive files:

```shell
archive-diff left.tar.gz right.zip
```

By default, common prefix paths common to all files in the archive are ignored. If such a prefix is found for any of the
archives, the prefix is displayed. If this is not desired, add the `--keep-prefix` flag. To print only the differences
between the archives, ignoring the common files, add the `--suppress-common` flag.

To change the content hash function use `--hash-algorithm <algo>`. Available algorithms are printed by

```shell
archive-diff --help
```