import tensorflow as tf

from ...base.core.shape import BaseShapeAPI


class TensorFlowShapeAPI(BaseShapeAPI):
    def __init__(self):
        BaseShapeAPI.__init__(self)

    def ndim(self, x):
        return len(x.shape)

    def shape(self, x):
        return tuple(map(int, x.shape))

    def size(self, x):
        return int(tf.size(x).numpy())

    def reshape(self, x, shape):
        return tf.reshape(x, shape)

    def expand_dims(self, x, axis):
        return tf.expand_dims(x, axis)

    def squeeze(self, x, axis=None):
        return tf.squeeze(x, axis)

    def tile(self, x, reps):
        return tf.tile(x, reps)

    def transpose(self, x, axes):
        return tf.transpose(x, axes)

    def concat(self, xx, axis):
        return tf.concat(xx, axis)

    def stack(self, xx, axis=0):
        return tf.stack(xx, axis)