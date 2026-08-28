"""Huffman decoder for the compressed bundle-name tables in superbundle tocs.

Port of FrostySdk's HuffmanDecoder: the table is a flat list of uint32 node
values built bottom-up (pairs of child nodes fold into a new internal node with
an incrementing value); leaf values are the bitwise complement of the character.
Encoded strings are bit streams read LSB-first from an int32 array, walking the
tree (0 = left, 1 = right) until the NUL leaf.
"""
from __future__ import annotations

from .reader import Reader


class _Node:
    __slots__ = ("value", "left", "right")

    def __init__(self, value: int):
        self.value = value
        self.left = None
        self.right = None

    @property
    def leaf(self) -> bool:
        return self.left is None and self.right is None

    @property
    def letter(self) -> int:
        return ~self.value & 0xFFFFFFFF


class HuffmanDecoder:
    def __init__(self):
        self._root: _Node | None = None
        self._data: list[int] = []

    def read_table(self, r: Reader, count: int) -> None:
        nodes: dict[int, _Node] = {}
        left = right = None
        next_internal = 0
        for _ in range(count):
            value = r.u32()
            node = nodes.get(value)
            if node is None:
                node = _Node(value)
                nodes[value] = node
            if left is None:
                left = node
            elif right is None:
                right = node
                parent = _Node(next_internal)
                next_internal += 1
                parent.left, parent.right = left, right
                # parent value may collide with a leaf value only in theory;
                # FrostySdk keys lookups the same way
                nodes[parent.value] = parent
                self._root = parent
                left = right = None

    def read_data(self, r: Reader, int_count: int) -> None:
        self._data = [r.i32() for _ in range(int_count)]

    def decode(self, bit_index: int) -> str:
        if self._root is None:
            raise ValueError("huffman table not loaded")
        total_bits = len(self._data) * 32
        out = []
        while True:
            node = self._root
            while not node.leaf and bit_index < total_bits:
                bit = (self._data[bit_index // 32] >> (bit_index % 32)) & 1
                node = node.right if bit else node.left
                bit_index += 1
            ch = node.letter & 0xFF
            if ch == 0 or bit_index >= total_bits:
                return "".join(out)
            out.append(chr(ch))
