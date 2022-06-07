#!/bin/sh

# --lzip --lzma --lzop --compress --zstd

for file in "test_left" "test_right" "simple_archive"; do
  tar --create --auto-compress --file $file".tar" $file;
  tar --create --auto-compress --file $file".tar.gz" $file;
  tar --create --auto-compress --file $file".tgz" $file;
  tar --create --auto-compress --file $file".tar.bz2" $file;
  tar --create --auto-compress --file $file".tbz2" $file;
  tar --create --auto-compress --file $file".tar.xz" $file;
  tar --create --auto-compress --file $file".txz" $file;
  zip -rq $file $file
  7z a -bd $file".7z" -- $file
done;

