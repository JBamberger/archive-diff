"""
Data classes representing an archive diff.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Optional


class DiffState(Enum):
    """
    Enumeration that describes possible difference states for a single file path in the archive.
    """

    EQUAL = auto()
    DIFFERENT = auto()
    ONLY_LEFT = auto()
    ONLY_RIGHT = auto()


@dataclass
class DiffRecord:
    """
    This record represents an archive file path with the associated difference state between the two
    inputs.
    """
    relpath: str
    result: DiffState


@dataclass
class ArchiveDiff:
    """
    This class contains the full results of an archive diff.
    """
    prefix_left: str
    prefix_right: str
    records: List[DiffRecord]

    def stats(self) -> Dict[DiffState, int]:
        """
        Computes the total number of occurrences per `DiffState`.
        :return: Dict mapping `DiffState` to the corresponding file counts.
        """
        counts = {state: 0 for state in DiffState}
        for record in self.records:
            counts[record.result] += 1

        return counts


@dataclass
class DiffTreeNode(ABC):
    """
    Base class of a node in a diff tree.
    """
    name: str


@dataclass
class DiffTreeDirNode(DiffTreeNode):
    """
    Node in a diff tree representing a directory.
    """
    all_equal: bool
    children: List[DiffTreeNode]

    def __init__(self, name: str, children: List[DiffTreeNode]):
        """
        :param name: Name of this node.
        :param children: List of children of this directory.
        """
        super().__init__(name)

        def check_equality(node: DiffTreeNode) -> bool:
            if isinstance(node, DiffTreeFileNode):
                return node.state == DiffState.EQUAL

            if isinstance(node, DiffTreeDirNode):
                return node.all_equal

            raise ValueError('Node is not a valid DiffTreeNode.')

        self.children = children
        self.all_equal = all(check_equality(node) for node in self.children)


@dataclass
class DiffTreeFileNode(DiffTreeNode):
    """
    Diff tree node representing a file.
    """
    state: DiffState
    left_hash: Optional[str]
    right_hash: Optional[str]

    def __init__(self, name: str, state: DiffState):
        """
        :param name: Name of this node.
        :param state: Diff state of this node.
        """
        super().__init__(name)
        self.state = state


def build_diff_tree(archive_diff: ArchiveDiff) -> DiffTreeNode:
    """
    Helper function to build a diff tree from an archive diff.

    :param archive_diff: Input archive diff.
    :return: Root node of the generated diff tree.
    """

    @dataclass
    class DictNode:
        """
        Helper class used to represent the intermediate diff tree.
        """

        files: List[DiffTreeFileNode]
        dirs: Dict[str: DictNode]

        def __init__(self):
            """
            Creates an empty subtree without dirs or files.
            """
            self.files = []
            self.dirs = {}

    def to_tree_node(name: str, node: DictNode) -> DiffTreeDirNode:
        """
        Converts a `DictNode`-based tree to a diff-tree recursively.

        :param name: Root name
        :param node: Root `DictNode`
        :return:
        """
        children = []
        for key, value in node.dirs.items():
            children.append(to_tree_node(key, value))

        children += node.files

        return DiffTreeDirNode(name, children)

    # First, build the DictNode-based tree from the records
    archive_root = DictNode()
    for record in archive_diff.records:
        parts = record.relpath.split('/')

        directory = archive_root
        while len(parts) > 1:
            part = parts.pop(0)
            try:
                directory = archive_root.dirs[part]
            except KeyError:
                directory = DictNode()
                archive_root.dirs[part] = directory

        file_name = parts[0]
        directory.files.append(DiffTreeFileNode(file_name, state=record.result))

    # Then convert to DiffTreeNodes
    return to_tree_node('.', archive_root)
