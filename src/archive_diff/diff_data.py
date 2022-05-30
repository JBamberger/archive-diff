from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Callable, Optional


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
    This record represents an archive file path with the associated difference state between the two inputs.
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
        counts = {s: 0 for s in DiffState}
        for r in self.records:
            counts[r.result] += 1

        return counts


@dataclass
class DiffTreeNode(ABC):
    name: str

    @abstractmethod
    def visit(self, visitor: Callable[[DiffTreeNode], None]):
        raise NotImplementedError()


class DiffTreeDirNode(DiffTreeNode):
    all_equal: bool
    children: List[DiffTreeNode]

    def __init__(self, name: str, children: List[DiffTreeNode]):
        super(DiffTreeDirNode, self).__init__(name)

        def check_equality(node: DiffTreeNode) -> bool:
            if isinstance(node, DiffTreeFileNode):
                return node.state == DiffState.EQUAL
            elif isinstance(node, DiffTreeDirNode):
                return node.all_equal
            else:
                raise ValueError('Node is not a valid DiffTreeNode.')

        self.children = children
        self.all_equal = all(check_equality(node) for node in self.children)

    def visit(self, visitor: Callable[[DiffTreeNode], None]):
        visitor(self)
        for child in self.children:
            child.visit(visitor)


class DiffTreeFileNode(DiffTreeNode):
    state: DiffState
    left_hash: Optional[str]
    right_hash: Optional[str]

    def __init__(self, name: str, state: DiffState):
        super(DiffTreeFileNode, self).__init__(name)
        self.state = state

    def visit(self, visitor: Callable[[DiffTreeNode], None]):
        visitor(self)


def build_diff_tree(archive_diff: ArchiveDiff) -> DiffTreeNode:
    @dataclass
    class DictNode:
        files: List[DiffTreeFileNode]
        dirs: Dict[str: DictNode]

        def __init__(self):
            self.files = []
            self.dirs = {}

    def to_tree_node(name: str, node: DictNode) -> DiffTreeDirNode:
        children = []
        for k, v in node.dirs.items():
            children.append(to_tree_node(k, v))

        children += node.files

        return DiffTreeDirNode(name, children)

    archive_root = DictNode()
    for record in archive_diff.records:
        parts = record.relpath.split('/')

        d = archive_root
        while len(parts) > 1:
            part = parts.pop(0)
            try:
                d = archive_root.dirs[part]
            except KeyError:
                d = DictNode()
                archive_root.dirs[part] = d

        file_name = parts[0]
        d.files.append(DiffTreeFileNode(file_name, state=record.result))

    return to_tree_node('.', archive_root)
