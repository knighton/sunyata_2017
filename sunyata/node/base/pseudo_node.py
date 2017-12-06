from collections import defaultdict
from copy import deepcopy


class NodeChainer(object):
    def __init__(self):
        self._next_color = 1
        self._node2color = {}
        self._color2nodes = defaultdict(list)
        self._prev_right = None

    def _new_color(self):
        color = self._next_color
        self._next_color += 1
        return color

    def _attach_to(self, node, color):
        if node in self._node2color:
            node = deepcopy(node)
        self._node2color[node] = color
        self._color2nodes[color].append(node)

    def _color_of(self, node):
        color = self._node2color.get(node)
        if color is not None:
            return color
        color = self._new_color()
        self._attach_to(node, color)
        return color

    def _remove_color(self, node):
        del self._node2color[node]

    def _chain(self, color):
        from ..network import Chain
        nodes = self._color2nodes[color]
        nodes = deepcopy(nodes)
        return Chain(*nodes)

    def connect(self, left, right):
        if left is not self._prev_right:
            self._remove_color(left)
        self._prev_right = right
        color = self._color_of(left)
        self._attach_to(right, color)
        return self._chain(color)


_CHAIN_CACHE = NodeChainer()


class PseudoNode(object):
    def __gt__(self, right):
        _CHAIN_CACHE.connect(self, right)