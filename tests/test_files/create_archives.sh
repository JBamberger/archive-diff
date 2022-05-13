#!/bin/sh

# --lzip --lzma --lzop --compress --zstd

for file in "test_left" "test_right"; do
  for ext in ".tar" ".tar.gz" ".tar.bz2" ".tar.xz"; do
    tar --create --auto-compress --file $file$ext $file;
  done;
  zip $file $file
done;

