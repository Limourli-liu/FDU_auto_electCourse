config, Manager, log, lock = 0,0,0,0 #保存宿主传递的环境 分别为配置文件， 模块管理器，日志，全局线程锁
def _default_config(root, name): #返回默认配置文件 载入时被调用 root为数据文件根目录 name为当前模块名称
    return {
        'modInformation':{ #该模块的信息
            'Name': 'BaseMod editor',
            'Author': 'Limour @limour.top',
            'Version': '1.0',
            'description': 'A simple web editor'
        },
        'model_path': f'{root}/Captcha_break/cnn_LSTM_fc_CTC.pth',
        'triandata_path': f'{root}/Captcha_break/Captcha_train',
        'use_cuda': True,
        'priority': 9997
    }

def _init(m_name, _config, _Manager, _log): #载入时被调用
    global config, Manager, log, lock, db, model
    config, Manager, log, lock = _config, _Manager, _log, _Manager.threading_lock #保存宿主传递的环境
    loadModel()
    model.eval()

# 加载相关库
import os
from unicodedata import name
from PIL import Image
from io import BytesIO
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms.functional import to_tensor, to_pil_image

import numpy as np
from collections import OrderedDict
import string

from IPython.display import display
from tqdm import tqdm

# 修复pickle导入文件 需要显示引用的BUG
tp_Unpickler = torch.serialization.pickle.Unpickler
class CustomUnpickler(tp_Unpickler):
    def find_class(self, __module_name: str, __global_name: str):
        try: 
            return super(CustomUnpickler, self).find_class(__name__, __global_name)
        except AttributeError:
            return super(CustomUnpickler, self).find_class(__module_name, __global_name)
torch.serialization.pickle.Unpickler = CustomUnpickler


def _path(name, root=None):
    p =  os.path.join(root or os.getcwd(), name)
    return (os.path.exists(p) or not os.makedirs(p)) and p

# 定义网络模型
class Model(nn.Module):
    def __init__(self, n_classes, input_shape=(3, 64, 128)):
        super(Model, self).__init__()
        self.input_shape = input_shape
        channels = [32, 64, 128, 256, 256]
        layers = [2, 2, 2, 2, 2]
        kernels = [3, 3, 3, 3, 3]
        pools = [2, 2, 2, 2, (2, 1)]
        modules = OrderedDict()
        
        def cba(name, in_channels, out_channels, kernel_size):
            modules[f'conv{name}'] = nn.Conv2d(in_channels, out_channels, kernel_size,
                                               padding=(1, 1) if kernel_size == 3 else 0)
            modules[f'bn{name}'] = nn.BatchNorm2d(out_channels)
            modules[f'relu{name}'] = nn.ReLU(inplace=True)
        
        last_channel = 3
        for block, (n_channel, n_layer, n_kernel, k_pool) in enumerate(zip(channels, layers, kernels, pools)):
            for layer in range(1, n_layer + 1):
                cba(f'{block+1}{layer}', last_channel, n_channel, n_kernel)
                last_channel = n_channel
            modules[f'pool{block + 1}'] = nn.MaxPool2d(k_pool)
        modules[f'dropout'] = nn.Dropout(0.25, inplace=True)
        
        self.cnn = nn.Sequential(modules)
        self.lstm = nn.LSTM(input_size=self.infer_features(), hidden_size=128, num_layers=2, bidirectional=True)
        self.fc = nn.Linear(in_features=256, out_features=n_classes)
    
    def infer_features(self):
        x = torch.zeros((1,)+self.input_shape)
        x = self.cnn(x)
        x = x.reshape(x.shape[0], -1, x.shape[-1])
        return x.shape[1]

    def forward(self, x):
        x = self.cnn(x)
        x = x.reshape(x.shape[0], -1, x.shape[-1])
        x = x.permute(2, 0, 1)
        x, _ = self.lstm(x)
        x = self.fc(x)
        return x

# 加载预训练的模型
def loadModel():
    global model
    model = torch.load(config['model_path'])
    if torch.cuda.is_available() and config['use_cuda']:
        model = model.cuda()
def saveModel():
    torch.save(model, config['model_path'])

# 定义验证码编码
characters = '-' + string.digits + string.ascii_uppercase + string.ascii_lowercase
def decode(sequence):
    a = ''.join([characters[x] for x in sequence])
    s = ''.join([x for j, x in enumerate(a[:-1]) if x != characters[0] and x != a[j+1]])
    if len(s) == 0:
        return ''
    if a[-1] != characters[0] and s[-1] != a[-1]:
        s += a[-1]
    return s

# 定义预测函数
def pred_m(image):  
    output = model(image.unsqueeze(0).cuda())
    output_argmax = output.detach().permute(1, 0, 2).argmax(dim=-1)
    return decode(output_argmax[0])
def torchOCR(imgdata):
    if type(imgdata) is bytearray or type(imgdata) is bytes:
        img = Image.open(BytesIO(imgdata))
    else:
        img = imgdata
    img = img.resize((180, 70), Image.ANTIALIAS)
    img = to_tensor(img)
    res = pred_m(img)
    return res

# 定义训练数据的载入函数
def getImgD(path):
    return Image.open(path)
def getSample():
    lc_i = 0
    while True:
        if lc_i >= len(data_list): lc_i = 0 # 越界从0开始
        lc_image = getImgD(_path(data_list[lc_i], data_root))
        lc_label = data_list[lc_i].split(".")[1]
        # display(lc_image, lc_label)
        yield lc_image, lc_label
        lc_i += 1
class MyDataset(Dataset):
    def __init__(self, characters, length, width, height, input_length, label_length):
        super(MyDataset, self).__init__()
        self.characters = characters
        self.length = length
        self.width = width
        self.height = height
        self.input_length = input_length
        self.label_length = label_length
        self.n_class = len(characters)
        self.generator = getSample()
    def __len__(self):
        return self.length
    def __getitem__(self, index):
        image,random_str = next(self.generator)
        image = image.resize((180, 70),Image.ANTIALIAS)
        image = to_tensor(image)
        target = torch.tensor([self.characters.find(x) for x in random_str], dtype=torch.long)
        input_length = torch.full(size=(1, ), fill_value=self.input_length, dtype=torch.long)
        target_length = torch.full(size=(1, ), fill_value=self.label_length, dtype=torch.long)
        return image, target, input_length, target_length

# 训练的准备工作
def decode_target(sequence):
    return ''.join([characters[x] for x in sequence]).replace(' ', '')

def calc_acc(target, output):
    output_argmax = output.detach().permute(1, 0, 2).argmax(dim=-1)
    target = target.cpu().numpy()
    output_argmax = output_argmax.cpu().numpy()
    a = np.array([decode_target(true) == decode(pred) for true, pred in zip(target, output_argmax)])
    return a.mean()

def train(model, optimizer, epoch, dataloader):
    model.train()
    loss_mean = 0
    acc_mean = 0
    with tqdm(dataloader) as pbar:
        for batch_index, (data, target, input_lengths, target_lengths) in enumerate(pbar):
            data, target = data.cuda(), target.cuda()
            
            optimizer.zero_grad()
            output = model(data)
            
            output_log_softmax = F.log_softmax(output, dim=-1)
            loss = F.ctc_loss(output_log_softmax, target, input_lengths, target_lengths)
            
            loss.backward()
            optimizer.step()

            loss = loss.item()
            acc = calc_acc(target, output)

            
            if batch_index == 0:
                loss_mean = loss
                acc_mean = acc
            
            loss_mean = 0.1 * loss + 0.9 * loss_mean
            acc_mean = 0.1 * acc + 0.9 * acc_mean
            
            pbar.set_description(f'Epoch: {epoch} Loss: {loss_mean:.4f} Acc: {acc_mean:.4f} ')

if __name__ == "__main__":
    config = _default_config("../data/FDUXK", "Captcha_break")
    loadModel()
    model.train()
    # 模型的一些定义
    width, height, n_len, n_classes = 180, 70, 4, len(characters)
    n_input_length = 11
    # 训练前的准备工作
    global data_root, data_list
    data_root = config['triandata_path']
    data_list = next(os.walk(data_root))[2]
    batch_size = 32
    train_set = MyDataset(characters, 100 * batch_size, width, height, n_input_length, n_len)
    train_loader = DataLoader(train_set, batch_size=batch_size, num_workers=os.cpu_count())

    # 开始训练
    optimizer = torch.optim.Adam(model.parameters(), 1e-3, amsgrad=True)
    epochs = 5 # 训练轮数 自行设置
    for epoch in range(1, epochs + 1):
        train(model, optimizer, epoch, train_loader)
    # 保存训练后的模型
    saveModel()
