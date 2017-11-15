class Layer(object):
    def params(self):
        return []

    def forward_multi(self, xx, is_training):
        raise NotImplementedError


class MergeLayer(Layer):
    pass


class TransformLayer(Layer):
    def forward_one(self, x, is_training):
        raise NotImplementedError

    def forward_multi(self, xx, is_training):
        assert len(xx) == 1
        x, = xx
        x = self.forward_one(x, is_training)
        return [x]
