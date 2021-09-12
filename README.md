# 说明
复旦大学自动选课脚本

# 安装

```bash
git clone https://github.com/Limourli-liu/FDU_auto_electCourse.git --depth 1
cd FDU_auto_electCourse/
pip3 install -r requirements.txt
```

# 验证码识别

基于 `PyTorch`

采用 `cnn_LSTM_fc_CTC` 的网络结构

预训练模型在 `data/FDUXK/Captcha_break/cnn_LSTM_fc_CTC.pth`

训练数据 以 `ID_label.jpg` 命名 保存在 `data/FDUXK/Captcha_break/Captcha_train/`目录下

来源：

1、https://github.com/ypwhs/captcha_break/blob/master/ctc_pytorch.ipynb

2、https://github.com/sml2h3/captcha_trainer_pytorch/blob/master/framework.py

**注意：**

**1、数据标注未完成，请手动将待标注的数据完成标注后，保存到 训练数据的目录下**

**2、待标注的数据在 `data/FDUXK/Captcha_break/Captcha` 目录下**

**3、进入 `FDUXK`目录，运行 `python3 ./Captcha_break.py` 完成训练**

# 使用

`python3 ./start_xk.py`

打开 http://127.0.0.1:12021/mod/FDUxk

