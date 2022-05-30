from __future__ import annotations

import hashlib as hl


class FileHasher:
    def __init__(self, hash_algorithm: str, hash_buffer_size=128 * 1024):
        self.hash_algorithm = hash_algorithm
        self.hash_buffer_size = hash_buffer_size

    def compute_hash(self, io):
        """
        Computes the hash sum for an input io object.
        :param io: input io object
        :return: string with the hex representation of the hash
        """
        m = hl.new(self.hash_algorithm)
        while True:
            data = io.read(self.hash_buffer_size)
            if not data:
                break
            m.update(data)
        return m.hexdigest()
