import numpy as np
import torch
from torch.autograd import Variable


class Device(object):
    def __init__(self, id):
        assert isinstance(id, int)
        assert 0 <= id
        self.id = id

    @property
    def type(self):
        return 'gpu' if self.id else 'cpu'

    def is_cpu(self):
        return not self.id

    def is_gpu(self):
        return bool(self.id)


class API(object):
    def __init__(self):
        data = """
            uint8    torch.ByteTensor    torch.cuda.ByteTensor
            int8     torch.CharTensor    torch.cuda.CharTensor
            int16    torch.ShortTensor   torch.cuda.ShortTensor
            int32    torch.IntTensor     torch.cuda.IntTensor
            int64    torch.LongTensor    torch.cuda.LongTensor
            float16  torch.HalfTensor    torch.cuda.HalfTensor
            float32  torch.FloatTensor   torch.cuda.FloatTensor
            float64  torch.DoubleTensor  torch.cuda.DoubleTensor
        """

        self._tensor2dtype = {}
        self._dtype2cpu = {}
        self._dtype2gpu = {}
        for line in data.strip().split('\n'):
            dtype, cpu, gpu = line.split()
            self._tensor2dtype[cpu] = dtype
            self._dtype2cpu[dtype] = cpu
            self._tensor2dtype[gpu] = dtype
            self._dtype2gpu[dtype] = gpu

        self._devices = []
        for device_id in range(self.num_gpus() + 1):
            device = Device(device_id)
            self._devices.append(device)
        self._default_device = self._devices[-1]

    def constant(self, tensor):
        return Variable(tensor, requires_grad=False)

    def variable(self, tensor):
        return Variable(tensor, requires_grad=True)

    def num_gpus(self):
        return torch.cuda.device_count()

    def clip(self, x, min=-np.inf, max=np.inf):
        return x.clamp(min=0)

    def rank(self, x):
        return len(x.size())

    def shape(self, x):
        return tuple(x.size())

    def size(self, x):
        return x.nelement()

    def matmul(self, a, b):
        return a.mm(b)

    def default_dtype(self):
        return 'float32'

    def dtype(self, x):
        return x or self.default_dtype()

    def dtype_of(self, x):
        if isinstance(x, torch._TensorBase):
            tensor = x
        elif isinstance(x, Variable):
            tensor = x.data
        else:
            assert False
        return self._tensor2dtype[tensor.type()]

    def default_device(self):
        return self._default_device

    def device(self, x):
        if x is None:
            return self._default_device
        elif isinstance(x, Device):
            device = x
        else:
            assert isinstance(x, int)
            assert 0 <= x < len(self._devices)
            device = self._devices[x]
        return device

    def device_of(self, x):
        if x.is_cuda:
            device_id = x.get_device()
        else:
            device_id = 0
        return self._devices[device_id]

    def cast_onto(self, x, dtype=None, device=None, copy=False):
        dtype = self.dtype(dtype)
        tensor_class = self._get_tensor_class(dtype, device)
        if self.dtype_of(x) != dtype:
            x = x.type(tensor_class)
        from_device = self.device_of(x)
        to_device = self.device(device)
        if from_device.is_cpu():
            if to_device.is_cpu():
                if copy:
                    x = x.clone()
            elif to_device.is_gpu():
                with torch.cuda.device(to_device.gpu_id()):
                    x = x.cuda()
            else:
                assert False
        elif from_device.is_gpu():
            if to_device.is_cpu():
                x = x.cpu()
            elif to_device.is_gpu():
                if from_device is to_device:
                    if copy:
                        x = x.clone()
                else:
                    with torch.cuda.device(to_device.gpu_id()):
                        x = x.cuda()
            else:
                assert False
        else:
            assert False
        return x

    def cast(self, x, dtype=None, copy=False):
        return self.cast_onto(x, dtype, None, copy)

    def to_device(self, x, device=None, copy=False):
        return self.cast_onto(x, None, device, copy)

    def to_cpu(self, x, copy=False):
        return self.to_device(x, 0, copy)

    def to_gpu(self, x, device, copy=False):
        device = self.to_device(device)
        assert device.is_gpu()
        return self.to_device(x, device, copy)

    def _get_tensor_class(self, dtype, device):
        if device.is_cpu():
            dtype2class = self._dtype2cpu[dtype]
        elif device.is_gpu():
            dtype2class = self._dtype2gpu[dtype]
        else:
            assert False
        return dtype2class[dtype]

    def cast_numpy_onto(self, x, dtype=None, device=None):
        if dtype is not None:
            x = x.astype(dtype)
        device = self.device(device)
        if device.is_cpu():
            x = torch.from_numpy(x)
        elif device.is_gpu():
            with torch.cuda.device(device.gpu_id()):
                x = self._get_tensor_class(dtype, device)(x)
        else:
            assert False
        return x

    def assign(self, x, new_value):
        x.data = new_value
        x.grad.data.zero_()


Z = API()


class Form(object):
    def __init__(self, shape, dtype):
        self.shape = shape
        self.dtype = dtype

    def check(self, x):
        assert tuple(Z.shape(x)[1:]) == self.shape
        assert Z.dtype_of(x) == self.dtype


class Layer(object):
    def params(self):
        return []

    def forward(self, x):
        raise NotImplementedError


class InputLayer(Layer):
    def __init__(self, form):
        self.form = form

    def forward(self, x):
        self.form.check(x)
        return x


class DenseLayer(Layer):
    def __init__(self, kernel, bias):
        self.kernel = Z.variable(Z.cast_numpy_onto(kernel))
        self.bias = Z.variable(Z.cast_numpy_onto(bias))

    def params(self):
        return [self.kernel, self.bias]

    def forward(self, x):
        return Z.matmul(x, self.kernel) + self.bias


class ReLULayer(Layer):
    def forward(self, x):
        return Z.clip(x, min=0)


class SequenceLayer(Layer):
    def __init__(self, layers):
        self.layers = layers

    def params(self):
        params = []
        for layer in self.layers:
            params += layer.params()
        return params

    def forward(self, x):
        for layer in self.layers:
            x = layer.forward(x)
        return x


class Spec(object):
    def build(self, form=None):
        raise NotImplementedError


class InputSpec(Spec):
    def __init__(self, shape, dtype):
        self.form = Form(shape, dtype)

    def build(self, form=None):
        assert form is None
        return InputLayer(self.form), self.form


class DenseSpec(Spec):
    def __init__(self, out_dim):
        self.out_dim = out_dim

    def build(self, form=None):
        in_dim, = form.shape
        kernel = np.random.normal(
            0, 1, (in_dim, self.out_dim)).astype('float32')
        bias = np.random.normal(0, 1, (self.out_dim,)).astype('float32')
        out_shape = self.out_dim,
        return DenseLayer(kernel, bias), Form(out_shape, form.dtype)


class ReLUSpec(Spec):
    def build(self, form=None):
        return ReLULayer(), form


class SequenceSpec(Spec):
    def __init__(self, specs):
        self.specs = specs

    def build(self, form=None):
        layers = []
        for spec in self.specs:
            layer, form = spec.build(form)
            layers.append(layer)
        return SequenceLayer(layers), form


def mean_squared_error(true, pred):
    return (true - pred).pow(2).sum()


class Optimizer(object):
    def set_params(self, params):
        self.params = params

    def update_param(self, param):
        raise NotImplementedError

    def update(self):
        for param in self.params:
            self.update_param(param)


class SGD(Optimizer):
    def __init__(self, lr):
        self.lr = lr

    def update_param(self, param):
        Z.assign(param, param.data - self.lr * param.grad.data)


batch_size = 64
in_dim = 1000
hidden_dim = 100
num_classes = 10
lr = 1e-6

x = np.random.normal(0, 1, (batch_size, in_dim)).astype('float32')
x = Z.constant(Z.cast_numpy_onto(x))

y = np.random.normal(0, 1, (batch_size, num_classes)).astype('float32')
y = Z.constant(Z.cast_numpy_onto(y))

model = SequenceSpec([
    InputSpec((in_dim,), 'float32'),
    DenseSpec(hidden_dim),
    ReLUSpec(),
    DenseSpec(num_classes),
])

model, out_shape = model.build()

opt = SGD(lr)
opt.set_params(model.params())

for t in range(500):
    y_pred = model.forward(x)

    loss = mean_squared_error(y, y_pred)
    print(t, loss.data[0])

    loss.backward()

    opt.update()
