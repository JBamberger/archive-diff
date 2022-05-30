"""
Helper to display ArchiveDiff on the command line in various formats.
"""

import math
import sys
from collections import defaultdict

from archive_diff.diff_data import DiffState, ArchiveDiff, DiffTreeNode, DiffTreeDirNode, \
    DiffTreeFileNode, build_diff_tree


class DiffPrinter:
    """
    Utility to print archive diffs in various formats
    """

    def __init__(self, suppress_common_lines=False, quiet=False, tree=False, output=sys.stdout):
        """
        :param suppress_common_lines: True to only print lines that differ.
        :param quiet: True to use a short one line summary of the number of differences
        :param tree: True to print a tree-like diff output.
        :param output: Output stream to write to.
        """
        self.suppress_common_lines = suppress_common_lines
        self.quiet = quiet
        self.tree = tree
        self.output = output

        self._state_to_name = {
            DiffState.EQUAL: 'Equal',
            DiffState.DIFFERENT: 'Different',
            DiffState.ONLY_LEFT: 'Only left',
            DiffState.ONLY_RIGHT: 'Only right',
        }
        self._divider = '*' * 80

    def line(self, *args):
        """
        Prints a line to the configured output stream.
        :param args: line contents
        """
        print(*args, file=self.output)

    def print_diff(self, archive_diff: ArchiveDiff):
        """
        Prints the given diff in the configured output format.
        :param archive_diff: Archive diff to print.
        :throws ValueError: If there are duplicate paths in the diff.
        """
        counts_per_state = defaultdict(lambda: 0)
        for record in archive_diff.records:
            counts_per_state[record.result] += 1

        if self.quiet:
            if (archive_diff.prefix_left != archive_diff.prefix_right) or \
                    (sum(counts_per_state.values()) - counts_per_state[DiffState.EQUAL] > 0):
                prefix = "diff" if archive_diff.prefix_left != archive_diff.prefix_right else "same"
                self.line(f'Different:'
                          f' prefix={prefix}'
                          f' e={counts_per_state[DiffState.EQUAL]}'
                          f' d={counts_per_state[DiffState.DIFFERENT]}'
                          f' ol={counts_per_state[DiffState.ONLY_LEFT]}'
                          f' or={counts_per_state[DiffState.ONLY_RIGHT]}'
                          )
            return

        self.line(self._divider)

        if archive_diff.prefix_left != archive_diff.prefix_right:
            self.line('Prefixes differ:')
            self.line('Prefix 1:', archive_diff.prefix_left)
            self.line('Prefix 2:', archive_diff.prefix_right)
            self.line(self._divider)

        if self.tree:
            self.print_diff_tree(archive_diff)
        else:
            self.print_line_diff(archive_diff)

        self.line(self._divider)

        max_count = int(math.ceil(math.log10(max(counts_per_state.values()))))
        pattern = f'{{state_name:11s}} {{state_count:{max_count:d}d}}'
        for state in DiffState:
            self.line(pattern.format(state_name=self._state_to_name[state] + ":",
                                     state_count=counts_per_state[state]))

        self.line(self._divider)

    def print_line_diff(self, archive_diff):
        """
        Prints a line-based diff.
        :param archive_diff: Archive diff to print.
        """
        state_to_symbol = {
            DiffState.EQUAL: ' ',
            DiffState.DIFFERENT: '|',
            # The actual diff tool uses '/' for the last line of each differing block.
            DiffState.ONLY_LEFT: '<',
            DiffState.ONLY_RIGHT: '>',
        }
        longest_path = max(len(r.relpath) for r in archive_diff.records)
        record_template = f'{{rel_path:{longest_path}s}} {{state_sym:s}} {{state_name:s}}'
        for record in archive_diff.records:
            if not (self.suppress_common_lines and record.result == DiffState.EQUAL):
                self.line(record_template.format(
                    rel_path=record.relpath,
                    state_sym=state_to_symbol[record.result],
                    state_name=self._state_to_name[record.result]))

    def print_diff_tree(self, archive_diff):
        """
        Prints a tree-style diff.
        :param archive_diff: Archive diff to print.
        :throws ValueError: If there are duplicate paths in the diff.
        """
        state_to_symbol = {
            DiffState.EQUAL: '=',
            DiffState.DIFFERENT: '#',
            # The actual diff tool uses '/' for the last line of each differing block.
            DiffState.ONLY_LEFT: '<',
            DiffState.ONLY_RIGHT: '>',
        }

        def print_tree_node(node: DiffTreeNode, prefix):
            """
            Helper function to print a node of the tree and all of its child nodes.
            :param node: node to print
            :param prefix: current line prefix.
            """
            if isinstance(node, DiffTreeDirNode):
                if not (self.suppress_common_lines and node.all_equal):
                    self.line(prefix + f'{"=" if node.all_equal else "#":s} {node.name:s}')
                    for child in node.children:
                        print_tree_node(child, prefix + '|   ')
            elif isinstance(node, DiffTreeFileNode):
                if not (self.suppress_common_lines and node.state == DiffState.EQUAL):
                    self.line(prefix + f'{state_to_symbol[node.state]:s} {node.name:s}')
            else:
                raise ValueError('Invalid node type ' + str(type(node)))

        tree = build_diff_tree(archive_diff)
        print_tree_node(tree, '')


def print_diff(archive_diff: ArchiveDiff, *, suppress_common_lines=False, quiet=False,
               tree=False) -> None:
    """
    Prints the diff object as in a human-readable format to the standard output.

    :param archive_diff: diff object
    """

    printer = DiffPrinter(suppress_common_lines=suppress_common_lines, quiet=quiet, tree=tree)
    printer.print_diff(archive_diff)
