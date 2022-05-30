"""
Helper to compare file contents.
"""

from __future__ import annotations

import hashlib as hl


class FileHasher:
    """
    Helper class to compute hash values of io streams.
    """

    def __init__(self, hash_algorithm: str, hash_buffer_size=128 * 1024):
        """
        :param hash_algorithm: Hashing algorithm, must be supported by `hashlib`
        :param hash_buffer_size: Buffer size used to read the input streams.
        """
        self.hash_algorithm = hash_algorithm
        self.hash_buffer_size = hash_buffer_size

    def __repr__(self):
        return f'FileHasher({self.hash_algorithm})'

    def compute_hash(self, input_io):
        """
        Computes the hash sum for an input io object.
        :param input_io: input io object
        :return: string with the hex representation of the hash
        """
        digest = hl.new(self.hash_algorithm)
        while True:
            data = input_io.read(self.hash_buffer_size)
            if not data:
                break
            digest.update(data)
        return digest.hexdigest()
