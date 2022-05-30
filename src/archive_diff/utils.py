"""
Utility functions.
"""

import os
from typing import List


def path_parts(path: str) -> List[str]:
    """
    Splits a path into its parts.
    :param path: Input path.
    :return: parts of the path
    """

    # Replace with pl.Path.parts
    parts = []
    while True:
        rest, part = os.path.split(path)
        if part:
            parts.append(part)

        if path == rest:
            break
        path = rest

    parts.reverse()

    return parts
