from .... import backend as Z
from ..base import node_wrap, TransformLayer, TransformSpec


class HardSigmoidLayer(TransformLayer):
    def transform(self, x, is_training):
        return Z.hard_sigmoid(x)


class HardSigmoidSpec(TransformSpec):
    def __init__(self, ndim=None):
        super().__init__(ndim)

    def build_transform(self, form):
        return HardSigmoidLayer(), form


node_wrap(HardSigmoidSpec)
