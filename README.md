# Archive Diff Tool

This Python package contains a tool for archive file comparison. The main goal is to compare two archive files for their
content. The archives can be zip or tar files or alternatively the content of a directory. The primary goal of this tool
to compare the archives without extracting the content. The archives are read and compared without explicit extraction,
i.e. all operations are performed in-memory.
